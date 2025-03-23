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
                
                # If the form is already completed, return its status
                if form_selection.is_completed:
                    return Response({
                        "form_id": form.id,
                        "form_name": form.name,
                        "form_code": form.code,
                        "is_completed": True,
                        "completed_at": form_selection.completed_at,
                        "completed_by": form_selection.completed_by.email if form_selection.completed_by else None,
                        "completion_percentage": 100
                    })
                    
                # Get all required metrics for this form that apply to the selected regions
                required_metrics = []
                for metric in form.metrics.filter(is_required=True):
                    if metric.location == 'ALL' or metric.location in form_selection.regions:
                        required_metrics.append(metric.id)
                        
                # Check if all required metrics have submissions
                submitted_metrics = ESGMetricSubmission.objects.filter(
                    assignment=assignment,
                    metric__form=form
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
                    ).values('id', 'name', 'location')
                
                # Check if all required metrics are submitted but form isn't marked complete
                can_complete = total_required > 0 and total_submitted == total_required
                
                return Response({
                    "form_id": form.id,
                    "form_name": form.name,
                    "form_code": form.code,
                    "is_completed": False,
                    "completion_percentage": completion_percentage,
                    "total_required_metrics": total_required,
                    "total_submitted_metrics": total_submitted,
                    "missing_metrics": list(missing_metrics),
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
            except TemplateFormSelection.DoesNotExist:
                return Response(
                    {"error": "This form is not part of the template"},
                    status=status.HTTP_400_BAD_REQUEST
                )
                
            # Get all required metrics for this form that apply to the selected regions
            required_metrics = []
            for metric in form.metrics.filter(is_required=True):
                if metric.location == 'ALL' or metric.location in form_selection.regions:
                    required_metrics.append(metric.id)
                    
            # Check if all required metrics have submissions
            submissions = ESGMetricSubmission.objects.filter(
                assignment=assignment,
                metric__form=form
            )
            submitted_metrics = submissions.values_list('metric_id', flat=True)
            
            missing_metrics = set(required_metrics) - set(submitted_metrics)
            
            if missing_metrics:
                # Get names of missing metrics for better error message
                missing_metric_names = ESGMetric.objects.filter(
                    id__in=missing_metrics
                ).values_list('name', flat=True)
                
                return Response({
                    "error": "Cannot complete form with missing required metrics",
                    "missing_metrics": list(missing_metric_names)
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Automatically attach evidence files related to this form's submissions
            evidence_count = attach_evidence_to_submissions(list(submissions), request.user)
                
            # Mark the form as completed
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
                "message": "Form successfully completed",
                "form_id": form.id,
                "form_name": form.name,
                "form_code": form.code,
                "evidence_attached": evidence_count,
                "all_forms_completed": all_forms_completed,
                "assignment_status": assignment.status
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
        else:
            # If we were passed an assignment directly
            assignment = submission_or_assignment
        
        # Get all metrics for the forms in this template
        metrics = ESGMetric.objects.filter(
            form__in=assignment.template.selected_forms.all()
        )
        
        # Get all submissions for this assignment
        submissions = ESGMetricSubmission.objects.filter(
            assignment=assignment
        )
        
        # Check if all required metrics have submissions
        all_required_metrics_submitted = True
        for metric in metrics:
            if metric.is_required:
                # For time-based metrics, we need to check if there's a submission
                # for each time period
                if metric.requires_time_reporting:
                    # Implementation depends on your business rules for time periods
                    # This is a simplified check
                    metric_submissions = submissions.filter(metric=metric)
                    if not metric_submissions.exists():
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
                    if metric.is_required and not submissions.filter(metric=metric).exists():
                        form_metrics_submitted = False
                        break
                
                if form_metrics_submitted and not form_selection.is_completed:
                    form_selection.is_completed = True
                    form_selection.completed_at = timezone.now()
                    form_selection.completed_by = submission.submitted_by
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
        if request.data.get('auto_attach_evidence') == 'true':
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
        serializer = self.get_serializer(submissions, many=True)
        return Response(serializer.data)

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
        for metric in metrics:
            if metric.is_required:
                # For time-based metrics, we need at least one submission
                # (In a real application, you might have more complex time period validation)
                has_submission = submissions.filter(metric=metric).exists()
                if not has_submission:
                    missing_metrics.append({
                        'id': metric.id,
                        'name': metric.name,
                        'form': metric.form.name
                    })
        
        if missing_metrics:
            return Response({
                'status': 'incomplete',
                'message': 'Template is incomplete. Missing required metrics.',
                'missing_metrics': missing_metrics
            }, status=400)
        
        # Evidence attachment is now handled at form completion stage
        # No need to call attach_evidence_to_submissions here
        
        # Update assignment status
        assignment.status = 'SUBMITTED'
        assignment.completed_at = timezone.now()
        assignment.save()
        
        # Update form selections
        for form_selection in assignment.template.templateformselection_set.all():
            form_metrics = metrics.filter(form=form_selection.form)
            form_metrics_submitted = True
            
            for metric in form_metrics:
                if metric.is_required and not submissions.filter(metric=metric).exists():
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