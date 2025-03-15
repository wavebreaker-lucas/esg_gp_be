from rest_framework.routers import DefaultRouter
from .views.templates import (
    ESGFormViewSet, ESGFormCategoryViewSet,
    TemplateViewSet
)

# Create a router for ViewSets
router = DefaultRouter()

# Register ViewSets with the router
router.register(r'esg-forms', ESGFormViewSet, basename='esg-form')
router.register(r'esg-categories', ESGFormCategoryViewSet, basename='esg-category')
router.register(r'templates', TemplateViewSet, basename='template')

# Export the router's URLs
urlpatterns = router.urls 