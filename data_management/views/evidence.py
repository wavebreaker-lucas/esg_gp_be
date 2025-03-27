"""
Views for managing ESG metric evidence.
"""

from rest_framework import views
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from accounts.models import LayerProfile
from ..models.templates import ESGMetricSubmission, ESGMetricEvidence
from ..serializers.templates import ESGMetricEvidenceSerializer
from ..serializers.esg import ESGMetricSubmissionSerializer


class BatchEvidenceView(views.APIView):
    """
    API view for fetching evidence and submission data for multiple submissions at once.
    This is an optimization for the admin interface to reduce the number of API calls.
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """
        Get evidence files and submission data for multiple submissions at once.
        
        Query parameters:
        - submission_ids: Comma-separated list of submission IDs
        
        Returns:
        A dictionary mapping submission IDs to their submission data and evidence files
        """
        submission_ids_param = request.query_params.get('submission_ids', '')
        submission_ids = [id.strip() for id in submission_ids_param.split(',') if id.strip().isdigit()]
        
        if not submission_ids:
            return Response({"error": "No valid submission IDs provided"}, status=400)
        
        # Get all submissions and evidence items for these IDs
        submissions = ESGMetricSubmission.objects.filter(id__in=submission_ids).select_related(
            'metric', 'assignment', 'submitted_by'
        )
        evidence_items = ESGMetricEvidence.objects.filter(submission_id__in=submission_ids)
        
        # Check permissions
        user = request.user
        if not (user.is_staff or user.is_superuser or user.is_baker_tilly_admin):
            # Regular users can only see evidence for submissions they have access to
            user_layers = LayerProfile.objects.filter(app_users__user=user)
            accessible_submissions = submissions.filter(
                assignment__layer__in=user_layers
            ).values_list('id', flat=True)
            
            submissions = submissions.filter(id__in=accessible_submissions)
            evidence_items = evidence_items.filter(submission_id__in=accessible_submissions)
        
        # Group evidence by submission ID
        evidence_by_submission = {}
        evidence_serializer = ESGMetricEvidenceSerializer
        
        for evidence in evidence_items:
            submission_id = str(evidence.submission_id)
            if submission_id not in evidence_by_submission:
                evidence_by_submission[submission_id] = []
            
            evidence_by_submission[submission_id].append(evidence_serializer(evidence).data)
        
        # Create response with submission data and evidence
        response_data = {}
        submission_serializer = ESGMetricSubmissionSerializer
        
        for submission in submissions:
            submission_id = str(submission.id)
            submission_data = submission_serializer(submission).data
            submission_data['evidence'] = evidence_by_submission.get(submission_id, [])
            response_data[submission_id] = submission_data
        
        return Response(response_data) 