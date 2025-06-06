from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView
from .views.layer_management import LayerProfileViewSet
from .views.user_management import AppUserViewSet
from .views.client_management import ClientSetupView, ClientUserManagementView, ClientStructureView, ClientStatisticsView
from .views.auth import (
    CustomTokenObtainPairView, LogoutView,
    VerifyOTPView, RequestPasswordResetView,
    ResetPasswordView, ResendOTPView,
    ChangePasswordView
)
from data_management.views import TemplateAssignmentView

# Create a router for ViewSets
router = DefaultRouter()
# Register ViewSets with the router
router.register(r'layers', LayerProfileViewSet, basename='layer-profile')  # /api/layers/
router.register(r'app_users', AppUserViewSet, basename='app-user')  # /api/app_users/

# URL patterns including both ViewSet URLs and regular views
urlpatterns = [
    # Baker Tilly Admin endpoints
    path('clients/setup/', ClientSetupView.as_view(), name='client-setup'),
    path('clients/<int:group_id>/users/', ClientUserManagementView.as_view(), name='client-users'),
    path('clients/<int:group_id>/structure/', ClientStructureView.as_view(), name='client-structure'),
    
    # Statistics endpoints
    path('clients/statistics/', ClientStatisticsView.as_view(), name='client-statistics'),
    path('clients/<int:group_id>/statistics/', ClientStatisticsView.as_view(), name='client-group-statistics'),
    
    # Auth endpoints
    path('login/', CustomTokenObtainPairView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('verify-otp/', VerifyOTPView.as_view(), name='verify-otp'),
    path('resend-otp/', ResendOTPView.as_view(), name='resend-otp'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('request-password-reset/', RequestPasswordResetView.as_view(), name='request-password-reset'),
    path('reset-password/<uuid:reset_token>/', ResetPasswordView.as_view(), name='reset-password'),
    path('change-password/', ChangePasswordView.as_view(), name='change-password'),
    
    # Template Assignment URLs
    path('clients/<int:layer_id>/templates/', TemplateAssignmentView.as_view(), name='client-templates'),
    
    # Include router URLs
    path('', include(router.urls)),
] 