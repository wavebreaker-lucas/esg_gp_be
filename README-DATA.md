# ESG Data Management System

## Overview

The ESG Data Management System is designed to handle ESG (Environmental, Social, and Governance) reporting requirements, with a specific focus on HKEX ESG reporting guidelines. The system uses a hierarchical structure of Categories, Forms, and **polymorphic Metrics** to organize and collect ESG data.

**Key Architectural Changes:**
- **Polymorphic Metrics:** Metrics are now defined using a base model (`BaseESGMetric`) and specific subclasses (`BasicMetric`, `TabularMetric`, `TimeSeriesMetric`, etc.) to represent different data structures and input types.
- **Separated Submission Data:** Raw data inputs are handled via a header record (`ESGMetricSubmission`) containing common metadata, linked to specific data storage models (`BasicMetricData`, `TabularMetricRow`, `TimeSeriesDataPoint`, etc.) that hold the actual values corresponding to the polymorphic metric type.
- **Aggregation & Reported Values:** An aggregation service (`aggregation.py`) orchestrates the calculation of final values, but the core calculation logic now resides within a `calculate_aggregate` method on each specific polymorphic metric model. These calculated results are stored in the `ReportedMetricValue` model, which includes an aggregation `level` (e.g., Monthly, Annual).
- **Completion Logic:** Form and template completion status is determined by checking for the existence of the final, annual (`level='A'`) `ReportedMetricValue` records for all required metrics.

## Layer Support

(This section remains largely the same, as layer support applies to both inputs and reported values)

The system now includes comprehensive layer-based data segregation, allowing ESG data to be associated with specific organizational layers:

### Layer Integration for Submissions, Evidence, and Reported Values
- Each ESG metric *input header* (`ESGMetricSubmission`) can be assigned to a specific layer.
- Evidence files (`ESGMetricEvidence`) are associated with input submissions and can also have a layer tag.
- Final `ReportedMetricValue` records are also linked to a specific layer, crucial for aggregation context.
- Default layer settings provide fallback when no layer is specified during input submission.

### Key Layer Features:
- **Layer Association**: `ESGMetricSubmission`, `ESGMetricEvidence`, and `ReportedMetricValue` have a `layer` field referencing a `LayerProfile`.
- **Default Layer**: System uses a configurable default layer (set via `DEFAULT_LAYER_ID` in settings) for inputs.
- **Fallback Mechanism**: When no layer is specified for an input, the system tries:
  1. Layer specified in settings via `DEFAULT_LAYER_ID`
  2. First available group layer
  3. Assignment's layer (for batch submissions)
- **Available Layers API**: Endpoint (`/api/submissions/available-layers/`) to retrieve all layers accessible to the current user.

### Available Layers Endpoint

```
GET /api/submissions/available-layers/
```

**Features:**
- Returns all layers the current user can access based on their role and permissions
- Sorted by layer type (GROUP, SUBSIDIARY, BRANCH) and then by name
- Includes parent layer information for easier navigation
- Optional filtering by assignment context

**Optional Parameters:**
- `assignment_id`: Filter layers to those relevant for a specific assignment

**Example Response:**
```json
[
  {
    "id": 1,
    "name": "Parent Group Inc.",
    "type": "GROUP",
    "location": "HK",
    "parent": null
  },
  {
    "id": 3,
    "name": "Manufacturing Division",
    "type": "SUBSIDIARY",
    "location": "PRC",
    "parent": {
      "id": 1,
      "name": "Parent Group Inc."
    }
  },
  {
    "id": 5,
    "name": "Shanghai Factory",
    "type": "BRANCH",
    "location": "PRC",
    "parent": {
      "id": 3,
      "name": "Manufacturing Division"
    }
  }
]
```

**Use Cases:**
- Displaying layer options in submission forms
- Filtering submissions or evidence by layer
- Building layer selection dropdowns in the UI

### Benefits of Layer-Based Data:
- **Data Segregation**: Clear separation of data between different organizational units
- **Targeted Reporting**: Generate reports specific to subsidiaries or branches
- **Layer-Specific Evidence**: Attach evidence files pertinent to particular organizational units
- **Improved Organization**: Better categorization of submissions and evidence

### Layer-Based Aggregation of Inputs (`sum_by_layer`)

**Note:** This endpoint operates on the raw *input* data headers (`ESGMetricSubmission`) and provides a sum of values from their linked specific data models (e.g., `BasicMetricData`, `TimeSeriesDataPoint`) per layer. It is distinct from the final, potentially calculated values stored in `ReportedMetricValue`.

The system supports aggregating raw metric *inputs* across different layers via the `sum_by_layer` endpoint:

```
GET /api/submissions/sum-by-layer/?assignment_id=1&metric_ids=5,6,7&layer_ids=3,4,5
```

**Parameters:**
- `assignment_id`: Required. The template assignment to aggregate data for.
- `metric_ids`: Required. Comma-separated list of metric IDs to include in the aggregation.
- `layer_ids`: Required. Comma-separated list of layer IDs to include in the aggregation.
- `period`: Optional. If provided, filter submissions to this specific period (YYYY-MM-DD).

**Example Response:**
```json
{
  "assignment_id": "1",
  "period": "2024-06-30",
  "metrics": {
    "5": {
      "id": 5,
      "name": "Electricity Consumption",
      "unit_type": "kWh",
      "custom_unit": null,
      "requires_time_reporting": true,
      "form_code": "HKEX-A2"
    },
    "6": {
      "id": 6,
      "name": "Water Consumption",
      "unit_type": "m3",
      "custom_unit": null,
      "requires_time_reporting": true,
      "form_code": "HKEX-A2"
    }
  },
  "layers": {
    "3": {
      "id": 3,
      "name": "Manufacturing Division",
      "type": "SUBSIDIARY",
      "location": "PRC"
    },
    "4": {
      "id": 4,
      "name": "Hong Kong Office",
      "type": "SUBSIDIARY",
      "location": "HK"
    }
  },
  "aggregation": [
    {
      "metric_id": 5,
      "values_by_layer": {
        "3": {
          "value": 12500.0,
          "submission_id": 101
        },
        "4": {
          "value": 3200.0,
          "submission_id": 102
        }
      }
    },
    {
      "metric_id": 6,
      "values_by_layer": {
        "3": {
          "value": 1850.0,
          "submission_id": 103
        },
        "4": {
          "value": 450.0,
          "submission_id": 104
        }
      }
    }
  ]
}
```

**Key Aggregation Features:**
- For time-based metrics without a specific period, the endpoint sums all values across reporting periods
- For non-time-based metrics, the endpoint returns the single submission value
- When a specific period is provided, only submissions matching that period are included
- All requested metrics and layers are returned, with null values for missing data
- Includes full metric metadata (name, unit type, form code) for easy display
- Includes layer metadata (name, type, location) for context
- References original submission IDs when available for drill-down capabilities

**Use Cases:**
- Comparing environmental metrics across different subsidiaries
- Creating layer-based dashboards showing consolidated metrics
- Generating consolidated reports across organizational structure
- Analyzing performance of different organizational units

### Submission Input Creation with Layers
When creating submission *input headers*, the layer can be specified explicitly or will default according to the fallback mechanism:
```json
POST /api/metric-submissions/
{
  "assignment_id": 1,
  "metric_id": 5,
  "value": 1234.56,
  "layer_id": 3, // Layer for this specific input
  "reporting_period": "2024-06-30"
}
```

### Batch Submission Input with Layers and Source Identifier
When submitting multiple metric *input headers* at once, a default layer can be specified for all inputs, with individual layer overrides. You can also provide an optional `source_identifier` for each input.
```json
POST /api/metric-submissions/batch_submit/
{
  "assignment_id": 1,
  "default_layer_id": 3, // Default layer for inputs in this batch
  "submissions": [
    {
      "metric_id": 5,
      "value": 1234.56, // Will use default_layer_id 3
      "source_identifier": "Meter A", // Optional source
      "layer_id": 3, // Overrides default_layer_id for this specific input
      "reporting_period": "2024-06-30"
    },
    {
      "metric_id": 6,
      "value": 789.01,
      "layer_id": 4,  // Overrides default_layer_id for this specific input
      "source_identifier": "Meter B",
      "reporting_period": "2024-06-30"
    },
    {
        "metric_id": 7,
        "value": 100,
        "layer_id": 3,
        "reporting_period": "2024-06-30",
        "source_identifier": null
    }
  ]
}
```

## Data Model: Polymorphic Metrics, Submissions, and Reported Values

The system now uses distinct models for metric definitions, raw submission inputs, and final reported values.

- **`BaseESGMetric` (and subclasses like `BasicMetric`, `TabularMetric`, `TimeSeriesMetric`, etc.)**: Defines the *type* of metric, its structure (e.g., columns for tabular, frequency for time series), validation rules, and other metadata. Uses `django-polymorphic`.
- **`ESGMetricSubmission`**: Represents a **header record** for a single raw data input event by a user for a specific metric, assignment, and layer. Contains common metadata like submitter, submission time, verification status (for the input itself), notes, evidence links, and an optional `source_identifier`. It no longer stores the actual `value` or `text_value`.
- **Specific Submission Data Models (`BasicMetricData`, `TabularMetricRow`, `TimeSeriesDataPoint`, etc.)**: These models store the *actual raw data values* submitted. Each is linked back (OneToOne or ForeignKey) to a single `ESGMetricSubmission` header. The type of data model used depends on the type of the linked `BaseESGMetric`.
- **`ReportedMetricValue`**: Represents the final, calculated, or **aggregated result** for a metric within a specific context (assignment, layer, reporting period, and **aggregation level** - e.g., Monthly, Annual). The actual calculation logic is defined in the `calculate_aggregate` method of the corresponding `BaseESGMetric` subclass, orchestrated by the aggregation service (`aggregation.py`). This model stores the final `aggregated_numeric_value` or `aggregated_text_value` and metadata about the aggregation (e.g., number of source inputs contributing, first/last submission time relevant to the inputs used). This is the value intended for final reports and dashboards, and used for completion checks (`level='A'`).

**(Removed Models:** `ESGMetric` (old monolithic), `MetricValueField`, `MetricValue`, `ReportedMetricFieldValue` are obsolete and have been removed).**

This separation allows for:
- Flexible definition of diverse metric types.
- Tracking individual raw data submissions, including their source.
- Implementing complex aggregation logic based on metric type.
- Independent verification of raw inputs.
- Clear distinction between data entry, aggregation processing, and final reporting views.

## Core Components

### 1. ESG Form Categories
Categories represent the main sections of ESG reporting:
- **Environmental** (`code='environmental'`)
- **Social** (`code='social'`)
- **Governance** (`code='governance'`)

Properties:
- `name`: Display name of the category
- `code`: Unique identifier
- `icon`: Visual representation (e.g., 'leaf' for Environmental)
- `order`: Display sequence

### 2. ESG Forms
Forms are predefined sets of metrics that align with HKEX reporting requirements:
- **HKEX-A1**: Emissions
- **HKEX-A2**: Resource Use
- **HKEX-B1**: Employment
- **HKEX-B2**: Health and Safety
etc.

Properties:
- `category`: Link to ESG Form Category
- `code`: Unique identifier (e.g., 'HKEX-A1')
- `name`: Display name
- `description`: Detailed explanation
- `is_active`: Whether the form is currently in use
- `order`: Display sequence within category

### 3. Polymorphic ESG Metrics (`BaseESGMetric` and Subclasses)
Metrics are the actual data points collected for each form, now defined polymorphically.

**Base Properties (`BaseESGMetric`):**
- `form`: Link to ESG Form
- `name`: Name of the metric
- `description`: Detailed explanation
- `order`: Display sequence within form
- `requires_evidence`: Whether supporting documentation is required
- `validation_rules`: JSON field for rules (e.g., min/max, regex) applied *during submission data validation*.
- `location`: Where this metric applies ('HK', 'PRC', 'ALL')
- `is_required`: Whether this metric must have a final `ReportedMetricValue` (level='A') for form completion.
- `aggregates_inputs`: If `True`, the `calculate_report_value` service processes raw inputs to generate a `ReportedMetricValue`. If `False`, aggregation is skipped.
- `help_text`: Guidance text for users.
- `ocr_analyzer_id`: Optional Azure Form Recognizer ID.

**Specialized Types (Examples):**
- **`BasicMetric`**: For single values. Adds `unit_type` (kWh, tonnes, text, count, etc.) and `custom_unit`.
- **`TabularMetric`**: For row-based data. Adds `column_definitions` (JSON defining keys, labels, types), `allow_adding_rows`, `min_rows`, `max_rows`.
- **`TimeSeriesMetric`**: For periodic single values. Adds `frequency` (monthly, annual), `aggregation_method` (SUM, AVG, LAST), `unit_type`.
- **`MaterialTrackingMatrixMetric`**: Specific for material tracking. Adds `category` (waste, packaging), `max_material_types`, `default_unit`, `fixed_time_period`.
- **`MultiFieldTimeSeriesMetric`**: For tracking multiple defined fields over time. Adds `field_definitions` (JSON), `frequency`, `total_row_aggregation` rules.
- **`MultiFieldMetric`**: For a fixed set of related fields reported once. Adds `field_definitions` (JSON).

### 4. Submission Data Structure
- **`ESGMetricSubmission` (Header)**: Contains `assignment`, `metric` (FK to `BaseESGMetric`), `layer`, `reporting_period` (tag), `submitted_by`, `submitted_at`, `is_verified` (for input), `notes`, `source_identifier`.
- **`BasicMetricData`**: Linked OneToOne to header. Contains `value_numeric`, `value_text`.
- **`TabularMetricRow`**: Linked ManyToOne (FK) to header. Contains `row_index`, `row_data` (JSON).
- **`TimeSeriesDataPoint`**: Linked ManyToOne to header. Contains `period` (date), `value` (float).
- **`MaterialMatrixDataPoint`**: Linked ManyToOne to header. Contains `material_type` (str), `period` (date), `value` (float), `unit` (str).
- **`MultiFieldTimeSeriesDataPoint`**: Linked ManyToOne to header. Contains `period` (date), `field_data` (JSON).
- **`MultiFieldDataPoint`**: Linked OneToOne to header. Contains `field_data` (JSON).

### 5. Custom Forms and Metrics
The system allows Baker Tilly administrators to create custom forms and metrics for specific client needs:

1. **Custom Categories**: New form categories can be created beyond the standard Environmental, Social, and Governance.
2. **Custom Forms**: Administrators can create bespoke forms for specialized reporting requirements.
3. **Custom Metrics**: Industry-specific or client-specific metrics can be defined with flexible properties:
   - Custom unit types
   - Location-specific metrics
   - Time-based reporting frequencies
   - Validation rules to ensure data quality
   - Configuration as multi-value metrics with custom fields.

Custom forms and metrics can be created alongside standard forms in templates, allowing a mix of standardized and client-specific reporting within the same workflow.

### Related API Endpoints:
- `POST /api/esg-categories/`: Create custom category
- `POST /api/esg-forms/`: Create custom form
- **`POST /api/esg-forms/{id}/add_metric/`**: Add a polymorphic metric to a form (requires `metric_subtype` and type-specific fields in payload).
- `GET /api/esg-metrics/{id}/`: Get specific metric details (will include type-specific fields).
- `PUT /api/esg-metrics/{id}/`: Update metric (requires `metric_subtype` and type-specific fields).

## Templates and Assignments

### 1. Templates
Templates combine multiple ESG forms for assignment to companies:

Properties:
- `name`: Template name
- `description`: Template description
- `is_active`: Whether template is currently usable
- `version`: Template version number
- `created_by`: Baker Tilly admin who created the template

### 2. Template Form Selection
Links templates to specific forms with regional configuration:

Properties:
- `template`: Link to Template
- `form`: Link to ESG Form
- `regions`: List of applicable regions
- `order`: Display sequence in template
- `is_completed`: Whether this form has been completed *based on the existence of final ReportedMetricValue records* for its required metrics within the linked assignment.
- `completed_at`: When the form was marked complete.
- `completed_by`: User who triggered the completion check that resulted in the form being marked complete.

### 3. Template Assignment
Assigns templates to companies for reporting:

Properties:
- `template`: Link to Template
- `layer`: Link to Company (LayerProfile)
- `assigned_to`: User responsible for reporting
- `due_date`: Submission deadline
- `status`: Current status (PENDING, IN_PROGRESS, SUBMITTED, VERIFIED, REJECTED)
- `reporting_period_start`: Start of reporting period covered by assignment.
- `reporting_period_end`: End of reporting period covered by assignment.
- `reporting_year`: (Deprecated, use start/end dates) The specific year for which data is being reported.
- `completed_at`: When the template assignment was marked 'SUBMITTED'.

### User Template Management

#### GET /api/user-templates/
Returns all template assignments accessible to the authenticated user, including templates assigned to their direct layer and parent layers.

**Response Example:**
```json
[
  {
    "id": 1, // Assignment ID
    "template": { // Template Object (TemplateSerializer)
      "id": 1,
      "name": "HKEX ESG Reporting Template 2024",
      "description": "Standard HKEX template covering Environmental, Social, and Governance aspects.",
      "is_active": true,
      "version": 1,
      "created_by": 1, // User ID
      "created_at": "2024-05-01T10:00:00Z",
      "updated_at": "2024-05-10T11:30:00Z",
      "selected_forms": [ // Nested List (TemplateFormSelectionSerializer)
        {
          "id": 10,
          "form": { // Basic Form Details (ESGFormSerializer)
            "id": 1,
            "code": "HKEX-A1",
            "name": "Environmental - Emissions",
            "description": "Reporting on greenhouse gas emissions.",
            "is_active": true,
            "category": { // Nested Category (ESGFormCategorySerializer)
              "id": 1,
              "name": "Environmental",
              "code": "environmental",
              "icon": "leaf",
              "order": 1
            },
            "category_id": 1,
            "order": 1,
            "metric_count": 3
          },
          "regions": ["HK", "PRC"],
          "order": 1,
          "is_completed": false,
          "completed_at": null,
          "completed_by": null
        },
        {
          "id": 11,
          "form": {
            "id": 2,
            "code": "HKEX-A2",
            "name": "Environmental - Resource Use",
            "description": "Reporting on consumption of resources like water and energy.",
            "is_active": true,
            "category": {
              "id": 1,
              "name": "Environmental",
              "code": "environmental",
              "icon": "leaf",
              "order": 1
            },
            "category_id": 1,
            "order": 2,
            "metric_count": 2
          },
          "regions": ["HK"],
          "order": 2,
          "is_completed": false,
          "completed_at": null,
          "completed_by": null
        }
      ]
    },
    "layer": { // Nested Layer (LayerBasicSerializer)
        "id": 5,
        "company_name": "Example Subsidiary Ltd."
    },
    "assigned_to": 25, // User ID or null
    "assigned_at": "2024-06-01T09:00:00Z",
    "due_date": "2025-03-31",
    "completed_at": null,
    "reporting_period_start": "2024-01-01",
    "reporting_period_end": "2024-12-31",
    "reporting_year": 2024,
    "status": "IN_PROGRESS",
    "relationship": "direct" // Added by view
  },
  {
    "id": 2, // Second Assignment example
    "template": { // Template Object
      "id": 2,
      "name": "Governance Disclosure 2024",
      "description": "Template for governance reporting.",
      "is_active": true,
      "version": 1,
      "created_by": 1,
      "created_at": "2024-04-15T14:00:00Z",
      "updated_at": "2024-04-15T14:00:00Z",
      "selected_forms": [
        {
          "id": 15,
          "form": {
            "id": 5,
            "code": "HKEX-G1",
            "name": "Governance - Board Structure",
            "description": "Details about the board.",
            "is_active": true,
            "category": {
              "id": 3,
              "name": "Governance",
              "code": "governance",
              "icon": "balance-scale",
              "order": 3
            },
            "category_id": 3,
            "order": 1,
            "metric_count": 4
          },
          "regions": ["ALL"],
          "order": 1,
          "is_completed": true,
          "completed_at": "2024-11-01T16:00:00Z",
          "completed_by": 30
        }
      ]
    },
    "layer": { // Layer for the second assignment
      "id": 1,
      "company_name": "Parent Group Inc."
    },
    "assigned_to": 30, // User ID
    "assigned_at": "2024-07-01T10:00:00Z",
    "due_date": "2025-01-31",
    "completed_at": "2024-11-01T16:00:00Z", // Example completed assignment
    "reporting_period_start": "2024-01-01",
    "reporting_period_end": "2024-12-31",
    "reporting_year": 2024,
    "status": "SUBMITTED",
    "relationship": "inherited" // Example inherited assignment
  }
  // ... more assignments in the list ...
]
```

**Key Features:**
- Automatically finds templates assigned to the user's layer and all parent layers
- No parameters required - uses the authenticated user's context
- Includes "relationship" field to indicate if the template is directly assigned to the user's layer or inherited from a parent
- Provides essential template information including status and due dates

#### GET /api/user-templates/{assignment_id}/
Returns detailed **metadata** about a specific template assignment, such as status, dates, and layer information.

**Response Example:**
```json
{
  "id": 1,
  "template": {
    "id": 1,
    "name": "HKEX ESG Reporting Template 2024",
    "description": "Standard HKEX template covering Environmental, Social, and Governance aspects.",
    "is_active": true,
    "version": 1,
    "created_by": 1, // User ID
    "created_at": "2024-05-01T10:00:00Z",
    "updated_at": "2024-05-10T11:30:00Z",
    "selected_forms": [
      {
        "id": 10, // TemplateFormSelection ID
        "form": { // Basic Form Details (from ESGFormSerializer)
          "id": 1,
          "code": "HKEX-A1",
          "name": "Environmental - Emissions",
          "description": "Reporting on greenhouse gas emissions.",
          "is_active": true,
          "category": { // Nested Category (from ESGFormCategorySerializer)
            "id": 1,
            "name": "Environmental",
            "code": "environmental",
            "icon": "leaf",
            "order": 1
          },
          "category_id": 1, // Write-only field, not typically shown in read response
          "order": 1, // Form's order within its category
          "metric_count": 3 // Example count of metrics in this form
        },
        "regions": ["HK", "PRC"], // Regions selected for this form in this template
        "order": 1, // Order of this form within this template
        "is_completed": false,
        "completed_at": null,
        "completed_by": null // User ID or null
      },
      {
        "id": 11, // TemplateFormSelection ID
        "form": { // Basic Form Details (from ESGFormSerializer)
          "id": 2,
          "code": "HKEX-A2",
          "name": "Environmental - Resource Use",
          "description": "Reporting on consumption of resources like water and energy.",
          "is_active": true,
          "category": { // Nested Category
            "id": 1,
            "name": "Environmental",
            "code": "environmental",
            "icon": "leaf",
            "order": 1
          },
          "category_id": 1,
          "order": 2,
          "metric_count": 2
        },
        "regions": ["HK"], // Different regions for this form
        "order": 2,
        "is_completed": false,
        "completed_at": null,
        "completed_by": null
      }
      // ... potentially more selected forms ...
    ]
  },
  "layer": { // Nested Layer Details (from LayerBasicSerializer)
      "id": 5,
      "company_name": "Example Subsidiary Ltd."
  },
  "assigned_to": 25, // User ID or null
  "assigned_at": "2024-06-01T09:00:00Z",
  "due_date": "2025-03-31",
  "completed_at": null,
  "reporting_period_start": "2024-01-01",
  "reporting_period_end": "2024-12-31",
  "reporting_year": 2024, // Or null/deprecated depending on implementation
  "status": "IN_PROGRESS", // e.g., PENDING, IN_PROGRESS, SUBMITTED, VERIFIED, REJECTED
  "relationship": "direct" // Added by the view ('direct' or 'inherited')
}
```

#### GET /api/user-templates/{assignment_id}/structure/
Returns the detailed structure (forms and metrics) for a specific template assignment.

**Response Example:**
```json
{
  "forms": [
    {
      "form_id": 1,
      "form_code": "HKEX-A1",
      "form_name": "Environmental - Emissions",
      "regions": ["HK", "PRC"], // Regions active for this form in this assignment
      "category": { // Full Category Details
        "id": 1,
        "name": "Environmental",
        "code": "environmental",
        "icon": "leaf",
        "order": 1
      },
      "order": 1, // Form's order within the template selection
      "metrics": [ // Detailed Polymorphic Metrics List
        {
          // --- Fields from BaseESGMetric ---
          "id": 1,
          "metric_subtype": "BasicMetric", // Added by polymorphic serializer
          "name": "Scope 1 GHG Emissions",
          "description": "Direct emissions from owned or controlled sources.",
          "order": 1, // Metric order within the form
          "requires_evidence": true,
          "validation_rules": {"min": 0},
          "location": "ALL", // Location applicability
          "is_required": true,
          "aggregates_inputs": true,
          "help_text": "Report total Scope 1 emissions in tonnes of CO2e.",
          "ocr_analyzer_id": null,
          // --- Fields specific to BasicMetric ---
          "unit_type": "tCO2e", // Display value or code
          "custom_unit": null
        },
        {
          // --- Fields from BaseESGMetric ---
          "id": 2,
          "metric_subtype": "BasicMetric",
          "name": "Scope 2 GHG Emissions",
          "description": "Indirect emissions from the generation of purchased energy.",
          "order": 2,
          "requires_evidence": true,
          "validation_rules": {"min": 0},
          "location": "ALL",
          "is_required": true,
          "aggregates_inputs": true,
          "help_text": "Report total Scope 2 emissions in tonnes of CO2e.",
          "ocr_analyzer_id": null,
          // --- Fields specific to BasicMetric ---
          "unit_type": "tCO2e",
          "custom_unit": null
        },
        {
           // --- Fields from BaseESGMetric ---
          "id": 5,
          "metric_subtype": "TimeSeriesMetric",
          "name": "Electricity Consumption (Grid)",
          "description": "Monthly electricity consumption from the grid.",
          "order": 3,
          "requires_evidence": true,
          "validation_rules": {"min": 0},
          "location": "HK", // Specific location example
          "is_required": true,
          "aggregates_inputs": true,
          "help_text": "Report monthly grid electricity usage in kWh.",
          "ocr_analyzer_id": null,
           // --- Fields specific to TimeSeriesMetric ---
          "frequency": "monthly", // Display value or code
          "aggregation_method": "SUM", // Display value or code
          "unit_type": "kWh",
          "custom_unit": null
        }
        // ... more metrics for this form ...
      ]
    },
    {
      "form_id": 2,
      "form_code": "HKEX-A2",
      "form_name": "Environmental - Resource Use",
      "regions": ["HK"], // Regions active for this form in this assignment
      "category": { // Full Category Details
        "id": 1,
        "name": "Environmental",
        "code": "environmental",
        "icon": "leaf",
        "order": 1
      },
      "order": 2, // Form's order within the template selection
      "metrics": [
        {
           // --- Fields from BaseESGMetric ---
          "id": 10,
          "metric_subtype": "BasicMetric",
          "name": "Total Water Consumption",
          "description": "Total water consumed from all sources.",
          "order": 1,
          "requires_evidence": false,
          "validation_rules": {"min": 0},
          "location": "HK",
          "is_required": true,
          "aggregates_inputs": true,
          "help_text": "Report total water usage in cubic meters (m³).",
          "ocr_analyzer_id": null,
           // --- Fields specific to BasicMetric ---
          "unit_type": "m3",
          "custom_unit": null
        }
        // ... more metrics for this form ...
      ]
    }
    // ... more forms ...
  ]
}
```

**Important Notes:**
- Returns complete form and metric details for the template assignment structure.
- Only includes metrics relevant to the selected regions for the specific form within the assignment.
- Provides validation rules and requirements for each metric
- **Includes category information for each form**, allowing frontend to group forms by category

### Reporting Year Implementation

Starting in 2025, the system uses a simplified approach to track reporting periods:

1. **New Field: `reporting_year`**
   - Added to the `TemplateAssignment` model
   - Represents the year for which data is being collected
   - Default value: 2025
   - Simplifies the reporting period context

2. **Transition from Date Ranges**
   - The previous fields `reporting_period_start` and `reporting_period_end` are now deprecated
   - They remain in the database for backward compatibility
   - New implementations should use the more intuitive `reporting_year` field
   - Frontend applications should prioritize displaying and using the reporting_year

3. **Benefits**
   - More intuitive for users (clear indication of which calendar year is being reported on)
   - Simplifies filtering and queries
   - Aligns with how most ESG reporting is structured (annual basis)

4. **API Considerations**
   - All API responses now include the `reporting_year` field
   - Applications should be updated to handle this new field appropriately
   - Date range fields will continue to be included in responses for backward compatibility

## Location-Based Reporting

The system supports location-based reporting for companies operating in:
- Hong Kong only
- Mainland China only
- Both Hong Kong and Mainland China

Key features:
1. **Flexible Metrics**: Each metric can be location-specific
2. **Optional Reporting**: Location-specific metrics are optional by default
3. **Automatic Adaptation**: Reports automatically adjust based on company operations

Example:
```python
# Health and Safety metrics for both locations
"Number of work-related fatalities (HK)" - order=1
"Number of work-related fatalities (PRC)" - order=2
"Lost days due to work injury (HK)" - order=3
"Lost days due to work injury (PRC)" - order=4
```

## Time-Based Reporting (Inputs and Aggregation)

The system supports time-based reporting for metrics like `TimeSeriesMetric`, `MaterialTrackingMatrixMetric`, and `MultiFieldTimeSeriesMetric`.

1.  **Configuring Time-Based Metrics**: Set the `frequency` field (e.g., 'monthly', 'annual') on the metric definition. Set the `aggregation_method` ('SUM', 'AVG', 'LAST') for `TimeSeriesMetric`.
2.  **Submitting Time-Based *Inputs***:
    - Create an `ESGMetricSubmission` header record, tagging it with a consistent `reporting_period` (e.g., month-end date).
    - Provide the actual data, including the specific `period` date, in the linked data model (e.g., `TimeSeriesDataPoint`, `MaterialMatrixDataPoint`, `MultiFieldTimeSeriesDataPoint`).
    - Multiple *input* records (header + specific data) will typically be created over the reporting year.
3.  **Aggregation**:
    - When an input is saved/deleted, the `calculate_report_value` service is triggered via signals.
    - It calculates aggregates for relevant levels (e.g., Monthly, Annual) and target `reporting_period` end dates.
    - It fetches the relevant specific data points (e.g., `TimeSeriesDataPoint`) based on their `period` falling within the calculated window (e.g., all points where `period` is in January for the 'M' level ending '2024-01-31').
    - It applies the aggregation method (SUM, AVG, LAST) to the filtered data points.
    - It saves the result in `ReportedMetricValue`, tagged with the correct target `reporting_period` and `level`.

## Aggregation Service (`calculate_report_value`)

For metrics marked with `aggregates_inputs=True`, the `calculate_report_value` service automatically calculates and updates the final aggregated values stored in `ReportedMetricValue`.

- **Trigger**: Triggered by `post_save`/`post_delete` signals on `ESGMetricSubmission`.
- **Context**: Requires `assignment`, `metric`, `layer`, target `reporting_period` (end date), and target `level` ('M', 'A').
- **Logic**:
    - Determines the metric's specific type (e.g., `BasicMetric`, `TimeSeriesMetric`).
    - Fetches relevant `ESGMetricSubmission` headers broadly.
    - Fetches *all* linked specific data records (e.g., `BasicMetricData`, `TimeSeriesDataPoint`).
    - Filters the specific data records based on the target `reporting_period` and `level` (e.g., selects `TimeSeriesDataPoint` where `period` falls within the target month/year).
    - Applies aggregation (SUM, AVG, LAST, COUNT, etc.) based on metric type and configuration to the *filtered* data. Placeholder logic exists for complex types (`Tabular`, `MaterialMatrix`, etc.).
    - Creates/Updates the `ReportedMetricValue` record for the specific `reporting_period` and `level`, storing the result in `aggregated_numeric_value` or `aggregated_text_value` and updating metadata. If no relevant data is found for the period/level, any existing `ReportedMetricValue` for that slot is deleted.

## API Endpoints

### ESG Data Management

#### ESG Data Endpoints (Legacy - Review if still needed)
- `GET /api/esg-data/?company_id={id}`: Get ESG data entries for a company
- `POST /api/esg-data/`: Create new ESG data entry
- `PUT /api/esg-data/{data_id}/`: Update ESG data entry
- `POST /api/esg-data/{data_id}/verify/`: Verify ESG data entry (Baker Tilly admin only)
**(Note: These endpoints seem related to an older model `ESGData`. Review if this model and its endpoints are still relevant alongside the Template/Submission/ReportedValue system).**

### ESG Metric Submission Endpoints (`/api/metric-submissions/`)
Manages the **raw input headers** (`ESGMetricSubmission` model) and their linked specific data.

- `GET /api/metric-submissions/`: List accessible submission *headers*. Response now includes `submission_data` field containing nested specific data based on metric type.
- `POST /api/metric-submissions/`: Submit a single metric input. Payload requires `metric` (BaseESGMetric ID), `assignment`, and a specific data field matching the metric type (e.g., `basic_data`, `tabular_rows`). Triggers aggregation.
- `GET /api/metric-submissions/{id}/`: Get details of a specific submission *header*. Response includes `submission_data` field.
- `PUT /api/metric-submissions/{id}/`: Update a metric input header and its associated specific data (full replace for list data like tabular rows). Triggers aggregation.
- `PATCH /api/metric-submissions/{id}/`: Partially update a metric input header (cannot partially update nested specific data easily with default implementation). Triggers aggregation.
- `DELETE /api/metric-submissions/{id}/`: Delete a metric input header and its linked specific data. Triggers aggregation.
- `GET /api/metric-submissions/by_assignment/?assignment_id={id}`: Get all submission *headers* for an assignment. Supports filtering. Response includes `submission_data`.
- `POST /api/metric-submissions/batch_submit/`: Submit multiple metric inputs at once. Payload requires `assignment_id` and a `submissions` list, where each item contains `metric` and a specific data field (e.g., `basic_data`). Triggers aggregation.
- `POST /api/metric-submissions/submit_template/`: Mark a template assignment as submitted. Checks for the existence of required **annual** (`level='A'`) `ReportedMetricValue` records.
- `POST /api/metric-submissions/{id}/verify/`: Verify a *specific raw input header* (`ESGMetricSubmission`). (Baker Tilly admin only).
- `GET /api/submissions/available-layers/`: Get layers accessible to the user.
- `GET /api/submissions/sum-by-layer/`: Aggregate *raw inputs* by layer (reads from specific data models).

### Reported Metric Value Endpoints (`/api/reported-metric-values/`)
Provides **read-only access** to the final, calculated **aggregated metric records** (`ReportedMetricValue`).

- `GET /api/reported-metric-values/`: List accessible final aggregated records.
- **Filtering**: Supports filtering by `assignment`, `metric` (BaseESGMetric ID), `layer`, `reporting_period`, and **`level`** ('M', 'A').
- **Permissions**: Users only see values for layers they have access to or assignments assigned to them.
- **Response**: Includes the `ReportedMetricValue` details (metadata, final aggregated value, `level`). **Does not include nested fields anymore.**

**Example Request:**
```
GET /api/reported-metric-values/?assignment=1&metric=5&layer=3&reporting_period=2024-12-31&level=A
```

**Example Response (Updated):**
```json
[
  {
    "id": 55, // ID of the ReportedMetricValue
    "assignment": 1,
    "metric": 5, // ID of the BaseESGMetric
    // "metric_unit": "tonnes", // Unit is on specific metric, not easily available here
    "layer": 3,
    "layer_name": "Manufacturing Division", // From layer relation
    "reporting_period": "2024-12-31",
    "level": "A", // The aggregation level this record represents
    "aggregated_numeric_value": 18050.5, // Final calculated value
    "aggregated_text_value": null,
    // --- Calculation & Aggregation Metadata ---
    "calculated_at": "2025-01-10T10:00:00Z",
    "last_updated_at": "2025-01-15T11:30:00Z",
    "source_submission_count": 12, // Count of source inputs *used for this specific period/level*
    "first_submission_at": "2024-01-15T09:00:00Z", // Timestamp of earliest submission header found
    "last_submission_at": "2024-12-10T14:00:00Z" // Timestamp of latest submission header found
  }
]
```

### ESG Metric Evidence Endpoints
- `GET /api/metric-evidence/`: List all accessible evidence files
- `POST /api/metric-evidence/`: Upload evidence for a metric submission
- `GET /api/metric-evidence/{id}/`: Get details of a specific evidence file
- `DELETE /api/metric-evidence/{id}/`: Delete an evidence file
- `GET /api/metric-evidence/by_submission/?submission_id={id}`: Get all evidence for a submission
- `GET /api/metric-evidence/batch/?submission_ids=1,2,3,4,5`: Get submission data and evidence for multiple submissions

### Form and Template Management

#### ESG Forms
- `GET /api/esg-forms/`: List active ESG forms. **Uses `ESGFormSerializer` and returns basic form details *without* nested metrics, but *includes* `metric_count` (the number of metrics associated with the form), optimized for list views.**
- `GET /api/esg-forms/{id}/`: Get specific form details. **Uses `ESGFormDetailSerializer` and includes nested `polymorphic_metrics` for the specified form.**
- `POST /api/esg-forms/`: Create new ESG form (Baker Tilly Admin only)
- `PUT /api/esg-forms/{id}/`: Update ESG form (Baker Tilly Admin only)
- `DELETE /api/esg-forms/{id}/`: Delete ESG form (Baker Tilly Admin only)
- `GET /api/esg-forms/{id}/metrics/`: Get **polymorphic** metrics for a specific form (uses `ESGMetricPolymorphicSerializer`). **Note:** The detail view (`GET /api/esg-forms/{id}/`) now also includes these metrics.
- `POST /api/esg-forms/{id}/add_metric/`: Add a **polymorphic** metric to a form (Admin only, requires `metric_subtype` in payload).
- `GET /api/esg-forms/{id}/check_completion/?assignment_id={id}`: Check completion status (uses `ReportedMetricValue`, level 'A').
- `POST /api/esg-forms/{id}/complete_form/`: Mark a form as completed (uses `ReportedMetricValue`, level 'A').

#### ESG Categories
- `GET /api/esg-categories/`: List all categories with their active forms
- `GET /api/esg-categories/{id}/`: Get specific category details
- `POST /api/esg-categories/`: Create new category (Baker Tilly Admin only)
- `PUT /api/esg-categories/{id}/`: Update category (Baker Tilly Admin only)
- `PATCH /api/esg-categories/{id}/`: Partially update category (Baker Tilly Admin only)
- `DELETE /api/esg-categories/{id}/`: Delete category (Baker Tilly Admin only)

#### ESG Metrics (Polymorphic)
- `GET /api/esg-metrics/`: List all *base* metrics (might not be very useful). Use `/api/esg-forms/{id}/metrics/` instead.
- `GET /api/esg-metrics/{id}/`: Get specific metric details (will use polymorphic serializer to show correct fields).
- `POST /api/esg-metrics/`: Create new metric (Admin only - requires `metric_subtype` and type-specific fields).
- `PUT /api/esg-metrics/{id}/`: Update metric (Admin only - requires `metric_subtype` and type-specific fields).
- `DELETE /api/esg-metrics/{id}/`: Delete metric (Admin only).

#### Templates (Baker Tilly Admin only)
- `GET /api/templates/`: List all templates
- `POST /api/templates/`: Create new template
- `GET /api/templates/{id}/`: Get template details
- `PUT /api/templates/{id}/`: Update template
- `DELETE /api/templates/{id}/`: Delete template
- `GET /api/templates/{id}/preview/`: Preview template with forms and metrics
- `GET /api/templates/{id}/completion_status/?assignment_id={id}`: Get completion status (uses `ReportedMetricValue`, level 'A').

#### Template Assignments
- `GET /api/clients/{layer_id}/templates/`: Get client's template assignments
- `POST /api/clients/{layer_id}/templates/`: Assign template to client
- `DELETE /api/clients/{layer_id}/templates/`: Remove template assignment (requires assignment_id in request body)

### API Best Practices

#### PUT vs PATCH for Updates

The ESG Platform API supports both PUT and PATCH for updating resources, each with a different purpose:

- **PUT**: Use when updating an entire resource. You must include all required fields in the request, even if you're only changing one value. Missing fields may be reset to defaults.

- **PATCH**: Use when updating only specific fields of a resource. Only the fields included in the request will be modified; all other fields will remain unchanged.

Example PATCH request:
```json
PATCH /api/esg-metrics/26/
{
    "is_required": false,
    "order": 3
}
```

This is more efficient than PUT when you only need to update a few fields, as it requires less data to be sent and processed.

### API Permissions Overview

The ESG Platform API implements granular permissions based on user roles:

1. **Baker Tilly Admins**
   - Full access to all endpoints and data
   - Can access and modify data for all clients, templates, and submissions
   - Can verify submissions (`POST /api/metric-submissions/{id}/verify/`)
   - Can create and manage templates, forms, metrics, and multi-value fields.

2. **Regular Users**
   - Access restricted to their assigned layers (companies/organizations)
   - Can only view and modify submissions for their own layers
   - Can't access data from other client organizations
   - Can't verify submissions (reserved for Baker Tilly admins)

For many endpoints, the system automatically filters results based on user permissions, so regular users will only see data they have access to, while Baker Tilly admins see all data.

### Enhanced Endpoints for Optimized Review

The API includes optimized endpoints that make the review process more efficient:

#### 1. Filtered Metric Submission *Inputs*
```
GET /api/metric-submissions/by_assignment/?assignment_id={id}&form_id={form_id}
```

**Permissions:**
- Baker Tilly admins can view all submissions for any assignment
- Regular users can only view submissions for:
  - Assignments directly assigned to them
  - Assignments within their layer
  - Assignments from parent layers they have access to

**Features:**
- Filter submissions by form_id to focus on one form at a time
- Filter by verification status with `is_verified=true|false`
- Filter by submission date ranges with `submitted_after` and `submitted_before`
- Sort results with `sort_by` and `sort_direction` parameters
- Paginate results with `page` and `page_size` parameters

**Example Request:**
```
GET /api/metric-submissions/by_assignment/?assignment_id=5&form_id=2&is_verified=false&page=1&page_size=50&sort_by=submitted_at&sort_direction=desc
```

**Example Response:**
```json
{
  "total_count": 120,
  "page": 1,
  "page_size": 50,
  "total_pages": 3,
  "results": [
    {
      "id": 1,
      "assignment": 1,
      "metric": 5,
      "metric_name": "Electricity consumption (CLP)",
      "metric_unit": "kWh",
      "value": 120.5,
      "submitted_by_name": "john.doe@example.com",
      "submitted_at": "2024-04-15T10:30:00Z",
      "is_verified": false,
      "evidence": []
    },
    // ... more submissions
  ]
}
```

#### 2. Batch Evidence Retrieval
```
GET /api/metric-evidence/batch/?submission_ids=1,2,3,4,5
```

**Permissions:**
- Baker Tilly admins can access all submissions and evidence
- Regular users can only access submissions and evidence for their assigned layers
- Results are automatically filtered based on user permissions

**Features:**
- Fetch submission data and evidence for multiple submissions in a single request
- Includes complete submission details including metric information and verification status
- Evidence is nested within each submission's data
- Reduces network overhead during verification workflows

**Example Response:**
```json
{
  "1": {
    "id": 1,
    "assignment": 1,
    "metric": 5,
    "metric_name": "Electricity consumption (CLP)",
    "metric_unit": "kWh",
    "value": 120.5,
    "text_value": null,
    "submitted_by": 3,
    "submitted_by_name": "john.doe@example.com",
    "submitted_at": "2024-04-15T10:30:00Z",
    "updated_at": "2024-04-15T10:30:00Z",
    "notes": "Value from March 2024 electricity bill",
    "is_verified": false,
    "verified_by": null,
    "verified_by_name": null,
    "verified_at": null,
    "verification_notes": "",
    "evidence": [
      {
        "id": 1,
        "file": "/media/esg_evidence/2024/04/emissions_report.pdf",
        "filename": "emissions_report.pdf",
        "file_type": "application/pdf",
        "uploaded_by_name": "john.doe@example.com",
        "uploaded_at": "2024-04-15T10:35:00Z",
        "description": "Emissions report for Q1 2024"
      }
    ]
  },
  "2": {
    "id": 2,
    "assignment": 1,
    "metric": 6,
    "metric_name": "Water consumption",
    "metric_unit": "m3",
    "value": 85.2,
    "text_value": null,
    "submitted_by": 3,
    "submitted_by_name": "john.doe@example.com",
    "submitted_at": "2024-04-15T10:30:00Z",
    "updated_at": "2024-04-15T10:30:00Z",
    "notes": "Value from March 2024 water bill",
    "is_verified": false,
    "verified_by": null,
    "verified_by_name": null,
    "verified_at": null,
    "verification_notes": "",
    "evidence": [
      {
        "id": 2,
        "file": "/media/esg_evidence/2024/04/electricity_bill.pdf",
        "filename": "electricity_bill.pdf",
        "file_type": "application/pdf",
        "uploaded_by_name": "john.doe@example.com",
        "uploaded_at": "2024-04-15T10:36:00Z",
        "description": "Electricity bill for March 2024"
      }
    ]
  }
}
```

These optimized endpoints maintain the separate endpoint architecture while addressing potential performance bottlenecks in the review process. They provide targeted improvements for specific admin workflows without introducing the complexity of fully consolidated endpoints.

### Client Integration Guidelines

When integrating with these endpoints in your client application:

1. **Authentication:** Always include authentication tokens in your requests.
2. **Error Handling:** Handle 403 Forbidden responses gracefully, as they indicate permission issues.
3. **Pagination:** For endpoints that support pagination:
   - Always check total_count and total_pages in the response
   - Implement pagination controls in your UI
   - Set reasonable page_size values (10-50 items per page recommended)
4. **Batch Processing:** Use batch endpoints when dealing with multiple related items to reduce API calls.

### Example Requests and Responses

#### Submit a Single Metric Input Value
```json
POST /api/metric-submissions/
{
    "assignment": 1,
    "metric": 5,
    "layer_id": 3,
    "reporting_period": "2024-03-31",
    "notes": "Input value for March 2024 electricity",
    "basic_data": {
        "value_numeric": 120.5
    }
}

// Response (Example - Updated)
{
    "id": 101,
    "assignment": 1,
    "metric": 5,
    "metric_name": "Electricity consumption (CLP)",
    "reporting_period": "2024-03-31",
    "submitted_by_name": "john.doe@example.com",
    "submitted_at": "...",
    "updated_at": "...",
    "notes": "Input value for March 2024 electricity",
    "is_verified": false,
    "layer_id": 3,
    "layer_name": "Manufacturing Division",
    "source_identifier": null,
    "evidence": [],
    "submission_data": {
        "data_type": "BasicMetricData",
        "value_numeric": 120.5,
        "value_text": null
    }
}
```

#### Batch Submit Multiple Metric Input Values
```json
POST /api/metric-submissions/batch_submit/
{
  "assignment_id": 1,
  "submissions": [
    {
      "metric": 5,
      "layer_id": 3,
      "reporting_period": "2024-06-30",
      "source_identifier": "Meter A",
      "basic_data": { "value_numeric": 1234.56 }
    },
    {
      "metric": 6,
      "layer_id": 4,
      "reporting_period": "2024-06-30",
      "source_identifier": "Waste Log",
      "tabular_rows": [
          { "row_index": 0, "row_data": { "waste_type": "Paper", "amount_kg": 50 } },
          { "row_index": 1, "row_data": { "waste_type": "Plastic", "amount_kg": 25 } }
      ]
    }
  ]
}

// Response (Example - List of created submission headers w/ data)
[
    {
        "id": 102,
        "assignment": 1,
        "metric": 5,
        "metric_name": "...",
        "reporting_period": "2024-06-30",
        // ... other header fields ...
        "source_identifier": "Meter A",
        "submission_data": {
            "data_type": "BasicMetricData",
            "value_numeric": 1234.56,
            "value_text": null
        }
    },
    {
        "id": 103,
        "assignment": 1,
        "metric": 6,
        "metric_name": "...",
        "reporting_period": "2024-06-30",
        // ... other header fields ...
        "source_identifier": "Waste Log",
        "submission_data": {
            "data_type": "TabularMetricRow",
            "many": true,
            "results": [
                {"id": 201, "row_index": 0, "row_data": {"waste_type": "Paper", "amount_kg": 50}},
                {"id": 202, "row_index": 1, "row_data": {"waste_type": "Plastic", "amount_kg": 25}}
            ]
        }
    }
]

```

##### Check Form Completion Status
(Description updated to reflect check against `ReportedMetricValue` level 'A').
```json
GET /api/esg-forms/{form_id}/check_completion/?assignment_id=1

// Response (Example reflecting new logic)
{
    "form_id": 2,
    "form_name": "Resource Use",
    "form_code": "HKEX-A2",
    "assignment_id": 1,
    "is_completed": false,
    "is_actually_complete": false,
    "status_inconsistent": false,
    "completed_at": null,
    "completed_by": null,
    "completion_percentage": 75.0,
    "total_required_points": 4,
    "reported_points_count": 3,
    "missing_final_reported_values": [
        {"metric_id": 10, "metric_name": "Wastewater consumption", "location": "HK", "expected_periods_count": 1, "found_periods_count": 0, "missing_periods": ["2024-12-31"]}
    ],
    "can_complete": false
}
```

##### Complete a Form
(Description updated).
```json
POST /api/esg-forms/{form_id}/complete_form/
{
    "assignment_id": 1
}

// Response (Success Example)
{
    "message": "Form 'Resource Use' successfully marked as completed.",
    "form_id": 2,
    "form_is_complete": true,
    "assignment_status_updated": false,
    "assignment_status": "In Progress"
}
```

##### Submit a Template
(Description updated).
```json
POST /api/metric-submissions/submit_template/
{
    "assignment_id": 1
}

// Response (Success Example)
{
    "message": "Template successfully submitted (all required annual reported values exist)",
    "assignment_id": 1,
    "status": "SUBMITTED",
    "completed_at": "..."
}
```

##### Get Template Completion Status
(Description updated).
```json
GET /api/templates/{template_id}/completion_status/?assignment_id=1

// Response (Example reflecting new logic)
{
    "assignment_id": 1,
    "template_id": 1,
    "template_name": "Environmental Assessment 2024",
    "assignment_status": "In Progress",
    "overall_completion_percentage": 75.00,
    "overall_total_required_points": 4,
    "overall_reported_points_count": 3,
    "all_requirements_met": false,
    "form_statuses": [
        {
            "form_id": 1,
            "form_name": "Emissions",
            "is_marked_complete": true,
            "is_actually_complete": true,
            "total_required_points": 1,
            "reported_points_count": 1
        },
        {
            "form_id": 2,
            "form_name": "Resource Use",
            "is_marked_complete": false,
            "is_actually_complete": false,
            "total_required_points": 3,
            "reported_points_count": 2
        }
    ]
}
```

##### Get Submission *Inputs* for a Template Assignment
(Request remains the same. Response is a list of `ESGMetricSubmission` inputs, as before, but no longer includes `reported_value_id`).

##### Verify a Metric Submission *Input* (Baker Tilly Admin only)
(Request/Response remains the same, clarifies it verifies the *input*).

#### 5. ESG Metric Evidence
(Requests/Responses remain largely the same, context clarified to link evidence to *inputs*).

## ESG Data Models (Updated Summary)

### `ReportedMetricValue` (Updated)
Stores the **parent aggregation record** for a specific input metric context.

Properties:
- `assignment`: Link to TemplateAssignment
- `metric`: Link to the *input* ESGMetric being aggregated
- `layer`: Link to LayerProfile (context for aggregation)
- `reporting_period`: Date identifying the specific period this aggregation covers
- `aggregated_numeric_value`: Stores the final aggregated value for **single-value numeric** metrics.
- `aggregated_text_value`: Stores the final aggregated value for **single-value text** metrics.
- `calculated_at`: Timestamp when this record was first created by aggregation.
- `last_updated_at`: Timestamp when this record (or its fields/children) were last updated by aggregation.
- `source_submission_count`: Total number of source `ESGMetricSubmission` inputs contributing to this aggregation.
- `first_submission_at`: Timestamp of the earliest source input.
- `last_submission_at`: Timestamp of the latest source input.

### `ESGMetricSubmission` (Updated)
Represents a **raw input data point**.

Properties:
- `assignment`: Link to TemplateAssignment
- `metric`: Link to ESGMetric
- `value`: Raw numeric value (for single-value numeric inputs)
- `text_value`: Raw text value (for single-value text inputs)
- `reporting_period`: Date for time-based inputs
- `submitted_by`, `submitted_at`, `updated_at`, `notes`
- `is_verified`, `verified_by`, `verified_at`, `verification_notes`: Verification status of this *raw input*.
- `layer`: Link to LayerProfile for this input.
- `source_identifier`: (New) Optional text field to identify the source of the input (e.g., meter ID, filename). Indexed for filtering.
- `multi_values` (related name): Links to `MetricValue` records for multi-value inputs.

### `MetricValue`
Stores the **individual input value for a specific field** within a multi-value `ESGMetricSubmission`.

Properties:
- `submission`: Link back to the `ESGMetricSubmission` input record.
- `field`: Link to the `MetricValueField` definition.
- `numeric_value`, `text_value`: The raw input value provided by the user for this field.

### `ESGMetricEvidence`
Stores supporting documentation for ESG metric submissions.

Properties:
- `submission`: Link to ESGMetricSubmission
- `file`: Uploaded file
- `filename`: Original filename
- `file_type`: MIME type of the file
- `uploaded_by`: User who uploaded the file
- `uploaded_at`: Upload timestamp
- `description`: Description of the evidence

## Enterprise-Grade Consolidated Endpoints

For optimal performance and user experience in enterprise settings, we recommend implementing consolidated endpoints that combine related data in a single request. This is particularly valuable for Baker Tilly admins who need to review template submissions.

### Recommended Consolidated Endpoint

```
GET /api/admin/template-submissions/{assignment_id}/
```

This endpoint would return a complete view including:
- Template structure with forms and categories
- All metric submissions with values (including `multi_values` data)
- Evidence files for each submission
- Verification status information

**Benefits:**
1. Reduces network overhead with a single request instead of multiple API calls
2. Ensures data consistency (all data from the same point in time)
3. Improves performance for admin review workflows
4. Follows enterprise best practices for complex data retrieval

**Sample Response:**
```json
{
  "assignment_id": 1,
  "template_id": 1,
  "template_name": "Environmental Assessment 2024",
  "layer_id": 3,
  "layer_name": "Example Corp",
  "status": "IN_PROGRESS",
  "due_date": "2024-12-31",
  "reporting_year": 2025,
  "forms": [
    {
      "form_id": 1,
      "form_code": "HKEX-A1",
      "form_name": "Environmental - Emissions",
      "category": {
        "id": 1,
        "name": "Environmental",
        "code": "environmental"
      },
      "metrics": [
        {
          "id": 1,
          "name": "Greenhouse gas emissions",
          "unit_type": "tCO2e",
          "location": "HK",
          "submission": {
            "id": 1,
            "value": 120.5,
            "submitted_by": "john.doe@example.com",
            "submitted_at": "2024-04-15T10:30:00Z",
            "is_verified": false,
            "evidence": [
              {
                "id": 1,
                "filename": "emissions_report.pdf",
                "uploaded_at": "2024-04-15T10:35:00Z"
              }
            ]
          }
        }
      ]
    }
  ]
}
```

### Implementation Considerations
- Include pagination for large datasets
- Support filtering by form or category
- Add caching mechanisms where appropriate
- Consider combining with GraphQL for more flexible data querying

This approach consolidates what would otherwise require multiple separate API calls:
1. `GET /api/user-templates/{assignment_id}/`
2. `GET /api/metric-submissions/by_assignment/?assignment_id={assignment_id}`
3. Multiple calls to `GET /api/metric-evidence/by_submission/?submission_id={submission_id}`

## Submission Workflow

1. **View Assigned Templates**: Users view templates assigned to their company using `/api/user-templates/`
2. **View Template Details**: Users get detailed information about a specific template using `/api/user-templates/{assignment_id}/`
3. **Submit Metric Values**: Users submit values for metrics using `/api/metric-submissions/` or `/api/metric-submissions/batch_submit/`. For multi-value metrics, they provide data in the `multi_values` dictionary.
4. **Upload Evidence**: Users upload supporting documentation using `/api/metric-evidence/`
5. **Complete Forms**: Users mark forms as completed using `/api/esg-forms/{form_id}/complete_form/` when all required metrics are filled
6. **Check Completion Status**: Users check the completion status of the template using `/api/templates/{template_id}/completion_status/`
7. **Submit Template**: Users submit the completed template using `/api/metric-submissions/submit_template/` when all forms are completed
8. **Verification**: Baker Tilly admins verify submissions using `/api/metric-submissions/{id}/verify/`

## Best Practices

1. **Metric Organization**:
   - Keep related metrics together using order field
   - Group location-specific metrics sequentially
   - Use clear, consistent naming conventions
   - For multi-value metrics, define clear `field_key`s and `display_name`s for each `MetricValueField`.

2. **Evidence Requirements**:
   - Set `requires_evidence=True` for critical metrics
   - Ensure evidence requirements align with HKEX guidelines

3. **Template Creation**:
   - Group related forms together
   - Consider company operations when selecting forms
   - Set realistic due dates

4. **Data Collection**:
   - Collect data separately for each location
   - Maintain consistent units across periods
   - Include supporting evidence as required
   - For multi-value metrics, ensure all required fields are submitted.

## Admin Interface

Access the admin interface at `/admin/` to manage:
- ESG Form Categories
- ESG Forms
- **Base ESG Metrics (and subclasses)** - View/Edit polymorphic metrics.
- Templates
- Template Assignments
- **ESG Metric Submissions (Headers)** - View common metadata, links to evidence.
- **Specific Submission Data Models** (`BasicMetricData`, `TabularMetricRow`, etc.) - View raw submitted values (possibly via inlines on Submission admin).
- **Reported Metric Values** - View final aggregated values for different levels ('M', 'A').
- ESG Metric Evidence

**(Removed:** `ESGMetric`, `MetricValueField`, `MetricValue`, `ReportedMetricFieldValue` from admin list).**

### Time-Based Metrics Validation

For metrics that require time-based reporting (e.g., monthly electricity consumption), the API expects multiple submissions based on the reporting frequency:

- Monthly metrics: 12 submissions (one for each month)
- Quarterly metrics: 4 submissions (one for each quarter)
- Annual metrics: 1 submission

The `check_completion` endpoint provides detailed information about time-based metrics completion status:

```
GET /api/esg-forms/{form_id}/check_completion/?assignment_id={id}
```

**Response Example (with time-based metrics):**
```json
{
  "form_id": 12,
  "form_name": "Environmental Impacts",
  "form_code": "HKEX-A1",
  "is_completed": false,
  "completion_percentage": 60,
  "total_required_metrics": 8,
  "total_submitted_metrics": 5,
  "missing_regular_metrics": [
    {
      "id": 45,
      "name": "Water consumption",
      "location": "HK"
    }
  ],
  "incomplete_time_based_metrics": [
    {
      "id": 52,
      "name": "Electricity consumption",
      "location": "ALL",
      "reporting_frequency": "monthly",
      "submitted_count": 5,
      "required_count": 12
    }
  ],
  "can_complete": false
}
```

The form can only be completed when:
1. All regular metrics have at least one submission
2. All time-based metrics have the required number of submissions based on their reporting frequency

When attempting to complete a form with incomplete time-based metrics, the API will return:

```json
{
  "error": "Cannot complete form with incomplete time-based metrics",
  "incomplete_time_based_metrics": [
    {
      "id": 52,
      "name": "Electricity consumption",
      "reporting_frequency": "monthly",
      "submitted_count": 5,
      "required_count": 12
    }
  ]
}
```

### Form Completion Status Validation

The form completion status API has been enhanced to handle various scenarios, including cases where requirements change after a form has been completed.

#### Enhanced Completion Status Check

```
GET /api/esg-forms/{form_id}/check_completion/?assignment_id={id}
```

The `check_completion` endpoint now performs validation even for forms that are already marked as completed. The response includes:

- `is_completed`: Whether the form is officially marked as completed in the database
- `is_actually_complete`: Whether the form meets all current completion requirements
- `status_inconsistent`: Flag indicating if the form is marked as complete but doesn't meet current requirements

This approach ensures that when requirements change (e.g., new metrics are added or time-based validation is enabled), the system can detect and report the inconsistency.

**Example Response (Inconsistent Status):**
```json
{
  "form_id": 12,
  "form_name": "Environmental Impacts",
  "form_code": "HKEX-A1",
  "is_completed": true,
  "is_actually_complete": false,
  "status_inconsistent": true,
  "completed_at": "2024-04-01T10:30:00Z",
  "completed_by": "john.doe@example.com",
  "completion_percentage": 75,
  "total_required_metrics": 8,
  "total_submitted_metrics": 6,
  "missing_final_reported_values": [
    {"metric_id": 45, "metric_name": "Water consumption", "location": "HK", "expected_periods_count": 1, "found_periods_count": 0, "missing_periods": ["2024-12-31"]}
  ],
  "incomplete_time_based_metrics": [],
  "can_complete": false
}
```

#### Revalidating Completed Forms

If a form needs to be revalidated due to new requirements, you can use the `complete_form` endpoint with the `revalidate` parameter:

```
POST /api/esg-forms/{form_id}/complete_form/
{
  "assignment_id": 123,
  "revalidate": true
}
```

This will:
1. Check if the form meets all current requirements
2. Update the completion status if requirements are met
3. Return a response indicating if the form was revalidated

**Example Response (Revalidation):**
```json
{
  "message": "Form successfully revalidated",
  "form_id": 12,
  "form_name": "Environmental Impacts",
  "form_code": "HKEX-A1",
  "evidence_attached": 2,
  "all_forms_completed": true,
  "assignment_status": "SUBMITTED",
  "was_revalidated": true
}
```

This approach maintains data integrity while providing a clear way to handle changes in validation requirements over time.

## Uncompleting Forms (Admin Only)

Administrators can mark previously completed forms as incomplete using the `uncomplete_form` API endpoint. This is useful when:

1. A form was accidentally marked as complete
2. Requirements have changed and forms need to be reopened for additional submissions
3. A form needs to be audited or revised

### API Endpoint

```
POST /api/esg-forms/{form_id}/uncomplete_form/
```

Request body:
```json
{
  "assignment_id": 123
}
```

Response:
```json
{
  "message": "Form successfully marked as incomplete",
  "form_id": 45,
  "form_name": "Carbon Emissions",
  "form_code": "HKEX-A1",
  "assignment_status": "IN_PROGRESS"
}
```

### Effects of Uncompleting a Form

When a form is marked as incomplete:

1. The form's `is_completed` flag is set to `false`
2. The `completed_at` and `completed_by` fields are cleared
3. If the assignment was in "SUBMITTED" status, it will be changed to "IN_PROGRESS"
4. The `completed_at` field on the assignment will be cleared

**Note:** This operation does not affect any existing metric submissions. All submitted data remains intact.

### Permissions

Only Baker Tilly administrators can use this endpoint.