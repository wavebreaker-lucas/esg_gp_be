import re
from django.core.mail import EmailMessage, send_mail, EmailMultiAlternatives
from rest_framework import serializers
from django.conf import settings
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
import uuid
from django.utils import timezone

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
    subject = "Your Account Has Been Created on ESG Platform / 您在ESG平台的账户已成功创建"
    
    # Plain text version
    text_message = (
        f"Dear User,\n\n"
        f"An account has been successfully created for you on ESG platform.\n\n"
        f"Please use the following temporary credentials to log in:\n\n"
        f"Email: {email}\n"
        f"Temporary Password: {password}\n\n"
        f"For security purposes, you will be required to change this temporary password upon your first login.\n\n"
        f"If you did not request this account or believe this email was sent in error, please contact our support team immediately at support@greenpoint.com.hk.\n\n"
        f"Sincerely,\n"
        f"The ESG Platform Team\n\n"
        f"--------------------------------------------------\n\n"
        f"尊敬的用户，\n\n"
        f"您的ESG平台账户已成功创建。\n\n"
        f"请使用以下临时凭证登录：\n\n"
        f"电子邮件：{email}\n"
        f"临时密码：{password}\n\n"
        f"出于安全考虑，您将需要在首次登录时更改此临时密码。\n\n"
        f"如果您没有申请此账户或认为此邮件是错误发送的，请立即通过 support@greenpoint.com.hk 联系我们的支持团队。\n\n"
        f"此致，\n"
        f"ESG平台团队"
    )
    
    # HTML version
    html_message = (
        f"<p>Dear User,</p>"
        f"<p>An account has been successfully created for you on ESG platform.</p>"
        f"<p>Please use the following temporary credentials to log in:</p>"
        f"<ul>"
        f"<li><strong>Email:</strong> {email}</li>"
        f"<li><strong>Temporary Password:</strong> {password}</li>"
        f"</ul>"
        f"<p>For security purposes, you will be required to change this temporary password upon your first login.</p>"
        f"<p>If you did not request this account or believe this email was sent in error, please contact our support team immediately at <a href='mailto:support@greenpoint.com.hk'>support@greenpoint.com.hk</a>.</p>"
        f"<p>Sincerely,<br>The ESG Platform Team</p>"
        f"<hr>"
        f"<p>尊敬的用户，</p>"
        f"<p>您的ESG平台账户已成功创建。</p>"
        f"<p>请使用以下临时凭证登录：</p>"
        f"<ul>"
        f"<li><strong>电子邮件：</strong> {email}</li>"
        f"<li><strong>临时密码：</strong> {password}</li>"
        f"</ul>"
        f"<p>出于安全考虑，您将需要在首次登录时更改此临时密码。</p>"
        f"<p>如果您没有申请此账户或认为此邮件是错误发送的，请立即通过 <a href='mailto:support@greenpoint.com.hk'>support@greenpoint.com.hk</a> 联系我们的支持团队。</p>"
        f"<p>此致，<br>ESG平台团队</p>"
    )

    try:
        print(f"Attempting to send email to {email}")
        print(f"Using sender: {settings.DEFAULT_FROM_EMAIL}")
        print(f"Backend: {settings.EMAIL_BACKEND}")
        
        # Use EmailMultiAlternatives
        email_message = EmailMultiAlternatives(
            subject,
            text_message,  # Plain text body
            settings.DEFAULT_FROM_EMAIL,
            [email],
        )
        email_message.attach_alternative(html_message, "text/html") # Attach HTML version
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
    # Baker Tilly Admins should bypass this check
    if getattr(user, 'is_baker_tilly_admin', False):
        return True

    # Handle case where layer is passed as ID
    layer_instance = None
    if isinstance(layer, LayerProfile):
        layer_instance = layer
    elif isinstance(layer, (int, str)):
        try:
            layer_id = int(layer)
            # Use select_related to potentially optimize if needed later
            layer_instance = LayerProfile.objects.get(pk=layer_id)
        except (ValueError, TypeError, LayerProfile.DoesNotExist):
             return False # Invalid layer ID or layer not found
    else:
        return False

    # Check if the user has any AppUser record assigned
    if not user.app_users.exists():
         return False

    user_role = getattr(user, 'role', None) # Get user role

    result = False # Default to False
    if user_role == RoleChoices.MANAGEMENT:
        # Check if 'layer' is within the hierarchy managed by this user
        manager_layer = user.app_users.first().layer
        if manager_layer:
            accessible_layers_qs = get_all_lower_layers(manager_layer)
            # Check if layer_instance.pk is in the queryset's values
            result = accessible_layers_qs.filter(pk=layer_instance.pk).exists()
        else:
             result = False
            
    elif user_role == RoleChoices.OPERATION:
        # Operation users only have access to their direct layer
        operation_layer = user.app_users.first().layer
        if operation_layer:
            result = (layer_instance.pk == operation_layer.pk)
        else:
             result = False
            
    elif user_role == RoleChoices.CREATOR:
        # Check if 'layer' is one the creator manages (direct or children)
        creator_accessible_layers_qs = get_creator_layers(user)
        # Check if layer_instance.pk is in the queryset's values
        result = creator_accessible_layers_qs.filter(pk=layer_instance.pk).exists()
        
    else:
        result = False
        
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

def get_user_layers_and_parents_ids(user):
    """Gets all layer IDs accessible to the user (direct + parents).

    This is used to find assignments inherited from parent layers.
    """
    # Ensure user is authenticated or handle appropriately if needed
    if not user or not user.is_authenticated:
        return set()

    user_app_users = AppUser.objects.filter(user=user).select_related('layer')
    # Handle cases where a user might somehow not have an AppUser/Layer assigned
    user_layers = [app_user.layer for app_user in user_app_users if app_user.layer]

    accessible_layer_ids = set()
    for layer in user_layers:
        accessible_layer_ids.add(layer.id)

        current_layer = layer
        # Traverse up the hierarchy
        # Using hasattr avoids needing specific LayerType imports here
        if hasattr(current_layer, 'branchlayer'):
            # If it's a branch, get subsidiary and potentially group
            subsidiary = current_layer.branchlayer.subsidiary_layer
            if subsidiary:
                accessible_layer_ids.add(subsidiary.id)
                if hasattr(subsidiary, 'subsidiarylayer') and hasattr(subsidiary.subsidiarylayer, 'group_layer'):
                    group = subsidiary.subsidiarylayer.group_layer
                    if group:
                        accessible_layer_ids.add(group.id)

        elif hasattr(current_layer, 'subsidiarylayer'):
             # If it's a subsidiary, get group
             if hasattr(current_layer.subsidiarylayer, 'group_layer'):
                 group = current_layer.subsidiarylayer.group_layer
                 if group:
                     accessible_layer_ids.add(group.id)

    return accessible_layer_ids 

def send_password_reset_email(user):
    """Generate reset token, save it, and send password reset email."""
    # Generate reset token
    user.reset_token = uuid.uuid4()
    user.reset_token_created_at = timezone.now()
    user.save(update_fields=['reset_token', 'reset_token_created_at'])

    # Send reset email
    reset_link = f"{settings.FRONTEND_URL}/reset-password/{user.reset_token}/"
    subject = "Password Reset Request for Your ESG Platform Account / 您的ESG平台账户密码重置请求"
    
    # Plain text version
    text_message = (
        f"Dear User,\n\n"
        f"We received a request to reset the password for your account associated with the email address {user.email}.\n\n"
        f"To proceed with resetting your password, please click the link below:\n"
        f"{reset_link}\n\n"
        f"For security reasons, this link will expire in one hour. If you did not initiate this request, please disregard this email or contact our support team immediately at support@greenpoint.com.hk if you have concerns.\n\n"
        f"Sincerely,\n"
        f"The ESG Platform Team\n\n"
        f"--------------------------------------------------\n\n"
        f"尊敬的用户，\n\n"
        f"我们收到了重置与电子邮件地址 {user.email} 相关联的账户密码的请求。\n\n"
        f"要继续重置您的密码，请点击下面的链接：\n"
        f"{reset_link}\n\n"
        f"出于安全考虑，此链接将在一小时内失效。如果您没有发起此请求，请忽略此电子邮件，或者如果您有任何疑虑，请立即通过 support@greenpoint.com.hk 联系我们的支持团队。\n\n"
        f"此致，\n"
        f"ESG平台团队"
    )
    
    # HTML version
    html_message = (
        f"<p>Dear User,</p>"
        f"<p>We received a request to reset the password for your account associated with the email address {user.email}.</p>"
        f"<p>To proceed with resetting your password, please click the link below:</p>"
        f"<p><a href='{reset_link}'>{reset_link}</a></p>"
        f"<p>For security reasons, this link will expire in one hour. If you did not initiate this request, please disregard this email or contact our support team immediately at <a href='mailto:support@greenpoint.com.hk'>support@greenpoint.com.hk</a> if you have concerns.</p>"
        f"<p>Sincerely,<br>The ESG Platform Team</p>"
        f"<hr>"
        f"<p>尊敬的用户，</p>"
        f"<p>我们收到了重置与电子邮件地址 {user.email} 相关联的账户密码的请求。</p>"
        f"<p>要继续重置您的密码，请点击下面的链接：</p>"
        f"<p><a href='{reset_link}'>{reset_link}</a></p>"
        f"<p>出于安全考虑，此链接将在一小时内失效。如果您没有发起此请求，请忽略此电子邮件，或者如果您有任何疑虑，请立即通过 <a href='mailto:support@greenpoint.com.hk'>support@greenpoint.com.hk</a> 联系我们的支持团队。</p>"
        f"<p>此致，<br>ESG平台团队</p>"
    )
    
    try:
        print(f"Attempting to send password reset email to {user.email}")
        print(f"Using sender: {settings.DEFAULT_FROM_EMAIL}")
        print(f"Backend: {settings.EMAIL_BACKEND}")

        # Use EmailMultiAlternatives
        email_message = EmailMultiAlternatives(
            subject,
            text_message, # Plain text body
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
        )
        email_message.attach_alternative(html_message, "text/html") # Attach HTML version
        result = email_message.send(fail_silently=False)
        print(f"Password reset email send result: {result}")
        return True
    except Exception as e:
        import traceback
        print(f"Error sending password reset email: {str(e)}")
        print(f"Error type: {type(e).__name__}")
        print(f"Traceback: {traceback.format_exc()}")
        return False # Indicate failure 