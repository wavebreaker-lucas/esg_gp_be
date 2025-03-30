from rest_framework import serializers
from accounts.models import CustomUser, LayerProfile
from ..models import BoundaryItem, EmissionFactor, ESGData, DataEditLog
from ..models.templates import (
    ESGMetricSubmission, ESGMetricEvidence, ESGMetric, 
    MetricSchemaRegistry, ESGMetricBatchSubmission
)

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
            'edited_by', 'edited_by_name', 'submission', 'layer_id', 'layer_name',
            'reference_path', 'extracted_data', 'ocr_data', 'intended_metric'
        ]
        read_only_fields = [
            'uploaded_by', 'uploaded_at', 'is_processed_by_ocr', 
            'extracted_value', 'period', 'was_manually_edited',
            'edited_at', 'edited_by', 'layer_name', 'extracted_data', 'ocr_data'
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
    """Serializer for ESG metric submissions"""
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
    batch_id = serializers.PrimaryKeyRelatedField(
        source='batch_submission',
        read_only=True
    )
    
    class Meta:
        model = ESGMetricSubmission
        fields = [
            'id', 'assignment', 'metric', 'metric_name', 'metric_unit',
            'data', 'batch_id', 'batch_submission',
            'submitted_by', 'submitted_by_name',
            'submitted_at', 'updated_at', 'notes', 'is_verified',
            'verified_by', 'verified_by_name', 'verified_at', 
            'verification_notes', 'evidence', 'layer_id', 'layer_name'
        ]
        read_only_fields = [
            'submitted_by', 'submitted_at', 'updated_at', 
            'is_verified', 'verified_by', 'verified_at', 'layer_name',
            'batch_id'
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
    
    def validate(self, data):
        """Validate JSON data against metric schema"""
        metric = data.get('metric')
        json_data = data.get('data')
        assignment = data.get('assignment')
        
        # Validate that data is provided
        if not json_data:
            raise serializers.ValidationError("JSON data is required")
            
        # Validate data is a JSON object
        if not isinstance(json_data, dict):
            raise serializers.ValidationError("Data must be a JSON object")
            
        # If the metric has a schema, validate against it
        schema = None
        if metric.schema_registry and hasattr(metric.schema_registry, 'schema'):
            schema = metric.schema_registry.schema
        elif metric.data_schema:
            schema = metric.data_schema
            
        if schema:
            try:
                from jsonschema import validate, ValidationError as JsonSchemaError
                validate(instance=json_data, schema=schema)
            except ImportError:
                # If jsonschema is not available, perform basic validation
                pass
            except JsonSchemaError as e:
                raise serializers.ValidationError(f"JSON data validation error: {str(e)}")
        
        # Check for duplicate submissions with the same layer
        layer = data.get('layer')
        
        # If this is an update, exclude the current instance
        instance = self.instance
        if instance:
            try:
                existing = ESGMetricSubmission.objects.exclude(pk=instance.pk).get(
                    assignment=assignment,
                    metric=metric,
                    layer=layer
                )
                raise serializers.ValidationError(
                    f"A submission for this metric with the same layer already exists"
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
            # Note: Now we check for uniqueness based on assignment, metric, and layer
            layer = validated_data.get('layer')
            existing_filter = {
                'assignment': validated_data['assignment'],
                'metric': validated_data['metric']
            }
            
            if layer:
                existing_filter['layer'] = layer
                
            submission = ESGMetricSubmission.objects.get(**existing_filter)
            
            # Update existing submission
            for attr, value in validated_data.items():
                setattr(submission, attr, value)
            submission.save()
            return submission
        except ESGMetricSubmission.DoesNotExist:
            # Create a new submission
            return super().create(validated_data)

class ESGMetricBatchSubmissionSerializer(serializers.Serializer):
    """Serializer for batch submission of multiple metrics through API"""
    assignment_id = serializers.IntegerField()
    submissions = serializers.ListField(
        child=serializers.DictField()
    )
    name = serializers.CharField(required=False, allow_blank=True)
    notes = serializers.CharField(required=False, allow_blank=True)
    layer_id = serializers.IntegerField(required=False, allow_null=True)
    
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
            
            if 'data' not in submission:
                raise serializers.ValidationError("Each submission must include JSON data")
            
            # Validate metric exists
            try:
                metric = ESGMetric.objects.get(id=submission['metric_id'])
            except ESGMetric.DoesNotExist:
                raise serializers.ValidationError(f"Metric with ID {submission['metric_id']} not found")
            
            # Validate data field
            if not isinstance(submission['data'], dict):
                raise serializers.ValidationError(f"Data for metric {metric.name} must be a JSON object")
            
            # Check against schema if available
            schema = None
            if hasattr(metric, 'schema_registry') and metric.schema_registry and hasattr(metric.schema_registry, 'schema'):
                schema = metric.schema_registry.schema
            elif hasattr(metric, 'data_schema') and metric.data_schema:
                schema = metric.data_schema
                
            if schema:
                try:
                    from jsonschema import validate, ValidationError as JsonSchemaError
                    validate(instance=submission['data'], schema=schema)
                except ImportError:
                    # Basic validation if jsonschema not available
                    pass
                except JsonSchemaError as e:
                    raise serializers.ValidationError(f"JSON schema validation failed for {metric.name}: {str(e)}")
            
            # Check for duplicate submissions with the same layer
            layer_id = submission.get('layer_id', data.get('layer_id'))
            if layer_id:
                try:
                    existing = ESGMetricSubmission.objects.get(
                        assignment_id=data['assignment_id'],
                        metric_id=submission['metric_id'],
                        layer_id=layer_id
                    )
                    # Allow updating existing submissions
                    submission['update_id'] = existing.id
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
        if not (user.is_staff or user.is_superuser or user.is_baker_tilly_admin):
            raise serializers.ValidationError("Only Baker Tilly admins can verify submissions")
            
        return data 

class MetricSchemaRegistrySerializer(serializers.ModelSerializer):
    """Serializer for metric JSON schemas"""
    created_by_name = serializers.SerializerMethodField()
    
    class Meta:
        model = MetricSchemaRegistry
        fields = [
            'id', 'name', 'description', 'schema', 'version',
            'created_at', 'updated_at', 'created_by', 'created_by_name',
            'is_active'
        ]
        read_only_fields = ['created_at', 'updated_at']
    
    def get_created_by_name(self, obj):
        if obj.created_by:
            return obj.created_by.email
        return None
    
    def validate_schema(self, value):
        """Validate that the schema is a valid JSON Schema"""
        if not isinstance(value, dict):
            raise serializers.ValidationError("Schema must be a JSON object")
        
        # Check for required JSON Schema fields
        if 'type' not in value:
            raise serializers.ValidationError("Schema must have a 'type' field")
            
        # For objects, check for properties
        if value.get('type') == 'object' and 'properties' not in value:
            raise serializers.ValidationError("Object schemas must define 'properties'")
            
        return value
    
    def create(self, validated_data):
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            validated_data['created_by'] = request.user
        return super().create(validated_data) 

class BatchSubmissionModelSerializer(serializers.ModelSerializer):
    """ModelSerializer for ESGMetricBatchSubmission"""
    submission_count = serializers.SerializerMethodField()
    submitted_by_name = serializers.SerializerMethodField()
    verified_by_name = serializers.SerializerMethodField()
    layer_name = serializers.SerializerMethodField()
    
    class Meta:
        model = ESGMetricBatchSubmission
        fields = [
            'id', 'name', 'assignment', 'submitted_by', 'submitted_by_name',
            'submitted_at', 'updated_at', 'layer', 'layer_name', 'notes',
            'is_verified', 'verified_by', 'verified_by_name', 'verified_at',
            'verification_notes', 'submission_count'
        ]
        read_only_fields = [
            'submitted_by', 'submitted_at', 'updated_at',
            'is_verified', 'verified_by', 'verified_at', 'submission_count'
        ]
    
    def get_submission_count(self, obj):
        return obj.submissions.count()
    
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