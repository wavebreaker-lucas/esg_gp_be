from rest_framework.routers import DefaultRouter
from django.urls import path
from .views.templates import (
    ESGFormViewSet, ESGFormCategoryViewSet,
    TemplateViewSet, TemplateAssignmentView, UserTemplateAssignmentView,
    ESGMetricSubmissionViewSet, ESGMetricEvidenceViewSet, ESGMetricViewSet
)

# Create a router for ViewSets
router = DefaultRouter()

# Register ViewSets with the router
router.register(r'esg-forms', ESGFormViewSet, basename='esg-form')
router.register(r'esg-categories', ESGFormCategoryViewSet, basename='esg-category')
router.register(r'templates', TemplateViewSet, basename='template')
router.register(r'metric-submissions', ESGMetricSubmissionViewSet, basename='metric-submission')
router.register(r'metric-evidence', ESGMetricEvidenceViewSet, basename='metric-evidence')
router.register(r'esg-metrics', ESGMetricViewSet, basename='esg-metric')

# Export the router's URLs
urlpatterns = router.urls

# Add non-ViewSet URLs
urlpatterns += [
    path('user-templates/', UserTemplateAssignmentView.as_view(), name='user-templates'),
    path('user-templates/<int:assignment_id>/', UserTemplateAssignmentView.as_view(), name='user-template-detail'),
] 