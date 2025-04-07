from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
import random, string
from .models import LayerTypeChoices, LayerProfile, GroupLayer, SubsidiaryLayer, BranchLayer

def validate_password(password, user=None):
    """
    Validate password strength according to security requirements.
    
    Args:
        password (str): Password to validate
        user (CustomUser, optional): User for additional checks
        
    Raises:
        ValidationError: If password doesn't meet requirements
    """
    if len(password) < 8:
        raise ValidationError(
            _("Password must be at least 8 characters long."),
            code='password_too_short',
        )
    
    if not any(char.isdigit() for char in password):
        raise ValidationError(
            _("Password must contain at least one number."),
            code='password_no_number',
        )
        
    if not any(char.isupper() for char in password):
        raise ValidationError(
            _("Password must contain at least one uppercase letter."),
            code='password_no_upper',
        )
        
    if not any(char.islower() for char in password):
        raise ValidationError(
            _("Password must contain at least one lowercase letter."),
            code='password_no_lower',
        )

    if user is not None and user.is_staff and len(password) < 12:
        raise ValidationError(
            _("Administrator passwords must be at least 12 characters long."),
            code='password_admin_too_short',
        )
        
    return password

def generate_otp_code(length=6):
    """Generate a random OTP code of specified length"""
    digits = string.digits
    return ''.join(random.choice(digits) for _ in range(length))

def get_all_lower_layers(layer):
    """
    Fetch the current layer and all lower layers (subsidiary and branch layers)
    under a given layer.
    """
    layers = [layer.id]

    if layer.layer_type == LayerTypeChoices.GROUP:
        subsidiary_ids = SubsidiaryLayer.objects.filter(group_layer=layer).values_list('id', flat=True)
        branch_ids = BranchLayer.objects.filter(subsidiary_layer__id__in=subsidiary_ids).values_list('id', flat=True)
        layers.extend(subsidiary_ids)
        layers.extend(branch_ids)

    elif layer.layer_type == LayerTypeChoices.SUBSIDIARY:
        branch_ids = BranchLayer.objects.filter(subsidiary_layer=layer).values_list('id', flat=True)
        layers.extend(branch_ids)

    return LayerProfile.objects.filter(id__in=layers)

def get_creator_layers(user):
    """
    Fetch all layers associated with the creator's GROUP layer.
    (Original, potentially restrictive logic)
    """
    # Find the IDs of any GROUP layers the user is directly assigned to via AppUser
    group_ids = GroupLayer.objects.filter(app_users__user=user).values_list('id', flat=True)

    # Find all subsidiary IDs belonging to those group(s)
    subsidiary_ids = SubsidiaryLayer.objects.filter(group_layer__id__in=group_ids).values_list('id', flat=True)

    # Find all branch IDs belonging to those subsidiaries
    branch_ids = BranchLayer.objects.filter(subsidiary_layer__id__in=subsidiary_ids).values_list('id', flat=True)

    all_accessible_ids = list(group_ids) + list(subsidiary_ids) + list(branch_ids)

    # Return a queryset containing the Group layers, their subsidiaries, and their branches
    return LayerProfile.objects.filter(
        id__in=all_accessible_ids
    )

def get_parent_layer(layer):
    """Return the parent layer of a given layer (if applicable)."""
    if isinstance(layer, SubsidiaryLayer):
        return layer.group_layer
    elif isinstance(layer, BranchLayer):
        return layer.subsidiary_layer
    return None 