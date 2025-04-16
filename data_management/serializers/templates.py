from rest_framework import serializers
from accounts.models import CustomUser, LayerProfile
from accounts.services import get_accessible_layers
# Updated imports: Removed deleted models, added BaseESGMetric placeholder
from ..models.templates import (
    ESGFormCategory, ESGForm,
    Template, TemplateFormSelection, TemplateAssignment,
    ESGMetricSubmission, ESGMetricEvidence,
    ReportedMetricValue
)
# Import the new base model (might need specialized ones later)
from ..models.polymorphic_metrics import (
    BaseESGMetric, BasicMetric, TabularMetric, MaterialTrackingMatrixMetric,
    TimeSeriesMetric, MultiFieldTimeSeriesMetric, MultiFieldMetric, VehicleTrackingMetric
)
# Import the specific data models needed for get_submission_data
from ..models.submission_data import (
    BasicMetricData, TabularMetricRow, MaterialMatrixDataPoint, 
    TimeSeriesDataPoint, MultiFieldTimeSeriesDataPoint, MultiFieldDataPoint
)
# Import the new submission data serializers
from .submission_data import (
    BasicMetricDataSerializer,
    TabularMetricRowSerializer,
    MaterialMatrixDataPointSerializer,
    TimeSeriesDataPointSerializer,
    MultiFieldTimeSeriesDataPointSerializer,
    MultiFieldDataPointSerializer,
    PolymorphicSubmissionDataSerializer, # Import the new polymorphic reader
    VehicleRecordSerializer,
    VehicleMonthlyDataSerializer
)
# Import the polymorphic metric serializer
from .polymorphic_metrics import ESGMetricPolymorphicSerializer 
import logging

logger = logging.getLogger(__name__)

# --- Serializers for Removed/Obsolete Models (Commented Out) ---
# class ESGMetricSerializer(serializers.ModelSerializer):
#     """Serializer for ESG metrics - NEEDS REPLACEMENT WITH POLYMORPHIC SERIALIZER"""
#     form_id = serializers.PrimaryKeyRelatedField(
#         queryset=ESGForm.objects.all(),
#         write_only=True,
#         source='form',
#         required=False
#     )
#     
#     class Meta:
#         model = ESGMetric # Old model
#         fields = ['id', 'name', 'description', 'unit_type', 'custom_unit', 
#                  'requires_evidence', 'order', 'validation_rules', 'location', 'is_required',
#                  'requires_time_reporting', 'reporting_frequency', 'is_multi_value', 'aggregates_inputs',
#                  'form_id']
#         read_only_fields = ['id']

# class MetricValueFieldSerializer(serializers.ModelSerializer):
#     """Serializer for metric value fields (components of multi-value metrics) - OBSOLETE"""
#     class Meta:
#         model = MetricValueField # Deleted model
#         fields = [
#             'id', 'metric', 'field_key', 'display_name', 'description',
#             'column_header', 'display_type', 'order', 'options', 'is_required'
#         ]
#         read_only_fields = ['id']

# class MetricValueSerializer(serializers.ModelSerializer):
#     """Serializer for individual values within a multi-value metric submission input - OBSOLETE"""
#     field_name = serializers.SerializerMethodField()
#     field_key = serializers.SerializerMethodField()
#     
#     class Meta:
#         model = MetricValue # Deleted model
#         fields = [
#             'id', 'field', 'field_name', 'field_key', 'numeric_value', 'text_value'
#         ]
#         read_only_fields = ['id']
#     
#     def get_field_name(self, obj):
#         return obj.field.display_name
#         
#     def get_field_key(self, obj):
#         return obj.field.field_key

# class ReportedMetricFieldValueSerializer(serializers.ModelSerializer):
#     """Serializer for the aggregated value of a specific field within a multi-value metric. - OBSOLETE"""
#     field_key = serializers.CharField(source='field.field_key', read_only=True)
#     field_display_name = serializers.CharField(source='field.display_name', read_only=True)
# 
#     class Meta:
#         model = ReportedMetricFieldValue # Deleted model
#         fields = [
#             'id', 'field', 'field_key', 'field_display_name',
#             'aggregated_numeric_value', 'aggregated_text_value',
#             'aggregation_method', 'source_submission_count',
#             'last_updated_at'
#         ]
#         read_only_fields = fields

# --- Existing Serializers (Adjusted/Commented Fields) ---

class ESGFormCategorySerializer(serializers.ModelSerializer):
    """Serializer for ESG form categories"""
    class Meta:
        model = ESGFormCategory
        fields = ['id', 'name', 'code', 'icon', 'order']

class ESGFormSerializer(serializers.ModelSerializer):
    """Serializer for ESG forms (Basic List/Create/Update View)"""
    # metrics = ESGMetricSerializer(many=True, read_only=True) # Commented out: Needs Polymorphic relation
    category = ESGFormCategorySerializer(read_only=True)
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=ESGFormCategory.objects.all(),
        write_only=True,
        source='category'
    )
    # Explicitly define the annotated field
    metric_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = ESGForm
        # Removed 'metrics' from fields
        # Add the annotated 'metric_count' field
        fields = ['id', 'code', 'name', 'description', 'is_active', 'category', 'category_id', 'order', 'metric_count']
        # No need to list metric_count in read_only_fields here, as it's defined as read_only above
        read_only_fields = ['id']

    def create(self, validated_data):
        """Create a new ESG form"""
        return super().create(validated_data)

# Used in category listing views with forms nested inside categories
class ESGFormCategoryWithFormsSerializer(serializers.ModelSerializer):
    """Serializer for ESG form categories with nested forms"""
    forms = ESGFormSerializer(many=True, read_only=True)
    
    class Meta:
        model = ESGFormCategory
        fields = ['id', 'name', 'code', 'icon', 'order', 'forms']

class TemplateFormSelectionSerializer(serializers.ModelSerializer):
    form = ESGFormSerializer(read_only=True)
    form_id = serializers.PrimaryKeyRelatedField(
        queryset=ESGForm.objects.all(),
        write_only=True,
        source='form'
    )
    completed_by = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = TemplateFormSelection
        fields = ['id', 'form', 'form_id', 'regions', 'order', 'is_completed', 'completed_at', 'completed_by']

class TemplateSerializer(serializers.ModelSerializer):
    selected_forms = TemplateFormSelectionSerializer(
        source='templateformselection_set',
        many=True
    )
    created_by = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = Template
        fields = ['id', 'name', 'description',
                 'is_active', 'version', 'created_by', 'created_at',
                 'updated_at', 'selected_forms']

    def create(self, validated_data):
        selected_forms_data = validated_data.pop('templateformselection_set', [])
        template = Template.objects.create(**validated_data)
        
        for form_data in selected_forms_data:
            TemplateFormSelection.objects.create(
                template=template,
                **form_data
            )
        
        return template

    def update(self, instance, validated_data):
        selected_forms_data = validated_data.pop('templateformselection_set', [])
        
        # Update template fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # Update form selections
        instance.templateformselection_set.all().delete()
        for form_data in selected_forms_data:
            TemplateFormSelection.objects.create(
                template=instance,
                **form_data
            )
        
        return instance

# --- Simple Serializer for Nested Layer Info ---
class LayerBasicSerializer(serializers.ModelSerializer):
    """Basic serializer for LayerProfile including just ID and name."""
    class Meta:
        model = LayerProfile
        fields = ['id', 'company_name']
        read_only_fields = fields # Make all fields read-only

# --- Template Assignment Serializer --- 

class TemplateAssignmentSerializer(serializers.ModelSerializer):
    template = TemplateSerializer(read_only=True)
    template_id = serializers.PrimaryKeyRelatedField(queryset=Template.objects.all(), write_only=True, source='template') # Added source for clarity
    # layer = serializers.PrimaryKeyRelatedField(queryset=LayerProfile.objects.all()) # Removed old field
    layer = LayerBasicSerializer(read_only=True) # Use nested serializer for read operations
    layer_id = serializers.PrimaryKeyRelatedField(queryset=LayerProfile.objects.all(), write_only=True, source='layer') # Add separate write field
    assigned_to = serializers.PrimaryKeyRelatedField(queryset=CustomUser.objects.all(), required=False, allow_null=True)

    class Meta:
        model = TemplateAssignment
        # fields = '__all__' # Replaced with explicit list
        fields = [
            'id', 'template', 'template_id', 'layer', 'layer_id', 'assigned_to', 
            'assigned_at', 'due_date', 'completed_at', 'reporting_period_start', 
            'reporting_period_end', 'reporting_year', 'status'
        ] # Explicitly list fields to include new layer_id
        
    def create(self, validated_data):
        # template = validated_data.pop('template_id') # No longer needed due to source='template' on template_id
        # validated_data['template'] = template
        return super().create(validated_data) # Correctly call super to create the instance

# === Moved Serializers from esg.py ===

class ESGMetricEvidenceSerializer(serializers.ModelSerializer):
    """Serializer for ESG metric evidence files"""
    uploaded_by_name = serializers.SerializerMethodField()
    edited_by_name = serializers.SerializerMethodField()
    layer_id = serializers.PrimaryKeyRelatedField(
        source='layer',
        queryset=LayerProfile.objects.all(),
        required=False,
        allow_null=True
    )
    layer_name = serializers.SerializerMethodField()
    
    class Meta:
        model = ESGMetricEvidence
        # submission field points to ESGMetricSubmission, intended_metric points to BaseESGMetric - OK
        fields = [
            'id', 'file', 'filename', 'file_type', 
            'uploaded_by', 'uploaded_by_name', 'uploaded_at', 'description',
            'enable_ocr_processing', 'is_processed_by_ocr', 'extracted_value', 
            'period', 'was_manually_edited', 'edited_at', 
            'edited_by', 'edited_by_name', 'intended_metric', # Removed submission
            'layer_id', 'layer_name', 'source_identifier' # Added source_identifier
        ]
        read_only_fields = [
            'uploaded_by', 'uploaded_at', 'is_processed_by_ocr', 
            'extracted_value', 'period', 'was_manually_edited',
            'edited_at', 'edited_by', 'layer_name'
        ]
    
    def get_uploaded_by_name(self, obj):
        if obj.uploaded_by:
            return obj.uploaded_by.email
        return None
        
    def get_edited_by_name(self, obj):
        if obj.edited_by:
            return obj.edited_by.email
        return None
        
    def get_layer_name(self, obj):
        if obj.layer:
            return obj.layer.company_name
        return None

class ESGMetricSubmissionSerializer(serializers.ModelSerializer):
    """Serializer for ESG metric submission inputs (header + specific data)."""
    evidence = serializers.SerializerMethodField(read_only=True)
    metric_name = serializers.SerializerMethodField()
    # metric_unit = serializers.SerializerMethodField() # Commented out: Unit info is now on specialized metrics
    submitted_by_name = serializers.SerializerMethodField(read_only=True)
    verified_by_name = serializers.SerializerMethodField(read_only=True)
    layer_id = serializers.PrimaryKeyRelatedField(
        source='layer',
        queryset=LayerProfile.objects.all(),
        required=False,
        allow_null=True
    )
    layer_name = serializers.SerializerMethodField(read_only=True)
    # is_multi_value = serializers.SerializerMethodField() # Commented out: Property gone from BaseESGMetric
    # multi_values = MetricValueSerializer(many=True, read_only=True) # Commented out: Obsolete model
    source_identifier = serializers.CharField(max_length=100, required=False, allow_null=True, allow_blank=True)
    metric = serializers.PrimaryKeyRelatedField(queryset=BaseESGMetric.objects.all()) # Ensure queryset uses BaseESGMetric

    # --- Fields for specific submission data --- 
    # Only one of these should be provided depending on the metric type
    basic_data = BasicMetricDataSerializer(required=False, write_only=True, allow_null=True)
    tabular_rows = TabularMetricRowSerializer(many=True, required=False, write_only=True, allow_null=True)
    material_data_points = MaterialMatrixDataPointSerializer(many=True, required=False, write_only=True, allow_null=True)
    timeseries_data_points = TimeSeriesDataPointSerializer(many=True, required=False, write_only=True, allow_null=True)
    multifield_timeseries_data_points = MultiFieldTimeSeriesDataPointSerializer(many=True, required=False, write_only=True, allow_null=True)
    multifield_data = MultiFieldDataPointSerializer(required=False, write_only=True, allow_null=True)

    # --- Field for reading specific submission data ---
    submission_data = serializers.SerializerMethodField(read_only=True)

    vehicle_records = VehicleRecordSerializer(many=True, required=False)  # Now writable

    class Meta:
        model = ESGMetricSubmission
        # Removed 'value', 'text_value'
        # Added specific data fields to fields list for input processing
        fields = [
            'id', 'assignment', 'metric', 'metric_name', # Removed metric_unit 
            # 'value', 'text_value', # <-- REMOVED
            'reporting_period', 'submitted_by', 'submitted_by_name',
            'submitted_at', 'updated_at', 'notes', 
            'is_verified', 'verified_by', 'verified_by_name', 'verified_at', 'verification_notes', 
            'evidence', 'layer_id', 'layer_name',
            # Removed is_multi_value, multi_values
            'source_identifier',
            # --- Write-only fields for submission data ---
            'basic_data', 'tabular_rows', 'material_data_points', 
            'timeseries_data_points', 'multifield_timeseries_data_points', 'multifield_data',
            'vehicle_records',
            # --- Read-only field for output ---
            'submission_data'
        ]
        read_only_fields = [
            'id',
            'submitted_by_name', # Made read-only, set in create/update
            'submitted_at', 'updated_at', 
            'layer_name', 
            'verified_by_name', 'verified_at', # Verification is separate process
        ]
        # submitted_by will be set automatically based on request user

    def get_metric_name(self, obj):
        # Accessing metric.name should work via polymorphism
        return obj.metric.name if obj.metric else "No Metric"
    
    # def get_metric_unit(self, obj):
    #     # Needs to access specialized metric type (e.g., obj.metric.basicmetric.unit_type)
    #     # Requires polymorphic serializer or more complex logic - comment out for now
    #     # if isinstance(obj.metric, BasicMetric):
    #     #    if obj.metric.unit_type == 'custom':
    #     #        return obj.metric.custom_unit
    #     #    return obj.metric.get_unit_type_display()
    #     # return None # Or a default
    #     pass
    
    def get_submitted_by_name(self, obj):
        if obj.submitted_by:
            return obj.submitted_by.email
        return None
    
    def get_verified_by_name(self, obj):
        if obj.verified_by:
            return obj.verified_by.email
        return None
        
    def get_layer_name(self, obj):
        if obj.layer:
            return obj.layer.company_name
        return None
    
    # def get_is_multi_value(self, obj):
    #     # Property no longer exists on base metric
    #     # Can potentially determine from metric type: isinstance(obj.metric, MultiFieldMetric)
    #     pass 
    
    def get_submission_data(self, obj):
        """Serialize the specific submission data based on the metric type."""
        try:
            # Ensure we have the specific metric instance
            metric = obj.metric.get_real_instance()
        except AttributeError:
            return None # Or return an error indication
            
        data_to_serialize = None
        serializer_kwargs = {'context': self.context}
        
        # Determine which related data to fetch based on metric type
        if isinstance(metric, BasicMetric):
            try:
                data_to_serialize = obj.basic_data
            except BasicMetricData.DoesNotExist:
                pass # No data submitted yet
        elif isinstance(metric, TabularMetric):
            data_to_serialize = obj.tabular_rows.all()
            serializer_kwargs['many'] = True
        elif isinstance(metric, MaterialTrackingMatrixMetric):
            data_to_serialize = obj.material_data_points.all()
            serializer_kwargs['many'] = True
        elif isinstance(metric, TimeSeriesMetric):
            data_to_serialize = obj.timeseries_data_points.all()
            serializer_kwargs['many'] = True
        elif isinstance(metric, MultiFieldTimeSeriesMetric):
            data_to_serialize = obj.multifield_timeseries_data_points.all()
            serializer_kwargs['many'] = True
        elif isinstance(metric, MultiFieldMetric):
            try:
                data_to_serialize = obj.multifield_data
            except MultiFieldDataPoint.DoesNotExist:
                pass
        elif isinstance(metric, VehicleTrackingMetric):
            data_to_serialize = obj.vehicle_records.all()
            serializer_kwargs['many'] = True
            serializer = VehicleRecordSerializer(data_to_serialize, **serializer_kwargs)
            return serializer.data
        
        if data_to_serialize is not None:
            # Use the Polymorphic serializer to render the correct structure
            serializer = PolymorphicSubmissionDataSerializer(data_to_serialize, **serializer_kwargs)
            return serializer.data
        
        return None # Return None if no data found or metric type unhandled

    def get_evidence(self, obj):
        """
        Get related evidence using metadata-based matching via the get_evidence method.
        """
        evidence = obj.get_evidence()
        return ESGMetricEvidenceSerializer(evidence, many=True, context=self.context).data

    def validate_basic_data(self, basic_data):
        """Validate basic structure of basic_data."""
        logger.info(f"Validating basic_data: {basic_data}")
        if basic_data is not None and not isinstance(basic_data, dict):
            logger.error(f"basic_data must be a dictionary, got {type(basic_data)}")
            raise serializers.ValidationError("basic_data must be a dictionary.")
        return basic_data

    def validate(self, data):
        """
        Validate submission based on metric type, ensure only one data field is present,
        and check for duplicates based on the metric's allow_multiple_submissions_per_period flag.
        """
        logger.info(f"Validating submission data: {data}")
        metric = data.get('metric')
        assignment = data.get('assignment')
        reporting_period = data.get('reporting_period', None)
        basic_data = data.get('basic_data')
        
        if not metric:
            logger.error("Metric is required")
            raise serializers.ValidationError("Metric is required.")
        
        # --- BEGIN: Duplicate check (added logic) ---
        is_creating = self.instance is None
        if is_creating:
            if not metric.allow_multiple_submissions_per_period:
                if not assignment:
                    logger.error("Assignment is required when creating a submission")
                    raise serializers.ValidationError({"assignment": "Assignment is required when creating a submission."})

                # Get the layer from the submission data, or default to assignment's layer
                submission_layer = data.get('layer')
                if not submission_layer:
                    submission_layer = assignment.layer
                
                existing_submission_qs = ESGMetricSubmission.objects.filter(
                    assignment=assignment,
                    metric=metric,
                    reporting_period=reporting_period,
                    layer=submission_layer # Add layer to the uniqueness check
                )

                if existing_submission_qs.exists():
                    period_str = f" for period {reporting_period}" if reporting_period else " (no specific period)"
                    metric_name = getattr(metric, 'name', 'Unknown Metric')
                    assignment_name = str(assignment)
                    error_msg = f"A submission already exists for metric '{metric_name}' in assignment '{assignment_name}'{period_str}."
                    logger.error(error_msg)
                    raise serializers.ValidationError(error_msg)
        
        # --- Check data payload presence and type match --- 
        provided_data_fields = [
            f for f in [
                'basic_data', 'tabular_rows', 'material_data_points', 
                'timeseries_data_points', 'multifield_timeseries_data_points', 'multifield_data',
                'vehicle_records'  # Add vehicle_records as a valid data field
            ] if data.get(f) is not None
        ]
        
        logger.info(f"Provided data fields: {provided_data_fields}")
        
        if not provided_data_fields:
            # Special case for VehicleTrackingMetric - if we're submitting for a vehicle tracking metric
            # and there's no error yet, don't raise an error about missing data fields
            if not is_creating or not isinstance(metric, VehicleTrackingMetric) or 'vehicle_records' not in data:
                logger.error("No submission data provided")
                raise serializers.ValidationError("No submission data provided (e.g., basic_data, tabular_rows, etc.).")
        
        # For BasicMetric, we expect basic_data
        if isinstance(metric, BasicMetric) and 'basic_data' not in provided_data_fields:
            logger.error("Basic metric requires basic_data")
            raise serializers.ValidationError(f"Metric of type BasicMetric requires 'basic_data' field, got {provided_data_fields}.")
        
        # Ensure only one type of data is provided (except vehicle_records can be combined)
        data_without_vehicle = [f for f in provided_data_fields if f != 'vehicle_records']
        if len(data_without_vehicle) > 1:
            logger.error(f"Multiple data fields provided: {data_without_vehicle}")
            raise serializers.ValidationError("Multiple types of submission data provided. Only one is allowed.")
        
        # Only perform type match check if a data field was actually provided
        if provided_data_fields:
            provided_field = provided_data_fields[0]
            
            try:
                specific_metric = metric.get_real_instance()
                logger.info(f"Got specific metric type: {type(specific_metric).__name__}")
            except AttributeError:
                logger.error("Could not determine specific metric type")
                raise serializers.ValidationError("Could not determine specific metric type.")

            expected_field_map = {
                BasicMetric: 'basic_data',
                TabularMetric: 'tabular_rows',
                MaterialTrackingMatrixMetric: 'material_data_points',
                TimeSeriesMetric: 'timeseries_data_points',
                MultiFieldTimeSeriesMetric: 'multifield_timeseries_data_points',
                MultiFieldMetric: 'multifield_data',
                VehicleTrackingMetric: 'vehicle_records',  # Add support for VehicleTrackingMetric
            }

            expected_field = None
            for model_class, field_name in expected_field_map.items():
                if isinstance(specific_metric, model_class):
                    expected_field = field_name
                    break
            
            if not expected_field:
                logger.error(f"Unsupported metric type: {type(specific_metric).__name__}")
                raise serializers.ValidationError(f"Unsupported metric type encountered: {type(specific_metric).__name__}")

            # Skip field validation for VehicleTrackingMetric since we handle it specially
            if isinstance(specific_metric, VehicleTrackingMetric):
                logger.info(f"Found VehicleTrackingMetric with vehicle_records data")
                pass  # Skip the field validation
            elif provided_field != expected_field:
                error_msg = f"Invalid data field '{provided_field}' provided for metric type '{type(specific_metric).__name__}'. Expected field: '{expected_field}'."
                logger.error(error_msg)
                raise serializers.ValidationError(error_msg)

            # --- Metric Type-Specific Validation ---
            if isinstance(specific_metric, BasicMetric):
                if basic_data is None:
                    logger.error("basic_data is required for BasicMetric")
                    raise serializers.ValidationError({"basic_data": "basic_data is required for BasicMetric."})
                
                unit_type = specific_metric.unit_type
                value_numeric = basic_data.get('value_numeric')
                value_text = basic_data.get('value_text')
                
                logger.info(f"Validating BasicMetric data - unit_type: {unit_type}, value_numeric: {value_numeric}, value_text: {value_text}")

                if unit_type == 'text':
                    if value_numeric is not None:
                        logger.error("Numeric value provided for text metric")
                        raise serializers.ValidationError({"basic_data": "Numeric value should not be provided for a text metric."})
                    if not value_text:
                        logger.error("Text value required for text metric")
                        raise serializers.ValidationError({"basic_data": "Text value is required for a text metric."})
                else:
                    if value_text is not None and value_text != "":
                        logger.error("Text value provided for non-text metric")
                        raise serializers.ValidationError({"basic_data": "Text value should not be provided for a non-text metric."})
                    if value_numeric is None:
                        logger.error("Numeric value required for non-text metric")
                        raise serializers.ValidationError({"basic_data": "Numeric value is required for a non-text metric."})
                    
                    rules = specific_metric.validation_rules or {}
                    if 'min' in rules and value_numeric < rules['min']:
                        logger.error(f"Value {value_numeric} below minimum {rules['min']}")
                        raise serializers.ValidationError({"basic_data": f"Value must be at least {rules['min']}."})
                    if 'max' in rules and value_numeric > rules['max']:
                        logger.error(f"Value {value_numeric} above maximum {rules['max']}")
                        raise serializers.ValidationError({"basic_data": f"Value must not exceed {rules['max']}."})

        logger.info("Validation successful")
        return data

    def create(self, validated_data):
        """Create submission with related nested data based on the metric type."""
        # Extract nested data
        basic_data = validated_data.pop('basic_data', None)
        tabular_rows = validated_data.pop('tabular_rows', None)
        material_data_points = validated_data.pop('material_data_points', None)
        timeseries_data_points = validated_data.pop('timeseries_data_points', None)
        multifield_timeseries_data_points = validated_data.pop('multifield_timeseries_data_points', None)
        multifield_data = validated_data.pop('multifield_data', None)
        
        # Extract nested vehicle data if present
        vehicle_records_data = validated_data.pop('vehicle_records', None)
        
        # Set the submitted_by field from the request
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            validated_data['submitted_by'] = request.user
        
        # Create the submission header
        submission = ESGMetricSubmission.objects.create(**validated_data)
        
        # Handle the specific data type based on what was provided
        if basic_data:
            from ..models.submission_data import BasicMetricData
            BasicMetricData.objects.create(submission=submission, **basic_data)
        
        if tabular_rows:
            from ..models.submission_data import TabularMetricRow
            for index, row_data in enumerate(tabular_rows):
                TabularMetricRow.objects.create(
                    submission=submission,
                    row_index=row_data.get('row_index', index),
                    row_data=row_data.get('row_data', {})
                )
        
        if material_data_points:
            from ..models.submission_data import MaterialMatrixDataPoint
            for point in material_data_points:
                MaterialMatrixDataPoint.objects.create(
                    submission=submission,
                    material_type=point.get('material_type', ''),
                    period=point.get('period'),
                    value=point.get('value'),
                    unit=point.get('unit', '')
                )
        
        if timeseries_data_points:
            from ..models.submission_data import TimeSeriesDataPoint
            for point in timeseries_data_points:
                TimeSeriesDataPoint.objects.create(
                    submission=submission,
                    period=point.get('period'),
                    value=point.get('value')
                )
        
        if multifield_timeseries_data_points:
            from ..models.submission_data import MultiFieldTimeSeriesDataPoint
            for point in multifield_timeseries_data_points:
                MultiFieldTimeSeriesDataPoint.objects.create(
                    submission=submission,
                    period=point.get('period'),
                    field_data=point.get('field_data', {})
                )
        
        if multifield_data:
            from ..models.submission_data import MultiFieldDataPoint
            MultiFieldDataPoint.objects.create(
                submission=submission,
                field_data=multifield_data.get('field_data', {})
            )
        
        # Handle vehicle_records nested creation
        if vehicle_records_data is not None:
            self._save_vehicle_records(submission, vehicle_records_data)
        
        return submission
        
    def update(self, instance, validated_data):
        """Update submission with related nested data."""
        # Extract nested data
        basic_data = validated_data.pop('basic_data', None)
        tabular_rows = validated_data.pop('tabular_rows', None)
        material_data_points = validated_data.pop('material_data_points', None)
        timeseries_data_points = validated_data.pop('timeseries_data_points', None)
        multifield_timeseries_data_points = validated_data.pop('multifield_timeseries_data_points', None)
        multifield_data = validated_data.pop('multifield_data', None)
        
        # Extract nested vehicle data if present
        vehicle_records_data = validated_data.pop('vehicle_records', None)
        
        # Update the base fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # Handle updating the specific data type
        if basic_data:
            from ..models.submission_data import BasicMetricData
            BasicMetricData.objects.update_or_create(
                submission=instance,
                defaults=basic_data
            )
        
        if tabular_rows:
            from ..models.submission_data import TabularMetricRow
            # Clear existing rows and create new ones
            instance.tabular_rows.all().delete()
            for index, row_data in enumerate(tabular_rows):
                TabularMetricRow.objects.create(
                    submission=instance,
                    row_index=row_data.get('row_index', index),
                    row_data=row_data.get('row_data', {})
                )
        
        if material_data_points:
            from ..models.submission_data import MaterialMatrixDataPoint
            # Clear existing points and create new ones
            instance.material_data_points.all().delete()
            for point in material_data_points:
                MaterialMatrixDataPoint.objects.create(
                    submission=instance,
                    material_type=point.get('material_type', ''),
                    period=point.get('period'),
                    value=point.get('value'),
                    unit=point.get('unit', '')
                )
        
        if timeseries_data_points:
            from ..models.submission_data import TimeSeriesDataPoint
            # Clear existing points and create new ones
            instance.timeseries_data_points.all().delete()
            for point in timeseries_data_points:
                TimeSeriesDataPoint.objects.create(
                    submission=instance,
                    period=point.get('period'),
                    value=point.get('value')
                )
        
        if multifield_timeseries_data_points:
            from ..models.submission_data import MultiFieldTimeSeriesDataPoint
            # Clear existing points and create new ones
            instance.multifield_timeseries_data_points.all().delete()
            for point in multifield_timeseries_data_points:
                MultiFieldTimeSeriesDataPoint.objects.create(
                    submission=instance,
                    period=point.get('period'),
                    field_data=point.get('field_data', {})
                )
        
        if multifield_data:
            from ..models.submission_data import MultiFieldDataPoint
            MultiFieldDataPoint.objects.update_or_create(
                submission=instance,
                defaults={'field_data': multifield_data.get('field_data', {})}
            )
        
        # Handle vehicle_records nested update
        if vehicle_records_data is not None:
            self._save_vehicle_records(instance, vehicle_records_data, update=True)
        
        return instance

    def _save_vehicle_records(self, submission_instance, vehicle_records_data, update=False):
        from ..models.submission_data import VehicleRecord, VehicleMonthlyData
        # For update, keep track of IDs to retain
        keep_vehicle_ids = []
        for vehicle_data in vehicle_records_data:
            monthly_data = vehicle_data.pop('monthly_data', [])
            vehicle_id = vehicle_data.get('id', None)
            if update and vehicle_id:
                # Update existing vehicle record
                try:
                    vehicle_obj = VehicleRecord.objects.get(id=vehicle_id, submission=submission_instance)
                    for attr, value in vehicle_data.items():
                        setattr(vehicle_obj, attr, value)
                    vehicle_obj.save()
                except VehicleRecord.DoesNotExist:
                    vehicle_obj = VehicleRecord.objects.create(submission=submission_instance, **vehicle_data)
            else:
                vehicle_obj = VehicleRecord.objects.create(submission=submission_instance, **vehicle_data)
            keep_vehicle_ids.append(vehicle_obj.id)

            # Handle monthly_data for this vehicle
            keep_monthly_ids = []
            for month_data in monthly_data:
                month_id = month_data.get('id', None)
                if update and month_id:
                    try:
                        month_obj = VehicleMonthlyData.objects.get(id=month_id, vehicle=vehicle_obj)
                        for attr, value in month_data.items():
                            setattr(month_obj, attr, value)
                        month_obj.save()
                    except VehicleMonthlyData.DoesNotExist:
                        month_obj = VehicleMonthlyData.objects.create(vehicle=vehicle_obj, **month_data)
                else:
                    month_obj = VehicleMonthlyData.objects.create(vehicle=vehicle_obj, **month_data)
                keep_monthly_ids.append(month_obj.id)
            # Delete monthly data not in keep list (for update)
            if update:
                VehicleMonthlyData.objects.filter(vehicle=vehicle_obj).exclude(id__in=keep_monthly_ids).delete()
        # Delete vehicle records not in keep list (for update)
        if update:
            VehicleRecord.objects.filter(submission=submission_instance).exclude(id__in=keep_vehicle_ids).delete()

# --- Serializer for Batch Submissions ---

class ESGMetricBatchSubmissionSerializer(serializers.Serializer):
    """Serializer for handling batch submission of multiple metrics for a single assignment."""
    assignment_id = serializers.PrimaryKeyRelatedField(
        queryset=TemplateAssignment.objects.all(),
        write_only=True,
        help_text="The ID of the TemplateAssignment this batch belongs to."
    )
    submissions = serializers.ListField(
        child=serializers.DictField(),
        help_text="List of submission data dictionaries, each containing metric data for submission."
    )
    
    def validate_submissions(self, submissions_data):
        """Validate structure of submissions and add assignment_id to each submission."""
        for index, sub_data in enumerate(submissions_data):
            # Add the assignment_id to each submission before validation
            if 'assignment' not in sub_data:
                assignment = self.initial_data.get('assignment_id')
                if assignment:
                    sub_data['assignment'] = assignment
                
            if 'metric' not in sub_data:
                logger.error(f"Submission {index} missing metric field")
                raise serializers.ValidationError(f"Item {index} in 'submissions' list is missing the 'metric' field.")
            # Individual item validation happens via the child ESGMetricSubmissionSerializer
        return submissions_data
    
    # Note: The actual creation/update logic will be handled in the viewset action
    # This serializer primarily validates the overall batch structure.

# --- Other Serializers (Verification, Aggregation) ---

class ESGMetricSubmissionVerifySerializer(serializers.Serializer):
    """Serializer for verifying ESG metric submissions"""
    verification_notes = serializers.CharField(required=False, allow_blank=True)
    
    def validate(self, data):
        """Ensure the user has permission to verify submissions"""
        request = self.context.get('request')
        if not request or not hasattr(request, 'user'):
            raise serializers.ValidationError("Authentication required")
            
        user = request.user
        # Assuming CustomUser model has these fields
        # TODO: Update permission check if needed
        if not (user.is_staff or user.is_superuser or getattr(user, 'is_baker_tilly_admin', False)): 
            raise serializers.ValidationError("Only Baker Tilly admins can verify submissions")
            
        return data

# --- New Serializers for Phase 3 --- 

# Removed ReportedMetricFieldValueSerializer

class ReportedMetricValueSerializer(serializers.ModelSerializer):
    """Serializer for the parent Aggregated Metric Record."""
    metric_name = serializers.CharField(source='metric.name', read_only=True)
    # metric_unit = serializers.SerializerMethodField(read_only=True) # Needs update for specialized types
    layer_name = serializers.CharField(source='layer.company_name', read_only=True)
    metric = serializers.PrimaryKeyRelatedField(queryset=BaseESGMetric.objects.all()) # Point to BaseESGMetric
    
    # Nested serializer for multi-value fields - Removed as dependent serializer is obsolete
    # aggregated_fields = ReportedMetricFieldValueSerializer(many=True, read_only=True)

    class Meta:
        model = ReportedMetricValue
        # Removed aggregated_fields
        fields = [
            'id', 'assignment', 'metric', 'metric_name', # Removed metric_unit
            'layer', 'layer_name', 'reporting_period',
            # Single-value results - kept for now
            'aggregated_numeric_value', 'aggregated_text_value',
            # Calculation & Aggregation Metadata
            'calculated_at', 'last_updated_at',
            'source_submission_count', 'first_submission_at', 'last_submission_at',
        ]
        read_only_fields = [ # Most fields are read-only, calculated by the service
            'id', 'assignment', 'metric', 'layer', 'reporting_period',
            'metric_name', 'layer_name', # Removed metric_unit
            'aggregated_numeric_value', 'aggregated_text_value',
            'calculated_at', 'last_updated_at',
            'source_submission_count', 'first_submission_at', 'last_submission_at',
        ]

    # def get_metric_unit(self, obj):
    #     # Needs update for specialized types
    #     pass

# --- NEW: Detail Serializer for ESG Forms (Includes Nested Metrics) ---
class ESGFormDetailSerializer(serializers.ModelSerializer):
    """Serializer for detailed ESG form view, including nested polymorphic metrics."""
    category = ESGFormCategorySerializer(read_only=True)
    # Use the related_name defined in BaseESGMetric.form ForeignKey
    polymorphic_metrics = ESGMetricPolymorphicSerializer(many=True, read_only=True)

    class Meta:
        model = ESGForm
        # Ensure 'polymorphic_metrics' matches the field name used above
        fields = [
            'id', 'code', 'name', 'description', 'is_active',
            'category', 'order', 'polymorphic_metrics'
        ]
        read_only_fields = ['id', 'polymorphic_metrics'] # Metrics are read-only in the context of the form detail


    def create(self, validated_data):
        # ... existing code ...
        pass

# ----------------------------------