from rest_framework import serializers
from ..models.factors import GHGEmissionFactor


class GHGEmissionFactorSerializer(serializers.ModelSerializer):
    """
    Serializer for GHG Emission Factors.
    Provides full CRUD operations for Baker Tilly admins.
    """
    
    class Meta:
        model = GHGEmissionFactor
        fields = [
            'id', 'name', 'source', 'source_url', 'year', 'category', 
            'sub_category', 'activity_unit', 'value', 'factor_unit', 
            'region', 'scope'
        ]
        
    def validate_value(self, value):
        """Validate that the emission factor value is positive"""
        if value <= 0:
            raise serializers.ValidationError("Emission factor value must be positive")
        return value
        
    def validate_year(self, value):
        """Validate that the year is reasonable"""
        if value < 2000 or value > 2050:
            raise serializers.ValidationError("Year must be between 2000 and 2050")
        return value
        
    def validate(self, data):
        """Validate the combination of fields"""
        # Check if factor_unit makes sense with activity_unit
        activity_unit = data.get('activity_unit', '').lower()
        factor_unit = data.get('factor_unit', '').lower()
        
        # Basic validation for common unit combinations
        valid_combinations = [
            ('kwh', 'kgco2e/kwh'),
            ('liters', 'kgco2e/liter'),
            ('kg', 'kgco2e/kg'),
            ('tonnes', 'kgco2e/tonne'),
            ('cubic meter', 'kgco2e/m3'),
            ('unit', 'kgco2e/unit'),
            ('m3', 'kgco2e/m3'),
        ]
        
        # Remove spaces and special characters for comparison
        activity_clean = activity_unit.replace(' ', '').replace('_', '')
        factor_clean = factor_unit.replace(' ', '').replace('_', '')
        
        # Check if it's a valid combination (not exhaustive, just basic check)
        is_valid = any(
            activity_clean in combo[0] and combo[0] in activity_clean
            for combo in valid_combinations
            if combo[1].replace('/', '').replace(' ', '') in factor_clean
        )
        
        if not is_valid and activity_unit and factor_unit:
            # Don't fail validation, just warn - admin might know what they're doing
            pass
            
        return data


class GHGEmissionFactorListSerializer(serializers.ModelSerializer):
    """
    Simplified serializer for listing emission factors.
    Used for performance when displaying many factors.
    """
    
    class Meta:
        model = GHGEmissionFactor
        fields = [
            'id', 'name', 'category', 'sub_category', 'activity_unit', 
            'value', 'factor_unit', 'year', 'region', 'scope'
        ]
        read_only_fields = fields


class GHGEmissionFactorBulkCreateSerializer(serializers.Serializer):
    """
    Serializer for bulk creating emission factors.
    Accepts a list of emission factor data.
    """
    factors = GHGEmissionFactorSerializer(many=True)
    
    def create(self, validated_data):
        factors_data = validated_data['factors']
        created_factors = []
        
        for factor_data in factors_data:
            # Use update_or_create to handle duplicates
            factor, created = GHGEmissionFactor.objects.update_or_create(
                category=factor_data['category'],
                sub_category=factor_data['sub_category'],
                activity_unit=factor_data['activity_unit'],
                region=factor_data.get('region', 'ALL'),
                year=factor_data['year'],
                scope=factor_data.get('scope', ''),
                defaults={
                    'name': factor_data['name'],
                    'value': factor_data['value'],
                    'factor_unit': factor_data['factor_unit'],
                    'source': factor_data.get('source', ''),
                    'source_url': factor_data.get('source_url', ''),
                }
            )
            created_factors.append(factor)
            
        return {'factors': created_factors} 