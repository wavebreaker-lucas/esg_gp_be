import logging
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
import datetime
from dateutil.relativedelta import relativedelta

from .models import ESGMetricSubmission, BaseESGMetric
from .services.aggregation import calculate_report_value

logger = logging.getLogger(__name__)

@receiver([post_save, post_delete], sender=ESGMetricSubmission)
def trigger_recalculation_on_submission_change(sender, instance, **kwargs):
    """ 
    When an ESGMetricSubmission is saved or deleted, trigger recalculation 
    of potentially affected ReportedMetricValue records.
    """
    # instance here is the ESGMetricSubmission that was saved/deleted
    print(f"[DEBUG] Signal triggered for ESGMetricSubmission {getattr(instance, 'pk', 'Unknown')}")
    print(f"[DEBUG] Signal kwargs: {kwargs}")

    # Basic check: Get essential info
    try:
        assignment = instance.assignment
        metric = instance.metric # Base metric instance
        layer = instance.layer or assignment.layer # Use submission layer if specified, else assignment layer
        submission_period = instance.reporting_period # Period tag on the submission header
        assignment_start = assignment.reporting_period_start
        assignment_end = assignment.reporting_period_end

        print(f"[DEBUG] Assignment: {assignment.pk} ({assignment})")
        print(f"[DEBUG] Metric: {metric.pk} ({metric.name}, type: {type(metric).__name__})")
        print(f"[DEBUG] Layer: {layer.pk} ({layer.company_name})")
        print(f"[DEBUG] Submission period: {submission_period}")
        print(f"[DEBUG] Assignment period: {assignment_start} to {assignment_end}")

        if not all([assignment, metric, layer]):
             logger.warning(f"Skipping aggregation trigger for Submission {instance.pk}: Missing assignment, metric, or layer.")
             print(f"[DEBUG] Skipping aggregation: Missing required data")
             return
             
        # --- Determine which periods/levels to recalculate --- 
        # This logic needs careful thought. A single submission might affect 
        # Monthly, Quarterly, and Annual aggregates.
        
        periods_to_recalculate = set()
        
        # 1. Recalculate for the specific period tagged on the submission (if any)
        if submission_period:
             # Assuming submission_period is the end date of a month
             # Add Monthly target
             periods_to_recalculate.add((submission_period, 'M')) 
             
        # 2. Always recalculate the Annual aggregate for the assignment year
        # Use assignment_end as the target period for Annual
        periods_to_recalculate.add((assignment_end, 'A'))
        
        logger.info(f"Submission change for Metric {metric.pk}, Assignment {assignment.pk}, Layer {layer.pk}. Triggering recalculation for: {periods_to_recalculate}")
        print(f"[DEBUG] Periods to recalculate: {periods_to_recalculate}")

        # 3. Call the aggregation service for each affected period/level
        for period_end, level in periods_to_recalculate:
            # Ensure the period_end is within the assignment range? Optional check.
            if assignment_start <= period_end <= assignment_end:
                try:
                    print(f"[DEBUG] Calling calculate_report_value for period {period_end}, level {level}")
                    # TODO: Consider running this asynchronously (e.g., Celery task)
                    result = calculate_report_value(
                        assignment=assignment,
                        metric=metric,
                        reporting_period=period_end,
                        layer=layer,
                        level=level
                    )
                    print(f"[DEBUG] calculate_report_value result: {result}")
                    if result:
                        print(f"[DEBUG] Created/updated ReportedMetricValue ID: {result.pk}")
                        print(f"[DEBUG] - Value: {result.aggregated_numeric_value or result.aggregated_text_value}")
                        print(f"[DEBUG] - Submissions count: {result.source_submission_count}")
                    else:
                        print(f"[DEBUG] No ReportedMetricValue created/updated")
                except Exception as e:
                    logger.error(f"Error during triggered recalculation for Metric {metric.pk}, Period {period_end}, Level {level}: {e}", exc_info=True)
                    print(f"[DEBUG] Error in calculate_report_value: {str(e)}")
                    import traceback
                    print(f"[DEBUG] Traceback: {traceback.format_exc()}")
            else:
                 logger.warning(f"Skipping recalculation for period {period_end} (Level {level}) as it's outside assignment range {assignment_start} - {assignment_end}.")
                 print(f"[DEBUG] Skipping period {period_end} (outside range)")
                 
    except Exception as e:
        # Catch potential errors fetching related objects if instance is partially deleted/invalid
        logger.error(f"Error in submission change signal handler for instance {getattr(instance, 'pk', 'Unknown PK')}: {e}", exc_info=True) 
        print(f"[DEBUG] Error in signal handler: {str(e)}")
        import traceback
        print(f"[DEBUG] Traceback: {traceback.format_exc()}") 