from ..models.templates import ESGMetricEvidence
import logging
from datetime import datetime
# Import the new polymorphic metric models
from ..models.polymorphic_metrics import (
    BaseESGMetric, TimeSeriesMetric, MaterialTrackingMatrixMetric,
    MultiFieldTimeSeriesMetric
)

# Configure logging to show in console
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def find_relevant_evidence(submission, user=None):
    """
    Find evidence files relevant to a specific submission based on metadata matching.
    
    Args:
        submission: An ESGMetricSubmission object
        user: Optional user to filter by uploaded_by (if None, returns all users' evidence)
        
    Returns:
        QuerySet of ESGMetricEvidence objects
    """
    # Base query on metadata matching
    evidence_query = ESGMetricEvidence.objects.filter(
        intended_metric=submission.metric,
        layer=submission.layer
    )
    
    # If submission has a source_identifier, filter by that too
    if submission.source_identifier:
        evidence_query = evidence_query.filter(source_identifier=submission.source_identifier)
        
    # For time-based metrics, filter by period if available
    if submission.reporting_period:
        evidence_query = evidence_query.filter(period=submission.reporting_period)
        
    # If user is provided, filter by that user
    if user:
        evidence_query = evidence_query.filter(uploaded_by=user)
    
    # Get specific metric instance to check if it's time-based
    try:
        specific_metric = submission.metric.get_real_instance()
        
        # Determine if time-based by checking the type
        is_time_based = isinstance(specific_metric, (
            TimeSeriesMetric,
            MaterialTrackingMatrixMetric,
            MultiFieldTimeSeriesMetric
        ))
        
        # For time-based metrics, we could expand the logic to find evidence 
        # for any period within the submission's time range (if needed)
        
    except (BaseESGMetric.DoesNotExist, AttributeError):
        # If we can't determine the type, just continue with the basic matching
        pass
    
    return evidence_query.select_related('layer', 'intended_metric') 