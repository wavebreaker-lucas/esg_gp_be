import logging
from django.core.exceptions import ObjectDoesNotExist, PermissionDenied # Added PermissionDenied

from accounts.models import (
    LayerProfile,
    GroupLayer,
    SubsidiaryLayer,
    BranchLayer,
    LayerTypeChoices
)
from data_management.models import TemplateAssignment
# Assuming get_accessible_layers and has_layer_access are in accounts/services.py
# If accounts.services is a package, the import might need adjustment.
# For now, assuming they can be imported directly if services.py is in the accounts app.
from accounts.services import get_accessible_layers as get_user_accessible_layer_profiles_qs
from accounts.services import has_layer_access

logger = logging.getLogger(__name__)

# --- Helper Functions ---

def get_specific_layer_instance(layer_proxy):
    """
    Helper to get the specific subclass instance (GroupLayer, SubsidiaryLayer, BranchLayer)
    from a LayerProfile proxy or instance.
    """
    if not isinstance(layer_proxy, LayerProfile):
        # Already a specific instance or not a LayerProfile at all
        return layer_proxy
    try:
        if layer_proxy.layer_type == LayerTypeChoices.GROUP:
            return layer_proxy.grouplayer
        elif layer_proxy.layer_type == LayerTypeChoices.SUBSIDIARY:
            return layer_proxy.subsidiarylayer
        elif layer_proxy.layer_type == LayerTypeChoices.BRANCH:
            return layer_proxy.branchlayer
    except ObjectDoesNotExist:
        logger.warning(
            f"Could not find specific subclass instance for LayerProfile ID "
            f"{layer_proxy.pk} with type {layer_proxy.layer_type}"
        )
    return layer_proxy # Fallback to base LayerProfile instance if specific not found

def get_layer_parent_specific(layer_instance):
    """
    Helper to get the specific parent layer instance (GroupLayer or SubsidiaryLayer).
    Returns None if no parent or if the input is not a BranchLayer or SubsidiaryLayer.
    """
    # Ensure we are working with a specific instance first
    specific_layer = get_specific_layer_instance(layer_instance)
    parent_profile = None
    if isinstance(specific_layer, BranchLayer):
        parent_profile = specific_layer.subsidiary_layer # This is a LayerProfile instance
    elif isinstance(specific_layer, SubsidiaryLayer):
        parent_profile = specific_layer.group_layer # This is a LayerProfile instance
    
    if parent_profile:
        return get_specific_layer_instance(parent_profile) # Convert parent profile to specific instance
    return None

def get_layer_children_specific(layer_instance):
    """
    Helper to get a QuerySet of specific child layer instances (SubsidiaryLayer or BranchLayer).
    Returns an empty QuerySet if no children or if the input is not a GroupLayer or SubsidiaryLayer.
    """
    specific_layer = get_specific_layer_instance(layer_instance)
    if isinstance(specific_layer, GroupLayer):
        # subsidiaries have a ForeignKey 'group_layer' to LayerProfile of the group
        # We need to fetch SubsidiaryLayer instances.
        return SubsidiaryLayer.objects.filter(group_layer_id=specific_layer.layerprofile_ptr_id)
    elif isinstance(specific_layer, SubsidiaryLayer):
        # branches have a ForeignKey 'subsidiary_layer' to LayerProfile of the subsidiary
        return BranchLayer.objects.filter(subsidiary_layer_id=specific_layer.layerprofile_ptr_id)
    return LayerProfile.objects.none() # Or an empty list if preferred

# --- Service Functions ---

def get_full_group_layer_data(group_id: int):
    """
    Fetches the full layer structure (specific instances) for a given group_id.
    Returns:
        A dictionary: {
            "group": GroupLayerInstance,
            "subsidiaries_with_branches": [
                (SubsidiaryLayerInstance, [BranchLayerInstance, ...]),
                ...
            ]
        }
    Raises:
        GroupLayer.DoesNotExist: If the group is not found.
    """
    try:
        # Fetch the GroupLayer instance directly
        group = GroupLayer.objects.get(pk=group_id)
    except GroupLayer.DoesNotExist:
        logger.warning(f"get_full_group_layer_data: GroupLayer with id {group_id} not found.")
        raise

    subsidiaries_with_branches = []
    # Get specific subsidiary instances linked to this group
    # Assuming SubsidiaryLayer.group_layer is a FK to the LayerProfile of the GroupLayer
    subsidiaries = SubsidiaryLayer.objects.filter(group_layer_id=group.layerprofile_ptr_id).select_related('layerprofile_ptr')

    for subsidiary in subsidiaries:
        branches_list = []
        # Get specific branch instances linked to this subsidiary
        # Assuming BranchLayer.subsidiary_layer is a FK to the LayerProfile of the SubsidiaryLayer
        branches = BranchLayer.objects.filter(subsidiary_layer_id=subsidiary.layerprofile_ptr_id).select_related('layerprofile_ptr')
        branches_list.extend(branches)
        subsidiaries_with_branches.append((subsidiary, branches_list))

    return {
        "group": group,
        "subsidiaries_with_branches": subsidiaries_with_branches
    }

def get_user_accessible_layer_data(user, assignment_id: int = None):
    """
    Fetches specific layer instances (GroupLayer, SubsidiaryLayer, BranchLayer)
    accessible to the user, optionally filtered by assignment context.
    Returns:
        A list of specific layer instances.
    Raises:
        TemplateAssignment.DoesNotExist, PermissionDenied, or other exceptions on failure.
    """
    # Start with LayerProfile QuerySet from the existing service
    # This returns LayerProfile instances.
    accessible_profiles_qs = get_user_accessible_layer_profiles_qs(user)
    
    # This set will store the specific layer instances that are deemed relevant
    relevant_specific_layers_set = set()

    if assignment_id:
        try:
            # Fetch the assignment and its associated LayerProfile
            assignment = TemplateAssignment.objects.select_related('layer').get(id=assignment_id)
            assignment_layer_profile = assignment.layer
            
            # Convert the assignment's LayerProfile to its specific instance (GroupLayer, etc.)
            assignment_layer_specific = get_specific_layer_instance(assignment_layer_profile)
            
            if not assignment_layer_specific or not isinstance(assignment_layer_specific, (GroupLayer, SubsidiaryLayer, BranchLayer)):
                 # If specific instance could not be determined or is just LayerProfile base
                 logger.warning(f"Could not determine specific layer type for assignment {assignment_id}'s layer {assignment_layer_profile.id}")
                 raise ObjectDoesNotExist(f"Specific layer for assignment {assignment_id} not found.")


            # Check if the user has access to this specific assignment layer
            if not has_layer_access(user, assignment_layer_specific):
                raise PermissionDenied(f'User {user.id} does not have access to the layer {assignment_layer_specific.id} of assignment {assignment_id}')

            relevant_specific_layers_set.add(assignment_layer_specific)

            # Add parent layers if accessible
            parent_specific = get_layer_parent_specific(assignment_layer_specific)
            while parent_specific:
                if has_layer_access(user, parent_specific):
                    relevant_specific_layers_set.add(parent_specific)
                parent_specific = get_layer_parent_specific(parent_specific)

            # Add child and grandchild layers if accessible
            # get_layer_children_specific returns a QuerySet of specific instances
            children_specific_qs = get_layer_children_specific(assignment_layer_specific)
            for child_specific in children_specific_qs:
                if has_layer_access(user, child_specific):
                    relevant_specific_layers_set.add(child_specific)
                    grandchildren_specific_qs = get_layer_children_specific(child_specific)
                    for grandchild_specific in grandchildren_specific_qs:
                        if has_layer_access(user, grandchild_specific):
                            relevant_specific_layers_set.add(grandchild_specific)
            
            # Now, filter the original accessible_profiles_qs to include only those whose
            # specific instances are in our relevant_specific_layers_set.
            # The IDs in relevant_specific_layers_set are PKs of the specific models,
            # which are also the PKs of their LayerProfile_ptr.
            relevant_profile_ids = {layer.pk for layer in relevant_specific_layers_set}
            
            final_layers_to_return = []
            # We need to iterate through the profiles that user has access to AND are relevant
            for profile in accessible_profiles_qs.filter(pk__in=relevant_profile_ids).select_related('grouplayer', 'subsidiarylayer', 'branchlayer'):
                final_layers_to_return.append(get_specific_layer_instance(profile))
            return final_layers_to_return

        except TemplateAssignment.DoesNotExist:
            logger.warning(f"get_user_accessible_layer_data: TemplateAssignment with id {assignment_id} not found for user {user.id}.")
            raise
        except PermissionDenied:
            logger.warning(f"get_user_accessible_layer_data: Permission denied for user {user.id} with assignment {assignment_id}.")
            raise
        except Exception as e:
            logger.error(f"Error in get_user_accessible_layer_data for assignment {assignment_id}, user {user.id}: {e}", exc_info=True)
            raise 
    else:
        # No assignment_id, so return all specific instances of user's accessible LayerProfiles
        all_accessible_specific_layers = []
        for profile in accessible_profiles_qs.select_related('grouplayer', 'subsidiarylayer', 'branchlayer'):
            all_accessible_specific_layers.append(get_specific_layer_instance(profile))
        return all_accessible_specific_layers 