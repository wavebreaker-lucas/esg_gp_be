import logging
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
import datetime
from dateutil.relativedelta import relativedelta
from django.db import transaction

from .models import ESGMetricSubmission, BaseESGMetric, ReportedMetricValue
from .models.polymorphic_metrics import BasicMetric, TimeSeriesMetric
from .models.submission_data import VehicleMonthlyData
from .services.aggregation import calculate_report_value
from .services.emissions import calculate_emissions_for_activity_value

logger = logging.getLogger(__name__)

@receiver([post_save, post_delete], sender=VehicleMonthlyData)
def trigger_recalculation_on_vehicle_data_change(sender, instance, **kwargs):
    """
    When VehicleMonthlyData is saved or deleted, trigger recalculation by updating
    the parent submission.
    """
    print(f"[DEBUG] Signal triggered for VehicleMonthlyData {getattr(instance, 'pk', 'Unknown')}")
    
    # Get the parent submission through the vehicle record
    try:
        # For post_save, the instance is valid
        if not kwargs.get('raw', False):  # Skip during fixture loading
            vehicle = instance.vehicle
            if vehicle and vehicle.submission_id:
                submission = ESGMetricSubmission.objects.get(pk=vehicle.submission_id)
                
                # Simply touch the submission to trigger its post_save signal
                submission.save(update_fields=['updated_at'])
                print(f"[DEBUG] Triggered recalculation by touching submission {submission.pk}")
    except Exception as e:
        logger.error(f"Error in vehicle monthly data signal handler: {e}", exc_info=True)
        print(f"[DEBUG] Error in vehicle data signal handler: {str(e)}")

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
            
            # For time series metrics, handle monthly aggregations differently
            if isinstance(metric, TimeSeriesMetric):
                try:
                    # Find all the unique month periods from the time series data points
                    from .models.submission_data import TimeSeriesDataPoint
                    
                    # Get data points for this submission
                    if kwargs.get('created', False) or ('created' not in kwargs): # For new or updated submissions
                        print(f"[DEBUG] Finding time series data points for submission {instance_pk}")
                        data_points = TimeSeriesDataPoint.objects.filter(submission_id=instance_pk)
                        
                        # Extract unique month periods from the data points
                        unique_months = set()
                        for point in data_points:
                            # For each point, set the day to the last day of its month to use as the reporting period
                            if point.period:
                                # Calculate the last day of the month
                                next_month = point.period.replace(day=28) + datetime.timedelta(days=4)  # This will never be the last day of the month
                                month_end = next_month - datetime.timedelta(days=next_month.day)  # Subtract the extra days to get the last day
                                unique_months.add(month_end)
                        
                        print(f"[DEBUG] Found {len(unique_months)} unique months in time series data")
                        
                        # Add each unique month period with 'M' level to periods_to_recalculate
                        for month_end in unique_months:
                            if assignment_start <= month_end <= assignment_end:
                                periods_to_recalculate.add((month_end, 'M'))
                            else:
                                print(f"[DEBUG] Skipping month {month_end} as it's outside assignment range")
                    
                    # Also include the submission period with 'M' level as a fallback
                    if submission_period:
                        periods_to_recalculate.add((submission_period, 'M'))
                
                except Exception as e:
                    logger.error(f"Error finding time series periods: {e}")
                    print(f"[DEBUG] Error processing time series periods: {e}")
                    # Fallback to standard method
                    if submission_period:
                        periods_to_recalculate.add((submission_period, 'M'))
            
            # For non-time series, non-basic metrics:
            elif not isinstance(metric, BasicMetric):
                # Special handling for VehicleTrackingMetric
                from .models.polymorphic_metrics import VehicleTrackingMetric
                if isinstance(metric, VehicleTrackingMetric):
                    # For vehicle tracking, we need to aggregate based on vehicle monthly data periods
                    from .models.submission_data import VehicleRecord, VehicleMonthlyData
                    
                    try:
                        # Find all vehicle records for this submission
                        vehicle_records = VehicleRecord.objects.filter(submission_id=instance_pk)
                        
                        if vehicle_records.exists():
                            # Get all monthly data periods for these vehicles
                            monthly_data_periods = VehicleMonthlyData.objects.filter(
                                vehicle__in=vehicle_records
                            ).values_list('period', flat=True).distinct()
                            
                            # Add each period to recalculation set
                            for period in monthly_data_periods:
                                if period and assignment_start <= period <= assignment_end:
                                    periods_to_recalculate.add((period, 'M'))
                                
                            print(f"[DEBUG] Found {len(periods_to_recalculate)} vehicle monthly periods to recalculate")
                    except Exception as e:
                        logger.error(f"Error finding vehicle monthly periods: {e}")
                        print(f"[DEBUG] Error processing vehicle periods: {e}")
                else:
                    # Standard monthly aggregation for other metric types
                    if submission_period:
                        periods_to_recalculate.add((submission_period, 'M'))
            else:
                # For BasicMetric
                logger.info(f"Skipping Monthly recalculation trigger (post-commit) for BasicMetric {metric.pk}")
                print(f"[DEBUG] Skipping Monthly recalculation trigger (post-commit) for BasicMetric")

            # Always calculate Annual aggregation
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

@receiver(post_save, sender=ReportedMetricValue)
def trigger_emission_calculation(sender, instance, **kwargs):
    """
    When a ReportedMetricValue is saved, trigger emission calculation if the metric
    has emission categories configured.
    """
    # Skip if this is a new record and has no numeric value
    if kwargs.get('created', False) and instance.aggregated_numeric_value is None:
        return
        
    # Skip if metric doesn't have emission categories configured
    if not instance.metric.emission_category or not instance.metric.emission_sub_category:
        return
        
    def run_emission_calculation():
        try:
            result = calculate_emissions_for_activity_value(instance)
            if result:
                logger.info(f"Created/updated emission calculation for RPV {instance.pk}: {result.calculated_value} {result.emission_unit}")
            else:
                logger.debug(f"No emission calculation created for RPV {instance.pk} - no suitable factor found")
        except Exception as e:
            logger.error(f"Error calculating emissions for RPV {instance.pk}: {e}", exc_info=True)
            
    # Schedule the calculation after the transaction commits
    transaction.on_commit(run_emission_calculation)

# Optional: Handle potential errors in the main signal handler if needed,
# though most work is now deferred.
# Removed the outer try/except block as the main logic is deferred. 