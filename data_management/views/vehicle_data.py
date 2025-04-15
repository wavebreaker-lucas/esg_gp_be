from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from ..models.polymorphic_metrics import VehicleType, FuelType
from ..serializers.vehicle_data import VehicleTypeSerializer, FuelTypeSerializer

class VehicleTypeViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint that allows vehicle types to be viewed.
    """
    queryset = VehicleType.objects.all().order_by('label')
    serializer_class = VehicleTypeSerializer
    permission_classes = [IsAuthenticated]

class FuelTypeViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint that allows fuel types to be viewed.
    """
    queryset = FuelType.objects.all().order_by('label')
    serializer_class = FuelTypeSerializer
    permission_classes = [IsAuthenticated] 