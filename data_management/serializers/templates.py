from rest_framework import serializers
from accounts.models import CustomUser, LayerProfile
from ..models import (
    ESGFormCategory, ESGForm, ESGMetric,
    Template, TemplateFormSelection, TemplateAssignment,
    MetricSchemaRegistry
)
from .esg import MetricSchemaRegistrySerializer

class ESGMetricSerializer(serializers.ModelSerializer):
    """Serializer for ESG metrics"""
    form_id = serializers.PrimaryKeyRelatedField(
        queryset=ESGForm.objects.all(),
        write_only=True,
        source='form',
        required=False
    )
    schema_registry_details = MetricSchemaRegistrySerializer(source='schema_registry', read_only=True)
    schema_registry_id = serializers.PrimaryKeyRelatedField(
        queryset=MetricSchemaRegistry.objects.all(),
        write_only=True,
        source='schema_registry',
        required=False,
        allow_null=True
    )
    
    class Meta:
        model = ESGMetric
        fields = [
            'id', 'name', 'description', 
            'requires_evidence', 'order', 'validation_rules', 'location', 'is_required',
            'requires_time_reporting', 'reporting_frequency', 'form_id',
            # JSON schema fields
            'data_schema', 'schema_registry', 'schema_registry_id', 'schema_registry_details',
            'form_component', 'primary_path', 'ocr_analyzer_id'
        ]
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