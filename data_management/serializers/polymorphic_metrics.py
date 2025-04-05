# Serializers for Polymorphic ESG Metrics 
# Using drf_polymorphic import based on user feedback
from drf_polymorphic.serializers import PolymorphicSerializer
from rest_framework import serializers
from ..models.polymorphic_metrics import (
    BaseESGMetric, BasicMetric, TabularMetric, MaterialTrackingMatrixMetric,
    TimeSeriesMetric, MultiFieldTimeSeriesMetric, MultiFieldMetric
)
from ..models.templates import ESGForm # Needed for form_id write

# --- Specialized Serializers ---

class BasicMetricSerializer(serializers.ModelSerializer):
    form_id = serializers.PrimaryKeyRelatedField(
        queryset=ESGForm.objects.all(), source='form', write_only=True
    )
    component_type = serializers.CharField(default='basic-input', read_only=True)
    class Meta:
        model = BasicMetric
        # Include base fields + specialized fields
        fields = '__all__'
        # Optional: Add specific read_only_fields if needed
        # read_only_fields = ['polymorphic_ctype'] 

class TabularMetricSerializer(serializers.ModelSerializer):
    form_id = serializers.PrimaryKeyRelatedField(
        queryset=ESGForm.objects.all(), source='form', write_only=True
    )
    component_type = serializers.CharField(default='tabular-input', read_only=True)
    class Meta:
        model = TabularMetric
        fields = '__all__'

class MaterialTrackingMatrixMetricSerializer(serializers.ModelSerializer):
    form_id = serializers.PrimaryKeyRelatedField(
        queryset=ESGForm.objects.all(), source='form', write_only=True
    )
    component_type = serializers.CharField(default='material-matrix-input', read_only=True)
    class Meta:
        model = MaterialTrackingMatrixMetric
        fields = '__all__'

class TimeSeriesMetricSerializer(serializers.ModelSerializer):
    form_id = serializers.PrimaryKeyRelatedField(
        queryset=ESGForm.objects.all(), source='form', write_only=True
    )
    component_type = serializers.CharField(default='timeseries-input', read_only=True)
    class Meta:
        model = TimeSeriesMetric
        fields = '__all__'

class MultiFieldTimeSeriesMetricSerializer(serializers.ModelSerializer):
    form_id = serializers.PrimaryKeyRelatedField(
        queryset=ESGForm.objects.all(), source='form', write_only=True
    )
    component_type = serializers.CharField(default='multifield-timeseries-input', read_only=True)
    class Meta:
        model = MultiFieldTimeSeriesMetric
        fields = '__all__'

class MultiFieldMetricSerializer(serializers.ModelSerializer):
    form_id = serializers.PrimaryKeyRelatedField(
        queryset=ESGForm.objects.all(), source='form', write_only=True
    )
    component_type = serializers.CharField(default='multifield-input', read_only=True)
    class Meta:
        model = MultiFieldMetric
        fields = '__all__'

# --- Polymorphic Base Serializer ---

class ESGMetricPolymorphicSerializer(PolymorphicSerializer):
    model_serializer_mapping = {
        # BaseESGMetric: BaseMetricSerializer, # Optional: Define a serializer just for the base if needed
        BasicMetric: BasicMetricSerializer,
        TabularMetric: TabularMetricSerializer,
        MaterialTrackingMatrixMetric: MaterialTrackingMatrixMetricSerializer,
        TimeSeriesMetric: TimeSeriesMetricSerializer,
        MultiFieldTimeSeriesMetric: MultiFieldTimeSeriesMetricSerializer,
        MultiFieldMetric: MultiFieldMetricSerializer
    }
    # The 'polymorphic_ctype' field is automatically added by the library 
    # to identify the model type in the JSON output.
    resource_type_field_name = 'metric_subtype' # Optional: Rename the type field

    # If you need a common field across all types not on the base model, define it here.
    # Example: 
    # common_extra_field = serializers.SerializerMethodField()
    # def get_common_extra_field(self, obj): return "Some value" 