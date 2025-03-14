from django.db import migrations
from django.contrib.auth.models import Group, Permission

def add_data_management_permissions(apps, schema_editor):
    # Get Baker Tilly Admin group
    bt_group = Group.objects.get(name='Baker Tilly Admin')
    
    # Get all permissions for data_management models
    data_management_permissions = Permission.objects.filter(
        content_type__app_label='data_management',
        content_type__model__in=[
            'esgformcategory', 'esgform', 'esgmetric',
            'template', 'templateformselection', 'templateassignment',
            'boundaryitem', 'emissionfactor', 'esgdata', 'dataeditlog'
        ]
    )
    
    # Add permissions to group
    for perm in data_management_permissions:
        bt_group.permissions.add(perm)

def remove_data_management_permissions(apps, schema_editor):
    # Get Baker Tilly Admin group
    bt_group = Group.objects.get(name='Baker Tilly Admin')
    
    # Remove data_management permissions
    data_management_permissions = Permission.objects.filter(
        content_type__app_label='data_management'
    )
    for perm in data_management_permissions:
        bt_group.permissions.remove(perm)

class Migration(migrations.Migration):
    dependencies = [
        ('accounts', '0003_create_initial_bt_admin'),
        ('data_management', '0001_initial'),  # Make sure data_management models exist
    ]

    operations = [
        migrations.RunPython(add_data_management_permissions, remove_data_management_permissions),
    ] 