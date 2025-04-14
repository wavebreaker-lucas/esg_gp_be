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
        from ..services.emissions import find_matching_emission_factor
        
        # Parse vehicle data from the aggregated text value
        try:
            vehicle_data = self._parse_vehicle_data(rpv.aggregated_text_value)
            if not vehicle_data:
                logger.warning(f"Couldn't parse vehicle data for RPV {rpv.pk}")
                return []
                
            vehicles = vehicle_data.get('vehicles', [])
            if not vehicles:
                logger.warning(f"No vehicles found in data for RPV {rpv.pk}")
                return []
        except Exception as e:
            logger.error(f"Error parsing vehicle data for RPV {rpv.pk}: {e}")
            return []
            
        # Process each vehicle
        results = []
        total_fuel = Decimal('0')
        
        # First pass - calculate total fuel for proportion calculation
        for vehicle in vehicles:
            try:
                fuel_consumed = Decimal(str(vehicle.get('fuel_consumed', 0)))
                total_fuel += fuel_consumed
            except (ValueError, TypeError):
                # Skip invalid fuel values
                continue
            
        # No fuel consumed - nothing to calculate
        if total_fuel <= 0:
            logger.warning(f"No valid fuel consumption found for RPV {rpv.pk}")
            return []
            
        # Second pass - calculate emissions for each vehicle
        for vehicle in vehicles:
            try:
                vehicle_type = vehicle.get('vehicle_type')
                fuel_type = vehicle.get('fuel_type')
                fuel_consumed = Decimal(str(vehicle.get('fuel_consumed', 0)))
                
                if not fuel_consumed or not vehicle_type or not fuel_type:
                    continue
                    
                # Get appropriate subcategory using metric's mapping
                emission_sub_category = metric.get_emission_subcategory(vehicle_type, fuel_type)
                
                # Find matching factor
                factor = find_matching_emission_factor(
                    year=year,
                    category="transport",
                    sub_category=emission_sub_category,
                    activity_unit="liters",
                    region=region
                )
                
                if not factor:
                    logger.warning(f"No emission factor found for vehicle type={vehicle_type}, fuel={fuel_type}, sub_category={emission_sub_category}")
                    continue
                    
                # Calculate emissions
                emission_value = fuel_consumed * factor.value
                proportion = fuel_consumed / total_fuel
                
                # Get display labels
                vehicle_label = self._get_vehicle_label(vehicle_type, metric)
                fuel_label = self._get_fuel_label(fuel_type, metric)
                
                # Add to results
                results.append({
                    'factor': factor,
                    'activity_value': fuel_consumed,
                    'emission_value': emission_value,
                    'proportion': proportion,
                    'metadata': {
                        'vehicle_id': vehicle.get('id'),
                        'vehicle_type': vehicle_type,
                        'vehicle_label': vehicle_label,
                        'fuel_type': fuel_type,
                        'fuel_label': fuel_label,
                        'distance': vehicle.get('kilometers', 0),
                        'registration': vehicle.get('registration', '')
                    }
                })
            except Exception as e:
                logger.error(f"Error processing vehicle: {e}")
                continue
                
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
            
        for vt in metric.vehicle_type_choices:
            if isinstance(vt, dict) and vt.get('value') == vehicle_type:
                return vt.get('label', vehicle_type)
        return vehicle_type
        
    def _get_fuel_label(self, fuel_type, metric):
        """Get human-readable fuel type label from code"""
        if not fuel_type:
            return "Unknown"
            
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