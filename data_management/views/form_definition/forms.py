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
    ESGForm,
    Template, TemplateFormSelection, TemplateAssignment
)
from ...models.polymorphic_metrics import BaseESGMetric
from ...serializers.templates import (
    ESGFormSerializer, ESGMetricEvidenceSerializer
)


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

    # Commenting out actions heavily dependent on the old metric structure
    # These will need to be redesigned in Phase 4/5

    # @action(detail=True, methods=['get'])
    # def metrics(self, request, pk=None):
    #     """Get metrics for a specific form"""
    #     form = self.get_object()
    #     # Need to query polymorphic_metrics now
    #     # metrics = form.polymorphic_metrics.all()
    #     # Need a polymorphic serializer
    #     # serializer = PolymorphicESGMetricSerializer(metrics, many=True)
    #     # return Response(serializer.data)
    #     return Response("Metrics endpoint needs update for polymorphic model", status=status.HTTP_501_NOT_IMPLEMENTED)

    # @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, BakerTillyAdmin])
    # def add_metric(self, request, pk=None):
    #     """Add a new metric to the form"""
    #     # Needs to handle creation of specific polymorphic metric types
    #     return Response("Add metric endpoint needs update for polymorphic model", status=status.HTTP_501_NOT_IMPLEMENTED)

    # @action(detail=True, methods=['get'])
    # def check_completion(self, request, pk=None):
    #     """
    #     Check if a form is completed for a specific assignment.
    #     NEEDS COMPLETE REWRITE for polymorphic metrics and submission data structure
    #     """
    #     return Response("Check completion endpoint needs update for polymorphic model", status=status.HTTP_501_NOT_IMPLEMENTED)

    # @action(detail=True, methods=['post'])
    # @transaction.atomic
    # def complete_form(self, request, pk=None):
    #     """
    #     Mark a form as completed for a specific template assignment.
    #     NEEDS COMPLETE REWRITE based on check_completion logic
    #     """
    #     return Response("Complete form endpoint needs update for polymorphic model", status=status.HTTP_501_NOT_IMPLEMENTED)

    # @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, BakerTillyAdmin])
    # @transaction.atomic
    # def uncomplete_form(self, request, pk=None):
    #     """
    #     Mark a form as not completed for a specific template assignment.
    #     """
    #     # This might still be simple if just flipping the flag on TemplateFormSelection
    #     # But let's comment out for consistency during this refactor phase
    #     return Response("Uncomplete form endpoint temporarily disabled", status=status.HTTP_501_NOT_IMPLEMENTED) 