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
import uuid

from ..models.templates import ReportedMetricValue
from ..models.factors import GHGEmissionFactor
from ..models.results import CalculatedEmissionValue
from ..models.polymorphic_metrics import BaseESGMetric
from ..services.calculation_strategies import get_strategy_for_metric

logger = logging.getLogger(__name__)

def find_matching_emission_factor(
    year: int,
    category: str,
    sub_category: str,
    activity_unit: str = None,
    region: str = None,
    scope: str = None
) -> Optional[GHGEmissionFactor]:
    """
    Find the most appropriate emission factor for the given parameters with fallback logic.
    
    Args:
        year: The reporting year
        category: The emission category from metric configuration
        sub_category: The emission sub-category from metric configuration
        activity_unit: Optional unit of the activity data (used as secondary matching criterion)
        region: Optional region code from the metric's location field
        scope: Optional scope specification (Scope 1, 2, or 3) - not used in automatic lookup
        
    Returns:
        The best matching GHGEmissionFactor or None if no match found
    """
    # Start with the base category/subcategory match
    query = Q(
        year=year,
        category=category,
        sub_category=sub_category
    )
    
    # Add additional filters if provided
    if activity_unit:
        activity_unit_query = query & Q(activity_unit=activity_unit)
    else:
        activity_unit_query = query
        
    if scope:
        activity_unit_query &= Q(scope=scope)
    
    # Try exact region match first (with unit if specified)
    if region:
        region_query = activity_unit_query & Q(region=region)
        factor = GHGEmissionFactor.objects.filter(region_query).first()
        if factor:
            logger.debug(f"Found exact region match for {category}/{sub_category} in {region}")
            return factor
        
        # Try region fallback: "HK / PRC" for either "HK" or "PRC"
        if region in ['HK', 'PRC']:
            combined_region_query = activity_unit_query & Q(region='HK / PRC')
            factor = GHGEmissionFactor.objects.filter(combined_region_query).first()
            if factor:
                logger.debug(f"Found combined region match 'HK / PRC' for {category}/{sub_category}")
                return factor
    
    # Try universal region ("ALL") 
    universal_region_query = activity_unit_query & (Q(region='ALL') | Q(region='') | Q(region__isnull=True))
    factor = GHGEmissionFactor.objects.filter(universal_region_query).first()
    if factor:
        logger.debug(f"Found universal region match for {category}/{sub_category}")
        return factor
    
    # If we got this far with a unit specified and didn't find a match, 
    # try again WITHOUT the unit constraint
    if activity_unit and activity_unit_query != query:
        logger.debug(f"Trying factor lookup without unit constraint for {category}/{sub_category}")
        return find_matching_emission_factor(
            year=year,
            category=category,
            sub_category=sub_category,
            activity_unit=None,
            region=region,
            scope=scope
        )
    
    # Try year fallback - get the closest earlier year
    # Only if we have a region specified
    if region:
        earlier_year_query = Q(
            category=category,
            sub_category=sub_category,
            year__lt=year,
            region=region
        )
        
        if activity_unit:
            earlier_year_query &= Q(activity_unit=activity_unit)
            
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
        year__lt=year
    ) & (Q(region='ALL') | Q(region='') | Q(region__isnull=True))
    
    if activity_unit:
        universal_earlier_query &= Q(activity_unit=activity_unit)
        
    if scope:
        universal_earlier_query &= Q(scope=scope)
    
    universal_earlier_factor = GHGEmissionFactor.objects.filter(universal_earlier_query).order_by('-year').first()
    if universal_earlier_factor:
        logger.debug(f"Found universal earlier year ({universal_earlier_factor.year}) match for {category}/{sub_category}")
        return universal_earlier_factor
    
    # Try earlier year without unit constraint as last resort
    if activity_unit:
        logger.debug(f"Trying earlier year lookup without unit constraint for {category}/{sub_category}")
        return find_matching_emission_factor(
            year=year,
            category=category,
            sub_category=sub_category,
            activity_unit=None,
            region=region,
            scope=scope
        )
    
    # No match found after all fallbacks
    logger.warning(f"No emission factor found for {category}/{sub_category}, region={region}, year={year}")
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
def calculate_emissions_for_activity_value(rpv: ReportedMetricValue) -> List[CalculatedEmissionValue]:
    """
    Calculate emissions for a single ReportedMetricValue record.
    
    Args:
        rpv: The ReportedMetricValue instance containing the activity data
        
    Returns:
        A list of created CalculatedEmissionValue objects or empty list if calculation couldn't be performed
    """
    logger.info(f"[EMISSIONS] Starting calculation for RPV {rpv.pk}") # Log function start
    from ..services.calculation_strategies import get_strategy_for_metric
    
    metric = rpv.metric
    
    # Skip if no activity value is present
    if rpv.aggregated_numeric_value is None:
        logger.info(f"[EMISSIONS] Skipping RPV {rpv.pk} - no numeric value")
        return []
    
    # Get the specific metric instance
    try:
        specific_metric = metric.get_real_instance()
        logger.info(f"[EMISSIONS] RPV {rpv.pk} has specific metric type: {specific_metric.__class__.__name__}")
    except Exception as e:
        logger.error(f"[EMISSIONS] Error getting specific metric for RPV {rpv.pk}: {e}", exc_info=True)
        return [] # Cannot proceed without specific metric
    
    # Check for category/subcategory unless it's VehicleTrackingMetric
    from ..models.polymorphic_metrics import VehicleTrackingMetric
    if not metric.emission_category and not isinstance(specific_metric, VehicleTrackingMetric):
        logger.info(f"[EMISSIONS] Skipping RPV {rpv.pk} (Metric {metric.pk}) - missing category config and not VehicleTrackingMetric")
        return []
    elif not metric.emission_category and isinstance(specific_metric, VehicleTrackingMetric):
        logger.info(f"[EMISSIONS] Proceeding for RPV {rpv.pk} (VehicleTrackingMetric) despite missing base emission_category")
    else:
        logger.info(f"[EMISSIONS] Proceeding for RPV {rpv.pk} - metric has emission_category: {metric.emission_category}")
    
    # Get the year and region
    year = rpv.reporting_period.year
    region = metric.location
    logger.info(f"[EMISSIONS] RPV {rpv.pk} - Year: {year}, Region: {region}")
    
    # Get the appropriate calculation strategy for this metric type
    try:
        strategy = get_strategy_for_metric(specific_metric)
        logger.info(f"[EMISSIONS] Using strategy: {strategy.__class__.__name__} for RPV {rpv.pk}")
    except Exception as e:
        logger.error(f"[EMISSIONS] Error getting strategy for RPV {rpv.pk}, Metric: {specific_metric.__class__.__name__}: {e}", exc_info=True)
        return []
    
    # Calculate emissions using the strategy
    calculation_results = [] # Initialize
    try:
        calculation_results = strategy.calculate(rpv, specific_metric, year, region)
        logger.info(f"[EMISSIONS] Strategy calculation returned {len(calculation_results)} results for RPV {rpv.pk}")
    except Exception as e:
        logger.error(f"[EMISSIONS] Error during strategy.calculate for RPV {rpv.pk}: {e}", exc_info=True)
        return [] # Don't proceed if strategy failed
    
    if not calculation_results:
        logger.info(f"[EMISSIONS] No calculation results produced by strategy for RPV {rpv.pk}. No CalculatedEmissionValue will be created.")
        # Clean up any existing calculations for this source? Maybe not here, strategy might have intended empty result.
        # CalculatedEmissionValue.objects.filter(source_activity_value=rpv).delete()
        return []
    
    # If we have multiple results, generate a group ID
    group_id = uuid.uuid4() if len(calculation_results) > 1 else None
    if group_id:
        logger.info(f"[EMISSIONS] Generated group_id {group_id} for {len(calculation_results)} results for RPV {rpv.pk}")
    
    # Clean up any existing calculations for this source
    deleted_count, _ = CalculatedEmissionValue.objects.filter(source_activity_value=rpv).delete()
    if deleted_count > 0:
        logger.info(f"[EMISSIONS] Deleted {deleted_count} existing CalculatedEmissionValue records for RPV {rpv.pk}")
    
    # Create new calculation records
    created_records = []
    primary_record = None # Initialize primary record
    
    # Create a record for each calculation result (as components initially)
    for calc in calculation_results:
        factor = calc.get('factor')
        emission_value = calc.get('emission_value')
        proportion = calc.get('proportion', Decimal('1.0'))
        metadata = calc.get('metadata', {})
        
        if not factor or emission_value is None:
             logger.warning(f"[EMISSIONS] Skipping result for RPV {rpv.pk} due to missing factor or emission_value in calculation data: {calc}")
             continue
        
        # Create the emission record - always as a component first if group_id exists
        record = CalculatedEmissionValue.objects.create(
            source_activity_value=rpv,
            emission_factor=factor,
            calculated_value=emission_value,
            # emission_unit is set automatically on save based on factor
            related_group_id=group_id,
            is_primary_record=False, # Initially False if part of a group
            proportion=proportion,
            calculation_metadata=metadata
            # Context fields (assignment, layer, reporting_period, level, scope) are set automatically on save
        )
        created_records.append(record)
        logger.debug(f"[EMISSIONS] Created component CalculatedEmissionValue ID {record.pk} for RPV {rpv.pk}")
    
    # If we had multiple components, create a primary record with the total
    if group_id and created_records: # Only if group_id exists and we actually created components
        # Calculate the total emissions from the successfully created components
        total_emission_value = sum(r.calculated_value for r in created_records)
        
        # Use the first factor for the primary record (or maybe find the most relevant?)
        primary_factor = created_records[0].emission_factor
        
        # Create the primary record
        primary_record = CalculatedEmissionValue.objects.create(
            source_activity_value=rpv,
            emission_factor=primary_factor,
            calculated_value=total_emission_value,
            related_group_id=group_id,
            is_primary_record=True,
            proportion=Decimal('1.0'),
            calculation_metadata={
                'is_composite': True,
                'component_count': len(created_records),
                'calculation_type': 'composite',
                'metric_type': specific_metric.__class__.__name__
            }
        )
        logger.info(f"[EMISSIONS] Created primary CalculatedEmissionValue ID {primary_record.pk} (Total: {total_emission_value}) for RPV {rpv.pk}")
        # Add the primary record to the beginning of the list for return consistency
        created_records.insert(0, primary_record)
    elif not group_id and created_records: # Single result, make it the primary
        single_record = created_records[0]
        single_record.is_primary_record = True
        single_record.save(update_fields=['is_primary_record'])
        logger.info(f"[EMISSIONS] Marked single CalculatedEmissionValue ID {single_record.pk} as primary for RPV {rpv.pk}")
        primary_record = single_record # Set primary_record for the final log message
        
    # Final logging based on whether a primary record was established
    if primary_record:
        record_count = len(created_records)
        logger.info(f"[EMISSIONS] Successfully created {record_count} emission calculation record(s) for RPV {rpv.pk}. Primary ID: {primary_record.pk}")
    else:
        # This case means no results or only invalid results were returned by the strategy
        logger.info(f"[EMISSIONS] No valid emission calculation records created for RPV {rpv.pk}.")
        
    return created_records # Return all created records (primary first if exists)

def calculate_emissions_for_assignment(
    assignment_id: int,
    year: int = None,
    month: int = None,
    period_date: datetime.date = None,
    level: str = None
) -> Dict:
    """
    Calculate emissions for all relevant metrics in a specific assignment.
    
    Args:
        assignment_id: The ID of the TemplateAssignment to process
        year: Optional year to filter by 
        month: Optional month to filter by (requires year)
        period_date: Optional exact reporting period date (takes precedence over year/month)
        level: Optional aggregation level ('M' for monthly, 'A' for annual)
        
    Returns:
        Dictionary with summary statistics of calculations performed
    """
    logger.info(f"Starting emissions calculations for assignment {assignment_id}")
    
    # Build base query
    query = Q(
        assignment_id=assignment_id,
        aggregated_numeric_value__isnull=False
    )
    
    # Apply period filters if specified
    if period_date:
        logger.info(f"Filtering by exact reporting period: {period_date}")
        query &= Q(reporting_period=period_date)
    elif year:
        logger.info(f"Filtering by year: {year}")
        query &= Q(reporting_period__year=year)
        if month:
            logger.info(f"Filtering by month: {month}")
            query &= Q(reporting_period__month=month)
            
    # Apply level filter if specified
    if level:
        logger.info(f"Filtering by aggregation level: {level}")
        query &= Q(level=level)
    
    # Execute the query
    rpvs = ReportedMetricValue.objects.filter(query)
    
    stats = {
        'total_processed': 0,
        'successful_calculations': 0,
        'failed_calculations': 0,
        'total_records_created': 0,
        'primary_records_created': 0,
        'component_records_created': 0,
    }
    
    for rpv in rpvs:
        stats['total_processed'] += 1
        try:
            results = calculate_emissions_for_activity_value(rpv)
            if results:
                stats['successful_calculations'] += 1
                stats['total_records_created'] += len(results)
                
                # Count primary vs component records
                primary_count = len([r for r in results if r.is_primary_record])
                stats['primary_records_created'] += primary_count
                stats['component_records_created'] += len(results) - primary_count
            else:
                stats['failed_calculations'] += 1
        except Exception as e:
            logger.error(f"Error calculating emissions for RPV {rpv.pk}: {e}", exc_info=True)
            stats['failed_calculations'] += 1
    
    log_msg = f"Completed emissions calculations for assignment {assignment_id}"
    if period_date:
        log_msg += f" for period {period_date}"
    elif year:
        log_msg += f" for year {year}"
        if month:
            log_msg += f" month {month}"
    if level:
        log_msg += f" level {level}"
    log_msg += f". Stats: {stats}"
    
    logger.info(log_msg)
    return stats

def recalculate_all_emissions() -> Dict:
    """
    Recalculate emissions for all eligible activity values.
    Typically triggered by scheduled task or admin action.
    
    Returns:
        Dictionary with summary statistics
    """
    logger.info("Starting complete emissions recalculation")
    
    # Find all ReportedMetricValue records with numeric values
    rpvs = ReportedMetricValue.objects.filter(
        aggregated_numeric_value__isnull=False
    )
    
    stats = {
        'total_processed': 0,
        'successful_calculations': 0,
        'failed_calculations': 0,
        'total_records_created': 0,
        'primary_records_created': 0,
        'component_records_created': 0,
    }
    
    for rpv in rpvs:
        stats['total_processed'] += 1
        try:
            results = calculate_emissions_for_activity_value(rpv)
            if results:
                stats['successful_calculations'] += 1
                stats['total_records_created'] += len(results)
                
                # Count primary vs component records
                primary_count = len([r for r in results if r.is_primary_record])
                stats['primary_records_created'] += primary_count
                stats['component_records_created'] += len(results) - primary_count
            else:
                stats['failed_calculations'] += 1
        except Exception as e:
            logger.error(f"Error calculating emissions for RPV {rpv.pk}: {e}", exc_info=True)
            stats['failed_calculations'] += 1
    
    # Keep existing cleanup code
    source_rpvs = [r.id for r in rpvs]
    orphaned_count = CalculatedEmissionValue.objects.filter(
        ~Q(source_activity_value_id__in=source_rpvs)
    ).delete()[0]
    
    stats['orphaned_calculations_deleted'] = orphaned_count
    
    logger.info(f"Completed emissions recalculation. Stats: {stats}")
    return stats 