# data_management/models/results.py
from django.db import models
from django.utils import timezone
from decimal import Decimal
import uuid

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
    
    # Link to specific vehicle record (for vehicle emissions only)
    vehicle_record = models.ForeignKey(
        'data_management.VehicleRecord',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='emission_calculations',
        help_text="For vehicle emissions, the specific vehicle this calculation applies to"
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

    # --- New fields for multi-factor calculations ---
    calculation_metadata = models.JSONField(
        default=dict, 
        blank=True,
        help_text="Additional calculation metadata, especially for composite calculations"
    )
    
    related_group_id = models.UUIDField(
        null=True, 
        blank=True,
        db_index=True,
        help_text="UUID linking related calculations from the same source"
    )
    
    is_primary_record = models.BooleanField(
        default=True,
        db_index=True,
        help_text="Whether this is the primary calculation record for the source"
    )
    
    proportion = models.DecimalField(
        max_digits=5, 
        decimal_places=4, 
        default='1.0',  # Use string, not Decimal object
        help_text="Proportion this calculation contributes to the total (0.0-1.0)"
    )

    # --- Context (Copied/derived for easier querying/reporting) ---
    assignment = models.ForeignKey(TemplateAssignment, on_delete=models.CASCADE)
    layer = models.ForeignKey(LayerProfile, on_delete=models.CASCADE)
    reporting_period = models.DateField(db_index=True)
    level = models.CharField(max_length=1, choices=ReportedMetricValue.LEVEL_CHOICES, db_index=True)
    # Store the scope derived from the factor for convenience
    emission_scope = models.CharField(max_length=10, blank=True, db_index=True)

    class Meta:
        # Update unique_together to include vehicle_record
        unique_together = [['source_activity_value', 'emission_factor', 'related_group_id', 'is_primary_record', 'vehicle_record']]
        ordering = ['-reporting_period', 'assignment', 'layer', 'emission_scope', '-is_primary_record']
        indexes = [
            models.Index(fields=['reporting_period', 'level', 'layer']), # Index for common filtering
            models.Index(fields=['is_primary_record']), # Index for filtering primary records
            models.Index(fields=['related_group_id']), # Index for finding all related records
            models.Index(fields=['vehicle_record']), # Index for finding emissions by vehicle
        ]
        verbose_name = "Calculated GHG Emission Value"
        verbose_name_plural = "Calculated GHG Emission Values"

    def __str__(self):
        primary_indicator = " (Primary)" if self.is_primary_record else ""
        proportion_str = f" [{self.proportion*100:.1f}%]" if self.proportion != 1 else ""
        return f"{self.calculated_value} {self.emission_unit} ({self.emission_scope}){primary_indicator}{proportion_str} for {self.layer} ({self.reporting_period} - {self.level}) from RPV {self.source_activity_value_id}"

    def save(self, *args, **kwargs):
        # Automatically copy context from source activity and factor on save/update
        
        if self.source_activity_value_id and not self.assignment_id:
            self.assignment = self.source_activity_value.assignment
            self.layer = self.source_activity_value.layer
            self.reporting_period = self.source_activity_value.reporting_period
            self.level = self.source_activity_value.level
        
        if self.emission_factor_id and not self.emission_scope:
            self.emission_scope = self.emission_factor.scope
            
        if self.emission_factor_id and not self.emission_unit:
            # Get the emission unit from the factor 
            if hasattr(self.emission_factor, 'get_emission_unit'):
                self.emission_unit = self.emission_factor.get_emission_unit()
            else:
                self.emission_unit = self.emission_factor.factor_unit
        
        # Continue with the normal save operation
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