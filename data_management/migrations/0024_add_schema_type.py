"""
Migration for schema type field to support explicit calculation handlers.
"""
from django.db import migrations, models

def populate_schema_types(apps, schema_editor):
    """Populate schema_type field based on schema_registry data."""
    ESGMetric = apps.get_model('data_management', 'ESGMetric')
    MetricSchemaRegistry = apps.get_model('data_management', 'MetricSchemaRegistry')
    
    # Build a lookup dict of schema_registry_id -> name
    schema_registry_names = {}
    for registry in MetricSchemaRegistry.objects.all():
        schema_registry_names[registry.id] = registry.name
    
    # Update all metrics that have a schema_registry
    for metric in ESGMetric.objects.filter(schema_registry__isnull=False):
        if metric.schema_registry_id in schema_registry_names:
            metric.schema_type = schema_registry_names[metric.schema_registry_id]
            metric.save()


class Migration(migrations.Migration):

    dependencies = [
        ('data_management', '0023_add_time_reporting'),
    ]

    operations = [
        migrations.AddField(
            model_name='ESGMetric',
            name='schema_type',
            field=models.CharField(max_length=50, null=True, blank=True, 
                                help_text="Direct reference to schema type (e.g., 'electricity_hk', 'electricity_prc')"),
        ),
        migrations.RunPython(populate_schema_types, migrations.RunPython.noop),
    ] 