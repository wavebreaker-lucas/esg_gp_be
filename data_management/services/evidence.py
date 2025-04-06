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

def attach_evidence_to_submissions(submissions, user):
    """
    Automatically attach relevant standalone evidence to the given submissions.
    This is called during form completion and batch submission to link any pending evidence files.
    Note: This only attaches the evidence files, it does NOT apply OCR data automatically.
    
    Uses layer and period to improve the matching process:
    - For time-based metrics: Matches on both layer AND period
    - For non-time-based metrics: Matches primarily on layer
    
    Args:
        submissions: List of ESGMetricSubmission objects
        user: The user who is attaching the evidence
        
    Returns:
        int: Number of evidence files attached
    """
    if not submissions:
        return 0
    
    # Track number of attached files
    attached_count = 0
    
    # Group submissions by metric and layer
    submissions_by_metric_and_layer = {}
    for submission in submissions:
        metric_id = submission.metric.id
        layer_id = submission.layer.id if submission.layer else None
        
        key = (metric_id, layer_id)
        if key not in submissions_by_metric_and_layer:
            submissions_by_metric_and_layer[key] = []
        submissions_by_metric_and_layer[key].append(submission)
    
    # Find all standalone evidence files for these metrics
    for (metric_id, layer_id), subs in submissions_by_metric_and_layer.items():
        logger.info(f"Processing submissions for metric {metric_id}, layer {layer_id}")
        logger.info(f"Number of submissions: {len(subs)}")
        
        # Get the metric to check if it's time-based
        try:
            # Use the new BaseESGMetric model
            base_metric = BaseESGMetric.objects.get(id=metric_id)
            # Get the specific instance to check its type
            specific_metric = base_metric.get_real_instance()
            # Determine if time-based by checking the type
            is_time_based = isinstance(specific_metric, (
                TimeSeriesMetric,
                MaterialTrackingMatrixMetric,
                MultiFieldTimeSeriesMetric
            ))
            logger.info(f"Metric {metric_id} is type {type(specific_metric).__name__}. Is time-based: {is_time_based}")
        except BaseESGMetric.DoesNotExist: # Use the correct exception
            logger.warning(f"BaseESGMetric {metric_id} not found, assuming not time-based for evidence matching.")
            is_time_based = False
        except AttributeError: # Handle cases where get_real_instance might fail (shouldn't normally)
             logger.error(f"Could not determine specific type for BaseESGMetric {metric_id}. Assuming not time-based.")
             is_time_based = False
        
        # Get standalone evidence for this metric (intended_metric points to BaseESGMetric, so this is OK)
        evidence_query = ESGMetricEvidence.objects.filter(
            submission__isnull=True,
            uploaded_by=user,
            intended_metric__id=metric_id
        )
        
        # If the submission has a layer, prefer evidence from the same layer
        if layer_id:
            # First try exact layer match
            layer_evidence = evidence_query.filter(layer_id=layer_id)
            
            if layer_evidence.exists():
                evidence_files = layer_evidence
                logger.info(f"Found {evidence_files.count()} evidence files with exact layer match")
            else:
                # Fall back to any evidence for this metric
                evidence_files = evidence_query
                logger.info(f"No evidence with layer match, using all {evidence_files.count()} evidence files")
        else:
            # If submission doesn't have a layer, use any evidence
            evidence_files = evidence_query
            logger.info(f"Submission has no layer, using all {evidence_files.count()} evidence files")
        
        # Process each evidence file
        for evidence in evidence_files:
            if is_time_based:
                # For time-based metrics, match on both layer and period
                evidence_period = evidence.period or evidence.ocr_period
                
                if not evidence_period:
                    # Skip evidence without a period for time-based metrics
                    logger.info(f"Evidence {evidence.id} has no period, skipping for time-based metric")
                    continue
                
                # Find matching submission by period and layer
                best_match = None
                for sub in subs:
                    # Convert submission period to date if it's a string
                    sub_period = sub.reporting_period
                    if isinstance(sub_period, str):
                        try:
                            sub_period = datetime.strptime(sub_period, '%Y-%m-%d').date()
                        except ValueError:
                            logger.warning(f"Could not parse submission period {sub_period}")
                            continue
                    
                    # Perfect match: same period and layer
                    if sub_period == evidence_period and sub.layer and evidence.layer and sub.layer.id == evidence.layer.id:
                        best_match = sub
                        logger.info(f"Found perfect match (period+layer) for evidence {evidence.id}")
                        break
                    # Period match only
                    elif sub_period == evidence_period:
                        best_match = sub
                        logger.info(f"Found period match for evidence {evidence.id}")
                        # Keep looking for better match with matching layer
                
                # If no period match found, skip this evidence for time-based metrics
                if not best_match:
                    logger.info(f"No period match found for evidence {evidence.id}, skipping")
                    continue
            else:
                # For non-time-based metrics, match primarily on layer
                best_match = None
                
                # First try to find a submission with matching layer
                for sub in subs:
                    if sub.layer and evidence.layer and sub.layer.id == evidence.layer.id:
                        best_match = sub
                        logger.info(f"Found layer match for evidence {evidence.id}")
                        break
                
                # If no layer match, use first submission
                if not best_match and subs:
                    best_match = subs[0]
                    logger.info(f"No layer match found, using first submission for evidence {evidence.id}")
            
            # Attach evidence to submission if match was found
            if best_match:
                evidence.submission = best_match
                evidence.save()
                attached_count += 1
                logger.info(f"Attached evidence {evidence.id} to submission {best_match.id}")
                
                # We intentionally do NOT apply OCR data automatically
                # Users need to explicitly choose to use OCR data by calling attach_to_submission
                # with apply_ocr_data=true
    
    return attached_count 