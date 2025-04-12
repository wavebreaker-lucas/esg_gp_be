# Emissions Calculation Setup Guide

This guide explains how to set up metrics and emission factors for accurate GHG calculations.

## Overview

The system calculates greenhouse gas emissions using:
1. **Activity data** from ReportedMetricValue records
2. **Emission factors** from the GHGEmissionFactor database
3. **Matching logic** that links the two based on category/sub-category and context

## Configuring Metrics

To enable emissions calculation for a metric:

1. Set these fields on the BaseESGMetric:
   ```python
   metric.emission_category = "electricity"  # Required
   metric.emission_sub_category = "hk_clp"   # Required
   metric.location = "HK"                    # Required for regional factors
   ```

2. Ensure the unit_type is correctly set (on BasicMetric, TimeSeriesMetric, etc.)
   ```python
   # For BasicMetric or TimeSeriesMetric:
   metric.unit_type = "kWh"  # or use custom_unit field
   ```

## Category and Sub-Category Naming Convention

For best results, use these conventions:

### Electricity:
- **Category**: `electricity`
- **Sub-category**: Region/provider specific
  - `hk_hke` - Hong Kong Electric
  - `hk_clp` - CLP Power
  - `prc_northern` - Northern China grid
  - etc.

### Towngas:
- **Category**: `towngas`
- **Sub-category**: Region/usage specific
  - `hk_indirect` - Hong Kong indirect consumption

### Transport:
- **Category**: `transport`
- **Sub-category**: Vehicle/fuel/context specific
  - `company_gasoline` - Company vehicles (Scope 1)
  - `employee_commuting_gasoline` - Employee commuting (Scope 3)

### Other examples:
- **Category**: `waste`
  - Sub-categories: `landfill`, `recycling`, `incineration`
- **Category**: `refrigerants`
  - Sub-categories: `r410a`, `r22`, `r134a`

## Matching Process

The system matches activity data to factors using these steps:

1. Looks for factors matching:
   - Year (from reporting_period) 
   - Category (from metric.emission_category)
   - Sub-category (from metric.emission_sub_category)
   - Activity unit (from metric.unit_type or custom_unit)
   - Region (from metric.location)

2. If no exact match is found, fallbacks in this order:
   - Combined regions (e.g., "HK / PRC")
   - Universal regions ("ALL")
   - Earlier years (most recent first)

3. Once a factor is found, it applies any needed unit conversions

4. Scope is determined by the matched factor, not inferred by the system

## Example Configuration

```python
# Example 1: Hong Kong Electric electricity consumption
metric = BaseESGMetric.objects.create(
    name="Electricity Consumption (HKE)",
    emission_category="electricity",
    emission_sub_category="hk_hke",
    location="HK"
)

# Example 2: Company vehicle gasoline consumption
metric = BasicMetric.objects.create(
    name="Gasoline Consumption - Company Vehicles",
    unit_type="liters",
    emission_category="transport",
    emission_sub_category="company_gasoline",
    location="HK"
)
```

## Populating the Emission Factor Database

Run the provided script to populate sample emission factors:

```bash
python manage.py shell < data_management/scripts/populate_emission_factors.py
```

You can also add factors manually through the Django admin interface or by scripts using the GHGEmissionFactor model.

## Viewing Calculated Results

After running calculations, view results in:
1. Django Admin interface under CalculatedEmissionValue
2. Through the REST API (if configured)
3. In dashboard reports showing emissions by scope

## Troubleshooting

If calculations aren't appearing:
1. Check metric configuration (category/sub-category must be set)
2. Verify factors exist in the database for the right year/region
3. Check activity data is present in ReportedMetricValue
4. Examine logs for matching errors 