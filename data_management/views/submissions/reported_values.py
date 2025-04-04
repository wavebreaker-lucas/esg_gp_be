"""
ViewSet for accessing the final, aggregated ReportedMetricValue records.
"""

from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

from accounts.models import LayerProfile
from ...models import ReportedMetricValue, TemplateAssignment
from ...serializers.templates import ReportedMetricValueSerializer


class ReportedMetricValueViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Provides read-only access to the final calculated metric values.

    Filtering is available on:
    - assignment (ID)
    - metric (ID)
    - layer (ID)
    - reporting_period (Date)
    - is_verified (Boolean)
    """
    serializer_class = ReportedMetricValueSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = [
        'assignment', 
        'metric',
        'layer',
        'reporting_period',
        'is_verified'
    ]

    def get_queryset(self):
        """Ensure users only see reported values for layers they have access to."""
        user = self.request.user
        queryset = ReportedMetricValue.objects.select_related(
            'metric', 'layer', 'assignment', 'verified_by'
        ).prefetch_related('source_submissions') # Prefetch for serializer count/ids

        if user.is_staff or user.is_superuser or user.is_baker_tilly_admin:
            return queryset

        # Filter by accessible layers for non-admins
        # Assumes a user is linked to LayerProfiles via AppUser -> LayerProfile
        try:
            user_layers = LayerProfile.objects.filter(app_users__user=user)
            # User can see values reported for their layers OR values linked to assignments they manage
            # Note: This logic might need adjustment based on exact permission requirements
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
    # - @action(detail=True, methods=['post'], permission_classes=[IsAdminUser]) # Or custom permission
    #   def verify(self, request, pk=None): ...
    # - @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    #   def recalculate(self, request, pk=None): ... 