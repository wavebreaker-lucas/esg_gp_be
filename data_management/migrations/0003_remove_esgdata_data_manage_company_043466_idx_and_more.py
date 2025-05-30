# Generated by Django 5.1.7 on 2025-03-16 09:12

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0004_add_data_management_permissions'),
        ('data_management', '0002_alter_templateassignment_assigned_to'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.RemoveIndex(
            model_name='esgdata',
            name='data_manage_company_043466_idx',
        ),
        migrations.RemoveIndex(
            model_name='templateassignment',
            name='data_manage_templat_1dca89_idx',
        ),
        migrations.RenameField(
            model_name='esgdata',
            old_name='company',
            new_name='layer',
        ),
        migrations.RenameField(
            model_name='templateassignment',
            old_name='company',
            new_name='layer',
        ),
        migrations.AddIndex(
            model_name='esgdata',
            index=models.Index(fields=['layer', 'date_recorded'], name='data_manage_layer_i_8cc433_idx'),
        ),
        migrations.AddIndex(
            model_name='templateassignment',
            index=models.Index(fields=['template', 'layer'], name='data_manage_templat_22d8d7_idx'),
        ),
    ]
