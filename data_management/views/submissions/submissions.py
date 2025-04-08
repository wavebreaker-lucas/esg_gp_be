"""
Views for managing ESG metric submissions.
"""

from rest_framework import viewsets, views, status, serializers
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination
from django.db import transaction, models
from django.utils import timezone
import logging
# Import the filter backend and FilterSet
import django_filters
from django_filters.rest_framework import DjangoFilterBackend 

from accounts.models import CustomUser, AppUser, LayerProfile
from accounts.services import get_accessible_layers, has_layer_access
from ...models import (
    ESGForm, 
    Template, TemplateAssignment, TemplateFormSelection,
    ReportedMetricValue
)
from ...models.templates import (
    ESGMetricSubmission, ESGMetricEvidence
)
from ...models.polymorphic_metrics import BaseESGMetric
from ...serializers.templates import (
    ESGMetricSubmissionSerializer, 
    ESGMetricEvidenceSerializer, 
    ESGMetricSubmissionVerifySerializer,
    ESGMetricBatchSubmissionSerializer
)

logger = logging.getLogger(__name__)

# --- Custom FilterSet --- 
class ESGMetricSubmissionFilter(django_filters.FilterSet):
    # RENAME Filter by the form ID via the related metric
    form_id = django_filters.NumberFilter(field_name='metric__form', lookup_expr='exact')
    # RENAME existing filters
    assignment_id = django_filters.NumberFilter(field_name='assignment', lookup_expr='exact')
    metric = django_filters.NumberFilter(field_name='metric', lookup_expr='exact')
    reporting_period = django_filters.DateFilter(field_name='reporting_period', lookup_expr='exact')
    is_verified = django_filters.BooleanFilter(field_name='is_verified')

    class Meta:
        model = ESGMetricSubmission
        # UPDATE fields list to use new names
        fields = ['assignment_id', 'metric', 'form_id', 'reporting_period', 'is_verified']

class ESGMetricSubmissionViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing individual ESG metric submission inputs.
    Allows users to submit, update, and view their metric data.
    
    NEEDS SIGNIFICANT REWORK FOR POLYMORPHIC METRICS & SUBMISSIONS
    """
    serializer_class = ESGMetricSubmissionSerializer
    permission_classes = [IsAuthenticated]
    # Use the custom FilterSet
    filter_backends = [DjangoFilterBackend]
    filterset_class = ESGMetricSubmissionFilter 
    # Disable pagination
    pagination_class = None 

    def get_queryset(self):
        """Ensure users only see submissions for layers they have access to."""
        user = self.request.user
        queryset = ESGMetricSubmission.objects.select_related(
            'metric', 'assignment', 'submitted_by', 'verified_by', 'layer'
        ).prefetch_related('evidence') # Removed multi_values prefetch

        if user.is_staff or user.is_superuser or user.is_baker_tilly_admin:
            return queryset

        # Filter by accessible layers
        accessible_layer_ids = get_accessible_layers(user)
        queryset = queryset.filter(
            models.Q(layer_id__in=accessible_layer_ids) |
            models.Q(assignment__assigned_to=user)
        ).distinct()
        
        return queryset

    # --- Methods needing rewrite for Polymorphism (Commented Out) ---

    # def get_serializer_class(self):
    #     # Need to return different serializers based on metric type?
    #     # if self.action == 'create':
    #     #     return ESGMetricSubmissionCreateSerializer # This one is commented out
    #     return ESGMetricSubmissionSerializer

    def perform_create(self, serializer):
        # The serializer now handles setting submitted_by and saving related data.
        # We just need to call save().
        # Any aggregation triggers would likely happen via signals after save.
        serializer.save()
    
    def perform_update(self, serializer):
        # The serializer now handles updating the header and related data.
        # Any aggregation triggers would likely happen via signals after save.
        serializer.save()

    def perform_destroy(self, instance):
        # Default destroy is likely fine, but consider aggregation implications.
        # If deleting a submission requires recalculating aggregates, add logic here or use signals.
        logger.warning("perform_destroy: Consider if aggregation recalculation is needed.")
        super().perform_destroy(instance)
    
    # def _check_form_completion(self, assignment):
    #     """
    #     Recalculates the completion status for all forms within an assignment.
    #     NEEDS REWRITE based on new metric/submission structure.
    #     """
    #     pass

    @action(detail=True, methods=['post'])
    def attach_evidence(self, request, pk=None):
        """
        Attach an existing evidence file (by ID) to this submission input.
        """
        # This might still work, needs testing
        submission = self.get_object()
        evidence_id = request.data.get('evidence_id')
        if not evidence_id:
            return Response({'error': 'evidence_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            evidence = ESGMetricEvidence.objects.get(id=evidence_id, submission=None) # Only attach standalone evidence
            # TODO: Check permissions? Does user own evidence or have access?
            evidence.submission = submission
            evidence.save()
            serializer = ESGMetricEvidenceSerializer(evidence)
            return Response(serializer.data)
        except ESGMetricEvidence.DoesNotExist:
            return Response({'error': 'Standalone evidence not found or already attached'}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=True, methods=['post'])
    def verify_submission(self, request, pk=None):
        """Mark a specific submission input as verified (Baker Tilly Admin only)."""
        # Needs rewrite potentially, but basic logic might be okay
        submission = self.get_object()
        serializer = ESGMetricSubmissionVerifySerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
             # Permission check done in serializer
            submission.is_verified = True
            submission.verified_by = request.user
            submission.verified_at = timezone.now()
            submission.verification_notes = serializer.validated_data.get('verification_notes', '')
            submission.save()
            # Need to return the updated submission data
            output_serializer = self.get_serializer(submission)
            return Response(output_serializer.data)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'])
    @transaction.atomic # Ensure all submissions succeed or fail together
    def batch_submit(self, request):
        """Handle batch submission of multiple metric inputs for a single assignment."""
        logger.info(f"Received batch submission request: {request.data}")
        
        batch_serializer = ESGMetricBatchSubmissionSerializer(data=request.data, context=self.get_serializer_context())
        if not batch_serializer.is_valid():
            logger.error(f"Batch submission validation failed: {batch_serializer.errors}")
            return Response(batch_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        assignment = batch_serializer.validated_data['assignment_id']
        submissions_data = batch_serializer.validated_data['submissions']
        logger.info(f"Processing {len(submissions_data)} submissions for assignment {assignment.pk}")
        
        # Check if user has access to the target assignment's layer
        if not has_layer_access(request.user, assignment.layer_id):
            logger.error(f"User {request.user} does not have access to layer {assignment.layer_id}")
            return Response({"detail": "You do not have permission for this assignment's layer."}, status=status.HTTP_403_FORBIDDEN)

        results = []
        errors = []

        for index, sub_data in enumerate(submissions_data):
            logger.info(f"Processing submission {index + 1}/{len(submissions_data)}: {sub_data}")
            # Don't add assignment here - it should already be in the validated data
            # The assignment field is now added in the validate_submissions method
            
            # Use ESGMetricSubmissionSerializer for validation and saving each item
            # Create a new serializer instance for each item
            item_serializer = ESGMetricSubmissionSerializer(data=sub_data, context=self.get_serializer_context())
            
            if item_serializer.is_valid():
                try:
                    # Perform create logic (no instance passed)
                    instance = item_serializer.save()
                    logger.info(f"Successfully saved submission {index + 1}")
                    results.append(item_serializer.data) # Append serialized result of created object
                except Exception as e:
                    # Catch potential errors during save (though validation should prevent most)
                    logger.error(f"Error saving batch submission item {index}: {str(e)}", exc_info=True)
                    errors.append({f"item_{index}": f"Error during save: {str(e)}"})
            else:
                logger.error(f"Validation failed for submission {index + 1}: {item_serializer.errors}")
                errors.append({f"item_{index}": item_serializer.errors})

        if errors:
            # If any item failed, the transaction will be rolled back.
            # Return the collected errors.
            logger.error(f"Batch submission failed with errors: {errors}")
            return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)
        
        # If all items succeeded
        logger.info(f"Successfully processed all {len(results)} submissions")
        return Response(results, status=status.HTTP_201_CREATED)