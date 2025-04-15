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
        logger.info(f"[STRATEGY-Vehicle] Calculating emissions for RPV {rpv.pk}, Metric {metric.pk}") # Log strategy start
        from ..services.emissions import find_matching_emission_factor
        
        # Parse vehicle data from the aggregated text value
        try:
            vehicle_data = self._parse_vehicle_data(rpv.aggregated_text_value)
            if not vehicle_data:
                logger.warning(f"[STRATEGY-Vehicle] RPV {rpv.pk}: Couldn't parse vehicle data from aggregated_text_value: {rpv.aggregated_text_value}")
                return []
                
            vehicles = vehicle_data.get('vehicles', [])
            if not vehicles:
                logger.warning(f"[STRATEGY-Vehicle] RPV {rpv.pk}: No 'vehicles' key found in parsed data: {vehicle_data}")
                return []
            logger.info(f"[STRATEGY-Vehicle] RPV {rpv.pk}: Parsed {len(vehicles)} vehicles from aggregated text.")
        except Exception as e:
            logger.error(f"[STRATEGY-Vehicle] RPV {rpv.pk}: Error parsing vehicle data: {e}", exc_info=True)
            return []
            
        # Process each vehicle
        results = []
        total_fuel = Decimal('0')
        
        # First pass - calculate total fuel for proportion calculation
        logger.info(f"[STRATEGY-Vehicle] RPV {rpv.pk}: Calculating total fuel...")
        for idx, vehicle in enumerate(vehicles):
            try:
                fuel_consumed = Decimal(str(vehicle.get('fuel_consumed', 0)))
                logger.debug(f"[STRATEGY-Vehicle] RPV {rpv.pk}: Vehicle {idx} fuel: {fuel_consumed}")
                total_fuel += fuel_consumed
            except (ValueError, TypeError) as e:
                logger.warning(f"[STRATEGY-Vehicle] RPV {rpv.pk}: Invalid fuel value for vehicle {idx}: {vehicle.get('fuel_consumed')}. Error: {e}")
                continue
            
        logger.info(f"[STRATEGY-Vehicle] RPV {rpv.pk}: Calculated total_fuel = {total_fuel}")
            
        # No fuel consumed - nothing to calculate
        if total_fuel <= 0:
            logger.warning(f"[STRATEGY-Vehicle] RPV {rpv.pk}: Total fuel is zero or negative. No emissions will be calculated.")
            return []
            
        # Second pass - calculate emissions for each vehicle
        logger.info(f"[STRATEGY-Vehicle] RPV {rpv.pk}: Calculating emissions per vehicle...")
        for idx, vehicle in enumerate(vehicles):
            try:
                vehicle_type = vehicle.get('vehicle_type')
                fuel_type = vehicle.get('fuel_type')
                fuel_consumed = Decimal(str(vehicle.get('fuel_consumed', 0)))
                kilometers = Decimal(str(vehicle.get('kilometers', 0)))
                registration = vehicle.get('registration', 'N/A')
                
                logger.debug(f"[STRATEGY-Vehicle] RPV {rpv.pk}: Processing Vehicle {idx}: Type={vehicle_type}, Fuel={fuel_type}, Consumed={fuel_consumed}, Reg={registration}")
                
                if not fuel_consumed or not vehicle_type or not fuel_type:
                    logger.warning(f"[STRATEGY-Vehicle] RPV {rpv.pk}: Skipping vehicle {idx} due to missing type/fuel/consumption: {vehicle}")
                    continue
                    
                # Get appropriate subcategory using metric's mapping
                emission_sub_category = metric.get_emission_subcategory(vehicle_type, fuel_type)
                logger.debug(f"[STRATEGY-Vehicle] RPV {rpv.pk}: Derived subcategory for Vehicle {idx}: '{emission_sub_category}'")
                
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
                
                logger.info(f"[STRATEGY-Vehicle] RPV {rpv.pk}: Found factor for Vehicle {idx}: ID={factor.pk}, Value={factor.value}")
                    
                # Calculate emissions
                emission_value = fuel_consumed * factor.value
                # Ensure proportion calculation doesn't divide by zero (though checked earlier)
                proportion = fuel_consumed / total_fuel if total_fuel > 0 else Decimal('0') 
                
                # Get display labels
                vehicle_label = self._get_vehicle_label(vehicle_type, metric)
                fuel_label = self._get_fuel_label(fuel_type, metric)
                
                logger.debug(f"[STRATEGY-Vehicle] RPV {rpv.pk}: Vehicle {idx} calculated emission: {emission_value}, proportion: {proportion}")
                
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
                
        logger.info(f"[STRATEGY-Vehicle] RPV {rpv.pk}: Finished processing vehicles. Returning {len(results)} calculation results.")
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


# Registry of strategies keyed by metric class name
strategy_registry = {
    'BasicMetric': BasicMetricCalculationStrategy(),
    'TimeSeriesMetric': TimeSeriesCalculationStrategy(),
    'VehicleTrackingMetric': VehicleTrackingCalculationStrategy(),
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