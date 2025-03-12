from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
import random, string
from .models import LayerTypeChoices, LayerProfile, GroupLayer, SubsidiaryLayer, BranchLayer
from .serializers.models import LayerProfileSerializer

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
    """
    group_ids = GroupLayer.objects.filter(app_users__user=user).values_list('id', flat=True)
    subsidiary_ids = SubsidiaryLayer.objects.filter(group_layer__id__in=group_ids).values_list('id', flat=True)
    branch_ids = BranchLayer.objects.filter(subsidiary_layer__id__in=subsidiary_ids).values_list('id', flat=True)

    return LayerProfile.objects.filter(
        id__in=list(group_ids) + list(subsidiary_ids) + list(branch_ids)
    )

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

def get_parent_layer(layer):
    """Return the parent layer of a given layer (if applicable)."""
    if isinstance(layer, SubsidiaryLayer):
        return layer.group_layer
    elif isinstance(layer, BranchLayer):
        return layer.subsidiary_layer
    return None 