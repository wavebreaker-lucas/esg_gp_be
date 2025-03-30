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
        """Get a list of pre-defined schema types for common metrics"""
        # These are just examples - you would customize these for your specific needs
        schema_types = [
            {
                "type": "emissions",
                "name": "Emissions Metric",
                "description": "For tracking GHG emissions with scope information",
                "template": {
                    "type": "object",
                    "properties": {
                        "value": {"type": "number"},
                        "unit": {"type": "string", "enum": ["tCO2e", "kgCO2e"]},
                        "scope": {"type": "string", "enum": ["Scope 1", "Scope 2", "Scope 3"]},
                        "source": {"type": "string"},
                        "calculation_method": {"type": "string", "enum": ["location-based", "market-based"]},
                        "periods": {
                            "type": "object",
                            "additionalProperties": {
                                "type": "object",
                                "properties": {
                                    "value": {"type": "number"},
                                    "notes": {"type": "string"}
                                }
                            }
                        }
                    },
                    "required": ["value", "unit", "scope"]
                }
            },
            {
                "type": "resource_consumption",
                "name": "Resource Consumption",
                "description": "For tracking energy, water, or material usage",
                "template": {
                    "type": "object",
                    "properties": {
                        "value": {"type": "number"},
                        "unit": {"type": "string"},
                        "resource_type": {"type": "string"},
                        "renewable_percentage": {"type": "number", "minimum": 0, "maximum": 100},
                        "periods": {
                            "type": "object",
                            "additionalProperties": {
                                "type": "object",
                                "properties": {
                                    "value": {"type": "number"},
                                    "notes": {"type": "string"}
                                }
                            }
                        }
                    },
                    "required": ["value", "unit"]
                }
            },
            {
                "type": "training",
                "name": "Employee Training",
                "description": "For tracking employee training metrics",
                "template": {
                    "type": "object",
                    "properties": {
                        "total_employees": {"type": "integer"},
                        "employees_trained": {"type": "integer"},
                        "total_hours": {"type": "number"},
                        "average_hours_per_employee": {"type": "number"},
                        "training_categories": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "category": {"type": "string"},
                                    "participants": {"type": "integer"},
                                    "hours": {"type": "number"}
                                }
                            }
                        }
                    },
                    "required": ["total_employees", "employees_trained"]
                }
            },
            {
                "type": "legal_cases",
                "name": "Legal Cases",
                "description": "For tracking legal cases and compliance issues",
                "template": {
                    "type": "object",
                    "properties": {
                        "total_cases": {"type": "integer"},
                        "open_cases": {"type": "integer"},
                        "closed_cases": {"type": "integer"},
                        "cases": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "case_id": {"type": "string"},
                                    "description": {"type": "string"},
                                    "status": {"type": "string", "enum": ["open", "closed", "pending"]},
                                    "resolution": {"type": "string"},
                                    "monetary_impact": {"type": "number"},
                                    "date_opened": {"type": "string", "format": "date"},
                                    "date_closed": {"type": "string", "format": "date"}
                                },
                                "required": ["case_id", "description", "status"]
                            }
                        }
                    },
                    "required": ["total_cases"]
                }
            }
        ]
        
        return Response(schema_types) 