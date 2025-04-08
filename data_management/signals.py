import logging
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
import datetime
from dateutil.relativedelta import relativedelta
from django.db import transaction

from .models import ESGMetricSubmission, BaseESGMetric
from .models.polymorphic_metrics import BasicMetric
from .services.aggregation import calculate_report_value

logger = logging.getLogger(__name__)

@receiver([post_save, post_delete], sender=ESGMetricSubmission)
def trigger_recalculation_on_submission_change(sender, instance, **kwargs):
    """ 
    When an ESGMetricSubmission is saved or deleted, trigger recalculation 
    of potentially affected ReportedMetricValue records AFTER the transaction commits.
    """
    # instance here is the ESGMetricSubmission that was saved/deleted
    print(f"[DEBUG] Signal triggered for ESGMetricSubmission {getattr(instance, 'pk', 'Unknown')}")
    print(f"[DEBUG] Signal kwargs: {kwargs}")

    # Get PK now, as instance might not be valid inside on_commit if deleted
    instance_pk = instance.pk
    
    # Define the work to be done after commit
    def run_aggregation_after_commit():
        print(f"[DEBUG] Running aggregation logic inside on_commit for Submission PK {instance_pk}")
        try:
            # Re-fetch the instance inside the on_commit block if needed, 
            # or pass necessary IDs from the outer scope.
            # For deletion, instance might not exist, so we rely on IDs passed.
            # We need assignment_id, metric_id, layer_id, submission_period, assignment_end
            try:
                 # Use a fresh instance if possible (for post_save)
                 committed_instance = sender.objects.get(pk=instance_pk) 
                 assignment = committed_instance.assignment
                 metric = committed_instance.metric
                 layer = committed_instance.layer or assignment.layer
                 submission_period = committed_instance.reporting_period
                 assignment_start = assignment.reporting_period_start
                 assignment_end = assignment.reporting_period_end
            except sender.DoesNotExist:
                 # Instance was deleted (post_delete signal)
                 # We have to rely on the potentially stale data from the outer scope
                 # This might be less reliable for post_delete if related objects also change
                 print(f"[DEBUG] Instance PK {instance_pk} not found, likely deleted. Using outer scope data.")
                 # Need to ensure these were captured correctly before deletion
                 # Re-capture them here for clarity, though they come from outer scope
                 assignment = instance.assignment # May fail if cascade deleted
                 metric = instance.metric # May fail if cascade deleted
                 layer = instance.layer or assignment.layer # May fail
                 submission_period = instance.reporting_period
                 assignment_start = assignment.reporting_period_start
                 assignment_end = assignment.reporting_period_end

            print(f"[DEBUG] Post-commit Assignment: {assignment.pk}")
            print(f"[DEBUG] Post-commit Metric: {metric.pk}")
            print(f"[DEBUG] Post-commit Layer: {layer.pk}")
            print(f"[DEBUG] Post-commit Submission period: {submission_period}")

            if not all([assignment, metric, layer]):
                 logger.warning(f"Skipping aggregation trigger (post-commit) for Submission {instance_pk}: Missing assignment, metric, or layer.")
                 print(f"[DEBUG] Skipping aggregation (post-commit): Missing required data")
                 return

            periods_to_recalculate = set()
            if submission_period:
                 if not isinstance(metric, BasicMetric):
                     periods_to_recalculate.add((submission_period, 'M'))
                 else:
                     logger.info(f"Skipping Monthly recalculation trigger (post-commit) for BasicMetric {metric.pk}")
                     print(f"[DEBUG] Skipping Monthly recalculation trigger (post-commit) for BasicMetric")

            periods_to_recalculate.add((assignment_end, 'A'))

            logger.info(f"Submission change committed for Metric {metric.pk}, Assignment {assignment.pk}, Layer {layer.pk}. Triggering recalculation for: {periods_to_recalculate}")
            print(f"[DEBUG] Post-commit Periods to recalculate: {periods_to_recalculate}")

            for period_end, level in periods_to_recalculate:
                if assignment_start <= period_end <= assignment_end:
                    try:
                        print(f"[DEBUG] Calling calculate_report_value (post-commit) for period {period_end}, level {level}")
                        result = calculate_report_value(
                            assignment=assignment,
                            metric=metric,
                            reporting_period=period_end,
                            layer=layer,
                            level=level
                        )
                        print(f"[DEBUG] calculate_report_value (post-commit) result: {result}")
                        if result:
                            print(f"[DEBUG] Created/updated ReportedMetricValue ID: {result.pk}")
                            print(f"[DEBUG] - Value: {result.aggregated_numeric_value or result.aggregated_text_value}")
                            print(f"[DEBUG] - Submissions count: {result.source_submission_count}")
                        else:
                            print(f"[DEBUG] No ReportedMetricValue created/updated (post-commit)")
                    except Exception as e:
                        logger.error(f"Error during triggered recalculation (post-commit) for Metric {metric.pk}, Period {period_end}, Level {level}: {e}", exc_info=True)
                        print(f"[DEBUG] Error in calculate_report_value (post-commit): {str(e)}")
                        import traceback
                        print(f"[DEBUG] Traceback: {traceback.format_exc()}")
                else:
                     logger.warning(f"Skipping recalculation (post-commit) for period {period_end} (Level {level}) as it's outside assignment range {assignment_start} - {assignment_end}.")
                     print(f"[DEBUG] Skipping period {period_end} (outside range, post-commit)")
                     
        except Exception as e:
            logger.error(f"Error in post-commit signal handler logic for Submission PK {instance_pk}: {e}", exc_info=True) 
            print(f"[DEBUG] Error in on_commit handler: {str(e)}")
            import traceback
            print(f"[DEBUG] Traceback: {traceback.format_exc()}")
            
    # Schedule the function to run after the current transaction commits
    transaction.on_commit(run_aggregation_after_commit)
    print(f"[DEBUG] Aggregation logic scheduled via on_commit for Submission PK {instance_pk}")

# Optional: Handle potential errors in the main signal handler if needed,
# though most work is now deferred.
# Removed the outer try/except block as the main logic is deferred. 