from ..models.templates import ESGMetricEvidence
import logging

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
    
    Uses layer, reference_path, and submission_identifier to improve the matching process:
    - For submissions with identifiers: Uses the identifier for precise matching
    - For time-based metrics: Uses reference_path to match with the correct period in the JSON data
    - For all metrics: Matches primarily on layer and metric
    
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
            from ..models.templates import ESGMetric
            metric = ESGMetric.objects.get(id=metric_id)
            is_time_based = metric.requires_time_reporting
        except ESGMetric.DoesNotExist:
            logger.warning(f"Metric {metric_id} not found, assuming not time-based")
            is_time_based = False
        
        # Get standalone evidence for this metric
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
            # First, sort submissions by those with identifiers (most specific) first
            sorted_subs = sorted(subs, key=lambda s: s.submission_identifier != '', reverse=True)
            
            # Check if any evidence has a matching submission_identifier
            if hasattr(evidence, 'submission_identifier') and evidence.submission_identifier:
                identifier_matches = [s for s in sorted_subs if s.submission_identifier == evidence.submission_identifier]
                if identifier_matches:
                    # Perfect match on identifier - use this submission
                    best_match = identifier_matches[0]
                    logger.info(f"Found identifier match for evidence {evidence.id}")
                    evidence.submission = best_match
                    evidence.save()
                    attached_count += 1
                    logger.info(f"Attached evidence {evidence.id} to submission {best_match.id} (identifier match)")
                    continue
            
            # If we reach here, there was no identifier match, try reference path next
            if evidence.reference_path:
                # For time-based metrics or any evidence with supports_multiple_periods flag, use path-based matching
                if evidence.supports_multiple_periods or is_time_based:
                    # If evidence supports multiple periods, its reference_path contains the base path
                    # where periods are stored (e.g., 'periods')
                    
                    # Find matching submission by checking if reference_path exists in JSON data
                    best_match = None
                    for sub in sorted_subs:
                        # Skip submissions without data
                        if not sub.data:
                            continue
                        
                        if evidence.supports_multiple_periods:
                            # For multiple periods evidence, just check if the base path exists
                            if evidence.reference_path in sub.data:
                                if sub.layer and evidence.layer and sub.layer.id == evidence.layer.id:
                                    # Perfect match: base path exists and layer matches
                                    best_match = sub
                                    logger.info(f"Found perfect match for multi-period evidence {evidence.id}")
                                    break
                                elif not best_match:
                                    # Path match but layer doesn't match - use as fallback
                                    best_match = sub
                                    logger.info(f"Found base path match for multi-period evidence {evidence.id}")
                        else:
                            # For regular reference_path matching (specific period or value)
                            # Check if the reference path exists in the JSON data
                            parts = evidence.reference_path.split('.')
                            current = sub.data
                            path_exists = True
                            
                            for part in parts:
                                if isinstance(current, dict) and part in current:
                                    current = current[part]
                                else:
                                    path_exists = False
                                    break
                            
                            if path_exists:
                                # Found a submission with matching reference path in data
                                if sub.layer and evidence.layer and sub.layer.id == evidence.layer.id:
                                    # Perfect match: reference path exists and layer matches
                                    best_match = sub
                                    logger.info(f"Found perfect match (path+layer) for evidence {evidence.id}")
                                    break
                                elif not best_match:
                                    # Path match but layer doesn't match - use as fallback
                                    best_match = sub
                                    logger.info(f"Found path match for evidence {evidence.id}")
                                    # Keep looking for better match with matching layer
                    
                    # If no matching path found, skip this evidence
                    if not best_match:
                        logger.info(f"No path match found for evidence {evidence.id}, skipping")
                        continue
                    
                    # Attach evidence to the best matching submission
                    evidence.submission = best_match
                    evidence.save()
                    attached_count += 1
                    logger.info(f"Attached evidence {evidence.id} to submission {best_match.id} (path match)")
                    continue
            
            # If we reach here, there was no identifier or path match
            # For non-time-based metrics or evidence without reference path, match primarily on layer
            best_match = None
            
            # First try to find a submission with matching layer
            for sub in sorted_subs:
                if sub.layer and evidence.layer and sub.layer.id == evidence.layer.id:
                    best_match = sub
                    logger.info(f"Found layer match for evidence {evidence.id}")
                    break
            
            # If no layer match, use first submission
            if not best_match and sorted_subs:
                best_match = sorted_subs[0]
                logger.info(f"No layer match found, using first submission for evidence {evidence.id}")
            
            # Attach evidence to submission if match was found
            if best_match:
                evidence.submission = best_match
                evidence.save()
                attached_count += 1
                logger.info(f"Attached evidence {evidence.id} to submission {best_match.id}")
    
    return attached_count 