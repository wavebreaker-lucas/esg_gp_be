from rest_framework import serializers
from accounts.models import CustomUser, LayerProfile
from ..models import BoundaryItem, EmissionFactor, ESGData, DataEditLog

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