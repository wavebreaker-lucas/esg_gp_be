from rest_framework import serializers
from accounts.models import CustomUser, LayerProfile
from ..models import (
    ESGFormCategory, ESGForm, ESGMetric,
    Template, TemplateFormSelection, TemplateAssignment,
    ESGMetricSubmission, ESGMetricEvidence, MetricValueField, MetricValue,
    ReportedMetricValue, ReportedMetricFieldValue
)

class ESGMetricSerializer(serializers.ModelSerializer):
    """Serializer for ESG metrics"""
    form_id = serializers.PrimaryKeyRelatedField(
        queryset=ESGForm.objects.all(),
        write_only=True,
        source='form',
        required=False
    )
    
    class Meta:
        model = ESGMetric
        fields = ['id', 'name', 'description', 'unit_type', 'custom_unit', 
                 'requires_evidence', 'order', 'validation_rules', 'location', 'is_required',
                 'requires_time_reporting', 'reporting_frequency', 'is_multi_value', 'aggregates_inputs',
                 'form_id']
        read_only_fields = ['id']

class ESGFormCategorySerializer(serializers.ModelSerializer):
    """Serializer for ESG form categories"""
    class Meta:
        model = ESGFormCategory
        fields = ['id', 'name', 'code', 'icon', 'order']

class ESGFormSerializer(serializers.ModelSerializer):
    """Serializer for ESG forms with nested metrics"""
    metrics = ESGMetricSerializer(many=True, read_only=True)
    category = ESGFormCategorySerializer(read_only=True)
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=ESGFormCategory.objects.all(),
        write_only=True,
        source='category'
    )

    class Meta:
        model = ESGForm
        fields = ['id', 'code', 'name', 'description', 'is_active', 'metrics', 'category', 'category_id', 'order']
        read_only_fields = ['id']

    def create(self, validated_data):
        """Create a new ESG form"""
        # Just create the form, don't auto-create metrics
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
        fields = [
            'id', 'file', 'filename', 'file_type', 
            'uploaded_by', 'uploaded_by_name', 'uploaded_at', 'description',
            'enable_ocr_processing', 'is_processed_by_ocr', 'extracted_value', 
            'period', 'was_manually_edited', 'edited_at', 
            'edited_by', 'edited_by_name', 'submission', 'layer_id', 'layer_name'
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

class MetricValueFieldSerializer(serializers.ModelSerializer):
    """Serializer for metric value fields (components of multi-value metrics)"""
    
    class Meta:
        model = MetricValueField
        fields = [
            'id', 'metric', 'field_key', 'display_name', 'description',
            'column_header', 'display_type', 'order', 'options', 'is_required'
        ]
        read_only_fields = ['id']

class MetricValueSerializer(serializers.ModelSerializer):
    """Serializer for individual values within a multi-value metric submission input"""
    field_name = serializers.SerializerMethodField()
    field_key = serializers.SerializerMethodField()
    
    class Meta:
        model = MetricValue
        fields = [
            'id', 'field', 'field_name', 'field_key', 'numeric_value', 'text_value'
        ]
        read_only_fields = ['id']
    
    def get_field_name(self, obj):
        return obj.field.display_name
        
    def get_field_key(self, obj):
        return obj.field.field_key

class ESGMetricSubmissionSerializer(serializers.ModelSerializer):
    """Serializer for ESG metric submission inputs (raw data)."""
    evidence = ESGMetricEvidenceSerializer(many=True, read_only=True)
    metric_name = serializers.SerializerMethodField()
    metric_unit = serializers.SerializerMethodField()
    submitted_by_name = serializers.SerializerMethodField()
    verified_by_name = serializers.SerializerMethodField()
    layer_id = serializers.PrimaryKeyRelatedField(
        source='layer',
        queryset=LayerProfile.objects.all(),
        required=False,
        allow_null=True
    )
    layer_name = serializers.SerializerMethodField()
    is_multi_value = serializers.SerializerMethodField()
    multi_values = MetricValueSerializer(many=True, read_only=True)
    
    class Meta:
        model = ESGMetricSubmission
        fields = [
            'id', 'assignment', 'metric', 'metric_name', 'metric_unit',
            'value', 'text_value', 'reporting_period', 'submitted_by', 'submitted_by_name',
            'submitted_at', 'updated_at', 'notes', 
            'is_verified', 'verified_by', 'verified_by_name', 'verified_at', 'verification_notes', 
            'evidence', 'layer_id', 'layer_name',
            'is_multi_value', 'multi_values',
        ]
        read_only_fields = [
            'id',
            'submitted_by', 'submitted_at', 'updated_at', 
            'layer_name', 
        ]
    
    def get_metric_name(self, obj):
        return obj.metric.name
    
    def get_metric_unit(self, obj):
        if obj.metric.unit_type == 'custom':
            return obj.metric.custom_unit
        return obj.metric.unit_type
    
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
    
    def get_is_multi_value(self, obj):
        return obj.metric.is_multi_value
    
    def validate(self, data):
        """Basic validation for the input data."""
        metric = data.get('metric')
        value = data.get('value')
        text_value = data.get('text_value')
        
        # Check if numeric metrics have a numeric value (if provided)
        # Allow None for updates where only notes/etc are changed
        numeric_units = ['kWh', 'MWh', 'm3', 'tonnes', 'tCO2e', 'percentage']
        if metric and metric.unit_type in numeric_units and 'value' in data and data['value'] is None:
             # Only raise if 'value' was explicitly passed as None for a numeric metric
            if self.partial and 'value' not in self.initial_data:
                 pass # Allow partial update without value
            else:
                 raise serializers.ValidationError(f"A numeric value is required for {metric.name}, cannot be null.")
        
        # Check if at least one value type is provided on create
        # Allow updates to modify only other fields like notes
        if not self.instance and value is None and not text_value:
            raise serializers.ValidationError("Either a numeric value or text value must be provided for a new submission input.")
        
        return data

class ESGMetricSubmissionCreateSerializer(ESGMetricSubmissionSerializer):
    """Serializer for creating ESG metric submissions with batch support"""
    class Meta(ESGMetricSubmissionSerializer.Meta):
        pass
    
    def create(self, validated_data):
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            validated_data['submitted_by'] = request.user
        
        # Check if submission already exists and update instead
        try:
            submission = ESGMetricSubmission.objects.get(
                assignment=validated_data['assignment'],
                metric=validated_data['metric']
            )
            for attr, value in validated_data.items():
                setattr(submission, attr, value)
            submission.save()
            return submission
        except ESGMetricSubmission.DoesNotExist:
            return super().create(validated_data)

class ESGMetricBatchSubmissionSerializer(serializers.Serializer):
    """Serializer for batch submission of multiple metrics"""
    assignment_id = serializers.IntegerField()
    submissions = serializers.ListField(
        child=serializers.DictField()
    )
    
    def validate(self, data):
        """Validate that the assignment exists and user has access"""
        # Import moved here, was previously from ..models.templates
        # Need ESGMetric as well for validation logic below
        from ..models import TemplateAssignment, ESGMetricSubmission, ESGMetric 
        
        try:
            assignment = TemplateAssignment.objects.get(id=data['assignment_id'])
            self.context['assignment'] = assignment
        except TemplateAssignment.DoesNotExist:
            raise serializers.ValidationError("Template assignment not found")
        
        # Validate each submission has required fields
        for submission in data['submissions']:
            if 'metric_id' not in submission:
                raise serializers.ValidationError("Each submission must include a metric_id")
            
            # Validate metric exists
            try:
                metric = ESGMetric.objects.get(id=submission['metric_id'])
            except ESGMetric.DoesNotExist:
                raise serializers.ValidationError(f"Metric with ID {submission['metric_id']} not found")
            
            # For multi-value metrics, validate multi_values field is provided
            if metric.is_multi_value:
                if 'multi_values' not in submission:
                    raise serializers.ValidationError(f"multi_values field is required for multi-value metric {metric.name}")
                
                multi_values = submission.get('multi_values', {})
                if not isinstance(multi_values, dict):
                    raise serializers.ValidationError(f"multi_values must be a dictionary for metric {metric.name}")
                
                # Check that all required fields have values
                for field in metric.value_fields.filter(is_required=True):
                    if field.field_key not in multi_values:
                        raise serializers.ValidationError(f"Required field '{field.field_key}' missing from multi_values for metric {metric.name}")
            else:
                # Validate regular metrics as before
                numeric_units = ['kWh', 'MWh', 'm3', 'tonnes', 'tCO2e', 'percentage']
                if metric.unit_type in numeric_units and 'value' not in submission:
                    raise serializers.ValidationError(f"A numeric value is required for {metric.name}")
                
                if 'value' not in submission and 'text_value' not in submission:
                    raise serializers.ValidationError(f"Either value or text_value must be provided for {metric.name}")
            
            # Check for duplicate submissions with the same reporting period
            if 'reporting_period' in submission:
                try:
                    existing = ESGMetricSubmission.objects.get(
                        assignment_id=data['assignment_id'],
                        metric_id=submission['metric_id'],
                        reporting_period=submission['reporting_period']
                    )
                    raise serializers.ValidationError(
                        f"A submission for metric ID {submission['metric_id']} with reporting period {submission['reporting_period']} already exists"
                    )
                except ESGMetricSubmission.DoesNotExist:
                    pass
        
        return data

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
        if not (user.is_staff or user.is_superuser or getattr(user, 'is_baker_tilly_admin', False)): 
            raise serializers.ValidationError("Only Baker Tilly admins can verify submissions")
            
        return data

# --- New Serializers for Phase 3 --- 

class ReportedMetricFieldValueSerializer(serializers.ModelSerializer):
    """Serializer for the aggregated value of a specific field within a multi-value metric."""
    field_key = serializers.CharField(source='field.field_key', read_only=True)
    field_display_name = serializers.CharField(source='field.display_name', read_only=True)

    class Meta:
        model = ReportedMetricFieldValue
        fields = [
            'id', 'field', 'field_key', 'field_display_name',
            'aggregated_numeric_value', 'aggregated_text_value',
            'aggregation_method', 'source_submission_count',
            'last_updated_at'
        ]
        read_only_fields = fields # All fields are read-only as they are calculated

class ReportedMetricValueSerializer(serializers.ModelSerializer):
    """Serializer for the parent Aggregated Metric Record."""
    metric_name = serializers.CharField(source='metric.name', read_only=True)
    metric_unit = serializers.SerializerMethodField(read_only=True)
    layer_name = serializers.CharField(source='layer.company_name', read_only=True)
    
    # Nested serializer for multi-value fields
    aggregated_fields = ReportedMetricFieldValueSerializer(many=True, read_only=True)

    class Meta:
        model = ReportedMetricValue # Point to the correct model
        fields = [
            'id', 'assignment', 'metric', 'metric_name', 'metric_unit',
            'layer', 'layer_name', 'reporting_period',
            # Single-value results (Option 2a)
            'aggregated_numeric_value', 'aggregated_text_value',
            # Calculation & Aggregation Metadata
            'calculated_at', 'last_updated_at',
            'source_submission_count', 'first_submission_at', 'last_submission_at',
            # Nested fields for multi-value results
            'aggregated_fields'
        ]
        read_only_fields = [ # Most fields are read-only, calculated by the service
            'id', 'assignment', 'metric', 'layer', 'reporting_period',
            'metric_name', 'metric_unit', 'layer_name',
            'aggregated_numeric_value', 'aggregated_text_value',
            'calculated_at', 'last_updated_at',
            'source_submission_count', 'first_submission_at', 'last_submission_at',
            'aggregated_fields'
        ]

    def get_metric_unit(self, obj):
        # The metric related is the *input* metric
        if obj.metric.unit_type == 'custom':
            return obj.metric.custom_unit
        return obj.metric.unit_type
# ----------------------------------