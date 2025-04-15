from django.db import models
from .templates import ESGMetricSubmission
from .polymorphic_metrics import (
    BasicMetric, TabularMetric, MaterialTrackingMatrixMetric,
    TimeSeriesMetric, MultiFieldTimeSeriesMetric, MultiFieldMetric,
    VehicleTrackingMetric, VehicleType, FuelType
)

# --- Submission Data Models ---
# These models store the actual data values submitted for different metric types.
# Each has a ForeignKey to the main ESGMetricSubmission header record.

class BasicMetricData(models.Model):
    """Stores the single value for a BasicMetric submission."""
    submission = models.OneToOneField(
        ESGMetricSubmission,
        on_delete=models.CASCADE,
        related_name='basic_data' # Allows access via submission.basic_data
    )
    value_numeric = models.FloatField(null=True, blank=True, help_text="Submitted numeric value")
    value_text = models.TextField(null=True, blank=True, help_text="Submitted text value")

    class Meta:
        verbose_name = "Basic Metric Data"
        verbose_name_plural = "Basic Metric Data"

    def __str__(self):
        val = self.value_numeric if self.value_numeric is not None else self.value_text
        return f"Data for Submission {self.submission.pk}: {val}"

class TabularMetricRow(models.Model):
    """Stores a single row of data for a TabularMetric submission."""
    submission = models.ForeignKey(
        ESGMetricSubmission,
        on_delete=models.CASCADE,
        related_name='tabular_rows' # Allows access via submission.tabular_rows
    )
    row_index = models.PositiveIntegerField(help_text="Order of the row within the submission")
    # Stores the data for this row based on the metric's column_definitions
    row_data = models.JSONField(default=dict, help_text='Key-value pairs for the columns in this row')

    class Meta:
        ordering = ['submission', 'row_index']
        unique_together = ['submission', 'row_index']
        verbose_name = "Tabular Metric Row"
        verbose_name_plural = "Tabular Metric Rows"

    def __str__(self):
        return f"Row {self.row_index} for Submission {self.submission.pk}"

class MaterialMatrixDataPoint(models.Model):
    """Stores data for a specific material type in a specific period for a MaterialTrackingMatrixMetric submission."""
    submission = models.ForeignKey(
        ESGMetricSubmission,
        on_delete=models.CASCADE,
        related_name='material_data_points'
    )
    material_type = models.CharField(max_length=100, help_text="Name of the material type (e.g., Cardboard)")
    period = models.DateField(help_text="The period this data point represents (e.g., month end)")
    value = models.FloatField(null=True, blank=True)
    unit = models.CharField(max_length=50, blank=True, help_text="Unit used for this specific data point (if overrides default)")

    class Meta:
        ordering = ['submission', 'period', 'material_type']
        unique_together = ['submission', 'period', 'material_type']
        verbose_name = "Material Matrix Data Point"
        verbose_name_plural = "Material Matrix Data Points"

    def __str__(self):
        return f"{self.material_type} ({self.period}) for Submission {self.submission.pk}"

class TimeSeriesDataPoint(models.Model):
    """Stores a single data point for a TimeSeriesMetric submission."""
    submission = models.ForeignKey(
        ESGMetricSubmission,
        on_delete=models.CASCADE,
        related_name='timeseries_data_points'
    )
    period = models.DateField(help_text="The specific period this data point represents")
    value = models.FloatField(null=True, blank=True)

    class Meta:
        ordering = ['submission', 'period']
        unique_together = ['submission', 'period']
        verbose_name = "Time Series Data Point"
        verbose_name_plural = "Time Series Data Points"

    def __str__(self):
        return f"Data ({self.period}) for Submission {self.submission.pk}"

class MultiFieldTimeSeriesDataPoint(models.Model):
    """Stores data for all fields in a single period for a MultiFieldTimeSeriesMetric submission."""
    submission = models.ForeignKey(
        ESGMetricSubmission,
        on_delete=models.CASCADE,
        related_name='multifield_timeseries_data_points'
    )
    period = models.DateField(help_text="The specific period this row of data represents")
    # Stores the data for this period based on the metric's field_definitions
    field_data = models.JSONField(default=dict, help_text='Key-value pairs for the fields in this period')

    class Meta:
        ordering = ['submission', 'period']
        unique_together = ['submission', 'period']
        verbose_name = "Multi-Field Time Series Data Point"
        verbose_name_plural = "Multi-Field Time Series Data Points"

    def __str__(self):
        return f"Multi-field Data ({self.period}) for Submission {self.submission.pk}"

class MultiFieldDataPoint(models.Model):
    """Stores data for all fields for a MultiFieldMetric submission (non-time-series)."""
    submission = models.OneToOneField(
        ESGMetricSubmission,
        on_delete=models.CASCADE,
        related_name='multifield_data'
    )
    # Stores the data based on the metric's field_definitions
    field_data = models.JSONField(default=dict, help_text='Key-value pairs for the fields')

    class Meta:
        verbose_name = "Multi-Field Data Point"
        verbose_name_plural = "Multi-Field Data Points"

    def __str__(self):
        return f"Multi-field Data for Submission {self.submission.pk}"

class VehicleRecord(models.Model):
    """Stores metadata for a single vehicle in a VehicleTrackingMetric submission."""
    submission = models.ForeignKey(
        ESGMetricSubmission,
        on_delete=models.CASCADE,
        related_name='vehicle_records'
    )
    
    # Basic vehicle information
    brand = models.CharField(max_length=100, help_text="Vehicle brand/make")
    model = models.CharField(max_length=100, help_text="Vehicle model")
    registration_number = models.CharField(max_length=50, help_text="Vehicle registration/license plate number")
    
    # Type information - use ForeignKeys instead of CharFields
    vehicle_type = models.ForeignKey(
        VehicleType,
        on_delete=models.PROTECT,  # Use PROTECT to prevent accidental deletion
        related_name='vehicles',
        help_text="Type of vehicle (e.g., private car, truck)"
    )
    
    fuel_type = models.ForeignKey(
        FuelType,
        on_delete=models.PROTECT,  # Use PROTECT to prevent accidental deletion
        related_name='vehicles',
        help_text="Type of fuel used (e.g., petrol, diesel)"
    )
    
    # For backward compatibility during migration - these can be removed later
    vehicle_type_code = models.CharField(
        max_length=50, 
        blank=True, 
        null=True,
        help_text="DEPRECATED: Legacy vehicle type code"
    )
    
    fuel_type_code = models.CharField(
        max_length=50, 
        blank=True, 
        null=True,
        help_text="DEPRECATED: Legacy fuel type code"
    )
    
    # Additional information
    notes = models.TextField(blank=True, help_text="Additional notes about this vehicle")
    is_active = models.BooleanField(default=True, help_text="Whether this vehicle is currently active")
    
    class Meta:
        ordering = ['submission', 'brand', 'model', 'registration_number']
        verbose_name = "Vehicle Record"
        verbose_name_plural = "Vehicle Records"
        # No unique constraint since one submission can have multiple vehicles
    
    def __str__(self):
        return f"{self.brand} {self.model} ({self.registration_number}) - Submission {self.submission.pk}"

class VehicleMonthlyData(models.Model):
    """Stores monthly data for a vehicle in a VehicleTrackingMetric submission."""
    vehicle = models.ForeignKey(
        VehicleRecord,
        on_delete=models.CASCADE,
        related_name='monthly_data'
    )
    
    # Time period information
    period = models.DateField(help_text="The month-end date this data represents")
    
    # Performance metrics
    kilometers = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Distance traveled in kilometers during this period"
    )
    
    fuel_consumed = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Amount of fuel consumed in liters during this period"
    )
    
    # Emission calculation fields
    emission_calculated = models.BooleanField(
        default=False,
        help_text="Whether emissions have been calculated for this data point"
    )
    
    emission_value = models.DecimalField(
        max_digits=12,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Calculated emissions value (typically in kgCO2e)"
    )
    
    emission_unit = models.CharField(
        max_length=20,
        default="kgCO2e",
        help_text="Unit of emission calculation"
    )
    
    class Meta:
        ordering = ['vehicle', 'period']
        # Removed unique_together constraint to allow multiple entries per vehicle/period
        verbose_name = "Vehicle Monthly Data"
        verbose_name_plural = "Vehicle Monthly Data"
    
    def __str__(self):
        fuel_str = f"{self.fuel_consumed} L" if self.fuel_consumed is not None else "N/A"
        km_str = f"{self.kilometers} km" if self.kilometers is not None else "N/A"
        return f"{self.vehicle.brand} {self.vehicle.model} - {self.period.strftime('%b %Y')}: {km_str}, {fuel_str}"

class VehicleDataSource(models.Model):
    """Stores individual data sources for vehicles (from receipts, fuel logs, etc.)."""
    vehicle_monthly_data = models.ForeignKey(
        VehicleMonthlyData,
        on_delete=models.CASCADE,
        related_name='data_sources',
        help_text="The monthly summary record this data source contributes to"
    )
    
    # Source information
    source_date = models.DateField(help_text="Date of the data source (e.g., receipt date)")
    source_reference = models.CharField(
        max_length=100, 
        blank=True, 
        help_text="Reference number or identifier for this data source"
    )
    
    # Values from this specific source
    kilometers = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Distance traveled in kilometers from this source"
    )
    
    fuel_consumed = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Amount of fuel consumed in liters from this source"
    )
    
    # Additional fields
    location = models.CharField(
        max_length=255,
        blank=True,
        help_text="Location where data was collected"
    )
    
    notes = models.TextField(
        blank=True,
        help_text="Additional notes about this data source"
    )
    
    # For file attachments (optional - assuming ESGMetricEvidence handles this)
    # evidence = models.ForeignKey(
    #     'ESGMetricEvidence',
    #     on_delete=models.SET_NULL,
    #     null=True,
    #     blank=True,
    #     related_name='vehicle_data_sources'
    # )
    
    class Meta:
        ordering = ['vehicle_monthly_data', 'source_date']
        verbose_name = "Vehicle Data Source"
        verbose_name_plural = "Vehicle Data Sources"
    
    def __str__(self):
        return f"Source {self.source_reference} - {self.source_date} for {self.vehicle_monthly_data.vehicle}" 