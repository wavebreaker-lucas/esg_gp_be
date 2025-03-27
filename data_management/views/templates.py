from rest_framework import viewsets, views, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db import transaction
from django.utils import timezone
from accounts.permissions import BakerTillyAdmin
from accounts.models import CustomUser, AppUser, LayerProfile
from ..models import (
    ESGFormCategory, ESGForm, ESGMetric,
    Template, TemplateFormSelection, TemplateAssignment
)
from ..models.templates import ESGMetricSubmission, ESGMetricEvidence
from ..serializers.templates import (
    ESGFormCategorySerializer, ESGFormSerializer, ESGMetricSerializer,
    TemplateSerializer, TemplateAssignmentSerializer
)
from ..serializers.esg import (
    ESGMetricSubmissionSerializer, ESGMetricSubmissionCreateSerializer,
    ESGMetricEvidenceSerializer, ESGMetricBatchSubmissionSerializer,
    ESGMetricSubmissionVerifySerializer
)
from rest_framework import serializers
from django.conf import settings
from django.urls import reverse
from django.db import models
from ..services import attach_evidence_to_submissions

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
                
                # Helper function to get required submission count for time-based metrics
                def get_required_submission_count(metric, assignment):
                    if not metric.requires_time_reporting or not metric.reporting_frequency:
                        return 1
                        
                    # For simplicity, use fixed counts based on reporting frequency
                    if metric.reporting_frequency == 'monthly':
                        return 12
                    elif metric.reporting_frequency == 'quarterly':
                        return 4
                    elif metric.reporting_frequency == 'annual':
                        return 1
                    
                    return 1  # Default fallback
                    
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
                
            # Helper function to get required submission count for time-based metrics
            def get_required_submission_count(metric, assignment):
                if not metric.requires_time_reporting or not metric.reporting_frequency:
                    return 1
                    
                # For simplicity, use fixed counts based on reporting frequency
                if metric.reporting_frequency == 'monthly':
                    return 12
                elif metric.reporting_frequency == 'quarterly':
                    return 4
                elif metric.reporting_frequency == 'annual':
                    return 1
                
                return 1  # Default fallback
                
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

class ESGFormCategoryViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing ESG form categories with their associated forms.
    Baker Tilly admins can create, update, and delete categories.
    Other users can only view categories.
    """
    queryset = ESGFormCategory.objects.all()
    serializer_class = ESGFormCategorySerializer
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        """
        Only Baker Tilly admins can create, update, or delete categories.
        All authenticated users can view categories.
        """
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAuthenticated(), BakerTillyAdmin()]
        return [IsAuthenticated()]

    def list(self, request, *args, **kwargs):
        """List all categories with their active forms"""
        categories = self.get_queryset()
        # Prefetch related forms and metrics for performance
        categories = categories.prefetch_related(
            'forms__metrics'
        )
        serializer = self.get_serializer(categories, many=True)
        return Response(serializer.data)

class TemplateViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing templates created from ESG forms.
    """
    queryset = Template.objects.all()
    serializer_class = TemplateSerializer
    permission_classes = [IsAuthenticated, BakerTillyAdmin]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=['get'])
    def preview(self, request, pk=None):
        """Preview a template with all its forms and metrics"""
        template = self.get_object()
        # Update to include form__category in select_related
        form_selections = template.templateformselection_set.select_related('form', 'form__category').prefetch_related('form__metrics')
        
        # Create a flat list of forms with their metrics
        forms_data = []
        for selection in form_selections:
            form_data = {
                'form_id': selection.form.id,
                'form_code': selection.form.code,
                'form_name': selection.form.name,
                'regions': selection.regions,  # Keep the regions info at form level
                # Add category information to match the user-templates endpoint
                'category': {
                    'id': selection.form.category.id,
                    'name': selection.form.category.name,
                    'code': selection.form.category.code,
                    'icon': selection.form.category.icon,
                    'order': selection.form.category.order
                },
                'order': selection.form.order,
                'metrics': []
            }
            
            for metric in selection.form.metrics.all():
                # Only include metrics that match the form's regions or are for ALL locations
                if metric.location == 'ALL' or metric.location in selection.regions:
                    form_data['metrics'].append({
                        'id': metric.id,
                        'name': metric.name,
                        'unit_type': metric.unit_type,
                        'custom_unit': metric.custom_unit,
                        'requires_evidence': metric.requires_evidence,
                        'validation_rules': metric.validation_rules,
                        'location': metric.location,
                        'is_required': metric.is_required,
                        'order': metric.order,
                        'requires_time_reporting': metric.requires_time_reporting,
                        'reporting_frequency': metric.reporting_frequency
                    })
            
            # Sort metrics by order
            form_data['metrics'].sort(key=lambda x: x['order'])
            forms_data.append(form_data)
        
        # Sort forms by their selection order
        forms_data.sort(key=lambda x: next((s.order for s in form_selections if s.form.id == x['form_id']), 0))
        
        return Response({
            'template_id': template.id,
            'template_name': template.name,
            'description': template.description,
            'forms': forms_data
        })

    @action(detail=True, methods=['get'])
    def completion_status(self, request, pk=None):
        """Get the completion status of forms in a template for a specific assignment"""
        template = self.get_object()
        assignment_id = request.query_params.get('assignment_id')
        
        if not assignment_id:
            return Response(
                {"error": "assignment_id query parameter is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        try:
            assignment = TemplateAssignment.objects.get(id=assignment_id, template=template)
        except TemplateAssignment.DoesNotExist:
            return Response(
                {"error": "Template assignment not found"},
                status=status.HTTP_404_NOT_FOUND
            )
            
        # Get all form selections for this template
        form_selections = template.templateformselection_set.select_related('form').all()
        
        # Create a response with completion status for each form
        forms_status = []
        for selection in form_selections:
            # Get all required metrics for this form
            required_metrics = []
            for metric in selection.form.metrics.filter(is_required=True):
                if metric.location == 'ALL' or metric.location in selection.regions:
                    required_metrics.append(metric.id)
                    
            # Get submitted metrics for this form
            submitted_metrics = ESGMetricSubmission.objects.filter(
                assignment=assignment,
                metric__form=selection.form
            ).values_list('metric_id', flat=True)
            
            # Calculate completion percentage
            total_required = len(required_metrics)
            total_submitted = len(set(required_metrics) & set(submitted_metrics))
            
            completion_percentage = 0
            if total_required > 0:
                completion_percentage = (total_submitted / total_required) * 100
                
            # Get missing metrics if any
            missing_metrics = []
            if total_submitted < total_required:
                missing_metric_ids = set(required_metrics) - set(submitted_metrics)
                missing_metrics = ESGMetric.objects.filter(
                    id__in=missing_metric_ids
                ).values('id', 'name')
                
            forms_status.append({
                'form_id': selection.form.id,
                'form_name': selection.form.name,
                'form_code': selection.form.code,
                'is_completed': selection.is_completed,
                'completed_at': selection.completed_at,
                'completed_by': selection.completed_by.email if selection.completed_by else None,
                'total_required_metrics': total_required,
                'total_submitted_metrics': total_submitted,
                'completion_percentage': completion_percentage,
                'missing_metrics': list(missing_metrics)
            })
            
        # Calculate overall completion percentage
        total_forms = len(form_selections)
        completed_forms = sum(1 for selection in form_selections if selection.is_completed)
        
        overall_percentage = 0
        if total_forms > 0:
            overall_percentage = (completed_forms / total_forms) * 100
            
        return Response({
            'assignment_id': assignment.id,
            'template_id': template.id,
            'template_name': template.name,
            'status': assignment.status,
            'due_date': assignment.due_date,
            'completed_at': assignment.completed_at,
            'total_forms': total_forms,
            'completed_forms': completed_forms,
            'overall_completion_percentage': overall_percentage,
            'forms': forms_status
        })

class TemplateAssignmentView(views.APIView):
    """
    API view for managing template assignments to client layers.
    Templates are assigned directly to layers without requiring a specific user.
    Only group layers can have templates assigned to them.
    """
    permission_classes = [IsAuthenticated, BakerTillyAdmin]

    def get(self, request, layer_id):
        """Get all template assignments for a client layer"""
        # Validate that the layer is a group layer
        try:
            layer = LayerProfile.objects.get(id=layer_id)
            if layer.layer_type != 'GROUP':
                return Response(
                    {'error': 'Templates can only be assigned to group layers'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        except LayerProfile.DoesNotExist:
            return Response(
                {'error': 'Layer not found'},
                status=status.HTTP_404_NOT_FOUND
            )
            
        assignments = TemplateAssignment.objects.filter(
            layer_id=layer_id
        ).select_related('template', 'layer', 'assigned_to')
        
        serializer = TemplateAssignmentSerializer(assignments, many=True)
        return Response(serializer.data)

    @transaction.atomic
    def post(self, request, layer_id):
        """Assign a template to a client layer"""
        # Validate that the layer is a group layer
        try:
            layer = LayerProfile.objects.get(id=layer_id)
            if layer.layer_type != 'GROUP':
                return Response(
                    {'error': 'Templates can only be assigned to group layers'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        except LayerProfile.DoesNotExist:
            return Response(
                {'error': 'Layer not found'},
                status=status.HTTP_404_NOT_FOUND
            )
            
        data = {
            **request.data,
            'layer': layer_id
        }
        serializer = TemplateAssignmentSerializer(data=data)
        
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @transaction.atomic
    def delete(self, request, layer_id):
        """Remove a template assignment from a client layer"""
        # Validate that the layer is a group layer
        try:
            layer = LayerProfile.objects.get(id=layer_id)
            if layer.layer_type != 'GROUP':
                return Response(
                    {'error': 'Templates can only be assigned to group layers'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        except LayerProfile.DoesNotExist:
            return Response(
                {'error': 'Layer not found'},
                status=status.HTTP_404_NOT_FOUND
            )
            
        assignment_id = request.data.get('assignment_id')
        try:
            assignment = TemplateAssignment.objects.get(
                id=assignment_id,
                layer_id=layer_id
            )
            assignment.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except TemplateAssignment.DoesNotExist:
            return Response(
                {'error': 'Assignment not found'},
                status=status.HTTP_404_NOT_FOUND
            )

class UserTemplateAssignmentView(views.APIView):
    """
    API view for group users to access templates assigned to their group.
    Also includes templates assigned to parent groups.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, assignment_id=None):
        """
        Get template assignments for the user's groups and parent groups.
        If assignment_id is provided, return details for that specific assignment.
        """
        # Get all layers (groups) the user belongs to
        user_app_users = AppUser.objects.filter(user=request.user).select_related('layer')
        user_layers = [app_user.layer for app_user in user_app_users]
        
        # Get all accessible layer IDs including parent groups
        accessible_layer_ids = set()
        for layer in user_layers:
            # Add the current layer
            accessible_layer_ids.add(layer.id)
            
            # Add parent layers based on layer type
            if hasattr(layer, 'branchlayer'):
                # For branch layer, add subsidiary and group
                subsidiary = layer.branchlayer.subsidiary_layer
                accessible_layer_ids.add(subsidiary.id)
                accessible_layer_ids.add(subsidiary.group_layer.id)
            elif hasattr(layer, 'subsidiarylayer'):
                # For subsidiary layer, add group
                accessible_layer_ids.add(layer.subsidiarylayer.group_layer.id)
        
        if assignment_id:
            # Get specific template assignment
            try:
                assignment = TemplateAssignment.objects.get(
                    id=assignment_id,
                    layer_id__in=accessible_layer_ids
                )
                
                # Get template with forms and metrics
                template = assignment.template
                form_selections = template.templateformselection_set.select_related('form', 'form__category').prefetch_related('form__metrics')
                
                # Create a flat list of forms with their metrics
                forms_data = []
                for selection in form_selections:
                    form_data = {
                        'form_id': selection.form.id,
                        'form_code': selection.form.code,
                        'form_name': selection.form.name,
                        'regions': selection.regions,
                        'category': {
                            'id': selection.form.category.id,
                            'name': selection.form.category.name,
                            'code': selection.form.category.code,
                            'icon': selection.form.category.icon,
                            'order': selection.form.category.order
                        },
                        'order': selection.form.order,
                        'metrics': []
                    }
                    
                    for metric in selection.form.metrics.all():
                        # Only include metrics that match the form's regions or are for ALL locations
                        if metric.location == 'ALL' or metric.location in selection.regions:
                            form_data['metrics'].append({
                                'id': metric.id,
                                'name': metric.name,
                                'unit_type': metric.unit_type,
                                'custom_unit': metric.custom_unit,
                                'requires_evidence': metric.requires_evidence,
                                'validation_rules': metric.validation_rules,
                                'location': metric.location,
                                'is_required': metric.is_required,
                                'order': metric.order,
                                'requires_time_reporting': metric.requires_time_reporting,
                                'reporting_frequency': metric.reporting_frequency
                            })
                    
                    # Sort metrics by order
                    form_data['metrics'].sort(key=lambda x: x['order'])
                    forms_data.append(form_data)
                
                # Sort forms by their selection order
                forms_data.sort(key=lambda x: next((s.order for s in form_selections if s.form.id == x['form_id']), 0))
                
                response_data = {
                    'assignment_id': assignment.id,
                    'template_id': template.id,
                    'template_name': template.name,
                    'layer_id': assignment.layer.id,
                    'layer_name': assignment.layer.company_name,
                    'status': assignment.status,
                    'due_date': assignment.due_date,
                    'reporting_period_start': assignment.reporting_period_start,
                    'reporting_period_end': assignment.reporting_period_end,
                    'reporting_year': assignment.reporting_year,
                    'forms': forms_data
                }
                
                return Response(response_data)
                
            except TemplateAssignment.DoesNotExist:
                return Response(
                    {'error': 'Template assignment not found or you do not have access to it'},
                    status=status.HTTP_404_NOT_FOUND
                )
        else:
            # Get all template assignments for these layers
            assignments = TemplateAssignment.objects.filter(
                layer_id__in=accessible_layer_ids
            ).select_related('template', 'layer')
            
            # Add layer relationship info to each assignment
            assignments_data = []
            for assignment in assignments:
                assignment_data = TemplateAssignmentSerializer(assignment).data
                
                # Add relationship info (direct or inherited)
                user_direct_layers = [layer.id for layer in user_layers]
                if assignment.layer_id in user_direct_layers:
                    assignment_data['relationship'] = 'direct'
                else:
                    assignment_data['relationship'] = 'inherited'
                
                assignments_data.append(assignment_data)
            
            return Response(assignments_data)

class ESGMetricSubmissionViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing ESG metric submissions.
    """
    serializer_class = ESGMetricSubmissionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Base queryset
        queryset = ESGMetricSubmission.objects.all()
        
        # Filter by user's permissions
        user = self.request.user
        
        # Admin users can see all submissions
        if user.is_staff or user.is_superuser or user.is_baker_tilly_admin:
            return queryset
        
        # Other users can only see submissions for their layers
        user_layers = LayerProfile.objects.filter(app_users__user=user)
        return queryset.filter(
            assignment__layer__in=user_layers
        )

    def get_serializer_class(self):
        if self.action == 'verify':
            return ESGMetricSubmissionVerifySerializer
        return self.serializer_class

    def perform_create(self, serializer):
        submission = serializer.save(submitted_by=self.request.user)
        # Check if form is complete after new submission
        self._check_form_completion(submission)
        return submission

    def _check_form_completion(self, submission_or_assignment):
        """Check if a form is complete after a submission is added or updated"""
        # Get the template assignment
        if hasattr(submission_or_assignment, 'assignment'):
            # If we were passed a submission
            assignment = submission_or_assignment.assignment
            submitter = submission_or_assignment.submitted_by
        else:
            # If we were passed an assignment directly
            assignment = submission_or_assignment
            submitter = None  # We don't know who to attribute the completion to
        
        # Get all metrics for the forms in this template
        metrics = ESGMetric.objects.filter(
            form__in=assignment.template.selected_forms.all()
        )
        
        # Get all submissions for this assignment
        submissions = ESGMetricSubmission.objects.filter(
            assignment=assignment
        )
        
        # Helper function to get required submission count for time-based metrics
        def get_required_submission_count(metric, assignment):
            if not metric.requires_time_reporting or not metric.reporting_frequency:
                return 1
                
            # For simplicity, use fixed counts based on reporting frequency
            if metric.reporting_frequency == 'monthly':
                return 12
            elif metric.reporting_frequency == 'quarterly':
                return 4
            elif metric.reporting_frequency == 'annual':
                return 1
            
            return 1  # Default fallback
        
        # Check if all required metrics have submissions
        all_required_metrics_submitted = True
        for metric in metrics:
            if metric.is_required:
                # For time-based metrics, check if we have enough entries
                if metric.requires_time_reporting:
                    # Count submissions for this metric
                    submissions_count = submissions.filter(metric=metric).count()
                    
                    # Calculate required count based on frequency
                    required_count = get_required_submission_count(metric, assignment)
                    
                    if submissions_count < required_count:
                        all_required_metrics_submitted = False
                        break
                else:
                    # For regular metrics, we need at least one submission
                    has_submission = submissions.filter(metric=metric).exists()
                    if not has_submission:
                        all_required_metrics_submitted = False
                        break
        
        # Update assignment status if all required metrics are submitted
        if all_required_metrics_submitted and assignment.status in ['PENDING', 'IN_PROGRESS']:
            assignment.status = 'SUBMITTED'
            assignment.completed_at = timezone.now()
            assignment.save()
            
            # Update any form selection completions
            for form_selection in assignment.template.templateformselection_set.all():
                form_metrics = metrics.filter(form=form_selection.form)
                form_metrics_submitted = True
                
                for metric in form_metrics:
                    if metric.is_required:
                        if metric.requires_time_reporting:
                            # For time-based metrics, check submission count
                            submissions_count = submissions.filter(metric=metric).count()
                            required_count = get_required_submission_count(metric, assignment)
                            
                            if submissions_count < required_count:
                                form_metrics_submitted = False
                                break
                        else:
                            # For regular metrics, check if any submission exists
                            if not submissions.filter(metric=metric).exists():
                                form_metrics_submitted = False
                                break
                
                if form_metrics_submitted and not form_selection.is_completed:
                    form_selection.is_completed = True
                    form_selection.completed_at = timezone.now()
                    # If we have a submitter, use that, otherwise try to find a recent submitter
                    if submitter:
                        form_selection.completed_by = submitter
                    else:
                        # Try to get the most recent submitter for a metric in this form
                        recent_submission = submissions.filter(
                            metric__form=form_selection.form
                        ).order_by('-submitted_at').first()
                        if recent_submission:
                            form_selection.completed_by = recent_submission.submitted_by
                    form_selection.save()

    def perform_destroy(self, instance):
        # Store assignment before deleting
        assignment = instance.assignment
        
        # Call parent method to delete
        super().perform_destroy(instance)
        
        # Re-check form completion status
        self._check_form_completion(assignment)

    @action(detail=False, methods=['post'])
    @transaction.atomic
    def batch_submit(self, request):
        """
        Submit multiple metric values at once.
        
        POST parameters:
        - assignment_id: The ID of the template assignment
        - submissions: List of submission objects with metric_id, value, and optional reporting_period
        - auto_attach_evidence: (Optional) Boolean to automatically attach standalone evidence
        """
        # Validate assignment_id
        assignment_id = request.data.get('assignment_id')
        if not assignment_id:
            return Response({'error': 'assignment_id is required'}, status=400)
        
        try:
            assignment = TemplateAssignment.objects.get(id=assignment_id)
        except TemplateAssignment.DoesNotExist:
            return Response({'error': 'Assignment not found'}, status=404)
        
        # Check permissions
        if not (request.user.is_staff or request.user.is_superuser or 
                request.user.is_baker_tilly_admin or 
                request.user == assignment.assigned_to or
                LayerProfile.objects.filter(id=assignment.layer.id, app_users__user=request.user).exists()):
            return Response({'error': 'You do not have permission to submit for this assignment'}, status=403)
        
        # Get submissions data
        submissions_data = request.data.get('submissions', [])
        if not submissions_data:
            return Response({'error': 'No submissions provided'}, status=400)
        
        # Create or update submissions
        created_submissions = []
        updated_submissions = []
        
        for sub_data in submissions_data:
            metric_id = sub_data.get('metric_id')
            value = sub_data.get('value')
            text_value = sub_data.get('text_value')
            reporting_period = sub_data.get('reporting_period')
            notes = sub_data.get('notes', '')
            
            # Validate metric exists
            try:
                metric = ESGMetric.objects.get(id=metric_id)
            except ESGMetric.DoesNotExist:
                return Response({
                    'error': f'Metric with ID {metric_id} not found'
                }, status=400)
            
            # Check if submission already exists for this metric/period
            try:
                existing = ESGMetricSubmission.objects.get(
                    assignment=assignment,
                    metric=metric,
                    reporting_period=reporting_period
                )
                
                # Update existing submission
                existing.value = value
                existing.text_value = text_value
                existing.notes = notes
                existing.save()
                updated_submissions.append(existing)
                
            except ESGMetricSubmission.DoesNotExist:
                # Create new submission
                submission = ESGMetricSubmission.objects.create(
                    assignment=assignment,
                    metric=metric,
                    value=value,
                    text_value=text_value,
                    reporting_period=reporting_period,
                    notes=notes,
                    submitted_by=request.user
                )
                created_submissions.append(submission)
        
        # Update assignment status
        if assignment.status in ['PENDING', 'IN_PROGRESS']:
            assignment.status = 'IN_PROGRESS'
            assignment.save()
        
        # Check if form is now complete
        if created_submissions:
            self._check_form_completion(created_submissions[0])
        elif updated_submissions:
            self._check_form_completion(updated_submissions[0])
        
        # Automatically attach standalone evidence files if requested
        evidence_count = 0
        if request.data.get('auto_attach_evidence') in [True, 'true', 'True']:
            all_submissions = created_submissions + updated_submissions
            evidence_count = attach_evidence_to_submissions(all_submissions, request.user)
        
        return Response({
            'status': 'success',
            'message': f'Created {len(created_submissions)} and updated {len(updated_submissions)} submissions',
            'evidence_attached': evidence_count,
            'assignment_status': assignment.status
        })

    @action(detail=False, methods=['get'])
    def by_assignment(self, request):
        """Get all submissions for a specific assignment"""
        assignment_id = request.query_params.get('assignment_id')
        if not assignment_id:
            return Response({'error': 'assignment_id is required'}, status=400)
        
        try:
            assignment = TemplateAssignment.objects.get(id=assignment_id)
        except TemplateAssignment.DoesNotExist:
            return Response({'error': 'Assignment not found'}, status=404)
        
        # Check permissions
        if not (request.user.is_staff or request.user.is_superuser or 
                request.user.is_baker_tilly_admin or 
                request.user == assignment.assigned_to or
                LayerProfile.objects.filter(id=assignment.layer.id, app_users__user=request.user).exists()):
            return Response({'error': 'You do not have permission to view this assignment'}, status=403)
        
        # Get all submissions for this assignment
        submissions = ESGMetricSubmission.objects.filter(assignment=assignment)
        
        # Apply filters
        form_id = request.query_params.get('form_id')
        if form_id:
            submissions = submissions.filter(metric__form_id=form_id)
            
        metric_id = request.query_params.get('metric_id')
        if metric_id:
            submissions = submissions.filter(metric_id=metric_id)
            
        is_verified = request.query_params.get('is_verified')
        if is_verified is not None:
            is_verified_bool = is_verified.lower() in ['true', '1', 'yes']
            submissions = submissions.filter(is_verified=is_verified_bool)
            
        # Date range filtering
        submitted_after = request.query_params.get('submitted_after')
        if submitted_after:
            submissions = submissions.filter(submitted_at__gte=submitted_after)
            
        submitted_before = request.query_params.get('submitted_before')
        if submitted_before:
            submissions = submissions.filter(submitted_at__lte=submitted_before)
            
        # Sorting
        sort_by = request.query_params.get('sort_by', 'submitted_at')
        sort_direction = request.query_params.get('sort_direction', 'desc')
        
        if sort_direction.lower() == 'desc':
            sort_by = f'-{sort_by}'
        
        submissions = submissions.order_by(sort_by)
        
        # Pagination
        page_size = int(request.query_params.get('page_size', 50))
        page = int(request.query_params.get('page', 1))
        
        start = (page - 1) * page_size
        end = start + page_size
        
        total_count = submissions.count()
        submissions = submissions[start:end]
        
        serializer = self.get_serializer(submissions, many=True)
        
        return Response({
            'total_count': total_count,
            'page': page,
            'page_size': page_size,
            'total_pages': (total_count + page_size - 1) // page_size,
            'results': serializer.data
        })

    @action(detail=True, methods=['post'])
    @transaction.atomic
    def verify(self, request, pk=None):
        """Verify a submission (for Baker Tilly admins)"""
        submission = self.get_object()
        
        # Only Baker Tilly admins can verify submissions
        if not (request.user.is_staff or request.user.is_superuser or request.user.is_baker_tilly_admin):
            return Response({'error': 'Only Baker Tilly admins can verify submissions'}, status=403)
        
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Update verification status
        submission.is_verified = True
        submission.verified_by = request.user
        submission.verified_at = timezone.now()
        submission.verification_notes = serializer.validated_data.get('verification_notes', '')
        submission.save()
        
        return Response({
            'status': 'success',
            'message': 'Submission verified successfully'
        })

    @action(detail=False, methods=['post'])
    @transaction.atomic
    def submit_template(self, request):
        """
        Submit a complete template and mark it as submitted.
        
        POST parameters:
        - assignment_id: The ID of the template assignment
        """
        # Validate assignment_id
        assignment_id = request.data.get('assignment_id')
        if not assignment_id:
            return Response({'error': 'assignment_id is required'}, status=400)
        
        try:
            assignment = TemplateAssignment.objects.get(id=assignment_id)
        except TemplateAssignment.DoesNotExist:
            return Response({'error': 'Assignment not found'}, status=404)
        
        # Check permissions
        if not (request.user.is_staff or request.user.is_superuser or 
                request.user.is_baker_tilly_admin or 
                request.user == assignment.assigned_to or
                LayerProfile.objects.filter(id=assignment.layer.id, app_users__user=request.user).exists()):
            return Response({'error': 'You do not have permission to submit this template'}, status=403)
        
        # Helper function to get required submission count for time-based metrics
        def get_required_submission_count(metric, assignment):
            if not metric.requires_time_reporting or not metric.reporting_frequency:
                return 1
                
            # For simplicity, use fixed counts based on reporting frequency
            if metric.reporting_frequency == 'monthly':
                return 12
            elif metric.reporting_frequency == 'quarterly':
                return 4
            elif metric.reporting_frequency == 'annual':
                return 1
            
            return 1  # Default fallback
        
        # Get all metrics for the forms in this template
        metrics = ESGMetric.objects.filter(
            form__in=assignment.template.selected_forms.all()
        )
        
        # Get all submissions for this assignment
        submissions = ESGMetricSubmission.objects.filter(
            assignment=assignment
        )
        
        # Check if all required metrics have submissions
        missing_metrics = []
        incomplete_time_based = []
        
        for metric in metrics:
            if metric.is_required:
                if metric.requires_time_reporting:
                    # For time-based metrics, check submission count
                    submissions_count = submissions.filter(metric=metric).count()
                    required_count = get_required_submission_count(metric, assignment)
                    
                    if submissions_count < required_count:
                        incomplete_time_based.append({
                            'id': metric.id,
                            'name': metric.name,
                            'form': metric.form.name,
                            'reporting_frequency': metric.reporting_frequency,
                            'submitted_count': submissions_count,
                            'required_count': required_count
                        })
                else:
                    # For regular metrics, we need at least one submission
                    has_submission = submissions.filter(metric=metric).exists()
                    if not has_submission:
                        missing_metrics.append({
                            'id': metric.id,
                            'name': metric.name,
                            'form': metric.form.name
                        })
        
        errors = {}
        if missing_metrics:
            errors["missing_metrics"] = missing_metrics
            
        if incomplete_time_based:
            errors["incomplete_time_based_metrics"] = incomplete_time_based
            
        if errors:
            return Response({
                'status': 'incomplete',
                'message': 'Template is incomplete.',
                **errors
            }, status=400)
        
        # Update assignment status
        assignment.status = 'SUBMITTED'
        assignment.completed_at = timezone.now()
        assignment.save()
        
        # Update form selections
        for form_selection in assignment.template.templateformselection_set.all():
            form_metrics = metrics.filter(form=form_selection.form)
            form_metrics_submitted = True
            
            for metric in form_metrics:
                if metric.is_required:
                    if metric.requires_time_reporting:
                        # For time-based metrics, check submission count
                        submissions_count = submissions.filter(metric=metric).count()
                        required_count = get_required_submission_count(metric, assignment)
                        
                        if submissions_count < required_count:
                            form_metrics_submitted = False
                            break
                    else:
                        # For regular metrics, check if any submission exists
                        if not submissions.filter(metric=metric).exists():
                            form_metrics_submitted = False
                            break
            
            if form_metrics_submitted:
                form_selection.is_completed = True
                form_selection.completed_at = timezone.now()
                form_selection.completed_by = request.user
                form_selection.save()
        
        return Response({
            'status': 'success',
            'message': 'Template submitted successfully',
            'assignment_status': assignment.status
        })

class ESGMetricViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing ESG metrics.
    Baker Tilly admins can create, update, and delete metrics.
    Other users can only view metrics.
    """
    queryset = ESGMetric.objects.all()
    serializer_class = ESGMetricSerializer
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        """
        Only Baker Tilly admins can create, update, or delete metrics.
        All authenticated users can view metrics.
        """
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAuthenticated(), BakerTillyAdmin()]
        return [IsAuthenticated()]

    def get_queryset(self):
        """
        Filter metrics by form_id query parameter if provided.
        """
        queryset = super().get_queryset()
        form_id = self.request.query_params.get('form_id')
        if form_id:
            queryset = queryset.filter(form_id=form_id)
        return queryset

    def perform_create(self, serializer):
        """
        Create a new ESG metric.
        Requires form_id in request data unless already specified in query parameters.
        """
        form_id = self.request.data.get('form_id') or self.request.query_params.get('form_id')
        if not form_id:
            raise serializers.ValidationError({"form_id": "This field is required."})
            
        try:
            form = ESGForm.objects.get(id=form_id)
            serializer.save(form=form)
        except ESGForm.DoesNotExist:
            raise serializers.ValidationError({"form_id": f"Form with ID {form_id} not found."})

class BatchEvidenceView(views.APIView):
    """
    API view for fetching evidence and submission data for multiple submissions at once.
    This is an optimization for the admin interface to reduce the number of API calls.
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """
        Get evidence files and submission data for multiple submissions at once.
        
        Query parameters:
        - submission_ids: Comma-separated list of submission IDs
        
        Returns:
        A dictionary mapping submission IDs to their submission data and evidence files
        """
        submission_ids_param = request.query_params.get('submission_ids', '')
        submission_ids = [id.strip() for id in submission_ids_param.split(',') if id.strip().isdigit()]
        
        if not submission_ids:
            return Response({"error": "No valid submission IDs provided"}, status=400)
        
        # Get all submissions and evidence items for these IDs
        submissions = ESGMetricSubmission.objects.filter(id__in=submission_ids).select_related(
            'metric', 'assignment', 'submitted_by'
        )
        evidence_items = ESGMetricEvidence.objects.filter(submission_id__in=submission_ids)
        
        # Check permissions
        user = request.user
        if not (user.is_staff or user.is_superuser or user.is_baker_tilly_admin):
            # Regular users can only see evidence for submissions they have access to
            user_layers = LayerProfile.objects.filter(app_users__user=user)
            accessible_submissions = submissions.filter(
                assignment__layer__in=user_layers
            ).values_list('id', flat=True)
            
            submissions = submissions.filter(id__in=accessible_submissions)
            evidence_items = evidence_items.filter(submission_id__in=accessible_submissions)
        
        # Group evidence by submission ID
        evidence_by_submission = {}
        evidence_serializer = ESGMetricEvidenceSerializer
        
        for evidence in evidence_items:
            submission_id = str(evidence.submission_id)
            if submission_id not in evidence_by_submission:
                evidence_by_submission[submission_id] = []
            
            evidence_by_submission[submission_id].append(evidence_serializer(evidence).data)
        
        # Create response with submission data and evidence
        response_data = {}
        submission_serializer = ESGMetricSubmissionSerializer
        
        for submission in submissions:
            submission_id = str(submission.id)
            submission_data = submission_serializer(submission).data
            submission_data['evidence'] = evidence_by_submission.get(submission_id, [])
            response_data[submission_id] = submission_data
        
        return Response(response_data) 