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
    ESGMetricEvidenceSerializer, ESGMetricBatchSubmissionSerializer
)
from rest_framework import serializers
from django.conf import settings
from ..services.bill_analyzer import UtilityBillAnalyzer

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
            submitted_metrics = ESGMetricSubmission.objects.filter(
                assignment=assignment,
                metric__form=form
            ).values_list('metric_id', flat=True)
            
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
                "assignment_id": assignment.id,
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
        """
        Filter submissions based on user's access to template assignments.
        """
        user = self.request.user
        
        # Get all layers (groups) the user belongs to
        user_app_users = AppUser.objects.filter(user=user).select_related('layer')
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
        
        # Filter submissions by assignments to accessible layers
        return ESGMetricSubmission.objects.filter(
            assignment__layer_id__in=accessible_layer_ids
        ).select_related(
            'assignment', 'metric', 'submitted_by', 'verified_by'
        ).prefetch_related('evidence')

    def get_serializer_class(self):
        """
        Use different serializers for list/retrieve vs create/update.
        """
        if self.action in ['create', 'update', 'partial_update']:
            return ESGMetricSubmissionCreateSerializer
        return ESGMetricSubmissionSerializer

    def perform_create(self, serializer):
        """
        Set the submitted_by field to the current user.
        """
        serializer.save(submitted_by=self.request.user)
        
        # Update assignment status to IN_PROGRESS if it's PENDING
        assignment = serializer.instance.assignment
        if assignment.status == 'PENDING':
            assignment.status = 'IN_PROGRESS'
            assignment.save(update_fields=['status'])
            
        # Check if the form is now complete
        self._check_form_completion(serializer.instance)
            
    def _check_form_completion(self, submission):
        """
        Helper method to check if a form is complete after a submission.
        If all required metrics for a form are submitted, mark the form as completed.
        """
        # Get the form for this metric
        form = submission.metric.form
        assignment = submission.assignment
        
        try:
            # Find the form selection for this form in the template
            form_selection = TemplateFormSelection.objects.get(
                template=assignment.template,
                form=form
            )
            
            # If the form is already completed, no need to check again
            if form_selection.is_completed:
                return
                
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
            
            # If all required metrics are submitted, mark the form as completed
            if set(required_metrics).issubset(set(submitted_metrics)):
                form_selection.is_completed = True
                form_selection.completed_at = timezone.now()
                form_selection.completed_by = self.request.user
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
                    
        except TemplateFormSelection.DoesNotExist:
            # This form is not part of the template, so we can't mark it as completed
            pass

    def perform_destroy(self, instance):
        """
        Check if the user has permission to delete this submission.
        Users can only delete their own submissions, while Baker Tilly admins can delete any.
        """
        user = self.request.user
        if instance.submitted_by == user or user.is_baker_tilly_admin:
            instance.delete()
        else:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("You do not have permission to delete this submission.")

    @action(detail=False, methods=['post'])
    @transaction.atomic
    def batch_submit(self, request):
        """
        Submit multiple metric values at once for a template assignment.
        """
        serializer = ESGMetricBatchSubmissionSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        
        assignment_id = serializer.validated_data['assignment_id']
        submissions_data = serializer.validated_data['submissions']
        assignment = serializer.context['assignment']
        
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
        
        # Process each submission
        results = []
        submissions_by_form = {}  # Track submissions by form to check completion
        
        for submission_data in submissions_data:
            metric_id = submission_data.pop('metric_id')
            
            try:
                metric = ESGMetric.objects.get(id=metric_id)
                form_id = metric.form_id
                
                # Add to form tracking
                if form_id not in submissions_by_form:
                    submissions_by_form[form_id] = []
                submissions_by_form[form_id].append(metric_id)
                
                # Check if submission already exists with the same reporting period
                reporting_period = submission_data.get('reporting_period')
                
                try:
                    # Try to find an existing submission with the same metric and reporting period
                    submission = ESGMetricSubmission.objects.get(
                        assignment_id=assignment_id,
                        metric_id=metric_id,
                        reporting_period=reporting_period
                    )
                    
                    # Update existing submission
                    for key, value in submission_data.items():
                        setattr(submission, key, value)
                    
                    submission.submitted_by = request.user
                    submission.save()
                    
                except ESGMetricSubmission.DoesNotExist:
                    # Create new submission
                    submission = ESGMetricSubmission.objects.create(
                        assignment_id=assignment_id,
                        metric_id=metric_id,
                        submitted_by=request.user,
                        **submission_data
                    )
                
                results.append({
                    'metric_id': metric_id,
                    'submission_id': submission.id,
                    'status': 'success',
                    'reporting_period': reporting_period
                })
                
            except ESGMetric.DoesNotExist:
                results.append({
                    'metric_id': metric_id,
                    'status': 'error',
                    'message': f"Metric with ID {metric_id} not found"
                })
        
        # Update assignment status to IN_PROGRESS if it's PENDING
        if assignment.status == 'PENDING':
            assignment.status = 'IN_PROGRESS'
            assignment.save(update_fields=['status'])
        
        # Check form completion for each form that had submissions
        forms_completed = []
        for form_id in submissions_by_form.keys():
            try:
                form = ESGForm.objects.get(id=form_id)
                form_selection = TemplateFormSelection.objects.get(
                    template=assignment.template,
                    form=form
                )
                
                # If the form is already completed, skip it
                if form_selection.is_completed:
                    continue
                    
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
                
                # If all required metrics are submitted, mark the form as completed
                if set(required_metrics).issubset(set(submitted_metrics)):
                    form_selection.is_completed = True
                    form_selection.completed_at = timezone.now()
                    form_selection.completed_by = request.user
                    form_selection.save()
                    forms_completed.append(form.name)
                    
            except (ESGForm.DoesNotExist, TemplateFormSelection.DoesNotExist):
                # Skip if form doesn't exist or isn't part of the template
                continue
                
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
            'assignment_id': assignment_id,
            'results': results,
            'forms_completed': forms_completed,
            'all_forms_completed': all_forms_completed,
            'assignment_status': assignment.status
        })

    @action(detail=False, methods=['get'])
    def by_assignment(self, request):
        """
        Get all submissions for a specific template assignment.
        """
        assignment_id = request.query_params.get('assignment_id')
        if not assignment_id:
            return Response(
                {"error": "assignment_id query parameter is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if user has access to this assignment
        queryset = self.get_queryset().filter(assignment_id=assignment_id)
        if not queryset.exists():
            # Check if assignment exists but has no submissions
            try:
                assignment = TemplateAssignment.objects.get(id=assignment_id)
                # If we get here, the assignment exists but has no submissions
                return Response([])
            except TemplateAssignment.DoesNotExist:
                return Response(
                    {"error": "Template assignment not found or you do not have access to it"},
                    status=status.HTTP_404_NOT_FOUND
                )
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    @transaction.atomic
    def verify(self, request, pk=None):
        """
        Verify a metric submission (Baker Tilly admin only).
        """
        if not request.user.is_baker_tilly_admin:
            return Response(
                {"error": "Only Baker Tilly admins can verify submissions"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        submission = self.get_object()
        verification_notes = request.data.get('verification_notes', '')
        
        submission.is_verified = True
        submission.verified_by = request.user
        submission.verified_at = timezone.now()
        submission.verification_notes = verification_notes
        submission.save()
        
        serializer = self.get_serializer(submission)
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    @transaction.atomic
    def submit_template(self, request):
        """
        Mark a template assignment as submitted when all forms are completed.
        This is the final step in the submission process after completing all forms.
        """
        assignment_id = request.data.get('assignment_id')
        if not assignment_id:
            return Response(
                {"error": "assignment_id is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Get the assignment and check user access
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
            
            # Check if all forms in the template are completed
            form_selections = assignment.template.templateformselection_set.all()
            incomplete_forms = [
                selection.form.name
                for selection in form_selections
                if not selection.is_completed
            ]
            
            if incomplete_forms:
                return Response({
                    "error": "Cannot submit template with incomplete forms",
                    "incomplete_forms": incomplete_forms
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Update assignment status to SUBMITTED
            assignment.status = 'SUBMITTED'
            assignment.completed_at = timezone.now()
            assignment.save()
            
            return Response({
                "message": "Template successfully submitted",
                "assignment_id": assignment.id,
                "status": assignment.status,
                "completed_at": assignment.completed_at
            })
            
        except TemplateAssignment.DoesNotExist:
            return Response(
                {"error": "Template assignment not found"},
                status=status.HTTP_404_NOT_FOUND
            )

class ESGMetricEvidenceViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing evidence files for ESG metric submissions.
    """
    serializer_class = ESGMetricEvidenceSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """
        Filter evidence files based on user's access to submissions.
        """
        user = self.request.user
        
        # Get all layers (groups) the user belongs to
        user_app_users = AppUser.objects.filter(user=user).select_related('layer')
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
        
        # Filter evidence by submissions for assignments to accessible layers
        return ESGMetricEvidence.objects.filter(
            submission__assignment__layer_id__in=accessible_layer_ids
        ).select_related('submission', 'uploaded_by')
    
    def perform_create(self, serializer):
        """
        Set the uploaded_by field to the current user.
        """
        serializer.save(uploaded_by=self.request.user)
    
    @action(detail=False, methods=['get'])
    def by_submission(self, request):
        """
        Get all evidence files for a specific submission.
        """
        submission_id = request.query_params.get('submission_id')
        if not submission_id:
            return Response(
                {"error": "submission_id query parameter is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        queryset = self.get_queryset().filter(submission_id=submission_id)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def process_ocr(self, request, pk=None):
        """
        Process an uploaded evidence file with OCR.
        This endpoint triggers the Azure Content Understanding OCR processing for a utility bill.
        """
        try:
            evidence = ESGMetricEvidence.objects.get(pk=pk)
            
            # Check if the user has access to this evidence
            # (Implement your access control logic here)
            
            # Enable OCR processing for this evidence
            evidence.enable_ocr_processing = True
            evidence.save(update_fields=['enable_ocr_processing'])
            
            # Process the evidence with OCR
            analyzer = UtilityBillAnalyzer()
            success, result = analyzer.process_evidence(evidence)
            
            if success:
                return Response({
                    "status": "success",
                    "message": "OCR processing completed successfully",
                    "extracted_value": evidence.extracted_value,
                    "period": evidence.period.strftime('%Y-%m-%d') if evidence.period else None,
                    "additional_periods": result.get('additional_periods', [])
                }, status=status.HTTP_200_OK)
            else:
                return Response({
                    "status": "error",
                    "message": result.get('error', 'OCR processing failed')
                }, status=status.HTTP_400_BAD_REQUEST)
                
        except ESGMetricEvidence.DoesNotExist:
            return Response(
                {"error": "Evidence not found"}, 
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {"error": f"OCR processing error: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['get'])
    def ocr_results(self, request, pk=None):
        """
        Get the OCR processing results for an evidence file.
        """
        try:
            evidence = ESGMetricEvidence.objects.get(pk=pk)
            
            # Check if the user has access to this evidence
            # (Implement your access control logic here)
            
            # Check if OCR processing was enabled
            if not evidence.enable_ocr_processing:
                return Response({
                    "status": "not_applicable",
                    "message": "OCR processing was not enabled for this file"
                }, status=status.HTTP_200_OK)
            
            # Check if OCR processing has been completed
            if evidence.is_processed_by_ocr:
                return Response({
                    "status": "success",
                    "extracted_value": evidence.extracted_value,
                    "period": evidence.period.strftime('%Y-%m-%d') if evidence.period else None
                }, status=status.HTTP_200_OK)
            else:
                # OCR processing was enabled but not yet completed
                return Response({
                    "status": "pending",
                    "message": "OCR processing has not yet completed"
                }, status=status.HTTP_200_OK)
                
        except ESGMetricEvidence.DoesNotExist:
            return Response(
                {"error": "Evidence not found"}, 
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {"error": f"Error retrieving OCR results: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['post'])
    def apply_ocr_to_submission(self, request, pk=None):
        """
        Apply OCR-extracted values to the related submission.
        
        This endpoint updates the ESGMetricSubmission with values extracted by OCR,
        and tracks whether the user edited these values.
        """
        evidence = self.get_object()
        submission = evidence.submission
        
        # Check if this is an OCR-processed evidence
        if not evidence.ocr_processed or not evidence.is_utility_bill:
            return Response(
                {"error": "This evidence has not been processed with OCR"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get values from request
        value = request.data.get('value')
        reporting_period = request.data.get('reporting_period')
        
        # Determine if values were manually edited
        was_edited = False
        
        # Check if value was manually edited
        if value is not None and evidence.extracted_value is not None:
            try:
                if abs(float(value) - evidence.extracted_value) > 0.001:
                    was_edited = True
            except (ValueError, TypeError):
                # If we can't compare them, assume they're different
                was_edited = True
        
        # Check if period was manually edited
        if reporting_period is not None and evidence.extracted_period is not None:
            from dateutil.parser import parse
            try:
                submitted_date = parse(reporting_period).date()
                if submitted_date != evidence.extracted_period:
                    was_edited = True
            except (ValueError, TypeError):
                # If we can't parse or compare them, assume they're different
                was_edited = True
        
        # Update the evidence record to track edits
        if was_edited:
            evidence.was_manually_edited = True
            evidence.edited_at = timezone.now()
            evidence.edited_by = request.user
            evidence.save()
        
        # Update the submission with the provided values
        if value is not None:
            try:
                submission.value = float(value)
            except (ValueError, TypeError):
                return Response(
                    {"error": "Invalid value format"},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        if reporting_period is not None:
            from dateutil.parser import parse
            try:
                submission.reporting_period = parse(reporting_period).date()
            except (ValueError, TypeError):
                return Response(
                    {"error": "Invalid reporting_period format"},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        submission.save()
        
        # Return updated submission and evidence
        return Response({
            "status": "success",
            "was_edited": was_edited,
            "submission": ESGMetricSubmissionSerializer(submission).data,
            "evidence": self.get_serializer(evidence).data
        })
    
    @action(detail=True, methods=['post'])
    def apply_multiple_periods(self, request, pk=None):
        """
        Apply multiple billing periods from OCR data to create multiple submissions.
        
        This endpoint handles utility bills that contain multiple billing periods,
        creating or updating submissions for each period.
        """
        evidence = self.get_object()
        original_submission = evidence.submission
        
        # Check if this is an OCR-processed evidence with multiple periods
        if not evidence.ocr_processed or not evidence.is_utility_bill:
            return Response(
                {"error": "This evidence has not been processed with OCR"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get the periods data
        periods = request.data.get('periods', [])
        if not periods:
            return Response(
                {"error": "No period data provided"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Track if any values were edited
        was_edited = False
        
        # Get original periods from OCR data for comparison
        original_periods = {}
        if evidence.ocr_data and 'raw_data' in evidence.ocr_data and 'periods' in evidence.ocr_data['raw_data']:
            for period in evidence.ocr_data['raw_data']['periods']:
                if 'period' in period and 'consumption' in period:
                    original_periods[period['period']] = period['consumption']
        
        # Process each period
        results = []
        from dateutil.parser import parse
        
        for period_data in periods:
            period_str = period_data.get('period')
            consumption = period_data.get('consumption')
            
            # Skip invalid data
            if not period_str or consumption is None:
                continue
            
            # Convert period to date
            try:
                period_date = parse(period_str).date() if isinstance(period_str, str) else period_str
            except ValueError:
                continue
            
            # Check if this period was edited
            period_edited = False
            if period_str in original_periods:
                try:
                    orig_consumption = float(original_periods[period_str])
                    new_consumption = float(consumption)
                    if abs(orig_consumption - new_consumption) > 0.001:
                        period_edited = True
                        was_edited = True
                except (ValueError, TypeError):
                    # If we can't compare, assume they're different
                    period_edited = True
                    was_edited = True
            
            # Create or update submission for this period
            try:
                # Try to find existing submission for this period
                period_submission = ESGMetricSubmission.objects.get(
                    assignment=original_submission.assignment,
                    metric=original_submission.metric,
                    reporting_period=period_date
                )
            except ESGMetricSubmission.DoesNotExist:
                # Create new submission for this period
                period_submission = ESGMetricSubmission.objects.create(
                    assignment=original_submission.assignment,
                    metric=original_submission.metric,
                    reporting_period=period_date,
                    submitted_by=request.user
                )
            
            # Update the value
            period_submission.value = float(consumption)
            period_submission.save()
            
            # Add to results
            results.append({
                "period": period_date,
                "value": consumption,
                "submission_id": period_submission.id,
                "was_edited": period_edited
            })
        
        # Update evidence record if any values were edited
        if was_edited:
            evidence.was_manually_edited = True
            evidence.edited_at = timezone.now()
            evidence.edited_by = request.user
            evidence.save()
        
        return Response({
            "status": "success",
            "was_edited": was_edited,
            "message": f"{len(results)} periods processed",
            "periods": results
        })

    def create(self, request, *args, **kwargs):
        """
        Upload an evidence file for an ESG metric submission.
        This is the standard upload endpoint without OCR processing.
        """
        # Get required parameters
        submission_id = request.data.get('submission_id')
        if not submission_id:
            return Response(
                {"error": "submission_id is required"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get the uploaded file
        uploaded_file = request.FILES.get('file')
        if not uploaded_file:
            return Response(
                {"error": "No file provided"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate submission exists and user has access
        try:
            submission = ESGMetricSubmission.objects.get(id=submission_id)
            
            # Check if the user has access to this submission
            # (Implement your access control logic here)
            
        except ESGMetricSubmission.DoesNotExist:
            return Response(
                {"error": "Submission not found"}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Prepare file metadata
        filename = uploaded_file.name
        file_type = filename.split('.')[-1].lower()
        
        # Check if OCR processing is requested (optional parameter)
        enable_ocr_processing = request.data.get('enable_ocr_processing') == 'true'
        
        # Create evidence record
        evidence = ESGMetricEvidence.objects.create(
            submission=submission,
            file=uploaded_file,
            filename=filename,
            file_type=file_type,
            uploaded_by=request.user,
            description=request.data.get('description', ''),
            enable_ocr_processing=enable_ocr_processing
        )
        
        # Return the evidence info
        serializer = self.get_serializer(evidence)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['post'])
    def upload_with_ocr(self, request):
        """
        Upload a file and enable OCR processing in a single step.
        Convenience endpoint for utility bill uploads that need OCR processing.
        """
        # Get required parameters
        submission_id = request.data.get('submission_id')
        if not submission_id:
            return Response(
                {"error": "submission_id is required"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get the uploaded file
        uploaded_file = request.FILES.get('file')
        if not uploaded_file:
            return Response(
                {"error": "No file provided"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate submission exists and user has access
        try:
            submission = ESGMetricSubmission.objects.get(id=submission_id)
            
            # Check if the user has access to this submission
            # (Implement your access control logic here)
            
        except ESGMetricSubmission.DoesNotExist:
            return Response(
                {"error": "Submission not found"}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Prepare file metadata
        filename = uploaded_file.name
        file_type = filename.split('.')[-1].lower()
        
        # Create evidence record with OCR processing enabled
        evidence = ESGMetricEvidence.objects.create(
            submission=submission,
            file=uploaded_file,
            filename=filename,
            file_type=file_type,
            uploaded_by=request.user,
            description=request.data.get('description', ''),
            enable_ocr_processing=True
        )
        
        # Return the evidence info with a note about OCR processing
        serializer = self.get_serializer(evidence)
        response_data = serializer.data
        response_data['ocr_status'] = 'pending'
        response_data['message'] = 'File uploaded successfully. OCR processing has been enabled.'
        
        # Include a reference to the process_ocr endpoint for later use
        response_data['process_ocr_url'] = request.build_absolute_uri(
            f'/api/metric-evidence/{evidence.id}/process_ocr/'
        )
        
        return Response(response_data, status=status.HTTP_201_CREATED)

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