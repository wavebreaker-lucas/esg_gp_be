from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('data_management', '0022_update_uniqueness_constraints'),
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
        
        # Add PostgreSQL jsonb index
        migrations.AddIndex(
            model_name='esgmetricsubmission',
            index=models.Index(fields=['data'], name='data_gin_idx', opclasses=['jsonb_path_ops']),
        ),
    ] 