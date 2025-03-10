from django.db import transaction
from django.utils import timezone
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny

from ..serializers import CustomUserSerializer, GroupLayerSerializer
from ..models import AppUser
from ..services import generate_otp_code, send_otp_via_email
from .mixins import ErrorHandlingMixin

class RegisterLayerProfileView(APIView, ErrorHandlingMixin):
    """
    API endpoint for registering a user and a GroupLayer.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        """
        Create a new user and their associated group layer.
        Sends OTP via email for verification.
        """
        try:
            user_data = request.data.get("user")
            group_layer_data = request.data.get("group_layer")

            if not user_data or not group_layer_data:
                return self.handle_validation_error(
                    "User data and group layer data are required."
                )

            with transaction.atomic():
                # Create user
                user_data["is_active"] = False
                user_data["must_change_password"] = False
                user_serializer = CustomUserSerializer(data=user_data)
                if not user_serializer.is_valid():
                    return self.handle_validation_error(user_serializer.errors)
                
                user = user_serializer.save()

                # Create group layer
                group_layer_serializer = GroupLayerSerializer(data=group_layer_data)
                if not group_layer_serializer.is_valid():
                    return self.handle_validation_error(group_layer_serializer.errors)
                
                group_layer = group_layer_serializer.save()

                # Create app user
                AppUser.objects.create(
                    user=user,
                    name=user_data.get("name", user.email.split("@")[0]),
                    layer=group_layer,
                    title=user_data.get("title", "CEO"),
                )

            # Generate and send OTP
            otp_code = generate_otp_code()
            user.otp_code = otp_code
            user.otp_created_at = timezone.now()
            user.save()

            send_otp_via_email(user.email, otp_code)
        
            return Response(
                {
                    "message": "User and Group Layer created successfully. Check email for OTP.",
                    "user": user_serializer.data,
                    "group_layer": group_layer_serializer.data,
                },
                status=status.HTTP_201_CREATED,
            )

        except Exception as e:
            return self.handle_unknown_error(e) 