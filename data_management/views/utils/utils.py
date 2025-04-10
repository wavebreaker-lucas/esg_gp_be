"""
Utility functions for data management views.
These are helper functions used across multiple view classes.
"""

from accounts.models import LayerProfile
from ...models.polymorphic_metrics import BaseESGMetric


def get_required_submission_count(metric, assignment):
    """
    Calculate the required number of submissions for time-based metrics.
    
    Args:
        metric: The BaseESGMetric instance
        assignment: The TemplateAssignment instance
        
    Returns:
        int: The number of required submissions
    """
    if not metric.requires_time_reporting or not metric.reporting_frequency:
        return 1
        
    # For simplicity, use fixed counts based on reporting frequency
    if metric.reporting_frequency == 'monthly':
        return 12
    elif metric.reporting_frequency == 'quarterly':
        return 4
    elif metric.reporting_frequency == 'annual':
        return 1
    
    return 1  # Default fallback


def attach_evidence_to_submissions(submissions, user):
    """
    Compatibility wrapper for find_relevant_evidence.
    This preserves the API for code that calls this function.
    
    Args:
        submissions: List of ESGMetricSubmission objects
        user: The user who is finding evidence
        
    Returns:
        int: Placeholder count (0) - no attachment happens anymore
    """
    from data_management.services import find_relevant_evidence
    
    # This function no longer attaches evidence, but returns a constant
    # to maintain backwards compatibility
    # Code should be updated to use find_relevant_evidence instead
    
    return 0 