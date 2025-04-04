"""
Views for managing ESG metric submissions.
"""

from rest_framework import viewsets, views, status, serializers
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db import transaction, models
from django.utils import timezone
import logging

from accounts.models import CustomUser, AppUser, LayerProfile
from accounts.services import get_accessible_layers, has_layer_access
from ...models import (
    ESGForm, ESGMetric, 
    Template, TemplateAssignment, TemplateFormSelection,
    ReportedMetricValue
)
from ...models.templates import (
    ESGMetricSubmission, ESGMetricEvidence,
    MetricValueField, MetricValue
)
from ...serializers.templates import (
    ESGMetricSubmissionSerializer, ESGMetricSubmissionCreateSerializer,
    ESGMetricEvidenceSerializer, ESGMetricBatchSubmissionSerializer,
    ESGMetricSubmissionVerifySerializer
)
from ..utils import get_required_submission_count, attach_evidence_to_submissions
from ...services.aggregation import calculate_report_value

logger = logging.getLogger(__name__)

class ESGMetricSubmissionViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing ESG metric submission INPUTS (raw data).
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
        """Handle creation of a single submission input."""
        submission = serializer.save(submitted_by=self.request.user)
        
        # --- Trigger Aggregation on Create --- 
        # Check if the metric aggregates and if context is complete
        if submission.metric.aggregates_inputs and submission.layer and submission.reporting_period:
            try:
                calculate_report_value(
                    submission.assignment, 
                    submission.metric, 
                    submission.reporting_period, 
                    submission.layer
                )
            except Exception as e:
                 logger.error(f"Aggregation failed for single create context ({submission.assignment}, {submission.metric}, {submission.reporting_period}, {submission.layer}): {e}", exc_info=True)
        elif submission.metric.aggregates_inputs:
            logger.warning(f"Cannot trigger aggregation for created submission ID {submission.id}: Missing layer or reporting_period.")
        # -------------------------------------

        # Check form completion - using the new logic based on ReportedMetricValue
        self._check_form_completion(submission.assignment) # Pass assignment for context
        return submission
    
    def perform_update(self, serializer):
        """Handle update of a single submission input and trigger re-aggregation."""
        # Get pre-save state to know the old context if it changed
        instance = serializer.instance
        old_context = None
        if instance.metric.aggregates_inputs and instance.layer and instance.reporting_period:
            old_context = (instance.assignment, instance.metric, instance.reporting_period, instance.layer)

        submission = serializer.save() # Save changes first

        # --- Trigger Aggregation on Update --- 
        new_context = None
        if submission.metric.aggregates_inputs and submission.layer and submission.reporting_period:
            new_context = (submission.assignment, submission.metric, submission.reporting_period, submission.layer)

        contexts_to_recalculate = set()
        if new_context:
            contexts_to_recalculate.add(new_context)
        # If the context itself changed (e.g., reporting_period was edited), recalculate the old context too
        if old_context and old_context != new_context:
             contexts_to_recalculate.add(old_context)

        for context_tuple in contexts_to_recalculate:
            try:
                calculate_report_value(*context_tuple)
            except Exception as e:
                 logger.error(f"Aggregation failed for update context {context_tuple}: {e}", exc_info=True)
        # -------------------------------------

        # Check form completion - using the new logic based on ReportedMetricValue
        self._check_form_completion(submission.assignment)

    def perform_destroy(self, instance):
        """Handle deletion of a single submission input and trigger re-aggregation."""
        # Store context before deleting
        context_to_recalculate = None
        if instance.metric.aggregates_inputs and instance.layer and instance.reporting_period:
            context_to_recalculate = (
                instance.assignment, 
                instance.metric, 
                instance.reporting_period, 
                instance.layer
            )
        assignment_to_check = instance.assignment

        # Call parent method to delete
        super().perform_destroy(instance)

        # --- Trigger Aggregation on Delete --- 
        if context_to_recalculate:
            try:
                calculate_report_value(*context_to_recalculate)
            except Exception as e:
                 logger.error(f"Aggregation failed for delete context {context_to_recalculate}: {e}", exc_info=True)
        # -------------------------------------

        # Re-check form completion status for the assignment
        self._check_form_completion(assignment_to_check)

    def _check_form_completion(self, assignment):
        """
        Check if an assignment is complete based on ReportedMetricValue existence.
        This method now takes the assignment directly.
        """
        logger.debug(f"Checking completion status for assignment {assignment.id}")

        # Get all required metrics for the forms in this template assignment
        required_metrics = ESGMetric.objects.filter(
            form__in=assignment.template.selected_forms.all(),
            is_required=True
        )

        if not required_metrics.exists():
            logger.debug(f"No required metrics found for assignment {assignment.id}. Marking complete.")
            # Consider if an assignment with no required metrics should be SUBMITTED or handled differently
            if assignment.status in ['PENDING', 'IN_PROGRESS']:
                assignment.status = 'SUBMITTED' # Or maybe a different status? 'N/A'?
                assignment.completed_at = timezone.now()
                assignment.save()
            return # Nothing more to check

        all_required_metrics_reported = True
        completion_timestamp = timezone.now()

        # Fetch all existing reported values for this assignment to minimize queries
        # Assumes layer context for reported value matches assignment layer - might need adjustment if layers differ
        existing_reported_values = ReportedMetricValue.objects.filter(
            assignment=assignment,
            layer=assignment.layer # Check against the assignment's layer
        ).values_list('metric_id', 'reporting_period')
        
        reported_value_lookup = {(metric_id, period) for metric_id, period in existing_reported_values}

        for metric in required_metrics:
            if metric.requires_time_reporting:
                expected_periods = get_required_submission_count(metric, assignment, return_dates=True)
                if not expected_periods: # Function returned empty list
                     logger.warning(f"Could not determine expected periods for time-based metric {metric.id} on assignment {assignment.id}")
                     all_required_metrics_reported = False
                     break # Cannot determine completeness

                for period_date in expected_periods:
                    # Check if a ReportedMetricValue exists for this specific metric, period, and layer
                    if (metric.id, period_date) not in reported_value_lookup:
                        logger.debug(f"Missing ReportedMetricValue for metric {metric.id} ({metric.name}), period {period_date}, layer {assignment.layer.id}")
                        all_required_metrics_reported = False
                        break # Missing a required period for this metric
            else:
                 # For non-time-based metrics, expect one ReportedMetricValue (period might be None or end date?)
                 # Let's assume period should match assignment end date for simplicity for now.
                 # TODO: Define policy for reporting_period on non-time-based ReportedMetricValue
                 expected_period_for_non_time_based = assignment.reporting_period_end
                 if (metric.id, expected_period_for_non_time_based) not in reported_value_lookup:
                    logger.debug(f"Missing ReportedMetricValue for non-time-based metric {metric.id} ({metric.name}), expected period {expected_period_for_non_time_based}, layer {assignment.layer.id}")
                    all_required_metrics_reported = False
            
            if not all_required_metrics_reported:
                break # Stop checking metrics if one fails
        
        # Update assignment status if all required final values are reported
        if all_required_metrics_reported and assignment.status in ['PENDING', 'IN_PROGRESS']:
            logger.info(f"Marking assignment {assignment.id} as SUBMITTED.")
            assignment.status = 'SUBMITTED'
            assignment.completed_at = completion_timestamp
            assignment.save()

            # Update form selection completion status (based on reported values)
            # TODO: Revisit logic for attributing completion user if needed
            # For now, just mark forms complete if all their required metrics have reported values.
            for form_selection in assignment.template.templateformselection_set.filter(is_completed=False):
                form = form_selection.form
                form_metrics = required_metrics.filter(form=form)
                form_metrics_complete = True
                for metric in form_metrics:
                    if metric.requires_time_reporting:
                        expected_periods = get_required_submission_count(metric, assignment, return_dates=True)
                        for period_date in expected_periods:
                            if (metric.id, period_date) not in reported_value_lookup:
                                form_metrics_complete = False
                                break
                    else:
                        expected_period_for_non_time_based = assignment.reporting_period_end
                        if (metric.id, expected_period_for_non_time_based) not in reported_value_lookup:
                            form_metrics_complete = False
                    if not form_metrics_complete:
                        break
                
                if form_metrics_complete:
                    logger.info(f"Marking form selection {form_selection.id} (Form: {form.name}) as completed for assignment {assignment.id}.")
                    form_selection.is_completed = True
                    form_selection.completed_at = completion_timestamp
                    # form_selection.completed_by = ? # Need a way to determine this if required
                    form_selection.save()
        
        elif not all_required_metrics_reported and assignment.status == 'SUBMITTED':
             # If inputs were deleted causing incompleteness, revert status
             logger.info(f"Reverting assignment {assignment.id} status to IN_PROGRESS due to missing reported values.")
             assignment.status = 'IN_PROGRESS'
             assignment.completed_at = None
             assignment.save()
             # Also revert associated form selections
             assignment.template.templateformselection_set.update(is_completed=False, completed_at=None, completed_by=None)

    @action(detail=False, methods=['post'])
    @transaction.atomic
    def batch_submit(self, request):
        """
        Submit multiple metric INPUTS (raw data) at once.
        Aggregates values for relevant metrics into ReportedMetricValue.
        
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
        
        # Create submission inputs
        created_submissions = []
        # updated_submissions = [] # No longer tracking updates here
        
        for sub_data in submissions_data:
            metric_id = sub_data.get('metric_id')
            value = sub_data.get('value')
            text_value = sub_data.get('text_value')
            reporting_period = sub_data.get('reporting_period')
            notes = sub_data.get('notes', '')
            source_identifier = sub_data.get('source_identifier') # Get optional source identifier
            
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
            
            # --- Approach B Change: Always create a new input submission ---
            # REMOVED: The try/except block that looked for existing submissions to update
            # -------------------------------------------------------------

            # Create new submission input record
            submission = ESGMetricSubmission.objects.create(
                assignment=assignment,
                metric=metric,
                value=value,
                text_value=text_value,
                reporting_period=reporting_period,
                notes=notes,
                submitted_by=request.user,
                layer=layer, # Use the determined layer for this input
                source_identifier=source_identifier # Pass the source identifier
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
                            text_value_mv = None # Use different name to avoid conflict
                        else:
                            numeric_value = None
                            text_value_mv = str(field_value) if field_value is not None else None

                        # Create the MetricValue linked to the new submission input
                        MetricValue.objects.create(
                            submission=submission, # Link to the newly created submission
                            field=field,
                            numeric_value=numeric_value,
                            text_value=text_value_mv
                        )
                    except MetricValueField.DoesNotExist:
                        # Log but don't fail if field doesn't exist
                        # import logging # Already imported at top
                        logger.warning(f"Field '{field_key}' not found for metric {metric.id}")

        # --- Approach B Change: Trigger Aggregation --- 
        affected_contexts = set()
        for sub in created_submissions: # Only process newly created ones
            # Ensure layer is not None and period is not None before adding to context
            if sub.metric.aggregates_inputs and sub.layer and sub.reporting_period:
                affected_contexts.add((
                    sub.assignment,
                    sub.metric,
                    sub.reporting_period,
                    sub.layer
                ))
            elif sub.metric.aggregates_inputs and (not sub.layer or not sub.reporting_period):
                # Log a warning if essential context is missing for an aggregating metric
                # import logging # Already imported at top
                logger.warning(f"Cannot trigger aggregation for submission ID {sub.id}: Missing layer or reporting_period.")


        # Trigger calculation for each affected context
        if affected_contexts:
            # from ...services.aggregation import calculate_report_value # Already imported at top
            for context_tuple in affected_contexts:
                try:
                    calculate_report_value(*context_tuple)
                except Exception as e:
                    # Log error but don't fail the whole batch? Decide error handling.
                    # import logging # Already imported at top
                    logger.error(f"Aggregation failed for context {context_tuple}: {e}", exc_info=True)
        # ----------------------------------------------

        # Update assignment status
        if assignment.status in ['PENDING', 'IN_PROGRESS']:
            assignment.status = 'IN_PROGRESS'
            assignment.save()

        # Check if form is now complete - Using the new logic based on ReportedMetricValue
        if created_submissions:
             # Pass assignment directly now
            self._check_form_completion(assignment)
        # elif updated_submissions: # No longer applicable
        #     pass 

        # Automatically attach standalone evidence files if requested (remains the same)
        evidence_count = 0
        if request.data.get('auto_attach_evidence') in [True, 'true', 'True']:
            # Attach evidence to the newly created submissions
            evidence_count = attach_evidence_to_submissions(created_submissions, request.user)

        return Response({
            'status': 'success',
            # Updated message to reflect only creations
            'message': f'Created {len(created_submissions)} submission inputs.',
            'evidence_attached': evidence_count,
            'assignment_status': assignment.status # Return current status
        })

    @action(detail=False, methods=['get'])
    def by_assignment(self, request):
        """Get all submission INPUTS for a specific assignment"""
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
            
        # Filter by source identifier
        source_id = request.query_params.get('source_identifier')
        if source_id:
            submissions = submissions.filter(source_identifier=source_id)
            
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
        submissions = submissions.select_related('metric', 'layer', 'submitted_by', 'reported_value').order_by(sort_by)
        
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
        """Verify a specific submission INPUT (for Baker Tilly admins)."""
        submission = self.get_object() # Gets the ESGMetricSubmission instance
        
        # Only Baker Tilly admins can verify submissions
        if not (request.user.is_staff or request.user.is_superuser or request.user.is_baker_tilly_admin):
            return Response({'error': 'Only Baker Tilly admins can verify submissions'}, status=403)
        
        serializer = self.get_serializer(data=request.data) # Uses ESGMetricSubmissionVerifySerializer
        serializer.is_valid(raise_exception=True)
        
        # Update verification status on the ESGMetricSubmission record
        submission.is_verified = True
        submission.verified_by = request.user
        submission.verified_at = timezone.now()
        submission.verification_notes = serializer.validated_data.get('verification_notes', '')
        submission.save()
        
        # Note: Verification of the INPUT does not automatically verify the ReportedMetricValue
        # A separate mechanism would be needed to verify the final aggregated value if required.
        
        return Response({
            'status': 'success',
            'message': 'Submission input verified successfully'
        })

    @action(detail=False, methods=['post'])
    @transaction.atomic
    def submit_template(self, request):
        """
        Submit a complete template and mark it as submitted.
        DECISION: Should submission check ReportedMetricValue verification status?
        For now, just checks existence, similar to _check_form_completion.
        
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
        
        # --- Check Completion based on ReportedMetricValue --- 
        required_metrics = ESGMetric.objects.filter(
            form__in=assignment.template.selected_forms.all(),
            is_required=True
        )

        if not required_metrics.exists():
            # No required metrics, consider it complete
            assignment.status = 'SUBMITTED'
            assignment.completed_at = timezone.now()
            assignment.save()
            # Mark all form selections complete
            assignment.template.templateformselection_set.update(
                is_completed=True, completed_at=timezone.now(), completed_by=request.user
            )
            return Response({
                'status': 'success',
                'message': 'Template submitted successfully (no required metrics)',
                'assignment_status': assignment.status
            }) 

        missing_final_values = []
        # Fetch all existing reported values for this assignment
        existing_reported_values = ReportedMetricValue.objects.filter(
            assignment=assignment,
            layer=assignment.layer
        ).values_list('metric_id', 'reporting_period')
        reported_value_lookup = {(metric_id, period) for metric_id, period in existing_reported_values}

        for metric in required_metrics:
            if metric.requires_time_reporting:
                expected_periods = get_required_submission_count(metric, assignment, return_dates=True)
                for period_date in expected_periods:
                    if (metric.id, period_date) not in reported_value_lookup:
                        missing_final_values.append({
                            'id': metric.id,
                            'name': metric.name,
                            'form': metric.form.name,
                            'missing_period': period_date.isoformat()
                        })
            else:
                expected_period_for_non_time_based = assignment.reporting_period_end
                if (metric.id, expected_period_for_non_time_based) not in reported_value_lookup:
                    missing_final_values.append({
                        'id': metric.id,
                        'name': metric.name,
                        'form': metric.form.name,
                        'missing_period': 'Overall' # Or expected_period_for_non_time_based.isoformat()
                    })
            
        if missing_final_values:
            return Response({
                'status': 'incomplete',
                'message': 'Template is incomplete. Final reported values are missing.',
                'missing_final_values': missing_final_values
            }, status=400)
        
        # --- Mark as Submitted --- 
        assignment.status = 'SUBMITTED'
        assignment.completed_at = timezone.now()
        assignment.save()
        
        # Update form selections (redundant if _check_form_completion is reliable, but safe to do here)
        for form_selection in assignment.template.templateformselection_set.all():
            # Reuse check logic, but maybe simplify?
             form_metrics = required_metrics.filter(form=form_selection.form)
             form_metrics_complete = True
             for metric in form_metrics:
                 if metric.requires_time_reporting:
                     expected_periods = get_required_submission_count(metric, assignment, return_dates=True)
                     for period_date in expected_periods:
                         if (metric.id, period_date) not in reported_value_lookup:
                             form_metrics_complete = False
                             break
                 else:
                     expected_period_for_non_time_based = assignment.reporting_period_end
                     if (metric.id, expected_period_for_non_time_based) not in reported_value_lookup:
                         form_metrics_complete = False
                 if not form_metrics_complete:
                     break
            
             if form_metrics_complete:
                 form_selection.is_completed = True
                 form_selection.completed_at = timezone.now()
                 form_selection.completed_by = request.user
                 form_selection.save()
        
        return Response({
            'status': 'success',
            'message': 'Template submitted successfully',
            'assignment_status': assignment.status
        }) 