# Generated by Django 5.1.7 on 2025-03-30 12:31

from django.conf import settings
from django.db import migrations, models
from django.contrib.postgres.indexes import GinIndex


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0006_layerprofile_created_by_admin'),
        ('data_management', '0021_remove_legacy_fields'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.RemoveIndex(
            model_name='esgmetricsubmission',
            name='data_gin_idx',
        ),
        migrations.RemoveField(
            model_name='esgmetric',
            name='custom_unit',
        ),
        migrations.RemoveField(
            model_name='esgmetric',
            name='unit_type',
        ),
        migrations.AddField(
            model_name='esgmetric',
            name='primary_path',
            field=models.CharField(blank=True, help_text="Path to the primary value in the JSON data (e.g., 'electricity.value' or '_metadata.primary_measurement')", max_length=255, null=True),
        ),
        migrations.AddIndex(
            model_name='esgmetricsubmission',
            index=GinIndex(fields=['data'], name='data_gin_idx', opclasses=['jsonb_path_ops']),
        ),
    ]
