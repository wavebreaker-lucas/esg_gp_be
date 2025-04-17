"""
Strategy pattern implementations for emissions calculations.

This module provides different calculation strategies for various metric types,
enabling accurate and type-specific emission calculations.
"""

from abc import ABC, abstractmethod
import json
from decimal import Decimal
import logging
import uuid

from django.db.models import QuerySet
from django.db.models import Sum, Avg, Max, Min

logger = logging.getLogger(__name__)

class EmissionCalculationStrategy(ABC):
    """Base abstract class for emission calculation strategies"""
    
    @abstractmethod
    def calculate(self, rpv, metric, year, region):
        """
        Calculate emissions for the given metric and reported value.
        
        Args:
            rpv: ReportedMetricValue instance containing the activity data
            metric: The specific metric instance (e.g., BasicMetric, VehicleTrackingMetric)
            year: Reporting year (from rpv.reporting_period.year)
            region: Region code (from metric.location)
            
        Returns:
            List of calculation results. Each result is a dictionary with:
            {
                'factor': GHGEmissionFactor instance,
                'activity_value': Decimal value used for calculation,
                'emission_value': Decimal calculated emission value,
                'proportion': Decimal representing proportion of total (0.0-1.0),
                'metadata': dict with additional data about this calculation
            }
            
            Returns empty list if calculation couldn't be performed.
        """
        pass


class BasicMetricCalculationStrategy(EmissionCalculationStrategy):
    """Strategy for simple metrics with a single value and factor"""
    
    def calculate(self, rpv, metric, year, region):
        """Calculate emissions for basic metrics"""
        from ..services.emissions import find_matching_emission_factor
        
        if rpv.aggregated_numeric_value is None:
            return []
            
        # Get appropriate unit based on metric type
        activity_unit = self._get_unit(metric)
            
        # Find matching factor
        factor = find_matching_emission_factor(
            year=year,
            category=metric.emission_category,
            sub_category=metric.emission_sub_category,
            activity_unit=activity_unit,
            region=region
        )
        
        if not factor:
            logger.warning(f"No suitable emission factor found for metric {metric.pk} with category={metric.emission_category}, sub_category={metric.emission_sub_category}")
            return []
            
        # Calculate with single factor
        activity_value = Decimal(str(rpv.aggregated_numeric_value))
        emission_value = activity_value * factor.value
        
        return [{
            'factor': factor,
            'activity_value': activity_value, 
            'emission_value': emission_value,
            'proportion': Decimal('1.0'),
            'metadata': {
                'metric_type': metric.__class__.__name__,
                'calculation_type': 'direct'
            }
        }]
    
    def _get_unit(self, metric):
        """Extract the appropriate unit from a metric"""
        if hasattr(metric, 'unit_type'):
            if metric.unit_type == 'custom' and metric.custom_unit:
                return metric.custom_unit
            return metric.unit_type
        return 'count'  # Default fallback


class TimeSeriesCalculationStrategy(EmissionCalculationStrategy):
    """Strategy for time series metrics"""
    
    def calculate(self, rpv, metric, year, region):
        """Calculate emissions for time series metrics"""
        # Time series metrics use the same basic calculation approach as BasicMetric
        basic_strategy = BasicMetricCalculationStrategy()
        results = basic_strategy.calculate(rpv, metric, year, region)
        
        # Add time series specific metadata if we have results
        if results:
            results[0]['metadata'].update({
                'metric_type': 'TimeSeriesMetric',
                'frequency': metric.frequency,
                'aggregation_method': metric.aggregation_method
            })
            
        return results


class VehicleTrackingCalculationStrategy(EmissionCalculationStrategy):
    """Strategy for vehicle metrics with multiple vehicle types and fuels"""
    
    def calculate(self, rpv, metric, year, region):
        """Calculate emissions for vehicle tracking metrics"""
        # logger.info(f"[STRATEGY-Vehicle] Calculating emissions for RPV {rpv.pk}, Metric {metric.pk}") # Log strategy start
        from ..services.emissions import find_matching_emission_factor
        
        # Parse vehicle data from the aggregated text value
        try:
            vehicle_data = self._parse_vehicle_data(rpv.aggregated_text_value)
            if not vehicle_data:
                print(f"[STRATEGY-Vehicle][WARNING] RPV {rpv.pk}: Couldn't parse vehicle data from aggregated_text_value: {rpv.aggregated_text_value}")
                return []
                
            vehicles = vehicle_data.get('vehicles', [])
            if not vehicles:
                print(f"[STRATEGY-Vehicle][WARNING] RPV {rpv.pk}: No 'vehicles' key found in parsed data: {vehicle_data}")
                return []
            # logger.info(f"[STRATEGY-Vehicle] RPV {rpv.pk}: Parsed {len(vehicles)} vehicles from aggregated text.")
        except Exception as e:
            print(f"[STRATEGY-Vehicle][ERROR] RPV {rpv.pk}: Error parsing vehicle data: {e}")
            return []
            
        # Process each vehicle
        results = []
        total_fuel = Decimal('0')
        
        # First pass - calculate total fuel for proportion calculation
        # logger.info(f"[STRATEGY-Vehicle] RPV {rpv.pk}: Calculating total fuel...")
        for idx, vehicle in enumerate(vehicles):
            try:
                # Make sure we're checking for valid data using the new field names
                if not vehicle.get('vehicle_type_value') or not vehicle.get('fuel_type_value'):
                    print(f"[STRATEGY-Vehicle][WARNING] RPV {rpv.pk}: Skipping vehicle {idx} in first pass due to missing vehicle_type_value or fuel_type_value")
                    continue
                    
                fuel_consumed = Decimal(str(vehicle.get('fuel_consumed', 0)))
                # logger.debug(f"[STRATEGY-Vehicle] RPV {rpv.pk}: Vehicle {idx} fuel: {fuel_consumed}")
                total_fuel += fuel_consumed
            except (ValueError, TypeError) as e:
                print(f"[STRATEGY-Vehicle][WARNING] RPV {rpv.pk}: Invalid fuel value for vehicle {idx}: {vehicle.get('fuel_consumed')}. Error: {e}")
                continue
            
        # logger.info(f"[STRATEGY-Vehicle] RPV {rpv.pk}: Calculated total_fuel = {total_fuel}")
            
        # No fuel consumed - nothing to calculate
        if total_fuel <= 0:
            print(f"[STRATEGY-Vehicle][WARNING] RPV {rpv.pk}: Total fuel is zero or negative. No emissions will be calculated.")
            return []
            
        # Second pass - calculate emissions for each vehicle
        # logger.info(f"[STRATEGY-Vehicle] RPV {rpv.pk}: Calculating emissions per vehicle...")
        for idx, vehicle in enumerate(vehicles):
            try:
                # Use the new field names that include _value suffix
                vehicle_type = vehicle.get('vehicle_type_value')
                fuel_type = vehicle.get('fuel_type_value')
                vehicle_label = vehicle.get('vehicle_type_label', 'Unknown')
                fuel_label = vehicle.get('fuel_type_label', 'Unknown')
                
                fuel_consumed = Decimal(str(vehicle.get('fuel_consumed', 0)))
                kilometers = Decimal(str(vehicle.get('kilometers', 0)))
                registration = vehicle.get('registration', 'N/A')
                
                # logger.debug(f"[STRATEGY-Vehicle] RPV {rpv.pk}: Processing Vehicle {idx}: Type={vehicle_type}, Fuel={fuel_type}, Consumed={fuel_consumed}, Reg={registration}")
                
                if not fuel_consumed or not vehicle_type or not fuel_type:
                    logger.warning(f"[STRATEGY-Vehicle] RPV {rpv.pk}: Skipping vehicle {idx} due to missing type/fuel/consumption: {vehicle}")
                    continue
                    
                # Get appropriate subcategory using metric's mapping
                emission_sub_category = metric.get_emission_subcategory(vehicle_type, fuel_type)
                # logger.debug(f"[STRATEGY-Vehicle] RPV {rpv.pk}: Derived subcategory for Vehicle {idx}: '{emission_sub_category}'")
                
                # Find matching factor
                factor = find_matching_emission_factor(
                    year=year,
                    category="transport", # Hardcoded category for VehicleTrackingMetric
                    sub_category=emission_sub_category,
                    activity_unit="liters", # Hardcoded activity unit
                    region=region
                )
                
                if not factor:
                    logger.warning(f"[STRATEGY-Vehicle] RPV {rpv.pk}: No emission factor found for Vehicle {idx} (Type={vehicle_type}, Fuel={fuel_type}, SubCat={emission_sub_category}, Year={year}, Region={region}) - Skipping vehicle.")
                    continue
                
                # logger.info(f"[STRATEGY-Vehicle] RPV {rpv.pk}: Found factor for Vehicle {idx}: ID={factor.pk}, Value={factor.value}")
                    
                # Calculate emissions
                emission_value = fuel_consumed * factor.value
                # Ensure proportion calculation doesn't divide by zero (though checked earlier)
                proportion = fuel_consumed / total_fuel if total_fuel > 0 else Decimal('0') 
                
                # We now get labels directly from the data rather than looking them up
                # logger.debug(f"[STRATEGY-Vehicle] RPV {rpv.pk}: Vehicle {idx} calculated emission: {emission_value}, proportion: {proportion}")
                
                # Add to results
                results.append({
                    'factor': factor,
                    'activity_value': fuel_consumed,
                    'emission_value': emission_value,
                    'proportion': proportion,
                    'metadata': {
                        # 'vehicle_id': vehicle.get('id'), # ID might not be in aggregated data
                        'vehicle_type': vehicle_type,
                        'vehicle_label': vehicle_label,
                        'fuel_type': fuel_type,
                        'fuel_label': fuel_label,
                        'distance': float(kilometers), # Store original KM
                        'registration': registration
                    }
                })
            except Exception as e:
                logger.error(f"[STRATEGY-Vehicle] RPV {rpv.pk}: Error processing vehicle {idx}: {e}", exc_info=True)
                continue
                
        # logger.info(f"[STRATEGY-Vehicle] RPV {rpv.pk}: Finished processing vehicles. Returning {len(results)} calculation results.")
        return results
    
    def _parse_vehicle_data(self, text_value):
        """Parse vehicle data from aggregated_text_value"""
        if not text_value:
            return None
            
        # If it's already a dict, just return it
        if isinstance(text_value, dict):
            return text_value
            
        # Try to parse JSON string
        try:
            return json.loads(text_value)
        except (json.JSONDecodeError, TypeError):
            # Not valid JSON
            return None
    
    def _get_vehicle_label(self, vehicle_type, metric):
        """Get human-readable vehicle type label from code"""
        if not vehicle_type:
            return "Unknown"
            
        # First try to find a VehicleType object
        try:
            from ..models.polymorphic_metrics import VehicleType
            vehicle_type_obj = VehicleType.objects.filter(value=vehicle_type).first()
            if vehicle_type_obj:
                return vehicle_type_obj.label
        except Exception:
            # If there's an error, fall back to the JSONField approach
            pass
            
        # Fall back to the old JSONField approach
        for vt in metric.vehicle_type_choices:
            if isinstance(vt, dict) and vt.get('value') == vehicle_type:
                return vt.get('label', vehicle_type)
                
        return vehicle_type
        
    def _get_fuel_label(self, fuel_type, metric):
        """Get human-readable fuel type label from code"""
        if not fuel_type:
            return "Unknown"
            
        # First try to find a FuelType object
        try:
            from ..models.polymorphic_metrics import FuelType
            fuel_type_obj = FuelType.objects.filter(value=fuel_type).first()
            if fuel_type_obj:
                return fuel_type_obj.label
        except Exception:
            # If there's an error, fall back to the JSONField approach
            pass
            
        # Fall back to the old JSONField approach
        for ft in metric.fuel_type_choices:
            if isinstance(ft, dict) and ft.get('value') == fuel_type:
                return ft.get('label', fuel_type)
                
        return fuel_type


class FuelConsumptionCalculationStrategy(EmissionCalculationStrategy):
    """Strategy for fuel consumption metrics with multiple sources and fuel types"""
    
    def calculate(self, rpv, metric, year, region):
        """Calculate emissions for fuel consumption metrics"""
        # logger.info(f"[STRATEGY-Fuel] Calculating emissions for RPV {rpv.pk}, Metric {metric.pk}")
        from ..services.emissions import find_matching_emission_factor
        
        # Parse fuel consumption data from the aggregated text value
        try:
            fuel_data = self._parse_fuel_data(rpv.aggregated_text_value)
            if not fuel_data:
                print(f"[STRATEGY-Fuel][WARNING] RPV {rpv.pk}: Couldn't parse fuel data from aggregated_text_value: {rpv.aggregated_text_value}")
                return []
                
            sources = fuel_data.get('sources', [])
            if not sources:
                print(f"[STRATEGY-Fuel][WARNING] RPV {rpv.pk}: No 'sources' key found in parsed data: {fuel_data}")
                return []
            # logger.info(f"[STRATEGY-Fuel] RPV {rpv.pk}: Parsed {len(sources)} sources from aggregated text.")
        except Exception as e:
            print(f"[STRATEGY-Fuel][ERROR] RPV {rpv.pk}: Error parsing fuel data: {e}")
            return []
            
        # Process each source
        results = []
        total_consumption = Decimal('0')
        
        # First pass - calculate total consumption for proportion calculation
        # logger.info(f"[STRATEGY-Fuel] RPV {rpv.pk}: Calculating total consumption...")
        for idx, source in enumerate(sources):
            try:
                # Make sure we're checking for valid data
                if not source.get('source_type_value') or not source.get('fuel_type_value'):
                    print(f"[STRATEGY-Fuel][WARNING] RPV {rpv.pk}: Skipping source {idx} in first pass due to missing source_type_value or fuel_type_value")
                    continue
                    
                consumption = Decimal(str(source.get('consumption', 0)))
                # logger.debug(f"[STRATEGY-Fuel] RPV {rpv.pk}: Source {idx} consumption: {consumption}")
                total_consumption += consumption
            except (ValueError, TypeError) as e:
                print(f"[STRATEGY-Fuel][WARNING] RPV {rpv.pk}: Invalid consumption value for source {idx}: {source.get('consumption')}. Error: {e}")
                continue
            
        # logger.info(f"[STRATEGY-Fuel] RPV {rpv.pk}: Calculated total_consumption = {total_consumption}")
            
        # No fuel consumed - nothing to calculate
        if total_consumption <= 0:
            print(f"[STRATEGY-Fuel][WARNING] RPV {rpv.pk}: Total consumption is zero or negative. No emissions will be calculated.")
            return []
            
        # Second pass - calculate emissions for each source
        # logger.info(f"[STRATEGY-Fuel] RPV {rpv.pk}: Calculating emissions per source...")
        for idx, source in enumerate(sources):
            try:
                # Use the field names with _value suffix
                source_type = source.get('source_type_value')
                fuel_type = source.get('fuel_type_value')
                source_type_label = source.get('source_type_label', 'Unknown')
                fuel_type_label = source.get('fuel_type_label', 'Unknown')
                
                consumption = Decimal(str(source.get('consumption', 0)))
                source_name = source.get('source_name', 'Unknown Source')
                fuel_record_id = source.get('id')
                
                # logger.debug(f"[STRATEGY-Fuel] RPV {rpv.pk}: Processing Source {idx}: Type={source_type}, Fuel={fuel_type}, Consumption={consumption}, Name={source_name}")
                
                if not consumption or not source_type or not fuel_type:
                    logger.warning(f"[STRATEGY-Fuel] RPV {rpv.pk}: Skipping source {idx} due to missing type/fuel/consumption: {source}")
                    continue
                    
                # Get appropriate subcategory using metric's mapping - only needs fuel type for FuelConsumptionMetric
                emission_sub_category = metric.get_emission_subcategory(fuel_type)
                # logger.debug(f"[STRATEGY-Fuel] RPV {rpv.pk}: Derived subcategory for Source {idx}: '{emission_sub_category}'")
                
                # Find matching factor - use stationary_combustion as the category
                factor = find_matching_emission_factor(
                    year=year,
                    category="stationary_combustion", # Use the category set in FuelConsumptionMetric
                    sub_category=emission_sub_category,
                    activity_unit=None, # Let the factor lookup handle unit conversion
                    region=region
                )
                
                if not factor:
                    logger.warning(f"[STRATEGY-Fuel] RPV {rpv.pk}: No emission factor found for Source {idx} (Type={source_type}, Fuel={fuel_type}, SubCat={emission_sub_category}, Year={year}, Region={region}) - Skipping source.")
                    continue
                
                # logger.info(f"[STRATEGY-Fuel] RPV {rpv.pk}: Found factor for Source {idx}: ID={factor.pk}, Value={factor.value}")
                    
                # Calculate emissions
                emission_value = consumption * factor.value
                # Ensure proportion calculation doesn't divide by zero (though checked earlier)
                proportion = consumption / total_consumption if total_consumption > 0 else Decimal('0') 
                
                # logger.debug(f"[STRATEGY-Fuel] RPV {rpv.pk}: Source {idx} calculated emission: {emission_value}, proportion: {proportion}")
                
                # Add to results
                results.append({
                    'factor': factor,
                    'activity_value': consumption,
                    'emission_value': emission_value,
                    'proportion': proportion,
                    'metadata': {
                        'fuel_record_id': fuel_record_id,
                        'source_type': source_type,
                        'source_type_label': source_type_label,
                        'fuel_type': fuel_type,
                        'fuel_type_label': fuel_type_label,
                        'source_name': source_name,
                        'notes': source.get('notes', '')
                    }
                })
            except Exception as e:
                logger.error(f"[STRATEGY-Fuel] RPV {rpv.pk}: Error processing source {idx}: {e}", exc_info=True)
                continue
                
        # logger.info(f"[STRATEGY-Fuel] RPV {rpv.pk}: Finished processing sources. Returning {len(results)} calculation results.")
        return results
    
    def _parse_fuel_data(self, text_value):
        """Parse fuel data from aggregated_text_value"""
        if not text_value:
            return None
            
        # If it's already a dict, just return it
        if isinstance(text_value, dict):
            return text_value
            
        # Try to parse JSON string
        try:
            return json.loads(text_value)
        except (json.JSONDecodeError, TypeError):
            # Not valid JSON
            return None


# Registry of strategies keyed by metric class name
strategy_registry = {
    'BasicMetric': BasicMetricCalculationStrategy(),
    'TimeSeriesMetric': TimeSeriesCalculationStrategy(),
    'VehicleTrackingMetric': VehicleTrackingCalculationStrategy(),
    'FuelConsumptionMetric': FuelConsumptionCalculationStrategy(), # Add the new strategy
}

def get_strategy_for_metric(metric):
    """
    Get the appropriate calculation strategy for a metric.
    
    Args:
        metric: A BaseESGMetric instance
        
    Returns:
        An EmissionCalculationStrategy instance
    """
    metric_class = metric.__class__.__name__
    
    # Try to get a specialized strategy
    strategy = strategy_registry.get(metric_class)
    
    # Fall back to basic strategy if no specialized one exists
    if not strategy:
        logger.debug(f"No specialized strategy for {metric_class}, using BasicMetricCalculationStrategy")
        strategy = BasicMetricCalculationStrategy()
        
    return strategy 