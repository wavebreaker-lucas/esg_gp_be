from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views.registration import RegisterLayerProfileView
from .views.layer_management import LayerProfileViewSet
from .views.user_management import AppUserViewSet
from .views.auth import (
    CustomTokenObtainPairView, LogoutView,
    VerifyOTPView, RequestPasswordResetView,
    ResetPasswordView
)

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
    
    # Auth endpoints
    path('login/', CustomTokenObtainPairView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('verify-otp/', VerifyOTPView.as_view(), name='verify-otp'),
    path('request-password-reset/', 
         RequestPasswordResetView.as_view(), 
         name='request-password-reset'),
    path('reset-password/<uuid:reset_token>/',
         ResetPasswordView.as_view(),
         name='reset-password'),
    
    # Include all router-generated URLs
    path('', include(router.urls)),
] 