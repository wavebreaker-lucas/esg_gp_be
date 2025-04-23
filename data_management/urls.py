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
from .views.checklist_reports import (
    generate_checklist_report, generate_combined_checklist_report,
    get_reports_by_submission, get_report_by_id, get_reports_by_layer,
    get_checklist_status, generate_combined_report_for_layer
)

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

    # Checklist Reports
    path('checklist-reports/generate/', generate_checklist_report, name='generate_checklist_report'),
    path('checklist-reports/generate-combined/', generate_combined_checklist_report, name='generate_combined_checklist_report'),
    
    # New automated ESG reporting endpoints
    path('checklist-status/<int:layer_id>/', get_checklist_status, name='get_checklist_status'),
    path('checklist-reports/generate-for-layer/', generate_combined_report_for_layer, name='generate_combined_report_for_layer'),
    
    # Saved Reports endpoints
    path('checklist-reports/submission/<int:submission_id>/', get_reports_by_submission, name='get_reports_by_submission'),
    path('checklist-reports/<int:report_id>/', get_report_by_id, name='get_report_by_id'),
    path('checklist-reports/layer/<int:layer_id>/', get_reports_by_layer, name='get_reports_by_layer'),
] 