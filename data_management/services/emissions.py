"""
Service functions for calculating greenhouse gas (GHG) emissions.

This module implements the calculation logic for converting activity data into emissions
values using appropriate emission factors.
"""

import logging
import datetime
from decimal import Decimal
from typing import Optional, List, Dict, Tuple, Union
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from ..models.templates import ReportedMetricValue
from ..models.factors import GHGEmissionFactor
from ..models.results import CalculatedEmissionValue
from ..models.polymorphic_metrics import BaseESGMetric

logger = logging.getLogger(__name__)

def find_matching_emission_factor(
    year: int,
    category: str,
    sub_category: str,
    activity_unit: str,
    region: str,
    scope: str = None
) -> Optional[GHGEmissionFactor]:
    """
    Find the most appropriate emission factor for the given parameters with fallback logic.
    
    Args:
        year: The reporting year
        category: The emission category from metric configuration
        sub_category: The emission sub-category from metric configuration
        activity_unit: The unit of the activity data
        region: The region code from the metric's location field
        scope: Optional scope specification (Scope 1, 2, or 3)
        
    Returns:
        The best matching GHGEmissionFactor or None if no match found
    """
    # Start with exact match query including region
    query = Q(
        year=year,
        category=category,
        sub_category=sub_category,
        activity_unit=activity_unit
    )
    
    # Add scope filter if provided
    if scope:
        query &= Q(scope=scope)
    
    # Try exact region match first
    region_query = query & Q(region=region)
    factor = GHGEmissionFactor.objects.filter(region_query).first()
    if factor:
        logger.debug(f"Found exact region match for {category}/{sub_category} in {region}")
        return factor
    
    # Try region fallback: "HK / PRC" for either "HK" or "PRC"
    if region in ['HK', 'PRC']:
        combined_region_query = query & Q(region='HK / PRC')
        factor = GHGEmissionFactor.objects.filter(combined_region_query).first()
        if factor:
            logger.debug(f"Found combined region match 'HK / PRC' for {category}/{sub_category}")
            return factor
    
    # Try universal region ("ALL") 
    universal_region_query = query & (Q(region='ALL') | Q(region='') | Q(region__isnull=True))
    factor = GHGEmissionFactor.objects.filter(universal_region_query).first()
    if factor:
        logger.debug(f"Found universal region match for {category}/{sub_category}")
        return factor
    
    # Try year fallback - get the closest earlier year with a matching factor
    # First try with the specific region
    earlier_year_query = Q(
        category=category,
        sub_category=sub_category,
        activity_unit=activity_unit,
        region=region,
        year__lt=year
    )
    if scope:
        earlier_year_query &= Q(scope=scope)
    
    earlier_factor = GHGEmissionFactor.objects.filter(earlier_year_query).order_by('-year').first()
    if earlier_factor:
        logger.debug(f"Found earlier year ({earlier_factor.year}) match for {category}/{sub_category} in {region}")
        return earlier_factor
    
    # Finally, try universal region with earlier year
    universal_earlier_query = Q(
        category=category,
        sub_category=sub_category,
        activity_unit=activity_unit,
        year__lt=year
    ) & (Q(region='ALL') | Q(region='') | Q(region__isnull=True))
    
    if scope:
        universal_earlier_query &= Q(scope=scope)
    
    universal_earlier_factor = GHGEmissionFactor.objects.filter(universal_earlier_query).order_by('-year').first()
    if universal_earlier_factor:
        logger.debug(f"Found universal earlier year ({universal_earlier_factor.year}) match for {category}/{sub_category}")
        return universal_earlier_factor
    
    # No match found after all fallbacks
    logger.warning(f"No emission factor found for {category}/{sub_category}, {activity_unit}, {region}, {year}")
    return None

def convert_unit_if_needed(value: Decimal, source_unit: str, target_unit: str) -> Tuple[Decimal, bool]:
    """
    Convert values between compatible units if needed.
    
    Args:
        value: The numeric value to convert
        source_unit: The source unit (from activity data)
        target_unit: The unit expected by the factor
        
    Returns:
        (Converted value, was_converted flag)
    """
    # This is a simplified version - would need a comprehensive unit conversion system
    
    # If units already match, no conversion needed
    if source_unit.lower() == target_unit.lower():
        return value, False
    
    # Handle common volume unit conversions
    if source_unit.lower() == 'liters' and target_unit.lower() == 'l':
        return value, False  # Alias, no conversion needed
    
    if source_unit.lower() == 'l' and target_unit.lower() == 'liters':
        return value, False  # Alias, no conversion needed
    
    # Handle common mass unit conversions
    if source_unit.lower() == 'tonnes' and target_unit.lower() == 't':
        return value, False  # Alias, no conversion needed
    
    if source_unit.lower() == 'kg' and target_unit.lower() == 't':
        return value / Decimal(1000), True
        
    if source_unit.lower() == 't' and target_unit.lower() == 'kg':
        return value * Decimal(1000), True
    
    # Handle volume conversions
    if source_unit.lower() == 'm3' and target_unit.lower() == 'liters':
        return value * Decimal(1000), True
        
    if source_unit.lower() == 'liters' and target_unit.lower() == 'm3':
        return value / Decimal(1000), True
    
    # Handle energy unit conversions
    if source_unit.lower() == 'kwh' and target_unit.lower() == 'mwh':
        return value / Decimal(1000), True
        
    if source_unit.lower() == 'mwh' and target_unit.lower() == 'kwh':
        return value * Decimal(1000), True
    
    # If we reach this point, we don't know how to convert
    logger.warning(f"Don't know how to convert {source_unit} to {target_unit}")
    return value, False

@transaction.atomic
def calculate_emissions_for_activity_value(rpv: ReportedMetricValue) -> Optional[CalculatedEmissionValue]:
    """
    Calculate emissions for a single ReportedMetricValue record.
    
    Args:
        rpv: The ReportedMetricValue instance containing the activity data
        
    Returns:
        The created/updated CalculatedEmissionValue or None if calculation couldn't be performed
    """
    metric = rpv.metric
    
    # Skip if metric doesn't have emission category configured
    if not metric.emission_category or not metric.emission_sub_category:
        logger.debug(f"Skipping emissions calculation for metric {metric.pk} - missing category configuration")
        return None
    
    # Skip if no activity value is present
    if rpv.aggregated_numeric_value is None:
        logger.debug(f"Skipping emissions calculation for RPV {rpv.pk} - no numeric value")
        return None
    
    # Get activity unit from the metric
    specific_metric = metric.get_real_instance()
    
    # Extract unit based on metric type
    from ..models.polymorphic_metrics import BasicMetric, TimeSeriesMetric
    
    if isinstance(specific_metric, (BasicMetric, TimeSeriesMetric)):
        if specific_metric.unit_type == 'custom' and specific_metric.custom_unit:
            activity_unit = specific_metric.custom_unit
        else:
            activity_unit = specific_metric.unit_type
    else:
        # For other metric types, might need custom handling
        activity_unit = 'count'  # Default fallback
    
    # Get the year from the reporting period
    year = rpv.reporting_period.year
    
    # Get region from the metric's location field
    region = metric.location
    
    # Determine scope based on emission category (simple logic, expand as needed)
    scope = None
    if metric.emission_category.lower() == 'electricity':
        scope = '2'
    elif metric.emission_category.lower() in ['transport', 'refrigerants', 'fuel']:
        scope = '1'
    elif metric.emission_category.lower() in ['water', 'waste', 'travel']:
        scope = '3'
    
    # Find matching emission factor
    factor = find_matching_emission_factor(
        year=year,
        category=metric.emission_category,
        sub_category=metric.emission_sub_category,
        activity_unit=activity_unit,
        region=region,
        scope=scope
    )
    
    if not factor:
        logger.warning(f"No suitable emission factor found for RPV {rpv.pk}")
        return None
    
    # Extract activity value
    activity_value = Decimal(str(rpv.aggregated_numeric_value))
    
    # Check if unit conversion is needed
    factor_unit_parts = factor.factor_unit.split('/')
    if len(factor_unit_parts) > 1:
        expected_activity_unit = factor_unit_parts[1]
    else:
        expected_activity_unit = activity_unit  # Default to same unit if factor format is unclear
    
    # Convert the value if needed
    converted_value, was_converted = convert_unit_if_needed(
        value=activity_value,
        source_unit=activity_unit,
        target_unit=expected_activity_unit
    )
    
    if was_converted:
        logger.info(f"Converted activity value from {activity_value} {activity_unit} to {converted_value} {expected_activity_unit}")
    
    # Calculate the emission value
    emission_value = converted_value * factor.value
    
    # Extract emission unit from factor
    emission_unit = factor.get_emission_unit()
    
    # Create or update the result
    emission_result, created = CalculatedEmissionValue.objects.update_or_create(
        source_activity_value=rpv,
        emission_factor=factor,
        defaults={
            'calculated_value': emission_value,
            'emission_unit': emission_unit,
            # The save method of CalculatedEmissionValue will handle additional context
        }
    )
    
    action = "Created" if created else "Updated"
    logger.info(f"{action} emission calculation: {emission_value} {emission_unit} for RPV {rpv.pk}")
    
    return emission_result

def calculate_emissions_for_assignment(assignment_id: int) -> Dict:
    """
    Calculate emissions for all relevant metrics in a specific assignment.
    
    Args:
        assignment_id: The ID of the TemplateAssignment to process
        
    Returns:
        Dictionary with summary statistics of calculations performed
    """
    logger.info(f"Starting emissions calculations for assignment {assignment_id}")
    
    # Find all ReportedMetricValue records for the assignment that have relevant metrics
    rpvs = ReportedMetricValue.objects.filter(
        assignment_id=assignment_id,
        metric__emission_category__isnull=False,
        metric__emission_sub_category__isnull=False,
        aggregated_numeric_value__isnull=False
    )
    
    stats = {
        'total_processed': 0,
        'successful_calculations': 0,
        'failed_calculations': 0,
    }
    
    for rpv in rpvs:
        stats['total_processed'] += 1
        try:
            result = calculate_emissions_for_activity_value(rpv)
            if result:
                stats['successful_calculations'] += 1
            else:
                stats['failed_calculations'] += 1
        except Exception as e:
            logger.error(f"Error calculating emissions for RPV {rpv.pk}: {e}", exc_info=True)
            stats['failed_calculations'] += 1
    
    logger.info(f"Completed emissions calculations for assignment {assignment_id}. Stats: {stats}")
    return stats

def recalculate_all_emissions() -> Dict:
    """
    Recalculate emissions for all eligible activity values.
    Typically triggered by scheduled task or admin action.
    
    Returns:
        Dictionary with summary statistics
    """
    logger.info("Starting complete emissions recalculation")
    
    # Find all ReportedMetricValue records with emission category/sub-category
    rpvs = ReportedMetricValue.objects.filter(
        metric__emission_category__isnull=False,
        metric__emission_sub_category__isnull=False,
        aggregated_numeric_value__isnull=False
    )
    
    stats = {
        'total_processed': 0,
        'successful_calculations': 0,
        'failed_calculations': 0,
    }
    
    for rpv in rpvs:
        stats['total_processed'] += 1
        try:
            result = calculate_emissions_for_activity_value(rpv)
            if result:
                stats['successful_calculations'] += 1
            else:
                stats['failed_calculations'] += 1
        except Exception as e:
            logger.error(f"Error calculating emissions for RPV {rpv.pk}: {e}", exc_info=True)
            stats['failed_calculations'] += 1
    
    # Clean up orphaned calculations (no longer have valid source RPVs)
    orphaned_count = CalculatedEmissionValue.objects.filter(
        ~Q(source_activity_value__in=rpvs)
    ).delete()[0]
    
    stats['orphaned_calculations_deleted'] = orphaned_count
    
    logger.info(f"Completed emissions recalculation. Stats: {stats}")
    return stats 