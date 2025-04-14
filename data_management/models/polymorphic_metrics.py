# Polymorphic models for ESG Metrics will be defined here. 
from django.db import models
from polymorphic.models import PolymorphicModel
import datetime
from django.db.models import QuerySet, Sum, Avg
from django.utils import timezone # Needed for potential 'LAST' logic refinement

# Choices definitions (can be moved to a central location later if needed)
LOCATION_CHOICES = [
    ('HK', 'Hong Kong'),
    ('PRC', 'Mainland China'),
    ('ALL', 'All Locations'),
]

UNIT_TYPES = [
    # Environmental
    ('kWh', 'Kilowatt Hours'),
    ('MWh', 'Megawatt Hours'),
    ('m3', 'Cubic Meters'),
    ('tonnes', 'Tonnes'),
    ('tCO2e', 'Tonnes CO2 Equivalent'),
    # Social
    ('person', 'Person'),
    ('hours', 'Hours'),
    ('days', 'Days'),
    ('count', 'Count'),
    ('percentage', 'Percentage'),
    # Generic/Custom
    ('text', 'Text'),
    ('custom', 'Custom Unit'),
]

class BaseESGMetric(PolymorphicModel):
    """Base model for all ESG metrics using django-polymorphic."""
    form = models.ForeignKey(
        'data_management.ESGForm',
        on_delete=models.CASCADE, 
        related_name='polymorphic_metrics' # Use a new related_name to avoid conflicts initially
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    order = models.PositiveIntegerField(default=0, help_text="Display order within the form")
    requires_evidence = models.BooleanField(default=False, help_text="Does this metric require supporting evidence?")
    validation_rules = models.JSONField(
        default=dict, 
        blank=True, 
        help_text="Optional validation rules (e.g., min/max, regex for text)"
    )
    location = models.CharField(
        max_length=3, 
        choices=LOCATION_CHOICES, 
        default='ALL', 
        help_text="Location relevance (e.g., HK, PRC, ALL)"
    )
    is_required = models.BooleanField(default=True, help_text="Whether users must provide input for this metric")
    ocr_analyzer_id = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Custom Azure Form Recognizer model ID for evidence processing (if applicable)"
    )
    aggregates_inputs = models.BooleanField(
        default=False,
        help_text="Indicates if this metric's value is derived from aggregating other inputs/metrics"
    )
    help_text = models.TextField(blank=True, null=True, help_text="Optional guidance text displayed to the user in the form")

    # --- NEW FIELD ---
    allow_multiple_submissions_per_period = models.BooleanField(
        default=False, # Default to disallowing multiple submissions
        help_text="Allow multiple submission records for the same assignment, metric, and reporting period? (Set True for metrics expecting data from multiple sources per period, like TimeSeries from different facilities)"
    )

    # --- NEW Fields for Emission Calculation Link ---
    emission_category = models.CharField(
        max_length=100, blank=True, null=True, db_index=True,
        help_text="Category used to lookup GHG Emission Factors (e.g., Energy, Waste)"
    )
    emission_sub_category = models.CharField(
        max_length=255, blank=True, null=True, db_index=True,
        help_text="Sub-category used to lookup GHG Emission Factors (e.g., Grid Electricity, Landfill Waste)"
    )

    # --- NEW Fields for Pollutant Calculation Link ---
    pollutant_category = models.CharField(
        max_length=100, blank=True, null=True, db_index=True,
        help_text="Category used to lookup Pollutant Factors (e.g., Vehicles, Gaseous Fuel Consumption)"
    )
    pollutant_sub_category = models.CharField(
        max_length=255, blank=True, null=True, db_index=True,
        help_text="Sub-category used to lookup Pollutant Factors (e.g., Private cars, Towngas)"
    )

    # --- NEW Fields for Energy Conversion Link ---
    energy_category = models.CharField(
        max_length=100, blank=True, null=True, db_index=True,
        help_text="Category used to lookup Energy Conversion Factors (e.g., Petroleum products, Natural gas)"
    )
    energy_sub_category = models.CharField(
        max_length=255, blank=True, null=True, db_index=True,
        help_text="Sub-category used to lookup Energy Conversion Factors (e.g., Gas/ Diesel oil, Towngas)"
    )

    class Meta:
        ordering = ['form', 'order']
        verbose_name = "ESG Metric (Base)"
        verbose_name_plural = "ESG Metrics (Base)"

    def __str__(self):
        return f"{self.form.code} - {self.name}"

    # --- Add the abstract aggregation method ---
    def calculate_aggregate(self, relevant_submission_pks: QuerySet[int], target_start_date: datetime.date, target_end_date: datetime.date, level: str) -> dict | None:
        """
        Calculates the aggregated value for this metric based on relevant submissions
        within the specified date range and aggregation level.

        Args:
            relevant_submission_pks: A QuerySet of primary keys for ESGMetricSubmission
                                     headers relevant to the overall context (assignment, layer).
                                     NOTE: This represents *potentially* relevant submissions. The method
                                     needs to filter the actual data points based on dates if applicable.
            target_start_date: The start date of the aggregation period.
            target_end_date: The end date of the aggregation period.
            level: The aggregation level ('M', 'A', etc.).

        Returns:
            A dictionary containing:
                {
                    'aggregated_numeric_value': float | None,
                    'aggregated_text_value': str | None,
                    'aggregation_method': str, # e.g., 'SUM', 'AVG', 'LAST', 'COUNT'
                    'contributing_submissions_count': int # Count of distinct submission headers whose data was *used*
                }
            Returns None if no relevant data is found or aggregation is not applicable.
        """
        # Default implementation for subclasses that don't override
        raise NotImplementedError(f"Aggregation logic not implemented for metric type: {self.__class__.__name__}")

# --- Specialized Metric Types ---

class BasicMetric(BaseESGMetric):
    """Metrics representing a single value (numeric, text, percentage, or custom unit)."""
    # Inherits allow_multiple_submissions_per_period=False (default)
    unit_type = models.CharField(
        max_length=20, 
        choices=UNIT_TYPES, 
        default='count', 
        help_text="The type of unit this metric uses"
    )
    custom_unit = models.CharField(
        max_length=50, 
        blank=True, 
        null=True, 
        help_text="Specify the unit if unit_type is 'custom'"
    )

    class Meta:
        verbose_name = "Basic Metric"
        verbose_name_plural = "Basic Metrics"

    def __str__(self):
        unit_display = ""
        if self.unit_type == 'custom' and self.custom_unit:
            unit_display = f" ({self.custom_unit})"
        elif self.unit_type != 'text': # Don't show unit for plain text
            unit_display = f" ({self.get_unit_type_display()})"
        return f"[Basic] {super().__str__()}{unit_display}"

    # --- Implement aggregation for BasicMetric ---
    def calculate_aggregate(self, relevant_submission_pks: QuerySet[int], target_start_date: datetime.date, target_end_date: datetime.date, level: str) -> dict | None:
        from .templates import ESGMetricSubmission # Local import to avoid circularity at module level
        from .submission_data import BasicMetricData

        # Aggregate ALL linked data points, regardless of target_start/end_date for BasicMetric
        # The period/level defines WHEN the aggregate is stored, not WHICH basic inputs to sum/take last of.
        data_points = BasicMetricData.objects.filter(submission_id__in=relevant_submission_pks)
        count = data_points.count()

        if count == 0:
            return None

        aggregated_numeric = None
        aggregated_text = None
        agg_method = 'UNKNOWN'
        contributing_submissions_count = data_points.values('submission_id').distinct().count()

        if self.unit_type == 'text':
            # Get the data point associated with the most recent submission among the relevant ones
            last_submission_pk = ESGMetricSubmission.objects.filter(
                pk__in=relevant_submission_pks
            ).order_by('-submitted_at', '-pk').values_list('pk', flat=True).first()

            if last_submission_pk:
                last_data = data_points.filter(submission_id=last_submission_pk).first()
                if last_data:
                    aggregated_text = last_data.value_text
            agg_method = 'LAST'
        else: # Numeric types
            # TODO: Allow configuration of SUM/AVG on BasicMetric itself? Defaulting to SUM.
            result = data_points.aggregate(total=Sum('value_numeric'))
            aggregated_numeric = result.get('total')
            agg_method = 'SUM'

        return {
            'aggregated_numeric_value': aggregated_numeric,
            'aggregated_text_value': aggregated_text,
            'aggregation_method': agg_method,
            'contributing_submissions_count': contributing_submissions_count
        }

class TabularMetric(BaseESGMetric):
    """Metrics representing tabular data where users can add/edit rows based on defined columns."""
    # Inherits allow_multiple_submissions_per_period=False (default)
    column_definitions = models.JSONField(
        default=list, 
        help_text='Structure of table columns. E.g., [{"key": "col_a", "label": "Column A", "type": "text", "required": true}]'
    )
    allow_adding_rows = models.BooleanField(default=True, help_text="Can users add new rows to the table?")
    allow_deleting_rows = models.BooleanField(default=True, help_text="Can users delete rows from the table?")
    max_rows = models.PositiveIntegerField(null=True, blank=True, help_text="Optional limit on the number of rows allowed")
    min_rows = models.PositiveIntegerField(default=0, help_text="Minimum number of rows required (0 means optional)")

    class Meta:
        verbose_name = "Tabular Metric"
        verbose_name_plural = "Tabular Metrics"

    def __str__(self):
        cols = len(self.column_definitions) if isinstance(self.column_definitions, list) else 0
        return f"[Tabular ({cols} cols)] {super().__str__()}"

class MaterialTrackingMatrixMetric(BaseESGMetric):
    """Metrics for tracking materials (e.g., waste, packaging) by type across monthly periods."""
    # Inherits allow_multiple_submissions_per_period=False (default) - assuming one matrix submission covers the period. Can be overridden if needed.
    MATERIAL_CATEGORIES = [
        ('waste', 'Waste'),
        ('packaging', 'Packaging'),
        ('other', 'Other Material')
    ]
    category = models.CharField(
        max_length=50, 
        choices=MATERIAL_CATEGORIES, 
        default='waste', 
        help_text="The category of material being tracked"
    )
    max_material_types = models.PositiveIntegerField(
        default=10, 
        help_text="Maximum number of material type columns users can define"
    )
    default_unit = models.CharField(
        max_length=50, 
        default="tonnes", 
        help_text="Default unit for material amounts (e.g., tonnes, kg, m3)"
    )
    allow_custom_units_per_type = models.BooleanField(
        default=False, 
        help_text="Allow users to specify different units for each material type column?"
    )
    fixed_time_period = models.CharField(
        max_length=20, 
        default='monthly', 
        choices=[('monthly', 'Monthly'), ('quarterly', 'Quarterly'), ('annual', 'Annual')],
        help_text="The time period represented by the rows (usually monthly)"
    )

    class Meta:
        verbose_name = "Material Tracking Matrix Metric"
        verbose_name_plural = "Material Tracking Matrix Metrics"

    def __str__(self):
        return f"[Material Matrix - {self.get_category_display()}] {super().__str__()}"

# Potential future additions:
class TimeSeriesMetric(BaseESGMetric):
    """Metrics reported periodically (e.g., monthly energy use)."""
    REPORTING_FREQUENCY_CHOICES = [
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('annual', 'Annual'),
    ]
    AGGREGATION_METHOD_CHOICES = [
        ('SUM', 'Sum'), 
        ('AVG', 'Average'), 
        ('LAST', 'Last Value')
    ]

    frequency = models.CharField(
        max_length=20, 
        choices=REPORTING_FREQUENCY_CHOICES, 
        default='monthly',
        help_text="How often is data expected for this metric?"
    )
    aggregation_method = models.CharField(
        max_length=20,
        choices=AGGREGATION_METHOD_CHOICES,
        default='SUM',
        help_text="How should values be aggregated over a larger period (e.g., monthly sum to annual)?"
    )
    # Potentially add unit_type here if time series are typically numeric/custom
    unit_type = models.CharField(max_length=20, choices=UNIT_TYPES, default='count') 
    custom_unit = models.CharField(max_length=50, blank=True, null=True, help_text="Specify unit if unit_type is 'custom'")

    class Meta:
        verbose_name = "Time Series Metric"
        verbose_name_plural = "Time Series Metrics"

    def __str__(self):
        return f"[Time Series - {self.get_frequency_display()}] {super().__str__()}"

    # --- Implement aggregation for TimeSeriesMetric ---
    def calculate_aggregate(self, relevant_submission_pks: QuerySet[int], target_start_date: datetime.date, target_end_date: datetime.date, level: str) -> dict | None:
        from .templates import ESGMetricSubmission # Local import
        from .submission_data import TimeSeriesDataPoint

        # Fetch all potentially relevant data points
        all_data_points = TimeSeriesDataPoint.objects.filter(submission_id__in=relevant_submission_pks)

        # Filter by the data point's own period matching the target aggregation window
        points_in_period = all_data_points.filter(
            period__gte=target_start_date,
            period__lte=target_end_date
        )

        count = points_in_period.count()
        if count == 0:
            return None

        aggregated_numeric = None
        aggregated_text = None # Assuming TimeSeries is numeric for now
        agg_method = self.aggregation_method
        # Count distinct submissions contributing data points *within this period*
        contributing_submissions_count = points_in_period.values('submission_id').distinct().count()

        if agg_method == 'SUM':
            result = points_in_period.aggregate(total=Sum('value'))
            aggregated_numeric = result.get('total')
        elif agg_method == 'AVG':
            result = points_in_period.aggregate(avg=Avg('value'))
            aggregated_numeric = result.get('avg')
        elif agg_method == 'LAST':
            # Find the latest submission *among those that have points in this period*
            relevant_pks_in_period = points_in_period.values_list('submission_id', flat=True).distinct()
            last_submission_in_period_pk = ESGMetricSubmission.objects.filter(
                pk__in=relevant_pks_in_period
            ).order_by('-submitted_at', '-pk').values_list('pk', flat=True).first()

            if last_submission_in_period_pk:
                # Get the data point associated with that latest submission (should only be one per period per submission typically for TimeSeries)
                last_data = points_in_period.filter(submission_id=last_submission_in_period_pk).order_by('-period').first()
                if last_data:
                    aggregated_numeric = last_data.value
            else:
                # Should not happen if count > 0, but safety check
                aggregated_numeric = None
        else:
            # Should not happen if choices are enforced, but handle unexpected method
            agg_method = 'UNKNOWN'
            aggregated_numeric = None
            contributing_submissions_count = 0 # Mark as unknown contribution
            # Maybe log a warning here?
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Unsupported aggregation method '{self.aggregation_method}' for TimeSeriesMetric {self.pk}")

        # Return None if the chosen method didn't produce a value (e.g., LAST found no submission)
        if aggregated_numeric is None and aggregated_text is None:
            # Ensure count is zero if no value was produced, otherwise could be misleading
            contributing_submissions_count = 0
            return None

        return {
            'aggregated_numeric_value': aggregated_numeric,
            'aggregated_text_value': aggregated_text,
            'aggregation_method': agg_method,
            'contributing_submissions_count': contributing_submissions_count
        }

class MultiFieldTimeSeriesMetric(BaseESGMetric):
    """Metrics tracking multiple predefined fields over time, potentially with calculations."""
    # Consider overriding default? If multiple sources might submit partial data, set True.
    # If one submission contains all fields for the period, keep False. Let's assume False for now.
    # allow_multiple_submissions_per_period = models.BooleanField(default=True, ...) # Optional override

    REPORTING_FREQUENCY_CHOICES = [
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('annual', 'Annual'),
        # Add others like weekly if needed
    ]
    # Example field_definitions: 
    # [{"key": "sold", "label": "Total Sold", "type": "number", "unit": "count"}, 
    #  {"key": "recalled", "label": "Total Recalled", "type": "number", "unit": "count"},
    #  {"key": "percentage", "label": "Percentage", "type": "calculated", "formula": "recalled / sold * 100", "unit": "%"}]
    field_definitions = models.JSONField(
        default=list, 
        help_text="Definitions of the fixed fields/columns, including type, label, unit, and optional calculations."
    ) 
    frequency = models.CharField(
        max_length=20, 
        choices=REPORTING_FREQUENCY_CHOICES, 
        default='monthly',
        help_text="The time period represented by each row (e.g., monthly)."
    )
    show_total_row = models.BooleanField(default=True, help_text="Whether to display an automatically calculated total row.")
    # Define how totals are calculated if show_total_row is True
    # Example: {"sold": "SUM", "recalled": "SUM", "percentage": "RECALCULATE"} 
    total_row_aggregation = models.JSONField(
        default=dict, 
        blank=True, 
        help_text="Defines how each field is aggregated in the total row (e.g., SUM, AVG, RECALCULATE)."
    )

    class Meta:
        verbose_name = "Multi-Field Time Series Metric"
        verbose_name_plural = "Multi-Field Time Series Metrics"

    def __str__(self):
        fields = len(self.field_definitions) if isinstance(self.field_definitions, list) else 0
        return f"[Multi-Field TS ({fields} fields) - {self.get_frequency_display()}] {super().__str__()}"

class MultiFieldMetric(BaseESGMetric):
    """Metrics representing a fixed set of related fields reported together once per period."""
    # Example field_definitions: 
    # [{"key": "scope1", "label": "Scope 1 Emissions", "type": "number", "unit": "tCO2e"}, 
    #  {"key": "scope2", "label": "Scope 2 Emissions", "type": "number", "unit": "tCO2e"}]
    field_definitions = models.JSONField(
        default=list, 
        help_text="Definitions of the fixed fields/columns, including type, label, and unit."
    ) 

    class Meta:
        verbose_name = "Multi-Field Metric"
        verbose_name_plural = "Multi-Field Metrics"

    def __str__(self):
        fields = len(self.field_definitions) if isinstance(self.field_definitions, list) else 0
        return f"[Multi-Field ({fields} fields)] {super().__str__()}"

class VehicleTrackingMetric(BaseESGMetric):
    """Metrics for tracking multiple vehicles with monthly fuel consumption and distance data."""
    
    # Default vehicle type choices - can be extended through admin
    DEFAULT_VEHICLE_TYPES = [
        {"value": "private_cars", "label": "Private cars"},
        {"value": "light_goods_lte_2_5", "label": "Light goods vehicles (<=2.5tonnes)"},
        {"value": "light_goods_2_5_3_5", "label": "Light goods vehicles (2.5-3.5tonnes)"},
        {"value": "light_goods_3_5_5_5", "label": "Light goods vehicles (3.5-5.5tonnes)"},
        {"value": "medium_heavy_goods_5_5_15", "label": "Medium & Heavy goods vehicles (5.5-15tonnes)"},
        {"value": "medium_heavy_goods_gte_15", "label": "Medium & Heavy goods vehicles (>=15tonnes)"},
    ]
    
    # Default fuel type choices - can be extended through admin
    DEFAULT_FUEL_TYPES = [
        {"value": "diesel_oil", "label": "Diesel oil"},
        {"value": "lpg", "label": "LPG"},
        {"value": "petrol", "label": "Petrol"},
        {"value": "unleaded_petrol", "label": "Unleaded petrol"},
    ]
    
    # Default emission factor mapping
    DEFAULT_EMISSION_MAPPING = {
        # Vehicle type + fuel type combinations
        "private_cars_diesel_oil": "transport_cars_diesel",
        "private_cars_petrol": "transport_cars_petrol", 
        "private_cars_unleaded_petrol": "transport_cars_petrol",
        "private_cars_lpg": "transport_cars_lpg",
        
        # Light goods vehicles
        "light_goods_lte_2_5_diesel_oil": "transport_light_commercial_diesel",
        "light_goods_2_5_3_5_diesel_oil": "transport_light_commercial_diesel",
        "light_goods_3_5_5_5_diesel_oil": "transport_light_commercial_diesel",
        
        # Medium & heavy goods vehicles
        "medium_heavy_goods_5_5_15_diesel_oil": "transport_heavy_goods_diesel",
        "medium_heavy_goods_gte_15_diesel_oil": "transport_heavy_goods_diesel",
        
        # Fallbacks by fuel type only
        "diesel_oil": "transport_general_diesel",
        "petrol": "transport_general_petrol",
        "unleaded_petrol": "transport_general_petrol",
        "lpg": "transport_lpg"
    }
    
    # Configuration fields
    vehicle_type_choices = models.JSONField(
        default=list,  # Using callable 'list' instead of DEFAULT_VEHICLE_TYPES
        help_text="List of vehicle types available for selection"
    )
    
    fuel_type_choices = models.JSONField(
        default=list,  # Using callable 'list' instead of DEFAULT_FUEL_TYPES
        help_text="List of fuel types available for selection"
    )
    
    emission_factor_mapping = models.JSONField(
        default=dict,  # Using callable 'dict' instead of DEFAULT_EMISSION_MAPPING
        help_text="Mapping of vehicle_type + fuel_type combinations to emission subcategories"
    )
    
    reporting_year = models.PositiveIntegerField(
        default=2025,  # Using a static year instead of lambda function
        help_text="Default reporting year for vehicle data"
    )
    
    REPORTING_FREQUENCY_CHOICES = [
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('annual', 'Annual'),
    ]
    
    frequency = models.CharField(
        max_length=20,
        choices=REPORTING_FREQUENCY_CHOICES,
        default='monthly',
        help_text="Frequency of data collection for vehicles"
    )
    
    # Additional configuration
    show_registration_number = models.BooleanField(
        default=True,
        help_text="Whether to display and require vehicle registration number"
    )
    
    class Meta:
        verbose_name = "Vehicle Tracking Metric"
        verbose_name_plural = "Vehicle Tracking Metrics"
        
    def __str__(self):
        return f"[Vehicle Tracking - {self.get_frequency_display()}] {super().__str__()}"
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set this instance to allow multiple submissions as vehicles are tracked separately
        self.allow_multiple_submissions_per_period = True
        
        # Set default emission category for vehicle tracking
        if not self.emission_category:
            self.emission_category = "transport"
            
        # Initialize JSONFields with default values if they're empty
        if not self.vehicle_type_choices:
            self.vehicle_type_choices = self.DEFAULT_VEHICLE_TYPES
            
        if not self.fuel_type_choices:
            self.fuel_type_choices = self.DEFAULT_FUEL_TYPES
            
        if not self.emission_factor_mapping:
            self.emission_factor_mapping = self.DEFAULT_EMISSION_MAPPING
        
    def get_emission_subcategory(self, vehicle_type, fuel_type):
        """
        Dynamically determine the appropriate emission subcategory based on
        vehicle type and fuel type.
        
        Args:
            vehicle_type: The vehicle type code (e.g., 'private_cars')
            fuel_type: The fuel type code (e.g., 'diesel_oil')
            
        Returns:
            The appropriate emission subcategory code for lookup
        """
        # Try the specific vehicle_type + fuel_type combination
        specific_key = f"{vehicle_type}_{fuel_type}"
        if specific_key in self.emission_factor_mapping:
            return self.emission_factor_mapping[specific_key]
            
        # Try just the fuel type (more general)
        if fuel_type in self.emission_factor_mapping:
            return self.emission_factor_mapping[fuel_type]
            
        # Fall back to a constructed key if nothing else matched
        return f"transport_{vehicle_type}_{fuel_type}"
        
    def calculate_aggregate(self, relevant_submission_pks: QuerySet[int], target_start_date: datetime.date, target_end_date: datetime.date, level: str) -> dict | None:
        """Calculate aggregate for vehicle tracking metrics."""
        # Import here to avoid circular imports
        from ..models.submission_data import VehicleRecord, VehicleMonthlyData, VehicleDataSource
        from .templates import ESGMetricSubmission
        from django.db.models import Sum
        
        # Get all vehicle records for these submissions
        vehicle_records = VehicleRecord.objects.filter(
            submission_id__in=relevant_submission_pks
        )
        
        if not vehicle_records.exists():
            return None
            
        # Get vehicle monthly data for the target period
        monthly_data = VehicleMonthlyData.objects.filter(
            vehicle__in=vehicle_records,
            period__gte=target_start_date,
            period__lte=target_end_date
        )
        
        if not monthly_data.exists():
            return None
            
        # Aggregate fuel consumption across all vehicles in the period
        total_fuel = monthly_data.aggregate(total=Sum('fuel_consumed'))['total'] or 0
        # Aggregate kilometers across all vehicles in the period
        total_km = monthly_data.aggregate(total=Sum('kilometers'))['total'] or 0
        
        # Count distinct submissions that contributed data
        contributing_submissions_count = vehicle_records.values('submission_id').distinct().count()
        
        # For annual aggregation, we return the total fuel and kilometers
        # For monthly, we would filter by the specific month
        
        # Create a JSON structure with the aggregated data
        aggregated_text_value = {
            'total_fuel_consumed_liters': float(total_fuel),
            'total_kilometers': float(total_km),
            'vehicle_count': vehicle_records.count()
        }
        
        # For numeric value, use the total fuel consumption as the primary metric
        # This will be used for emissions calculations
        return {
            'aggregated_numeric_value': float(total_fuel),
            'aggregated_text_value': str(aggregated_text_value),
            'aggregation_method': 'SUM',
            'contributing_submissions_count': contributing_submissions_count
        }

# class NarrativeMetric(BaseESGMetric): ...