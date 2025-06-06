"""
Views for managing ESG metric submissions.
"""

from rest_framework import viewsets, views, status, serializers
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db import transaction
from django.utils import timezone
from datetime import datetime
import copy
import logging

# Configure logger
logger = logging.getLogger(__name__)

from accounts.models import CustomUser, AppUser, LayerProfile
from accounts.services import get_accessible_layers, has_layer_access
from ..models import (
    ESGForm, ESGMetric, 
    Template, TemplateAssignment, TemplateFormSelection
)
from ..models.templates import ESGMetricSubmission, ESGMetricEvidence, ESGMetricBatchSubmission
from ..serializers.esg import (
    ESGMetricSubmissionSerializer, ESGMetricSubmissionCreateSerializer,
    ESGMetricEvidenceSerializer, ESGMetricBatchSubmissionSerializer,
    ESGMetricSubmissionVerifySerializer
)
from .utils import get_required_submission_count, attach_evidence_to_submissions
from ..services.calculations import validate_and_update_totals
from django.contrib.contenttypes.models import ContentType


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
        if self.action == 'create':
            return ESGMetricSubmissionCreateSerializer
        elif self.action == 'verify':
            return ESGMetricSubmissionVerifySerializer
        return self.serializer_class

    def perform_create(self, serializer):
        """
        Process a single submission during standard REST create operation.
        """
        # Get the data and calculate totals for time-based metrics
        if hasattr(serializer, 'validated_data') and 'data' in serializer.validated_data:
            data = serializer.validated_data['data']
            
            # Get metric object for calculation if available
            metric = None
            if 'metric' in serializer.validated_data:
                metric = serializer.validated_data['metric']
            
            # Update data with calculated fields if needed
            if data and isinstance(data, dict):
                try:
                    # Calculate totals based on the metric schema
                    updated_data = validate_and_update_totals(data, metric)
                    serializer.validated_data['data'] = updated_data
                except Exception as e:
                    # Log the error but continue with original data
                    logger.warning(f"Calculation error during submission creation: {e}")
        
        # Set default values for new fields if not provided
        if 'submission_identifier' not in serializer.validated_data:
            serializer.validated_data['submission_identifier'] = ''
        if 'data_source' not in serializer.validated_data:
            serializer.validated_data['data_source'] = ''
        
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
                # For time-based metrics, check the structure of the JSON data
                if metric.requires_time_reporting:
                    # Get submissions for this metric
                    metric_submissions = submissions.filter(metric=metric)
                    
                    if not metric_submissions.exists():
                        all_required_metrics_submitted = False
                        break
                    
                    # For simplicity, consider any submission with a 'periods' object containing data as complete
                    # In a more complex implementation, you could check for specific required periods
                    submission_is_complete = False
                    for sub in metric_submissions:
                        if sub.data and isinstance(sub.data, dict) and 'periods' in sub.data:
                            periods = sub.data['periods']
                            if isinstance(periods, dict) and len(periods) > 0:
                                # Check that at least one period has a value
                                for period_key, period_data in periods.items():
                                    if isinstance(period_data, dict) and 'value' in period_data:
                                        submission_is_complete = True
                                        break
                        
                        if submission_is_complete:
                            break
                    
                    if not submission_is_complete:
                        all_required_metrics_submitted = False
                        break
                else:
                    # For regular metrics, we need at least one submission with a value
                    has_valid_submission = False
                    for sub in submissions.filter(metric=metric):
                        if sub.data and isinstance(sub.data, dict) and 'value' in sub.data:
                            has_valid_submission = True
                            break
                    
                    if not has_valid_submission:
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
                            # For time-based metrics, check the structure of the JSON data
                            metric_submissions = submissions.filter(metric=metric)
                            
                            if not metric_submissions.exists():
                                form_metrics_submitted = False
                                break
                            
                            # Look for a submission with a valid periods structure
                            submission_is_complete = False
                            for sub in metric_submissions:
                                if sub.data and isinstance(sub.data, dict) and 'periods' in sub.data:
                                    periods = sub.data['periods']
                                    if isinstance(periods, dict) and len(periods) > 0:
                                        # Check that at least one period has a value
                                        for period_key, period_data in periods.items():
                                            if isinstance(period_data, dict) and 'value' in period_data:
                                                submission_is_complete = True
                                                break
                                
                                if submission_is_complete:
                                    break
                            
                            if not submission_is_complete:
                                form_metrics_submitted = False
                                break
                        else:
                            # For regular metrics, check if any submission has a valid value
                            has_valid_submission = False
                            for sub in submissions.filter(metric=metric):
                                if sub.data and isinstance(sub.data, dict) and 'value' in sub.data:
                                    has_valid_submission = True
                                    break
                            
                            if not has_valid_submission:
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
        - submissions: List of submission objects with metric_id, data
        - auto_attach_evidence: (Optional) Boolean to automatically attach standalone evidence
        - default_layer_id: (Optional) Default layer ID for all submissions
        - update_timestamp: (Optional) Boolean to update the submitted_at timestamp
        - force_new_submission: (Optional) Boolean to force creating a new submission even if one exists
        """
        serializer = ESGMetricBatchSubmissionSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        # Get validated data
        validated_data = serializer.validated_data
        assignment_id = validated_data['assignment_id']
        submissions_data = validated_data['submissions']
        name = validated_data.get('name', '')
        notes = validated_data.get('notes', '')
        layer_id = validated_data.get('layer_id')
        update_timestamp = validated_data.get('update_timestamp', False)
        force_new_submission = validated_data.get('force_new_submission', False)
        submission_identifier = validated_data.get('submission_identifier', '')
        
        # Get assignment and validate
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
        
        # Get default layer if provided
        default_layer = None
        if layer_id:
            try:
                default_layer = LayerProfile.objects.get(id=layer_id)
                # Check if user has access
                if not (request.user.is_staff or request.user.is_superuser or 
                        request.user.is_baker_tilly_admin or 
                        LayerProfile.objects.filter(id=layer_id, app_users__user=request.user).exists()):
                    return Response({'error': 'You do not have access to the specified layer'}, status=403)
            except LayerProfile.DoesNotExist:
                return Response({'error': f'Layer with ID {layer_id} not found'}, status=404)
        else:
            # Use assignment's layer as default
            default_layer = assignment.layer
            
        # Create batch record
        batch = ESGMetricBatchSubmission.objects.create(
            assignment=assignment,
            name=name,
            notes=notes,
            submitted_by=request.user,
            layer=default_layer
        )
        
        # Process each submission
        created_submissions = []
        updated_submissions = []
        failed_submissions = []
        
        for sub_data in submissions_data:
            metric_id = sub_data.get('metric_id')
            data = sub_data.get('data')
            notes = sub_data.get('notes', '')
            sub_identifier = sub_data.get('submission_identifier', submission_identifier)
            sub_force_new = sub_data.get('force_new_submission', force_new_submission)
            data_source = sub_data.get('data_source', '')
            
            # Validate metric exists
            try:
                metric = ESGMetric.objects.get(id=metric_id)
            except ESGMetric.DoesNotExist:
                failed_submissions.append({
                    'metric_id': metric_id,
                    'error': f'Metric with ID {metric_id} not found'
                })
                continue
            
            # Calculate and validate totals
            if data and isinstance(data, dict):
                try:
                    # Calculate totals for the data
                    data = validate_and_update_totals(data, metric)
                except Exception as e:
                    # Log error but continue with original data
                    logger.warning(f"Calculation error for metric {metric_id}: {e}")
                    failed_submissions.append({
                        'metric_id': metric_id,
                        'error': f'Calculation error: {str(e)}'
                    })
                    # Continue with the original data
            
            # Get layer for this submission (submission-specific or default)
            layer = default_layer
            submission_layer_id = sub_data.get('layer_id')
            if submission_layer_id:
                try:
                    layer = LayerProfile.objects.get(id=submission_layer_id)
                    # Check if user has access
                    if not (request.user.is_staff or request.user.is_superuser or 
                            request.user.is_baker_tilly_admin or 
                            LayerProfile.objects.filter(id=submission_layer_id, app_users__user=request.user).exists()):
                        failed_submissions.append({
                            'metric_id': metric_id,
                            'error': f'No access to layer with ID {submission_layer_id}'
                        })
                        continue
                except LayerProfile.DoesNotExist:
                    failed_submissions.append({
                        'metric_id': metric_id,
                        'error': f'Layer with ID {submission_layer_id} not found'
                    })
                    continue
            
            # Handle updates if an explicit update_id was provided
            if 'update_id' in sub_data:
                try:
                    submission = ESGMetricSubmission.objects.get(id=sub_data['update_id'])
                    
                    # Update fields
                    submission.data = data
                    submission.notes = notes
                    submission.batch_submission = batch
                    
                    # Update metadata fields if provided
                    if sub_identifier:
                        submission.submission_identifier = sub_identifier
                    if data_source:
                        submission.data_source = data_source
                    
                    # Update timestamp if requested
                    if update_timestamp:
                        submission.submitted_at = timezone.now()
                    
                    # Only update layer if specified
                    if layer:
                        submission.layer = layer
                        
                    submission.save()
                    updated_submissions.append(submission)
                    
                except ESGMetricSubmission.DoesNotExist:
                    # If submission no longer exists, create a new one
                    submission = ESGMetricSubmission.objects.create(
                        assignment=assignment,
                        metric=metric,
                        data=data,
                        notes=notes,
                        submitted_by=request.user,
                        layer=layer,
                        batch_submission=batch,
                        submission_identifier=sub_identifier,
                        data_source=data_source
                    )
                    created_submissions.append(submission)
            else:
                # If force_new_submission is True, always create a new submission
                if sub_force_new:
                    submission = ESGMetricSubmission.objects.create(
                        assignment=assignment,
                        metric=metric,
                        data=data,
                        notes=notes,
                        submitted_by=request.user,
                        layer=layer,
                        batch_submission=batch,
                        submission_identifier=sub_identifier,
                        data_source=data_source
                    )
                    created_submissions.append(submission)
                else:
                    # Try to find an exact match by identifier if one is provided
                    existing_submission = None
                    if sub_identifier:
                        try:
                            existing_submission = ESGMetricSubmission.objects.get(
                                assignment=assignment,
                                metric=metric,
                                layer=layer,
                                submission_identifier=sub_identifier
                            )
                        except ESGMetricSubmission.DoesNotExist:
                            pass
                    
                    # If no identifier match but we're not forcing a new submission,
                    # look for any submission with the same metric/layer and no identifier
                    if not existing_submission and not sub_identifier and not sub_force_new:
                        try:
                            existing_submission = ESGMetricSubmission.objects.filter(
                                assignment=assignment,
                                metric=metric,
                                layer=layer,
                                submission_identifier=''
                            ).first()
                        except ESGMetricSubmission.DoesNotExist:
                            pass
                    
                    # Update existing submission if found
                    if existing_submission:
                        existing_submission.data = data
                        existing_submission.notes = notes
                        existing_submission.batch_submission = batch
                        
                        # Update metadata fields if provided
                        if sub_identifier:
                            existing_submission.submission_identifier = sub_identifier
                        if data_source:
                            existing_submission.data_source = data_source
                        
                        # Update timestamp if requested
                        if update_timestamp:
                            existing_submission.submitted_at = timezone.now()
                        
                        existing_submission.save()
                        updated_submissions.append(existing_submission)
                    else:
                        # Create new submission if no existing found or if using identifier
                        submission = ESGMetricSubmission.objects.create(
                            assignment=assignment,
                            metric=metric,
                            data=data,
                            notes=notes,
                            submitted_by=request.user,
                            layer=layer,
                            batch_submission=batch,
                            submission_identifier=sub_identifier,
                            data_source=data_source
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
        
        # Prepare response
        response_data = {
            'status': 'success',
            'message': f'Created {len(created_submissions)} and updated {len(updated_submissions)} submissions',
            'evidence_attached': evidence_count,
            'assignment_status': assignment.status,
            'batch_id': batch.id
        }
        
        if failed_submissions:
            response_data['failed_submissions'] = failed_submissions
        
        return Response(response_data)

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
                    # For time-based metrics, check the structure of the JSON data
                    metric_submissions = submissions.filter(metric=metric)
                    
                    if not metric_submissions.exists():
                        incomplete_time_based.append({
                            'id': metric.id,
                            'name': metric.name,
                            'form': metric.form.name,
                            'reporting_frequency': metric.reporting_frequency,
                            'submitted_count': 0,
                            'required_count': 1  # At least one submission with periods
                        })
                        continue
                    
                    # Look for a submission with a valid periods structure
                    submission_is_complete = False
                    for sub in metric_submissions:
                        if sub.data and isinstance(sub.data, dict) and 'periods' in sub.data:
                            periods = sub.data['periods']
                            if isinstance(periods, dict) and len(periods) > 0:
                                # Check that at least one period has a value
                                for period_key, period_data in periods.items():
                                    if isinstance(period_data, dict) and 'value' in period_data:
                                        submission_is_complete = True
                                        break
                        
                        if submission_is_complete:
                            break
                    
                    if not submission_is_complete:
                        incomplete_time_based.append({
                            'id': metric.id,
                            'name': metric.name,
                            'form': metric.form.name,
                            'reporting_frequency': metric.reporting_frequency,
                            'issue': 'Missing or incomplete periods data in JSON'
                        })
                else:
                    # For regular metrics, check if any submission has a valid value
                    has_valid_submission = False
                    for sub in submissions.filter(metric=metric):
                        if sub.data and isinstance(sub.data, dict) and 'value' in sub.data:
                            has_valid_submission = True
                            break
                    
                    if not has_valid_submission:
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
                        # For time-based metrics, check the structure of the JSON data
                        metric_submissions = submissions.filter(metric=metric)
                        
                        if not metric_submissions.exists():
                            form_metrics_submitted = False
                            break
                        
                        # Look for a submission with a valid periods structure
                        submission_is_complete = False
                        for sub in metric_submissions:
                            if sub.data and isinstance(sub.data, dict) and 'periods' in sub.data:
                                periods = sub.data['periods']
                                if isinstance(periods, dict) and len(periods) > 0:
                                    # Check that at least one period has a value
                                    for period_key, period_data in periods.items():
                                        if isinstance(period_data, dict) and 'value' in period_data:
                                            submission_is_complete = True
                                            break
                            
                            if submission_is_complete:
                                break
                        
                        if not submission_is_complete:
                            form_metrics_submitted = False
                            break
                    else:
                        # For regular metrics, check if any submission has a valid value
                        has_valid_submission = False
                        for sub in submissions.filter(metric=metric):
                            if sub.data and isinstance(sub.data, dict) and 'value' in sub.data:
                                has_valid_submission = True
                                break
                        
                        if not has_valid_submission:
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

    @action(detail=False, methods=['get'])
    def available_layers(self, request):
        """
        Get all layers that the current user has access to.
        This is useful for the frontend to show layer options when creating or filtering submissions.
        
        Optional parameters:
            assignment_id: Filter layers to those relevant for a specific assignment
        """
        # Get all layers the user has access to using the existing utility function
        user_layers = get_accessible_layers(request.user)
        
        # Filter by assignment if provided
        assignment_id = request.query_params.get('assignment_id')
        if assignment_id:
            try:
                assignment = TemplateAssignment.objects.get(id=assignment_id)
                
                # For assignments, we should include:
                # 1. The assignment's own layer
                # 2. Any child layers of the assignment's layer
                
                # Add the assignment's layer
                assignment_layer = assignment.layer
                if assignment_layer not in user_layers:
                    if not has_layer_access(request.user, assignment_layer):
                        return Response({
                            'error': f'You do not have access to layer {assignment_layer.id}'
                        }, status=403)
                
                # Get all layers the user has access to that are related to this assignment
                available_layers = []
                
                # Include the assignment's own layer
                available_layers.append({
                    'id': assignment_layer.id,
                    'name': assignment_layer.company_name,
                    'type': assignment_layer.layer_type,
                    'location': assignment_layer.company_location,
                    'parent': None
                })
                
                # Include child layers if the assignment layer is a group
                if assignment_layer.layer_type == 'GROUP':
                    # Get subsidiaries
                    for subsidiary in user_layers.filter(
                        layer_type='SUBSIDIARY',
                        subsidiarylayer__group_layer=assignment_layer
                    ):
                        available_layers.append({
                            'id': subsidiary.id,
                            'name': subsidiary.company_name,
                            'type': subsidiary.layer_type,
                            'location': subsidiary.company_location,
                            'parent': {
                                'id': assignment_layer.id,
                                'name': assignment_layer.company_name
                            }
                        })
                        
                        # Get branches of this subsidiary
                        for branch in user_layers.filter(
                            layer_type='BRANCH',
                            branchlayer__subsidiary_layer__id=subsidiary.id
                        ):
                            available_layers.append({
                                'id': branch.id,
                                'name': branch.company_name,
                                'type': branch.layer_type,
                                'location': branch.company_location,
                                'parent': {
                                    'id': subsidiary.id,
                                    'name': subsidiary.company_name
                                }
                            })
                
                # Include parent layers (e.g., if assignment is for a subsidiary, include its group)
                if assignment_layer.layer_type == 'SUBSIDIARY':
                    try:
                        group_layer = assignment_layer.subsidiarylayer.group_layer
                        if group_layer in user_layers:
                            # Add at the beginning as it's the top-level parent
                            available_layers.insert(0, {
                                'id': group_layer.id,
                                'name': group_layer.company_name,
                                'type': group_layer.layer_type,
                                'location': group_layer.company_location,
                                'parent': None
                            })
                            # Update the assignment layer's parent reference
                            available_layers[1]['parent'] = {
                                'id': group_layer.id,
                                'name': group_layer.company_name
                            }
                    except Exception:
                        # Just continue if we can't get the parent
                        pass
                
                # If it's a branch, include both its subsidiary and group
                elif assignment_layer.layer_type == 'BRANCH':
                    try:
                        subsidiary_layer = assignment_layer.branchlayer.subsidiary_layer
                        if subsidiary_layer in user_layers:
                            # Add before the assignment layer
                            available_layers.insert(0, {
                                'id': subsidiary_layer.id,
                                'name': subsidiary_layer.company_name,
                                'type': subsidiary_layer.layer_type,
                                'location': subsidiary_layer.company_location,
                                'parent': None
                            })
                            # Update the assignment layer's parent reference
                            available_layers[1]['parent'] = {
                                'id': subsidiary_layer.id,
                                'name': subsidiary_layer.company_name
                            }
                            
                            # Also add the group
                            try:
                                group_layer = subsidiary_layer.subsidiarylayer.group_layer
                                if group_layer in user_layers:
                                    # Add at the very beginning
                                    available_layers.insert(0, {
                                        'id': group_layer.id,
                                        'name': group_layer.company_name,
                                        'type': group_layer.layer_type,
                                        'location': group_layer.company_location,
                                        'parent': None
                                    })
                                    # Update the subsidiary layer's parent reference
                                    available_layers[1]['parent'] = {
                                        'id': group_layer.id,
                                        'name': group_layer.company_name
                                    }
                            except Exception:
                                pass
                    except Exception:
                        # Just continue if we can't get the parent
                        pass
                
                return Response(available_layers)
            except TemplateAssignment.DoesNotExist:
                return Response({'error': f'Assignment with ID {assignment_id} not found'}, status=404)
        
        # Prepare all accessible layers
        result = []
        
        # First, include all GROUP layers
        for layer in user_layers.filter(layer_type='GROUP').order_by('company_name'):
            result.append({
                'id': layer.id,
                'name': layer.company_name,
                'type': layer.layer_type,
                'location': layer.company_location,
                'parent': None
            })
        
        # Then include all SUBSIDIARY layers with parent information
        for layer in user_layers.filter(layer_type='SUBSIDIARY').order_by('company_name'):
            parent = None
            try:
                group_layer = layer.subsidiarylayer.group_layer
                if group_layer in user_layers:
                    parent = {
                        'id': group_layer.id,
                        'name': group_layer.company_name
                    }
            except Exception:
                pass
            
            result.append({
                'id': layer.id,
                'name': layer.company_name,
                'type': layer.layer_type,
                'location': layer.company_location,
                'parent': parent
            })
        
        # Finally, include all BRANCH layers with parent information
        for layer in user_layers.filter(layer_type='BRANCH').order_by('company_name'):
            parent = None
            try:
                subsidiary_layer = layer.branchlayer.subsidiary_layer
                if subsidiary_layer in user_layers:
                    parent = {
                        'id': subsidiary_layer.id,
                        'name': subsidiary_layer.company_name
                    }
            except Exception:
                pass
            
            result.append({
                'id': layer.id,
                'name': layer.company_name,
                'type': layer.layer_type,
                'location': layer.company_location,
                'parent': parent
            })
        
        return Response(result)

    @action(detail=False, methods=['get'])
    def sum_by_layer(self, request):
        """
        Get aggregated values for metric submissions by layer.
        This endpoint allows aggregating metrics across different layers for comparison.

        Parameters:
            assignment_id: Required. The template assignment to aggregate data for.
            metric_ids: Comma-separated list of metric IDs to include in the aggregation.
            layer_ids: Comma-separated list of layer IDs to include in the aggregation.
            period: Optional. JSON path to specific period within data (e.g. "periods.Q1-2024")
            
        Returns:
            Aggregated values for each metric by layer
        """
        # Required parameters
        assignment_id = request.query_params.get('assignment_id')
        if not assignment_id:
            return Response({'error': 'assignment_id is required'}, status=400)
            
        # Get metrics to aggregate
        metric_ids_param = request.query_params.get('metric_ids')
        if not metric_ids_param:
            return Response({'error': 'metric_ids is required'}, status=400)
        
        try:
            metric_ids = [int(id.strip()) for id in metric_ids_param.split(',') if id.strip()]
            if not metric_ids:
                return Response({'error': 'No valid metric IDs provided'}, status=400)
        except ValueError:
            return Response({'error': 'Invalid metric_ids format. Use comma-separated integers.'}, status=400)
            
        # Get layers to aggregate
        layer_ids_param = request.query_params.get('layer_ids')
        if not layer_ids_param:
            return Response({'error': 'layer_ids is required'}, status=400)
            
        try:
            layer_ids = [int(id.strip()) for id in layer_ids_param.split(',') if id.strip()]
            if not layer_ids:
                return Response({'error': 'No valid layer IDs provided'}, status=400)
        except ValueError:
            return Response({'error': 'Invalid layer_ids format. Use comma-separated integers.'}, status=400)
            
        # Validate assignment
        try:
            assignment = TemplateAssignment.objects.get(id=assignment_id)
        except TemplateAssignment.DoesNotExist:
            return Response({'error': f'Assignment with ID {assignment_id} not found'}, status=404)
            
        # Check permissions
        user_layers = get_accessible_layers(request.user)
        accessible_layer_ids = set(user_layers.values_list('id', flat=True))
        
        # Check if user has access to all requested layers
        inaccessible_layers = set(layer_ids) - accessible_layer_ids
        if inaccessible_layers:
            return Response({
                'error': f'You do not have access to the following layers: {", ".join(map(str, inaccessible_layers))}'
            }, status=403)
            
        # Validate metrics
        metrics = ESGMetric.objects.filter(id__in=metric_ids)
        if metrics.count() != len(metric_ids):
            found_ids = set(metrics.values_list('id', flat=True))
            missing_ids = set(metric_ids) - found_ids
            return Response({
                'error': f'The following metrics were not found: {", ".join(map(str, missing_ids))}'
            }, status=404)
        
        # Optional period filter
        period_path = request.query_params.get('period')
        
        # Fetch submissions that match the criteria
        submissions = ESGMetricSubmission.objects.filter(
            assignment_id=assignment_id,
            metric_id__in=metric_ids,
            layer_id__in=layer_ids
        ).select_related('metric', 'layer')
        
        # Prepare the result structure
        result = {
            'assignment_id': assignment_id,
            'period_path': period_path,
            'metrics': {},
            'layers': {},
            'aggregation': []
        }
        
        # Create lookup dictionaries for metrics and layers
        for metric in metrics:
            result['metrics'][metric.id] = {
                'id': metric.id,
                'name': metric.name,
                'unit_type': metric.unit_type,
                'custom_unit': metric.custom_unit,
                'requires_time_reporting': metric.requires_time_reporting,
                'form_code': metric.form.code
            }
            
        for layer_id in layer_ids:
            layer = user_layers.get(id=layer_id)
            result['layers'][layer_id] = {
                'id': layer_id,
                'name': layer.company_name,
                'type': layer.layer_type,
                'location': layer.company_location
            }
            
        # Helper function to extract value from JSON data using path
        def get_value_from_data(data, path=None):
            if not path:
                # If no path specified, try to get the 'value' field at the root level
                return data.get('value')
                
            # Navigate through the path to get the value
            parts = path.split('.')
            current = data
            for part in parts:
                if isinstance(current, dict) and part in current:
                    current = current[part]
                else:
                    return None
            
            # If we reached a dict with a 'value' key, return that
            if isinstance(current, dict) and 'value' in current:
                return current['value']
            return current  # Otherwise return the object at the path
        
        # Build aggregation data structure
        for metric_id in metric_ids:
            metric_data = {
                'metric_id': metric_id,
                'values_by_layer': {}
            }
            
            for layer_id in layer_ids:
                # Filter submissions for this metric and layer
                layer_submissions = submissions.filter(
                    metric_id=metric_id,
                    layer_id=layer_id
                )
                
                # Calculate aggregated value
                if period_path:
                    # For period-specific query, get the specified period data
                    submission = layer_submissions.first()
                    if submission and submission.data:
                        value = get_value_from_data(submission.data, period_path)
                    else:
                        value = None
                    submission_id = submission.id if submission else None
                else:
                    # For metrics with time reporting without a specific period, get the whole data structure
                    submission = layer_submissions.first()
                    if submission:
                        value = submission.data
                    else:
                        value = None
                    submission_id = submission.id if submission else None
                
                metric_data['values_by_layer'][layer_id] = {
                    'value': value,
                    'submission_id': submission_id,
                    'data': submission.data if submission else None
                }
                
            result['aggregation'].append(metric_data)
            
        return Response(result)

    @action(detail=True, methods=['post'])
    def clone(self, request, *args, **kwargs):
        """
        Create a copy of the current metric submission for a new reporting period.
        """
        instance = self.get_object()
        
        # Get parameters for the new period
        new_period_start = request.data.get('period_start')
        new_period_end = request.data.get('period_end')
        new_name = request.data.get('name', f"Copy of {instance.metric.name}")
        
        # Validate period dates
        if not new_period_end:
            return Response(
                {"detail": "New period_end date is required"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
            
        try:
            # Convert to date objects if they are strings
            if isinstance(new_period_end, str):
                new_period_end = datetime.strptime(new_period_end, '%Y-%m-%d').date()
            if new_period_start and isinstance(new_period_start, str):
                new_period_start = datetime.strptime(new_period_start, '%Y-%m-%d').date()
        except ValueError:
            return Response(
                {"detail": "Invalid date format. Use YYYY-MM-DD"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Create a new instance with copied base attributes
        new_instance = ESGMetricSubmission(
            assignment=instance.assignment,
            metric=instance.metric,
            notes=instance.notes,
            submitted_by=request.user,
            layer=instance.layer
        )
        
        # Copy the data structure but reset values if needed
        if instance.data:
            # Create a deep copy
            new_data = copy.deepcopy(instance.data)
            
            # Reset values in periods if requested
            if request.data.get('reset_values', False):
                if 'periods' in new_data and isinstance(new_data['periods'], dict):
                    # Reset based on schema structure
                    for period_key, period_data in new_data['periods'].items():
                        if isinstance(period_data, dict):
                            # If it's a nested structure (like HK/PRC or CLP/HKE)
                            if any(k in period_data for k in ['HK', 'PRC', 'CLP', 'HKE']):
                                for region_key, region_data in list(period_data.items()):
                                    if isinstance(region_data, dict) and 'value' in region_data:
                                        region_data['value'] = None
                            # If it's a simple value/unit structure
                            elif 'value' in period_data:
                                period_data['value'] = None
            
            # Update any total_consumption fields
            try:
                new_data = validate_and_update_totals(new_data, instance.metric)
            except Exception as e:
                logger.warning(f"Calculation error during cloning: {e}")
                # Continue with original data
                
            new_instance.data = new_data
        
        # Save the new instance
        new_instance.save()
        
        # Return the new instance
        serializer = self.get_serializer(new_instance)
        return Response(serializer.data) 