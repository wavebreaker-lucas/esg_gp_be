from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from .views import modules  # Import our newly modularized views

router = DefaultRouter()
router.register(r'forms', views.ESGFormViewSet, 'esgform')
router.register(r'form-categories', views.ESGFormCategoryViewSet, 'esgformcategory')
router.register(r'metrics', views.ESGMetricViewSet, 'esgmetric')
router.register(r'templates', views.TemplateViewSet, 'template')
router.register(r'metric-submissions', views.ESGMetricSubmissionViewSet, 'esgmetricsubmission')
router.register(r'metric-evidence', views.ESGMetricEvidenceViewSet, 'esgmetricevidence')

urlpatterns = [
    path('api/', include(router.urls)),
    # Add non-ViewSet APIs
    path('api/layer/<int:layer_id>/templates/', views.TemplateAssignmentView.as_view(), name='layer-templates'),
    path('api/user-templates/', views.UserTemplateAssignmentView.as_view(), name='user-templates'),
    path('api/user-templates/<int:assignment_id>/', views.UserTemplateAssignmentView.as_view(), name='user-template-detail'),
] 