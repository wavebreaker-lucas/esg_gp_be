"""
Service functions for calculating aggregated metric values.
"""

import logging
from django.db.models import Sum, Avg, Count, Max, Min, F, Q, DateTimeField, ExpressionWrapper # Import aggregation functions
from django.utils import timezone
from django.db import transaction
import datetime # Need date/time handling

from accounts.models import LayerProfile
from ..models.templates import TemplateAssignment, ReportedMetricValue, ESGMetricSubmission # Remove ESGMetric, MetricValue, etc.
from ..models.polymorphic_metrics import (
    BaseESGMetric, BasicMetric, TimeSeriesMetric, TabularMetric, 
    MaterialTrackingMatrixMetric, MultiFieldTimeSeriesMetric, MultiFieldMetric
)
from ..models.submission_data import (
    BasicMetricData, TimeSeriesDataPoint, TabularMetricRow, 
    MaterialMatrixDataPoint, MultiFieldTimeSeriesDataPoint, MultiFieldDataPoint
)

logger = logging.getLogger(__name__)

@transaction.atomic # Keep transactions for safety
def calculate_report_value(assignment: TemplateAssignment, metric: BaseESGMetric, reporting_period: datetime.date, layer: LayerProfile, level: str):
    """
    Calculates and saves the aggregated value for a given metric context and level
    into ReportedMetricValue, reading from the new submission data models.

    Args:
        assignment: The TemplateAssignment instance.
        metric: The BaseESGMetric instance.
        reporting_period: The specific date representing the END of the reporting period
                          for which the aggregation is being calculated.
        layer: The LayerProfile instance the value pertains to.
        level: The aggregation level ('M', 'Q', 'A').

    Returns:
        The created or updated ReportedMetricValue instance, or None.
    """
    # Validate level input
    valid_levels = [choice[0] for choice in ReportedMetricValue.LEVEL_CHOICES]
    if level not in valid_levels:
        logger.error(f"Invalid aggregation level '{level}' passed to calculate_report_value.")
        return None
        
    # logger.debug(f"Calculating report value for Metric ID {metric.pk} ({metric.name}), Assignment {assignment.pk}, Period {reporting_period}, Level {level}, Layer {layer.pk}")

    # Check if aggregation is needed
    if not metric.aggregates_inputs:
        logger.debug(f"Skipping aggregation for metric {metric.id} as aggregates_inputs is False.")
        deleted_count, _ = ReportedMetricValue.objects.filter(
            assignment=assignment,
            metric=metric,
            reporting_period=reporting_period,
            layer=layer,
            level=level
        ).delete()
        if deleted_count > 0:
            logger.info(f"Deleted Aggregated Metric Record for {metric.name} ({reporting_period}, Level: {level}) - {layer.company_name} as aggregates_inputs is now False.")
        return None

    # --- Get Specific Metric Instance ---
    try:
        specific_metric = metric.get_real_instance()
    except Exception as e:
        logger.error(f"Could not get specific instance for metric {metric.pk}: {e}")
        return None

    # --- Fetch Relevant Submission Headers Broadly --- 
    source_submissions = ESGMetricSubmission.objects.filter(
        assignment=assignment,
        metric=metric, # Use base metric here
        layer=layer # Filter by layer here for efficiency
    ).order_by('submitted_at', 'pk')

    # Pass a QuerySet of PKs to the metric method
    source_submission_pks_qs = source_submissions.values_list('pk', flat=True)
    source_submission_count = source_submissions.count() # Use count() for efficiency
    
    # Get first/last submission timestamps *from the potentially relevant set*
    first_submission_at = source_submissions.first().submitted_at if source_submission_count > 0 else None
    last_submission_at = source_submissions.last().submitted_at if source_submission_count > 0 else None

    # --- Determine Target Start/End Dates Based on reporting_period AND level --- 
    target_end_date = reporting_period 
    target_year = reporting_period.year
    target_month = reporting_period.month
    
    # Calculate start date based on level
    if level == 'A': # Annual
        target_start_date = reporting_period.replace(month=1, day=1)
    elif level == 'M': # Monthly
        target_start_date = reporting_period.replace(day=1)
    # TODO: Add Daily, Weekly if needed
    # TODO: Add Quarterly calculation
    # elif level == 'Q': # Quarterly
    #     quarter = (target_month - 1) // 3 + 1
    #     target_start_date = reporting_period.replace(month=3 * quarter - 2, day=1)
    else: # Should be caught by initial level validation
        logger.error(f"Unhandled level '{level}' during date calculation.")
        return None 
    
    logger.debug(f"Aggregation window for Level '{level}', End: {target_end_date}: {target_start_date} to {target_end_date}")
    
    # --- Delegate Aggregation to the Specific Metric Instance --- 
    aggregation_result = None
    if source_submission_count > 0: # Only call if there are potentially relevant submissions
        try:
            aggregation_result = specific_metric.calculate_aggregate(
                relevant_submission_pks=source_submission_pks_qs, # Pass the QuerySet of PKs
                target_start_date=target_start_date,
                target_end_date=target_end_date,
                level=level
            )
        except NotImplementedError:
            logger.error(f"Aggregation logic not implemented for metric type: {type(specific_metric).__name__} (ID: {metric.pk})")
            # Do not return here, allow deletion logic below to proceed if needed
            pass
        except Exception as e:
            logger.error(f"Error during metric-specific aggregation call for {metric.pk}: {e}", exc_info=True)
            # Do not return here, allow deletion logic below to proceed if needed
            pass

    # --- Process Aggregation Result --- 
    aggregated_numeric = None
    aggregated_text = None
    agg_method = 'UNKNOWN' 
    # Use the count returned by the metric method, representing actual contribution
    final_source_submission_count = 0 

    if aggregation_result: 
        aggregated_numeric = aggregation_result.get('aggregated_numeric_value')
        aggregated_text = aggregation_result.get('aggregated_text_value')
        agg_method = aggregation_result.get('aggregation_method', 'UNKNOWN')
        final_source_submission_count = aggregation_result.get('contributing_submissions_count', 0)

    # --- Update or Create Parent Aggregation Record --- 
    # Use final_source_submission_count > 0 as the condition
    if final_source_submission_count > 0 or (aggregated_text is not None and aggregated_text != ""): # Also save if text result is non-empty
        parent_defaults = {
            'source_submission_count': final_source_submission_count, # Use count from metric method result
            'first_submission_at': first_submission_at, # Still derived from broad query context
            'last_submission_at': last_submission_at, # Still derived from broad query context
            'aggregated_numeric_value': aggregated_numeric,
            'aggregated_text_value': aggregated_text,
            'last_updated_at': timezone.now()
            # 'aggregation_method': agg_method # Consider adding this field to ReportedMetricValue if useful
        }

        parent_agg_record, created = ReportedMetricValue.objects.update_or_create(
            assignment=assignment,
            metric=metric,
            reporting_period=reporting_period,
            layer=layer,
            level=level, # Pass the level parameter here
            defaults=parent_defaults
        )
        action = "Created" if created else "Updated"
        logger.info(f"{action} ReportedMetricValue (ID: {parent_agg_record.id}) for Metric {metric.pk} - Period {reporting_period} - Level {level}. Method: {agg_method}. Result: Num={aggregated_numeric}, Text='{aggregated_text}' ({final_source_submission_count} contributing submissions)")
        return parent_agg_record
    else:
        # No relevant data found/contributed for this specific reporting_period/level, delete existing RPV
        logger.info(f"No contributing source data found via metric aggregation for Metric {metric.pk} for period ending {reporting_period}, level {level}. Deleting existing record if any.")
        deleted_count, _ = ReportedMetricValue.objects.filter(
            assignment=assignment,
            metric=metric,
            reporting_period=reporting_period,
            layer=layer,
            level=level # Filter by level for deletion
        ).delete()
        if deleted_count > 0:
             logger.info(f"Deleted existing ReportedMetricValue for {metric.name} ({reporting_period}, Level: {level}) as no contributing data was found.")
        return None 