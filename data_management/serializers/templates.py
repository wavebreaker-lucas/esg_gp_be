from rest_framework import serializers
from accounts.models import CustomUser, LayerProfile
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
    TimeSeriesMetric, MultiFieldTimeSeriesMetric, MultiFieldMetric # Import specific types
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
    PolymorphicSubmissionDataSerializer # Import the new polymorphic reader
)

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
    """Serializer for ESG forms with nested metrics"""
    # metrics = ESGMetricSerializer(many=True, read_only=True) # Commented out: Needs Polymorphic relation
    category = ESGFormCategorySerializer(read_only=True)
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=ESGFormCategory.objects.all(),
        write_only=True,
        source='category'
    )

    class Meta:
        model = ESGForm
        # Removed 'metrics' from fields
        fields = ['id', 'code', 'name', 'description', 'is_active', 'category', 'category_id', 'order']
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

class TemplateAssignmentSerializer(serializers.ModelSerializer):
    template = TemplateSerializer(read_only=True)
    template_id = serializers.PrimaryKeyRelatedField(queryset=Template.objects.all(), write_only=True)
    layer = serializers.PrimaryKeyRelatedField(queryset=LayerProfile.objects.all())
    assigned_to = serializers.PrimaryKeyRelatedField(queryset=CustomUser.objects.all(), required=False, allow_null=True)

    class Meta:
        model = TemplateAssignment
        fields = '__all__'
        
    def create(self, validated_data):
        template = validated_data.pop('template_id')
        validated_data['template'] = template
        return super().create(validated_data)

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
            'edited_by', 'edited_by_name', 'submission', 'intended_metric', # Added intended_metric
            'layer_id', 'layer_name'
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
    evidence = ESGMetricEvidenceSerializer(many=True, read_only=True)
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
        
        if data_to_serialize is not None:
            # Use the Polymorphic serializer to render the correct structure
            serializer = PolymorphicSubmissionDataSerializer(data_to_serialize, **serializer_kwargs)
            return serializer.data
        
        return None # Return None if no data found or metric type unhandled

    def validate(self, data):
        """Validate submission based on metric type and ensures only one data field is present."""
        metric = data.get('metric')
        if not metric:
            # This should be caught by the PrimaryKeyRelatedField, but double-check
            raise serializers.ValidationError("Metric is required.")
        
        # Check which data field is provided and if it matches the metric type
        provided_data_fields = [
            f for f in [
                'basic_data', 'tabular_rows', 'material_data_points', 
                'timeseries_data_points', 'multifield_timeseries_data_points', 'multifield_data'
            ] if data.get(f) is not None
        ]
        
        if len(provided_data_fields) == 0:
            raise serializers.ValidationError("No submission data provided (e.g., basic_data, tabular_rows, etc.).")
        if len(provided_data_fields) > 1:
            raise serializers.ValidationError("Multiple types of submission data provided. Only one is allowed.")
            
        provided_field = provided_data_fields[0]
        metric_instance = metric # Already fetched by PrimaryKeyRelatedField
        
        # --- Type Checking Logic --- 
        # Fetch the actual subclass instance to check its type
        # This ensures we are checking against the specific metric type (Basic, Tabular, etc.)
        try:
            specific_metric = metric_instance.get_real_instance()
        except AttributeError:
             # Should not happen if using BaseESGMetric queryset correctly, but safeguard
             raise serializers.ValidationError("Could not determine specific metric type.")

        expected_field_map = {
            BasicMetric: 'basic_data',
            TabularMetric: 'tabular_rows',
            MaterialTrackingMatrixMetric: 'material_data_points',
            TimeSeriesMetric: 'timeseries_data_points',
            MultiFieldTimeSeriesMetric: 'multifield_timeseries_data_points',
            MultiFieldMetric: 'multifield_data',
        }

        expected_field = None
        for model_class, field_name in expected_field_map.items():
            if isinstance(specific_metric, model_class):
                expected_field = field_name
                break
        
        if not expected_field:
             raise serializers.ValidationError(f"Unsupported metric type encountered: {type(specific_metric).__name__}")

        if provided_field != expected_field:
            raise serializers.ValidationError(
                f"Invalid data field '{provided_field}' provided for metric type '{type(specific_metric).__name__}'. "
                f"Expected field: '{expected_field}'."
            )

        # Detailed validation is now handled by validate_<field> methods
        
        return data

    # --- Field-specific validation methods ---

    def _get_specific_metric(self):
        """Helper to get the specific metric instance based on initial data."""
        metric_id = self.initial_data.get('metric')
        if not metric_id:
            # Should have been caught earlier, but safeguard
            return None 
        try:
            # Fetch the base metric first
            base_metric = BaseESGMetric.objects.get(pk=metric_id)
            # Get the actual subclass instance
            return base_metric.get_real_instance()
        except (BaseESGMetric.DoesNotExist, AttributeError):
            # Raise validation error if metric not found or type determination fails
            raise serializers.ValidationError({'metric': f"Metric with ID {metric_id} not found or invalid."}) 

    def validate_basic_data(self, basic_data):
        """Validate data for BasicMetric."""
        if not basic_data: # Don't validate if field wasn't provided
            return basic_data 
            
        metric = self._get_specific_metric()
        if not isinstance(metric, BasicMetric):
            # This case should be prevented by the main validate method, but good practice to check
            # Or, alternatively, just return basic_data if the type doesn't match
            return basic_data # Ignore if not relevant type

        # --- BasicMetric specific checks ---
        unit_type = metric.unit_type
        value_numeric = basic_data.get('value_numeric')
        value_text = basic_data.get('value_text')

        if unit_type == 'text':
            if value_numeric is not None:
                raise serializers.ValidationError({'basic_data': "Numeric value should not be provided for a text metric."}) 
            if not value_text:
                 raise serializers.ValidationError({'basic_data': "Text value is required for a text metric."}) 
        else: # Numeric, percentage, count, custom unit etc.
            if value_text is not None and value_text != "":
                raise serializers.ValidationError({'basic_data': "Text value should not be provided for a non-text metric."}) 
            if value_numeric is None:
                 raise serializers.ValidationError({'basic_data': "Numeric value is required for a non-text metric."}) 
            
            # Add optional min/max checks based on metric.validation_rules if needed
            rules = metric.validation_rules or {}
            if 'min' in rules and value_numeric < rules['min']:
                raise serializers.ValidationError({'basic_data': f"Value must be at least {rules['min']}."})
            if 'max' in rules and value_numeric > rules['max']:
                raise serializers.ValidationError({'basic_data': f"Value must not exceed {rules['max']}."})

        return basic_data

    def validate_tabular_rows(self, tabular_rows):
        """Validate data for TabularMetric."""
        if not tabular_rows: # Don't validate if field wasn't provided
            return tabular_rows
            
        metric = self._get_specific_metric()
        if not isinstance(metric, TabularMetric):
            return tabular_rows # Ignore if not relevant type

        # --- TabularMetric specific checks ---
        if not isinstance(metric.column_definitions, list):
             raise serializers.ValidationError("Invalid column definitions for the metric.") # Internal config error
        
        defined_keys = {col.get('key') for col in metric.column_definitions if col.get('key')}
        required_keys = {col.get('key') for col in metric.column_definitions if col.get('required') and col.get('key')}

        if metric.min_rows and len(tabular_rows) < metric.min_rows:
             raise serializers.ValidationError(f"At least {metric.min_rows} row(s) are required.")
        if metric.max_rows and len(tabular_rows) > metric.max_rows:
             raise serializers.ValidationError(f"No more than {metric.max_rows} row(s) are allowed.")

        validated_rows = []
        for index, row in enumerate(tabular_rows):
            row_data = row.get('row_data')
            if not isinstance(row_data, dict):
                 raise serializers.ValidationError({f'tabular_rows[{index}]': "row_data must be an object/dictionary."}) 
            
            submitted_keys = set(row_data.keys())
            
            # Check for missing required keys
            missing_required = required_keys - submitted_keys
            if missing_required:
                raise serializers.ValidationError({f'tabular_rows[{index}]': f"Missing required fields: {', '.join(missing_required)}."}) 
                
            # Check for unexpected keys
            unexpected_keys = submitted_keys - defined_keys
            if unexpected_keys:
                 raise serializers.ValidationError({f'tabular_rows[{index}]': f"Unexpected fields provided: {', '.join(unexpected_keys)}."}) 
            
            # TODO: Add type validation based on column_definitions (e.g., check if numeric field is number)
            
            # Ensure row_index is provided if creating/updating rows via serializer directly (might not be needed if handled in create/update)
            # if 'row_index' not in row:
            #      raise serializers.ValidationError({f'tabular_rows[{index}]': "row_index is required."}) 

            validated_rows.append(row) # Append original row data for now
            
        return validated_rows # Return the list of validated row data

    # --- Placeholder validation methods for other types (Implement as needed) ---

    def validate_material_data_points(self, data):
        if not data: return data
        metric = self._get_specific_metric()
        if not isinstance(metric, MaterialTrackingMatrixMetric): return data
        # TODO: Implement validation for MaterialTrackingMatrixMetric
        # - Check material_type, period, value, unit based on metric definition
        # - Check against max_material_types?
        return data

    def validate_timeseries_data_points(self, data):
        if not data: return data
        metric = self._get_specific_metric()
        if not isinstance(metric, TimeSeriesMetric): return data
        # TODO: Implement validation for TimeSeriesMetric
        # - Check period (uniqueness? frequency?), value
        return data

    def validate_multifield_timeseries_data_points(self, data):
        if not data: return data
        metric = self._get_specific_metric()
        if not isinstance(metric, MultiFieldTimeSeriesMetric): return data
        # TODO: Implement validation for MultiFieldTimeSeriesMetric
        # - Check period, field_data keys against field_definitions
        # - Validate field data types
        return data

    def validate_multifield_data(self, data):
        if not data: return data
        metric = self._get_specific_metric()
        if not isinstance(metric, MultiFieldMetric): return data
        # TODO: Implement validation for MultiFieldMetric
        # - Check field_data keys against field_definitions
        # - Validate field data types
        return data

    # --- Create / Update Methods --- 

    def create(self, validated_data):
        """Create the submission header and associated specific data."""
        # Pop specific data fields
        basic_data_payload = validated_data.pop('basic_data', None)
        tabular_rows_payload = validated_data.pop('tabular_rows', None)
        material_data_points_payload = validated_data.pop('material_data_points', None)
        timeseries_data_points_payload = validated_data.pop('timeseries_data_points', None)
        multifield_timeseries_data_points_payload = validated_data.pop('multifield_timeseries_data_points', None)
        multifield_data_payload = validated_data.pop('multifield_data', None)
        
        # Set submitted_by from context
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            validated_data['submitted_by'] = request.user
            
        # Create the main submission header
        submission = ESGMetricSubmission.objects.create(**validated_data)
        
        # Get the specific metric instance
        metric = submission.metric.get_real_instance()

        # Create the associated specific data based on metric type
        # (Error handling for missing data should be covered by validate method)
        if isinstance(metric, BasicMetric) and basic_data_payload:
            BasicMetricData.objects.create(submission=submission, **basic_data_payload)
        elif isinstance(metric, TabularMetric) and tabular_rows_payload:
            for row_data in tabular_rows_payload:
                TabularMetricRow.objects.create(submission=submission, **row_data)
        elif isinstance(metric, MaterialTrackingMatrixMetric) and material_data_points_payload:
            for point_data in material_data_points_payload:
                 MaterialMatrixDataPoint.objects.create(submission=submission, **point_data)
        elif isinstance(metric, TimeSeriesMetric) and timeseries_data_points_payload:
            for point_data in timeseries_data_points_payload:
                TimeSeriesDataPoint.objects.create(submission=submission, **point_data)
        elif isinstance(metric, MultiFieldTimeSeriesMetric) and multifield_timeseries_data_points_payload:
            for point_data in multifield_timeseries_data_points_payload:
                MultiFieldTimeSeriesDataPoint.objects.create(submission=submission, **point_data)
        elif isinstance(metric, MultiFieldMetric) and multifield_data_payload:
            MultiFieldDataPoint.objects.create(submission=submission, **multifield_data_payload)
        else:
            # This case should ideally be prevented by the validate method
            # Consider logging an error or raising an exception if it occurs
            print(f"Warning: Metric type {type(metric).__name__} matched but no corresponding payload found for submission {submission.pk}")
            # raise serializers.ValidationError("Mismatch between metric type and provided data payload during creation.")

        return submission

    def update(self, instance, validated_data):
        """Update the submission header and associated specific data."""
        # Pop specific data fields - we'll handle updates based on what's provided
        basic_data_payload = validated_data.pop('basic_data', None)
        tabular_rows_payload = validated_data.pop('tabular_rows', None)
        material_data_points_payload = validated_data.pop('material_data_points', None)
        timeseries_data_points_payload = validated_data.pop('timeseries_data_points', None)
        multifield_timeseries_data_points_payload = validated_data.pop('multifield_timeseries_data_points', None)
        multifield_data_payload = validated_data.pop('multifield_data', None)

        # Update the main submission header fields
        # Note: metric and assignment typically shouldn't change on update
        instance.notes = validated_data.get('notes', instance.notes)
        instance.reporting_period = validated_data.get('reporting_period', instance.reporting_period)
        instance.source_identifier = validated_data.get('source_identifier', instance.source_identifier)
        instance.layer = validated_data.get('layer', instance.layer)
        # submitted_by and metric usually don't change
        # Verification fields are handled separately
        instance.save()
        
        # Get the specific metric instance
        metric = instance.metric.get_real_instance()

        # --- Update/Replace the associated specific data --- 
        # This logic assumes a full replacement of the related data on PUT/PATCH
        # More granular updates (e.g., adding/deleting single tabular rows) would require more complex logic.

        if isinstance(metric, BasicMetric) and basic_data_payload:
            BasicMetricData.objects.update_or_create(
                submission=instance,
                defaults=basic_data_payload
            )
        elif isinstance(metric, TabularMetric) and tabular_rows_payload:
            # Full replacement: Delete existing rows, create new ones
            instance.tabular_rows.all().delete()
            for row_data in tabular_rows_payload:
                TabularMetricRow.objects.create(submission=instance, **row_data)
        elif isinstance(metric, MaterialTrackingMatrixMetric) and material_data_points_payload:
            instance.material_data_points.all().delete()
            for point_data in material_data_points_payload:
                 MaterialMatrixDataPoint.objects.create(submission=instance, **point_data)
        elif isinstance(metric, TimeSeriesMetric) and timeseries_data_points_payload:
            instance.timeseries_data_points.all().delete()
            for point_data in timeseries_data_points_payload:
                TimeSeriesDataPoint.objects.create(submission=instance, **point_data)
        elif isinstance(metric, MultiFieldTimeSeriesMetric) and multifield_timeseries_data_points_payload:
            instance.multifield_timeseries_data_points.all().delete()
            for point_data in multifield_timeseries_data_points_payload:
                MultiFieldTimeSeriesDataPoint.objects.create(submission=instance, **point_data)
        elif isinstance(metric, MultiFieldMetric) and multifield_data_payload:
            MultiFieldDataPoint.objects.update_or_create(
                 submission=instance,
                 defaults=multifield_data_payload
             )
        # No else needed here, as validate ensures the correct data type is present if *any* data is provided.
        # If no specific data payload is provided in the update, we don't modify the specific data.

        return instance

# class ESGMetricSubmissionCreateSerializer(ESGMetricSubmissionSerializer):
#     """Serializer for creating ESG metric submissions - NEEDS REVISITING"""
#     # This logic assumed specific fields - needs updating for polymorphic submissions
#     class Meta(ESGMetricSubmissionSerializer.Meta):
#         pass
#     
#     def create(self, validated_data):
#         request = self.context.get('request')
#         if request and hasattr(request, 'user'):
#             validated_data['submitted_by'] = request.user
#         
#         # Update-or-create logic might need rethinking
#         try:
#             submission = ESGMetricSubmission.objects.get(
#                 assignment=validated_data['assignment'],
#                 metric=validated_data['metric']
#                 # Need to consider reporting_period for time series?
#             )
#             for attr, value in validated_data.items():
#                 setattr(submission, attr, value)
#             submission.save()
#             return submission
#         except ESGMetricSubmission.DoesNotExist:
#             return super().create(validated_data)

# class ESGMetricBatchSubmissionSerializer(serializers.Serializer):
#     """Serializer for batch submission of multiple metrics - NEEDS MAJOR REWRITE"""
#     assignment_id = serializers.IntegerField()
#     submissions = serializers.ListField(
#         child=serializers.DictField()
#     )
#     
#     def validate(self, data):
#         # Validation heavily relied on old structure - comment out for now
#         pass
#         # from ..models import TemplateAssignment, ESGMetricSubmission, BaseESGMetric
#         # ... existing validation logic removed ...
#         return data

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
# ----------------------------------