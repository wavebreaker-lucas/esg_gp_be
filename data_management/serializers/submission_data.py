from rest_framework import serializers
# Using drf_polymorphic import based on user feedback
from rest_polymorphic.serializers import PolymorphicSerializer
from ..models.submission_data import (
    BasicMetricData, TabularMetricRow, MaterialMatrixDataPoint, 
    TimeSeriesDataPoint, MultiFieldTimeSeriesDataPoint, MultiFieldDataPoint,
    VehicleRecord, VehicleMonthlyData
)

# --- Serializers for Specific Submission Data Models ---

class BasicMetricDataSerializer(serializers.ModelSerializer):
    class Meta:
        model = BasicMetricData
        # Exclude the submission FK, as it will be handled by the parent serializer
        exclude = ('submission', 'id') # Exclude id too for cleaner output?

class TabularMetricRowSerializer(serializers.ModelSerializer):
    # id field might be useful for frontend updates within a table
    id = serializers.IntegerField(read_only=True) 
    class Meta:
        model = TabularMetricRow
        exclude = ('submission',)

class MaterialMatrixDataPointSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(read_only=True)
    class Meta:
        model = MaterialMatrixDataPoint
        exclude = ('submission',)

class TimeSeriesDataPointSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(read_only=True)
    class Meta:
        model = TimeSeriesDataPoint
        exclude = ('submission',)

class MultiFieldTimeSeriesDataPointSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(read_only=True)
    class Meta:
        model = MultiFieldTimeSeriesDataPoint
        exclude = ('submission',)

class MultiFieldDataPointSerializer(serializers.ModelSerializer):
    class Meta:
        model = MultiFieldDataPoint
        exclude = ('submission', 'id') # OneToOne field, ID less relevant?

class VehicleMonthlyDataSerializer(serializers.ModelSerializer):
    class Meta:
        model = VehicleMonthlyData
        exclude = ('vehicle',)

class VehicleRecordSerializer(serializers.ModelSerializer):
    monthly_data = VehicleMonthlyDataSerializer(many=True, read_only=True)
    class Meta:
        model = VehicleRecord
        exclude = ('submission',)

# --- Polymorphic Serializer for Reading Submission Data --- 

class PolymorphicSubmissionDataSerializer(PolymorphicSerializer):
    # Define the mapping from the data model to its serializer
    model_serializer_mapping = {
        BasicMetricData: BasicMetricDataSerializer,
        TabularMetricRow: TabularMetricRowSerializer, # Note: This handles ONE row
        MaterialMatrixDataPoint: MaterialMatrixDataPointSerializer,
        TimeSeriesDataPoint: TimeSeriesDataPointSerializer,
        MultiFieldTimeSeriesDataPoint: MultiFieldTimeSeriesDataPointSerializer,
        MultiFieldDataPoint: MultiFieldDataPointSerializer,
        VehicleRecord: VehicleRecordSerializer,  # Add VehicleRecord for polymorphic support
    }
    # This serializer is primarily for READING the specific data associated
    # with a submission. It determines the type based on the related object.
    resource_type_field_name = 'data_type' # Optional: Rename the type field

    # We don't define a queryset here as it's used nested within ESGMetricSubmissionSerializer

    # Add any other necessary methods or overrides from the base class 