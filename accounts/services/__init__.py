# This file can be empty.
# It makes Python treat the 'services' directory as a package. 

# Expose key functions/classes from modules within this package or related utilities
# to make them available directly from the accounts.services package.

from ..utils import validate_password, generate_otp_code, get_all_lower_layers, get_creator_layers, get_parent_layer

# If you had other service modules within the 'services' package, e.g., 'auth_services.py',
# you might expose their contents like this:
# from .auth_services import some_other_auth_service_function

# Or from layer_services.py if you want to expose its functions at this level:
# from .layer_services import get_full_group_layer_data, get_user_accessible_layer_data 

# From .core (the file previously known as accounts/services.py)
from .core import (
    get_flat_sorted_layers,
    send_email_to_user,
    send_otp_via_email,
    has_layer_access,
    get_accessible_layers,
    has_permission_to_manage_users,
    is_creator_on_layer,
    get_user_layers_and_parents_ids,
    send_password_reset_email
)

# From .layer_services (our newly created service module)
from .layer_services import (
    get_specific_layer_instance,
    get_layer_parent_specific,
    get_layer_children_specific,
    get_full_group_layer_data,
    get_user_accessible_layer_data
)

# Listing all exposed names for clarity (optional, but good practice)
__all__ = [
    'validate_password', 'generate_otp_code', 'get_all_lower_layers', 'get_creator_layers', 'get_parent_layer',
    'get_flat_sorted_layers',
    'send_email_to_user',
    'send_otp_via_email',
    'has_layer_access',
    'get_accessible_layers',
    'has_permission_to_manage_users',
    'is_creator_on_layer',
    'get_user_layers_and_parents_ids',
    'send_password_reset_email',
    'get_specific_layer_instance',
    'get_layer_parent_specific',
    'get_layer_children_specific',
    'get_full_group_layer_data',
    'get_user_accessible_layer_data',
] 