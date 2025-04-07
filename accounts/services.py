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
        print(f"Attempting to send email to {email}")
        print(f"Using sender: {settings.DEFAULT_FROM_EMAIL}")
        print(f"Backend: {settings.EMAIL_BACKEND}")
        
        email_message = EmailMessage(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [email],
        )
        result = email_message.send(fail_silently=False)
        print(f"Email send result: {result}")
        return True
    except Exception as e:
        # Log the exception with more details
        import traceback
        print(f"Error sending email: {str(e)}")
        print(f"Error type: {type(e).__name__}")
        print(f"Traceback: {traceback.format_exc()}")
        return False

def send_otp_via_email(email, otp_code):
    """Send OTP code via email"""
    subject = "OTP verification"
    message = f"Your OTP code for verification: {otp_code}\nYou have 10min to apply it."
    from_email = settings.DEFAULT_FROM_EMAIL
    recipient_list = [email]

    try:
        print(f"Attempting to send OTP email to {email}")
        print(f"Using sender: {from_email}")
        print(f"Backend: {settings.EMAIL_BACKEND}")
        
        result = send_mail(
            subject,
            message,
            from_email,
            recipient_list,
            fail_silently=False,
        )
        print(f"OTP email send result: {result}")
        return True
    except Exception as e:
        # Log the exception with more details
        import traceback
        print(f"Error sending OTP email: {str(e)}")
        print(f"Error type: {type(e).__name__}")
        print(f"Traceback: {traceback.format_exc()}")
        raise  # Re-raise the exception to maintain original behavior

def has_layer_access(user, layer):
    """
    Check if the user has access to a specific layer or its sub-layers.
    
    Args:
        user: CustomUser instance
        layer: LayerProfile instance OR LayerProfile ID
    
    Returns:
        bool: True if user has access to the layer
    """
    print(f"--- has_layer_access: Called for user {user} (ID: {user.pk}) with layer arg: {layer} (type: {type(layer)}) ---")
    
    # Baker Tilly Admins should bypass this check
    if getattr(user, 'is_baker_tilly_admin', False):
        print("--- has_layer_access: User is admin, returning True (bypass). ---")
        return True

    # Handle case where layer is passed as ID
    layer_instance = None
    if isinstance(layer, LayerProfile):
        layer_instance = layer
        print(f"--- has_layer_access: Layer arg is instance ID: {layer_instance.pk} ---")
    elif isinstance(layer, (int, str)):
        try:
            layer_id = int(layer)
            # Use select_related to potentially optimize if needed later
            layer_instance = LayerProfile.objects.get(pk=layer_id)
            print(f"--- has_layer_access: Layer arg is ID, fetched instance: {layer_instance.pk} ---")
        except (ValueError, TypeError, LayerProfile.DoesNotExist):
             print(f"--- has_layer_access: Invalid layer ID {layer} or layer not found, returning False. ---")
             return False # Invalid layer ID or layer not found
    else:
        print(f"--- has_layer_access: Invalid type for layer argument ({type(layer)}), returning False. ---")
        return False

    # Check if the user has any AppUser record assigned
    if not user.app_users.exists():
         print(f"--- has_layer_access: User has no AppUser assignments, returning False. ---")
         return False

    user_role = getattr(user, 'role', None) # Get user role
    print(f"--- has_layer_access: User role is {user_role} ---")

    result = False # Default to False
    if user_role == RoleChoices.MANAGEMENT:
        print("--- has_layer_access: Checking MANAGEMENT logic... ---")
        # Check if 'layer' is within the hierarchy managed by this user
        # Assumes manager is assigned to one layer via AppUser
        manager_layer = user.app_users.first().layer
        if manager_layer:
            print(f"--- has_layer_access: Manager Layer ID: {manager_layer.pk} ---")
            accessible_layers_qs = get_all_lower_layers(manager_layer)
            # Check if layer_instance.pk is in the queryset's values
            result = accessible_layers_qs.filter(pk=layer_instance.pk).exists()
            print(f"--- has_layer_access: Target layer {layer_instance.pk} in manager's hierarchy? {result} ---")
        else:
             print("--- has_layer_access: Management user has no assigned layer, returning False. ---")
             result = False
            
    elif user_role == RoleChoices.OPERATION:
        print("--- has_layer_access: Checking OPERATION logic... ---")
        # Operation users only have access to their direct layer
        operation_layer = user.app_users.first().layer
        if operation_layer:
            print(f"--- has_layer_access: Operation Layer ID: {operation_layer.pk} ---")
            result = (layer_instance.pk == operation_layer.pk)
            print(f"--- has_layer_access: Target layer {layer_instance.pk} matches operation layer? {result} ---")
        else:
             print("--- has_layer_access: Operation user has no assigned layer, returning False. ---")
             result = False
            
    elif user_role == RoleChoices.CREATOR:
        print("--- has_layer_access: Checking CREATOR logic... ---")
        # Check if 'layer' is one the creator manages (direct or children)
        creator_accessible_layers_qs = get_creator_layers(user)
        # Check if layer_instance.pk is in the queryset's values
        result = creator_accessible_layers_qs.filter(pk=layer_instance.pk).exists()
        print(f"--- has_layer_access: Target layer {layer_instance.pk} in creator's accessible layers? {result} ---")
        # For debugging, you could print the accessible layer IDs:
        # print(f"--- has_layer_access: Creator accessible layer IDs: {list(creator_accessible_layers_qs.values_list('pk', flat=True))} ---")
        
    else:
        print(f"--- has_layer_access: Unknown or unhandled user role {user_role}, returning False. ---")
        result = False
        
    print(f"--- has_layer_access: Final result: {result} ---")
    return result

def get_accessible_layers(user):
    """
    Get all layers accessible to the user based on their role.
    """
    # Baker Tilly admins have access to all layers
    if user.is_baker_tilly_admin:
        return LayerProfile.objects.all()

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