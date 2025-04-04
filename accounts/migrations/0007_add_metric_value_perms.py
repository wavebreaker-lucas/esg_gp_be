from django.db import migrations
from django.contrib.auth.management import create_permissions
from django.apps import apps as global_apps

def add_multi_value_permissions(apps, schema_editor):
    """Grant permissions for MetricValueField and MetricValue to Baker Tilly Admin group."""
    # Ensure permissions for the 'data_management' app are created
    try:
        dm_app_config = global_apps.get_app_config('data_management')
        # create_permissions is idempotent, safe to call again
        create_permissions(dm_app_config, verbosity=0)
    except Exception as e:
        print(f"Warning (0007): Error triggering data_management permission creation: {e}")
        # Continue execution even if permission creation fails, as they might already exist

    # Get models via apps registry
    Group = apps.get_model('auth', 'Group')
    Permission = apps.get_model('auth', 'Permission')
    ContentType = apps.get_model('contenttypes', 'ContentType')

    # Get Baker Tilly Admin group
    try:
        bt_group = Group.objects.get(name='Baker Tilly Admin')
    except Group.DoesNotExist:
        print("Warning (0007): 'Baker Tilly Admin' group not found. Skipping permission assignment.")
        return

    # Models to grant permissions for
    models_to_permit = ['metricvaluefield', 'metricvalue']
    permissions_to_add = []

    # Query for the specific permissions
    for model_name in models_to_permit:
        try:
            content_type = ContentType.objects.get(
                app_label='data_management',
                model=model_name
            )
            for action in ['add', 'change', 'delete', 'view']:
                codename = f"{action}_{model_name}"
                try:
                    perm = Permission.objects.get(
                        content_type=content_type,
                        codename=codename
                    )
                    permissions_to_add.append(perm)
                except Permission.DoesNotExist:
                    print(f"Warning (0007): Permission {codename} not found for data_management.{model_name}")
        except ContentType.DoesNotExist:
             print(f"Warning (0007): ContentType for data_management.{model_name} not found.")

    # Add permissions to group
    if permissions_to_add:
        bt_group.permissions.add(*permissions_to_add)
        print(f"Added {len(permissions_to_add)} multi-value permissions (from 0007) to Baker Tilly Admin group")
    else:
        print("Warning (0007): No multi-value permissions found to add.")

def remove_multi_value_permissions(apps, schema_editor):
    """Remove permissions for MetricValueField and MetricValue from Baker Tilly Admin group."""
    Group = apps.get_model('auth', 'Group')
    Permission = apps.get_model('auth', 'Permission')
    ContentType = apps.get_model('contenttypes', 'ContentType')

    try:
        bt_group = Group.objects.get(name='Baker Tilly Admin')
    except Group.DoesNotExist:
        print("Warning (0007 reverse): 'Baker Tilly Admin' group not found. Skipping permission removal.")
        return

    models_to_revoke = ['metricvaluefield', 'metricvalue']
    permissions_to_remove = []

    for model_name in models_to_revoke:
        try:
            content_type = ContentType.objects.get(
                app_label='data_management',
                model=model_name
            )
            # Find permissions specifically for these actions and model
            perms = Permission.objects.filter(
                content_type=content_type,
                codename__in=[f"{action}_{model_name}" for action in ['add', 'change', 'delete', 'view']]
            )
            permissions_to_remove.extend(list(perms))
        except ContentType.DoesNotExist:
            print(f"Warning (0007 reverse): ContentType for data_management.{model_name} not found.")

    # Remove permissions from group
    if permissions_to_remove:
        for perm in permissions_to_remove:
            # Check if the group actually has the perm before attempting removal
            if bt_group.permissions.filter(pk=perm.pk).exists():
                bt_group.permissions.remove(perm)
        print(f"Attempted removal of {len(permissions_to_remove)} multi-value permissions (from 0007) from Baker Tilly Admin group")

class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0006_layerprofile_created_by_admin'),  # Updated to depend on 0006 instead of 0005
        # Must depend on the data_management migration that creates MetricValueField and MetricValue
        ('data_management', '0004_esgmetricsubmission_esgmetricevidence_and_more'),
        ('contenttypes', '__latest__'), # Keep dependency
        ('auth', '__latest__'), # Keep dependency
    ]

    operations = [
        migrations.RunPython(add_multi_value_permissions, remove_multi_value_permissions),
    ] 