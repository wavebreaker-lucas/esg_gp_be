# Emission Factors Documentation

This document provides information about the emission factors used in the ESG Platform. All emission factors have been standardized to use the year 2025 and region "ALL" for consistent application.

## Overview

The emission factors are stored in the `GHGEmissionFactor` model and are populated using the Django management command `populate_emission_factors.py`. These factors are used to calculate greenhouse gas emissions from various activities.

## Emission Factor Structure

Each emission factor has the following attributes:

- **name**: Descriptive name of the emission factor
- **category**: Main category (electricity, transport, stationary_combustion, towngas)
- **sub_category**: Specific subcategory (e.g., hk_clp, transport_cars_diesel)
- **activity_unit**: Unit of activity measurement (kWh, liters, kg, etc.)
- **value**: Numeric value of the emission factor
- **factor_unit**: Unit of the emission factor (kgCO2e/kWh, kgCO2e/liter, etc.)
- **year**: Year of applicability (standardized to 2025)
- **region**: Geographic region (standardized to "ALL")
- **scope**: Emission scope (1 or 2)
- **source**: Source of the emission factor data
- **source_url**: URL to the source document

## Emission Factor Matching

When calculating emissions, it's critical to use the correct category and subcategory to match with the appropriate emission factor. The following sections provide detailed information for each emission factor, including the exact category and subcategory values used in the code.

## Categories of Emission Factors

### Electricity (`category="electricity"`)

| Name | Subcategory | Value (kgCO2e/kWh) | Activity Unit | Region | Scope |
|------|-------------|-------------------:|---------------|--------|-------|
| Electricity - HK Electric - 2025 | `hk_hke` | 0.7100 | kWh | ALL | 2 |
| Electricity - CLP Power - 2025 | `hk_clp` | 0.3900 | kWh | ALL | 2 |
| Electricity - Eastern China - 2025 | `prc_eastern` | 0.5703 | kWh | ALL | 2 |

### Towngas (`category="towngas"`)

| Name | Subcategory | Value (kgCO2e/Unit) | Activity Unit | Region | Scope |
|------|-------------|--------------------:|---------------|--------|-------|
| Towngas - Hong Kong - 2025 | `hk_indirect` | 0.5880 | Unit | ALL | 2 |

### Transport (`category="transport"`)

#### Diesel Vehicles

| Name | Subcategory | Value (kgCO2e/liter) | Activity Unit | Region | Scope |
|------|-------------|---------------------:|---------------|--------|-------|
| Diesel - Passenger Car | `transport_cars_diesel` | 2.6460 | liters | ALL | 1 |
| Diesel - Private Van | `transport_vans_diesel` | 2.7541 | liters | ALL | 1 |
| Diesel - Public Light Bus | `transport_bus_diesel` | 2.7722 | liters | ALL | 1 |
| Diesel - Light Goods Vehicle | `transport_light_goods_diesel` | 2.7541 | liters | ALL | 1 |
| Diesel - Light Commercial Vehicle | `transport_light_commercial_diesel` | 2.7541 | liters | ALL | 1 |
| Diesel - Medium Goods Vehicle | `transport_medium_goods_diesel` | 2.6377 | liters | ALL | 1 |
| Diesel - Heavy Goods Vehicle | `transport_heavy_goods_diesel` | 2.6377 | liters | ALL | 1 |
| Diesel - Other Mobile Machinery | `transport_mobile_machinery_diesel` | 2.6166 | liters | ALL | 1 |
| Diesel - General Mobile | `transport_general_diesel` | 2.6166 | liters | ALL | 1 |

#### Petrol/Unleaded Vehicles

| Name | Subcategory | Value (kgCO2e/liter) | Activity Unit | Region | Scope |
|------|-------------|---------------------:|---------------|--------|-------|
| Petrol - Motorcycle | `transport_motorcycle_petrol` | 2.4122 | liters | ALL | 1 |
| Petrol/Unleaded - Passenger Car | `transport_cars_petrol` | 2.6687 | liters | ALL | 1 |
| Petrol/Unleaded - Private Van | `transport_vans_petrol` | 2.6769 | liters | ALL | 1 |
| Petrol/Unleaded - Light Goods Vehicle | `transport_light_goods_petrol` | 2.6673 | liters | ALL | 1 |
| Petrol - General Mobile | `transport_general_petrol` | 2.6687 | liters | ALL | 1 |

#### LPG Vehicles

| Name | Subcategory | Value (kgCO2e/liter) | Activity Unit | Region | Scope |
|------|-------------|---------------------:|---------------|--------|-------|
| LPG - Private Van | `transport_vans_lpg` | 1.6859 | liters | ALL | 1 |
| LPG - Public Light Bus | `transport_bus_lpg` | 1.6859 | liters | ALL | 1 |
| LPG - Other Mobile Machinery | `transport_mobile_machinery_lpg` | 1.6791 | liters | ALL | 1 |
| LPG - Passenger Car | `transport_cars_lpg` | 1.6859 | liters | ALL | 1 |
| LPG - General Mobile | `transport_lpg` | 1.6859 | liters | ALL | 1 |

#### Detailed Vehicle Classifications

##### Light Goods Vehicles (≤2.5 tonnes)

| Name | Subcategory | Value (kgCO2e/liter) | Activity Unit | Region | Scope |
|------|-------------|---------------------:|---------------|--------|-------|
| Petrol - Light Goods Vehicle (≤2.5tonnes) | `transport_light_goods_lte_2_5_petrol` | 2.6673 | liters | ALL | 1 |
| Unleaded Petrol - Light Goods Vehicle (≤2.5tonnes) | `transport_light_goods_lte_2_5_unleaded_petrol` | 2.6673 | liters | ALL | 1 |
| LPG - Light Goods Vehicle (≤2.5tonnes) | `transport_light_goods_lte_2_5_lpg` | 1.6859 | liters | ALL | 1 |

##### Light Goods Vehicles (2.5-3.5 tonnes)

| Name | Subcategory | Value (kgCO2e/liter) | Activity Unit | Region | Scope |
|------|-------------|---------------------:|---------------|--------|-------|
| Petrol - Light Goods Vehicle (2.5-3.5tonnes) | `transport_light_goods_2_5_3_5_petrol` | 2.6673 | liters | ALL | 1 |
| Unleaded Petrol - Light Goods Vehicle (2.5-3.5tonnes) | `transport_light_goods_2_5_3_5_unleaded_petrol` | 2.6673 | liters | ALL | 1 |
| LPG - Light Goods Vehicle (2.5-3.5tonnes) | `transport_light_goods_2_5_3_5_lpg` | 1.6859 | liters | ALL | 1 |

##### Light Goods Vehicles (3.5-5.5 tonnes)

| Name | Subcategory | Value (kgCO2e/liter) | Activity Unit | Region | Scope |
|------|-------------|---------------------:|---------------|--------|-------|
| Petrol - Light Goods Vehicle (3.5-5.5tonnes) | `transport_light_goods_3_5_5_5_petrol` | 2.6673 | liters | ALL | 1 |
| Unleaded Petrol - Light Goods Vehicle (3.5-5.5tonnes) | `transport_light_goods_3_5_5_5_unleaded_petrol` | 2.6673 | liters | ALL | 1 |
| LPG - Light Goods Vehicle (3.5-5.5tonnes) | `transport_light_goods_3_5_5_5_lpg` | 1.6859 | liters | ALL | 1 |

##### Medium/Heavy Goods Vehicles (5.5-15 tonnes)

| Name | Subcategory | Value (kgCO2e/liter) | Activity Unit | Region | Scope |
|------|-------------|---------------------:|---------------|--------|-------|
| Petrol - Medium/Heavy Goods Vehicle (5.5-15tonnes) | `transport_medium_heavy_goods_5_5_15_petrol` | 2.6673 | liters | ALL | 1 |
| Unleaded Petrol - Medium/Heavy Goods Vehicle (5.5-15tonnes) | `transport_medium_heavy_goods_5_5_15_unleaded_petrol` | 2.6673 | liters | ALL | 1 |
| LPG - Medium/Heavy Goods Vehicle (5.5-15tonnes) | `transport_medium_heavy_goods_5_5_15_lpg` | 1.6859 | liters | ALL | 1 |

##### Medium/Heavy Goods Vehicles (≥15 tonnes)

| Name | Subcategory | Value (kgCO2e/liter) | Activity Unit | Region | Scope |
|------|-------------|---------------------:|---------------|--------|-------|
| Petrol - Medium/Heavy Goods Vehicle (≥15tonnes) | `transport_medium_heavy_goods_gte_15_petrol` | 2.6673 | liters | ALL | 1 |
| Unleaded Petrol - Medium/Heavy Goods Vehicle (≥15tonnes) | `transport_medium_heavy_goods_gte_15_unleaded_petrol` | 2.6673 | liters | ALL | 1 |
| LPG - Medium/Heavy Goods Vehicle (≥15tonnes) | `transport_medium_heavy_goods_gte_15_lpg` | 1.6859 | liters | ALL | 1 |

#### Other Transport 

| Name | Subcategory | Value (kgCO2e/liter) | Activity Unit | Region | Scope |
|------|-------------|---------------------:|---------------|--------|-------|
| Gas Oil - Ship | `transport_ship_gas_oil` | 2.9480 | liters | ALL | 1 |
| Jet Kerosene - Aviation | `transport_aviation_kerosene` | 2.4309 | liters | ALL | 1 |

### Stationary Combustion (`category="stationary_combustion"`)

| Name | Subcategory | Value | Activity Unit | Factor Unit | Region | Scope |
|------|-------------|------:|---------------|-------------|--------|-------|
| Diesel - Stationary Combustion (Generators) | `stationary_diesel` | 2.6167 | liters | kgCO2e/liter | ALL | 1 |
| LPG - Stationary Source | `stationary_lpg` | 3.0171 | kg | kgCO2e/kg | ALL | 1 |
| Kerosene - Stationary Source | `stationary_kerosene` | 2.4317 | liters | kgCO2e/liter | ALL | 1 |
| Charcoal - Stationary Source | `stationary_charcoal` | 3.1318 | kg | kgCO2e/kg | ALL | 1 |
| Towngas - Direct Consumption | `stationary_town_gas` | 2.5529 | Unit | kgCO2e/Unit | ALL | 1 |
| Petrol - Stationary Equipment | `stationary_petrol` | 2.6687 | liters | kgCO2e/liter | ALL | 1 |
| Natural Gas - Stationary Combustion | `stationary_natural_gas` | 2.1622 | cubic meter | kgCO2e/m³ | ALL | 1 |

## Vehicle Type and Fuel Type Mapping

When users select specific vehicle types and fuel types in the system, the following mapping is used to determine which emission factor will be applied:

### Vehicle Tracking Metric Mapping

| Vehicle Type | Fuel Type | Used Emission Factor Subcategory |
|--------------|-----------|----------------------------------|
| Private cars | Diesel oil | `transport_cars_diesel` |
| Private cars | Petrol | `transport_cars_petrol` |
| Private cars | Unleaded petrol | `transport_cars_petrol` |
| Private cars | LPG | `transport_cars_lpg` |
| Light goods vehicles (≤2.5tonnes) | Diesel oil | `transport_light_commercial_diesel` |
| Light goods vehicles (2.5-3.5tonnes) | Diesel oil | `transport_light_commercial_diesel` |
| Light goods vehicles (3.5-5.5tonnes) | Diesel oil | `transport_light_commercial_diesel` |
| Medium & Heavy goods vehicles (5.5-15tonnes) | Diesel oil | `transport_heavy_goods_diesel` |
| Medium & Heavy goods vehicles (≥15tonnes) | Diesel oil | `transport_heavy_goods_diesel` |

### Fallback Mappings

If a specific vehicle type + fuel type combination is not in the mapping above, the system falls back to using a general emission factor based on fuel type only:

| Fuel Type | Fallback Emission Factor Subcategory |
|-----------|--------------------------------------|
| Diesel oil | `transport_general_diesel` |
| Petrol | `transport_general_petrol` |
| Unleaded petrol | `transport_general_petrol` |
| LPG | `transport_lpg` |

## Stationary Fuel Consumption Mapping

For stationary sources of emissions (as opposed to mobile/transport sources), the following mapping is used to determine which emission factor will be applied:

### Fuel Consumption Metric Mapping

| Fuel Type | Used Emission Factor Subcategory |
|-----------|----------------------------------|
| Diesel oil | `stationary_diesel` |
| LPG | `stationary_lpg` |
| Kerosene | `stationary_kerosene` |
| Natural gas | `stationary_natural_gas` |
| Charcoal | `stationary_charcoal` |
| Town gas | `stationary_town_gas` |
| Petrol | `stationary_petrol` |
| Unleaded petrol | `stationary_petrol` |

The FuelConsumptionMetric only looks at stationary fuel consumption, regardless of the source type (generators, boilers, cooking stoves, etc.). The emission factor is determined solely by the fuel type, as these factors are specific to stationary combustion rather than mobile sources.

### Scope 3 Emission Factors (`category="materials"`, `category="waste"`, `category="water"`)

These emission factors cover indirect emissions from activities across the value chain.

| Name | Category | Subcategory | Value | Activity Unit | Factor Unit | Region | Scope |
|------|----------|-------------|------:|---------------|-------------|--------|-------|
| Paper Consumption - Hong Kong | `materials` | `paper` | 4.8000 | kg | kgCO2e/kg | ALL | 3 |
| General Waste - Hong Kong | `waste` | `general_waste` | 1.5000 | kg | kgCO2e/kg | ALL | 3 |
| Fresh Water Consumption - Hong Kong | `water` | `fresh_water` | 0.4280 | cubic meter | kgCO2e/m3 | ALL | 3 |

## Usage

### Matching by Category and Subcategory

When calculating emissions, use the category and subcategory to fetch the appropriate emission factor:

```python
# Example code for matching emission factors
emission_factor = GHGEmissionFactor.objects.get(
    category="transport",
    sub_category="transport_cars_diesel",
    year=2025,
    region="ALL"
)

# Calculate emissions
activity_amount = 100  # liters of diesel
emissions = activity_amount * emission_factor.value  # Result in kgCO2e
```

### Calculation Examples

The emission factors are used to calculate GHG emissions by multiplying the factor value by the activity amount:

```
GHG Emissions = Activity Amount × Emission Factor
```

Examples:
- 100 kWh of electricity from CLP Power: 100 × 0.3900 = 39.00 kgCO2e
- 50 liters of diesel for a passenger car: 50 × 2.6460 = 132.30 kgCO2e

## Sources

Emission factors are derived from reputable sources including:
- HKEX Reporting Guidance
- HK Electric Investments Sustainability Report
- CLP Holdings Sustainability Report
- China Ministry of Environment Greenhouse Gas Emission Report
- TNB Sustainability Report
- Singapore Energy Statistics

## Adding New Emission Factors

To add new emission factors, modify the `populate_emission_factors.py` file with additional `create_factor()` calls following the existing pattern and run the management command:

```bash
python manage.py populate_emission_factors
``` 