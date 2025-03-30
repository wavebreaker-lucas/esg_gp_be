"""
Views for managing Metric Schema Registry.
"""
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db import transaction
from django.db.models import Count

from ..models import MetricSchemaRegistry, ESGMetric
from ..serializers.esg import MetricSchemaRegistrySerializer
from data_management.json_schemas import SCHEMA_TEMPLATES


class SchemaRegistryViewSet(viewsets.ModelViewSet):
    """ViewSet for managing metric schema registry"""
    serializer_class = MetricSchemaRegistrySerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Get all schemas, or filter by active status"""
        queryset = MetricSchemaRegistry.objects.all()
        
        # Filter by active status if requested
        active = self.request.query_params.get('active')
        if active is not None:
            is_active = active.lower() in ['true', '1', 'yes']
            queryset = queryset.filter(is_active=is_active)
            
        return queryset
    
    def perform_create(self, serializer):
        """Set the created_by field when creating a schema"""
        serializer.save(created_by=self.request.user)
    
    @action(detail=True, methods=['get'])
    def metrics(self, request, pk=None):
        """Get all metrics using this schema"""
        schema = self.get_object()
        metrics = ESGMetric.objects.filter(schema_registry=schema)
        
        # Simple response with metric info
        metrics_data = [{
            'id': metric.id,
            'name': metric.name,
            'form_code': metric.form.code,
            'form_name': metric.form.name
        } for metric in metrics]
        
        return Response(metrics_data)
    
    @action(detail=False, methods=['get'])
    def schema_types(self, request):
        """
        Returns a list of available schema types with examples for creating metrics.
        These templates help users create metrics with properly structured JSON schemas.
        """
        return Response({
            "schema_templates": SCHEMA_TEMPLATES
        }) 