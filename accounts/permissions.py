from rest_framework.permissions import BasePermission
from .models import (
    RoleChoices, 
    AppUser, 
    LayerProfile, 
    GroupLayer, 
    SubsidiaryLayer, 
    BranchLayer,
    CustomUser
)

class BakerTillyAccessMixin:
    """
    Mixin to add Baker Tilly admin access to any permission class.
    Allows Baker Tilly admins to bypass normal permission checks.
    """
    def has_permission(self, request, view):
        # Baker Tilly admins always have permission
        if request.user.is_baker_tilly_admin:
            return True
        # Otherwise, check normal permissions
        return super().has_permission(request, view)

    def has_object_permission(self, request, view, obj):
        # Baker Tilly admins can access any object
        if request.user.is_baker_tilly_admin:
            return True
        # Otherwise, check normal permissions
        return super().has_object_permission(request, view, obj)

class BakerTillyAdmin(BasePermission):
    """
    Permission class for Baker Tilly staff.
    Combines client setup and advisory capabilities.
    """
    def has_permission(self, request, view):
        return request.user.is_baker_tilly_admin

    def has_object_permission(self, request, view, obj):
        if not request.user.is_baker_tilly_admin:
            return False
            
        # Full access to company and user management
        if isinstance(obj, (LayerProfile, CustomUser, AppUser, 
                          GroupLayer, SubsidiaryLayer, BranchLayer)):
            return True
            
        # Can manage templates and configurations
        if hasattr(obj, 'template_type') or hasattr(obj, 'is_configuration'):
            return True
            
        # Allow access to Template objects
        if obj.__class__.__name__ == 'Template':
            return True
            
        return False

class IsManagement(BakerTillyAccessMixin, BasePermission):
    """
    Permission class for Management role.
    Allows access to users with MANAGEMENT role and checks layer access.
    Also allows access to Baker Tilly admins.
    """
    def has_permission(self, request, view):
        return super().has_permission(request, view) or request.user.role == RoleChoices.MANAGEMENT

    def has_object_permission(self, request, view, obj):
        # Check if user has access to this layer
        if hasattr(obj, 'layer'):
            return obj.layer in request.user.app_users.values_list('layer', flat=True)
        return True

class IsOperation(BakerTillyAccessMixin, BasePermission):
    """
    Permission class for Operation role.
    Restricts access to users' own layer type.
    Also allows access to Baker Tilly admins.
    """
    def has_permission(self, request, view):
        return super().has_permission(request, view) or request.user.role == RoleChoices.OPERATION

    def has_object_permission(self, request, view, obj):
        user_layer = request.user.app_users.first().layer if request.user.app_users.exists() else None
        if not user_layer:
            return False
        return getattr(obj, 'layer_type', None) == user_layer.layer_type

class IsCreator(BakerTillyAccessMixin, BasePermission):
    """
    Permission class for Creator role.
    Creators have access to their assigned layers and child layers.
    Also allows access to Baker Tilly admins.
    """
    def has_permission(self, request, view):
        return super().has_permission(request, view) or request.user.role == RoleChoices.CREATOR

    def has_object_permission(self, request, view, obj):
        creator_layers = self.get_creator_layers(request.user)
        if hasattr(obj, 'layer'):
            return obj.layer in creator_layers
        return obj in creator_layers

    @staticmethod
    def get_creator_layers(user):
        """Get all layers that the creator has access to"""
        layers = []
        for app_user in user.app_users.all():
            layers.append(app_user.layer)
            # If it's a group layer, add subsidiaries and branches
            if app_user.layer.layer_type == 'GROUP':
                layers.extend(app_user.layer.subsidiaries.all())
                for subsidiary in app_user.layer.subsidiaries.all():
                    layers.extend(subsidiary.branches.all())
            # If it's a subsidiary layer, add branches
            elif app_user.layer.layer_type == 'SUBSIDIARY':
                layers.extend(app_user.layer.branches.all())
        return layers

class CanManageAppUsers(BakerTillyAccessMixin, BasePermission):
    """
    Permission class for managing AppUsers.
    Only CREATOR or MANAGEMENT roles can manage users in their layers.
    Also allows access to Baker Tilly admins through BakerTillyAccessMixin.
    """
    def has_permission(self, request, view):
        # First check if user is Baker Tilly admin through the mixin
        if super().has_permission(request, view):
            return True
        # Then check normal permissions
        return request.user.is_authenticated and request.user.role in [
            RoleChoices.CREATOR,
            RoleChoices.MANAGEMENT
        ]

    def has_object_permission(self, request, view, obj):
        # First check if user is Baker Tilly admin through the mixin
        if super().has_object_permission(request, view, obj):
            return True
            
        """Check if user can manage AppUsers in this layer"""
        layer = obj.layer if isinstance(obj, AppUser) else obj
        user_layers = request.user.app_users.values_list('layer', flat=True)
        
        # Check if the layer or any of its parent layers are in user's layers
        current_layer = layer
        while current_layer:
            if current_layer.id in user_layers:
                return True
            # Move up the hierarchy
            if hasattr(current_layer, 'subsidiary_layer'):
                current_layer = current_layer.subsidiary_layer
            elif hasattr(current_layer, 'group_layer'):
                current_layer = current_layer.group_layer
            else:
                break
        return False 