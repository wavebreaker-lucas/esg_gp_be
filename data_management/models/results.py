# data_management/models/results.py
from django.db import models
from django.utils import timezone

# Import models needed for relationships
# Assuming factors.py and templates.py are in the same app/directory level
from .templates import ReportedMetricValue, TemplateAssignment
from .factors import GHGEmissionFactor, PollutantFactor, EnergyConversionFactor
from accounts.models import LayerProfile

class CalculatedEmissionValue(models.Model):
    """ Stores calculated GHG emission values derived from activity data and emission factors. """
    # Link to the source activity data
    source_activity_value = models.ForeignKey(
        ReportedMetricValue,
        on_delete=models.CASCADE, # If activity data is deleted, delete calculation
        related_name='derived_ghg_emissions'
    )
    # Link to the factor used
    emission_factor = models.ForeignKey(
        GHGEmissionFactor,
        on_delete=models.PROTECT, # Prevent deleting factor if used in calculations
        related_name='ghg_emission_calculations'
    )

    # --- Calculation Result ---
    calculated_value = models.DecimalField(
        max_digits=15, decimal_places=5,
        help_text="The calculated emission value (e.g., in kgCO2e or tCO2e)"
    )
    emission_unit = models.CharField(
        max_length=50,
        help_text="Unit of the calculated emission (e.g., tCO2e, kgCO2e)"
    )
    calculation_timestamp = models.DateTimeField(auto_now=True)

    # --- Context (Copied/derived for easier querying/reporting) ---
    assignment = models.ForeignKey(TemplateAssignment, on_delete=models.CASCADE)
    layer = models.ForeignKey(LayerProfile, on_delete=models.CASCADE)
    reporting_period = models.DateField(db_index=True)
    level = models.CharField(max_length=1, choices=ReportedMetricValue.LEVEL_CHOICES, db_index=True)
    # Store the scope derived from the factor for convenience
    emission_scope = models.CharField(max_length=10, blank=True, db_index=True)

    class Meta:
        unique_together = [['source_activity_value', 'emission_factor']] # Allow one calc per source/factor
        ordering = ['-reporting_period', 'assignment', 'layer', 'emission_scope']
        indexes = [
            models.Index(fields=['reporting_period', 'level', 'layer']), # Index for common filtering
        ]
        verbose_name = "Calculated GHG Emission Value"
        verbose_name_plural = "Calculated GHG Emission Values"

    def __str__(self):
        return f"{self.calculated_value} {self.emission_unit} ({self.emission_scope}) for {self.layer} ({self.reporting_period} - {self.level}) from RPV {self.source_activity_value_id}"

    def save(self, *args, **kwargs):
        # Automatically copy context from source activity and factor on save/update
        # Use update_fields if needed for efficiency during updates
        self.assignment = self.source_activity_value.assignment
        self.layer = self.source_activity_value.layer
        self.reporting_period = self.source_activity_value.reporting_period
        self.level = self.source_activity_value.level
        self.emission_scope = self.emission_factor.scope
        self.emission_unit = self.emission_factor.get_emission_unit() # Get from factor helper
        super().save(*args, **kwargs)


class CalculatedPollutantValue(models.Model):
    """ Stores calculated non-GHG pollutant values (NOx, SOx, PM) derived from activity data. """
    source_activity_value = models.ForeignKey(
        ReportedMetricValue,
        on_delete=models.CASCADE,
        related_name='derived_pollutant_emissions'
    )
    pollutant_factor = models.ForeignKey(
        PollutantFactor,
        on_delete=models.PROTECT,
        related_name='pollutant_emission_calculations'
    )

    # --- Calculation Results (in grams, based on PollutantFactor.pollutant_unit) ---
    calculated_nox_g = models.DecimalField(max_digits=15, decimal_places=5, null=True, blank=True)
    calculated_sox_g = models.DecimalField(max_digits=15, decimal_places=5, null=True, blank=True)
    calculated_pm_g = models.DecimalField(max_digits=15, decimal_places=5, null=True, blank=True)
    calculation_timestamp = models.DateTimeField(auto_now=True)

    # --- Context ---
    assignment = models.ForeignKey(TemplateAssignment, on_delete=models.CASCADE)
    layer = models.ForeignKey(LayerProfile, on_delete=models.CASCADE)
    reporting_period = models.DateField(db_index=True)
    level = models.CharField(max_length=1, choices=ReportedMetricValue.LEVEL_CHOICES, db_index=True)

    class Meta:
        unique_together = [['source_activity_value', 'pollutant_factor']] # One record per source/factor
        ordering = ['-reporting_period', 'assignment', 'layer']
        indexes = [
            models.Index(fields=['reporting_period', 'level', 'layer']), # Index for common filtering
        ]
        verbose_name = "Calculated Pollutant Value (NOx, SOx, PM)"
        verbose_name_plural = "Calculated Pollutant Values (NOx, SOx, PM)"

    def __str__(self):
        nox = self.calculated_nox_g if self.calculated_nox_g is not None else 'N/A'
        sox = self.calculated_sox_g if self.calculated_sox_g is not None else 'N/A'
        pm = self.calculated_pm_g if self.calculated_pm_g is not None else 'N/A'
        return f"Pollutants (NOx:{nox}, SOx:{sox}, PM:{pm}) g for {self.layer} ({self.reporting_period} - {self.level}) from RPV {self.source_activity_value_id}"

    def save(self, *args, **kwargs):
        # Auto-populate context
        self.assignment = self.source_activity_value.assignment
        self.layer = self.source_activity_value.layer
        self.reporting_period = self.source_activity_value.reporting_period
        self.level = self.source_activity_value.level
        super().save(*args, **kwargs)


class CalculatedEnergyValue(models.Model):
    """ Stores calculated energy values (e.g., in kWh) derived from activity data using conversion factors. """
    source_activity_value = models.ForeignKey(
        ReportedMetricValue,
        on_delete=models.CASCADE,
        related_name='derived_energy_values'
    )
    energy_conversion_factor = models.ForeignKey(
        EnergyConversionFactor,
        on_delete=models.PROTECT,
        related_name='energy_conversion_calculations'
    )

    # --- Calculation Result ---
    calculated_energy_value = models.DecimalField(max_digits=15, decimal_places=5, help_text="The calculated energy value")
    energy_unit = models.CharField(max_length=50, help_text="Unit of the calculated energy (e.g., kWh, MJ)")
    calculation_timestamp = models.DateTimeField(auto_now=True)

    # --- Context ---
    assignment = models.ForeignKey(TemplateAssignment, on_delete=models.CASCADE)
    layer = models.ForeignKey(LayerProfile, on_delete=models.CASCADE)
    reporting_period = models.DateField(db_index=True)
    level = models.CharField(max_length=1, choices=ReportedMetricValue.LEVEL_CHOICES, db_index=True)

    class Meta:
        unique_together = [['source_activity_value', 'energy_conversion_factor']]
        ordering = ['-reporting_period', 'assignment', 'layer']
        indexes = [
            models.Index(fields=['reporting_period', 'level', 'layer']), # Index for common filtering
        ]
        verbose_name = "Calculated Energy Value"
        verbose_name_plural = "Calculated Energy Values"

    def __str__(self):
        return f"{self.calculated_energy_value} {self.energy_unit} for {self.layer} ({self.reporting_period} - {self.level}) from RPV {self.source_activity_value_id}"

    def save(self, *args, **kwargs):
        # Auto-populate context
        self.assignment = self.source_activity_value.assignment
        self.layer = self.source_activity_value.layer
        self.reporting_period = self.source_activity_value.reporting_period
        self.level = self.source_activity_value.level
        self.energy_unit = self.energy_conversion_factor.target_unit # Use the target unit from the factor
        super().save(*args, **kwargs) 