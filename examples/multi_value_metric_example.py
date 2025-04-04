"""
Example showing how to use multi-value metrics in the ESG platform.

This demonstrates creating a product recall metric with multiple values
and submitting data for it.
"""
from datetime import date
from django.utils import timezone
from data_management.models import (
    ESGForm, ESGMetric, MetricValueField, MetricValue,
    TemplateAssignment, ESGMetricSubmission
)

# Example 1: Creating a product recall metric
def create_product_recall_metric(form):
    """Create a product recall metric with multiple values"""
    # Create the base metric
    metric = ESGMetric.objects.create(
        form=form,
        name="Product Recall Tracking",
        description="Track products sold vs products recalled for safety reasons",
        unit_type="count",
        requires_evidence=True,
        requires_time_reporting=True,
        reporting_frequency="monthly",
        is_multi_value=True  # Set this to True for multi-value metrics
    )
    
    # Add the value fields
    MetricValueField.objects.create(
        metric=metric,
        field_key="products_sold",
        display_name="Total No. of Products sold or shipped",
        description="Total number of products sold in the reporting period",
        column_header="A",
        order=1
    )
    
    MetricValueField.objects.create(
        metric=metric,
        field_key="products_recalled",
        display_name="Products recalled for safety reasons",
        description="Number of products recalled due to safety or health concerns",
        column_header="B",
        order=2
    )
    
    return metric

# Example 2: Creating a diversity metric
def create_diversity_metric(form):
    """Create an employee diversity metric with multiple values"""
    metric = ESGMetric.objects.create(
        form=form,
        name="Employee Diversity",
        description="Breakdown of employees by gender identity",
        unit_type="person",
        requires_evidence=False,
        is_multi_value=True
    )
    
    # Add fields for different gender categories
    MetricValueField.objects.create(
        metric=metric,
        field_key="male",
        display_name="Male Employees",
        description="Number of employees who identify as male",
        order=1
    )
    
    MetricValueField.objects.create(
        metric=metric,
        field_key="female",
        display_name="Female Employees",
        description="Number of employees who identify as female",
        order=2
    )
    
    MetricValueField.objects.create(
        metric=metric,
        field_key="non_binary",
        display_name="Non-binary Employees",
        description="Number of employees who identify as non-binary",
        order=3
    )
    
    MetricValueField.objects.create(
        metric=metric,
        field_key="not_disclosed",
        display_name="Not Disclosed",
        description="Number of employees who have not disclosed gender identity",
        order=4
    )
    
    return metric

# Example 3: Creating an energy consumption metric
def create_energy_consumption_metric(form):
    """Create an energy consumption metric with multiple energy sources"""
    metric = ESGMetric.objects.create(
        form=form,
        name="Energy Consumption Breakdown",
        description="Energy consumption by source",
        unit_type="MWh",
        requires_evidence=True,
        requires_time_reporting=True,
        reporting_frequency="quarterly",
        is_multi_value=True
    )
    
    # Add fields for different energy sources
    MetricValueField.objects.create(
        metric=metric,
        field_key="electricity",
        display_name="Electricity",
        description="Electricity consumption in MWh",
        order=1
    )
    
    MetricValueField.objects.create(
        metric=metric,
        field_key="natural_gas",
        display_name="Natural Gas",
        description="Natural gas consumption converted to MWh",
        order=2
    )
    
    MetricValueField.objects.create(
        metric=metric,
        field_key="diesel",
        display_name="Diesel Fuel",
        description="Diesel fuel consumption converted to MWh",
        order=3
    )
    
    MetricValueField.objects.create(
        metric=metric,
        field_key="renewable",
        display_name="Renewable Energy",
        description="Renewable energy consumption in MWh",
        order=4
    )
    
    return metric

# Example 4: Submitting data for multi-value metrics
def submit_product_recall_data(assignment, metric, reporting_period, products_sold, products_recalled, user):
    """Submit data for a product recall metric"""
    # Create the base submission
    submission = ESGMetricSubmission.objects.create(
        assignment=assignment,
        metric=metric,
        reporting_period=reporting_period,
        submitted_by=user,
        submitted_at=timezone.now()
    )
    
    # Add the values using the helper method
    submission.add_value("products_sold", products_sold)
    submission.add_value("products_recalled", products_recalled)
    
    return submission

# Example 5: Using the batch submit API
def prepare_batch_submission_data(assignment_id, multi_value_metrics):
    """
    Prepare data for batch submission API
    
    Example usage:
    
    data = prepare_batch_submission_data(
        assignment_id=123,
        multi_value_metrics=[
            {
                'metric_id': 456,
                'reporting_period': '2024-01-31',
                'multi_values': {
                    'products_sold': 15000,
                    'products_recalled': 120
                }
            },
            {
                'metric_id': 789,
                'multi_values': {
                    'male': 356,
                    'female': 289,
                    'non_binary': 12,
                    'not_disclosed': 8
                }
            }
        ]
    )
    """
    return {
        'assignment_id': assignment_id,
        'submissions': multi_value_metrics
    }

# Example 6: Retrieving and aggregating multi-value data
def generate_product_recall_report(assignment, metric):
    """Generate a report showing product recall rates over time"""
    submissions = ESGMetricSubmission.objects.filter(
        assignment=assignment,
        metric=metric
    ).order_by('reporting_period')
    
    print(f"Product Recall Report for {assignment.layer.company_name}")
    print(f"Reporting Period: {assignment.reporting_period_start} to {assignment.reporting_period_end}")
    print("\nMonth\tProducts Sold\tProducts Recalled\tRecall Rate")
    print("-" * 70)
    
    # Prefetch all multi_values to minimize database queries
    submissions = submissions.prefetch_related('multi_values__field')
    
    for sub in submissions:
        # Create a dictionary mapping field_key to value for easy access
        values_dict = {}
        for mv in sub.multi_values.all():
            field_key = mv.field.field_key
            value = mv.numeric_value if mv.numeric_value is not None else mv.text_value
            values_dict[field_key] = value
        
        # Get values using the dictionary
        products_sold = values_dict.get('products_sold', 0)
        products_recalled = values_dict.get('products_recalled', 0)
        
        # Calculate the recall rate
        recall_rate = f"{(products_recalled / products_sold * 100):.2f}%" if products_sold else "N/A"
        
        # Format and print the row
        month = sub.reporting_period.strftime("%b %Y")
        print(f"{month}\t{products_sold:,}\t\t{products_recalled:,}\t\t{recall_rate}")

# Example 7: Converting a regular metric to a multi-value metric
def convert_to_multi_value(metric):
    """Convert a regular single-value metric to a multi-value metric"""
    if metric.is_multi_value:
        return metric
        
    # Set the flag to convert this to a multi-value metric
    metric.is_multi_value = True
    metric.save()
    
    # Create a "primary" field for the original value
    MetricValueField.objects.create(
        metric=metric,
        field_key="primary",
        display_name=f"Primary {metric.name} Value",
        description=f"Primary value for {metric.name}",
        order=1
    )
    
    # Migrate existing submissions to use the new field
    migrate_submissions_to_multi_value(metric)
    
    return metric

def migrate_submissions_to_multi_value(metric):
    """Migrate existing submissions for a converted metric"""
    # Get all submissions for this metric
    submissions = ESGMetricSubmission.objects.filter(metric=metric)
    
    # Get the primary field
    primary_field = metric.value_fields.get(field_key="primary")
    
    # For each submission, create a MetricValue for the original value
    for submission in submissions:
        if submission.value is not None:
            MetricValue.objects.create(
                submission=submission,
                field=primary_field,
                numeric_value=submission.value
            )
        elif submission.text_value:
            MetricValue.objects.create(
                submission=submission,
                field=primary_field,
                text_value=submission.text_value
            ) 