"""
Views for managing ESG forms.
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db import transaction
from django.utils import timezone

from accounts.permissions import BakerTillyAdmin
from accounts.models import CustomUser, AppUser, LayerProfile
from accounts.services import get_accessible_layers, has_layer_access
from ...models import (
    ESGForm,
    Template, TemplateFormSelection, TemplateAssignment,
    ReportedMetricValue
)
from ...models.polymorphic_metrics import BaseESGMetric
from ...serializers.templates import (
    ESGFormSerializer, ESGMetricEvidenceSerializer
)
from ...serializers import ESGMetricPolymorphicSerializer


class ESGFormViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing ESG forms. 
    Baker Tilly admins can create, update, and delete forms.
    Other users can only view forms.
    """
    queryset = ESGForm.objects.filter(is_active=True)
    serializer_class = ESGFormSerializer
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        """
        Only Baker Tilly admins can create, update, or delete forms.
        All authenticated users can view forms.
        """
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAuthenticated(), BakerTillyAdmin()]
        return [IsAuthenticated()]

    def perform_create(self, serializer):
        """Create a new ESG form"""
        serializer.save()

    @action(detail=True, methods=['get'])
    def metrics(self, request, pk=None):
        """Get polymorphic metrics for a specific form"""
        form = self.get_object()
        metrics = form.polymorphic_metrics.all().order_by('order')
        serializer = ESGMetricPolymorphicSerializer(metrics, many=True, context={'request': request})
        return Response(serializer.data)

    # Commenting out actions heavily dependent on the old metric structure
    # These will need to be redesigned in Phase 4/5

    @action(detail=True, methods=['get'])
    def check_completion(self, request, pk=None):
        """
        Check if a form's required metrics have aggregated values for a specific assignment.
        Defines completion based on the existence of ReportedMetricValue records.
        """
        form = self.get_object()
        assignment_id = request.query_params.get('assignment_id')
        if not assignment_id:
            return Response({"error": "assignment_id query parameter is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Eager load related fields needed for checks
            assignment = TemplateAssignment.objects.select_related('layer', 'template').get(pk=assignment_id)
        except TemplateAssignment.DoesNotExist:
            return Response({"error": "Assignment not found."}, status=status.HTTP_404_NOT_FOUND)

        # Check user access to the assignment's layer
        if not has_layer_access(request.user, assignment.layer_id):
             return Response({"detail": "You do not have permission for this assignment's layer."}, status=status.HTTP_403_FORBIDDEN)

        # Get all required metrics for this form using the correct related_name
        required_metrics = form.polymorphic_metrics.filter(is_required=True)
        
        total_required_points = 0 # Can represent metrics or metric-periods
        reported_points_count = 0
        missing_final_values = []

        # --- Period Calculation Logic --- 
        # TODO: Refine this logic significantly based on actual requirements
        # This simplified version assumes non-timeseries metrics need one value for the assignment period,
        # and timeseries need one value per month within the assignment period.
        assignment_start = assignment.reporting_period_start
        assignment_end = assignment.reporting_period_end
        
        # Helper function (could be moved to a service)
        def calculate_expected_periods(metric, start_date, end_date):
            if hasattr(metric, 'frequency'): # Check for TimeSeriesMetric, MultiFieldTimeSeriesMetric
                freq = metric.frequency
                if freq == 'monthly':
                    periods = []
                    current_date = start_date
                    while current_date <= end_date:
                        # Assuming monthly means end-of-month reporting
                        import calendar
                        last_day = calendar.monthrange(current_date.year, current_date.month)[1]
                        periods.append(current_date.replace(day=last_day))
                        # Move to the first day of the next month
                        if current_date.month == 12:
                             current_date = current_date.replace(year=current_date.year + 1, month=1, day=1)
                        else:
                             current_date = current_date.replace(month=current_date.month + 1, day=1)
                    return periods
                # TODO: Implement weekly, quarterly, daily if needed
                elif freq == 'annual':
                     return [end_date]
                else: # Default for unknown frequencies or other time-based
                     return [end_date] 
            else: # Not a time-series metric
                 return [end_date] # Expect one value for the end period

        # --- Check each required metric --- 
        for metric in required_metrics.iterator():
            # Fetch the specific instance to check its type
            specific_metric = metric.get_real_instance()
            
            expected_periods_dates = calculate_expected_periods(specific_metric, assignment_start, assignment_end)
            expected_periods_count = len(expected_periods_dates)
            
            if expected_periods_count == 0:
                continue # Skip if no periods are expected
            
            total_required_points += expected_periods_count

            # Check how many ReportedMetricValue exist for the expected periods
            # Ensure we query using the base metric ID
            found_periods_count = ReportedMetricValue.objects.filter(
                assignment=assignment,
                metric_id=metric.id, # Query by base metric ID 
                layer=assignment.layer, 
                reporting_period__in=expected_periods_dates
            ).count()
            
            reported_points_count += found_periods_count

            if found_periods_count < expected_periods_count:
                # Find which specific periods are missing 
                found_periods = set(ReportedMetricValue.objects.filter(
                    assignment=assignment,
                    metric_id=metric.id, 
                    layer=assignment.layer, 
                    reporting_period__in=expected_periods_dates
                ).values_list('reporting_period', flat=True))
                
                missing_periods = [d.isoformat() for d in expected_periods_dates if d not in found_periods]
                
                missing_final_values.append({
                    "metric_id": metric.pk,
                    "metric_name": metric.name,
                    "location": metric.location, 
                    "expected_periods_count": expected_periods_count,
                    "found_periods_count": found_periods_count,
                    "missing_periods": missing_periods
                })

        completion_percentage = (reported_points_count / total_required_points * 100) if total_required_points > 0 else 100
        is_actually_complete = reported_points_count == total_required_points and total_required_points > 0 # Must have requirements to be complete

        # Check against the stored completion flag from TemplateFormSelection
        try:
            selection = TemplateFormSelection.objects.get(template=assignment.template, form=form)
            is_marked_complete = selection.is_completed
            completed_at = selection.completed_at
            completed_by_email = selection.completed_by.email if selection.completed_by else None
        except TemplateFormSelection.DoesNotExist:
            # If no selection exists, it implies the form hasn't been marked completed
            is_marked_complete = False
            completed_at = None
            completed_by_email = None
            
        status_inconsistent = is_marked_complete and not is_actually_complete

        return Response({
            "form_id": form.pk,
            "form_name": form.name,
            "form_code": form.code,
            "assignment_id": assignment.pk,
            "is_completed": is_marked_complete, # Status stored in DB
            "is_actually_complete": is_actually_complete, # Status based on current check
            "status_inconsistent": status_inconsistent,
            "completed_at": completed_at,
            "completed_by": completed_by_email,
            "completion_percentage": round(completion_percentage, 2),
            "total_required_points": total_required_points, # Total metrics or metric-periods
            "reported_points_count": reported_points_count, # Count of metrics/periods with ReportedMetricValue
            "missing_final_reported_values": missing_final_values,
            "can_complete": is_actually_complete # Can only press 'complete' if requirements met
        })

    @action(detail=True, methods=['post'])
    @transaction.atomic
    def complete_form(self, request, pk=None):
        """
        Mark a form as completed for a specific template assignment, 
        if all required metrics have aggregated ReportedMetricValue records.
        Allows revalidation via 'revalidate=true' parameter.
        """
        form = self.get_object()
        assignment_id = request.data.get('assignment_id')
        revalidate = request.data.get('revalidate') == True # Optional flag
        
        if not assignment_id:
            return Response({"error": "assignment_id is required in the request body."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            assignment = TemplateAssignment.objects.select_related('template', 'layer').get(pk=assignment_id)
        except TemplateAssignment.DoesNotExist:
            return Response({"error": "Assignment not found."}, status=status.HTTP_404_NOT_FOUND)
            
        # Check user access to the assignment's layer
        if not has_layer_access(request.user, assignment.layer_id):
             return Response({"detail": "You do not have permission for this assignment's layer."}, status=status.HTTP_403_FORBIDDEN)

        # --- Replicate check_completion logic --- 
        # (Alternatively, call it internally if performance allows)
        required_metrics = form.polymorphic_metrics.filter(is_required=True)
        total_required_points = 0
        reported_points_count = 0
        assignment_start = assignment.reporting_period_start
        assignment_end = assignment.reporting_period_end
        all_requirements_met = True

        # Helper function (same as in check_completion - refactor potential)
        def calculate_expected_periods(metric, start_date, end_date):
            if hasattr(metric, 'frequency'):
                freq = metric.frequency
                if freq == 'monthly':
                    periods = []
                    current_date = start_date
                    while current_date <= end_date:
                        import calendar
                        last_day = calendar.monthrange(current_date.year, current_date.month)[1]
                        periods.append(current_date.replace(day=last_day))
                        if current_date.month == 12:
                             current_date = current_date.replace(year=current_date.year + 1, month=1, day=1)
                        else:
                             current_date = current_date.replace(month=current_date.month + 1, day=1)
                    return periods
                elif freq == 'annual': return [end_date]
                else: return [end_date] 
            else: return [end_date]

        if not required_metrics.exists():
             all_requirements_met = True # Form with no required metrics is complete by default?
        else:
            for metric in required_metrics.iterator():
                specific_metric = metric.get_real_instance()
                expected_periods_dates = calculate_expected_periods(specific_metric, assignment_start, assignment_end)
                expected_periods_count = len(expected_periods_dates)
                
                if expected_periods_count == 0: continue
                total_required_points += expected_periods_count
                
                found_periods_count = ReportedMetricValue.objects.filter(
                    assignment=assignment,
                    metric_id=metric.id,
                    layer=assignment.layer, 
                    reporting_period__in=expected_periods_dates
                ).count()
                reported_points_count += found_periods_count
                
                if found_periods_count < expected_periods_count:
                    all_requirements_met = False
                    # If just completing (not revalidating), we can stop checking early
                    if not revalidate: 
                       break 
        
        # Determine actual completeness based on checks
        is_actually_complete = all_requirements_met and total_required_points > 0
        if total_required_points == 0 and required_metrics.exists():
            # Edge case: required metrics exist but generate 0 expected periods? Treat as incomplete?
            is_actually_complete = False 
        elif total_required_points == 0 and not required_metrics.exists():
            # No required metrics -> complete by default
            is_actually_complete = True
            
        # Handle completion/revalidation attempt
        if not is_actually_complete and not revalidate:
             # Trying to mark as complete, but requirements not met.
             # Call check_completion to get detailed error response?
             check_response = self.check_completion(request._request, pk=pk) # Pass internal request object
             return Response(
                 {"error": "Cannot complete form. Requirements not met.", "details": check_response.data.get('missing_final_reported_values')},
                 status=status.HTTP_400_BAD_REQUEST
             )
                 
        # Find or create the TemplateFormSelection entry
        # Need to handle potential IntegrityError if created concurrently?
        selection, created = TemplateFormSelection.objects.get_or_create(
            template=assignment.template,
            form=form,
            defaults={'order': form.order} # Set default order if creating
        )

        response_message = ""
        status_changed = False

        if is_actually_complete:
            if not selection.is_completed:
                selection.is_completed = True
                selection.completed_at = timezone.now()
                selection.completed_by = request.user
                selection.save()
                status_changed = True
                response_message = f"Form '{form.name}' successfully marked as completed."
                if revalidate: response_message = f"Form '{form.name}' successfully revalidated and marked as completed."
            else:
                # Already marked complete and requirements met
                response_message = f"Form '{form.name}' is already marked as complete and meets requirements."
                if revalidate: response_message = f"Form '{form.name}' revalidated and confirmed complete."
        else: # Requirements not met (only reachable if revalidate=True)
            if selection.is_completed:
                 # Was marked complete, but no longer meets requirements
                selection.is_completed = False
                selection.completed_at = None
                selection.completed_by = None
                selection.save()
                status_changed = True
                response_message = f"Form '{form.name}' marked as incomplete because requirements are no longer met."
            else: # Not actually complete, and not marked complete 
                 response_message = f"Form '{form.name}' revalidated and confirmed incomplete."

        # --- Check overall assignment completion --- 
        # Check if *all* forms associated with the template *in this assignment context* are complete
        all_forms_in_template_ids = TemplateFormSelection.objects.filter(template=assignment.template).values_list('form_id', flat=True)
        
        # Check completion status based on the updated selection states
        # We only care about forms actually part of this template
        all_forms_complete = not TemplateFormSelection.objects.filter(
            template=assignment.template, 
            form_id__in=all_forms_in_template_ids, # Ensure we only check forms in this template
            # form__polymorphic_metrics__is_required=True, # This check might be too complex/slow here
            is_completed=False
        ).exists()
        
        assignment_status_updated = False
        if all_forms_complete:
            # Check if all required *metrics* across all forms have ReportedMetricValue
            # This is a more robust check than just the flags
            # Requires iterating through all forms/metrics again - potentially heavy
            # Simplified check: If all flags are true, mark as SUBMITTED
            if assignment.status != 'SUBMITTED': # Only update if not already submitted/verified etc.
                 assignment.status = 'SUBMITTED'
                 assignment.completed_at = timezone.now() # Or use latest form completion time?
                 assignment.save(update_fields=['status', 'completed_at'])
                 assignment_status_updated = True
        elif status_changed and not selection.is_completed: # If this action made a form incomplete
             if assignment.status in ['SUBMITTED', 'VERIFIED']: # Revert assignment status if needed
                 assignment.status = 'IN_PROGRESS'
                 assignment.completed_at = None
                 assignment.save(update_fields=['status', 'completed_at'])
                 assignment_status_updated = True

        return Response({
            "message": response_message,
            "form_id": form.pk,
            "form_is_complete": selection.is_completed,
            "assignment_status_updated": assignment_status_updated,
            "assignment_status": assignment.get_status_display()
        })

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, BakerTillyAdmin])
    @transaction.atomic
    def uncomplete_form(self, request, pk=None):
        """
        Mark a form as not completed for a specific template assignment (Admin only).
        """
        form = self.get_object()
        assignment_id = request.data.get('assignment_id')
        if not assignment_id:
            return Response({"error": "assignment_id is required in the request body."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            assignment = TemplateAssignment.objects.select_related('template').get(pk=assignment_id)
            selection = TemplateFormSelection.objects.get(template=assignment.template, form=form)
        except TemplateAssignment.DoesNotExist:
            return Response({"error": "Assignment not found."}, status=status.HTTP_404_NOT_FOUND)
        except TemplateFormSelection.DoesNotExist:
             # If selection doesn't exist, it's already effectively incomplete
             return Response({"message": "Form was already considered incomplete (no selection record)."})

        if selection.is_completed:
            selection.is_completed = False
            selection.completed_at = None
            selection.completed_by = None
            selection.save()
            
            # Revert assignment status if needed
            if assignment.status in ['SUBMITTED', 'VERIFIED']:
                assignment.status = 'IN_PROGRESS'
                assignment.completed_at = None
                assignment.save(update_fields=['status', 'completed_at'])
                
            return Response({
                "message": f"Form '{form.name}' successfully marked as incomplete.",
                "assignment_status": assignment.get_status_display()
            })
        else:
            return Response({"message": f"Form '{form.name}' was already incomplete."}) 

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, BakerTillyAdmin])
    def add_metric(self, request, pk=None):
        """Add a new polymorphic metric to this form."""
        form = self.get_object() # Get the target form
        
        # Prepare data for the serializer
        metric_data = request.data.copy()
        metric_data['form'] = form.pk # Ensure the form FK is set

        # Use the polymorphic serializer to create the metric
        # The request data MUST include 'metric_subtype' (or whatever resource_type_field_name is set to)
        # to determine which specific metric model/serializer to use.
        serializer = ESGMetricPolymorphicSerializer(data=metric_data, context={'request': request})
        
        if serializer.is_valid():
            serializer.save() # This creates the correct subclass instance
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)