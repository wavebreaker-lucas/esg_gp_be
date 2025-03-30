from django.db import migrations, models
from django.contrib.postgres.indexes import GinIndex


class Migration(migrations.Migration):

    dependencies = [
        ('data_management', '0020_esgmetricbatchsubmission_metricschemaregistry_and_more'),
    ]

    operations = [
        # Remove legacy fields from ESGMetric
        migrations.RemoveField(
            model_name='esgmetric',
            name='requires_time_reporting',
        ),
        migrations.RemoveField(
            model_name='esgmetric',
            name='reporting_frequency',
        ),
        
        # Remove legacy fields from ESGMetricSubmission 
        migrations.RemoveField(
            model_name='esgmetricsubmission',
            name='value',
        ),
        migrations.RemoveField(
            model_name='esgmetricsubmission',
            name='text_value',
        ),
        migrations.RemoveField(
            model_name='esgmetricsubmission',
            name='reporting_period',
        ),
        
        # Make data field required in ESGMetricSubmission
        migrations.AlterField(
            model_name='esgmetricsubmission',
            name='data',
            field=models.JSONField(help_text='All metric data in structured JSON format'),
        ),
        
        # Add PostgreSQL GIN index for JSON field
        migrations.AddIndex(
            model_name='esgmetricsubmission',
            index=GinIndex(fields=['data'], name='data_gin_idx'),
        ),
    ] 