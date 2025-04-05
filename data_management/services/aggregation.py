"""
Service functions for calculating aggregated metric values.
"""

import logging
from django.db.models import Sum, Avg, Count, Max, Min, F, Q, DateTimeField, ExpressionWrapper # Import aggregation functions
from django.utils import timezone
from django.db import transaction
import datetime # Need date/time handling

from accounts.models import LayerProfile
from ..models.templates import (
    ESGMetricSubmission, ReportedMetricValue, ESGMetric, TemplateAssignment,
    MetricValue, MetricValueField, ReportedMetricFieldValue
)
from ..models.polymorphic_metrics import (
    BaseESGMetric, BasicMetric, TimeSeriesMetric, TabularMetric, 
    MaterialTrackingMatrixMetric, MultiFieldTimeSeriesMetric, MultiFieldMetric
)
from ..models.submission_data import (
    BasicMetricData, TimeSeriesDataPoint, TabularMetricRow, 
    MaterialMatrixDataPoint, MultiFieldTimeSeriesDataPoint, MultiFieldDataPoint
)

logger = logging.getLogger(__name__)

def _calculate_aggregation_period(metric, reporting_period_end):
    """Calculates the likely start date for fetching submissions for aggregation."""
    # Simplistic placeholder - assumes aggregation targets the single period end date
    # Or for monthly, assumes aggregation covers the whole month ending reporting_period_end
    if hasattr(metric, 'frequency') and metric.frequency == 'monthly':
        # Start of the month for the given end period
        return reporting_period_end.replace(day=1)
    elif hasattr(metric, 'frequency') and metric.frequency == 'annual':
        # Start of the year for the given end period
        return reporting_period_end.replace(month=1, day=1)
    # Default: Assume aggregation is just for the single end date (e.g., non-time-series)
    return reporting_period_end 

@transaction.atomic # Keep transactions for safety
def calculate_report_value(assignment: TemplateAssignment, metric: BaseESGMetric, reporting_period: datetime.date, layer: LayerProfile):
    """
    Calculates and saves the aggregated value for a given metric context
    into ReportedMetricValue, reading from the new submission data models.

    Args:
        assignment: The TemplateAssignment instance.
        metric: The BaseESGMetric instance.
        reporting_period: The specific date representing the END of the reporting period
                          for which the aggregation is being calculated.
        layer: The LayerProfile instance the value pertains to.

    Returns:
        The created or updated ReportedMetricValue instance, or None.
    """
    logger.debug(f"Calculating report value for Metric ID {metric.pk} ({metric.name}), Assignment {assignment.pk}, Period {reporting_period}, Layer {layer.pk}")

    # Check if aggregation is needed (this flag is still on BaseESGMetric)
    if not metric.aggregates_inputs:
        logger.debug(f"Skipping aggregation for metric {metric.id} as aggregates_inputs is False.")
        # Ensure no Aggregated Metric Record exists if aggregation is turned off
        deleted_count, _ = ReportedMetricValue.objects.filter(
            assignment=assignment,
            metric=metric, # Link using input metric
            reporting_period=reporting_period,
            layer=layer
        ).delete()
        if deleted_count > 0:
            logger.info(f"Deleted Aggregated Metric Record for {metric.name} ({reporting_period}) - {layer.company_name} as aggregates_inputs is now False.")
        return None

    # --- Get Specific Metric Instance ---
    try:
        specific_metric = metric.get_real_instance()
    except Exception as e:
        logger.error(f"Could not get specific instance for metric {metric.pk}: {e}")
        return None # Cannot proceed without specific type

    # --- Determine aggregation period ---    
    # TODO: Refine start date calculation based on metric frequency/assignment range
    aggregation_start_date = _calculate_aggregation_period(specific_metric, reporting_period)
    aggregation_end_date = reporting_period # End date is the target period

    # --- Fetch Relevant Submission Headers --- 
    # Find submission headers whose OWN reporting period falls within the aggregation window
    source_submissions = ESGMetricSubmission.objects.filter(
        assignment=assignment,
        metric=metric, # Use base metric here
        layer=layer,
        reporting_period__gte=aggregation_start_date,
        reporting_period__lte=aggregation_end_date
    ).order_by('submitted_at', 'pk')

    source_submission_pks = list(source_submissions.values_list('pk', flat=True))
    source_submission_count = len(source_submission_pks)
    
    # Get first/last submission timestamps *from the filtered set*
    first_submission_at = source_submissions.first().submitted_at if source_submission_count > 0 else None
    last_submission_at = source_submissions.last().submitted_at if source_submission_count > 0 else None

    if source_submission_count == 0:
        logger.debug(f"No source submissions found for Metric {metric.pk} in period {aggregation_start_date} - {aggregation_end_date} for layer {layer.pk}.")
        # If no inputs exist, ensure no parent aggregate record exists.
        deleted_count, _ = ReportedMetricValue.objects.filter(
            assignment=assignment,
            metric=metric,
            reporting_period=reporting_period,
            layer=layer
        ).delete()
        if deleted_count > 0:
            logger.info(f"Deleted Aggregated Metric Record for {metric.name} ({reporting_period}) - {layer.company_name} due to no source inputs.")
        return None

    # --- Aggregate Based on Metric Type --- 
    aggregated_numeric = None
    aggregated_text = None
    agg_method = None # We'll set this based on logic

    if isinstance(specific_metric, BasicMetric):
        # Fetch BasicMetricData linked to the source submissions
        data_points = BasicMetricData.objects.filter(submission_id__in=source_submission_pks)
        if specific_metric.unit_type == 'text':
            # Get text from the *last* submission's data 
            last_sub_pk = source_submissions.last().pk if source_submission_count > 0 else None
            last_data = data_points.filter(submission_id=last_sub_pk).first()
            aggregated_text = last_data.value_text if last_data else None
            agg_method = 'LAST'
        else: # Numeric types
            # TODO: Add aggregation method choice (SUM, AVG?) on BasicMetric? Default to SUM.
            result = data_points.aggregate(total=Sum('value_numeric'))
            aggregated_numeric = result.get('total')
            agg_method = 'SUM'

    elif isinstance(specific_metric, TimeSeriesMetric):
        # Fetch TimeSeriesDataPoint linked to the source submissions
        data_points = TimeSeriesDataPoint.objects.filter(submission_id__in=source_submission_pks)
        # Use the aggregation_method defined on the TimeSeriesMetric model
        agg_method = specific_metric.aggregation_method
        if agg_method == 'SUM':
             result = data_points.aggregate(total=Sum('value'))
             aggregated_numeric = result.get('total')
        elif agg_method == 'AVG':
             result = data_points.aggregate(avg=Avg('value'))
             aggregated_numeric = result.get('avg')
        elif agg_method == 'LAST':
             # Find the data point linked to the last submission header
             last_sub_pk = source_submissions.last().pk if source_submission_count > 0 else None
             last_data = data_points.filter(submission_id=last_sub_pk).first()
             aggregated_numeric = last_data.value if last_data else None
        # TODO: Handle text-based time series?
        
    # --- TODO: Implement aggregation logic for other types ---
    elif isinstance(specific_metric, TabularMetric):
        data_rows = TabularMetricRow.objects.filter(submission_id__in=source_submission_pks)
        logger.info(f"Aggregation logic for TabularMetric (ID: {metric.pk}) TBD. Found {data_rows.count()} rows.")
        agg_method = 'COUNT' # Example: Store row count
        aggregated_numeric = data_rows.count() 
        
    elif isinstance(specific_metric, MaterialTrackingMatrixMetric):
        data_points = MaterialMatrixDataPoint.objects.filter(submission_id__in=source_submission_pks)
        # Example: Sum all values regardless of material type?
        result = data_points.aggregate(total=Sum('value'))
        aggregated_numeric = result.get('total')
        agg_method = 'SUM_ALL'
        logger.info(f"Aggregation logic for MaterialTrackingMatrixMetric (ID: {metric.pk}) TBD. Found {data_points.count()} points, summed to {aggregated_numeric}.")
        
    elif isinstance(specific_metric, MultiFieldTimeSeriesMetric):
        data_points = MultiFieldTimeSeriesDataPoint.objects.filter(submission_id__in=source_submission_pks)
        # Example: Count the number of periods submitted?
        aggregated_numeric = data_points.values('period').distinct().count()
        agg_method = 'COUNT_PERIODS'
        logger.info(f"Aggregation logic for MultiFieldTimeSeriesMetric (ID: {metric.pk}) TBD. Found {aggregated_numeric} distinct periods.")
        
    elif isinstance(specific_metric, MultiFieldMetric):
        # This likely doesn't aggregate to a single value easily.
        data_exists = MultiFieldDataPoint.objects.filter(submission_id__in=source_submission_pks).exists()
        aggregated_text = "Data Submitted" if data_exists else "No Data"
        agg_method = 'METADATA_ONLY'
        logger.info(f"Aggregation logic for MultiFieldMetric (ID: {metric.pk}) TBD. Data exists: {data_exists}.")
        
    else:
        logger.warning(f"Aggregation not implemented for metric type: {type(specific_metric).__name__} (ID: {metric.pk})")
        agg_method = 'UNKNOWN'
        # Do not create a ReportedMetricValue if type is unknown
        return None 

    # --- Update or Create Parent Aggregation Record --- 
    parent_defaults = {
        'source_submission_count': source_submission_count,
        'first_submission_at': first_submission_at,
        'last_submission_at': last_submission_at,
        'aggregated_numeric_value': aggregated_numeric,
        'aggregated_text_value': aggregated_text,
        # Maybe store agg_method used?
        'last_updated_at': timezone.now()
    }

    parent_agg_record, created = ReportedMetricValue.objects.update_or_create(
        assignment=assignment,
        metric=metric, # Link to the base metric
        reporting_period=reporting_period, # The target aggregation period
        layer=layer,
        defaults=parent_defaults
    )
    action = "Created" if created else "Updated"
    logger.info(f"{action} ReportedMetricValue (ID: {parent_agg_record.id}) for Metric {metric.pk} - Period {reporting_period} - Layer {layer.pk}. Method: {agg_method}. Result: Num={aggregated_numeric}, Text='{aggregated_text}'")

    return parent_agg_record 