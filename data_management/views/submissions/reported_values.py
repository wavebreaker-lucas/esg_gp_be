"""
ViewSet for accessing the final, aggregated ReportedMetricValue records.
"""

import logging
from django.db import models
from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

from accounts.models import LayerProfile
from ...models import ReportedMetricValue, TemplateAssignment
from ...serializers.templates import ReportedMetricValueSerializer

logger = logging.getLogger(__name__)

class ReportedMetricValueViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Provides read-only access to the final calculated/aggregated metric records.

    Filtering is available on:
    - assignment (ID)
    - metric (ID) - Note: This is the *input* metric ID.
    - layer (ID)
    - reporting_period (Date)
    """
    serializer_class = ReportedMetricValueSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = [
        'assignment', 
        'metric', # Filters by the input metric ID
        'layer',
        'reporting_period',
        'level', # Added level filtering
        # REMOVED: 'is_verified' as verification is not on this model anymore
    ]

    def get_queryset(self):
        """Ensure users only see reported values for layers they have access to."""
        user = self.request.user
        # Select related fields on the parent record
        # Prefetch related fields for nested serializers (aggregated_fields)
        queryset = ReportedMetricValue.objects.select_related(
            'metric', 'layer', 'assignment' # Removed 'verified_by'
        ).prefetch_related(
            'aggregated_fields', # Prefetch the child fields
            'aggregated_fields__field' # Also prefetch the field definition within the child
        )

        if user.is_staff or user.is_superuser or user.is_baker_tilly_admin:
            return queryset

        # Filter by accessible layers for non-admins
        # Assumes a user is linked to LayerProfiles via AppUser -> LayerProfile
        try:
            user_layers = LayerProfile.objects.filter(app_users__user=user)
            # User can see values reported for their layers OR values linked to assignments they manage
            queryset = queryset.filter(
                models.Q(layer__in=user_layers) |
                models.Q(assignment__assigned_to=user)
            ).distinct()
        except Exception:
            # Handle cases where user might not be linked correctly
            logger.warning(f"Could not determine layers for user {user.id}, returning empty queryset for reported values.")
            return queryset.none()

        return queryset

    # Potential Future Actions (add later if needed):
    # - @action(detail=True, methods=['post']) # Add permissions
    #   def recalculate(self, request, pk=None):
    #       instance = self.get_object()
    #       try:
    #           calculate_report_value(instance.assignment, instance.metric, instance.reporting_period, instance.layer)
    #           return Response({"status": "recalculation triggered"})
    #       except Exception as e:
    #           logger.error(f"Manual recalculation failed for {instance.id}: {e}")
    #           return Response({"error": "Recalculation failed"}, status=500) 