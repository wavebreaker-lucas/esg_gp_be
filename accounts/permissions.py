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
# Import BaseESGMetric to check its instances
from data_management.models.polymorphic_metrics import BaseESGMetric
# Also import other needed models if not implicitly handled
from data_management.models.templates import Template, ESGForm, ESGFormCategory
from data_management.models.factors import GHGEmissionFactor

class BakerTillyAccessMixin:
    """
    Mixin to add Baker Tilly admin access to any permission class.
    Allows Baker Tilly admins to bypass normal permission checks.
    """
    def has_permission(self, request, view):
        # Baker Tilly admins always have permission
        # Use safer getattr check
        if getattr(request.user, 'is_baker_tilly_admin', False):
            return True
        # Otherwise, check normal permissions
        # Ensure super() is called correctly based on MRO if this mixin is used elsewhere
        if hasattr(super(), 'has_permission'):
             return super().has_permission(request, view)
        return True # Or False depending on desired default if no super().has_permission

    def has_object_permission(self, request, view, obj):
        # Baker Tilly admins can access any object
        if getattr(request.user, 'is_baker_tilly_admin', False):
            return True
        # Otherwise, check normal permissions
        if hasattr(super(), 'has_object_permission'):
             return super().has_object_permission(request, view, obj)
        return True # Or False depending on desired default

class BakerTillyAdmin(BasePermission):
    """
    Permission class for Baker Tilly staff.
    Combines client setup and advisory capabilities.
    """
    def has_permission(self, request, view):
        is_admin = getattr(request.user, 'is_baker_tilly_admin', False)
        # print(f"--- BakerTillyAdmin has_permission check: User={request.user}, IsAdmin={is_admin} ---")
        return is_admin

    def has_object_permission(self, request, view, obj):
        print(f"--- BakerTillyAdmin: Checking object permission for user {request.user} on object {obj} (type: {type(obj)}) ---")
        is_admin = getattr(request.user, 'is_baker_tilly_admin', False) # Safer check
        print(f"User is_baker_tilly_admin: {is_admin}")

        if not is_admin:
            print("Permission DENIED: User is not Baker Tilly Admin.")
            return False

        # Add checks for other types if BakerTillyAdmin should manage them
        if isinstance(obj, (LayerProfile, CustomUser, AppUser, GroupLayer, SubsidiaryLayer, BranchLayer)):
             print(f"Permission GRANTED: Object is Layer/User type.")
             return True
        if isinstance(obj, (Template, ESGForm, ESGFormCategory)):
             print(f"Permission GRANTED: Object is Template/Form/Category type.")
             return True

        # Check for Polymorphic Metrics
        is_metric = isinstance(obj, BaseESGMetric)
        print(f"Is object instance of BaseESGMetric? {is_metric}")
        if is_metric:
             print(f"Permission GRANTED: Object is BaseESGMetric instance.")
             return True

        # Check for GHG Emission Factors
        if isinstance(obj, GHGEmissionFactor):
             print(f"Permission GRANTED: Object is GHGEmissionFactor instance.")
             return True

        print("Permission DENIED: Object type not recognized for admin object permission.")
        return False # Default deny

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