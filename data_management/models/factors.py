# data_management/models/factors.py
import logging
from django.db import models
# from django.conf import settings # If using AUTH_USER_MODEL

logger = logging.getLogger(__name__)

class GHGEmissionFactor(models.Model):
    """ Stores emission factors used for calculating GHG emissions from activity data. """
    name = models.CharField(max_length=255, help_text="Constructed descriptive name (e.g., Diesel - Stationary combustion (Generators) - HKEX Appendix 2 2023)")
    source = models.CharField(max_length=255, blank=True, help_text="Source document name (e.g., HKEX Appendix 2, DEFRA)")
    source_url = models.URLField(max_length=500, blank=True, null=True, help_text="URL to the source document")

    year = models.PositiveIntegerField(db_index=True, help_text="Applicable year for the factor")

    # --- Factor Identification Criteria ---
    category = models.CharField(max_length=100, db_index=True, help_text="Broad activity category (e.g., Energy, Waste, Transport)")
    sub_category = models.CharField(max_length=255, db_index=True, help_text="Specific activity/material and detail (e.g., Grid Electricity, Diesel - Stationary combustion)")
    activity_unit = models.CharField(max_length=50, help_text="Unit of the *activity data* this factor applies to (e.g., MWh, tonne, km, kg, litres)")

    # --- Factor Value ---
    value = models.DecimalField(max_digits=15, decimal_places=7, help_text="The numerical emission factor")
    factor_unit = models.CharField(max_length=50, help_text="Unit of the factor (e.g., kgCO2e/MWh, tCO2e/tonne)") # Ensure consistency (e.g., always use kgCO2e/...)

    # --- Context ---
    region = models.CharField(max_length=100, blank=True, null=True, db_index=True, help_text="Geographic region applicability (e.g., UK, PRC, HK, ALL)")
    scope = models.CharField(max_length=10, blank=True, db_index=True, help_text="Emission scope (e.g., Scope 1, Scope 2, Scope 3)")

    # Optional: Add fields if you need to track individual GHGs
    # value_co2 = models.DecimalField(max_digits=15, decimal_places=7, null=True, blank=True)
    # value_ch4_co2e = models.DecimalField(max_digits=15, decimal_places=7, null=True, blank=True, help_text="CH4 factor converted to CO2e using GWP")
    # value_n2o_co2e = models.DecimalField(max_digits=15, decimal_places=7, null=True, blank=True, help_text="N2O factor converted to CO2e using GWP")

    class Meta:
        # Ensure factors are unique for a given context
        unique_together = [['year', 'category', 'sub_category', 'activity_unit', 'factor_unit', 'region', 'scope']] # Added scope for uniqueness
        ordering = ['-year', 'scope', 'category', 'sub_category', 'region']
        verbose_name = "GHG Emission Factor"
        verbose_name_plural = "GHG Emission Factors"

    def __str__(self):
        region_str = f" [{self.region}]" if self.region else ""
        scope_str = f"S{self.scope} " if self.scope else ""
        return f"{scope_str}{self.category} - {self.sub_category}{region_str} ({self.year}) = {self.value} {self.factor_unit}"

    def get_emission_unit(self):
        """ Helper to extract the emission unit part (e.g., 'kgCO2e') from the factor unit. """
        if '/' in self.factor_unit:
            return self.factor_unit.split('/')[0]
        logger.warning(f"Could not parse emission unit from factor_unit: {self.factor_unit} for factor {self.pk}")
        return "CO2e" # Default or raise error


class PollutantFactor(models.Model):
    """ Stores factors for calculating non-GHG pollutants (NOx, SOx, PM) from activity data. """
    category = models.CharField(max_length=100, db_index=True, help_text="Broad activity category (e.g., Gaseous Fuel Consumption, Vehicles)")
    sub_category = models.CharField(max_length=255, db_index=True, help_text="Specific activity/fuel/vehicle type (e.g., Towngas, Private cars)")
    activity_unit = models.CharField(max_length=50, help_text="Unit of the activity data (e.g., Unit, MJ, L, kg, km)")

    # --- Factor Values (per activity unit) ---
    nox_factor = models.DecimalField(max_digits=15, decimal_places=7, null=True, blank=True, help_text="NOx factor value per activity unit (e.g., g/Unit)")
    sox_factor = models.DecimalField(max_digits=15, decimal_places=7, null=True, blank=True, help_text="SOx factor value per activity unit (e.g., g/Unit)")
    pm_factor = models.DecimalField(max_digits=15, decimal_places=7, null=True, blank=True, help_text="PM factor value per activity unit (e.g., g/km)")
    pollutant_unit = models.CharField(max_length=50, default='g', help_text="Unit of the calculated pollutant (usually grams, 'g')") # Unit the factors produce

    # --- Context ---
    year = models.PositiveIntegerField(db_index=True, help_text="Applicable year for the factor")
    source = models.CharField(max_length=255, blank=True, help_text="Source document name")
    source_url = models.URLField(max_length=500, blank=True, null=True)
    region = models.CharField(max_length=100, blank=True, null=True, db_index=True, help_text="Geographic region applicability (e.g., HK / PRC, HK, ALL)")

    class Meta:
        unique_together = [['year', 'category', 'sub_category', 'activity_unit', 'region']]
        ordering = ['-year', 'category', 'sub_category', 'region']
        verbose_name = "Pollutant Factor (NOx, SOx, PM)"
        verbose_name_plural = "Pollutant Factors (NOx, SOx, PM)"

    def __str__(self):
        region_str = f" [{self.region}]" if self.region else ""
        return f"Pollutant: {self.category} - {self.sub_category} ({self.activity_unit}){region_str} ({self.year})"


class EnergyConversionFactor(models.Model):
    """ Stores factors for converting activity data units to a standard energy unit (e.g., kWh). """
    category = models.CharField(max_length=100, db_index=True, help_text="Broad activity category (e.g., Petroleum products, Coals, Natural gas)")
    sub_category = models.CharField(max_length=255, db_index=True, help_text="Specific fuel/activity type (e.g., Gas/ Diesel oil, Anthracite, Towngas)")
    activity_unit = models.CharField(max_length=50, help_text="Unit of the *activity data* (e.g., litres, kg, Unit (= 0.048 GJ), cubic meter)")

    # --- Factor Value ---
    conversion_factor = models.DecimalField(max_digits=15, decimal_places=7, help_text="Numerical factor to convert activity unit to target unit")
    target_unit = models.CharField(max_length=50, default='kWh', help_text="The target energy unit after conversion (e.g., kWh, MJ)")

    # --- Context ---
    year = models.PositiveIntegerField(db_index=True, help_text="Applicable year for the factor")
    source = models.CharField(max_length=255, blank=True, help_text="Source document name")
    source_url = models.URLField(max_length=500, blank=True, null=True)
    region = models.CharField(max_length=100, blank=True, null=True, db_index=True, help_text="Geographic region applicability")

    class Meta:
        unique_together = [['year', 'category', 'sub_category', 'activity_unit', 'target_unit', 'region']]
        ordering = ['-year', 'category', 'sub_category', 'region']
        verbose_name = "Energy Conversion Factor"
        verbose_name_plural = "Energy Conversion Factors"

    def __str__(self):
        region_str = f" [{self.region}]" if self.region else ""
        return f"Energy: {self.category} - {self.sub_category} ({self.activity_unit}){region_str} ({self.year}) -> {self.conversion_factor} {self.target_unit}" 