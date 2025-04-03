from django.db import migrations
# Remove direct Group/Permission imports, use apps registry
from django.contrib.auth.management import create_permissions
from django.apps import apps as global_apps

def add_data_management_permissions(apps, schema_editor):
    # Ensure permissions for the 'data_management' app are created first
    try:
        dm_app_config = global_apps.get_app_config('data_management')
        create_permissions(dm_app_config, verbosity=0)
        print("Successfully triggered permission creation for 'data_management' app (in 0004).")
    except Exception as e:
        print(f"Error triggering data_management permission creation (in 0004): {e}")

    # Get models via apps registry
    Group = apps.get_model('auth', 'Group')
    Permission = apps.get_model('auth', 'Permission')
    ContentType = apps.get_model('contenttypes', 'ContentType')

    # Get Baker Tilly Admin group
    try:
        bt_group = Group.objects.get(name='Baker Tilly Admin')
    except Group.DoesNotExist:
        print("Warning: 'Baker Tilly Admin' group not found in migration 0004. Skipping permission assignment.")
        return

    # Define models in data_management to grant permissions for
    models_to_permit = [
        'esgformcategory', 'esgform', 'esgmetric',
        'template', 'templateformselection', 'templateassignment',
        'boundaryitem', 'emissionfactor', 'esgdata', 'dataeditlog'
        # Note: esgmetricsubmission & esgmetricevidence are handled in 0005
    ]
    permissions_to_add = []

    # Query for the now-existing permissions
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
                    print(f"Warning (0004): Permission {codename} not found for data_management.{model_name}")
        except ContentType.DoesNotExist:
             print(f"Warning (0004): ContentType for data_management.{model_name} not found.")

    # Add permissions to group
    if permissions_to_add:
        bt_group.permissions.add(*permissions_to_add)
        print(f"Added {len(permissions_to_add)} data_management permissions (from 0004) to Baker Tilly Admin group")
    else:
        print("Warning (0004): No data_management permissions found to add.")

def remove_data_management_permissions(apps, schema_editor):
    # This reverse function might still be fragile, but keeps original intent
    Group = apps.get_model('auth', 'Group')
    Permission = apps.get_model('auth', 'Permission')
    try:
        bt_group = Group.objects.get(name='Baker Tilly Admin')
        data_management_permissions = Permission.objects.filter(
            content_type__app_label='data_management'
        )
        # Be careful removing *all* - only remove those added by this migration ideally
        # For simplicity, we follow the original logic here.
        for perm in data_management_permissions:
             # Check if the group actually has the perm before removing
            if bt_group.permissions.filter(pk=perm.pk).exists():
                bt_group.permissions.remove(perm)
    except Group.DoesNotExist:
        pass # Group doesn't exist, nothing to remove

class Migration(migrations.Migration):
    dependencies = [
        ('accounts', '0003_create_initial_bt_admin'),
        # Depend only on the initial data_management migration
        ('data_management', '0001_initial'), 
        ('contenttypes', '__latest__'),
        ('auth', '__latest__'),
    ]

    operations = [
        migrations.RunPython(add_data_management_permissions, remove_data_management_permissions),
    ] 