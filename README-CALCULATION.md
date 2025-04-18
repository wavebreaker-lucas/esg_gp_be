# ESG Calculation Framework

## Overview

This document outlines the backend framework designed to calculate derived environmental metrics, such as Greenhouse Gas (GHG) emissions (CO2e), specific pollutants (NOx, SOx, PM), and standardized energy values (kWh), based on the aggregated activity data stored in the `ReportedMetricValue` model.

The framework relies on a separation of concerns:
1.  **Activity Data:** Aggregated input data (e.g., total annual litres of diesel consumed) stored in `ReportedMetricValue`.
2.  **Factor Data:** Reference data (emission factors, pollutant factors, energy conversion factors) stored in dedicated models.
3.  **Metric Linking:** Configuration on the `BaseESGMetric` definition to link specific activity metrics to the relevant factors.
4.  **Calculation Logic:** Service functions implementing lookups and calculations for emissions (implemented) and other metrics (to be implemented).
5.  **Calculated Results:** Stores the output of calculations in dedicated models for traceability and reporting.
6.  **Automatic Triggers:** Signal handlers that automatically initiate calculations when relevant data changes.

## Core Components

### 1. Factor Models (`data_management/models/factors.py`)

These models store the reference data used for calculations. They are designed to be updated independently (e.g., annually when new government factors are released).

*   **`GHGEmissionFactor`**:
    *   Stores factors to calculate GHG emissions (typically CO2e) from activity data.
    *   Key lookup fields: `year`, `category`, `sub_category`, `activity_unit`, `region`, `scope`.
    *   Stores the `value` (e.g., kgCO2e per activity unit) and the `factor_unit`.
    *   Includes factors for different years (2023, 2025) to support calculations across reporting periods.
    *   Populated via management command: `python manage.py populate_emission_factors`.

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

#### 2.1 Dynamic Factor Mapping for Vehicle Tracking

For the `VehicleTrackingMetric`, a more dynamic approach is implemented due to the variable nature of vehicle fleets:

* The **base emission category** is set to "transport"
* A configurable **`emission_factor_mapping`** field (JSONField) maps vehicle type + fuel type combinations to emission subcategories:
  ```json
  {
    "private_cars_diesel_oil": "transport_cars_diesel",
    "private_cars_petrol": "transport_cars_petrol",
    "light_goods_lte_2_5_diesel_oil": "transport_light_commercial_diesel",
    "diesel_oil": "transport_general_diesel"
  }
  ```
* The `get_emission_subcategory(vehicle_type, fuel_type)` method dynamically selects the appropriate emission subcategory based on the vehicle's characteristics
* The lookup follows a fallback pattern:
  1. Try the specific vehicle_type + fuel_type combination
  2. Try just the fuel_type
  3. Fall back to a constructed key

This approach allows:
* A single metric definition to handle different emission factors for different vehicles
* Updates to emission factor mappings without code changes
* Flexible configuration to match available emission factors in the database

#### 2.2 Dynamic Factor Mapping for Fuel Consumption

For the `FuelConsumptionMetric`, a similar dynamic approach is used:

* The **base emission category** is set to "stationary_combustion".
* The `get_emission_subcategory(fuel_type)` method dynamically selects the appropriate emission subcategory based on the source's fuel type (e.g., "diesel_oil" → "stationary_diesel").
* The `emission_factor_mapping` field on the metric allows overrides.

This allows:
* A single metric definition to handle different emission factors for different fuel types.
* Updates to emission factor mappings without code changes.

### 3. Calculated Result Models (`data_management/models/results.py`)

These models store the output of the calculations, providing traceability back to the source data and the factor used.

*   **`CalculatedEmissionValue`**:
    *   Stores the calculated GHG emission value (e.g., kgCO2e).
    *   Links to the source `ReportedMetricValue` (`source_activity_value`).
    *   Links to the `GHGEmissionFactor` used (`emission_factor`).
    *   Links to specific `VehicleRecord` or `FuelRecord` for corresponding calculations.
    *   Includes copied context (assignment, layer, period, level, scope).
    *   Uses a `unique_together` constraint on [`source_activity_value`, `emission_factor`, `related_group_id`, `is_primary_record`, `vehicle_record`, `fuel_record`] to ensure data integrity.

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

### 4. Vehicle Emissions Calculation (`data_management/services/vehicle_emissions.py`)

The vehicle emissions calculation extends the standard emissions calculation with specialized handling for vehicle data:

*   **Vehicle-Specific Logic:** 
    *   Processes individual vehicle records and their monthly data entries
    *   Dynamically selects emission factors based on vehicle type and fuel type
    *   Handles multiple vehicles with different characteristics within a single metric
    *   Maintains data integrity by creating separate calculation records per vehicle

*   **Data Flow:**
    1. When vehicle data is aggregated in `ReportedMetricValue`, it contains JSON data with vehicle records
    2. The calculation service parses this structure to extract:
       - Distance traveled per vehicle/month
       - Fuel consumed per vehicle/month
       - Vehicle metadata (type, fuel type, etc.)
    3. For each vehicle record, the appropriate emission factor is selected using the dynamic mapping
    4. Emissions are calculated per vehicle and then summed for the total
    5. Each vehicle gets its own CalculatedEmissionValue record

*   **Special Cases:**
    *   **Fuel-based calculation:** When fuel consumption data is available, emissions are calculated based on fuel volume × emission factor
    *   **Distance-based calculation:** When only distance data is available, emissions are calculated based on distance × emission factor
    *   **Preference order:** Fuel-based calculation is prioritized over distance-based when both data types are present

### 5. Emission Factor Population

Emission factors are populated and maintained through management commands:

*   **`populate_emission_factors` command:**
    * Creates/updates emission factors for electricity, towngas, transport, and **stationary combustion**.
    * Includes factors for different years (2023, 2025) to support multi-year reporting
    * Handles various regions (HK, PRC, ALL) and vehicle/fuel combinations
    * Ensures correct factors exist for all supported vehicle types and fuel types
    * Run this command to ensure all necessary emission factors are available:
      ```
      python manage.py populate_emission_factors
      ```

## Calculation Flow (Implemented for Emissions)

1.  **Trigger:** A calculation process is initiated in one of the following ways:
    - **Automatically via signals:** When a `ReportedMetricValue` is created or updated, a signal handler triggers calculation (if the metric has emission categories configured)
    - **Manually via functions:** Using `calculate_emissions_for_activity_value`, `calculate_emissions_for_assignment`, or `recalculate_all_emissions`.
2.  **Select Activity Data:** The process identifies `ReportedMetricValue` records that require calculation (filtering on `metric__emission_category` and `metric__emission_sub_category`).
3.  **Lookup Factor:** For a given `ReportedMetricValue`:
    *   The linked `BaseESGMetric` instance (and its specific type) is retrieved.
    *   Relevant linking keys (`emission_category`, `emission_sub_category`) are extracted from the metric definition.
    *   **For VehicleTrackingMetric/FuelConsumptionMetric**: The emission_subcategory is dynamically determined using the `get_emission_subcategory` method.
    *   Context is extracted:
        *   `year` from the `ReportedMetricValue.reporting_period`
        *   `region` from the `BaseESGMetric.location` field (NOT from the layer)
    *   Factors are queried with robust fallback logic (exact match → combined regions → universal regions → earlier years).
    *   Emission scope is determined by the matched factor in the database, not inferred from categories.
4.  **Perform Calculation:** When a matching factor is found:
    *   The activity amount is retrieved from `ReportedMetricValue.aggregated_numeric_value` or `ReportedMetricValue.aggregated_text_value` (if structured data like vehicles/fuel sources).
    *   The appropriate calculation strategy is selected based on the metric type (`get_strategy_for_metric`).
    *   The strategy processes the activity data (e.g., looping through vehicles or fuel sources in `aggregated_text_value`).
    *   Unit conversion is performed if needed, with common conversions handled automatically.
    *   The (potentially converted) activity amount for each component (vehicle/source) is multiplied by the factor value.
5.  **Store Result:** The calculated value is saved into the `CalculatedEmissionValue` model, linking back to the source `ReportedMetricValue` and the factor used. For metrics with multiple components (vehicles/fuel sources), each component gets its own record linked to the appropriate `VehicleRecord` or `FuelRecord`, and a primary summary record is created.
6.  **Cleanup:** Orphaned calculations (those with no valid source RPVs) are automatically removed during recalculation.

## Implementation Status

*   **Emissions Calculation:** Fully implemented in `data_management/services/emissions.py`.
    *   Relies on metric configuration (`emission_category`, `emission_sub_category`, `location`) and factor database.
    *   Scope is determined by the factor database, not inferred by the system.
    *   **Automatic triggering** implemented via Django signals in `data_management/signals.py`.
    *   **Special handling for VehicleTrackingMetric and FuelConsumptionMetric** with dynamic emission subcategory mapping and calculation strategies.
    *   **Component-specific calculation logic** implemented with proper per-vehicle/per-fuel-source record uniqueness constraints.
*   **Pollutant Calculation:** To be implemented in `data_management/services/pollutants.py`.
*   **Energy Conversion Calculation:** To be implemented in `data_management/services/energy.py`.

## Future Work

*   ~~**Triggering Mechanism:** Implement a reliable method for initiating calculations automatically (scheduled tasks recommended for decoupling and performance).~~ ✅ Implemented using Django signals for ReportedMetricValue changes.
*   **Factor Management:** Create tools or scripts to populate and maintain the data in the factor tables.
*   **Unit Conversion Expansion:** Enhance the current unit conversion system to handle a wider range of units and conversions.
*   **Testing:** Implement thorough testing for factor lookups, unit conversions, and calculation logic.
*   **Admin Interface:** Develop admin interfaces for monitoring and triggering emissions calculations.
*   **Additional Signals:** Implement similar signal triggers for pollutant and energy calculations once those services are implemented. 