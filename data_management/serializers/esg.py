from rest_framework import serializers
from accounts.models import CustomUser, LayerProfile
from ..models import BoundaryItem, EmissionFactor, ESGData, DataEditLog
from ..models.templates import ESGMetricSubmission, ESGMetricEvidence, ESGMetric

class BoundaryItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = BoundaryItem
        fields = '__all__'

class EmissionFactorSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmissionFactor
        fields = '__all__'

class ESGDataSerializer(serializers.ModelSerializer):
    company = serializers.PrimaryKeyRelatedField(queryset=LayerProfile.objects.all())
    boundary_item = BoundaryItemSerializer(read_only=True)
    submitted_by = serializers.PrimaryKeyRelatedField(
        queryset=CustomUser.objects.all(),
        required=False
    )
    verified_by = serializers.PrimaryKeyRelatedField(
        queryset=CustomUser.objects.all(),
        required=False,
        allow_null=True
    )

    class Meta:
        model = ESGData
        fields = '__all__'

class DataEditLogSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(
        queryset=CustomUser.objects.all(),
        required=False
    )
    esg_data = ESGDataSerializer(read_only=True)

    class Meta:
        model = DataEditLog
        fields = '__all__'

class ESGMetricEvidenceSerializer(serializers.ModelSerializer):
    """Serializer for ESG metric evidence files"""
    uploaded_by_name = serializers.SerializerMethodField()
    edited_by_name = serializers.SerializerMethodField()
    
    class Meta:
        model = ESGMetricEvidence
        fields = [
            'id', 'file', 'filename', 'file_type', 
            'uploaded_by', 'uploaded_by_name', 'uploaded_at', 'description',
            'is_utility_bill', 'ocr_processed', 'extracted_value', 
            'extracted_period', 'was_manually_edited', 'edited_at', 
            'edited_by', 'edited_by_name'
        ]
        read_only_fields = [
            'uploaded_by', 'uploaded_at', 'ocr_processed', 
            'extracted_value', 'extracted_period', 'was_manually_edited',
            'edited_at', 'edited_by'
        ]
    
    def get_uploaded_by_name(self, obj):
        if obj.uploaded_by:
            return obj.uploaded_by.get_full_name() or obj.uploaded_by.email
        return None
        
    def get_edited_by_name(self, obj):
        if obj.edited_by:
            return obj.edited_by.get_full_name() or obj.edited_by.email
        return None

class ESGMetricSubmissionSerializer(serializers.ModelSerializer):
    """Serializer for ESG metric submissions"""
    evidence = ESGMetricEvidenceSerializer(many=True, read_only=True)
    metric_name = serializers.SerializerMethodField()
    metric_unit = serializers.SerializerMethodField()
    submitted_by_name = serializers.SerializerMethodField()
    verified_by_name = serializers.SerializerMethodField()
    
    class Meta:
        model = ESGMetricSubmission
        fields = [
            'id', 'assignment', 'metric', 'metric_name', 'metric_unit',
            'value', 'text_value', 'reporting_period', 'submitted_by', 'submitted_by_name',
            'submitted_at', 'updated_at', 'notes', 'is_verified',
            'verified_by', 'verified_by_name', 'verified_at', 
            'verification_notes', 'evidence'
        ]
        read_only_fields = [
            'submitted_by', 'submitted_at', 'updated_at', 
            'is_verified', 'verified_by', 'verified_at'
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
    
    def validate(self, data):
        """Validate that either value or text_value is provided based on metric type"""
        metric = data.get('metric')
        value = data.get('value')
        text_value = data.get('text_value')
        
        # Check if numeric metrics have a numeric value
        numeric_units = ['kWh', 'MWh', 'm3', 'tonnes', 'tCO2e', 'percentage']
        if metric.unit_type in numeric_units and value is None:
            raise serializers.ValidationError(f"A numeric value is required for {metric.name}")
        
        # Check if at least one value type is provided
        if value is None and not text_value:
            raise serializers.ValidationError("Either a numeric value or text value must be provided")
        
        # Check for duplicate submissions with the same reporting period
        assignment = data.get('assignment')
        reporting_period = data.get('reporting_period')
        
        # If this is an update, exclude the current instance
        instance = self.instance
        if instance:
            try:
                existing = ESGMetricSubmission.objects.exclude(pk=instance.pk).get(
                    assignment=assignment,
                    metric=metric,
                    reporting_period=reporting_period
                )
                raise serializers.ValidationError(
                    f"A submission for this metric with reporting period {reporting_period} already exists"
                )
            except ESGMetricSubmission.DoesNotExist:
                pass
        
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
        from ..models.templates import TemplateAssignment, ESGMetricSubmission
        
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
            
            # Validate value based on metric type
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