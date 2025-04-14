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


class VehicleAggregationTest(TransactionTestCase):
    """
    Tests the aggregation of vehicle data from individual submissions.
    Focuses on the calculate_aggregate method of VehicleTrackingMetric.
    """
    
    def setUp(self):
        """Set up test data for aggregation test"""
        # Basic setup (Layer, Category, Form, Template, Assignment)
        self.layer = LayerProfile.objects.create(company_name="AggTest Co")
        self.category = ESGFormCategory.objects.create(code="AGG-CAT", name="Agg Category")
        self.form = ESGForm.objects.create(category=self.category, code="AGG-FORM", name="Agg Form")
        self.template = Template.objects.create(name="Agg Template")
        self.template.selected_forms.add(self.form)
        self.assignment = TemplateAssignment.objects.create(
            template=self.template,
            layer=self.layer,
            reporting_period_start=datetime.date(2024, 1, 1),
            reporting_period_end=datetime.date(2024, 12, 31),
            reporting_year=2024
        )
        
        # Create the VehicleTrackingMetric
        self.metric = VehicleTrackingMetric.objects.create(
            form=self.form,
            name="Vehicle Aggregation Test Metric",
            frequency='monthly' # Matches the data we'll create
        )
        
        # Create a single submission header
        # In a real scenario, data might come from multiple submissions, 
        # but for testing aggregation logic, one header is sufficient.
        self.submission = self.assignment.submissions.create(
            metric=self.metric,
            # submitted_by= # Optional: assign a user if needed
        )
        
        # --- Vehicle 1 Data --- 
        self.vehicle1 = VehicleRecord.objects.create(
            submission=self.submission,
            brand="Toyota", model="Camry", registration_number="V1",
            vehicle_type="private_cars", fuel_type="petrol"
        )
        # Create 12 months of data for Vehicle 1
        self.v1_total_fuel = Decimal('0')
        self.v1_total_km = Decimal('0')
        for month in range(1, 13):
            fuel = Decimal(f'{100 + month * 5:.2f}') # e.g., 105.00, 110.00, ...
            km = Decimal(f'{1000 + month * 50:.2f}') # e.g., 1050.00, 1100.00, ...
            VehicleMonthlyData.objects.create(
                vehicle=self.vehicle1,
                period=datetime.date(2024, month, 28), # Use end-of-month approx
                fuel_consumed=fuel,
                kilometers=km
            )
            self.v1_total_fuel += fuel
            self.v1_total_km += km
            
        # --- Vehicle 2 Data --- 
        self.vehicle2 = VehicleRecord.objects.create(
            submission=self.submission,
            brand="Ford", model="Transit", registration_number="V2",
            vehicle_type="light_goods_lte_2_5", fuel_type="diesel_oil"
        )
        # Create 12 months of data for Vehicle 2
        self.v2_total_fuel = Decimal('0')
        self.v2_total_km = Decimal('0')
        for month in range(1, 13):
            fuel = Decimal(f'{200 - month * 3:.2f}') # e.g., 197.00, 194.00, ...
            km = Decimal(f'{1500 - month * 20:.2f}') # e.g., 1480.00, 1460.00, ...
            VehicleMonthlyData.objects.create(
                vehicle=self.vehicle2,
                period=datetime.date(2024, month, 28),
                fuel_consumed=fuel,
                kilometers=km
            )
            self.v2_total_fuel += fuel
            self.v2_total_km += km
    
    def test_calculate_aggregate_annual(self):
        """Test the calculate_aggregate method for an annual level."""
        
        # Define the target aggregation period (full year 2024)
        start_date = datetime.date(2024, 1, 1)
        end_date = datetime.date(2024, 12, 31)
        
        # Get the PKs of relevant submissions (just one in this test)
        submission_pks = self.assignment.submissions.filter(metric=self.metric).values_list('pk', flat=True)
        
        # Call the aggregation method
        result = self.metric.calculate_aggregate(
            relevant_submission_pks=submission_pks,
            target_start_date=start_date,
            target_end_date=end_date,
            level='A' # Annual level
        )
        
        # --- Assertions --- 
        self.assertIsNotNone(result, "calculate_aggregate should return a result dictionary")
        
        # Check aggregation method and contribution count
        self.assertEqual(result.get('aggregation_method'), 'SUM')
        # Should count distinct submission headers contributing data
        self.assertEqual(result.get('contributing_submissions_count'), 1) 
        
        # Check aggregated numeric value (should be total fuel)
        expected_total_fuel = self.v1_total_fuel + self.v2_total_fuel
        self.assertAlmostEqual(
            Decimal(str(result.get('aggregated_numeric_value'))), 
            expected_total_fuel, 
            places=2
        )
        
        # Check aggregated text value (JSON string)
        aggregated_text = result.get('aggregated_text_value')
        self.assertIsNotNone(aggregated_text)
        try:
            agg_data = json.loads(aggregated_text)
        except json.JSONDecodeError:
            self.fail("aggregated_text_value is not valid JSON")
            
        expected_total_km = self.v1_total_km + self.v2_total_km
        
        self.assertIn('total_fuel_consumed_liters', agg_data)
        self.assertAlmostEqual(Decimal(str(agg_data['total_fuel_consumed_liters'])), expected_total_fuel, places=2)
        
        self.assertIn('total_kilometers', agg_data)
        self.assertAlmostEqual(Decimal(str(agg_data['total_kilometers'])), expected_total_km, places=2)
        
        self.assertIn('vehicle_count', agg_data)
        self.assertEqual(agg_data['vehicle_count'], 2) # We created 2 vehicles 