import re
from django.core.mail import EmailMessage, send_mail
from rest_framework import serializers
from django.conf import settings
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType

from .models import RoleChoices, LayerTypeChoices, GroupLayer, SubsidiaryLayer, LayerProfile, BranchLayer, AppUser, CustomUser
from .utils import (
    validate_password,
    generate_otp_code,
    get_all_lower_layers,
    get_creator_layers,
    get_parent_layer
)
from .serializers.models import LayerProfileSerializer

# Common password list for security validation
COMMON_PASSWORDS = {
    "password", "123456", "12345678Aa!", "12345678aA!", 
    "12345678Aa.", "12345678aA.", "qwerty", "letmein", 
    "welcome", "admin"
}

def get_flat_sorted_layers(accessible_layers):
    """
    Convert hierarchical layer structure to flat sorted list
    """
    flat_list = []
    group_qs = accessible_layers.filter(layer_type=LayerTypeChoices.GROUP)
    
    if group_qs.exists():
        group_ids = group_qs.values_list('id', flat=True)
        groups = GroupLayer.objects.filter(id__in=group_ids).order_by('created_at')
        for group in groups:
            group_serialized = LayerProfileSerializer(group).data
            flat_list.append(group_serialized)
            
            subsidiary_ids = accessible_layers.filter(
                layer_type=LayerTypeChoices.SUBSIDIARY
            ).values_list('id', flat=True)
            subsidiaries = SubsidiaryLayer.objects.filter(
                group_layer=group,
                id__in=subsidiary_ids
            ).order_by('created_at')
            
            for subsidiary in subsidiaries:
                subsidiary_serialized = LayerProfileSerializer(subsidiary).data
                flat_list.append(subsidiary_serialized)
                
                branch_ids = accessible_layers.filter(
                    layer_type=LayerTypeChoices.BRANCH
                ).values_list('id', flat=True)
                branches = BranchLayer.objects.filter(
                    subsidiary_layer=subsidiary,
                    id__in=branch_ids
                ).order_by('created_at')
                
                for branch in branches:
                    branch_serialized = LayerProfileSerializer(branch).data
                    flat_list.append(branch_serialized)
        return flat_list
    
    # If no GROUP layer, just serialize all accessible layers
    return LayerProfileSerializer(
        accessible_layers.order_by('created_at'), 
        many=True
    ).data

def send_email_to_user(email, password):
    """
    Send an email to the user with their generated password.

    Args:
        email (str): The user's email address.
        password (str): The generated password for the user.

    Returns:
        bool: True if the email is sent successfully, False otherwise.
    """
    subject = "Welcome to Our Platform"
    message = (
        f"Dear User,\n\n"
        f"Your account has been created successfully.\n"
        f"Here are your login details:\n\n"
        f"Email: {email}\n"
        f"Password: {password}\n\n"
        f"Please log in and change your password as soon as possible.\n\n"
        f"Best regards,\n"
        f"The Team"
    )

    try:
        email_message = EmailMessage(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [email],
        )
        email_message.send(fail_silently=False)
        return True
    except Exception as e:
        # Log the exception (you can use your logger here)
        print(f"Error sending email: {str(e)}")
        return False

def send_otp_via_email(email, otp_code):
    """Send OTP code via email"""
    subject = "OTP verification"
    message = f"Your OTP code for verification: {otp_code}\nYou have 10min to apply it."
    from_email = settings.DEFAULT_FROM_EMAIL
    recipient_list = [email]

    send_mail(
        subject,
        message,
        from_email,
        recipient_list,
        fail_silently=False,
    )

def has_layer_access(user, layer):
    """
    Check if the user has access to a specific layer or its sub-layers.
    
    Args:
        user: CustomUser instance
        layer: LayerProfile instance
    
    Returns:
        bool: True if user has access to the layer
    """
    if user.role == RoleChoices.MANAGEMENT:
        return layer in get_all_lower_layers(user.app_users.first().layer)
    elif user.role == RoleChoices.OPERATION:
        return layer == user.app_users.first().layer
    elif user.role == RoleChoices.CREATOR:
        return layer in get_creator_layers(user)
    return False

def get_accessible_layers(user):
    """
    Get all layers accessible to the user based on their role.
    """
    if user.role == RoleChoices.MANAGEMENT:
        return get_all_lower_layers(user.app_users.first().layer)

    elif user.role == RoleChoices.OPERATION:
        return LayerProfile.objects.filter(
            app_users__user=user,
            layer_type=user.app_users.first().layer.layer_type,
        )

    elif user.role == RoleChoices.CREATOR:
        return get_creator_layers(user)

    return LayerProfile.objects.none()

def has_permission_to_manage_users(user, layer):
    """
    Check if the user has permission to manage users for a specific layer.
    Only CREATOR or MANAGEMENT roles can manage users, and they must have
    access to the layer or its parent layers.
    """
    if user.role in [RoleChoices.CREATOR, RoleChoices.MANAGEMENT]:
        accessible_layers = get_accessible_layers(user)
        return layer in accessible_layers

    return False

def is_creator_on_layer(user, layer):
    """Check if the given user is a CREATOR on the specified layer."""
    return AppUser.objects.filter(
        layer=layer,
        user=user,
        user__role=RoleChoices.CREATOR
    ).exists() 