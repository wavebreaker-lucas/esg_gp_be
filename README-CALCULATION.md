# ESG Calculation Framework

## Overview

This document outlines the backend framework designed to calculate derived environmental metrics, such as Greenhouse Gas (GHG) emissions (CO2e), specific pollutants (NOx, SOx, PM), and standardized energy values (kWh), based on the aggregated activity data stored in the `ReportedMetricValue` model.

The framework relies on a separation of concerns:
1.  **Activity Data:** Aggregated input data (e.g., total annual litres of diesel consumed) stored in `ReportedMetricValue`.
2.  **Factor Data:** Reference data (emission factors, pollutant factors, energy conversion factors) stored in dedicated models.
3.  **Metric Linking:** Configuration on the `BaseESGMetric` definition to link specific activity metrics to the relevant factors.
4.  **Calculation Logic:** Service functions implementing lookups and calculations for emissions (implemented) and other metrics (to be implemented).
5.  **Calculated Results:** Stores the output of calculations in dedicated models for traceability and reporting.

## Core Components

### 1. Factor Models (`data_management/models/factors.py`)

These models store the reference data used for calculations. They are designed to be updated independently (e.g., annually when new government factors are released).

*   **`GHGEmissionFactor`**:
    *   Stores factors to calculate GHG emissions (typically CO2e) from activity data.
    *   Key lookup fields: `year`, `category`, `sub_category`, `activity_unit`, `region`, `scope`.
    *   Stores the `value` (e.g., kgCO2e per activity unit) and the `factor_unit`.

*   **`PollutantFactor`**:
    *   Stores factors to calculate specific air pollutants (NOx, SOx, Particulate Matter) from activity data.
    *   Key lookup fields: `year`, `category`, `sub_category`, `activity_unit`, `region`.
    *   Stores individual factors: `nox_factor`, `sox_factor`, `pm_factor` (e.g., grams per activity unit).

*   **`EnergyConversionFactor`**:
    *   Stores factors to convert activity data from its original unit to a standard energy unit (e.g., kWh).
    *   Key lookup fields: `year`, `category`, `sub_category`, `activity_unit`, `region`.
    *   Stores the `conversion_factor` (e.g., kWh per activity unit) and the `target_unit`.

### 2. Linking Fields on `BaseESGMetric` (`data_management/models/polymorphic_metrics.py`)

To connect activity data to the correct factors, specific fields have been added to the `BaseESGMetric` model. These fields **must be configured** when defining each metric that requires calculation.

*   `emission_category`, `emission_sub_category`: Link to `GHGEmissionFactor`.
*   `pollutant_category`, `pollutant_sub_category`: Link to `PollutantFactor`.
*   `energy_category`, `energy_sub_category`: Link to `EnergyConversionFactor`.

The `activity_unit` for lookup is derived from the metric's `unit_type` or `custom_unit` field.

### 3. Calculated Result Models (`data_management/models/results.py`)

These models store the output of the calculations, providing traceability back to the source data and the factor used.

*   **`CalculatedEmissionValue`**:
    *   Stores the calculated GHG emission value (e.g., kgCO2e).
    *   Links to the source `ReportedMetricValue` (`source_activity_value`).
    *   Links to the `GHGEmissionFactor` used (`emission_factor`).
    *   Includes copied context (assignment, layer, period, level, scope).

*   **`CalculatedPollutantValue`**:
    *   Stores calculated NOx, SOx, and PM values (typically in grams).
    *   Links to the source `ReportedMetricValue`.
    *   Links to the `PollutantFactor` used.
    *   Includes copied context.

*   **`CalculatedEnergyValue`**:
    *   Stores the calculated energy value in the target unit (e.g., kWh).
    *   Links to the source `ReportedMetricValue`.
    *   Links to the `EnergyConversionFactor` used.
    *   Includes copied context.

## Calculation Flow (Implemented for Emissions)

1.  **Trigger:** A calculation process is initiated (available via the functions `calculate_emissions_for_activity_value`, `calculate_emissions_for_assignment`, or `recalculate_all_emissions`).
2.  **Select Activity Data:** The process identifies `ReportedMetricValue` records that require calculation (filtering on `metric__emission_category` and `metric__emission_sub_category`).
3.  **Lookup Factor:** For a given `ReportedMetricValue`:
    *   The linked `BaseESGMetric` instance is retrieved.
    *   Relevant linking keys (`emission_category`, `emission_sub_category`) are extracted from the metric definition.
    *   Context is extracted:
        *   `year` from the `ReportedMetricValue.reporting_period`
        *   `region` from the `BaseESGMetric.location` field (NOT from the layer)
    *   Factors are queried with robust fallback logic (exact match → combined regions → universal regions → earlier years).
4.  **Perform Calculation:** When a matching factor is found:
    *   The activity amount is retrieved from `ReportedMetricValue.aggregated_numeric_value`.
    *   Unit conversion is performed if needed, with common conversions handled automatically.
    *   The (potentially converted) activity amount is multiplied by the factor value.
5.  **Store Result:** The calculated value is saved into the `CalculatedEmissionValue` model, linking back to the source `ReportedMetricValue` and the factor used.
6.  **Cleanup:** Orphaned calculations (those with no valid source RPVs) are automatically removed during recalculation.

## Implementation Status

*   **Emissions Calculation:** Fully implemented in `data_management/services/emissions.py`.
*   **Pollutant Calculation:** To be implemented in `data_management/services/pollutants.py`.
*   **Energy Conversion Calculation:** To be implemented in `data_management/services/energy.py`.

## Future Work

*   **Triggering Mechanism:** Implement a reliable method for initiating calculations automatically (scheduled tasks recommended for decoupling and performance).
*   **Factor Management:** Create tools or scripts to populate and maintain the data in the factor tables.
*   **Unit Conversion Expansion:** Enhance the current unit conversion system to handle a wider range of units and conversions.
*   **Testing:** Implement thorough testing for factor lookups, unit conversions, and calculation logic.
*   **Admin Interface:** Develop admin interfaces for monitoring and triggering emissions calculations. 