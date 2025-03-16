from rest_framework import viewsets, views, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db import transaction
from django.utils import timezone
from accounts.permissions import BakerTillyAdmin
from accounts.models import CustomUser, AppUser
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

class ESGFormViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing ESG forms. Forms are predefined and can only be modified
    through admin interface.
    """
    queryset = ESGForm.objects.filter(is_active=True)
    serializer_class = ESGFormSerializer
    permission_classes = [IsAuthenticated]

    @action(detail=True, methods=['get'])
    def metrics(self, request, pk=None):
        """Get metrics for a specific form"""
        form = self.get_object()
        metrics = form.metrics.all()
        serializer = ESGMetricSerializer(metrics, many=True)
        return Response(serializer.data)

class ESGFormCategoryViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing ESG form categories with their associated forms.
    """
    queryset = ESGFormCategory.objects.all()
    serializer_class = ESGFormCategorySerializer
    permission_classes = [IsAuthenticated]

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
        # Get all form selections with their forms and metrics
        form_selections = template.templateformselection_set.select_related('form').prefetch_related('form__metrics')
        
        # Create a flat list of forms with their metrics
        forms_data = []
        for selection in form_selections:
            form_data = {
                'form_id': selection.form.id,
                'form_code': selection.form.code,
                'form_name': selection.form.name,
                'regions': selection.regions,  # Keep the regions info at form level
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
            'name': template.name,
            'description': template.description,
            'reporting_period': template.reporting_period,
            'forms': forms_data
        })

class TemplateAssignmentView(views.APIView):
    """
    API view for managing template assignments to client layers.
    Templates are assigned directly to layers without requiring a specific user.
    """
    permission_classes = [IsAuthenticated, BakerTillyAdmin]

    def get(self, request, group_id):
        """Get all template assignments for a client layer"""
        assignments = TemplateAssignment.objects.filter(
            layer_id=group_id
        ).select_related('template', 'layer', 'assigned_to')
        
        serializer = TemplateAssignmentSerializer(assignments, many=True)
        return Response(serializer.data)

    @transaction.atomic
    def post(self, request, group_id):
        """Assign a template to a client layer"""
        data = {
            **request.data,
            'layer': group_id
        }
        serializer = TemplateAssignmentSerializer(data=data)
        
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @transaction.atomic
    def delete(self, request, group_id):
        """Remove a template assignment from a client layer"""
        assignment_id = request.data.get('assignment_id')
        try:
            assignment = TemplateAssignment.objects.get(
                id=assignment_id,
                layer_id=group_id
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
                form_selections = template.templateformselection_set.select_related('form').prefetch_related('form__metrics')
                
                # Create a flat list of forms with their metrics
                forms_data = []
                for selection in form_selections:
                    form_data = {
                        'form_id': selection.form.id,
                        'form_code': selection.form.code,
                        'form_name': selection.form.name,
                        'regions': selection.regions,
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
                    'reporting_period': template.reporting_period,
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
        for submission_data in submissions_data:
            metric_id = submission_data.pop('metric_id')
            
            try:
                metric = ESGMetric.objects.get(id=metric_id)
                
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
        
        return Response({
            'assignment_id': assignment_id,
            'results': results
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
    def submit_form(self, request):
        """
        Mark a template assignment as submitted when all required metrics are completed.
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
            
            # Get all required metrics for this template
            required_metrics = []
            form_selections = assignment.template.templateformselection_set.all()
            
            for selection in form_selections:
                # Get metrics that match the form's regions or are for ALL locations
                for metric in selection.form.metrics.filter(is_required=True):
                    if metric.location == 'ALL' or metric.location in selection.regions:
                        required_metrics.append(metric.id)
            
            # Check if all required metrics have submissions
            submitted_metrics = ESGMetricSubmission.objects.filter(
                assignment=assignment
            ).values_list('metric_id', flat=True)
            
            missing_metrics = set(required_metrics) - set(submitted_metrics)
            
            if missing_metrics:
                # Get names of missing metrics for better error message
                missing_metric_names = ESGMetric.objects.filter(
                    id__in=missing_metrics
                ).values_list('name', flat=True)
                
                return Response({
                    "error": "Cannot submit form with missing required metrics",
                    "missing_metrics": list(missing_metric_names)
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Update assignment status to SUBMITTED
            assignment.status = 'SUBMITTED'
            assignment.completed_at = timezone.now()
            assignment.save()
            
            return Response({
                "message": "Form successfully submitted",
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