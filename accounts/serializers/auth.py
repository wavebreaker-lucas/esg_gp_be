from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.exceptions import AuthenticationFailed
from django.utils.translation import gettext_lazy as _
from ..models import CustomUser
from ..services import validate_password

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)
        
        if not self.user.is_active:
            raise AuthenticationFailed(
                _('Your account is not active. Please verify your email.'),
                code='no_active_account'
            )
        
        # Add user data to response
        data['user'] = {
            'id': self.user.id,
            'email': self.user.email,
            'role': self.user.role,
            'is_superuser': self.user.is_superuser,
            'is_baker_tilly_admin': self.user.is_baker_tilly_admin,
            'must_change_password': self.user.must_change_password,
        }
        
        return data

class RequestPasswordResetSerializer(serializers.Serializer):
    email = serializers.EmailField()

class ResetPasswordSerializer(serializers.Serializer):
    new_password = serializers.CharField(write_only=True)

    def validate_new_password(self, value):
        """Validate new password using centralized validation"""
        return validate_password(value, self.context.get('user'))