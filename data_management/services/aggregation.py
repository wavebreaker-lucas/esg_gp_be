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
        
    logger.debug(f"Calculating report value for Metric ID {metric.pk} ({metric.name}), Assignment {assignment.pk}, Period {reporting_period}, Level {level}, Layer {layer.pk}")

    # Check if aggregation is needed
    if not metric.aggregates_inputs:
        logger.debug(f"Skipping aggregation for metric {metric.id} as aggregates_inputs is False.")
        deleted_count, _ = ReportedMetricValue.objects.filter(
            assignment=assignment, metric=metric, reporting_period=reporting_period, layer=layer, level=level
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

    source_submission_pks = list(source_submissions.values_list('pk', flat=True))
    source_submission_count = len(source_submission_pks)
    
    # Get first/last submission timestamps *from the potentially relevant set*
    first_submission_at = source_submissions.first().submitted_at if source_submission_count > 0 else None
    last_submission_at = source_submissions.last().submitted_at if source_submission_count > 0 else None

    # --- Aggregate Based on Metric Type --- 
    aggregated_numeric = None
    aggregated_text = None
    agg_method = None
    final_source_submission_count = 0

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
    else: # Should be caught by initial level validation
        logger.error(f"Unhandled level '{level}' during date calculation.")
        return None 
    
    logger.debug(f"Aggregation window for Level '{level}', End: {target_end_date}: {target_start_date} to {target_end_date}")
    
    # For non-time-series, the concept of a start/end date for filtering inputs might not apply
    is_time_based_aggregation = isinstance(specific_metric, (TimeSeriesMetric, MaterialTrackingMatrixMetric, MultiFieldTimeSeriesMetric))

    if isinstance(specific_metric, BasicMetric):
        # Basic metrics - aggregate ALL linked data points regardless of the target period?
        # Assumption: The target period (level+reporting_period) defines WHEN the aggregate is stored,
        # not WHICH basic inputs to include. 
        all_data_points = BasicMetricData.objects.filter(submission_id__in=source_submission_pks)
        final_source_submission_count = all_data_points.count()
        
        if final_source_submission_count > 0:
            if specific_metric.unit_type == 'text':
                # Still use last overall submission header
                last_sub_pk = source_submissions.last().pk if source_submission_count > 0 else None
                last_data = all_data_points.filter(submission_id=last_sub_pk).first()
                aggregated_text = last_data.value_text if last_data else None
                agg_method = 'LAST'
            else: # Numeric types
                # TODO: Allow configuration of SUM/AVG on BasicMetric?
                result = all_data_points.aggregate(total=Sum('value_numeric'))
                aggregated_numeric = result.get('total')
                agg_method = 'SUM'

    elif is_time_based_aggregation:
        # Fetch all potentially relevant data points first
        if isinstance(specific_metric, TimeSeriesMetric):
            all_data_points = TimeSeriesDataPoint.objects.filter(submission_id__in=source_submission_pks)
            value_field_name = 'value'
        elif isinstance(specific_metric, MaterialTrackingMatrixMetric):
            all_data_points = MaterialMatrixDataPoint.objects.filter(submission_id__in=source_submission_pks)
            value_field_name = 'value' # Assuming we sum the value field
        elif isinstance(specific_metric, MultiFieldTimeSeriesMetric):
            all_data_points = MultiFieldTimeSeriesDataPoint.objects.filter(submission_id__in=source_submission_pks)
            # Aggregation needs more complex logic based on field_definitions & total_row_aggregation
            value_field_name = None # Cannot simply aggregate a single field
        else: 
            all_data_points = None
            value_field_name = None
            
        if all_data_points is not None:
            # Filter by the data point's own period matching the target aggregation window
            points_in_period = all_data_points.filter(
                period__gte=target_start_date,
                period__lte=target_end_date
            )
            final_source_submission_count = points_in_period.values('submission_id').distinct().count()

            if final_source_submission_count > 0:
                # Apply specific aggregation based on type
                if isinstance(specific_metric, TimeSeriesMetric):
                    agg_method = specific_metric.aggregation_method
                    if agg_method == 'SUM':
                        result = points_in_period.aggregate(total=Sum(value_field_name))
                        aggregated_numeric = result.get('total')
                    elif agg_method == 'AVG':
                        result = points_in_period.aggregate(avg=Avg(value_field_name))
                        aggregated_numeric = result.get('avg')
                    elif agg_method == 'LAST':
                        # Find last submission *header* within the period that has a data point in the period
                        relevant_submission_pks = source_submissions.filter(
                            esgmetricsubmission_timeseriesdatapoint_set__period__gte=target_start_date,
                            esgmetricsubmission_timeseriesdatapoint_set__period__lte=target_end_date
                        ).values_list('pk', flat=True)
                        if relevant_submission_pks:
                            # Get the data point linked to the latest submission among those
                            last_data = points_in_period.filter(submission_id__in=relevant_submission_pks).order_by('-submission__submitted_at').first()
                            aggregated_numeric = last_data.value if last_data else None
                        else:
                             aggregated_numeric = None 
                    # TODO: Handle text-based time series?

                elif isinstance(specific_metric, MaterialTrackingMatrixMetric):
                    # Example: Sum all values in period regardless of material type?
                    result = points_in_period.aggregate(total=Sum(value_field_name))
                    aggregated_numeric = result.get('total')
                    agg_method = 'SUM_ALL_IN_PERIOD'
                
                elif isinstance(specific_metric, MultiFieldTimeSeriesMetric):
                    # Example: Count the number of distinct periods submitted within the target window?
                    aggregated_numeric = points_in_period.values('period').distinct().count()
                    agg_method = 'COUNT_PERIODS'
                    # TODO: Implement actual field aggregation based on total_row_aggregation

    # --- Other metric types --- 
    elif isinstance(specific_metric, TabularMetric):
        all_data_rows = TabularMetricRow.objects.filter(submission_id__in=source_submission_pks)
        # How does period apply? Assume we count rows from submissions tagged within period?
        subs_in_period = source_submissions.filter(reporting_period__gte=target_start_date, reporting_period__lte=target_end_date)
        subs_in_period_pks = list(subs_in_period.values_list('pk', flat=True))
        data_rows_in_period = all_data_rows.filter(submission_id__in=subs_in_period_pks)
        final_source_submission_count = subs_in_period.count()
        aggregated_numeric = data_rows_in_period.count()
        agg_method = 'COUNT_ROWS_IN_PERIOD'
        logger.info(f"Aggregation for TabularMetric ID {metric.pk}: Counted {aggregated_numeric} rows from {final_source_submission_count} submissions tagged in period.")

    elif isinstance(specific_metric, MultiFieldMetric):
        # Check if *any* submission exists in broad list.
        data_point_exists = MultiFieldDataPoint.objects.filter(submission_id__in=source_submission_pks).exists()
        aggregated_text = "Data Submitted" if data_point_exists else "No Data"
        agg_method = 'METADATA_ONLY'
        final_source_submission_count = 1 if data_point_exists else 0
        logger.info(f"Aggregation for MultiField ID {metric.pk}: Data exists: {data_point_exists}.")

    else:
        logger.warning(f"Aggregation not implemented for metric type: {type(specific_metric).__name__} (ID: {metric.pk})")
        agg_method = 'UNKNOWN'
        return None

    # --- Update or Create Parent Aggregation Record --- 
    if final_source_submission_count > 0 or aggregated_text is not None:
        parent_defaults = {
            'source_submission_count': final_source_submission_count,
            'first_submission_at': first_submission_at,
            'last_submission_at': last_submission_at,
            'aggregated_numeric_value': aggregated_numeric,
            'aggregated_text_value': aggregated_text,
            'last_updated_at': timezone.now()
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
        logger.info(f"{action} ReportedMetricValue (ID: {parent_agg_record.id}) for Metric {metric.pk} - Period {reporting_period} - Level {level}. Method: {agg_method}. Result: Num={aggregated_numeric}, Text='{aggregated_text}'")
        return parent_agg_record
    else:
        # No relevant data found for this specific reporting_period/level, delete existing RPV
        logger.info(f"No relevant source data found for Metric {metric.pk} for period ending {reporting_period}, level {level}. Deleting existing record if any.")
        deleted_count, _ = ReportedMetricValue.objects.filter(
            assignment=assignment,
            metric=metric,
            reporting_period=reporting_period,
            layer=layer,
            level=level # Filter by level for deletion
        ).delete()
        if deleted_count > 0:
             logger.info(f"Deleted existing ReportedMetricValue for {metric.name} ({reporting_period}, Level: {level}) as no relevant data was found.")
        return None 