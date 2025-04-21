from rest_framework import viewsets, status, views
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.urls import reverse
from django.db import models
from django.conf import settings

from ...models.templates import ESGMetricEvidence, ESGMetricSubmission
from ...serializers.templates import ESGMetricEvidenceSerializer, ESGMetricSubmissionSerializer
from ...services.bill_analyzer import UtilityBillAnalyzer
from accounts.permissions import BakerTillyAdmin
from accounts.models import LayerProfile
from ...models.polymorphic_metrics import BaseESGMetric, BasicMetric
from ...models.submission_data import BasicMetricData, VehicleRecord, FuelRecord


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
        
        # Other users can only see their own evidence or evidence for their layers
        user_layers = LayerProfile.objects.filter(app_users__user=user)
        return queryset.filter(
            models.Q(uploaded_by=user) | 
            models.Q(layer__in=user_layers)
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
        
        # Handle layer_id - get layer or default to layer 7
        layer_id = request.data.get('layer_id')
        layer = None
        
        if layer_id:
            try:
                # Verify user has access to this layer
                layer = LayerProfile.objects.get(
                    id=layer_id,
                    app_users__user=request.user
                )
            except LayerProfile.DoesNotExist:
                return Response({'error': 'Layer not found or you do not have access to it'}, status=400)
        else:
            # Default to layer 7 for backward compatibility
            try:
                # Get default layer from settings
                default_layer_id = getattr(settings, 'DEFAULT_LAYER_ID', None)
                
                if default_layer_id:
                    layer = LayerProfile.objects.get(id=default_layer_id)
                else:
                    # Fallback to first available group layer
                    layer = LayerProfile.objects.filter(layer_type='GROUP').first()
            except Exception:
                # Just continue without a layer if there's an error
                pass
        
        # Handle optional metric_id - use for OCR analyzer selection
        metric_id = request.data.get('metric_id')
        metric = None
        if metric_id:
            try:
                # Use BaseESGMetric now
                metric = BaseESGMetric.objects.get(id=metric_id)
            except BaseESGMetric.DoesNotExist: # Update exception type
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
        
        # Handle optional source_identifier parameter
        source_identifier = request.data.get('source_identifier')
        
        # Handle optional target_vehicle_id parameter
        target_vehicle_id = request.data.get('target_vehicle_id')
        target_vehicle = None
        if target_vehicle_id:
            try:
                target_vehicle = VehicleRecord.objects.get(id=target_vehicle_id)
                # Optionally: Add permission check to ensure user has access to this vehicle
            except VehicleRecord.DoesNotExist:
                return Response({'error': 'Vehicle not found'}, status=404)
        
        # --- Add Fuel Source Handling ---
        target_fuel_source_id = request.data.get('target_fuel_source_id')
        target_fuel_source = None
        if target_fuel_source_id:
            try:
                # Ensure FuelRecord is imported if not already
                target_fuel_source = FuelRecord.objects.get(id=target_fuel_source_id)
                # Optional: Add permission check for fuel source access
            except FuelRecord.DoesNotExist:
                return Response({'error': 'Fuel Source not found'}, status=404)
        # --- End Fuel Source Handling ---
        
        # Create standalone evidence record
        evidence = ESGMetricEvidence.objects.create(
            file=file_obj,
            filename=file_obj.name,
            file_type=file_obj.content_type,
            uploaded_by=request.user,
            description=request.data.get('description', ''),
            period=period,  # Set the user-provided period
            intended_metric=metric,  # Use the new field for metric relationship
            layer=layer,  # Set the layer
            source_identifier=source_identifier,  # Set the source identifier
            target_vehicle=target_vehicle,  # Set the target vehicle
            target_fuel_source=target_fuel_source # Pass the fetched fuel source
        )
        
        # Prepare response - use serializer to include layer_id and layer_name
        serializer = self.get_serializer(evidence)
        return Response(serializer.data, status=201)

    @action(detail=False, methods=['get'])
    def by_submission(self, request):
        """
        Get evidence files relevant to a specific submission based on metadata.
        
        Parameters:
            submission_id: ID of the submission to get evidence for
        """
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
                LayerProfile.objects.filter(id=submission.assignment.layer.id, app_users__user=request.user).exists()):
            return Response({'error': 'You do not have permission to view this submission'}, status=403)
        
        # Get evidence for this submission based on metadata matching
        evidence = ESGMetricEvidence.objects.filter(
            intended_metric=submission.metric,
            layer=submission.layer
        )
        
        # If submission has a source_identifier, filter by that too
        if submission.source_identifier:
            evidence = evidence.filter(source_identifier=submission.source_identifier)
            
        # For time-based metrics, filter by period if available
        if submission.reporting_period:
            evidence = evidence.filter(period=submission.reporting_period)
            
        evidence = evidence.select_related('layer', 'intended_metric')
        serializer = self.get_serializer(evidence, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def process_ocr(self, request, pk=None):
        evidence = self.get_object()
        
        # Check if already processed
        if evidence.is_processed_by_ocr:
            return Response({'message': 'This file has already been processed with OCR',
                            'ocr_results_url': request.build_absolute_uri(
                                reverse('metric-evidence-ocr-results', args=[evidence.id])
                            )}, status=200)
        
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
                reverse('metric-evidence-ocr-results', args=[evidence.id])
            ),
            'extracted_value': evidence.extracted_value,
            'period': evidence.period
        }, status=200)

    @action(detail=True, methods=['post'])
    def apply_ocr(self, request, pk=None):
        """
        Apply OCR data from evidence to a submission.
        
        Parameters:
            submission_id: ID of the submission to apply OCR data to
        """
        evidence = self.get_object()
        
        # Check if OCR has been processed
        if not evidence.is_processed_by_ocr:
            return Response({'error': 'This evidence has not been processed with OCR'}, status=400)
        
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
                    LayerProfile.objects.filter(id=submission.assignment.layer.id, app_users__user=request.user).exists()):
                return Response({'error': 'You do not have permission to modify this submission'}, status=403)
                
        except ESGMetricSubmission.DoesNotExist:
            return Response({'error': 'Submission not found'}, status=404)
        
        # Apply OCR data if available
        value_updated = False
        period_updated = False
        new_value = None
        new_period = submission.reporting_period # Default to existing
        warning = None
        message = 'OCR data applied successfully'
        
        if evidence.extracted_value is not None:
            try:
                # Get the specific metric instance to check its type
                specific_metric = submission.metric.get_real_instance()
                
                # Only apply OCR numeric value if it's a BasicMetric and not a 'text' type
                if isinstance(specific_metric, BasicMetric) and specific_metric.unit_type != 'text':
                    # Get or create the associated BasicMetricData record
                    basic_data, created = BasicMetricData.objects.get_or_create(submission=submission)
                    
                    # Check for existing value to warn about override
                    existing_value = basic_data.value_numeric
                    if existing_value == 0 and evidence.extracted_value != 0: # Check for overriding zero
                        warning = "Overriding an explicit zero value with OCR data"
                    elif existing_value is not None and existing_value != evidence.extracted_value:
                        warning = f"Overriding existing value {existing_value} with OCR data"
                    
                    # Update BasicMetricData value
                    basic_data.value_numeric = evidence.extracted_value
                    basic_data.value_text = None # Clear text value if setting numeric
                    basic_data.save()
                    value_updated = True
                    new_value = basic_data.value_numeric
                    message = 'OCR numeric data applied to submission'

                    # Update submission's reporting period if evidence period is available
                    evidence_period = evidence.period or evidence.ocr_period
                    if evidence_period:
                        if submission.reporting_period != evidence_period:
                            submission.reporting_period = evidence_period
                            submission.save() # Save submission only if period changes
                            period_updated = True
                        new_period = submission.reporting_period # Update new_period regardless
                        message += ' and submission period updated' if period_updated else ' (submission period already matched)'
                    
                else:
                    # Metric type is not compatible for applying numeric OCR value
                    warning = f"OCR value not applied: Metric type ({type(specific_metric).__name__}) is not a non-text BasicMetric."
                    message = 'OCR numeric value could not be applied due to incompatible metric type.'

            except BaseESGMetric.DoesNotExist:
                warning = "Could not find the metric associated with the submission."
                message = 'Could not verify metric type to apply OCR data.'
            except AttributeError:
                warning = "Could not determine the specific type of the metric."
                message = 'Could not determine specific metric type to apply OCR data.'
            except Exception as e:
                # Catch unexpected errors during OCR application
                warning = f"An unexpected error occurred while trying to apply OCR data: {str(e)}"
                message = 'An error occurred during OCR data application.'

        # Return the response    
        return Response({
            'message': message,
            'submission_id': submission.id,
            'value_updated': value_updated,
            'new_value': new_value,
            'period_updated': period_updated,
            'new_period': new_period,
            'warning': warning
        })

    @action(detail=True, methods=['get'])
    def ocr_results(self, request, pk=None):
        evidence = self.get_object()
        
        if not evidence.is_processed_by_ocr:
            return Response({'error': 'This file has not been processed with OCR'}, status=400)
        
        # Format the primary period if it exists
        formatted_period = None
        if evidence.period:
            if hasattr(evidence.period, 'strftime'):
                # Convert YYYY-MM-DD to MM/YYYY format which is more intuitive for billing periods
                formatted_period = evidence.period.strftime("%m/%Y")
            else:
                formatted_period = str(evidence.period)
        
        # Return OCR results
        result = {
            'id': evidence.id,
            'filename': evidence.filename,
            'extracted_value': evidence.extracted_value,
            'period': formatted_period,
            'additional_periods': evidence.ocr_data.get('additional_periods', []) 
                                 if isinstance(evidence.ocr_data, dict) else [],
            'raw_ocr_data': evidence.ocr_data,
            'is_processed_by_ocr': evidence.is_processed_by_ocr
        }
        
        # Check if additional_periods is empty but we have multiple billing periods data in the raw OCR data
        if not result['additional_periods'] and isinstance(evidence.ocr_data, dict):
            try:
                # Try to extract periods from the raw OCR data fields
                if 'result' in evidence.ocr_data and 'contents' in evidence.ocr_data['result']:
                    fields = evidence.ocr_data['result']['contents'][0]['fields']
                    
                    # Look for MultipleBillingPeriods field
                    if 'MultipleBillingPeriods' in fields and 'valueString' in fields['MultipleBillingPeriods']:
                        multiple_periods_str = fields['MultipleBillingPeriods']['valueString']
                        
                        # Try to extract the JSON array from the string
                        import re
                        import json
                        
                        # Use regex to find array pattern in the string
                        match = re.search(r'\[.*\]', multiple_periods_str)
                        if match:
                            try:
                                # Parse the JSON array
                                periods_array = json.loads(match.group(0))
                                additional_periods = []
                                
                                # Skip the first period if it matches our main period
                                first_period_skipped = False
                                
                                for period in periods_array:
                                    if isinstance(period, dict) and 'period' in period and 'consumption' in period:
                                        # Keep the original MM/YYYY format which is more intuitive for billing periods
                                        period_str = period['period']
                                        
                                        # Skip first period if it matches our current period and we haven't skipped one yet
                                        if not first_period_skipped and formatted_period and period_str == formatted_period:
                                            first_period_skipped = True
                                            continue
                                        
                                        additional_periods.append({
                                            "period": period_str,
                                            "consumption": period['consumption']
                                        })
                                
                                result['additional_periods'] = additional_periods
                            except json.JSONDecodeError:
                                # Ignore parsing errors
                                pass
            except Exception as e:
                # Just ignore errors in extracting additional periods
                pass
        
        return Response(result)

    @action(detail=False, methods=['get'])
    def by_metric(self, request):
        """
        Get evidence files for a specific metric.
        Useful for showing available evidence when filling out a form.
        
        Parameters:
            metric_id: ID of the metric to get evidence for
            layer_id: (Optional) Filter evidence by specific layer
            source_identifier: (Optional) Filter evidence by source
            period: (Optional) Filter evidence by period
        """
        metric_id = request.query_params.get('metric_id')
        if not metric_id:
            return Response({'error': 'metric_id is required'}, status=400)
        
        try:
            # Use BaseESGMetric here
            metric = BaseESGMetric.objects.get(id=metric_id)
        except BaseESGMetric.DoesNotExist: # Update exception type
            return Response({'error': 'Metric not found'}, status=404)
        
        # Check user access to layers
        user_layers = LayerProfile.objects.filter(app_users__user=request.user)
        
        # Base query
        evidence_query = ESGMetricEvidence.objects.filter(
            intended_metric=metric
        ).filter(
            models.Q(uploaded_by=request.user) | 
            models.Q(layer__in=user_layers)
        )
        
        # Apply optional filters
        
        # Layer filter
        layer_id = request.query_params.get('layer_id')
        if layer_id:
            try:
                # Verify that the layer exists and user has access to it
                layer = LayerProfile.objects.get(id=layer_id)
                if not (request.user.is_staff or request.user.is_superuser or 
                        request.user.is_baker_tilly_admin or
                        layer in user_layers):
                    return Response({'error': 'You do not have access to this layer'}, status=403)
                
                # Filter evidence by the selected layer
                evidence_query = evidence_query.filter(layer=layer)
            except LayerProfile.DoesNotExist:
                return Response({'error': f'Layer with ID {layer_id} not found'}, status=404)
                
        # Source identifier filter
        source_identifier = request.query_params.get('source_identifier')
        if source_identifier:
            evidence_query = evidence_query.filter(source_identifier=source_identifier)
            
        # Period filter
        period = request.query_params.get('period')
        if period:
            try:
                from datetime import datetime
                period_date = datetime.strptime(period, '%Y-%m-%d').date()
                evidence_query = evidence_query.filter(period=period_date)
            except ValueError:
                return Response({'error': 'Invalid period format. Use YYYY-MM-DD'}, status=400)
        
        # Execute query and serialize results
        evidence = evidence_query.select_related('layer', 'intended_metric')
        serializer = self.get_serializer(evidence, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def by_vehicle(self, request):
        """
        Get evidence files linked to a specific vehicle, optionally filtered by period.
        
        Parameters:
            vehicle_id: ID of the vehicle to get evidence for
            period: (Optional) Filter evidence by specific period (YYYY-MM-DD)
        """
        vehicle_id = request.query_params.get('vehicle_id')
        if not vehicle_id:
            return Response({'error': 'vehicle_id is required'}, status=400)
        
        # Check if vehicle exists (can be expanded to check permissions)
        try:
            vehicle = VehicleRecord.objects.get(id=vehicle_id)
            
            # Optional: Check if user has permission to access this vehicle
            # (Similar to permission checks in other methods)
        except VehicleRecord.DoesNotExist:
            return Response({'error': 'Vehicle not found'}, status=404)
        
        # Get evidence directly linked to this vehicle
        evidence_query = ESGMetricEvidence.objects.filter(target_vehicle_id=vehicle_id)
        
        # Apply period filter if provided
        period_str = request.query_params.get('period')
        if period_str:
            try:
                from datetime import datetime
                period_date = datetime.strptime(period_str, '%Y-%m-%d').date()
                evidence_query = evidence_query.filter(period=period_date)
            except ValueError:
                return Response({'error': 'Invalid period format. Use YYYY-MM-DD'}, status=400)
        
        # Execute query and return results
        evidence = evidence_query.select_related('layer', 'intended_metric', 'target_vehicle')
        serializer = self.get_serializer(evidence, many=True)
        return Response(serializer.data)


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
        
        # Get all submissions for these IDs
        submissions = ESGMetricSubmission.objects.filter(id__in=submission_ids).select_related(
            'metric', 'assignment', 'submitted_by'
        )
        
        # Check permissions
        user = request.user
        if not (user.is_staff or user.is_superuser or user.is_baker_tilly_admin):
            # Regular users can only see evidence for submissions they have access to
            user_layers = LayerProfile.objects.filter(app_users__user=user)
            accessible_submissions = submissions.filter(
                assignment__layer__in=user_layers
            ).values_list('id', flat=True)
            
            submissions = submissions.filter(id__in=accessible_submissions)
        
        # Find relevant evidence for each submission
        evidence_serializer = ESGMetricEvidenceSerializer
        response_data = {}
        submission_serializer = ESGMetricSubmissionSerializer
        
        for submission in submissions:
            submission_id = str(submission.id)
            
            # Find evidence based on metadata matching
            matching_evidence = ESGMetricEvidence.objects.filter(
                intended_metric=submission.metric,
                layer=submission.layer
            )
            
            # If submission has a source_identifier, filter by that too
            if submission.source_identifier:
                matching_evidence = matching_evidence.filter(source_identifier=submission.source_identifier)
                
            # For time-based metrics, filter by period if available
            if submission.reporting_period:
                matching_evidence = matching_evidence.filter(period=submission.reporting_period)
            
            # Serialize submission and evidence
            submission_data = submission_serializer(submission).data
            submission_data['evidence'] = [evidence_serializer(e).data for e in matching_evidence]
            response_data[submission_id] = submission_data
        
        return Response(response_data) 