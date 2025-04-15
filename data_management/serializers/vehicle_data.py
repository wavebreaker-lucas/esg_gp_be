from rest_framework import serializers
from ..models.polymorphic_metrics import VehicleType, FuelType

class VehicleTypeSerializer(serializers.ModelSerializer):
    """Serializer for VehicleType models."""
    class Meta:
        model = VehicleType
        fields = ['id', 'value', 'label']
        read_only_fields = fields  # Make all fields read-only

class FuelTypeSerializer(serializers.ModelSerializer):
    """Serializer for FuelType models."""
    class Meta:
        model = FuelType
        fields = ['id', 'value', 'label']
        read_only_fields = fields  # Make all fields read-only 