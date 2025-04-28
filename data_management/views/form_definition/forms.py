"""
Views for managing ESG forms.
"""

from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db import transaction
from django.utils import timezone
from django.db.models import Count

from accounts.permissions import BakerTillyAdmin
from accounts.models import CustomUser, AppUser, LayerProfile
from accounts.services import get_accessible_layers, has_layer_access
from ...models import (
    ESGForm,
    Template, TemplateFormSelection, TemplateAssignment,
    ReportedMetricValue, FormCompletionStatus
)
from ...models.polymorphic_metrics import BaseESGMetric
from ...serializers.templates import (
    ESGFormSerializer, ESGFormDetailSerializer
)
from ...serializers import ESGMetricPolymorphicSerializer


class ESGFormViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing ESG forms. 
    Baker Tilly admins can create, update, and delete forms.
    Other users can only view forms.
    """
    queryset = ESGForm.objects.select_related('category').all().order_by('category__order', 'order')
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        """Return appropriate serializer class based on action."""
        if self.action == 'retrieve':
            # Use the detailed serializer when fetching a single form instance
            return ESGFormDetailSerializer
        # Use the basic serializer for list, create, update, etc.
        return ESGFormSerializer

    def get_queryset(self):
        """Optimize queryset based on action."""
        # Start with the base queryset defined for the class
        queryset = super().get_queryset()

        if self.action == 'retrieve':
            # For a single form detail view, prefetch the polymorphic metrics
            # Use the correct 'related_name' from BaseESGMetric.form field
            return queryset.prefetch_related('polymorphic_metrics')
        elif self.action == 'list':
            # For the list view, annotate with the count of metrics
            # Use the correct related_name from BaseESGMetric.form
            queryset = queryset.annotate(metric_count=Count('polymorphic_metrics'))
            # No need to prefetch metrics here, just count them.
            # select_related('category') is already in the base queryset.

        # Return the optimized queryset for the current action
        return queryset

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

    @action(detail=True, methods=['get'])
    def check_completion(self, request, pk=None):
        """
        Check if a form is completed for a specific assignment.
        Uses the FormCompletionStatus model to track completion status.
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

        # --- SIMPLIFIED PERMISSION CHECK --- 
        # Check user access to the assignment's layer, BUT bypass for admins
        is_admin = getattr(request.user, 'is_baker_tilly_admin', False)
        if not is_admin: # Only check layer access if user is NOT an admin
            # Call has_layer_access and return immediately if False
            if not has_layer_access(request.user, assignment.layer_id):
                 return Response({"detail": "You do not have permission for this assignment's layer."}, status=status.HTTP_403_FORBIDDEN)
        # If we reach here, access is granted (either admin or passed has_layer_access)
        # --- END SIMPLIFIED CHECK --- 

        # Get the form completion status from the database
        try:
            selection = TemplateFormSelection.objects.get(template=assignment.template, form=form)
            
            # Now get the FormCompletionStatus for this assignment and form
            try:
                form_status = FormCompletionStatus.objects.get(
                    form_selection=selection,
                    assignment=assignment
                )
                is_completed = form_status.is_completed
                completed_at = form_status.completed_at
                completed_by_email = form_status.completed_by.email if form_status.completed_by else None
            except FormCompletionStatus.DoesNotExist:
                # If no status exists, it implies the form hasn't been marked completed
                is_completed = False
                completed_at = None
                completed_by_email = None
                
        except TemplateFormSelection.DoesNotExist:
            # If no selection exists, it implies the form isn't part of the template
            is_completed = False
            completed_at = None
            completed_by_email = None

        return Response({
            "form_id": form.pk,
            "form_name": form.name,
            "form_code": form.code,
            "assignment_id": assignment.pk,
            "is_completed": is_completed,
            "completed_at": completed_at,
            "completed_by": completed_by_email,
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
            # Get the form completion status for this assignment
            form_status = FormCompletionStatus.objects.get(form_selection=selection, assignment=assignment)
        except TemplateAssignment.DoesNotExist:
            return Response({"error": "Assignment not found."}, status=status.HTTP_404_NOT_FOUND)
        except TemplateFormSelection.DoesNotExist:
            # If selection doesn't exist, it's already effectively incomplete
            return Response({"message": "Form was already considered incomplete (no selection record)."})
        except FormCompletionStatus.DoesNotExist:
            # If completion status doesn't exist, it's already effectively incomplete
            return Response({"message": "Form was already considered incomplete (no completion status record)."})

        if form_status.is_completed:
            form_status.is_completed = False
            form_status.completed_at = None
            form_status.completed_by = None
            form_status.save()
            
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
        print(f"--- add_metric called for form ID: {pk} ---") # Log entry
        print(f"Request data: {request.data}") # Log raw request data
        
        form = self.get_object() # Get the target form
        
        # Prepare data for the serializer
        metric_data = request.data.copy()
        # Use 'form_id', which matches the PrimaryKeyRelatedField in specific serializers
        metric_data['form_id'] = form.pk # Ensure the form FK is set using the expected field name
        print(f"Data passed to serializer: {metric_data}") # Log data before serialization

        # Use the polymorphic serializer to create the metric
        # The request data MUST include 'metric_subtype' (or whatever resource_type_field_name is set to)
        # to determine which specific metric model/serializer to use.
        serializer = ESGMetricPolymorphicSerializer(data=metric_data, context={'request': request})
        
        print("Attempting serializer.is_valid()...") # Log before validation
        if serializer.is_valid():
            print("Serializer IS valid. Attempting save...") # Log success
            try:
                serializer.save() # This creates the correct subclass instance
                print("Save successful.") # Log save success
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            except Exception as e:
                print(f"!!! ERROR DURING SAVE: {type(e).__name__} - {e}") # Log save error
                # Consider logging the full traceback here too for deeper debugging
                import traceback
                traceback.print_exc()
                # Re-raise or return a 500
                return Response({"error": "Internal server error during save.", "detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        else:
            print(f"Serializer IS NOT valid. Errors: {serializer.errors}") # Log the actual errors
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def check_assignment_completion(self, assignment):
        """
        Helper method to check if all forms in an assignment are complete.
        Returns True if all forms have a FormCompletionStatus record with is_completed=True.
        Forms without a FormCompletionStatus record are considered incomplete.
        """
        # Get all form selections for this assignment's template
        template_form_selections = TemplateFormSelection.objects.filter(
            template=assignment.template
        )
        
        # Get count of all forms in the template
        total_forms_count = template_form_selections.count()
        
        if total_forms_count == 0:
            return False  # If no forms in template, it can't be complete
            
        # Count how many forms have been marked as completed
        completed_forms_count = FormCompletionStatus.objects.filter(
            assignment=assignment,
            form_selection__in=template_form_selections,
            is_completed=True
        ).count()
        
        # Assignment is complete only if ALL forms have been marked as completed
        return completed_forms_count == total_forms_count

    @action(detail=True, methods=['post'])
    @transaction.atomic
    def simple_complete_form(self, request, pk=None):
        """
        A simplified form completion endpoint that allows users to directly mark 
        a form as complete or incomplete without validation checks.
        
        Required parameters:
        - assignment_id: ID of the template assignment
        - is_complete: Boolean indicating whether the form should be marked as complete or incomplete
        """
        form = self.get_object()
        assignment_id = request.data.get('assignment_id')
        is_complete = request.data.get('is_complete', True)  # Default to marking complete if not specified
        
        # Validate the assignment_id parameter
        if not assignment_id:
            return Response(
                {"error": "assignment_id is required in the request body."}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Get the assignment
            assignment = TemplateAssignment.objects.select_related('template', 'layer').get(pk=assignment_id)
        except TemplateAssignment.DoesNotExist:
            return Response(
                {"error": "Assignment not found."}, 
                status=status.HTTP_404_NOT_FOUND
            )
            
        # Check user access to the assignment's layer
        if not has_layer_access(request.user, assignment.layer_id):
            return Response(
                {"detail": "You do not have permission for this assignment's layer."}, 
                status=status.HTTP_403_FORBIDDEN
            )
                
        # Find or create the TemplateFormSelection entry
        # This defines which forms are part of the template
        selection, created = TemplateFormSelection.objects.get_or_create(
            template=assignment.template,
            form=form,
            defaults={'order': form.order}  # Set default order if creating
        )

        # Find or create the FormCompletionStatus entry for this assignment
        form_status, status_created = FormCompletionStatus.objects.get_or_create(
            form_selection=selection,
            assignment=assignment,
            defaults={'is_completed': False}
        )

        status_changed = False
        
        # Update the completion status based on user's choice
        if is_complete and not form_status.is_completed:
            form_status.is_completed = True
            form_status.completed_at = timezone.now()
            form_status.completed_by = request.user
            form_status.save()
            status_changed = True
            response_message = f"Form '{form.name}' successfully marked as completed."
        elif not is_complete and form_status.is_completed:
            form_status.is_completed = False
            form_status.completed_at = None
            form_status.completed_by = None
            form_status.save()
            status_changed = True
            response_message = f"Form '{form.name}' successfully marked as incomplete."
        elif is_complete:
            response_message = f"Form '{form.name}' was already complete."
        else:
            response_message = f"Form '{form.name}' was already incomplete."

        # Update assignment status
        assignment_status_updated = False
        
        # If the form was marked as complete, check if all forms in the template are now complete
        if is_complete and status_changed:
            all_forms_complete = self.check_assignment_completion(assignment)
            
            # If all forms are complete, mark the assignment as SUBMITTED
            if all_forms_complete and assignment.status != 'SUBMITTED':
                assignment.status = 'SUBMITTED'
                assignment.completed_at = timezone.now()
                assignment.save(update_fields=['status', 'completed_at'])
                assignment_status_updated = True
        
        # If the form was marked as incomplete, update the assignment status if needed
        elif not is_complete and status_changed:
            if assignment.status in ['SUBMITTED', 'VERIFIED']:
                assignment.status = 'IN_PROGRESS'
                assignment.completed_at = None
                assignment.save(update_fields=['status', 'completed_at'])
                assignment_status_updated = True

        return Response({
            "message": response_message,
            "form_id": form.pk,
            "form_name": form.name,
            "form_is_complete": form_status.is_completed,
            "assignment_status_updated": assignment_status_updated,
            "assignment_status": assignment.get_status_display()
        })