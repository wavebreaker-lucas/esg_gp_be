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
    ESGMetricSubmissionVerifySerializer
)

logger = logging.getLogger(__name__)

class ESGMetricSubmissionViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing individual ESG metric submission inputs.
    Allows users to submit, update, and view their metric data.
    
    NEEDS SIGNIFICANT REWORK FOR POLYMORPHIC METRICS & SUBMISSIONS
    """
    serializer_class = ESGMetricSubmissionSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [] # Add filters later if needed
    # filterset_fields = ['assignment', 'metric', 'reporting_period', 'is_verified'] # Needs review

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
        # Needs rewrite for polymorphic data handling & aggregation trigger
        # super().perform_create(serializer) # Basic save might fail depending on serializer
        logger.warning("perform_create needs update for polymorphic metrics")
        # For now, just save básico to allow migration
        serializer.save(submitted_by=self.request.user)
    
    def perform_update(self, serializer):
        # Needs rewrite for polymorphic data handling & aggregation trigger
        logger.warning("perform_update needs update for polymorphic metrics")
        serializer.save()

    def perform_destroy(self, instance):
        # Needs rewrite for polymorphic data handling & aggregation trigger
        logger.warning("perform_destroy needs update for polymorphic metrics")
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
    @transaction.atomic
    def batch_submit(self, request):
        """Handle batch submission of multiple metric inputs."""
        # Needs complete rewrite
        logger.error("Batch submit endpoint needs rewrite for polymorphic metrics")
        return Response("Batch submit endpoint needs rewrite for polymorphic metrics", status=status.HTTP_501_NOT_IMPLEMENTED)