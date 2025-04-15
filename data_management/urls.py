from rest_framework.routers import DefaultRouter
from django.urls import path, include
# Removed ESGMetricViewSet, MetricValueFieldViewSet
# Adjust import to include metrics view module
from .views import (
    ESGFormViewSet, ESGFormCategoryViewSet, TemplateViewSet, 
    ESGMetricSubmissionViewSet, ESGMetricEvidenceViewSet, 
    UserTemplateAssignmentView, UserTemplateAssignmentStructureView,
    TemplateAssignmentView,
    BatchEvidenceView,
    AvailableLayersView, SumSubmissionsByLayerView, 
    ReportedMetricValueViewSet,
    VehicleTypeViewSet, FuelTypeViewSet
)
# Import the metrics view separately (or adjust above import)
from .views.form_definition import metrics as metric_views
# Import dashboard API views
from .views.dashboard_api import total_emissions_api, emissions_time_series_api, vehicle_emissions_breakdown_api

# Create a router for ViewSets
router = DefaultRouter()

# Register ViewSets with the router
router.register(r'esg-forms', ESGFormViewSet, basename='esg-form')
router.register(r'esg-categories', ESGFormCategoryViewSet, basename='esg-category')
router.register(r'templates', TemplateViewSet, basename='template')
router.register(r'metric-submissions', ESGMetricSubmissionViewSet, basename='metric-submission')
router.register(r'metric-evidence', ESGMetricEvidenceViewSet, basename='metric-evidence')
# router.register(r'esg-metrics', ESGMetricViewSet, basename='esg-metric') # Removed
# Uncomment/add the registration for the new ESGMetricViewSet
router.register(r'esg-metrics', metric_views.ESGMetricViewSet, basename='esgmetric')
# router.register(r'metric-value-fields', MetricValueFieldViewSet, basename='metric-value-field') # Removed
router.register(r'reported-metric-values', ReportedMetricValueViewSet, basename='reported-metric-value')
router.register(r'vehicle-types', VehicleTypeViewSet, basename='vehicle-type')
router.register(r'fuel-types', FuelTypeViewSet, basename='fuel-type')

# Export the router's URLs
# Assuming this urls.py is included under /api/ in your main urls.py
urlpatterns = router.urls

# Add non-ViewSet URLs
urlpatterns += [
    path('user-templates/', UserTemplateAssignmentView.as_view(), name='user-templates'),
    path('user-templates/<int:assignment_id>/', UserTemplateAssignmentView.as_view(), name='user-template-detail'),
    path('user-templates/<int:assignment_id>/structure/', UserTemplateAssignmentStructureView.as_view(), name='user_template_assignment_structure'),
    path('layer/<int:layer_id>/templates/', TemplateAssignmentView.as_view(), name='layer-templates'),
    path('metric-evidence/batch/', BatchEvidenceView.as_view(), name='batch-evidence'),
    path('submissions/available-layers/', AvailableLayersView.as_view(), name='submission-available-layers'),
    path('submissions/sum-by-layer/', SumSubmissionsByLayerView.as_view(), name='submission-sum-by-layer'),
    
    # Dashboard API endpoints
    path('dashboard/total-emissions/', total_emissions_api, name='dashboard-total-emissions'),
    path('dashboard/emissions-time-series/', emissions_time_series_api, name='dashboard-emissions-time-series'),
    path('dashboard/vehicle-emissions/', vehicle_emissions_breakdown_api, name='dashboard-vehicle-emissions'),
] 