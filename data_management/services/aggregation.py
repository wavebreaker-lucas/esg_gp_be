"""
Service functions for calculating aggregated metric values.
"""

import logging
from django.db.models import Sum, Avg, Count, Max, Min
from django.utils import timezone

from ..models import ESGMetricSubmission, ReportedMetricValue, ESGMetric, TemplateAssignment, LayerProfile

logger = logging.getLogger(__name__)

def calculate_report_value(assignment: TemplateAssignment, metric: ESGMetric, reporting_period: timezone.datetime.date, layer: LayerProfile):
    """
    Calculates and saves the ReportedMetricValue for a given context
    based on its source ESGMetricSubmission inputs.

    Args:
        assignment: The TemplateAssignment instance.
        metric: The ESGMetric instance.
        reporting_period: The specific date representing the reporting period.
        layer: The LayerProfile instance the value pertains to.

    Returns:
        The created or updated ReportedMetricValue instance, or None if no inputs exist.
    """

    # Ensure this metric is actually configured for aggregation
    if not metric.aggregates_inputs:
        logger.debug(f"Skipping aggregation for metric {metric.id} as aggregates_inputs is False.")
        # Optional: Clean up any potentially orphaned ReportedMetricValue if metric config changed?
        # ReportedMetricValue.objects.filter(...).delete()
        return None

    # Find all relevant raw input submissions
    source_inputs = ESGMetricSubmission.objects.filter(
        assignment=assignment,
        metric=metric,
        reporting_period=reporting_period,
        layer=layer
    )

    if not source_inputs.exists():
        # If no inputs exist, ensure no final reported value exists either.
        deleted_count, _ = ReportedMetricValue.objects.filter(
            assignment=assignment,
            metric=metric,
            reporting_period=reporting_period,
            layer=layer
        ).delete()
        if deleted_count > 0:
            logger.info(f"Deleted ReportedMetricValue for {metric.name} ({reporting_period}) - {layer.company_name} due to no source inputs.")
        return None

    # --- Aggregation Logic --- TODO: Make this more configurable
    calculated_value = None
    calculated_text_value = None

    # Define which unit types are typically numeric for aggregation
    numeric_units = ['kWh', 'MWh', 'm3', 'tonnes', 'tCO2e', 'percentage', 'count', 'person', 'hours', 'days']

    if metric.unit_type in numeric_units:
        # SUM numeric values by default for now
        aggregation_result = source_inputs.aggregate(total_value=Sum('value'))
        calculated_value = aggregation_result.get('total_value')
        logger.debug(f"Aggregated numeric value for {metric.name} ({reporting_period}) - {layer.company_name}: {calculated_value}")
    else:
        # For non-numeric, maybe take the value from the latest input?
        latest_input = source_inputs.order_by('-submitted_at', '-pk').first() # Use pk for tie-breaking
        if latest_input:
            calculated_text_value = latest_input.text_value
            logger.debug(f"Using latest text value for {metric.name} ({reporting_period}) - {layer.company_name}: {calculated_text_value}")

    # --- Save Result --- Decide on verification reset policy
    # Policy: Reset verification if the value changes significantly? For now, just update/create.
    defaults = {
        'value': calculated_value,
        'text_value': calculated_text_value,
        'last_updated_at': timezone.now()
        # Potential future: Store number of inputs aggregated, method used, etc.
        # 'metadata': {'source_input_count': source_inputs.count(), 'method': 'SUM'}
    }

    try:
        report_value_obj, created = ReportedMetricValue.objects.update_or_create(
            assignment=assignment,
            metric=metric,
            reporting_period=reporting_period,
            layer=layer,
            defaults=defaults
        )

        action = "Created" if created else "Updated"
        logger.info(f"{action} ReportedMetricValue for {metric.name} ({reporting_period}) - {layer.company_name} (ID: {report_value_obj.id})")

        # --- Link Inputs --- Update the FK on all source inputs
        updated_count = source_inputs.update(reported_value=report_value_obj)
        logger.debug(f"Linked {updated_count} input submissions to ReportedMetricValue ID {report_value_obj.id}")

        return report_value_obj

    except Exception as e:
        logger.error(f"Failed to update or create ReportedMetricValue for {metric.name} ({reporting_period}) - {layer.company_name}: {e}", exc_info=True)
        # Should we attempt to unlink inputs if save fails? Difficult transactionally.
        return None 