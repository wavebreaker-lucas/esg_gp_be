from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from ..models.polymorphic_metrics import FuelSourceType, StationaryFuelType
from ..serializers.fuel_data import FuelSourceTypeSerializer, StationaryFuelTypeSerializer

class FuelSourceTypeViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint that allows fuel source types to be viewed.
    """
    queryset = FuelSourceType.objects.all().order_by('label')
    serializer_class = FuelSourceTypeSerializer
    permission_classes = [IsAuthenticated]

class StationaryFuelTypeViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint that allows stationary fuel types to be viewed.
    """
    queryset = StationaryFuelType.objects.all().order_by('label')
    serializer_class = StationaryFuelTypeSerializer
    permission_classes = [IsAuthenticated] 