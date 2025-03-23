from ..models.templates import ESGMetricEvidence

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
        metric_id = str(submission.metric.id)
        if metric_id not in submissions_by_metric:
            submissions_by_metric[metric_id] = []
        submissions_by_metric[metric_id].append(submission)
    
    # Find all standalone evidence files for these metrics
    for metric_id, subs in submissions_by_metric.items():
        # Get standalone evidence for this metric
        evidence_files = ESGMetricEvidence.objects.filter(
            submission__isnull=True,
            uploaded_by=user,
            ocr_data__icontains=f'"intended_metric_id": "{metric_id}"'
        )
        
        for evidence in evidence_files:
            # Find the best submission to attach to based on reporting period
            best_submission = None
            
            # If evidence has a period, try to match it
            if evidence.period and evidence.period is not None:
                for sub in subs:
                    if sub.reporting_period == evidence.period:
                        best_submission = sub
                        break
            
            # If no period match or no period, use the first submission
            if not best_submission and subs:
                best_submission = subs[0]
            
            # Attach evidence to submission if found
            if best_submission:
                evidence.submission = best_submission
                evidence.save()
                attached_count += 1
                
                # We intentionally do NOT apply OCR data automatically
                # Users need to explicitly choose to use OCR data by calling attach_to_submission
                # with apply_ocr_data=true
    
    return attached_count 