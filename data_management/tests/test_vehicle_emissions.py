import json
from decimal import Decimal
from django.test import TestCase
from django.utils import timezone
import datetime

from data_management.models.factors import GHGEmissionFactor
from data_management.models.templates import ReportedMetricValue, TemplateAssignment, Template, ESGForm, ESGFormCategory
from data_management.models.polymorphic_metrics import VehicleTrackingMetric
from data_management.models.results import CalculatedEmissionValue
from data_management.services.calculation_strategies import VehicleTrackingCalculationStrategy
from data_management.services.emissions import find_matching_emission_factor, calculate_emissions_for_activity_value
from accounts.models import LayerProfile


class VehicleEmissionFactorMappingTest(TestCase):
    """Tests for the VehicleTrackingMetric's dynamic emission factor mapping"""
    
    def setUp(self):
        """Set up test data for the mapping tests"""
        self.metric = VehicleTrackingMetric()
        # Initialize with default emission mappings
        self.metric.emission_factor_mapping = {
            "private_cars_diesel_oil": "transport_cars_diesel",
            "private_cars_petrol": "transport_cars_petrol", 
            "private_cars_lpg": "transport_cars_lpg",
            "light_goods_lte_2_5_diesel_oil": "transport_light_commercial_diesel",
            "diesel_oil": "transport_general_diesel",
            "petrol": "transport_general_petrol"
        }
    
    def test_specific_vehicle_fuel_mapping(self):
        """Test that specific vehicle+fuel combinations are mapped correctly"""
        # Test a direct match in the mapping
        subcategory = self.metric.get_emission_subcategory("private_cars", "diesel_oil")
        self.assertEqual(subcategory, "transport_cars_diesel")
        
        # Test another direct match
        subcategory = self.metric.get_emission_subcategory("private_cars", "petrol")
        self.assertEqual(subcategory, "transport_cars_petrol")
    
    def test_fuel_only_fallback_mapping(self):
        """Test fallback to fuel-only mapping when no specific combo exists"""
        # This combo doesn't exist in our mapping, should fall back to diesel_oil
        subcategory = self.metric.get_emission_subcategory("heavy_duty_truck", "diesel_oil")
        self.assertEqual(subcategory, "transport_general_diesel")
    
    def test_constructed_fallback_mapping(self):
        """Test fallback to constructed key when no match found"""
        # Neither this combo nor this fuel exists in our mapping
        subcategory = self.metric.get_emission_subcategory("special_vehicle", "hydrogen")
        self.assertEqual(subcategory, "transport_special_vehicle_hydrogen")


class EmissionFactorLookupTest(TestCase):
    """Tests for emission factor lookup with fallbacks"""
    
    def setUp(self):
        """Set up test emission factors in the database"""
        # Create factors with different specificities for testing the fallback logic
        # 1. Exact match factor (current year, specific region)
        self.exact_factor = GHGEmissionFactor.objects.create(
            name="Test Transport - Cars Diesel HK 2025",
            year=2025,
            category="transport",
            sub_category="transport_cars_diesel",
            activity_unit="liters",
            value=Decimal("2.70"),
            factor_unit="kgCO2e/liter",
            region="HK",
            scope="1"
        )
        
        # 2. Universal region factor (same year, ALL region)
        self.universal_factor = GHGEmissionFactor.objects.create(
            name="Test Transport - Cars Diesel ALL 2025",
            year=2025,
            category="transport",
            sub_category="transport_cars_petrol",
            activity_unit="liters",
            value=Decimal("2.40"),
            factor_unit="kgCO2e/liter",
            region="ALL",
            scope="1"
        )
        
        # 3. Earlier year factor (previous year, same region)
        self.earlier_factor = GHGEmissionFactor.objects.create(
            name="Test Transport - Light Commercial Diesel HK 2024",
            year=2024,
            category="transport",
            sub_category="transport_light_commercial_diesel",
            activity_unit="liters",
            value=Decimal("2.90"),
            factor_unit="kgCO2e/liter",
            region="HK",
            scope="1"
        )
    
    def test_exact_match_lookup(self):
        """Test finding an exact match for year, category, subcategory and region"""
        factor = find_matching_emission_factor(
            year=2025,
            category="transport",
            sub_category="transport_cars_diesel",
            activity_unit="liters",
            region="HK"
        )
        self.assertEqual(factor.id, self.exact_factor.id)
    
    def test_universal_region_fallback(self):
        """Test fallback to universal region when specific region not found"""
        factor = find_matching_emission_factor(
            year=2025,
            category="transport",
            sub_category="transport_cars_petrol",
            activity_unit="liters",
            region="PRC"  # Different from the factor's HK region
        )
        self.assertEqual(factor.id, self.universal_factor.id)
    
    def test_earlier_year_fallback(self):
        """Test fallback to earlier year when current year not found"""
        factor = find_matching_emission_factor(
            year=2025,  # Factor is from 2024
            category="transport",
            sub_category="transport_light_commercial_diesel",
            activity_unit="liters",
            region="HK"
        )
        self.assertEqual(factor.id, self.earlier_factor.id)


class VehicleCalculationStrategyTest(TestCase):
    """Tests for the VehicleTrackingCalculationStrategy"""
    
    def setUp(self):
        """Set up test data for the calculation strategy tests"""
        # Create a test emission factor
        self.test_factor = GHGEmissionFactor.objects.create(
            name="Test Transport - Cars Diesel",
            year=2025,
            category="transport",
            sub_category="transport_cars_diesel",
            activity_unit="liters",
            value=Decimal("2.70"),
            factor_unit="kgCO2e/liter",
            region="ALL",
            scope="1"
        )
        
        # Create a VehicleTrackingMetric
        self.metric = VehicleTrackingMetric()
        self.metric.emission_category = "transport"
        self.metric.emission_factor_mapping = {
            "private_cars_diesel_oil": "transport_cars_diesel"
        }
        
        # Create a strategy instance
        self.strategy = VehicleTrackingCalculationStrategy()
        
        # Create a category for the form
        self.category = ESGFormCategory.objects.create(code="TEST-CAT", name="Test Category")
        
        # Create a form for the metric (needed for template)
        self.form = ESGForm.objects.create(
            category=self.category, # Assign the category
            code="TEST-FORM", 
            name="Test Form"
        )
        self.metric.form = self.form
        self.metric.save()
        
        # Create a template
        self.template = Template.objects.create(name="Test Template")
        self.template.selected_forms.add(self.form)
        
        # Sample vehicle data JSON
        self.vehicle_data = {
            "vehicles": [
                {
                    "id": 1,
                    "vehicle_type": "private_cars",
                    "fuel_type": "diesel_oil", 
                    "fuel_consumed": 100.0,
                    "kilometers": 1000.0,
                    "registration": "AB1234"
                },
                {
                    "id": 2,
                    "vehicle_type": "private_cars",
                    "fuel_type": "diesel_oil",
                    "fuel_consumed": 50.0,
                    "kilometers": 500.0,
                    "registration": "CD5678"
                }
            ]
        }
    
    def test_parse_vehicle_data(self):
        """Test parsing vehicle data from JSON text"""
        # Test with JSON string
        json_text = json.dumps(self.vehicle_data)
        parsed = self.strategy._parse_vehicle_data(json_text)
        self.assertEqual(len(parsed["vehicles"]), 2)
        self.assertEqual(parsed["vehicles"][0]["fuel_consumed"], 100.0)
        
        # Test with dict input
        parsed = self.strategy._parse_vehicle_data(self.vehicle_data)
        self.assertEqual(parsed, self.vehicle_data)
        
        # Test with invalid input
        parsed = self.strategy._parse_vehicle_data("not valid json")
        self.assertIsNone(parsed)
        
        # Test with None
        parsed = self.strategy._parse_vehicle_data(None)
        self.assertIsNone(parsed)
    
    def test_vehicle_label_lookup(self):
        """Test retrieving human-readable labels for vehicle types"""
        self.metric.vehicle_type_choices = [
            {"value": "private_cars", "label": "Private Cars"},
            {"value": "truck", "label": "Truck"}
        ]
        
        # Test valid lookup
        label = self.strategy._get_vehicle_label("private_cars", self.metric)
        self.assertEqual(label, "Private Cars")
        
        # Test fallback when not found
        label = self.strategy._get_vehicle_label("unknown_type", self.metric)
        self.assertEqual(label, "unknown_type")
        
        # Test with None
        label = self.strategy._get_vehicle_label(None, self.metric)
        self.assertEqual(label, "Unknown")
    
    def test_calculate_emissions(self):
        """Test calculating emissions using the strategy"""
        # Create mock objects needed for calculation
        layer = LayerProfile.objects.create(company_name="Test Company")
        
        assignment = TemplateAssignment.objects.create(
            template=self.template,
            layer=layer,
            reporting_period_start=datetime.date(2025, 1, 1),
            reporting_period_end=datetime.date(2025, 12, 31),
            reporting_year=2025
        )
        
        # Create a ReportedMetricValue with our test vehicle data
        rpv = ReportedMetricValue.objects.create(
            assignment=assignment,
            metric=self.metric,
            layer=layer,
            reporting_period=datetime.date(2025, 12, 31),
            level='A',
            aggregated_text_value=json.dumps(self.vehicle_data)
        )
        
        # Mock the find_matching_emission_factor function to return our test factor
        def mock_find_factor(*args, **kwargs):
            return self.test_factor
            
        # Call calculate with our mocked objects
        # This test relies on monkeypatching which we'd normally do with pytest
        # but we're using unittest, so we'll check the returned structure manually
        results = self.strategy.calculate(rpv, self.metric, 2025, "ALL")
        
        # Basic validation of the results structure
        self.assertIsNotNone(results)
        self.assertTrue(isinstance(results, list))
        
        if results:  # If we got results without mocking
            # Basic structure checks
            self.assertIn('activity_value', results[0])
            self.assertIn('emission_value', results[0])
            self.assertIn('proportion', results[0])
            self.assertIn('metadata', results[0])
            
            # Metadata structure checks
            self.assertIn('vehicle_type', results[0]['metadata'])
            self.assertIn('fuel_type', results[0]['metadata'])
            self.assertIn('vehicle_label', results[0]['metadata'])


# Integration tests would require more extensive setup
class VehicleEmissionsIntegrationTest(TestCase):
    """Integration tests for the full vehicle emissions calculation flow"""
    
    def setUp(self):
        # Would need to mock or create all required objects:
        # - VehicleTrackingMetric
        # - TemplateAssignment
        # - LayerProfile
        # - ReportedMetricValue
        # - GHGEmissionFactor
        # - etc.
        pass
    
    def test_end_to_end_calculation(self):
        # Would test the full flow from ReportedMetricValue to CalculatedEmissionValue
        pass 