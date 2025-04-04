"""
Service functions for calculating aggregated metric values.
"""

import logging
from django.db.models import Sum, Avg, Count, Max, Min, F, Q, DateTimeField, ExpressionWrapper # Import aggregation functions
from django.utils import timezone
from django.db import transaction

from accounts.models import LayerProfile
from ..models.templates import (
    ESGMetricSubmission, ReportedMetricValue, ESGMetric, TemplateAssignment,
    MetricValue, MetricValueField, ReportedMetricFieldValue
)

logger = logging.getLogger(__name__)

def calculate_report_value(assignment: TemplateAssignment, input_metric: ESGMetric, reporting_period: timezone.datetime.date, layer: LayerProfile):
    """
    Calculates and saves the aggregated value(s) for a given input metric context
    into the new ReportedMetricValue and ReportedMetricFieldValue structure.

    Args:
        assignment: The TemplateAssignment instance.
        input_metric: The ESGMetric instance that defines the INPUTS.
        reporting_period: The specific date representing the reporting period.
        layer: The LayerProfile instance the value pertains to.

    Returns:
        The created or updated parent ReportedMetricValue instance, or None if no inputs exist.
    """

    # Check if this input metric requires aggregation
    if not input_metric.aggregates_inputs:
        logger.debug(f"Skipping aggregation for input metric {input_metric.id} as aggregates_inputs is False.")
        # Ensure no Aggregated Metric Record exists if aggregation is turned off
        deleted_count, _ = ReportedMetricValue.objects.filter(
            assignment=assignment,
            metric=input_metric, # Link using input metric
            reporting_period=reporting_period,
            layer=layer
        ).delete()
        if deleted_count > 0:
            logger.info(f"Deleted Aggregated Metric Record for {input_metric.name} ({reporting_period}) - {layer.company_name} as aggregates_inputs is now False.")
        return None

    # --- Find all relevant raw input submissions --- 
    source_submissions = ESGMetricSubmission.objects.filter(
        assignment=assignment,
        metric=input_metric, # Filter by the INPUT metric
        reporting_period=reporting_period,
        layer=layer
    ).order_by('submitted_at', 'pk') # Order for determining first/last/text

    source_submission_count = source_submissions.count()
    first_submission = source_submissions.first()
    last_submission = source_submissions.last()

    if source_submission_count == 0:
        # If no inputs exist, ensure no parent or child aggregate records exist.
        deleted_count, _ = ReportedMetricValue.objects.filter(
            assignment=assignment,
            metric=input_metric,
            reporting_period=reporting_period,
            layer=layer
        ).delete() # Cascading delete should handle children
        if deleted_count > 0:
            logger.info(f"Deleted Aggregated Metric Record for {input_metric.name} ({reporting_period}) - {layer.company_name} due to no source inputs.")
        return None

    # --- Get or Create Parent Aggregation Record --- 
    parent_defaults = {
        'source_submission_count': source_submission_count,
        'first_submission_at': first_submission.submitted_at if first_submission else None,
        'last_submission_at': last_submission.submitted_at if last_submission else None,
        'last_updated_at': timezone.now() # Explicitly set update time
    }

    # Use atomic transaction for updating/creating parent and children
    with transaction.atomic():
        parent_agg_record, created = ReportedMetricValue.objects.update_or_create(
            assignment=assignment,
            metric=input_metric, # Linked to the INPUT metric
            reporting_period=reporting_period,
            layer=layer,
            defaults=parent_defaults
        )
        action_parent = "Created" if created else "Updated"
        logger.debug(f"{action_parent} parent Aggregated Metric Record for {input_metric.name} ({reporting_period}) - {layer.company_name} (ID: {parent_agg_record.id})")

        # --- Handle Aggregation Based on Metric Type --- 
        if not input_metric.is_multi_value:
            # --- Single-Value Metric Aggregation --- 
            # Decide aggregation method (SUM for numeric, LAST for text default)
            # TODO: Make aggregation method configurable on ESGMetric?
            
            numeric_units = ['kWh', 'MWh', 'm3', 'tonnes', 'tCO2e', 'percentage', 'count', 'person', 'hours', 'days']
            aggregated_numeric = None
            aggregated_text = None
            agg_method = 'SUM' # Default

            if input_metric.unit_type in numeric_units:
                # Perform SUM aggregation on source_submissions.value
                result = source_submissions.aggregate(total=Sum('value'))
                aggregated_numeric = result.get('total')
                agg_method = 'SUM'
            else: # Assume text or custom
                # Take the text_value from the last submission
                if last_submission:
                    aggregated_text = last_submission.text_value
                agg_method = 'LAST'

            # Update the parent record directly (Option 2a)
            parent_agg_record.aggregated_numeric_value = aggregated_numeric
            parent_agg_record.aggregated_text_value = aggregated_text
            parent_agg_record.save(update_fields=['aggregated_numeric_value', 'aggregated_text_value', 'last_updated_at'])
            logger.debug(f"Stored single-value result ({agg_method}) on parent record {parent_agg_record.id}.")

            # Clean up any orphaned child field values if metric was switched from multi-value
            parent_agg_record.aggregated_fields.all().delete()

        else:
            # --- Multi-Value Metric Aggregation --- 
            # Clear single-value fields on parent if metric was switched
            parent_agg_record.aggregated_numeric_value = None
            parent_agg_record.aggregated_text_value = None
            parent_agg_record.save(update_fields=['aggregated_numeric_value', 'aggregated_text_value'])

            # Get the field definitions for this multi-value metric
            value_fields = input_metric.value_fields.all()
            if not value_fields.exists():
                logger.warning(f"Multi-value metric {input_metric.id} has no MetricValueFields defined. Cannot aggregate.")
                # Clean up existing children? 
                parent_agg_record.aggregated_fields.all().delete()
                return parent_agg_record # Return parent, but nothing was aggregated

            processed_field_pks = set()
            # Iterate through each defined field and aggregate its values
            for field_def in value_fields:
                processed_field_pks.add(field_def.pk)
                # Fetch the corresponding MetricValue records from the source submissions
                field_inputs = MetricValue.objects.filter(
                    submission__in=source_submissions,
                    field=field_def
                )
                field_submission_count = field_inputs.count()
                
                # Decide aggregation method for this field
                # TODO: Make method configurable per MetricValueField?
                aggregated_numeric = None
                aggregated_text = None
                agg_method = 'SUM' # Default
                
                if field_def.display_type == 'NUMBER':
                    result = field_inputs.aggregate(total=Sum('numeric_value'))
                    aggregated_numeric = result.get('total')
                    agg_method = 'SUM'
                else: # Assume TEXT or SELECT
                    # Find the MetricValue from the last overall submission that has a value for this field
                    last_field_input = field_inputs.filter(submission=last_submission).first()
                    if last_field_input:
                         aggregated_text = last_field_input.text_value
                    agg_method = 'LAST' # Default for text/select

                # Update or Create the ReportedMetricFieldValue record
                field_defaults = {
                    'aggregated_numeric_value': aggregated_numeric,
                    'aggregated_text_value': aggregated_text,
                    'aggregation_method': agg_method,
                    'source_submission_count': field_submission_count,
                    'last_updated_at': timezone.now()
                }
                
                field_agg_record, field_created = ReportedMetricFieldValue.objects.update_or_create(
                    reported_value=parent_agg_record,
                    field=field_def,
                    defaults=field_defaults
                )
                action_field = "Created" if field_created else "Updated"
                logger.debug(f"{action_field} ReportedMetricFieldValue for field {field_def.field_key} on parent {parent_agg_record.id}.")
            
            # Clean up child records for fields that no longer exist on the metric
            parent_agg_record.aggregated_fields.exclude(field__pk__in=processed_field_pks).delete()

    # Return the parent aggregation record
    return parent_agg_record 