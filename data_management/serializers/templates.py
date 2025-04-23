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
    TimeSeriesMetric, MultiFieldTimeSeriesMetric, MultiFieldMetric, VehicleTrackingMetric,
    FuelConsumptionMetric, ChecklistMetric  # Add ChecklistMetric
)
# Import the specific data models needed for get_submission_data
from ..models.submission_data import (
    BasicMetricData, TabularMetricRow, MaterialMatrixDataPoint, 
    TimeSeriesDataPoint, MultiFieldTimeSeriesDataPoint, MultiFieldDataPoint,
    VehicleRecord, FuelRecord, ChecklistResponse  # Added import for VehicleRecord, FuelRecord, and ChecklistResponse
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
    VehicleMonthlyDataSerializer,
    FuelRecordSerializer,  # Add import for our new serializers
    FuelMonthlyDataSerializer,
    ChecklistResponseSerializer
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
    
    # Add target_vehicle_id field for write operations
    target_vehicle_id = serializers.PrimaryKeyRelatedField(
        source='target_vehicle',
        queryset=VehicleRecord.objects.all(),
        required=False,
        allow_null=True,
        write_only=True
    )
    
    # Add target_vehicle_info field for read operations
    target_vehicle_info = serializers.SerializerMethodField(read_only=True)
    
    # --- Add Fuel Source Linking ---
    # Add target_fuel_source_id field for write operations
    target_fuel_source_id = serializers.PrimaryKeyRelatedField(
        source='target_fuel_source',
        queryset=FuelRecord.objects.all(),
        required=False,
        allow_null=True,
        write_only=True
    )
    
    # Add target_fuel_source_info field for read operations
    target_fuel_source_info = serializers.SerializerMethodField(read_only=True)
    
    # --- End Fuel Source Linking ---

    class Meta:
        model = ESGMetricEvidence
        # submission field points to ESGMetricSubmission, intended_metric points to BaseESGMetric - OK
        fields = [
            'id', 'file', 'filename', 'file_type', 
            'uploaded_by', 'uploaded_by_name', 'uploaded_at', 'description',
            'enable_ocr_processing', 'is_processed_by_ocr', 'extracted_value', 
            'period', 'was_manually_edited', 'edited_at', 
            'edited_by', 'edited_by_name', 'intended_metric', # Removed submission
            'layer_id', 'layer_name', 'source_identifier', # Added source_identifier
            'target_vehicle_id', 'target_vehicle_info', # Added vehicle fields
            'target_fuel_source_id', 'target_fuel_source_info' # Added fuel source fields
        ]
        read_only_fields = [
            'id', 'filename', 'file_type', 'uploaded_by_name', 'uploaded_at',
            'is_processed_by_ocr', 'edited_at', 'edited_by_name',
            'layer_name', 'target_vehicle_info', 'target_fuel_source_info' # Added fuel source info
        ]
        # Ensure imports are present
        # from data_management.models import VehicleRecord
        from ..models.submission_data import VehicleRecord, FuelRecord

    def get_uploaded_by_name(self, obj):
        return obj.uploaded_by.email if obj.uploaded_by else None

    def get_edited_by_name(self, obj):
        return obj.edited_by.email if obj.edited_by else None

    def get_layer_name(self, obj):
        return obj.layer.company_name if obj.layer else None
        
    def get_target_vehicle_info(self, obj):
        """Return basic info about the target vehicle, if linked."""
        if obj.target_vehicle:
            return {
                'id': obj.target_vehicle.id,
                'registration': obj.target_vehicle.registration_number,
                # Use the string representation of the related objects for type/fuel
                'type': str(obj.target_vehicle.vehicle_type) if obj.target_vehicle.vehicle_type else None,
                'fuel': str(obj.target_vehicle.fuel_type) if obj.target_vehicle.fuel_type else None,
                # --- Added fields ---
                'brand': obj.target_vehicle.brand,
                'model': obj.target_vehicle.model,
                'notes': obj.target_vehicle.notes,
                'is_active': obj.target_vehicle.is_active
                # --- End added fields ---
            }
        return None
        
    def get_target_fuel_source_info(self, obj):
        """Return basic info about the linked fuel source."""
        if obj.target_fuel_source:
            return {
                'id': obj.target_fuel_source.id,
                'name': obj.target_fuel_source.name,
                'type': obj.target_fuel_source.source_type.label if obj.target_fuel_source.source_type else None,
                'fuel': obj.target_fuel_source.fuel_type.label if obj.target_fuel_source.fuel_type else None
            }
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

    vehicle_records = VehicleRecordSerializer(many=True, required=False)  # Now writable
    
    # Add fuel_records field for FuelConsumptionMetric
    fuel_records = FuelRecordSerializer(many=True, required=False)  # Now writable

    # Add checklist_responses field for ChecklistMetric
    checklist_responses = ChecklistResponseSerializer(many=True, required=False)  # Now writable

    # --- Field for reading specific submission data ---
    submission_data = serializers.SerializerMethodField(read_only=True)

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
            'vehicle_records', 'fuel_records', 'checklist_responses',  # Add checklist_responses
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
        """
        Return the submission data in the appropriate format based on the metric type.
        """
        from ..models.polymorphic_metrics import (
            BasicMetric, TabularMetric, MaterialTrackingMatrixMetric,
            TimeSeriesMetric, MultiFieldTimeSeriesMetric, MultiFieldMetric,
            VehicleTrackingMetric, FuelConsumptionMetric, ChecklistMetric
        )
        from ..serializers.submission_data import (
            BasicMetricDataSerializer, TabularMetricRowSerializer,
            MaterialMatrixDataPointSerializer, TimeSeriesDataPointSerializer,
            MultiFieldTimeSeriesDataPointSerializer, MultiFieldDataPointSerializer,
            VehicleRecordSerializer, FuelRecordSerializer, ChecklistResponseSerializer
        )
        
        # Get the actual metric type
        try:
            metric_instance = obj.metric.get_real_instance()
        except AttributeError:
            # Fall back to base type if get_real_instance fails
            metric_instance = obj.metric
        
        if isinstance(metric_instance, BasicMetric):
            try:
                data_to_serialize = obj.basic_data
                if data_to_serialize:
                    return BasicMetricDataSerializer(data_to_serialize, context=self.context).data
            except BasicMetricData.DoesNotExist:
                pass # No data submitted yet
            return None
        elif isinstance(metric_instance, TabularMetric):
            rows = obj.tabular_rows.all()
            if rows.exists():
                return TabularMetricRowSerializer(rows, many=True, context=self.context).data
            return []
        elif isinstance(metric_instance, MaterialTrackingMatrixMetric):
            points = obj.material_data_points.all()
            if points.exists():
                return MaterialMatrixDataPointSerializer(points, many=True, context=self.context).data
            return []
        elif isinstance(metric_instance, TimeSeriesMetric):
            points = obj.timeseries_data_points.all()
            if points.exists():
                return TimeSeriesDataPointSerializer(points, many=True, context=self.context).data
            return []
        elif isinstance(metric_instance, MultiFieldTimeSeriesMetric):
            points = obj.multifield_timeseries_data_points.all()
            if points.exists():
                return MultiFieldTimeSeriesDataPointSerializer(points, many=True, context=self.context).data
            return []
        elif isinstance(metric_instance, MultiFieldMetric):
            try:
                data_to_serialize = obj.multifield_data
                if data_to_serialize:
                    return MultiFieldDataPointSerializer(data_to_serialize, context=self.context).data
            except MultiFieldDataPoint.DoesNotExist:
                pass
            return None
        elif isinstance(metric_instance, VehicleTrackingMetric):
            # For vehicle tracking, include all vehicle records
            vehicle_records = obj.vehicle_records.all()
            if vehicle_records.exists():
                return VehicleRecordSerializer(vehicle_records, many=True).data
            return []
        elif isinstance(metric_instance, FuelConsumptionMetric):
            # For fuel consumption, include all fuel records
            fuel_records = obj.fuel_records.all()
            if fuel_records.exists():
                return FuelRecordSerializer(fuel_records, many=True).data
            return []
        elif isinstance(metric_instance, ChecklistMetric):
            # For checklists, include all checklist responses
            checklist_responses = obj.checklist_responses.all()
            if checklist_responses.exists():
                return ChecklistResponseSerializer(checklist_responses, many=True).data
            return []
            
        # If we got here with no match, return None
        return None

    def get_evidence(self, obj):
        """
        Get related evidence using metadata-based matching via the get_evidence method.
        """
        evidence = obj.get_evidence()
        return ESGMetricEvidenceSerializer(evidence, many=True, context=self.context).data

    def validate_basic_data(self, basic_data):
        # logger.info(f"Validating basic_data: {basic_data}")
        if basic_data is not None and not isinstance(basic_data, dict):
            # logger.error(f"basic_data must be a dictionary, got {type(basic_data)}")
            raise serializers.ValidationError("basic_data must be a dictionary.")
        return basic_data

    def validate(self, data):
        # logger.info(f"Validating submission data: {data}")
        metric = data.get('metric')
        assignment = data.get('assignment')
        reporting_period = data.get('reporting_period', None)
        basic_data = data.get('basic_data')
        
        if not metric:
            # logger.error("Metric is required")
            raise serializers.ValidationError("Metric is required.")
        
        # --- BEGIN: Duplicate check (added logic) ---
        is_creating = self.instance is None
        if is_creating:
            if not metric.allow_multiple_submissions_per_period:
                if not assignment:
                    # logger.error("Assignment is required when creating a submission")
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
                    # logger.error(error_msg)
                    raise serializers.ValidationError(error_msg)
        
        # --- Check data payload presence and type match --- 
        provided_data_fields = [
            f for f in [
                'basic_data', 'tabular_rows', 'material_data_points', 
                'timeseries_data_points', 'multifield_timeseries_data_points', 'multifield_data',
                'vehicle_records', 'fuel_records', 'checklist_responses'  # Add checklist_responses to valid data fields
            ] if data.get(f) is not None
        ]
        
        # logger.info(f"Provided data fields: {provided_data_fields}")
        
        if not provided_data_fields:
            # Special case for VehicleTrackingMetric - if we're submitting for a vehicle tracking metric
            # and there's no error yet, don't raise an error about missing data fields
            if not is_creating or (not isinstance(metric, VehicleTrackingMetric) and not isinstance(metric, ChecklistMetric)) or \
               ('vehicle_records' not in data and 'checklist_responses' not in data):
                # logger.error("No submission data provided")
                raise serializers.ValidationError("No submission data provided (e.g., basic_data, tabular_rows, etc.).")
        
        # For BasicMetric, we expect basic_data
        if isinstance(metric, BasicMetric) and 'basic_data' not in provided_data_fields:
            # logger.error("Basic metric requires basic_data")
            raise serializers.ValidationError(f"Metric of type BasicMetric requires 'basic_data' field, got {provided_data_fields}.")
        
        # Ensure only one type of data is provided (except vehicle_records can be combined)
        data_without_vehicle = [f for f in provided_data_fields if f != 'vehicle_records' and f != 'checklist_responses']
        if len(data_without_vehicle) > 1:
            # logger.error(f"Multiple data fields provided: {data_without_vehicle}")
            raise serializers.ValidationError("Multiple types of submission data provided. Only one is allowed.")
        
        # Only perform type match check if a data field was actually provided
        if provided_data_fields:
            provided_field = provided_data_fields[0]
            
            try:
                specific_metric = metric.get_real_instance()
                # logger.info(f"Got specific metric type: {type(specific_metric).__name__}")
            except AttributeError:
                # logger.error("Could not determine specific metric type")
                raise serializers.ValidationError("Could not determine specific metric type.")

            expected_field_map = {
                BasicMetric: 'basic_data',
                TabularMetric: 'tabular_rows',
                MaterialTrackingMatrixMetric: 'material_data_points',
                TimeSeriesMetric: 'timeseries_data_points',
                MultiFieldTimeSeriesMetric: 'multifield_timeseries_data_points',
                MultiFieldMetric: 'multifield_data',
                VehicleTrackingMetric: 'vehicle_records',
                FuelConsumptionMetric: 'fuel_records',  # Add mapping for FuelConsumptionMetric
                ChecklistMetric: 'checklist_responses',  # Add mapping for ChecklistMetric
            }

            expected_field = None
            for model_class, field_name in expected_field_map.items():
                if isinstance(specific_metric, model_class):
                    expected_field = field_name
                    break
            
            if not expected_field:
                # logger.error(f"Unsupported metric type: {type(specific_metric).__name__}")
                raise serializers.ValidationError(f"Unsupported metric type encountered: {type(specific_metric).__name__}")

            # Skip field validation for VehicleTrackingMetric since we handle it specially
            if isinstance(specific_metric, VehicleTrackingMetric):
                # logger.info(f"Found VehicleTrackingMetric with vehicle_records data")
                pass  # Skip the field validation
            # Skip field validation for ChecklistMetric since we handle it similarly
            elif isinstance(specific_metric, ChecklistMetric):
                # logger.info(f"Found ChecklistMetric with checklist_responses data")
                pass  # Skip the field validation
            elif provided_field != expected_field:
                error_msg = f"Invalid data field '{provided_field}' provided for metric type '{type(specific_metric).__name__}'. Expected field: '{expected_field}'."
                # logger.error(error_msg)
                raise serializers.ValidationError(error_msg)

            # --- Metric Type-Specific Validation ---
            if isinstance(specific_metric, BasicMetric):
                if basic_data is None:
                    # logger.error("basic_data is required for BasicMetric")
                    raise serializers.ValidationError({"basic_data": "basic_data is required for BasicMetric."})
                
                unit_type = specific_metric.unit_type
                value_numeric = basic_data.get('value_numeric')
                value_text = basic_data.get('value_text')
                
                # logger.info(f"Validating BasicMetric data - unit_type: {unit_type}, value_numeric: {value_numeric}, value_text: {value_text}")

                if unit_type == 'text':
                    if value_numeric is not None:
                        # logger.error("Numeric value provided for text metric")
                        raise serializers.ValidationError({"basic_data": "Numeric value should not be provided for a text metric."})
                    if not value_text:
                        # logger.error("Text value required for text metric")
                        raise serializers.ValidationError({"basic_data": "Text value is required for a text metric."})
                else:
                    if value_text is not None and value_text != "":
                        # logger.error("Text value provided for non-text metric")
                        raise serializers.ValidationError({"basic_data": "Text value should not be provided for a non-text metric."})
                    if value_numeric is None:
                        # logger.error("Numeric value required for non-text metric")
                        raise serializers.ValidationError({"basic_data": "Numeric value is required for a non-text metric."})
                    
                    rules = specific_metric.validation_rules or {}
                    if 'min' in rules and value_numeric < rules['min']:
                        # logger.error(f"Value {value_numeric} below minimum {rules['min']}")
                        raise serializers.ValidationError({"basic_data": f"Value must be at least {rules['min']}."})
                    if 'max' in rules and value_numeric > rules['max']:
                        # logger.error(f"Value {value_numeric} above maximum {rules['max']}")
                        raise serializers.ValidationError({"basic_data": f"Value must not exceed {rules['max']}."})

        # logger.info("Validation successful")
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
        
        # Extract nested vehicle and fuel data if present
        vehicle_records_data = validated_data.pop('vehicle_records', None)
        fuel_records_data = validated_data.pop('fuel_records', None)  # Extract fuel records data
        
        # Extract checklist responses if present
        checklist_responses_data = validated_data.pop('checklist_responses', None)
        
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
        
        # Handle fuel_records nested creation
        if fuel_records_data is not None:
            self._save_fuel_records(submission, fuel_records_data)
        
        # Handle checklist responses if provided
        if checklist_responses_data:
            self._save_checklist_responses(submission, checklist_responses_data)
        
        return submission
        
    def update(self, instance, validated_data):
        """Update existing submission with related nested data."""
        # Extract nested data
        basic_data = validated_data.pop('basic_data', None)
        tabular_rows = validated_data.pop('tabular_rows', None)
        material_data_points = validated_data.pop('material_data_points', None)
        timeseries_data_points = validated_data.pop('timeseries_data_points', None)
        multifield_timeseries_data_points = validated_data.pop('multifield_timeseries_data_points', None)
        multifield_data = validated_data.pop('multifield_data', None)
        
        # Extract nested vehicle and fuel data if present
        vehicle_records_data = validated_data.pop('vehicle_records', None)
        fuel_records_data = validated_data.pop('fuel_records', None)  # Extract fuel records data
        
        # Extract checklist responses if present
        checklist_responses_data = validated_data.pop('checklist_responses', None)
        
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
        
        # Handle fuel_records nested update
        if fuel_records_data is not None:
            self._save_fuel_records(instance, fuel_records_data, update=True)
        
        # Handle checklist responses if provided (update mode)
        if checklist_responses_data is not None:
            self._save_checklist_responses(instance, checklist_responses_data, update=True)
        
        return instance

    def _save_vehicle_records(self, submission_instance, vehicle_records_data, update=False):
        from ..models.submission_data import VehicleRecord, VehicleMonthlyData
        logger.info(f"[DEBUG] _save_vehicle_records called for submission {submission_instance.id}, update={update}")
        logger.info(f"[DEBUG] Incoming vehicle_records_data: {vehicle_records_data}")
        # For update, keep track of IDs to retain
        keep_vehicle_ids = []
        for vehicle_data in vehicle_records_data:
            monthly_data = vehicle_data.pop('monthly_data', [])
            vehicle_id = vehicle_data.get('id', None)
            if update and vehicle_id:
                # Add debug log before lookup
                logger.info(f"Looking for VehicleRecord with id={vehicle_id} and submission_id={submission_instance.id}")
                # Update existing vehicle record
                try:
                    vehicle_obj = VehicleRecord.objects.get(id=vehicle_id, submission=submission_instance)
                    logger.info(f"[DEBUG] Updating VehicleRecord id={vehicle_id} for submission {submission_instance.id}")
                    for attr, value in vehicle_data.items():
                        setattr(vehicle_obj, attr, value)
                    vehicle_obj.save()
                except VehicleRecord.DoesNotExist:
                    logger.warning(f"[DEBUG] VehicleRecord id={vehicle_id} not found for submission {submission_instance.id}, creating new.")
                    vehicle_obj = VehicleRecord.objects.create(submission=submission_instance, **vehicle_data)
            else:
                logger.info(f"[DEBUG] Creating new VehicleRecord for submission {submission_instance.id} (no id or not update mode)")
                vehicle_obj = VehicleRecord.objects.create(submission=submission_instance, **vehicle_data)
            keep_vehicle_ids.append(vehicle_obj.id)

            # Initialize keep_monthly_ids for the current vehicle
            keep_monthly_ids = []

            # Process monthly data
            for month_data in monthly_data:
                month_id = month_data.get('id')
                period = month_data.get('period')
                kilometers = month_data.get('kilometers')
                fuel_consumed = month_data.get('fuel_consumed')

                if month_id:
                    # Update existing monthly data
                    try:
                        month_obj = VehicleMonthlyData.objects.get(id=month_id, vehicle=vehicle_obj)
                        # Update fields
                        month_obj.period = period
                        month_obj.kilometers = kilometers
                        month_obj.fuel_consumed = fuel_consumed
                        # TODO: Add other fields? emission_calculated, emission_value etc?
                        month_obj.save()
                        keep_monthly_ids.append(month_id)
                    except VehicleMonthlyData.DoesNotExist:
                        logger.warning(f"VehicleMonthlyData with id {month_id} for vehicle {vehicle_obj.id} not found during update.")
                        # Optionally create it if missing? Or just skip? Skipping for now.
                        pass # Or raise an error?
                else:
                    # Create new monthly data
                    month_obj = VehicleMonthlyData.objects.create(
                        vehicle=vehicle_obj,
                        period=period,
                        kilometers=kilometers,
                        fuel_consumed=fuel_consumed
                        # TODO: Add other fields?
                    )
                    # --- FIX STARTS HERE ---
                    # Add the newly created object's ID to the keep list
                    keep_monthly_ids.append(month_obj.id)
                    # --- FIX ENDS HERE ---

            # Monthly data cleanup (only if updating the submission)
            if update:
                # Find monthly data linked to this vehicle in DB but NOT in the keep list
                deleted_months = VehicleMonthlyData.objects.filter(
                    vehicle=vehicle_obj).exclude(id__in=keep_monthly_ids)
                if deleted_months.exists():
                    count = deleted_months.count()
                    logger.info(f"Deleting {count} orphaned VehicleMonthlyData records for vehicle {vehicle_obj.id} (IDs not in {keep_monthly_ids}): {list(deleted_months.values_list('id', flat=True))}")
                    deleted_months.delete()

        # Vehicle record cleanup (only if updating the submission)
        if update:
            # Find vehicle records linked to this submission but NOT in the keep list
            deleted_vehicles = VehicleRecord.objects.filter(
                submission=submission_instance).exclude(id__in=keep_vehicle_ids)
            if deleted_vehicles.exists():
                count = deleted_vehicles.count()
                logger.info(f"Deleting {count} orphaned VehicleRecord records for submission {submission_instance.id} (IDs not in {keep_vehicle_ids}): {list(deleted_vehicles.values_list('id', flat=True))}")
                deleted_vehicles.delete()

        return submission_instance # Return the updated submission instance

    # Add method to save fuel records
    def _save_fuel_records(self, submission_instance, fuel_records_data, update=False):
        from ..models.submission_data import FuelRecord, FuelMonthlyData
        logger.info(f"[DEBUG] _save_fuel_records called for submission {submission_instance.id}, update={update}")
        
        # For update, keep track of IDs to retain
        keep_source_ids = []
        for source_data in fuel_records_data:
            monthly_data = source_data.pop('monthly_data', [])
            source_id = source_data.get('id', None)
            if update and source_id:
                # Update existing fuel record
                try:
                    source_obj = FuelRecord.objects.get(id=source_id, submission=submission_instance)
                    logger.info(f"[DEBUG] Updating FuelRecord id={source_id} for submission {submission_instance.id}")
                    for attr, value in source_data.items():
                        setattr(source_obj, attr, value)
                    source_obj.save()
                except FuelRecord.DoesNotExist:
                    logger.warning(f"[DEBUG] FuelRecord id={source_id} not found for submission {submission_instance.id}, creating new.")
                    source_obj = FuelRecord.objects.create(submission=submission_instance, **source_data)
            else:
                logger.info(f"[DEBUG] Creating new FuelRecord for submission {submission_instance.id} (no id or not update mode)")
                source_obj = FuelRecord.objects.create(submission=submission_instance, **source_data)
            keep_source_ids.append(source_obj.id)

            # Handle monthly_data for this source
            keep_monthly_ids = []
            for month_data in monthly_data:
                month_id = month_data.get('id', None)
                if update and month_id:
                    try:
                        month_obj = FuelMonthlyData.objects.get(id=month_id, source=source_obj)
                        logger.info(f"[DEBUG] Updating FuelMonthlyData id={month_id} for source {source_obj.id}")
                        for attr, value in month_data.items():
                            setattr(month_obj, attr, value)
                        month_obj.save()
                    except FuelMonthlyData.DoesNotExist:
                        logger.warning(f"[DEBUG] FuelMonthlyData id={month_id} not found for source {source_obj.id}, creating new.")
                        month_obj = FuelMonthlyData.objects.create(source=source_obj, **month_data)
                    # --- FIX STARTS HERE ---
                    # Add the newly created object's ID to the keep list
                    keep_monthly_ids.append(month_obj.id)
                    # --- FIX ENDS HERE ---
                else:
                    logger.info(f"[DEBUG] Creating new FuelMonthlyData for source {source_obj.id}")
                    month_obj = FuelMonthlyData.objects.create(source=source_obj, **month_data)
                    # --- FIX STARTS HERE ---
                    # Add the newly created object's ID to the keep list
                    keep_monthly_ids.append(month_obj.id)
                    # --- FIX ENDS HERE ---

            # Delete monthly data not in keep list (for update)
            if update:
                deleted_months = FuelMonthlyData.objects.filter(source=source_obj).exclude(id__in=keep_monthly_ids)
                logger.info(f"[DEBUG] Deleting FuelMonthlyData ids={[m.id for m in deleted_months]} for source {source_obj.id}")
                deleted_months.delete()
        # Delete fuel records not in keep list (for update)
        if update:
            sources_to_delete = FuelRecord.objects.filter(submission=submission_instance).exclude(id__in=keep_source_ids)
            logger.info(f"[DEBUG] Deleting FuelRecord ids={[v.id for v in sources_to_delete]} for submission {submission_instance.id}")
            sources_to_delete.delete()

    def _save_checklist_responses(self, submission_instance, checklist_responses_data, update=False):
        """Create or update checklist responses for a submission."""
        from ..models.submission_data import ChecklistResponse
        
        logger.info(f"_save_checklist_responses called for submission {submission_instance.id}, update={update}")
        
        # For update, keep track of IDs to retain
        keep_response_ids = []
        
        for response_data in checklist_responses_data:
            response_id = response_data.get('id', None)
            category_id = response_data.get('category_id')
            item_id = response_data.get('item_id')
            
            logger.info(f"Processing response: category_id={category_id}, item_id={item_id}, has_id={response_id is not None}")
            
            # First try to find an existing response
            response_obj = None
            
            # Try to find by ID if provided
            if update and response_id:
                try:
                    response_obj = ChecklistResponse.objects.get(id=response_id, submission=submission_instance)
                    logger.info(f"Found existing response by ID: {response_id}")
                except ChecklistResponse.DoesNotExist:
                    logger.info(f"Response with ID {response_id} not found")
                    response_obj = None
            
            # If not found by ID or ID not provided, try to find by natural key
            if response_obj is None and category_id and item_id:
                try:
                    response_obj = ChecklistResponse.objects.get(
                        submission=submission_instance,
                        category_id=category_id,
                        item_id=item_id
                    )
                    logger.info(f"Found existing response by natural key: category_id={category_id}, item_id={item_id}")
                except ChecklistResponse.DoesNotExist:
                    logger.info(f"No existing response found for category_id={category_id}, item_id={item_id}")
                    response_obj = None
            
            # Update existing response or create new one
            if response_obj:
                # Update existing response
                for attr, value in response_data.items():
                    if attr != 'id':  # Skip updating the ID field
                        setattr(response_obj, attr, value)
                response_obj.save()
                logger.info(f"Updated existing response (ID: {response_obj.id})")
            else:
                # Create new response
                response_obj = ChecklistResponse.objects.create(submission=submission_instance, **response_data)
                logger.info(f"Created new response (ID: {response_obj.id})")
                
            keep_response_ids.append(response_obj.id)
            
        # Clean up responses that weren't in the update
        if update:
            deleted_responses = ChecklistResponse.objects.filter(
                submission=submission_instance).exclude(id__in=keep_response_ids)
            if deleted_responses.exists():
                count = deleted_responses.count()
                ids = list(deleted_responses.values_list('id', flat=True))
                logger.info(f"Deleting {count} orphaned ChecklistResponse records: {ids}")
                deleted_responses.delete()

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
                # logger.error(f"Submission {index} missing metric field")
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