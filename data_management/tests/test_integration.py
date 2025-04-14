"""
Integration tests for vehicle emissions calculations.
Tests the full flow from data entry to emission calculation results.
"""

import json
from decimal import Decimal
from django.test import TestCase, TransactionTestCase
from django.utils import timezone
import datetime

from data_management.models.factors import GHGEmissionFactor
from data_management.models.templates import ReportedMetricValue, TemplateAssignment, ESGForm, ESGFormCategory, Template
from data_management.models.polymorphic_metrics import VehicleTrackingMetric
from data_management.models.results import CalculatedEmissionValue
from data_management.models.submission_data import VehicleRecord, VehicleMonthlyData
from data_management.services.emissions import calculate_emissions_for_activity_value
from accounts.models import LayerProfile

from .test_mock_vehicle_data import (
    SAMPLE_VEHICLE_DATA, 
    SAMPLE_EMISSION_MAPPING,
    SAMPLE_VEHICLE_TYPES,
    SAMPLE_FUEL_TYPES
)


class VehicleEmissionsIntegrationTest(TransactionTestCase):
    """
    Integration tests for the full vehicle emissions calculation flow.
    Uses TransactionTestCase to reset DB state between tests.
    """
    
    def setUp(self):
        """Set up the required test objects for integration testing"""
        # Create a layer
        self.layer = LayerProfile.objects.create(
            company_name="Test Company"
        )
        
        # Create a category for the form
        self.category = ESGFormCategory.objects.create(code="TEST-CAT-INT", name="Test Category Integration")
        
        # Create a form
        self.form = ESGForm.objects.create(
            category=self.category,
            code="ENV-VEH",
            name="Vehicle Emissions Form"
        )
        
        # Create a VehicleTrackingMetric
        self.metric = VehicleTrackingMetric.objects.create(
            form=self.form,
            name="Vehicle Tracking",
            emission_category="transport",
            vehicle_type_choices=SAMPLE_VEHICLE_TYPES,
            fuel_type_choices=SAMPLE_FUEL_TYPES,
            emission_factor_mapping=SAMPLE_EMISSION_MAPPING,
            location="HK"
        )
        
        # Create a template and link the form
        self.template = Template.objects.create(name="Test Integration Template")
        self.template.selected_forms.add(self.form)
        
        # Create an assignment
        self.assignment = TemplateAssignment.objects.create(
            template=self.template,
            layer=self.layer,
            reporting_period_start=datetime.date(2025, 1, 1),
            reporting_period_end=datetime.date(2025, 12, 31),
            reporting_year=2025
        )
        
        # Create emission factors
        self.diesel_factor = GHGEmissionFactor.objects.create(
            name="Transport - Cars Diesel",
            year=2025,
            category="transport",
            sub_category="transport_cars_diesel",
            activity_unit="liters",
            value=Decimal("2.70"),
            factor_unit="kgCO2e/liter",
            region="HK",
            scope="1"
        )
        
        self.petrol_factor = GHGEmissionFactor.objects.create(
            name="Transport - Cars Petrol",
            year=2025,
            category="transport",
            sub_category="transport_cars_petrol",
            activity_unit="liters",
            value=Decimal("2.40"),
            factor_unit="kgCO2e/liter",
            region="HK",
            scope="1"
        )
        
        self.commercial_factor = GHGEmissionFactor.objects.create(
            name="Transport - Light Commercial Diesel",
            year=2025,
            category="transport",
            sub_category="transport_light_commercial_diesel",
            activity_unit="liters",
            value=Decimal("2.90"),
            factor_unit="kgCO2e/liter",
            region="HK",
            scope="1"
        )
        
        # Create the aggregated ReportedMetricValue
        self.reported_value = ReportedMetricValue.objects.create(
            assignment=self.assignment,
            metric=self.metric,
            layer=self.layer,
            reporting_period=datetime.date(2025, 12, 31),
            level='A',
            aggregated_text_value=json.dumps(SAMPLE_VEHICLE_DATA),
            # The numeric value would typically be the total fuel consumed
            aggregated_numeric_value=420.0  # 100 + 120 + 200
        )
    
    def test_full_emission_calculation_flow(self):
        """Test the full flow from ReportedMetricValue to CalculatedEmissionValue"""
        # Ensure our metric has appropriate emission category/subcategory
        self.assertEqual(self.metric.emission_category, "transport")
        
        # Call the calculation service
        results = calculate_emissions_for_activity_value(self.reported_value)
        
        # Validate the results - should have 4 records:
        # 1. The primary composite record (total emissions)
        # 2-4. Individual vehicle emission records
        self.assertEqual(len(results), 4)
        
        # Check that we have one primary record
        primary_records = [r for r in results if r.is_primary_record]
        self.assertEqual(len(primary_records), 1)
        
        # Check that we have the correct number of component records
        component_records = [r for r in results if not r.is_primary_record]
        self.assertEqual(len(component_records), 3)
        
        # Validate the primary record
        primary = primary_records[0]
        self.assertEqual(primary.source_activity_value, self.reported_value)
        self.assertEqual(primary.proportion, Decimal('1.0'))
        self.assertTrue(primary.calculation_metadata.get('is_composite', False))
        self.assertEqual(primary.calculation_metadata.get('component_count'), 3)
        
        # Validate total emissions: 
        # 100 * 2.70 + 120 * 2.40 + 200 * 2.90 = 270 + 288 + 580 = 1138
        expected_total = Decimal('270') + Decimal('288') + Decimal('580')
        self.assertAlmostEqual(
            float(primary.calculated_value), 
            float(expected_total), 
            places=2
        )
        
        # Check that all component records share the same group_id
        group_id = primary.related_group_id
        self.assertIsNotNone(group_id)
        for record in component_records:
            self.assertEqual(record.related_group_id, group_id)
        
        # Check individual components
        # Find the diesel car record
        diesel_car = next(
            (r for r in component_records 
             if r.calculation_metadata.get('vehicle_type') == 'private_cars'
             and r.calculation_metadata.get('fuel_type') == 'diesel_oil'), 
            None
        )
        self.assertIsNotNone(diesel_car)
        self.assertAlmostEqual(
            float(diesel_car.calculated_value),
            float(100 * self.diesel_factor.value),
            places=2
        )
        
        # Verify all records have the correct context fields
        for record in results:
            self.assertEqual(record.assignment, self.assignment)
            self.assertEqual(record.layer, self.layer)
            self.assertEqual(record.reporting_period, self.reported_value.reporting_period)
            self.assertEqual(record.level, self.reported_value.level)
        
        # Verify that recalculating doesn't duplicate records
        previous_count = CalculatedEmissionValue.objects.count()
        calculate_emissions_for_activity_value(self.reported_value)
        self.assertEqual(CalculatedEmissionValue.objects.count(), previous_count)


class VehicleAggregationTest(TestCase):
    """
    Tests the aggregation of vehicle data from individual submissions.
    Focuses on the calculate_aggregate method of VehicleTrackingMetric.
    """
    
    def setUp(self):
        # Would set up multiple VehicleRecord and VehicleMonthlyData instances 
        # and then test the aggregation method
        pass
    
    def test_aggregate_method(self):
        # Would test the calculate_aggregate method of VehicleTrackingMetric
        pass 