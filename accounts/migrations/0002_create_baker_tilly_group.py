from django.db import migrations
from django.contrib.auth.models import Group, Permission

def create_baker_tilly_group(apps, schema_editor):
    # Create Baker Tilly Admin group
    bt_group, created = Group.objects.get_or_create(name='Baker Tilly Admin')
    
    # Get all permissions for our custom models
    model_permissions = Permission.objects.filter(
        content_type__app_label='accounts',
        content_type__model__in=['customuser', 'appuser', 'grouplayer', 'subsidiarylayer', 'branchlayer', 'csvtemplate']
    )
    
    # Add permissions to group
    for perm in model_permissions:
        bt_group.permissions.add(perm)

def remove_baker_tilly_group(apps, schema_editor):
    # Remove the group if migration is reversed
    Group.objects.filter(name='Baker Tilly Admin').delete()

class Migration(migrations.Migration):
    dependencies = [
        ('accounts', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(create_baker_tilly_group, remove_baker_tilly_group),
    ] 