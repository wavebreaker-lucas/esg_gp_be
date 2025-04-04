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
    ESGForm, ESGMetric,
    Template, TemplateFormSelection, TemplateAssignment
)
from ...models.templates import ESGMetricSubmission, ESGMetricEvidence
from ...serializers.templates import (
    ESGFormSerializer, ESGMetricSerializer, ESGMetricEvidenceSerializer
)
from ..utils import get_required_submission_count, attach_evidence_to_submissions


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
        """Get metrics for a specific form"""
        form = self.get_object()
        metrics = form.metrics.all()
        serializer = ESGMetricSerializer(metrics, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, BakerTillyAdmin])
    def add_metric(self, request, pk=None):
        """Add a new metric to the form"""
        form = self.get_object()
        
        # Create serializer with the form already set
        serializer = ESGMetricSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(form=form)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['get'])
    def check_completion(self, request, pk=None):
        """
        Check if a form is completed for a specific assignment.
        This endpoint returns the completion status, missing metrics,
        and completion percentage for the form.
        
        Even if a form is already marked as completed, this will still
        perform validation to check if it meets current requirements.
        """
        form = self.get_object()
        assignment_id = request.query_params.get('assignment_id')
        
        if not assignment_id:
            return Response(
                {"error": "assignment_id query parameter is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        try:
            # Get the assignment
            assignment = TemplateAssignment.objects.get(id=assignment_id)
            
            # Find the form selection for this form in the template
            try:
                form_selection = TemplateFormSelection.objects.get(
                    template=assignment.template,
                    form=form
                )
                
                # Store whether the form is officially marked as completed
                is_completed = form_selection.is_completed
                completed_at = form_selection.completed_at
                completed_by = form_selection.completed_by.email if form_selection.completed_by else None
                
                # Get all required metrics for this form that apply to the selected regions
                required_metrics = []
                time_based_metrics = []
                for metric in form.metrics.filter(is_required=True):
                    if metric.location == 'ALL' or metric.location in form_selection.regions:
                        required_metrics.append(metric.id)
                        if metric.requires_time_reporting:
                            time_based_metrics.append(metric.id)
                        
                # Get submitted metrics for this form
                submissions = ESGMetricSubmission.objects.filter(
                    assignment=assignment,
                    metric__form=form
                )
                submitted_metrics = submissions.values_list('metric_id', flat=True)
                
                # For time-based metrics, check if we have the required number of submissions
                time_based_status = {}
                for metric_id in time_based_metrics:
                    metric = ESGMetric.objects.get(id=metric_id)
                    submissions_count = submissions.filter(metric=metric).count()
                    required_count = get_required_submission_count(metric, assignment)
                    time_based_status[metric_id] = {
                        "submitted_count": submissions_count,
                        "required_count": required_count,
                        "is_complete": submissions_count >= required_count
                    }
                
                # Calculate completion percentage for non-time-based metrics
                regular_metrics = set(required_metrics) - set(time_based_metrics)
                total_regular = len(regular_metrics)
                submitted_regular = len(set(regular_metrics) & set(submitted_metrics))
                
                # Calculate completion for time-based metrics
                total_time_based = sum(status["required_count"] for status in time_based_status.values())
                submitted_time_based = sum(min(status["submitted_count"], status["required_count"]) 
                                          for status in time_based_status.values())
                
                # Calculate overall completion percentage
                total_required = total_regular + total_time_based
                total_submitted = submitted_regular + submitted_time_based
                
                completion_percentage = 0
                if total_required > 0:
                    completion_percentage = (total_submitted / total_required) * 100
                    
                # Get missing regular metrics if any
                missing_regular_metrics = []
                if submitted_regular < total_regular:
                    missing_metric_ids = set(regular_metrics) - set(submitted_metrics)
                    missing_regular_metrics = ESGMetric.objects.filter(
                        id__in=missing_metric_ids
                    ).values('id', 'name', 'location')
                
                # Get incomplete time-based metrics
                incomplete_time_based = []
                for metric_id, status in time_based_status.items():
                    if not status["is_complete"]:
                        metric = ESGMetric.objects.get(id=metric_id)
                        incomplete_time_based.append({
                            'id': metric.id,
                            'name': metric.name,
                            'location': metric.location,
                            'reporting_frequency': metric.reporting_frequency,
                            'submitted_count': status["submitted_count"],
                            'required_count': status["required_count"]
                        })
                
                # Check if all required metrics are submitted but form isn't marked complete
                all_regular_complete = submitted_regular == total_regular
                all_time_based_complete = all(status["is_complete"] for status in time_based_status.values())
                is_actually_complete = total_required > 0 and all_regular_complete and all_time_based_complete
                can_complete = is_actually_complete
                
                # Check if the form status is inconsistent (marked complete but not actually complete)
                status_inconsistent = is_completed and not is_actually_complete
                
                return Response({
                    "form_id": form.id,
                    "form_name": form.name,
                    "form_code": form.code,
                    "is_completed": is_completed,  # Whether the form is marked as completed in the DB
                    "is_actually_complete": is_actually_complete,  # Whether it meets current requirements
                    "status_inconsistent": status_inconsistent,  # Flag for frontend to show warnings
                    "completed_at": completed_at if is_completed else None,
                    "completed_by": completed_by if is_completed else None,
                    "completion_percentage": completion_percentage,
                    "total_required_metrics": len(required_metrics),
                    "total_submitted_metrics": len(set(submitted_metrics) & set(required_metrics)),
                    "missing_regular_metrics": list(missing_regular_metrics),
                    "incomplete_time_based_metrics": incomplete_time_based,
                    "can_complete": can_complete
                })
                
            except TemplateFormSelection.DoesNotExist:
                return Response(
                    {"error": "This form is not part of the template"},
                    status=status.HTTP_400_BAD_REQUEST
                )
                
        except TemplateAssignment.DoesNotExist:
            return Response(
                {"error": "Template assignment not found"},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=True, methods=['post'])
    @transaction.atomic
    def complete_form(self, request, pk=None):
        """
        Mark a form as completed for a specific template assignment.
        This is called when all required metrics for this form have been submitted.
        
        POST parameters:
        - assignment_id: The ID of the template assignment
        - revalidate: (Optional) If true, a form that was previously marked complete
                     but doesn't meet current requirements will be updated
        """
        form = self.get_object()
        assignment_id = request.data.get('assignment_id')
        revalidate = request.data.get('revalidate', False)
        
        if not assignment_id:
            return Response(
                {"error": "assignment_id is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        try:
            # Get the assignment
            assignment = TemplateAssignment.objects.get(id=assignment_id)
            
            # Check if user has access to this assignment
            user_app_users = AppUser.objects.filter(user=request.user).select_related('layer')
            user_layers = [app_user.layer.id for app_user in user_app_users]
            
            # Also check parent layers
            for app_user in user_app_users:
                layer = app_user.layer
                if hasattr(layer, 'branchlayer'):
                    user_layers.append(layer.branchlayer.subsidiary_layer.id)
                    user_layers.append(layer.branchlayer.subsidiary_layer.group_layer.id)
                elif hasattr(layer, 'subsidiarylayer'):
                    user_layers.append(layer.subsidiarylayer.group_layer.id)
            
            if assignment.layer.id not in user_layers:
                return Response(
                    {"error": "You do not have access to this template assignment"},
                    status=status.HTTP_403_FORBIDDEN
                )
                
            # Find the form selection for this form in the template
            try:
                form_selection = TemplateFormSelection.objects.get(
                    template=assignment.template,
                    form=form
                )
                
                # If the form is already completed and we're not revalidating, just return success
                if form_selection.is_completed and not revalidate:
                    return Response({
                        "message": "Form is already completed",
                        "form_id": form.id,
                        "form_name": form.name,
                        "form_code": form.code,
                        "is_completed": True,
                        "completed_at": form_selection.completed_at,
                        "completed_by": form_selection.completed_by.email if form_selection.completed_by else None
                    })
                
            except TemplateFormSelection.DoesNotExist:
                return Response(
                    {"error": "This form is not part of the template"},
                    status=status.HTTP_400_BAD_REQUEST
                )
                
            # Get all required metrics for this form that apply to the selected regions
            required_metrics = []
            time_based_metrics = []
            for metric in form.metrics.filter(is_required=True):
                if metric.location == 'ALL' or metric.location in form_selection.regions:
                    required_metrics.append(metric.id)
                    if metric.requires_time_reporting:
                        time_based_metrics.append(metric)
                    
            # Check if all required metrics have submissions
            submissions = ESGMetricSubmission.objects.filter(
                assignment=assignment,
                metric__form=form
            )
            submitted_metrics = submissions.values_list('metric_id', flat=True)
            
            # Check regular (non-time-based) metrics
            regular_metrics = set(required_metrics) - set(m.id for m in time_based_metrics)
            missing_regular = set(regular_metrics) - set(submitted_metrics)
            
            if missing_regular:
                # Get names of missing regular metrics for better error message
                missing_metric_names = ESGMetric.objects.filter(
                    id__in=missing_regular
                ).values_list('name', flat=True)
                
                return Response({
                    "error": "Cannot complete form with missing required metrics",
                    "missing_metrics": list(missing_metric_names)
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Check time-based metrics
            incomplete_time_based = []
            for metric in time_based_metrics:
                submissions_count = submissions.filter(metric=metric).count()
                required_count = get_required_submission_count(metric, assignment)
                
                if submissions_count < required_count:
                    incomplete_time_based.append({
                        'id': metric.id,
                        'name': metric.name,
                        'reporting_frequency': metric.reporting_frequency,
                        'submitted_count': submissions_count,
                        'required_count': required_count
                    })
            
            if incomplete_time_based:
                return Response({
                    "error": "Cannot complete form with incomplete time-based metrics",
                    "incomplete_time_based_metrics": incomplete_time_based
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Automatically attach evidence files related to this form's submissions
            evidence_count = attach_evidence_to_submissions(list(submissions), request.user)
                
            # Mark the form as completed
            was_already_completed = form_selection.is_completed
            form_selection.is_completed = True
            form_selection.completed_at = timezone.now()
            form_selection.completed_by = request.user
            form_selection.save()
            
            # Check if all forms in the template are completed
            all_forms_completed = all(
                selection.is_completed 
                for selection in assignment.template.templateformselection_set.all()
            )
            
            # If all forms are completed, update the assignment status
            if all_forms_completed and assignment.status != 'SUBMITTED':
                assignment.status = 'SUBMITTED'
                assignment.completed_at = timezone.now()
                assignment.save()
                
            return Response({
                "message": "Form successfully completed" if not was_already_completed else "Form successfully revalidated",
                "form_id": form.id,
                "form_name": form.name,
                "form_code": form.code,
                "evidence_attached": evidence_count,
                "all_forms_completed": all_forms_completed,
                "assignment_status": assignment.status,
                "was_revalidated": was_already_completed and revalidate
            })
            
        except TemplateAssignment.DoesNotExist:
            return Response(
                {"error": "Template assignment not found"},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, BakerTillyAdmin])
    @transaction.atomic
    def uncomplete_form(self, request, pk=None):
        """
        Mark a form as incomplete for a specific template assignment.
        Only Baker Tilly admins can uncomplete forms.
        
        POST parameters:
        - assignment_id: The ID of the template assignment
        """
        form = self.get_object()
        assignment_id = request.data.get('assignment_id')
        
        if not assignment_id:
            return Response(
                {"error": "assignment_id is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        try:
            # Get the assignment
            assignment = TemplateAssignment.objects.get(id=assignment_id)
            
            # Find the form selection for this form in the template
            try:
                form_selection = TemplateFormSelection.objects.get(
                    template=assignment.template,
                    form=form
                )
                
                # If the form is not completed, just return success
                if not form_selection.is_completed:
                    return Response({
                        "message": "Form is already marked as incomplete",
                        "form_id": form.id,
                        "form_name": form.name,
                        "form_code": form.code,
                        "is_completed": False
                    })
                
                # Mark the form as incomplete
                form_selection.is_completed = False
                form_selection.completed_at = None
                form_selection.completed_by = None
                form_selection.save()
                
                # Since a form is now incomplete, the assignment can't be in SUBMITTED status
                if assignment.status == 'SUBMITTED':
                    assignment.status = 'IN_PROGRESS'
                    assignment.completed_at = None
                    assignment.save()
                
                return Response({
                    "message": "Form successfully marked as incomplete",
                    "form_id": form.id,
                    "form_name": form.name,
                    "form_code": form.code,
                    "assignment_status": assignment.status
                })
                
            except TemplateFormSelection.DoesNotExist:
                return Response(
                    {"error": "This form is not part of the template"},
                    status=status.HTTP_400_BAD_REQUEST
                )
                
        except TemplateAssignment.DoesNotExist:
            return Response(
                {"error": "Template assignment not found"},
                status=status.HTTP_404_NOT_FOUND
            ) 