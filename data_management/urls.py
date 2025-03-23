from rest_framework.routers import DefaultRouter
from django.urls import path
from . import views

# Create a router for ViewSets
router = DefaultRouter()

# Register ViewSets with the router
router.register(r'esg-forms', views.ESGFormViewSet, basename='esg-form')
router.register(r'esg-categories', views.ESGFormCategoryViewSet, basename='esg-category')
router.register(r'templates', views.TemplateViewSet, basename='template')
router.register(r'metric-submissions', views.ESGMetricSubmissionViewSet, basename='metric-submission')
router.register(r'metric-evidence', views.ESGMetricEvidenceViewSet, basename='metric-evidence')
router.register(r'esg-metrics', views.ESGMetricViewSet, basename='esg-metric')

# Export the router's URLs
urlpatterns = router.urls

# Add non-ViewSet URLs
urlpatterns += [
    path('user-templates/', views.UserTemplateAssignmentView.as_view(), name='user-templates'),
    path('user-templates/<int:assignment_id>/', views.UserTemplateAssignmentView.as_view(), name='user-template-detail'),
    path('layer/<int:layer_id>/templates/', views.TemplateAssignmentView.as_view(), name='layer-templates'),
] 