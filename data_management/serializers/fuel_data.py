from rest_framework import serializers
from ..models.polymorphic_metrics import FuelSourceType, StationaryFuelType

class FuelSourceTypeSerializer(serializers.ModelSerializer):
    """Serializer for FuelSourceType models."""
    class Meta:
        model = FuelSourceType
        fields = ['id', 'value', 'label']
        read_only_fields = fields  # Make all fields read-only

class StationaryFuelTypeSerializer(serializers.ModelSerializer):
    """Serializer for StationaryFuelType models."""
    class Meta:
        model = StationaryFuelType
        fields = ['id', 'value', 'label', 'unit']
        read_only_fields = fields  # Make all fields read-only 