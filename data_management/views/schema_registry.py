"""
Views for managing schema registry
"""
from rest_framework import viewsets, permissions
from django.db.models import Count
from ..models import MetricSchemaRegistry, ESGMetric
from ..serializers.esg import MetricSchemaRegistrySerializer


class SchemaRegistryViewSet(viewsets.ModelViewSet):
    """ViewSet for managing JSON schemas in the registry"""
    serializer_class = MetricSchemaRegistrySerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Filter schemas based on user permissions"""
        queryset = MetricSchemaRegistry.objects.all()
        
        # Staff and superusers can see all schemas
        if self.request.user.is_staff or self.request.user.is_superuser:
            return queryset.annotate(metrics_count=Count('metrics'))
        
        # Regular users can only see active schemas
        return queryset.filter(is_active=True).annotate(metrics_count=Count('metrics'))
    
    def perform_create(self, serializer):
        """Set the current user as the creator"""
        serializer.save(created_by=self.request.user) 