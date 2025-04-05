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
from ..models.polymorphic_metrics import BaseESGMetric

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
    """Serializer for ESG metric submission inputs (raw data)."""
    evidence = ESGMetricEvidenceSerializer(many=True, read_only=True)
    metric_name = serializers.SerializerMethodField()
    # metric_unit = serializers.SerializerMethodField() # Commented out: Unit info is now on specialized metrics
    submitted_by_name = serializers.SerializerMethodField()
    verified_by_name = serializers.SerializerMethodField()
    layer_id = serializers.PrimaryKeyRelatedField(
        source='layer',
        queryset=LayerProfile.objects.all(),
        required=False,
        allow_null=True
    )
    layer_name = serializers.SerializerMethodField()
    # is_multi_value = serializers.SerializerMethodField() # Commented out: Property gone from BaseESGMetric
    # multi_values = MetricValueSerializer(many=True, read_only=True) # Commented out: Obsolete model
    source_identifier = serializers.CharField(max_length=100, required=False, allow_null=True, allow_blank=True)
    metric = serializers.PrimaryKeyRelatedField(queryset=BaseESGMetric.objects.all()) # Ensure queryset uses BaseESGMetric

    class Meta:
        model = ESGMetricSubmission
        # Removed fields dependent on deleted models/properties
        fields = [
            'id', 'assignment', 'metric', 'metric_name', # Removed metric_unit 
            'value', 'text_value', 'reporting_period', 'submitted_by', 'submitted_by_name',
            'submitted_at', 'updated_at', 'notes', 
            'is_verified', 'verified_by', 'verified_by_name', 'verified_at', 'verification_notes', 
            'evidence', 'layer_id', 'layer_name',
            # Removed is_multi_value, multi_values
            'source_identifier'
        ]
        read_only_fields = [
            'id',
            'submitted_by', 'submitted_at', 'updated_at', 
            'layer_name', 
        ]
    
    def get_metric_name(self, obj):
        # Accessing metric.name should work via polymorphism
        return obj.metric.name
    
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
    
    def validate(self, data):
        """Basic validation for the input data - NEEDS REVISITING for polymorphic types."""
        # metric = data.get('metric')
        # value = data.get('value')
        # text_value = data.get('text_value')
        
        # Original validation was tightly coupled to old model - skipping for now
        # Will need type-specific validation later
        
        # if not self.instance and value is None and not text_value:
        #     # This might only apply to BasicMetric now
        #     # raise serializers.ValidationError("Either a numeric value or text value must be provided for a new submission input.")
        
        return data

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