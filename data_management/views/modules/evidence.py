from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.urls import reverse
from django.db import models

from ...models.templates import ESGMetricEvidence, ESGMetricSubmission, ESGMetric
from ...serializers.esg import ESGMetricEvidenceSerializer
from ...services.bill_analyzer import UtilityBillAnalyzer
from accounts.permissions import BakerTillyAdmin


class ESGMetricEvidenceViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing evidence files for ESG metric submissions.
    """
    serializer_class = ESGMetricEvidenceSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Base queryset
        queryset = ESGMetricEvidence.objects.all()
        
        # Filter by user's permissions
        user = self.request.user
        
        # Admin users can see all evidence
        if user.is_staff or user.is_superuser or user.is_baker_tilly_admin:
            return queryset
        
        # Other users can only see their own evidence or evidence for their group's submissions
        return queryset.filter(
            models.Q(uploaded_by=user) | 
            models.Q(submission__assignment__layer__in=user.layers.all())
        )

    def create(self, request, *args, **kwargs):
        """
        Universal upload endpoint for evidence files.
        All evidence is initially created as standalone (without a submission).
        Accepts a period parameter to specify the reporting period for the evidence.
        """
        # Check for required file
        if 'file' not in request.FILES:
            return Response({'error': 'No file provided'}, status=400)
        
        file_obj = request.FILES['file']
        
        # Handle optional metric_id - use for OCR analyzer selection
        metric_id = request.data.get('metric_id')
        metric = None
        if metric_id:
            try:
                metric = ESGMetric.objects.get(id=metric_id)
            except ESGMetric.DoesNotExist:
                return Response({'error': 'Metric not found'}, status=404)
        
        # Handle optional period parameter
        period = None
        period_str = request.data.get('period')
        if period_str:
            try:
                from datetime import datetime
                period = datetime.strptime(period_str, '%Y-%m-%d').date()
            except ValueError:
                return Response({'error': 'Invalid period format. Use YYYY-MM-DD'}, status=400)
        
        # Create standalone evidence record
        evidence = ESGMetricEvidence.objects.create(
            file=file_obj,
            filename=file_obj.name,
            file_type=file_obj.content_type,
            uploaded_by=request.user,
            description=request.data.get('description', ''),
            enable_ocr_processing=request.data.get('enable_ocr_processing') == 'true',
            period=period  # Set the user-provided period
        )
        
        # Store metric_id in ocr_data for later use
        if metric_id:
            # Initialize ocr_data if needed
            if not evidence.ocr_data:
                evidence.ocr_data = {}
            
            # Ensure ocr_data is a dict
            if not isinstance(evidence.ocr_data, dict):
                evidence.ocr_data = {}
                
            # Store the metric_id
            evidence.ocr_data['intended_metric_id'] = metric_id
            evidence.save()
        
        # Prepare response
        response_data = {
            'id': evidence.id,
            'file': request.build_absolute_uri(evidence.file.url) if evidence.file else None,
            'filename': evidence.filename,
            'uploaded_at': evidence.uploaded_at,
            'is_standalone': True,
            'metric_id': metric_id,
            'period': period
        }
        
        # Add OCR processing URL if enabled
        if evidence.enable_ocr_processing:
            response_data['ocr_processing_url'] = request.build_absolute_uri(
                reverse('esgmetricevidence-process-ocr', args=[evidence.id])
            )
        
        return Response(response_data, status=201)

    @action(detail=False, methods=['get'])
    def by_submission(self, request):
        submission_id = request.query_params.get('submission_id')
        if not submission_id:
            return Response({'error': 'submission_id is required'}, status=400)
        
        try:
            submission = ESGMetricSubmission.objects.get(id=submission_id)
        except ESGMetricSubmission.DoesNotExist:
            return Response({'error': 'Submission not found'}, status=404)
        
        # Check permissions
        if not (request.user.is_staff or request.user.is_superuser or 
                request.user.is_baker_tilly_admin or 
                request.user == submission.submitted_by or
                request.user.layers.filter(id=submission.assignment.layer.id).exists()):
            return Response({'error': 'You do not have permission to view this submission'}, status=403)
        
        # Get evidence for this submission
        evidence = ESGMetricEvidence.objects.filter(submission=submission)
        serializer = self.get_serializer(evidence, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def process_ocr(self, request, pk=None):
        evidence = self.get_object()
        
        # Check if already processed
        if evidence.is_processed_by_ocr:
            return Response({'message': 'This file has already been processed with OCR',
                            'ocr_results_url': request.build_absolute_uri(
                                reverse('esgmetricevidence-ocr-results', args=[evidence.id])
                            )}, status=200)
        
        # Check if OCR is enabled
        if not evidence.enable_ocr_processing:
            return Response({'error': 'OCR processing is not enabled for this evidence'}, status=400)
        
        # Initialize bill analyzer service
        analyzer = UtilityBillAnalyzer()
        
        # Process the evidence
        success, result = analyzer.process_evidence(evidence)
        
        if not success:
            return Response({'error': result.get('error', 'Unknown error during OCR processing')}, 
                           status=400)
        
        # Return success with results URL
        return Response({
            'message': 'OCR processing successful',
            'ocr_results_url': request.build_absolute_uri(
                reverse('esgmetricevidence-ocr-results', args=[evidence.id])
            ),
            'extracted_value': evidence.extracted_value,
            'period': evidence.period
        }, status=200)

    @action(detail=True, methods=['get'])
    def ocr_results(self, request, pk=None):
        evidence = self.get_object()
        
        if not evidence.is_processed_by_ocr:
            return Response({'error': 'This file has not been processed with OCR'}, status=400)
        
        # Return OCR results
        return Response({
            'id': evidence.id,
            'filename': evidence.filename,
            'extracted_value': evidence.extracted_value,
            'period': evidence.period,
            'additional_periods': evidence.ocr_data.get('additional_periods', []) 
                                 if isinstance(evidence.ocr_data, dict) else [],
            'raw_ocr_data': evidence.ocr_data,
            'is_processed_by_ocr': evidence.is_processed_by_ocr
        })

    @action(detail=True, methods=['post'])
    def attach_to_submission(self, request, pk=None):
        """
        Attach a standalone evidence file to a submission.
        Optionally applies OCR data to the submission values.
        """
        evidence = self.get_object()
        
        # Check if already attached
        if evidence.submission is not None:
            return Response({'error': 'This evidence is already attached to a submission'}, status=400)
        
        # Get required submission_id
        submission_id = request.data.get('submission_id')
        if not submission_id:
            return Response({'error': 'submission_id is required'}, status=400)
        
        # Verify submission exists and user has access
        try:
            submission = ESGMetricSubmission.objects.get(id=submission_id)
            
            # Check permissions
            if not (request.user.is_staff or request.user.is_superuser or 
                    request.user.is_baker_tilly_admin or 
                    request.user == submission.submitted_by or
                    request.user.layers.filter(id=submission.assignment.layer.id).exists()):
                return Response({'error': 'You do not have permission to modify this submission'}, status=403)
                
        except ESGMetricSubmission.DoesNotExist:
            return Response({'error': 'Submission not found'}, status=404)
        
        # Attach evidence to submission
        evidence.submission = submission
        evidence.save()
        
        # Apply OCR data if requested and available
        apply_ocr = request.data.get('apply_ocr_data') == 'true'
        if apply_ocr and evidence.is_processed_by_ocr and evidence.extracted_value is not None:
            # Check if submission already has a value
            if submission.value == 0:
                # Warn that we're overriding a zero value, but proceed if explicitly requested
                warning = "Overriding an explicit zero value with OCR data"
            elif submission.value is not None:
                # Warn that we're overriding a non-zero value
                warning = f"Overriding existing value {submission.value} with OCR data"
            else:
                warning = None
                
            # Update submission value
            submission.value = evidence.extracted_value
            
            # Update period if available
            if evidence.period:
                submission.reporting_period = evidence.period
                
            submission.save()
            
            return Response({
                'message': 'Evidence attached to submission and OCR data applied',
                'submission_id': submission.id,
                'value_updated': True,
                'new_value': submission.value,
                'period_updated': evidence.period is not None,
                'new_period': submission.reporting_period,
                'warning': warning
            })
        
        # Return success without applying OCR data
        return Response({
            'message': 'Evidence attached to submission successfully',
            'submission_id': submission.id,
            'value_updated': False
        })

    @action(detail=False, methods=['get'])
    def by_metric(self, request):
        """
        Get standalone evidence files for a specific metric.
        Useful for showing available evidence when filling out a form.
        """
        metric_id = request.query_params.get('metric_id')
        if not metric_id:
            return Response({'error': 'metric_id is required'}, status=400)
        
        try:
            metric = ESGMetric.objects.get(id=metric_id)
        except ESGMetric.DoesNotExist:
            return Response({'error': 'Metric not found'}, status=404)
        
        # Find evidence for this metric (both directly attached and standalone with intended_metric_id)
        evidence = ESGMetricEvidence.objects.filter(
            models.Q(submission__metric=metric) |
            models.Q(
                submission__isnull=True,
                ocr_data__icontains=f'"intended_metric_id": "{metric_id}"'
            )
        ).filter(
            models.Q(uploaded_by=request.user) | 
            models.Q(submission__assignment__layer__in=request.user.layers.all())
        )
        
        serializer = self.get_serializer(evidence, many=True)
        return Response(serializer.data) 