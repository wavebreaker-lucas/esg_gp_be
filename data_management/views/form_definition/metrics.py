"""
Views for managing ESG metrics.
"""

from rest_framework import viewsets, serializers
from rest_framework.permissions import IsAuthenticated

from accounts.permissions import BakerTillyAdmin
from ...models import ESGMetric, ESGForm
from ...serializers.templates import ESGMetricSerializer, MetricValueFieldSerializer
from ...models.templates import MetricValueField


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


class MetricValueFieldViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing MetricValueField definitions.
    Primarily for Baker Tilly admins to configure multi-value metrics.
    """
    queryset = MetricValueField.objects.all()
    serializer_class = MetricValueFieldSerializer
    permission_classes = [IsAuthenticated, BakerTillyAdmin] # Only admins can manage these

    def get_queryset(self):
        """Allow filtering by metric_id."""
        queryset = super().get_queryset()
        metric_id = self.request.query_params.get('metric_id')
        if metric_id:
            queryset = queryset.filter(metric_id=metric_id)
        return queryset

    def perform_create(self, serializer):
        """Ensure the parent metric is marked as multi-value."""
        metric = serializer.validated_data.get('metric')
        if metric and not metric.is_multi_value:
            metric.is_multi_value = True
            metric.save()
        serializer.save() 