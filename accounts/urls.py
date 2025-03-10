from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views.registration import RegisterLayerProfileView
from .views.layer_management import LayerProfileViewSet
from .views.user_management import AppUserViewSet

# Create a router for ViewSets
router = DefaultRouter()
# Register ViewSets with the router
router.register(r'layers', LayerProfileViewSet, basename='layer-profile')  # /api/layers/
router.register(r'app_users', AppUserViewSet, basename='app-user')  # /api/app_users/

# URL patterns including both ViewSet URLs and regular views
urlpatterns = [
    # Custom registration endpoint
    path('register-layer-profile/', 
         RegisterLayerProfileView.as_view(), 
         name='register-layer-profile'),
    
    # Include all router-generated URLs
    path('', include(router.urls)),
] 