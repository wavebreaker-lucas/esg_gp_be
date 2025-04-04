"""
Views for managing ESG metric submissions.
"""

from rest_framework import viewsets, views, status, serializers
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db import transaction
from django.utils import timezone

from accounts.models import CustomUser, AppUser, LayerProfile
from accounts.services import get_accessible_layers, has_layer_access
from ..models import (
    ESGForm, ESGMetric, 
    Template, TemplateAssignment, TemplateFormSelection
)
from ..models.templates import (
    ESGMetricSubmission, ESGMetricEvidence,
    MetricValueField, MetricValue
)
from ..serializers.esg import (
    ESGMetricSubmissionSerializer, ESGMetricSubmissionCreateSerializer,
    ESGMetricEvidenceSerializer, ESGMetricBatchSubmissionSerializer,
    ESGMetricSubmissionVerifySerializer
)
from .utils import get_required_submission_count, attach_evidence_to_submissions


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
        
        # If no layer was specified, try to set a default layer
        if not submission.layer:
            try:
                # Try to get a default layer from settings (or use a fallback mechanism)
                from django.conf import settings
                default_layer_id = getattr(settings, 'DEFAULT_LAYER_ID', None)
                
                if default_layer_id:
                    default_layer = LayerProfile.objects.get(id=default_layer_id)
                else:
                    # Fallback: Get the first available group layer
                    default_layer = LayerProfile.objects.filter(layer_type='GROUP').first()
                
                if default_layer:
                    submission.layer = default_layer
                    submission.save()
            except Exception as e:
                # Just log the error, don't fail the submission creation
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"Could not set default layer for submission: {e}")
                
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
        - default_layer_id: (Optional) Default layer ID for all submissions
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
        
        # Get default layer if provided
        default_layer_id = request.data.get('default_layer_id')
        default_layer = None
        
        if default_layer_id:
            try:
                default_layer = LayerProfile.objects.get(id=default_layer_id)
                # Check if user has access
                if not (request.user.is_staff or request.user.is_superuser or 
                        request.user.is_baker_tilly_admin or 
                        LayerProfile.objects.filter(id=default_layer_id, app_users__user=request.user).exists()):
                    return Response({'error': 'You do not have access to the specified layer'}, status=403)
            except LayerProfile.DoesNotExist:
                return Response({'error': f'Layer with ID {default_layer_id} not found'}, status=404)
        else:
            # Try to get default layer from settings or use assignment's layer
            try:
                from django.conf import settings
                settings_default_layer_id = getattr(settings, 'DEFAULT_LAYER_ID', None)
                
                if settings_default_layer_id:
                    default_layer = LayerProfile.objects.get(id=settings_default_layer_id)
                else:
                    # Fallback to the assignment's layer (which is often what we want anyway)
                    default_layer = assignment.layer
            except Exception:
                # Fallback to assignment's layer if any error occurs
                default_layer = assignment.layer
        
        # Create or update submissions
        created_submissions = []
        updated_submissions = []
        
        for sub_data in submissions_data:
            metric_id = sub_data.get('metric_id')
            value = sub_data.get('value')
            text_value = sub_data.get('text_value')
            reporting_period = sub_data.get('reporting_period')
            notes = sub_data.get('notes', '')
            
            # Get layer for this submission
            layer = default_layer
            submission_layer_id = sub_data.get('layer_id')
            if submission_layer_id:
                try:
                    layer = LayerProfile.objects.get(id=submission_layer_id)
                    # Check if user has access
                    if not (request.user.is_staff or request.user.is_superuser or 
                            request.user.is_baker_tilly_admin or 
                            LayerProfile.objects.filter(id=submission_layer_id, app_users__user=request.user).exists()):
                        return Response({'error': f'You do not have access to the layer with ID {submission_layer_id}'}, status=403)
                except LayerProfile.DoesNotExist:
                    return Response({'error': f'Layer with ID {submission_layer_id} not found'}, status=404)
            
            # Validate metric exists
            try:
                metric = ESGMetric.objects.get(id=metric_id)
            except ESGMetric.DoesNotExist:
                return Response({
                    'error': f'Metric with ID {metric_id} not found'
                }, status=400)
            
            # Check if submission already exists for this metric/period/layer
            try:
                existing = ESGMetricSubmission.objects.get(
                    assignment=assignment,
                    metric=metric,
                    reporting_period=reporting_period,
                    layer=layer  # Also check the layer to ensure uniqueness
                )
                
                # Update existing submission
                existing.value = value
                existing.text_value = text_value
                existing.notes = notes
                existing.save()
                updated_submissions.append(existing)
                
                # Handle multi-value data if this is a multi-value metric
                if metric.is_multi_value and 'multi_values' in sub_data:
                    multi_values = sub_data.get('multi_values', {})
                    
                    # Process each field value
                    for field_key, field_value in multi_values.items():
                        try:
                            # Get the field definition
                            field = metric.value_fields.get(field_key=field_key)
                            
                            # Determine if value is numeric or text
                            if isinstance(field_value, (int, float)) or (
                                    isinstance(field_value, str) and 
                                    field_value.replace('.', '', 1).isdigit()):
                                numeric_value = float(field_value)
                                text_value = None
                            else:
                                numeric_value = None
                                text_value = str(field_value) if field_value is not None else None
                                
                            # Update or create the value
                            MetricValue.objects.update_or_create(
                                submission=existing,
                                field=field,
                                defaults={
                                    'numeric_value': numeric_value,
                                    'text_value': text_value
                                }
                            )
                        except MetricValueField.DoesNotExist:
                            # Log but don't fail if field doesn't exist
                            import logging
                            logger = logging.getLogger(__name__)
                            logger.warning(f"Field '{field_key}' not found for metric {metric.id}")
                
            except ESGMetricSubmission.DoesNotExist:
                # Create new submission
                submission = ESGMetricSubmission.objects.create(
                    assignment=assignment,
                    metric=metric,
                    value=value,
                    text_value=text_value,
                    reporting_period=reporting_period,
                    notes=notes,
                    submitted_by=request.user,
                    layer=layer
                )
                created_submissions.append(submission)
                
                # Handle multi-value data if this is a multi-value metric
                if metric.is_multi_value and 'multi_values' in sub_data:
                    multi_values = sub_data.get('multi_values', {})
                    
                    # Process each field value
                    for field_key, field_value in multi_values.items():
                        try:
                            # Get the field definition
                            field = metric.value_fields.get(field_key=field_key)
                            
                            # Determine if value is numeric or text
                            if isinstance(field_value, (int, float)) or (
                                    isinstance(field_value, str) and 
                                    field_value.replace('.', '', 1).isdigit()):
                                numeric_value = float(field_value)
                                text_value = None
                            else:
                                numeric_value = None
                                text_value = str(field_value) if field_value is not None else None
                                
                            # Create the value
                            MetricValue.objects.create(
                                submission=submission,
                                field=field,
                                numeric_value=numeric_value,
                                text_value=text_value
                            )
                        except MetricValueField.DoesNotExist:
                            # Log but don't fail if field doesn't exist
                            import logging
                            logger = logging.getLogger(__name__)
                            logger.warning(f"Field '{field_key}' not found for metric {metric.id}")
        
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
        # Implementation continues (too long for one code block)
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
        
        # Filter by layer if specified
        layer_id = request.query_params.get('layer_id')
        if layer_id:
            try:
                # Verify user has access to the layer
                layer = LayerProfile.objects.get(id=layer_id)
                if not (request.user.is_staff or request.user.is_superuser or 
                        request.user.is_baker_tilly_admin or
                        LayerProfile.objects.filter(id=layer_id, app_users__user=request.user).exists()):
                    return Response({'error': 'You do not have access to this layer'}, status=403)
                
                submissions = submissions.filter(layer=layer)
            except LayerProfile.DoesNotExist:
                return Response({'error': f'Layer with ID {layer_id} not found'}, status=404)
            
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
        
        # Optimize query with select_related
        submissions = submissions.select_related('metric', 'layer', 'submitted_by').order_by(sort_by)
        
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