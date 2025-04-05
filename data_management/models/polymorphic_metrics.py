# Polymorphic models for ESG Metrics will be defined here. 
from django.db import models
from polymorphic.models import PolymorphicModel
from .templates import ESGForm # Import necessary related models

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
        ESGForm, 
        on_delete=models.CASCADE, 
        related_name='polymorphic_metrics' # Use a new related_name to avoid conflicts initially
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
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
    help_text = models.TextField(blank=True, help_text="Optional guidance text displayed to the user in the form")

    class Meta:
        ordering = ['form', 'order']
        verbose_name = "ESG Metric (Base)"
        verbose_name_plural = "ESG Metrics (Base)"

    def __str__(self):
        return f"{self.form.code} - {self.name}"

# --- Specialized Metric Types ---

class BasicMetric(BaseESGMetric):
    """Metrics representing a single value (numeric, text, percentage, or custom unit)."""
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

class TabularMetric(BaseESGMetric):
    """Metrics representing tabular data where users can add/edit rows based on defined columns."""
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

class MultiFieldTimeSeriesMetric(BaseESGMetric):
    """Metrics tracking multiple predefined fields over time, potentially with calculations."""
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

# class VehicleTrackingMetric(BaseESGMetric): ...
# class NarrativeMetric(BaseESGMetric): ...
# class MultiFieldMetric(BaseESGMetric): ... # For fixed multi-value fields if needed 