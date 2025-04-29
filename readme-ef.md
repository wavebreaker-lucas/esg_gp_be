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

## Categories of Emission Factors

### Electricity

Emission factors for electricity consumption from different providers:

- HK Electric (0.7100 kgCO2e/kWh)
- CLP Power (0.3900 kgCO2e/kWh)
- Northern China (0.5703 kgCO2e/kWh)
- Northeast China (0.5703 kgCO2e/kWh)
- Eastern China (0.5703 kgCO2e/kWh)
- Malaysia (0.5600 kgCO2e/kWh)
- Singapore (0.4085 kgCO2e/kWh)

### Towngas

Emission factor for towngas consumption:

- Hong Kong Towngas (0.5880 kgCO2e/Unit)

### Transport

Emission factors for different vehicle types and fuels:

#### Diesel Vehicles
- Passenger Car (2.6460 kgCO2e/liter)
- Private Van (2.7541 kgCO2e/liter)
- Public Light Bus (2.7722 kgCO2e/liter)
- Light Goods Vehicle (2.7541 kgCO2e/liter)
- Light Commercial Vehicle (2.7541 kgCO2e/liter)
- Medium Goods Vehicle (2.6377 kgCO2e/liter)
- Heavy Goods Vehicle (2.6377 kgCO2e/liter)
- Other Mobile Machinery (2.6166 kgCO2e/liter)

#### Petrol/Unleaded Vehicles
- Motorcycle (2.4122 kgCO2e/liter)
- Passenger Car (2.6687 kgCO2e/liter)
- Private Van (2.6769 kgCO2e/liter)
- Light Goods Vehicle (2.6673 kgCO2e/liter)

#### LPG Vehicles
- Private Van (1.6859 kgCO2e/liter)
- Public Light Bus (1.6859 kgCO2e/liter)
- Other Mobile Machinery (1.6791 kgCO2e/liter)
- Passenger Car (1.6859 kgCO2e/liter)

#### Other Transport Factors
- Gas Oil - Ship (2.9480 kgCO2e/liter)
- Jet Kerosene - Aviation (2.4309 kgCO2e/liter)

### Stationary Combustion

Emission factors for stationary fuel combustion:

- Diesel - Generators (2.6167 kgCO2e/liter)
- LPG - Stationary Source (3.0171 kgCO2e/kg)
- Kerosene - Stationary Source (2.4317 kgCO2e/liter)
- Charcoal - Stationary Source (3.1318 kgCO2e/kg)
- Towngas - Direct Consumption (2.5529 kgCO2e/Unit)
- Petrol - Stationary Equipment (2.6687 kgCO2e/liter)
- Natural Gas - Stationary Combustion (2.1622 kgCO2e/m³)

## Usage

The emission factors are used to calculate GHG emissions by multiplying the factor value by the activity amount:

```
GHG Emissions = Activity Amount × Emission Factor
```

For example:
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