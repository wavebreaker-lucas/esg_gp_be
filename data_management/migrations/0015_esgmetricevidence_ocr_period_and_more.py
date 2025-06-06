# Generated by Django 5.1.7 on 2025-03-24 18:20

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('data_management', '0014_templateassignment_reporting_year'),
    ]

    operations = [
        migrations.AddField(
            model_name='esgmetricevidence',
            name='ocr_period',
            field=models.DateField(blank=True, help_text='Reporting period extracted by OCR', null=True),
        ),
        migrations.AlterField(
            model_name='esgmetricevidence',
            name='period',
            field=models.DateField(blank=True, help_text='User-selected reporting period', null=True),
        ),
    ]
