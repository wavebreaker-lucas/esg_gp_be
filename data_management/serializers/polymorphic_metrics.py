# Serializers for Polymorphic ESG Metrics 
# Using drf_polymorphic import based on user feedback
from rest_polymorphic.serializers import PolymorphicSerializer
from rest_framework import serializers
from ..models.polymorphic_metrics import (
    BaseESGMetric, BasicMetric, TabularMetric, MaterialTrackingMatrixMetric,
    TimeSeriesMetric, MultiFieldTimeSeriesMetric, MultiFieldMetric,
    VehicleTrackingMetric, FuelConsumptionMetric
)
from ..models.templates import ESGForm # Needed for form_id write

# --- Specialized Serializers ---

class BasicMetricSerializer(serializers.ModelSerializer):
    form_id = serializers.PrimaryKeyRelatedField(
        queryset=ESGForm.objects.all(), source='form', write_only=True
    )
    class Meta:
        model = BasicMetric
        # Include base fields + specialized fields
        fields = '__all__'
        # Optional: Add specific read_only_fields if needed
        read_only_fields = ('form',)

class TabularMetricSerializer(serializers.ModelSerializer):
    form_id = serializers.PrimaryKeyRelatedField(
        queryset=ESGForm.objects.all(), source='form', write_only=True
    )
    class Meta:
        model = TabularMetric
        fields = '__all__'
        read_only_fields = ('form',)

class MaterialTrackingMatrixMetricSerializer(serializers.ModelSerializer):
    form_id = serializers.PrimaryKeyRelatedField(
        queryset=ESGForm.objects.all(), source='form', write_only=True
    )
    class Meta:
        model = MaterialTrackingMatrixMetric
        fields = '__all__'
        read_only_fields = ('form',)

class TimeSeriesMetricSerializer(serializers.ModelSerializer):
    form_id = serializers.PrimaryKeyRelatedField(
        queryset=ESGForm.objects.all(), source='form', write_only=True
    )
    class Meta:
        model = TimeSeriesMetric
        fields = '__all__'
        read_only_fields = ('form',)

class MultiFieldTimeSeriesMetricSerializer(serializers.ModelSerializer):
    form_id = serializers.PrimaryKeyRelatedField(
        queryset=ESGForm.objects.all(), source='form', write_only=True
    )
    class Meta:
        model = MultiFieldTimeSeriesMetric
        fields = '__all__'
        read_only_fields = ('form',)

class MultiFieldMetricSerializer(serializers.ModelSerializer):
    form_id = serializers.PrimaryKeyRelatedField(
        queryset=ESGForm.objects.all(), source='form', write_only=True
    )
    class Meta:
        model = MultiFieldMetric
        fields = '__all__'
        read_only_fields = ('form',)

class VehicleTrackingMetricSerializer(serializers.ModelSerializer):
    form_id = serializers.PrimaryKeyRelatedField(
        queryset=ESGForm.objects.all(), source='form', write_only=True
    )
    class Meta:
        model = VehicleTrackingMetric
        fields = '__all__'
        read_only_fields = ('form',)

# Add new serializer for FuelConsumptionMetric
class FuelConsumptionMetricSerializer(serializers.ModelSerializer):
    form_id = serializers.PrimaryKeyRelatedField(
        queryset=ESGForm.objects.all(), source='form', write_only=True
    )
    class Meta:
        model = FuelConsumptionMetric
        fields = '__all__'
        read_only_fields = ('form',)

# --- Polymorphic Base Serializer ---

class ESGMetricPolymorphicSerializer(PolymorphicSerializer):
    model_serializer_mapping = {
        # BaseESGMetric: BaseMetricSerializer, # Optional: Define a serializer just for the base if needed
        BasicMetric: BasicMetricSerializer,
        TabularMetric: TabularMetricSerializer,
        MaterialTrackingMatrixMetric: MaterialTrackingMatrixMetricSerializer,
        TimeSeriesMetric: TimeSeriesMetricSerializer,
        MultiFieldTimeSeriesMetric: MultiFieldTimeSeriesMetricSerializer,
        MultiFieldMetric: MultiFieldMetricSerializer,
        VehicleTrackingMetric: VehicleTrackingMetricSerializer,
        FuelConsumptionMetric: FuelConsumptionMetricSerializer
    }
    # The 'polymorphic_ctype' field is automatically added by the library 
    # to identify the model type in the JSON output.
    resource_type_field_name = 'metric_subtype' # Optional: Rename the type field

    # If you need a common field across all types not on the base model, define it here.
    # Example: 
    # common_extra_field = serializers.SerializerMethodField()
    # def get_common_extra_field(self, obj): return "Some value" 