from rest_framework import serializers
from .models import BoundaryItem, EmissionFactor, ESGData
from accounts.models import CompanyLayer

class CompanyLayerSerializer(serializers.ModelSerializer):
    class Meta:
        model = CompanyLayer
        fields = '__all__'

class BoundaryItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = BoundaryItem
        fields = '__all__'
        
class EmissionFactorSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmissionFactor
        fields = '__all__'
        
class ESGDataSerializer(serializers.ModelSerializer):
    company_name = serializers.ReadOnlyField(source='company.name')
    boundary_item_name = serializers.ReadOnlyField(source='boundary_item.name')
    submitted_by_username = serializers.ReadOnlyField(source='submitted_by.username')
    
    class Meta:
        model = ESGData
        fields = ['id', 'company', 'company_name', 'boundary_item', 
                 'boundary_item_name', 'scope', 'value', 'unit', 
                 'date_recorded', 'submitted_by', 'submitted_by_username', 
                 'is_verified', 'verification_date', 'verified_by']
        read_only_fields = ['verification_date', 'verified_by', 'is_verified'] 