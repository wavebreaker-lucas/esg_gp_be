from ..models.templates import ESGMetricEvidence
import logging
from datetime import datetime

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
    
    # Group submissions by metric
    submissions_by_metric = {}
    for submission in submissions:
        metric_id = submission.metric.id
        if metric_id not in submissions_by_metric:
            submissions_by_metric[metric_id] = []
        submissions_by_metric[metric_id].append(submission)
    
    # Find all standalone evidence files for these metrics
    for metric_id, subs in submissions_by_metric.items():
        logger.info(f"Processing submissions for metric {metric_id}")
        logger.info(f"Number of submissions: {len(subs)}")
        
        # Get standalone evidence for this metric using the explicit field
        evidence_files = ESGMetricEvidence.objects.filter(
            submission__isnull=True,
            uploaded_by=user,
            intended_metric__id=metric_id
        )
        
        logger.info(f"Found {evidence_files.count()} standalone evidence files")
        
        for evidence in evidence_files:
            # Find the best submission to attach to based on reporting period
            best_submission = None
            
            # Try to match with user-selected period first, then OCR period
            evidence_period = evidence.period or evidence.ocr_period
            
            if evidence_period:
                logger.info(f"Evidence period: {evidence_period} (type: {type(evidence_period)})")
                for sub in subs:
                    # Convert submission period to date if it's a string
                    sub_period = sub.reporting_period
                    if isinstance(sub_period, str):
                        try:
                            sub_period = datetime.strptime(sub_period, '%Y-%m-%d').date()
                        except ValueError:
                            logger.warning(f"Could not parse submission period {sub_period}")
                            continue
                    
                    logger.info(f"Submission period: {sub_period} (type: {type(sub_period)})")
                    if sub_period == evidence_period:
                        best_submission = sub
                        logger.info(f"Found matching submission for period {evidence_period}")
                        break
            
            # If no period match or no period, use the first submission
            if not best_submission and subs:
                best_submission = subs[0]
                logger.info(f"No period match found, using first submission with period {best_submission.reporting_period}")
            
            # Attach evidence to submission if found
            if best_submission:
                evidence.submission = best_submission
                evidence.save()
                attached_count += 1
                logger.info(f"Attached evidence to submission {best_submission.id} with period {best_submission.reporting_period}")
                
                # We intentionally do NOT apply OCR data automatically
                # Users need to explicitly choose to use OCR data by calling attach_to_submission
                # with apply_ocr_data=true
    
    return attached_count 