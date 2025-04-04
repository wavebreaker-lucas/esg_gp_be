"""
Utility functions for data management views.
These are helper functions used across multiple view classes.
"""

from accounts.models import LayerProfile


def get_required_submission_count(metric, assignment):
    """
    Calculate the required number of submissions for time-based metrics.
    
    Args:
        metric: The ESGMetric instance
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
    Attach evidence files to submissions.
    This is a placeholder for the actual implementation, which should be moved here.
    
    Args:
        submissions: List of ESGMetricSubmission instances
        user: The user requesting the attachment
        
    Returns:
        int: Number of evidence items attached
    """
    from data_management.services import attach_evidence_to_submissions
    return attach_evidence_to_submissions(submissions, user) 