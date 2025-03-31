from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.urls import reverse
from django.db import models
from django.conf import settings

from ...models.templates import ESGMetricEvidence, ESGMetricSubmission, ESGMetric
from ...serializers.esg import ESGMetricEvidenceSerializer, ESGMetricSubmissionSerializer
from ...services.bill_analyzer import UtilityBillAnalyzer
from accounts.permissions import BakerTillyAdmin
from accounts.models import LayerProfile


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
        user_layers = LayerProfile.objects.filter(app_users__user=user)
        return queryset.filter(
            models.Q(uploaded_by=user) | 
            models.Q(submission__assignment__layer__in=user_layers)
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
            period=period,  # Set the user-provided period
            intended_metric=metric,  # Use the new field for metric relationship
            layer=layer  # Set the layer
        )
        
        # Prepare response - use serializer to include layer_id and layer_name
        serializer = self.get_serializer(evidence)
        return Response(serializer.data, status=201)

    @action(detail=False, methods=['get'])
    def by_submission(self, request):
        """
        Get evidence files for a specific submission.
        
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
        
        # Get evidence for this submission
        evidence = ESGMetricEvidence.objects.filter(submission=submission).select_related('layer')
        serializer = self.get_serializer(evidence, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def batch_evidence(self, request):
        """
        Get evidence files and submission data for multiple submissions at once.
        This is an optimization for the admin interface to reduce the number of API calls.
        
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

    @action(detail=True, methods=['post'])
    def process_ocr(self, request, pk=None):
        """
        Process evidence file with OCR to extract data.
        Sets extracted_value and period information on the evidence record.
        """
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
            'period': evidence.period.isoformat() if evidence.period else None,
            'multiple_periods': len(result.get('additional_periods', [])) > 0
        }, status=200)

    @action(detail=True, methods=['get'])
    def ocr_results(self, request, pk=None):
        """
        Get OCR results for an evidence file, including any extracted periods.
        Returns standardized period format (ISO for dates, MM/YYYY for billing periods).
        """
        evidence = self.get_object()
        
        if not evidence.is_processed_by_ocr:
            return Response({'error': 'This file has not been processed with OCR'}, status=400)
        
        # Format the primary period if it exists - always use ISO for consistency
        formatted_period = None
        if evidence.period:
            if hasattr(evidence.period, 'strftime'):
                # Use ISO format for consistency in API 
                formatted_period = evidence.period.isoformat()
                # Include MM/YYYY as display format for convenience
                display_period = evidence.period.strftime("%m/%Y")
            else:
                formatted_period = str(evidence.period)
                display_period = formatted_period
        
        # Retrieve standardized additional periods
        additional_periods = []
        if isinstance(evidence.ocr_data, dict) and 'additional_periods' in evidence.ocr_data:
            additional_periods = evidence.ocr_data['additional_periods']
            
            # Standardize period format for all additional periods
            for period in additional_periods:
                if 'period' in period and isinstance(period['period'], str):
                    # Ensure we have both machine-readable and display formats
                    period['period_display'] = period['period']  # MM/YYYY display format
                    
                    # Try to convert to ISO if possible
                    try:
                        from datetime import datetime
                        mm, yyyy = period['period'].split('/')
                        iso_date = datetime(int(yyyy), int(mm), 1).date().isoformat()
                        period['period_iso'] = iso_date
                    except (ValueError, AttributeError):
                        # Keep only the display format if conversion fails
                        pass
        
        # Return standardized OCR results
        result = {
            'id': evidence.id,
            'filename': evidence.filename,
            'extracted_value': evidence.extracted_value,
            'period': formatted_period,
            'period_display': display_period if formatted_period else None,
            'reference_path': evidence.reference_path,
            'additional_periods': additional_periods,
            'raw_ocr_data': evidence.ocr_data,
            'is_processed_by_ocr': evidence.is_processed_by_ocr
        }
        
        # If no additional periods extracted yet, try to extract from raw results
        if not additional_periods and isinstance(evidence.ocr_data, dict):
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
                                
                                for period in periods_array:
                                    if isinstance(period, dict) and 'period' in period and 'consumption' in period:
                                        # Add standardized period data
                                        period_str = period['period']
                                        consumption = period['consumption']
                                        
                                        period_entry = {
                                            "period_display": period_str,
                                            "consumption": consumption
                                        }
                                        
                                        # Try to add ISO date
                                        try:
                                            from datetime import datetime
                                            mm, yyyy = period_str.split('/')
                                            iso_date = datetime(int(yyyy), int(mm), 1).date().isoformat()
                                            period_entry['period_iso'] = iso_date
                                        except (ValueError, AttributeError):
                                            pass
                                            
                                        additional_periods.append(period_entry)
                                
                                result['additional_periods'] = additional_periods
                            except json.JSONDecodeError:
                                # Ignore parsing errors
                                pass
            except Exception:
                # Just ignore errors in extracting additional periods
                pass
        
        return Response(result)

    @action(detail=True, methods=['post'])
    def attach_to_submission(self, request, pk=None):
        """
        Attach a standalone evidence file to a submission.
        Optionally applies OCR data to the submission's JSON data structure.
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
                    LayerProfile.objects.filter(id=submission.assignment.layer.id, app_users__user=request.user).exists()):
                return Response({'error': 'You do not have permission to modify this submission'}, status=403)
                
        except ESGMetricSubmission.DoesNotExist:
            return Response({'error': 'Submission not found'}, status=404)
        
        # Get the target path for this evidence
        target_path = evidence.reference_path
        
        # If no explicit path is set, try to use the metric's primary_path
        if not target_path and submission.metric and submission.metric.primary_path:
            target_path = submission.metric.primary_path
        
        # Determine if this is a time-based metric
        is_time_based = False
        if submission.metric and submission.metric.requires_time_reporting:
            is_time_based = True
        
        # For time-based metrics without an explicit path, default to periods structure
        if is_time_based and not target_path:
            # Use the period from the evidence to create a default path
            evidence_period = evidence.period or evidence.ocr_period
            if evidence_period:
                period_key = evidence_period.strftime("%m/%Y")
                target_path = f"periods.{period_key}.value"
                
        # Attach evidence to submission and store the reference path
        evidence.submission = submission
        
        # Always store the path in reference_path field
        evidence.reference_path = target_path
        
        evidence.save()
        
        # Apply OCR data if requested and available
        apply_ocr = request.data.get('apply_ocr_data') == 'true'
        if apply_ocr and evidence.is_processed_by_ocr and evidence.extracted_value is not None:
            # Initialize submission data if not present
            if not submission.data:
                submission.data = {}
            
            if target_path:
                # Validate against schema if available
                schema_valid = True
                error_message = None
                
                if submission.metric and submission.metric.data_schema:
                    try:
                        # Import jsonschema validation if needed
                        import jsonschema
                        
                        # Create a temporary copy of the data to validate the change
                        import copy
                        temp_data = copy.deepcopy(submission.data) if submission.data else {}
                        
                        # Update the temporary data
                        parts = target_path.split('.')
                        data_pointer = temp_data
                        
                        # Build nested structure if needed
                        for i, part in enumerate(parts[:-1]):
                            if part not in data_pointer:
                                data_pointer[part] = {}
                            elif not isinstance(data_pointer[part], dict):
                                # Convert to dict if not already
                                old_value = data_pointer[part]
                                data_pointer[part] = {"value": old_value}
                            data_pointer = data_pointer[part]
                        
                        # Set the new value
                        data_pointer[parts[-1]] = evidence.extracted_value
                        
                        # Validate against schema
                        jsonschema.validate(instance=temp_data, schema=submission.metric.data_schema)
                    except (jsonschema.exceptions.ValidationError, Exception) as e:
                        schema_valid = False
                        error_message = str(e)
                
                if not schema_valid:
                    return Response({
                        'error': 'OCR data does not match the metric schema',
                        'details': error_message,
                        'submission_id': submission.id,
                        'evidence_id': evidence.id
                    }, status=400)
                
                # Schema validation passed (or not required), apply the update
                parts = target_path.split('.')
                data_pointer = submission.data
                warning = None
                
                # Build nested structure if needed
                for i, part in enumerate(parts[:-1]):
                    if part not in data_pointer:
                        data_pointer[part] = {}
                    elif not isinstance(data_pointer[part], dict):
                        # Convert to dict if not already
                        old_value = data_pointer[part]
                        data_pointer[part] = {"value": old_value}
                    data_pointer = data_pointer[part]
                
                # Get final part of path
                final_part = parts[-1]
                
                # Check if we're overriding an existing value
                if final_part in data_pointer:
                    existing_value = data_pointer[final_part]
                    if existing_value is not None and existing_value != evidence.extracted_value:
                        warning = f"Overriding existing value {existing_value} with OCR data {evidence.extracted_value}"
                
                # Set the new value
                data_pointer[final_part] = evidence.extracted_value
                
                # Handle period data - always store in standard format
                evidence_period = evidence.period or evidence.ocr_period
                period_updated = False
                
                if evidence_period:
                    # Store period in metadata
                    if '_metadata' not in submission.data:
                        submission.data['_metadata'] = {}
                    
                    # Always use ISO format for consistency
                    period_str = evidence_period.isoformat()
                    submission.data['_metadata']['period'] = period_str
                    period_updated = True
                    
                    # If not already using periods structure, initialize it for time-based metrics
                    if is_time_based and 'periods' not in submission.data:
                        submission.data['periods'] = {}
                        
                    # Add to periods structure if appropriate
                    if 'periods' in submission.data and isinstance(submission.data['periods'], dict) and not target_path.startswith('periods.'):
                        # Add a reference to this value in the periods structure
                        period_key = evidence_period.strftime("%m/%Y")  # Format as MM/YYYY for display
                        if period_key not in submission.data['periods']:
                            submission.data['periods'][period_key] = {}
                        
                        # Store the value and ISO date in the period structure
                        submission.data['periods'][period_key]['value'] = evidence.extracted_value
                        submission.data['periods'][period_key]['date'] = period_str
                
                # Save the updated submission
                submission.save()
                
                return Response({
                    'message': 'Evidence attached and OCR data applied to JSON structure',
                    'submission_id': submission.id,
                    'path_updated': target_path,
                    'new_value': evidence.extracted_value,
                    'period_updated': period_updated,
                    'new_period': evidence_period.isoformat() if evidence_period else None,
                    'schema_validated': True,
                    'warning': warning
                })
            else:
                # No target path available
                return Response({
                    'warning': 'No JSON path specified. OCR data not applied. Use set_target_path to specify where data should go.',
                    'submission_id': submission.id,
                    'evidence_id': evidence.id
                }, status=200)
        
        # OCR data not applied, return success with path info
        return Response({
            'message': 'Evidence attached to submission successfully',
            'submission_id': submission.id,
            'reference_path': evidence.reference_path
        })

    @action(detail=True, methods=['post'])
    def set_target_path(self, request, pk=None):
        """
        Set the target JSON path where OCR data should be applied.
        This should be called before processing OCR to specify where the data should go.
        
        Parameters:
            reference_path: JSON path where OCR data should be stored (e.g., 'electricity.consumption' or 'periods.Jan-2024.value')
        """
        evidence = self.get_object()
        
        # Get required path
        reference_path = request.data.get('reference_path')
        if not reference_path:
            return Response({'error': 'reference_path is required'}, status=400)
        
        # Validate the reference path format
        if not self._is_valid_path(reference_path):
            return Response({'error': 'Invalid path format. Path should only contain alphanumeric characters, dots, hyphens, and underscores'}, status=400)
        
        # If metric is available, validate against schema
        if evidence.intended_metric and evidence.intended_metric.data_schema:
            schema_valid, error = self._validate_path_against_schema(reference_path, evidence.intended_metric.data_schema)
            if not schema_valid:
                return Response({
                    'error': 'Path does not match the metric schema',
                    'details': error,
                    'metric_id': evidence.intended_metric.id
                }, status=400)
        
        # Set both the reference_path and json_path fields
        evidence.reference_path = reference_path
        
        evidence.save()
        
        return Response({
            'message': f'Target path set to {reference_path}',
            'reference_path': evidence.reference_path,
            'evidence_id': evidence.id
        })
        
    def _is_valid_path(self, path):
        """
        Validate that a reference path only contains allowed characters.
        Helps prevent injection attacks or invalid JSON paths.
        """
        import re
        # Path should contain only alphanumeric chars, dots, hyphens, and underscores
        # Plus allow brackets for array indices [0] etc.
        return bool(re.match(r'^[a-zA-Z0-9_.\-\[\]]+$', path))
        
    def _validate_path_against_schema(self, path, schema):
        """
        Validate that a JSON path is compatible with a JSON schema.
        Returns (True, None) if valid, (False, error_message) if invalid.
        """
        if not schema or not isinstance(schema, dict):
            return True, None
            
        parts = path.split('.')
        schema_obj = schema
        
        # For simple validation, just check if the path could exist in the schema
        try:
            for i, part in enumerate(parts):
                # If we're at the last part, just check if it's compatible with schema
                if i == len(parts) - 1:
                    # For the final part, it needs to be a property or a field in an object
                    if 'properties' in schema_obj and part in schema_obj['properties']:
                        return True, None
                    elif schema_obj.get('type') == 'object' and schema_obj.get('additionalProperties', False):
                        return True, None
                    else:
                        return False, f"Field '{part}' not found in schema"
                else:
                    # For intermediate parts, they must be objects
                    if 'properties' in schema_obj and part in schema_obj['properties']:
                        schema_obj = schema_obj['properties'][part]
                    else:
                        return False, f"Path segment '{part}' not found in schema"
                        
                    # Check if it's an object
                    if schema_obj.get('type') != 'object':
                        return False, f"Path segment '{part}' is not an object in schema"
        except Exception as e:
            return False, f"Error validating path: {str(e)}"
            
        return True, None
        
    @action(detail=True, methods=['post'])
    def apply_multiple_periods(self, request, pk=None):
        """
        Apply OCR-extracted data for multiple billing periods to a submission's JSON structure.
        This is useful for utility bills that contain multiple monthly/quarterly readings.
        
        Parameters:
            submission_id: ID of the submission to apply periods to
            base_path: Base path in the JSON where periods should be stored (default: 'periods')
            value_field: Name of the field to store consumption values (default: 'value')
        """
        evidence = self.get_object()
        
        # Check requirements
        if not evidence.is_processed_by_ocr:
            return Response({'error': 'Evidence has not been processed with OCR'}, status=400)
        
        # Get required submission_id
        submission_id = request.data.get('submission_id')
        if not submission_id:
            return Response({'error': 'submission_id is required'}, status=400)
        
        # Get optional parameters
        base_path = request.data.get('base_path', 'periods')
        value_field = request.data.get('value_field', 'value')
        
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
        
        # Check if there are actually multiple periods available
        additional_periods = []
        if isinstance(evidence.ocr_data, dict) and 'additional_periods' in evidence.ocr_data:
            additional_periods = evidence.ocr_data['additional_periods']
        
        # If no additional periods in ocr_data, try to extract them from raw results
        if not additional_periods and isinstance(evidence.ocr_data, dict):
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
                                
                                for period in periods_array:
                                    if isinstance(period, dict) and 'period' in period and 'consumption' in period:
                                        # Keep the original MM/YYYY format
                                        period_str = period['period']
                                        consumption = period['consumption']
                                        
                                        additional_periods.append({
                                            "period": period_str,
                                            "consumption": consumption
                                        })
                            except json.JSONDecodeError:
                                pass
            except Exception:
                # If extraction fails, just continue with empty additional_periods
                pass
        
        if not additional_periods and evidence.extracted_value is None:
            return Response({'error': 'No period data available in this evidence'}, status=400)
        
        # Initialize submission data if needed
        if not submission.data:
            submission.data = {}
        
        if base_path not in submission.data:
            submission.data[base_path] = {}
        
        # Add all periods
        periods_added = []
        
        # First add the primary period if available
        if evidence.extracted_value is not None and (evidence.period or evidence.ocr_period):
            period = evidence.period or evidence.ocr_period
            period_key = period.strftime("%m/%Y")
            
            if period_key not in submission.data[base_path]:
                submission.data[base_path][period_key] = {}
            
            # Store both the value and ISO date
            submission.data[base_path][period_key][value_field] = evidence.extracted_value
            submission.data[base_path][period_key]['date'] = period.isoformat()
            periods_added.append(period_key)
        
        # Then add all additional periods
        for period_data in additional_periods:
            period_key = period_data.get('period')
            consumption = period_data.get('consumption')
            
            if period_key and consumption is not None:
                # Make sure it's not already added
                if period_key in periods_added:
                    continue
                
                if period_key not in submission.data[base_path]:
                    submission.data[base_path][period_key] = {}
                
                # Store the value
                submission.data[base_path][period_key][value_field] = consumption
                
                # Try to add ISO date if not present
                if 'date' not in submission.data[base_path][period_key]:
                    try:
                        from datetime import datetime
                        if '/' in period_key:
                            mm, yyyy = period_key.split('/')
                            date_obj = datetime(int(yyyy), int(mm), 1).date()
                            submission.data[base_path][period_key]['date'] = date_obj.isoformat()
                    except (ValueError, AttributeError):
                        # If date parsing fails, just continue without the ISO date
                        pass
                        
                periods_added.append(period_key)
        
        # Set evidence status if not already attached
        if not evidence.submission_id:
            evidence.submission = submission
            
            # Use the new flag instead of json_path suffix pattern
            evidence.reference_path = base_path  # Store base path in reference_path
            evidence.supports_multiple_periods = True  # Set the flag instead of using .multiple suffix
            
            evidence.save()
        
        # Validate against schema if available
        schema_valid = True
        error_message = None
        
        if submission.metric and submission.metric.data_schema:
            try:
                import jsonschema
                jsonschema.validate(instance=submission.data, schema=submission.metric.data_schema)
            except (jsonschema.exceptions.ValidationError, Exception) as e:
                schema_valid = False
                error_message = str(e)
                
        # If validation failed, include warning but still save (don't block the operation)
        if not schema_valid:
            # Save the submission
            submission.save()
            
            return Response({
                'message': f'Applied {len(periods_added)} billing periods to submission',
                'submission_id': submission.id,
                'periods_added': periods_added,
                'base_path': base_path,
                'value_field': value_field,
                'warning': 'Data does not fully match schema',
                'validation_error': error_message
            })
        
        # Save the submission
        submission.save()
        
        return Response({
            'message': f'Applied {len(periods_added)} billing periods to submission',
            'submission_id': submission.id,
            'periods_added': periods_added,
            'base_path': base_path,
            'value_field': value_field
        })

    @action(detail=False, methods=['get'])
    def by_metric(self, request):
        """
        Get standalone evidence files for a specific metric.
        Useful for showing available evidence when filling out a form.
        
        Parameters:
            metric_id: ID of the metric to get evidence for
            layer_id: (Optional) Filter evidence by specific layer
        """
        metric_id = request.query_params.get('metric_id')
        if not metric_id:
            return Response({'error': 'metric_id is required'}, status=400)
        
        try:
            metric = ESGMetric.objects.get(id=metric_id)
        except ESGMetric.DoesNotExist:
            return Response({'error': 'Metric not found'}, status=404)
        
        # Find evidence for this metric (both directly attached and standalone with intended_metric)
        user_layers = LayerProfile.objects.filter(app_users__user=request.user)
        
        # Base query
        evidence_query = ESGMetricEvidence.objects.filter(
            models.Q(submission__metric=metric) |
            models.Q(
                submission__isnull=True,
                intended_metric=metric
            )
        ).filter(
            models.Q(uploaded_by=request.user) | 
            models.Q(submission__assignment__layer__in=user_layers)
        )
        
        # Apply layer filter if provided
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
        
        # Execute query and serialize results
        evidence = evidence_query.select_related('layer', 'intended_metric')
        serializer = self.get_serializer(evidence, many=True)
        return Response(serializer.data) 