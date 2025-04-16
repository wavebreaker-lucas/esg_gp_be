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
    
    # For deletion, check if we need to force-delete ReportedMetricValue records
    if kwargs.get('signal') == post_delete:
        print(f"[DEBUG] Post-delete signal for submission {instance.pk}")
        # Store values needed later since the instance is about to be deleted
        assignment_id = instance.assignment_id
        metric_id = instance.metric_id
        layer_id = instance.layer_id if instance.layer_id else instance.assignment.layer_id
        reporting_period = instance.reporting_period
        
        # Add a task to be executed after commit to clean up orphaned ReportedMetricValue records
        transaction.on_commit(lambda: clean_up_orphaned_reported_values(
            assignment_id, metric_id, layer_id, reporting_period
        ))
        print(f"[DEBUG] Scheduled orphaned record cleanup for submission {instance.pk}")

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
                    # Always process time series data points regardless of creation or update
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

def clean_up_orphaned_reported_values(assignment_id, metric_id, layer_id, reporting_period):
    """
    Check if any ReportedMetricValue records need to be deleted after a submission deletion.
    This is called via on_commit to ensure we're working with the post-transaction database state.
    """
    try:
        print(f"[DEBUG] Checking for orphaned ReportedMetricValue records")
        from .models import ReportedMetricValue, ESGMetricSubmission
        from .models.polymorphic_metrics import VehicleTrackingMetric, TimeSeriesMetric, MultiFieldTimeSeriesMetric, BaseESGMetric
        
        # Check if this is a time series-like metric that can have monthly data
        try:
            metric = BaseESGMetric.objects.get(pk=metric_id)
            real_instance = metric.get_real_instance()
            is_time_series_metric = isinstance(real_instance, (VehicleTrackingMetric, TimeSeriesMetric, MultiFieldTimeSeriesMetric))
            print(f"[DEBUG] Metric {metric_id} is a time series metric: {is_time_series_metric}")
        except:
            is_time_series_metric = False
            print(f"[DEBUG] Could not determine if metric {metric_id} is a time series metric, assuming it is not")
        
        # For annual aggregation level - handle like before
        try:
            level = 'A'
            annual_period = reporting_period.replace(month=12, day=31)
            rpv = ReportedMetricValue.objects.get(
                assignment_id=assignment_id,
                metric_id=metric_id,
                layer_id=layer_id,
                reporting_period=annual_period,
                level=level
            )
            
            # Count remaining submissions that should contribute
            remaining_submissions = ESGMetricSubmission.objects.filter(
                assignment_id=assignment_id,
                metric_id=metric_id,
                layer_id=layer_id
            ).count()
            
            print(f"[DEBUG] Found Annual ReportedMetricValue {rpv.pk} with {remaining_submissions} remaining submissions")
            
            # If no submissions left, delete the ReportedMetricValue
            if remaining_submissions == 0:
                print(f"[DEBUG] Deleting orphaned Annual ReportedMetricValue {rpv.pk}")
                rpv.delete()
                logger.info(f"Deleted orphaned Annual ReportedMetricValue {rpv.pk}")
            else:
                # Otherwise trigger recalculation
                from .services.aggregation import calculate_report_value
                print(f"[DEBUG] Recalculating Annual ReportedMetricValue {rpv.pk}")
                calculate_report_value(
                    assignment=rpv.assignment,
                    metric=rpv.metric,
                    reporting_period=rpv.reporting_period,
                    layer=rpv.layer,
                    level=rpv.level
                )
        except ReportedMetricValue.DoesNotExist:
            print(f"[DEBUG] No Annual ReportedMetricValue found")
        except Exception as e:
            logger.error(f"Error checking Annual ReportedMetricValue: {e}")
            print(f"[DEBUG] Error processing Annual records: {str(e)}")
        
        # For monthly aggregation level - special handling for time series metrics
        if is_time_series_metric:
            level = 'M'
            year = reporting_period.year
            
            # For time series metrics, check all months in the year
            print(f"[DEBUG] Checking all monthly records for time series metric in year {year}")
            
            # Find all monthly reports for this year, metric, assignment, and layer
            monthly_rpvs = ReportedMetricValue.objects.filter(
                assignment_id=assignment_id,
                metric_id=metric_id,
                layer_id=layer_id,
                reporting_period__year=year,
                level=level
            )
            
            print(f"[DEBUG] Found {monthly_rpvs.count()} monthly ReportedMetricValue records for year {year}")
            
            for rpv in monthly_rpvs:
                # For each monthly record, check if we need to delete or recalculate
                month_period = rpv.reporting_period
                print(f"[DEBUG] Processing monthly record for {month_period}")
                
                # Determine if any contributing data remains for this month
                # This has to be handled differently for each metric type
                has_contributing_data = False
                
                if isinstance(real_instance, VehicleTrackingMetric):
                    # Check for vehicle monthly data
                    from .models.submission_data import VehicleRecord, VehicleMonthlyData
                    has_contributing_data = VehicleMonthlyData.objects.filter(
                        vehicle__submission__assignment_id=assignment_id,
                        vehicle__submission__metric_id=metric_id,
                        vehicle__submission__layer_id=layer_id,
                        period__month=month_period.month,
                        period__year=month_period.year
                    ).exists()
                elif isinstance(real_instance, TimeSeriesMetric):
                    # Check for time series data points
                    from .models.submission_data import TimeSeriesDataPoint
                    has_contributing_data = TimeSeriesDataPoint.objects.filter(
                        submission__assignment_id=assignment_id,
                        submission__metric_id=metric_id,
                        submission__layer_id=layer_id,
                        period__month=month_period.month,
                        period__year=month_period.year
                    ).exists()
                elif isinstance(real_instance, MultiFieldTimeSeriesMetric):
                    # Check for multi-field time series data points
                    from .models.submission_data import MultiFieldTimeSeriesDataPoint
                    has_contributing_data = MultiFieldTimeSeriesDataPoint.objects.filter(
                        submission__assignment_id=assignment_id,
                        submission__metric_id=metric_id,
                        submission__layer_id=layer_id,
                        period__month=month_period.month,
                        period__year=month_period.year
                    ).exists()
                
                if not has_contributing_data:
                    print(f"[DEBUG] No data found for {month_period}, deleting ReportedMetricValue {rpv.pk}")
                    rpv.delete()
                    logger.info(f"Deleted orphaned Monthly ReportedMetricValue {rpv.pk} for {month_period}")
                else:
                    # Trigger recalculation for this month
                    from .services.aggregation import calculate_report_value
                    print(f"[DEBUG] Data still exists for {month_period}, recalculating ReportedMetricValue {rpv.pk}")
                    calculate_report_value(
                        assignment=rpv.assignment,
                        metric=rpv.metric,
                        reporting_period=rpv.reporting_period,
                        layer=rpv.layer,
                        level=rpv.level
                    )
        else:
            # For non-time series metrics, handle monthly level like before
            try:
                level = 'M'
                rpv = ReportedMetricValue.objects.get(
                    assignment_id=assignment_id,
                    metric_id=metric_id,
                    layer_id=layer_id,
                    reporting_period=reporting_period,  # Use exact reporting period
                    level=level
                )
                
                # Count remaining submissions that should contribute
                remaining_submissions = ESGMetricSubmission.objects.filter(
                    assignment_id=assignment_id,
                    metric_id=metric_id,
                    layer_id=layer_id
                ).count()
                
                print(f"[DEBUG] Found Monthly ReportedMetricValue {rpv.pk} with {remaining_submissions} remaining submissions")
                
                # If no submissions left, delete the ReportedMetricValue
                if remaining_submissions == 0:
                    print(f"[DEBUG] Deleting orphaned Monthly ReportedMetricValue {rpv.pk}")
                    rpv.delete()
                    logger.info(f"Deleted orphaned Monthly ReportedMetricValue {rpv.pk}")
                else:
                    # Otherwise trigger recalculation
                    from .services.aggregation import calculate_report_value
                    print(f"[DEBUG] Recalculating Monthly ReportedMetricValue {rpv.pk}")
                    calculate_report_value(
                        assignment=rpv.assignment,
                        metric=rpv.metric,
                        reporting_period=rpv.reporting_period,
                        layer=rpv.layer,
                        level=rpv.level
                    )
            except ReportedMetricValue.DoesNotExist:
                print(f"[DEBUG] No Monthly ReportedMetricValue found for the given context")
            except Exception as e:
                logger.error(f"Error checking Monthly ReportedMetricValue: {e}")
                print(f"[DEBUG] Error: {str(e)}")
    except Exception as e:
        logger.error(f"Error cleaning up orphaned ReportedMetricValue records: {e}")
        print(f"[DEBUG] Error in cleanup: {str(e)}")

@receiver(post_save, sender=ReportedMetricValue)
def trigger_emission_calculation(sender, instance, **kwargs):
    """
    When a ReportedMetricValue is saved, trigger emission calculation if the metric
    has emission categories configured.
    """
    logger.info(f"[SIGNAL] trigger_emission_calculation called for RPV {instance.pk}") # Log signal start
    
    # Skip if this is a new record and has no numeric value
    if kwargs.get('created', False) and instance.aggregated_numeric_value is None:
        logger.info(f"[SIGNAL] Skipping emission trigger for new RPV {instance.pk} - no numeric value")
        return
        
    # This check might be too strict for VehicleTrackingMetric, but log anyway
    if not instance.metric.emission_category or not instance.metric.emission_sub_category:
        logger.info(f"[SIGNAL] RPV {instance.pk} metric lacks emission category/subcategory. Relying on VehicleTrackingMetric exception later if applicable.")
        # Don't return here for now, let the main function handle the VehicleTrackingMetric exception
        # return
        
    def run_emission_calculation():
        logger.info(f"[SIGNAL-ONCOMMIT] Running emission calculation logic for RPV {instance.pk}") # Log on_commit start
        try:
            # Fetch the instance again to ensure it's up-to-date after commit
            latest_instance = ReportedMetricValue.objects.get(pk=instance.pk)
            results = calculate_emissions_for_activity_value(latest_instance)
            if results:
                logger.info(f"[SIGNAL-ONCOMMIT] Emission calculation successful for RPV {latest_instance.pk}. {len(results)} records created/updated.")
            else:
                logger.info(f"[SIGNAL-ONCOMMIT] Emission calculation did not produce results for RPV {latest_instance.pk}. Check logs from calculate_emissions_for_activity_value.")
        except ReportedMetricValue.DoesNotExist:
            logger.error(f"[SIGNAL-ONCOMMIT] RPV {instance.pk} not found after commit. Cannot calculate emissions.")
        except Exception as e:
            logger.error(f"[SIGNAL-ONCOMMIT] Error during emission calculation for RPV {instance.pk}: {e}", exc_info=True)
            
    # Schedule the calculation after the transaction commits
    logger.info(f"[SIGNAL] Scheduling run_emission_calculation via on_commit for RPV {instance.pk}")
    transaction.on_commit(run_emission_calculation)

# Optional: Handle potential errors in the main signal handler if needed,
# though most work is now deferred.
# Removed the outer try/except block as the main logic is deferred. 