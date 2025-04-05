from django.db import models
from .templates import ESGMetricSubmission
from .polymorphic_metrics import BasicMetric, TabularMetric, MaterialTrackingMatrixMetric, TimeSeriesMetric, MultiFieldTimeSeriesMetric, MultiFieldMetric

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