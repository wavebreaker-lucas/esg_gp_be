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
                                    "unit": {"type": "string", "enum": ["tCO2e", "kgCO2e"]},
                                    "notes": {"type": "string"}
                                }
                            }
                        }
                    },
                    "required": ["value", "unit", "scope"]
                }
            },
            {
                "type": "electricity",
                "name": "Electricity Consumption",
                "description": "For tracking electricity usage with unit information",
                "template": {
                    "type": "object",
                    "properties": {
                        "value": {"type": "number"},
                        "unit": {"type": "string", "enum": ["kWh", "MWh", "GWh"]},
                        "comments": {"type": "string"},
                        "periods": {
                            "type": "object",
                            "additionalProperties": {
                                "type": "object",
                                "properties": {
                                    "value": {"type": "number"},
                                    "unit": {"type": "string", "enum": ["kWh", "MWh", "GWh"]},
                                    "comments": {"type": "string"}
                                }
                            }
                        }
                    },
                    "required": ["value", "unit"]
                }
            },
            {
                "type": "utility_bundle",
                "name": "Multiple Utility Consumption",
                "description": "For tracking multiple utility consumptions together",
                "template": {
                    "type": "object",
                    "properties": {
                        "electricity": {
                            "type": "object",
                            "properties": {
                                "value": {"type": "number"},
                                "unit": {"type": "string", "enum": ["kWh", "MWh"]}
                            }
                        },
                        "water": {
                            "type": "object",
                            "properties": {
                                "value": {"type": "number"},
                                "unit": {"type": "string", "enum": ["m3", "liters"]}
                            }
                        },
                        "gas": {
                            "type": "object",
                            "properties": {
                                "value": {"type": "number"},
                                "unit": {"type": "string", "enum": ["m3", "BTU"]}
                            }
                        },
                        "comments": {"type": "string"},
                        "_metadata": {
                            "type": "object",
                            "properties": {
                                "primary_measurement": {"type": "string", "enum": ["electricity", "water", "gas"]}
                            }
                        }
                    }
                }
            },
            {
                "type": "supplier_assessment",
                "name": "Supplier Assessment",
                "description": "For tracking supplier compliance and assessments",
                "template": {
                    "type": "object",
                    "properties": {
                        "suppliers": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "name": {"type": "string"},
                                    "id": {"type": "string"},
                                    "assessment": {
                                        "type": "object",
                                        "properties": {
                                            "compliance_status": {
                                                "type": "string", 
                                                "enum": ["Compliant", "Partially Compliant", "Non-Compliant"]
                                            },
                                            "score": {
                                                "type": "object",
                                                "properties": {
                                                    "value": {"type": "number"},
                                                    "unit": {"type": "string", "enum": ["points", "percentage"]}
                                                }
                                            },
                                            "date": {"type": "string", "format": "date"}
                                        }
                                    },
                                    "categories": {
                                        "type": "array",
                                        "items": {"type": "string"}
                                    }
                                }
                            }
                        },
                        "assessment_period": {"type": "string"},
                        "comments": {"type": "string"},
                        "_metadata": {
                            "type": "object",
                            "properties": {
                                "primary_measurement": {"type": "string", "default": "suppliers[0].assessment.score"}
                            }
                        }
                    }
                }
            }
        ]
        
        return Response(schema_types) 