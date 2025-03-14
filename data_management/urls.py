from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views.templates import (
    ESGFormViewSet, ESGFormCategoryViewSet,
    TemplateViewSet, TemplateAssignmentView
)

# Create a router for ViewSets
router = DefaultRouter()
router.register(r'esg-forms', ESGFormViewSet)
router.register(r'esg-categories', ESGFormCategoryViewSet)
router.register(r'templates', TemplateViewSet)

# URL patterns
urlpatterns = [
    path('', include(router.urls)),
    path('companies/<int:group_id>/templates/', 
         TemplateAssignmentView.as_view(), 
         name='template-assignments'),
] 