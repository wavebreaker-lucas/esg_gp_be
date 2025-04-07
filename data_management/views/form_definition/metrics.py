"""
Views for managing individual ESG metrics and their value fields.
"""
from rest_framework import viewsets, status, permissions
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated

# Removed ESGMetric, MetricValueField from imports
from ...models import ESGForm 
# from ...models.templates import MetricValueField # Removed
# Import new base model for future reference
from ...models.polymorphic_metrics import BaseESGMetric 
# Import polymorphic serializer
from ...serializers.polymorphic_metrics import ESGMetricPolymorphicSerializer

# Removed ESGMetricSerializer, MetricValueFieldSerializer
# from ...serializers.templates import (
#    # ESGMetricSerializer, MetricValueFieldSerializer # Removed
# )
from accounts.permissions import BakerTillyAdmin

# --- Commented out obsolete ViewSets --- 

# class ESGMetricViewSet(viewsets.ModelViewSet):
#     """
#     ViewSet for managing ESG metrics.
#     Only Baker Tilly admins can modify metrics.
#     Related to specific ESGForms.
#     NEEDS REPLACEMENT with Polymorphic handling
#     """
#     serializer_class = ESGMetricSerializer
#     permission_classes = [IsAuthenticated]
# 
#     def get_queryset(self):
#         """Filter metrics based on the form specified in the URL if provided."""
#         queryset = ESGMetric.objects.all()
#         form_id = self.request.query_params.get('form_id')
#         if form_id:
#             queryset = queryset.filter(form_id=form_id)
#         return queryset
# 
#     def get_permissions(self):
#         """
#         Only Baker Tilly admins can create, update, or delete metrics.
#         All authenticated users can view metrics.
#         """
#         if self.action in ['create', 'update', 'partial_update', 'destroy']:
#             return [IsAuthenticated(), BakerTillyAdmin()]
#         return [IsAuthenticated()]
# 
#     def perform_create(self, serializer):
#         """Associate the metric with the form if provided in request body."""
#         form_id = self.request.data.get('form_id')
#         if form_id:
#             try:
#                 form = ESGForm.objects.get(id=form_id)
#                 serializer.save(form=form)
#             except ESGForm.DoesNotExist:
#                 # Handle error: Form not found
#                 # This case might need specific error handling depending on requirements
#                 # For now, let serializer validation handle invalid form_id if possible
#                 # Or raise a specific validation error here
#                 pass # Or raise validation error
#         else:
#             # Handle case where form_id is not provided, if necessary
#             # Depending on requirements, form might be mandatory
#             serializer.save() # Assumes form can be null or handled differently

# class MetricValueFieldViewSet(viewsets.ModelViewSet):
#     """
#     ViewSet for managing fields within multi-value ESG metrics.
#     Only Baker Tilly admins can modify these fields.
#     OBSOLETE - Handled by JSON field in new polymorphic metrics.
#     """
#     serializer_class = MetricValueFieldSerializer
#     permission_classes = [IsAuthenticated]
# 
#     def get_queryset(self):
#         """Filter fields based on the metric specified in the URL if provided."""
#         queryset = MetricValueField.objects.all()
#         metric_id = self.request.query_params.get('metric_id')
#         if metric_id:
#             queryset = queryset.filter(metric_id=metric_id)
#         return queryset
# 
#     def get_permissions(self):
#         """
#         Only Baker Tilly admins can create, update, or delete fields.
#         All authenticated users can view fields.
#         """
#         if self.action in ['create', 'update', 'partial_update', 'destroy']:
#             return [IsAuthenticated(), BakerTillyAdmin()]
#         return [IsAuthenticated()]
# 
#     def perform_create(self, serializer):
#         """Associate the field with the metric if provided."""
#         metric_id = self.request.data.get('metric') # Assuming metric ID is passed directly
#         if metric_id:
#             try:
#                 metric = ESGMetric.objects.get(id=metric_id)
#                 # Ensure the metric is actually a multi-value metric?
#                 # if not metric.is_multi_value:
#                 #     raise serializers.ValidationError("Cannot add fields to a single-value metric.")
#                 serializer.save(metric=metric)
#             except ESGMetric.DoesNotExist:
#                 pass # Let serializer validation handle invalid metric ID
#         else:
#              serializer.save() 

# --- NEW: ViewSet for Polymorphic ESG Metrics --- 

class ESGMetricViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing polymorphic ESG metrics (Basic, TimeSeries, etc.).
    Allows CRUD operations. Only Baker Tilly admins can modify.
    """
    # Use the base model for the queryset
    # Note: Polymorphic manager automatically handles fetching appropriate subclasses
    queryset = BaseESGMetric.objects.all().select_related('form', 'form__category').order_by('form__id', 'order') # Added ordering
    # Use the polymorphic serializer
    serializer_class = ESGMetricPolymorphicSerializer
    permission_classes = [IsAuthenticated] # Base permission

    def get_permissions(self):
        """
        Only Baker Tilly admins can create, update, or delete metrics.
        All authenticated users can view metrics.
        """
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            # Ensure BakerTillyAdmin is correctly imported and used
            return [IsAuthenticated(), BakerTillyAdmin()]
        # Allow read access for any authenticated user
        return [IsAuthenticated()]

    # Optional: Override methods if specific logic is needed
    # For example, perform_create might need context or validation
    # def perform_create(self, serializer):
    #     # Example: Ensure form_id is provided if creating via this endpoint?
    #     form_id = self.request.data.get('form_id')
    #     if not form_id:
    #         raise serializers.ValidationError({'form_id': 'This field is required when creating metrics directly.'})
    #     serializer.save()

    # Note: Creating metrics via POST /api/esg-metrics/ requires 'form_id' 
    # and 'metric_subtype' in the payload. Using the form-specific 
    # POST /api/esg-forms/{form_id}/add_metric/ is generally preferred. 