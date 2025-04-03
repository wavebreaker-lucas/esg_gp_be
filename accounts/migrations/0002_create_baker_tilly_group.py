from django.db import migrations
from django.contrib.auth.models import Group
from django.contrib.auth.management import create_permissions
from django.apps import apps as global_apps # Use a different name to avoid conflict with the 'apps' arg

def create_baker_tilly_group(apps, schema_editor):
    # Ensure permissions for the 'accounts' app are created first
    # We use global_apps here because the 'apps' argument in RunPython
    # provides historical models, not the AppConfig registry.
    try:
        accounts_app_config = global_apps.get_app_config('accounts')
        # Setting verbosity=0 prevents create_permissions from printing to stdout
        create_permissions(accounts_app_config, verbosity=0)
        print("Successfully triggered permission creation for 'accounts' app.")
    except Exception as e:
        print(f"Error triggering permission creation: {e}")
        # Decide if you want to proceed or raise an error if perm creation fails

    # Now get models using the migration's apps registry
    Group = apps.get_model('auth', 'Group')
    Permission = apps.get_model('auth', 'Permission')
    
    # Create or get Baker Tilly Admin group
    bt_group, created = Group.objects.get_or_create(name='Baker Tilly Admin')
    
    # Define models we want permissions for
    models_to_permit = [
        'customuser', 'appuser', 'grouplayer', 'subsidiarylayer', 
        'branchlayer', 'csvtemplate', 'layerprofile'
    ]
    permissions_to_add = []

    # Query for the now-existing permissions
    for model_name in models_to_permit:
        try:
            content_type = apps.get_model('contenttypes', 'ContentType').objects.get(
                app_label='accounts',
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
                    print(f"Warning: Permission {codename} not found after creation attempt.")
        except apps.get_model('contenttypes', 'ContentType').DoesNotExist:
             print(f"Warning: ContentType for accounts.{model_name} not found.")

    # Add permissions to group
    if permissions_to_add:
        bt_group.permissions.add(*permissions_to_add)
        print(f"Added {len(permissions_to_add)} permissions to Baker Tilly Admin group")
    else:
        print("Warning: Still no permissions found to add to Baker Tilly Admin group")

def remove_baker_tilly_group(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    Group.objects.filter(name='Baker Tilly Admin').delete()

class Migration(migrations.Migration):
    dependencies = [
        ('accounts', '0001_initial'),
        ('contenttypes', '__latest__'), # Dependency on contenttypes needed
        ('auth', '__latest__'), # Dependency on auth needed for Permission model
    ]

    operations = [
        migrations.RunPython(create_baker_tilly_group, remove_baker_tilly_group),
    ] 