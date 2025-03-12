import uuid
from django.utils import timezone
from django.conf import settings
from django.core.mail import send_mail
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.tokens import RefreshToken
from ..models import CustomUser
from ..serializers.auth import (
    CustomTokenObtainPairSerializer,
    RequestPasswordResetSerializer,
    ResetPasswordSerializer
)
from ..services import generate_otp_code, send_otp_via_email
from .mixins import ErrorHandlingMixin

class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer
    permission_classes = [AllowAny]

class LogoutView(APIView, ErrorHandlingMixin):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data.get('refresh')
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response(
                {"message": "Logged out successfully"},
                status=status.HTTP_200_OK
            )
        except Exception as e:
            return self.handle_unknown_error(e)

class ResendOTPView(APIView, ErrorHandlingMixin):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get("email")
        if not email:
            return self.handle_validation_error("Email is required.")

        try:
            user = CustomUser.objects.get(email=email)
        except CustomUser.DoesNotExist:
            return self.handle_not_found_error("User not found.")

        # Generate new OTP
        otp_code = generate_otp_code()
        user.otp_code = otp_code
        user.otp_created_at = timezone.now()
        user.save()

        # Send new OTP via email
        try:
            send_otp_via_email(user.email, otp_code)
            return Response(
                {"message": "New OTP code sent successfully."},
                status=status.HTTP_200_OK
            )
        except Exception as e:
            return self.handle_unknown_error("Failed to send OTP code.")

class VerifyOTPView(APIView, ErrorHandlingMixin):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get("email")
        otp_code = request.data.get("otp_code")

        if not email or not otp_code:
            return self.handle_validation_error("Email and OTP code are required.")

        try:
            user = CustomUser.objects.get(email=email)
        except CustomUser.DoesNotExist:
            return self.handle_not_found_error("User not found.")

        if user.otp_code != otp_code or user.is_otp_expired():
            return self.handle_validation_error("Invalid or expired OTP code.")

        user.is_active = True
        user.otp_code = None
        user.otp_created_at = None
        user.save()

        return Response(
            {"message": "Email verified successfully."},
            status=status.HTTP_200_OK
        )

class RequestPasswordResetView(APIView, ErrorHandlingMixin):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RequestPasswordResetSerializer(data=request.data)
        if not serializer.is_valid():
            return self.handle_validation_error(serializer.errors)

        email = serializer.validated_data['email']
        try:
            user = CustomUser.objects.get(email=email)
        except CustomUser.DoesNotExist:
            return self.handle_not_found_error("User not found.")

        # Generate reset token
        user.reset_token = uuid.uuid4()
        user.reset_token_created_at = timezone.now()
        user.save()

        # Send reset email
        reset_link = f"{settings.FRONTEND_URL}/reset-password/{user.reset_token}/"
        send_mail(
            "Password Reset Request",
            f"Click this link to reset your password: {reset_link}",
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            fail_silently=False,
        )

        return Response(
            {"message": "Password reset link sent to your email."},
            status=status.HTTP_200_OK
        )

class ResetPasswordView(APIView, ErrorHandlingMixin):
    permission_classes = [AllowAny]

    def post(self, request, reset_token):
        serializer = ResetPasswordSerializer(data=request.data)
        if not serializer.is_valid():
            return self.handle_validation_error(serializer.errors)

        try:
            user = CustomUser.objects.get(reset_token=reset_token)
        except CustomUser.DoesNotExist:
            return self.handle_not_found_error("Invalid reset token.")

        if user.reset_token_created_at and \
           (timezone.now() - user.reset_token_created_at).seconds > 3600:
            return self.handle_validation_error("Reset token has expired.")

        # Update password
        user.set_password(serializer.validated_data['new_password'])
        user.reset_token = None
        user.reset_token_created_at = None
        user.password_updated_at = timezone.now()
        user.must_change_password = False
        user.save()

        return Response(
            {"message": "Password reset successfully."},
            status=status.HTTP_200_OK
        )