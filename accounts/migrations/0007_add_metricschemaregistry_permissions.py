from django.db import migrations

def add_schema_registry_permissions(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    Permission = apps.get_model('auth', 'Permission')
    ContentType = apps.get_model('contenttypes', 'ContentType')
    
    # Get Baker Tilly Admin group
    try:
        bt_group = Group.objects.get(name='Baker Tilly Admin')
    except Group.DoesNotExist:
        # If the group doesn't exist, there's nothing to do
        return
    
    # Get content type for MetricSchemaRegistry
    try:
        schema_registry_ct = ContentType.objects.get(
            app_label='data_management',
            model='metricschemaregistry'
        )
    except ContentType.DoesNotExist:
        # If the content type doesn't exist, there's nothing to do
        return
    
    # Get all permissions for MetricSchemaRegistry
    schema_permissions = Permission.objects.filter(
        content_type=schema_registry_ct
    )
    
    # Add permissions to group
    for perm in schema_permissions:
        bt_group.permissions.add(perm)

def remove_schema_registry_permissions(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    Permission = apps.get_model('auth', 'Permission')
    ContentType = apps.get_model('contenttypes', 'ContentType')
    
    # Get Baker Tilly Admin group
    try:
        bt_group = Group.objects.get(name='Baker Tilly Admin')
    except Group.DoesNotExist:
        # If the group doesn't exist, there's nothing to do
        return
    
    # Get content type for MetricSchemaRegistry
    try:
        schema_registry_ct = ContentType.objects.get(
            app_label='data_management',
            model='metricschemaregistry'
        )
    except ContentType.DoesNotExist:
        # If the content type doesn't exist, there's nothing to do
        return
    
    # Get all permissions for MetricSchemaRegistry
    schema_permissions = Permission.objects.filter(
        content_type=schema_registry_ct
    )
    
    # Remove permissions from group
    for perm in schema_permissions:
        bt_group.permissions.remove(perm)

class Migration(migrations.Migration):
    dependencies = [
        ('accounts', '0006_layerprofile_created_by_admin'),
    ]

    operations = [
        migrations.RunPython(add_schema_registry_permissions, remove_schema_registry_permissions),
    ] 