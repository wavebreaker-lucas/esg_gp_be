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

    # Check if aggregation is needed
    if not metric.aggregates_inputs:
        logger.debug(f"Skipping aggregation for metric {metric.id} as aggregates_inputs is False.")
        deleted_count, _ = ReportedMetricValue.objects.filter(
            assignment=assignment, metric=metric, reporting_period=reporting_period, layer=layer
        ).delete()
        if deleted_count > 0:
            logger.info(f"Deleted Aggregated Metric Record for {metric.name} ({reporting_period}) - {layer.company_name} as aggregates_inputs is now False.")
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
    final_source_submission_count = 0 # Track count contributing to *this specific period*

    # Define target period start/end based on reporting_period (aggregation target)
    # This needs robust logic, esp. for frequencies != monthly/annual
    target_year = reporting_period.year
    target_month = reporting_period.month
    target_start_date = reporting_period.replace(day=1) # Default: start of month
    target_end_date = reporting_period # End date is always the target
    
    # Adjust start date for annual aggregation
    # TODO: Handle quarterly, weekly etc. based on metric frequency/level requested
    if hasattr(specific_metric, 'frequency') and specific_metric.frequency == 'annual':
         target_start_date = reporting_period.replace(month=1, day=1)
    # For non-time-series, the concept of a start/end date might not apply in the same way

    if isinstance(specific_metric, BasicMetric):
        # Basic metrics usually don't have inherent periods in their data
        # Aggregate ALL data points linked to the submissions found
        all_data_points = BasicMetricData.objects.filter(submission_id__in=source_submission_pks)
        final_source_submission_count = all_data_points.count() # Count how many data points exist
        
        if final_source_submission_count > 0:
            if specific_metric.unit_type == 'text':
                # Get text from the data linked to the *last overall submission header*
                last_sub_pk = source_submissions.last().pk if source_submission_count > 0 else None
                last_data = all_data_points.filter(submission_id=last_sub_pk).first()
                aggregated_text = last_data.value_text if last_data else None
                agg_method = 'LAST'
            else: # Numeric types
                # TODO: Aggregation method SUM/AVG? Default SUM.
                result = all_data_points.aggregate(total=Sum('value_numeric'))
                aggregated_numeric = result.get('total')
                agg_method = 'SUM'
        # Else: No data points found, values remain None

    elif isinstance(specific_metric, TimeSeriesMetric):
        all_data_points = TimeSeriesDataPoint.objects.filter(submission_id__in=source_submission_pks)
        
        # Filter by the data point's own period matching the target aggregation window
        points_in_period = all_data_points.filter(
            period__gte=target_start_date,
            period__lte=target_end_date
        )
        final_source_submission_count = points_in_period.count()

        if final_source_submission_count > 0:
            agg_method = specific_metric.aggregation_method
            if agg_method == 'SUM':
                 result = points_in_period.aggregate(total=Sum('value'))
                 aggregated_numeric = result.get('total')
            elif agg_method == 'AVG':
                 result = points_in_period.aggregate(avg=Avg('value'))
                 aggregated_numeric = result.get('avg')
            elif agg_method == 'LAST':
                 # Find the last data point *within the target period* 
                 # Need submission time from header AND period match
                 relevant_submission_pks = ESGMetricSubmission.objects.filter(
                     pk__in=source_submission_pks,
                     esgmetricsubmission_timeseriesdatapoint_set__period__gte=target_start_date,
                     esgmetricsubmission_timeseriesdatapoint_set__period__lte=target_end_date
                 ).order_by('-submitted_at').values_list('pk', flat=True)
                 
                 if relevant_submission_pks:
                     last_sub_pk_in_period = relevant_submission_pks.first()
                     last_data = points_in_period.filter(submission_id=last_sub_pk_in_period).first()
                     aggregated_numeric = last_data.value if last_data else None
                 else: # Should not happen if final_source_submission_count > 0
                     aggregated_numeric = None 
            # TODO: Handle text-based time series?

    # --- TODO: Implement *filtered* aggregation logic for other types ---
    elif isinstance(specific_metric, TabularMetric):
        all_data_rows = TabularMetricRow.objects.filter(submission_id__in=source_submission_pks)
        # How does period apply? Maybe filter submission headers by period tag?
        # Let's filter headers for now, assuming tag is reliable for this type.
        subs_in_period = source_submissions.filter(reporting_period__gte=target_start_date, reporting_period__lte=target_end_date)
        subs_in_period_pks = list(subs_in_period.values_list('pk', flat=True))
        data_rows_in_period = all_data_rows.filter(submission_id__in=subs_in_period_pks)
        final_source_submission_count = subs_in_period.count() # Count submissions in period
        aggregated_numeric = data_rows_in_period.count() # Count rows submitted in period
        agg_method = 'COUNT_ROWS_IN_PERIOD'
        logger.info(f"Aggregation for TabularMetric ID {metric.pk}: Counted {aggregated_numeric} rows from {final_source_submission_count} submissions in period.")

    elif isinstance(specific_metric, MaterialTrackingMatrixMetric):
        all_data_points = MaterialMatrixDataPoint.objects.filter(submission_id__in=source_submission_pks)
        # Filter by the data point's own period
        points_in_period = all_data_points.filter(
            period__gte=target_start_date,
            period__lte=target_end_date
        )
        final_source_submission_count = points_in_period.values('submission_id').distinct().count() # Count distinct submissions with data in period
        # Example: Sum all values in period regardless of material type?
        result = points_in_period.aggregate(total=Sum('value'))
        aggregated_numeric = result.get('total')
        agg_method = 'SUM_ALL_IN_PERIOD'
        logger.info(f"Aggregation for MaterialMatrix ID {metric.pk}: Summed {aggregated_numeric} from {points_in_period.count()} points ({final_source_submission_count} submissions) in period.")

    elif isinstance(specific_metric, MultiFieldTimeSeriesMetric):
        all_data_points = MultiFieldTimeSeriesDataPoint.objects.filter(submission_id__in=source_submission_pks)
        # Filter by the data point's own period
        points_in_period = all_data_points.filter(
            period__gte=target_start_date,
            period__lte=target_end_date
        )
        final_source_submission_count = points_in_period.values('submission_id').distinct().count()
        # Example: Count the number of distinct periods submitted within the target window?
        aggregated_numeric = points_in_period.values('period').distinct().count()
        agg_method = 'COUNT_PERIODS'
        logger.info(f"Aggregation for MultiFieldTS ID {metric.pk}: Counted {aggregated_numeric} distinct periods from {final_source_submission_count} submissions in window.")

    elif isinstance(specific_metric, MultiFieldMetric):
        # Doesn't have its own period. Check if *any* submission exists in broad list.
        data_point_exists = MultiFieldDataPoint.objects.filter(submission_id__in=source_submission_pks).exists()
        aggregated_text = "Data Submitted" if data_point_exists else "No Data"
        agg_method = 'METADATA_ONLY'
        final_source_submission_count = 1 if data_point_exists else 0 # Simplification
        logger.info(f"Aggregation for MultiField ID {metric.pk}: Data exists: {data_point_exists}.")

    else:
        logger.warning(f"Aggregation not implemented for metric type: {type(specific_metric).__name__} (ID: {metric.pk})")
        agg_method = 'UNKNOWN'
        return None # Do not create RPV if type is unknown

    # --- Update or Create Parent Aggregation Record --- 
    # Only create/update if there were relevant submissions/data for the period
    if final_source_submission_count > 0 or aggregated_text is not None:
        parent_defaults = {
            'source_submission_count': final_source_submission_count, # Now reflects count relevant to *this* period
            'first_submission_at': first_submission_at, # This still reflects overall first/last
            'last_submission_at': last_submission_at,
            'aggregated_numeric_value': aggregated_numeric,
            'aggregated_text_value': aggregated_text,
            'last_updated_at': timezone.now()
        }

        parent_agg_record, created = ReportedMetricValue.objects.update_or_create(
            assignment=assignment,
            metric=metric, # Link to the base metric
            reporting_period=reporting_period, # The target aggregation period END DATE
            layer=layer,
            # If using levels: level=level_parameter, # Pass level parameter here
            defaults=parent_defaults
        )
        action = "Created" if created else "Updated"
        logger.info(f"{action} ReportedMetricValue (ID: {parent_agg_record.id}) for Metric {metric.pk} - Period {reporting_period} - Layer {layer.pk}. Method: {agg_method}. Result: Num={aggregated_numeric}, Text='{aggregated_text}'")
        return parent_agg_record
    else:
        # No relevant data found for this specific reporting_period, delete any existing RPV
        logger.info(f"No relevant source data found for Metric {metric.pk} for period ending {reporting_period}. Deleting existing record if any.")
        deleted_count, _ = ReportedMetricValue.objects.filter(
            assignment=assignment,
            metric=metric,
            reporting_period=reporting_period,
            layer=layer
            # If using levels: level=level_parameter
        ).delete()
        if deleted_count > 0:
             logger.info(f"Deleted existing ReportedMetricValue for {metric.name} ({reporting_period}) as no relevant data was found.")
        return None 