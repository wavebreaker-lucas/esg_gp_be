from rest_framework import serializers
from accounts.models import CustomUser, LayerProfile
from ..models import (
    ESGFormCategory, ESGForm, ESGMetric,
    Template, TemplateFormSelection, TemplateAssignment
)

class ESGMetricSerializer(serializers.ModelSerializer):
    """Serializer for ESG metrics"""
    class Meta:
        model = ESGMetric
        fields = ['id', 'name', 'description', 'unit_type', 'custom_unit', 
                 'requires_evidence', 'order', 'validation_rules', 'location', 'is_required']

class ESGFormSerializer(serializers.ModelSerializer):
    """Serializer for ESG forms with nested metrics"""
    metrics = ESGMetricSerializer(many=True, read_only=True)

    class Meta:
        model = ESGForm
        fields = ['id', 'code', 'name', 'description', 'is_active', 'metrics']

    def create(self, validated_data):
        """Create a new ESG form with example metrics"""
        form = super().create(validated_data)
        
        # Example: Create metrics for HKEX-B2 (Health and Safety)
        if form.code == 'HKEX-B2':
            metrics = [
                {
                    'name': 'Number of work-related fatalities',
                    'description': 'Number of deaths due to work injury',
                    'unit_type': 'count',
                    'requires_evidence': True,
                    'order': 1,
                    'location': 'HK',
                    'is_required': False
                },
                {
                    'name': 'Number of work-related fatalities',
                    'description': 'Number of deaths due to work injury',
                    'unit_type': 'count',
                    'requires_evidence': True,
                    'order': 2,
                    'location': 'PRC',
                    'is_required': False
                },
                {
                    'name': 'Number of reported work injuries',
                    'description': 'Total reported cases of work-related injuries',
                    'unit_type': 'count',
                    'requires_evidence': True,
                    'order': 3,
                    'location': 'HK',
                    'is_required': False
                },
                {
                    'name': 'Number of reported work injuries',
                    'description': 'Total reported cases of work-related injuries',
                    'unit_type': 'count',
                    'requires_evidence': True,
                    'order': 4,
                    'location': 'PRC',
                    'is_required': False
                },
                {
                    'name': 'Lost days due to work injury',
                    'description': 'Number of days lost due to work injury',
                    'unit_type': 'days',
                    'requires_evidence': True,
                    'order': 5,
                    'location': 'HK',
                    'is_required': False
                },
                {
                    'name': 'Lost days due to work injury',
                    'description': 'Number of days lost due to work injury',
                    'unit_type': 'days',
                    'requires_evidence': True,
                    'order': 6,
                    'location': 'PRC',
                    'is_required': False
                }
            ]
            
            for metric_data in metrics:
                ESGMetric.objects.create(form=form, **metric_data)
        
        # Create metrics for HKEX-A2 (Energy and Water Consumption)
        elif form.code == 'HKEX-A2':
            # Electricity consumption metrics
            electricity_metrics = [
                {
                    'name': 'Electricity consumption (CLP)',
                    'description': 'Monthly electricity consumption from CLP',
                    'unit_type': 'kWh',
                    'requires_evidence': True,
                    'order': 1,
                    'location': 'HK',
                    'is_required': False,
                    'validation_rules': {'period': 'monthly', 'year': '2024'}
                },
                {
                    'name': 'Electricity consumption (HKE)',
                    'description': 'Monthly electricity consumption from HKE',
                    'unit_type': 'kWh',
                    'requires_evidence': True,
                    'order': 2,
                    'location': 'HK',
                    'is_required': False,
                    'validation_rules': {'period': 'monthly', 'year': '2024'}
                },
                {
                    'name': 'Electricity consumption',
                    'description': 'Monthly electricity consumption',
                    'unit_type': 'kWh',
                    'requires_evidence': True,
                    'order': 3,
                    'location': 'PRC',
                    'is_required': False,
                    'validation_rules': {'period': 'monthly', 'year': '2024'}
                },
            ]
            
            # Water consumption metrics
            water_metrics = [
                {
                    'name': 'Fresh water consumption',
                    'description': 'Monthly fresh water consumption',
                    'unit_type': 'm3',
                    'requires_evidence': True,
                    'order': 4,
                    'location': 'HK',
                    'is_required': False,
                    'validation_rules': {'period': 'monthly', 'year': '2024'}
                },
                {
                    'name': 'Fresh water consumption',
                    'description': 'Monthly fresh water consumption',
                    'unit_type': 'm3',
                    'requires_evidence': True,
                    'order': 5,
                    'location': 'PRC',
                    'is_required': False,
                    'validation_rules': {'period': 'monthly', 'year': '2024'}
                },
                {
                    'name': 'Wastewater consumption',
                    'description': 'Monthly wastewater consumption',
                    'unit_type': 'm3',
                    'requires_evidence': True,
                    'order': 6,
                    'location': 'HK',
                    'is_required': False,
                    'validation_rules': {'period': 'monthly', 'year': '2024'}
                },
                {
                    'name': 'Wastewater consumption',
                    'description': 'Monthly wastewater consumption',
                    'unit_type': 'm3',
                    'requires_evidence': True,
                    'order': 7,
                    'location': 'PRC',
                    'is_required': False,
                    'validation_rules': {'period': 'monthly', 'year': '2024'}
                },
            ]
            
            # Create all metrics
            for metric_data in electricity_metrics + water_metrics:
                ESGMetric.objects.create(form=form, **metric_data)
        
        return form

class ESGFormCategorySerializer(serializers.ModelSerializer):
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

    class Meta:
        model = TemplateFormSelection
        fields = ['id', 'form', 'form_id', 'regions', 'order']

class TemplateSerializer(serializers.ModelSerializer):
    selected_forms = TemplateFormSelectionSerializer(
        source='templateformselection_set',
        many=True
    )
    created_by = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = Template
        fields = ['id', 'name', 'description', 'reporting_period',
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
    company = serializers.PrimaryKeyRelatedField(queryset=LayerProfile.objects.all())
    assigned_to = serializers.PrimaryKeyRelatedField(queryset=CustomUser.objects.all(), required=False, allow_null=True)

    class Meta:
        model = TemplateAssignment
        fields = '__all__'
        
    def create(self, validated_data):
        template = validated_data.pop('template_id')
        validated_data['template'] = template
        return super().create(validated_data)