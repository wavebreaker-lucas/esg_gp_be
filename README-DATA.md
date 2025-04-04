# ESG Data Management System

## Overview

The ESG Data Management System is designed to handle ESG (Environmental, Social, and Governance) reporting requirements, with a specific focus on HKEX ESG reporting guidelines. The system uses a hierarchical structure of Categories, Forms, and Metrics to organize and collect ESG data.

**Key Architectural Change (Approach B):** The system now distinguishes between raw data *inputs* (`ESGMetricSubmission`) and final *reported values* (`ReportedMetricValue`). For certain metrics, raw inputs are automatically aggregated to calculate the final value stored in `ReportedMetricValue`. This provides a clearer separation between data entry and the final figures used for reporting.

## Layer Support

(This section remains largely the same, as layer support applies to both inputs and reported values)

The system now includes comprehensive layer-based data segregation, allowing ESG data to be associated with specific organizational layers:

### Layer Integration for Submissions, Evidence, and Reported Values
- Each ESG metric *input* (`ESGMetricSubmission`) can be assigned to a specific layer.
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

**Note:** This endpoint operates on the raw *input* data (`ESGMetricSubmission`) and provides a sum of those inputs per layer. It is distinct from the final, potentially calculated values stored in `ReportedMetricValue`.

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
When creating submission *inputs*, the layer can be specified explicitly or will default according to the fallback mechanism:
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
When submitting multiple metric *inputs* at once, a default layer can be specified for all inputs, with individual layer overrides. You can also provide an optional `source_identifier` for each input.
```json
POST /api/metric-submissions/batch_submit/
{
  "assignment_id": 1,
  "default_layer_id": 3, // Default layer for inputs in this batch
  "submissions": [
    {
      "metric_id": 5,
      "value": 1234.56, // Will use default_layer_id 3
      "source_identifier": "Meter A" // Optional source
    },
    {
      "metric_id": 6,
      "value": 789.01,
      "layer_id": 4,  // Overrides default_layer_id for this specific input
      "source_identifier": "Meter B"
    },
    {
        "metric_id": 7,
        "value": 100,
        // No source_identifier provided for this one
    }
  ]
}
```

## Data Model: Inputs vs. Reported Values

A core change in the system is the separation of raw data inputs from the final values used for reporting.

- **`ESGMetricSubmission`**: Represents a single, raw data point entered by a user for a specific metric, period, and layer. Includes an optional `source_identifier` field to label the origin of the input (e.g., 'Meter A', 'Invoice #123'). Multiple inputs can exist for the same metric/period/layer combination, distinguished by their `source_identifier` or lack thereof. Verification (`is_verified` flag) applies to *this specific input*.
- **`ReportedMetricValue`**: Represents the **parent aggregation record** for a metric for a given assignment, layer, and reporting period. It stores metadata about the aggregation (e.g., number of source inputs, first/last submission time).
    - For **single-value** metrics (where `ESGMetric.is_multi_value` is `False`), the aggregated result (e.g., sum or latest value of *all* relevant `ESGMetricSubmission` inputs, regardless of `source_identifier`) is stored directly on this record in the `aggregated_numeric_value` or `aggregated_text_value` fields.
    - For **multi-value** metrics, this record acts as a container, and the aggregated results for each field are stored in child `ReportedMetricFieldValue` records.
    - This is the value intended for final reports and dashboards. *Note: Verification is currently only applied to raw inputs (`ESGMetricSubmission`), not this final aggregated record.*
- **`ReportedMetricFieldValue`** (New): Represents the **aggregated result for a specific field** within a multi-value metric. It links back to the parent `ReportedMetricValue` and the specific `MetricValueField` definition. It stores the aggregated numeric or text value for that field, the aggregation method used, and the count of source inputs contributing to that field's value.

This separation allows for:
- Tracking individual contributions or data points, including their source.
- Implementing complex aggregation logic for both single and multi-value metrics.
- Independent verification of raw inputs.
- Clearer distinction between data entry and final reporting views.

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

### 3. ESG Metrics
Metrics are the actual data points collected for each form.

Properties:
- `form`: Link to ESG Form
- `name`: Name of the metric
- `description`: Detailed explanation
- `unit_type`: Type of measurement
  - Environmental: 'kWh', 'MWh', 'm3', 'tonnes', 'tCO2e'
  - Social: 'person', 'hours', 'days', 'count', 'percentage'
  - Custom: 'custom' (with custom_unit field)
- `custom_unit`: For custom unit types
- `requires_evidence`: Whether supporting documentation is required
- `order`: Display sequence within form
- `location`: Where this metric applies
  - 'HK': Hong Kong operations
  - 'PRC': Mainland China operations
  - 'ALL': All locations
- `is_required`: Whether this metric must be reported
- `requires_time_reporting`: Whether this metric requires reporting for multiple time periods
- `reporting_frequency`: Required frequency of reporting (monthly, quarterly, annual)
- `is_multi_value`: Boolean indicating if this metric requires multiple related values (e.g., components of a calculation). Defaults to `false`.
- **`aggregates_inputs`**: (New) Boolean. If `True`, the final value for this metric (`ReportedMetricValue`) is calculated by aggregating multiple `ESGMetricSubmission` inputs. If `False`, the final value is typically taken directly from a single input.

### 4. Multi-Value Metrics (Input vs. Aggregated Structure)

For complex ESG indicators that require multiple related fields, the system distinguishes between the *input structure* and the *aggregated result storage*:

**Input Structure:**

- **Activation**: Set `is_multi_value=True` on the `ESGMetric` model.
- **Structure Definition**: Define the individual components using the `MetricValueField` model.
- **Data Submission**: When creating an `ESGMetricSubmission` *input* for a multi-value metric, the individual field values provided by the user are stored using the `MetricValue` model, linked to that single `ESGMetricSubmission` input record.

#### MetricValueField
Defines the structure of each component within a multi-value metric.

Properties:
- `metric`: Foreign key to the parent `ESGMetric` (must have `is_multi_value=True`).
- `field_key`: Unique identifier for this field within the metric (e.g., "products_sold").
- `display_name`: User-friendly name (e.g., "Total Products Sold").
- `description`: Optional description.
- `column_header`: Optional header for tabular display (e.g., "A", "B").
- `display_type`: Input type ('TEXT', 'NUMBER', 'SELECT').
- `order`: Display order of this field.
- `options`: JSON for dropdown choices if `display_type` is 'SELECT'.
- `is_required`: Whether this specific field must be filled *when submitting an input*.

#### MetricValue
Stores the actual submitted value for a specific field within a single multi-value `ESGMetricSubmission` *input*.

Properties:
- `submission`: Foreign key to the parent `ESGMetricSubmission`.
- `field`: Foreign key to the `MetricValueField` definition.
- `numeric_value`: Stores float values (if the field is numeric).
- `text_value`: Stores string values (if the field is text or select).

**Aggregated Result Storage:**

- **`ReportedMetricValue`**: The parent record created by the aggregation service for the overall metric context (assignment, metric, layer, period). Holds metadata like `source_submission_count`.
- **`ReportedMetricFieldValue`**: Child records linked to the parent `ReportedMetricValue`. Each child stores the aggregated result (e.g., sum of `MetricValue.numeric_value` across multiple inputs) for one specific `MetricValueField`.

**Example**: A "Waste Disposal" metric (`is_multi_value=True`, `aggregates_inputs=True`) might track different waste types per disposal event.
- *Input Definition*: `MetricValueField`s defined: `field_key="general_waste_kg"`, `field_key="recyclable_waste_kg"`.
- *User Input*: A user creates one `ESGMetricSubmission` input for Jan 1st, linking two `MetricValue` records (10kg general, 5kg recyclable). Another input for Jan 15th links two more `MetricValue` records (8kg general, 6kg recyclable).
- *Aggregation*: The `calculate_report_value` service runs.
    - It creates one parent `ReportedMetricValue` for January.
    - It creates two child `ReportedMetricFieldValue` records linked to the parent:
        - One for `field_key="general_waste_kg"` with `aggregated_numeric_value = 18`.
        - One for `field_key="recyclable_waste_kg"` with `aggregated_numeric_value = 11`.

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
- `POST /api/esg-metrics/`: Create custom metric
- `POST /api/esg-forms/{id}/add_metric/`: Add metric to existing form
- `POST /api/metric-value-fields/`: Create a field definition for a multi-value metric (Requires metric ID)
- `PUT /api/metric-value-fields/{id}/`: Update a multi-value field definition

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
- `company`: Link to Company (LayerProfile)
- `assigned_to`: User responsible for reporting
- `due_date`: Submission deadline
- `status`: Current status (PENDING, IN_PROGRESS, SUBMITTED, VERIFIED, REJECTED)
- `reporting_period_start`: Start of reporting period (deprecated, use reporting_year instead)
- `reporting_period_end`: End of reporting period (deprecated, use reporting_year instead)
- `reporting_year`: The specific year for which data is being reported (added in 2025)
- `completed_at`: When the template was submitted

### User Template Management

#### GET /api/user-templates/
Returns all template assignments accessible to the authenticated user, including templates assigned to their direct layer and parent layers.

**Response Example:**
```json
[
  {
    "id": 1,
    "template": {
      "id": 1,
      "name": "Environmental Assessment 2024"
    },
    "layer": {
      "id": 3,
      "name": "Example Corp"
    },
    "status": "PENDING",
    "due_date": "2024-12-31",
    "reporting_period_start": "2024-01-01",
    "reporting_period_end": "2024-12-31",
    "reporting_year": 2025,
    "relationship": "direct"
  },
  {
    "id": 2,
    "template": {
      "id": 2,
      "name": "Governance Disclosure 2024"
    },
    "layer": {
      "id": 1,
      "name": "Parent Group"
    },
    "status": "PENDING",
    "due_date": "2024-12-31",
    "reporting_period_start": "2024-01-01",
    "reporting_period_end": "2024-12-31",
    "reporting_year": 2025,
    "relationship": "inherited"
  }
]
```

**Key Features:**
- Automatically finds templates assigned to the user's layer and all parent layers
- No parameters required - uses the authenticated user's context
- Includes "relationship" field to indicate if the template is directly assigned to the user's layer or inherited from a parent
- Provides essential template information including status and due dates

#### GET /api/user-templates/{assignment_id}/
Returns detailed information about a specific template assignment, including all forms and metrics.

**Response Example:**
```json
{
  "assignment_id": 1,
  "template_id": 1,
  "template_name": "Environmental Assessment 2024",
  "layer_id": 3,
  "layer_name": "Example Corp",
  "status": "PENDING",
  "due_date": "2024-12-31",
  "reporting_period_start": "2024-01-01",
  "reporting_period_end": "2024-12-31",
  "reporting_year": 2025,
  "forms": [
    {
      "form_id": 1,
      "form_code": "HKEX-A1",
      "form_name": "Environmental - Emissions",
      "regions": ["HK", "PRC"],
      "category": {
        "id": 1,
        "name": "Environmental",
        "code": "environmental",
        "icon": "leaf",
        "order": 1
      },
      "order": 1,
      "metrics": [
        {
          "id": 1,
          "name": "Greenhouse gas emissions",
          "unit_type": "tCO2e",
          "custom_unit": null,
          "requires_evidence": true,
          "validation_rules": {"min": 0},
          "location": "HK",
          "is_required": true,
          "order": 1,
          "requires_time_reporting": false,
          "reporting_frequency": null,
          "is_multi_value": false
        },
        {
          "id": 5,
          "name": "Electricity consumption (CLP)",
          "unit_type": "kWh",
          "custom_unit": null,
          "requires_evidence": true,
          "validation_rules": {"min": 0},
          "location": "HK",
          "is_required": true,
          "order": 2,
          "requires_time_reporting": true,
          "reporting_frequency": "monthly",
          "is_multi_value": false
        },
        {
          "id": 8,
          "name": "Packaging material - Paper",
          "unit_type": "tonnes",
          "custom_unit": null,
          "requires_evidence": true,
          "validation_rules": {"min": 0},
          "location": "HK",
          "is_required": false,
          "order": 3,
          "requires_time_reporting": true,
          "reporting_frequency": "monthly",
          "is_multi_value": false
        }
      ]
    }
  ]
}
```

**Important Notes:**
- Returns complete form and metric details for the template
- Only includes metrics relevant to the selected regions
- Provides validation rules and requirements for each metric
- **Includes category information for each form**, allowing frontend to group forms by category
- Each form includes its `order` value for proper sequencing within its category
- Requires appropriate permissions to access

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

The system supports time-based reporting for metrics that require data for multiple periods.

1.  **Configuring Time-Based Metrics**:
    - Set `requires_time_reporting=True`
    - Set `reporting_frequency`

2.  **Submitting Time-Based *Inputs***:
    - When creating `ESGMetricSubmission` *inputs* for time-based metrics, include a `reporting_period` date corresponding to the input's period (e.g., end of month for monthly).
    - Multiple *input* records will typically be created over the reporting year.

3.  **Aggregation**:
    - For metrics where `aggregates_inputs=True`, the `calculate_report_value` service uses the `reporting_period` of the inputs to calculate the final `ReportedMetricValue` (and child `ReportedMetricFieldValue` records if multi-value) for the relevant period(s).
    - The specific aggregation method (e.g., SUM, LAST) depends on the metric type (single/multi-value) and field type (numeric/text).

4.  **Usage Example (Submitting Inputs)**:
    ```json
    // Submit multiple monthly INPUTS for electricity consumption
    POST /api/metric-submissions/batch_submit/
    {
        "assignment_id": 1,
        "submissions": [
            { "metric_id": 5, "value": 120.5, "reporting_period": "2024-01-31", ... },
            { "metric_id": 5, "value": 115.2, "reporting_period": "2024-02-29", ... },
            { "metric_id": 5, "value": 130.8, "reporting_period": "2024-03-31", ... }
            // ... more monthly inputs
        ]
    }
    ```
    - Submitting these inputs automatically triggers the aggregation service to update the relevant `ReportedMetricValue`(s).

5.  **Validation Rules (Inputs)**:
    - `ESGMetricSubmission` *inputs* no longer have a uniqueness constraint on `assignment`, `metric`, `reporting_period`. Multiple inputs are allowed.
    - `reporting_period` is generally required for inputs to metrics where `requires_time_reporting=True`.

6.  **Frontend Implementation**:
    - Guide users to submit *inputs* according to the `reporting_frequency` (e.g., monthly inputs).
    - Display final aggregated values separately, likely fetched from the `/api/reported-metric-values/` endpoint.

## Aggregation Service (`calculate_report_value`)

For metrics marked with `aggregates_inputs=True`, the `calculate_report_value` service automatically calculates and updates the final aggregated values.

- **Trigger**: This service is triggered whenever an `ESGMetricSubmission` *input* is created, updated, or deleted for a metric where `aggregates_inputs=True`.
- **Context**: The calculation requires the `assignment`, `input_metric`, `reporting_period`, and `layer` to identify the correct set of inputs and the target aggregation records.
- **Logic**:
    - Finds or creates a parent `ReportedMetricValue` record for the context, updating metadata (submission counts, timestamps).
    - **Single-Value Metrics**: Aggregates `ESGMetricSubmission.value` (default: SUM for numeric types) or `ESGMetricSubmission.text_value` (default: LAST submission) and stores the result directly in the parent `ReportedMetricValue`'s `aggregated_numeric_value` or `aggregated_text_value` fields.
    - **Multi-Value Metrics**: Iterates through each `MetricValueField` defined for the input metric. For each field, it aggregates the corresponding `MetricValue` records from the source inputs (default: SUM for numeric, LAST for text/select) and updates or creates a child `ReportedMetricFieldValue` record.
    - Handles cleanup of orphaned aggregation records if inputs are deleted or metric configuration changes.
- **Result**: Creates or updates the parent `ReportedMetricValue` and any necessary child `ReportedMetricFieldValue` records.

## API Endpoints

### ESG Data Management

#### ESG Data Endpoints (Legacy - Review if still needed)
- `GET /api/esg-data/?company_id={id}`: Get ESG data entries for a company
- `POST /api/esg-data/`: Create new ESG data entry
- `PUT /api/esg-data/{data_id}/`: Update ESG data entry
- `POST /api/esg-data/{data_id}/verify/`: Verify ESG data entry (Baker Tilly admin only)
**(Note: These endpoints seem related to an older model `ESGData`. Review if this model and its endpoints are still relevant alongside the Template/Submission/ReportedValue system).**

#### ESG Metric Submission *Input* Endpoints (`/api/metric-submissions/`)
Manages the **raw input data points** (`ESGMetricSubmission` model).
- `GET /api/metric-submissions/`: List accessible submission *inputs*.
- `POST /api/metric-submissions/`: Submit a single metric *input*. Triggers aggregation if `metric.aggregates_inputs` is true.
- `GET /api/metric-submissions/{id}/`: Get details of a specific submission *input*. Includes `multi_values`.
- `PUT /api/metric-submissions/{id}/`: Update a metric *input*. Triggers aggregation if `metric.aggregates_inputs` is true.
- `DELETE /api/metric-submissions/{id}/`: Delete a metric *input*. Triggers aggregation if `metric.aggregates_inputs` is true.
- `GET /api/metric-submissions/by_assignment/?assignment_id={id}`: Get all submission *inputs* for an assignment. Supports filtering (e.g., by `form_id`, `metric_id`, `layer_id`, `is_verified`).
- `POST /api/metric-submissions/batch_submit/`: Submit multiple metric *inputs* at once. Triggers aggregation for relevant metrics. Use the `multi_values` dictionary within each submission object for multi-value metrics.
- `POST /api/metric-submissions/submit_template/`: Mark a template assignment as submitted. **Checks for the existence of required `ReportedMetricValue` records**, not just inputs.
- `POST /api/metric-submissions/{id}/verify/`: Verify a *specific raw input* (`ESGMetricSubmission`). Does **not** verify the final aggregated value. (Baker Tilly admin only).
- `GET /api/submissions/available-layers/`: Get layers accessible to the user.
- `GET /api/submissions/sum-by-layer/`: Aggregate *raw inputs* (`ESGMetricSubmission`) by layer. Distinct from viewing final aggregated values.

#### Reported Metric Value Endpoints (`/api/reported-metric-values/`) (New)
Provides **read-only access** to the final, calculated/official **aggregated metric records** (`ReportedMetricValue` and nested `ReportedMetricFieldValue` models).
- `GET /api/reported-metric-values/`: List accessible final aggregated records.
- **Filtering**: Supports filtering by `assignment`, `metric` (the input metric ID), `layer`, `reporting_period`.
- **Permissions**: Users only see values for layers they have access to or assignments assigned to them.
- **Response**: Includes the parent `ReportedMetricValue` details (metadata, single-value results if applicable) and nested `ReportedMetricFieldValue` details for multi-value metrics.

**Example Request:**
```
GET /api/reported-metric-values/?assignment=1&metric=5&layer=3&reporting_period=2024-12-31
```

**Example Response (Updated):**
```json
[
  {
    "id": 55, // ID of the parent ReportedMetricValue
    "assignment": 1,
    "metric": 5, // ID of the *input* ESGMetric
    "metric_name": "Annual Waste Disposal",
    "metric_unit": "tonnes", // Unit from the input ESGMetric
    "layer": 3,
    "layer_name": "Manufacturing Division",
    "reporting_period": "2024-12-31",
    // --- Single-value Results (Populated if input metric is NOT multi-value) ---
    "aggregated_numeric_value": null, // e.g., 14500.75 if single-value numeric
    "aggregated_text_value": null,
    // --- Calculation & Aggregation Metadata ---
    "calculated_at": "2025-01-10T10:00:00Z",
    "last_updated_at": "2025-01-15T11:30:00Z",
    "source_submission_count": 12, // Total count of source ESGMetricSubmission inputs
    "first_submission_at": "2024-01-15T09:00:00Z",
    "last_submission_at": "2024-12-10T14:00:00Z",
    // --- Nested fields for multi-value results (Populated if input metric IS multi-value) ---
    "aggregated_fields": [
        {
            "id": 101, // ID of ReportedMetricFieldValue
            "field": 10, // ID of the MetricValueField definition
            "field_key": "general_waste_kg",
            "field_display_name": "General Waste (kg)",
            "aggregated_numeric_value": 18050.5,
            "aggregated_text_value": null,
            "aggregation_method": "SUM",
            "source_submission_count": 12, // Submissions providing this field
            "last_updated_at": "2025-01-15T11:30:00Z"
        },
        {
            "id": 102,
            "field": 11,
            "field_key": "recyclable_waste_kg",
            "field_display_name": "Recyclable Waste (kg)",
            "aggregated_numeric_value": 5520.0,
            "aggregated_text_value": null,
            "aggregation_method": "SUM",
            "source_submission_count": 11,
            "last_updated_at": "2025-01-15T11:30:00Z"
        }
    ]
  }
]
```

#### ESG Metric Evidence Endpoints
- `GET /api/metric-evidence/`: List all accessible evidence files
- `POST /api/metric-evidence/`: Upload evidence for a metric submission
- `GET /api/metric-evidence/{id}/`: Get details of a specific evidence file
- `DELETE /api/metric-evidence/{id}/`: Delete an evidence file
- `GET /api/metric-evidence/by_submission/?submission_id={id}`: Get all evidence for a submission
- `GET /api/metric-evidence/batch/?submission_ids=1,2,3,4,5`: Get submission data and evidence for multiple submissions

### Form and Template Management

#### ESG Forms
- `GET /api/esg-forms/`: List active ESG forms
- `GET /api/esg-forms/{id}/`: Get specific form details
- `POST /api/esg-forms/`: Create new ESG form (Baker Tilly Admin only)
- `PUT /api/esg-forms/{id}/`: Update ESG form (Baker Tilly Admin only)
- `PATCH /api/esg-forms/{id}/`: Partially update ESG form (Baker Tilly Admin only)
- `DELETE /api/esg-forms/{id}/`: Delete ESG form (Baker Tilly Admin only)
- `GET /api/esg-forms/{id}/metrics/`: Get metrics for a specific form
- `POST /api/esg-forms/{id}/add_metric/`: Add a metric to a form (Baker Tilly Admin only)
- `GET /api/esg-forms/{id}/check_completion/?assignment_id={id}`: Check completion status of a specific form
- `POST /api/esg-forms/{id}/complete_form/`: Mark a form as completed

#### ESG Categories
- `GET /api/esg-categories/`: List all categories with their active forms
- `GET /api/esg-categories/{id}/`: Get specific category details
- `POST /api/esg-categories/`: Create new category (Baker Tilly Admin only)
- `PUT /api/esg-categories/{id}/`: Update category (Baker Tilly Admin only)
- `PATCH /api/esg-categories/{id}/`: Partially update category (Baker Tilly Admin only)
- `DELETE /api/esg-categories/{id}/`: Delete category (Baker Tilly Admin only)

#### ESG Metrics
- `GET /api/esg-metrics/`: List all metrics
- `GET /api/esg-metrics/?form_id={id}`: List metrics for a specific form
- `GET /api/esg-metrics/{id}/`: Get specific metric details
- `POST /api/esg-metrics/`: Create new metric (Baker Tilly Admin only)
- `PUT /api/esg-metrics/{id}/`: Update metric (Baker Tilly Admin only)
- `PATCH /api/esg-metrics/{id}/`: Partially update metric (Baker Tilly Admin only)
- `DELETE /api/esg-metrics/{id}/`: Delete metric (Baker Tilly Admin only)

#### Metric Value Fields (for Multi-Value Metrics)
- `GET /api/metric-value-fields/`: List all metric value field definitions
- `GET /api/metric-value-fields/?metric_id={id}`: List fields for a specific multi-value metric
- `GET /api/metric-value-fields/{id}/`: Get details of a specific field definition
- `POST /api/metric-value-fields/`: Create a new field definition (Baker Tilly Admin only)
- `PUT /api/metric-value-fields/{id}/`: Update a field definition (Baker Tilly Admin only)
- `PATCH /api/metric-value-fields/{id}/`: Partially update a field definition (Baker Tilly Admin only)
- `DELETE /api/metric-value-fields/{id}/`: Delete a field definition (Baker Tilly Admin only)

#### Templates (Baker Tilly Admin only)
- `GET /api/templates/`: List all templates
- `POST /api/templates/`: Create new template
- `GET /api/templates/{id}/`: Get template details
- `PUT /api/templates/{id}/`: Update template
- `DELETE /api/templates/{id}/`: Delete template
- `GET /api/templates/{id}/preview/`: Preview template with forms and metrics
- `GET /api/templates/{id}/completion_status/?assignment_id={id}`: Get completion status of all forms in a template

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

#### 1. ESG Data Management (Legacy - Review if needed)
(Keep as is for now, add note about potential deprecation)

#### 2. Template Management
(Remains the same)

#### 3. ESG Form and Metric Management
(Remains the same)

#### 4. ESG Metric Submissions (*Inputs* and Completion)

##### Submit a Single Metric *Input* Value
(Request/Response largely the same, removed `reported_value_id` from response)
```json
POST /api/metric-submissions/
{
    "assignment": 1,
    "metric": 5, // Assume aggregates_inputs=True, requires_time_reporting=True
    "value": 120.5,
    "reporting_period": "2024-03-31",
    "layer_id": 3,
    "notes": "Input value for March 2024 electricity bill"
}

// Response (Example - Updated)
{
    "id": 101, // ID of this specific input record
    "assignment": 1,
    "metric": 5,
    "metric_name": "Electricity consumption (CLP)",
    "metric_unit": "kWh",
    "value": 120.5,
    "text_value": null,
    "reporting_period": "2024-03-31",
    "submitted_by": 3,
    "submitted_by_name": "john.doe@example.com",
    "submitted_at": "...",
    "updated_at": "...",
    "notes": "Input value for March 2024 electricity bill",
    "is_verified": false, // Verification of this input
    "verified_by": null,
    // ... verification fields for input ...
    "layer_id": 3,
    "layer_name": "Manufacturing Division",
    "is_multi_value": false,
    "multi_values": [],
    "evidence": []
}
```

##### Batch Submit Multiple Metric *Input* Values
(Request remains the same. Response message clarified).
```json
POST /api/metric-submissions/batch_submit/
{ ... } // Same request structure

// Response (Example)
{
    // Updated message to clarify inputs
    "message": "Created 2 submission inputs. Aggregation triggered for relevant metrics.",
    "evidence_attached": 0, // If evidence was attached to inputs
    "assignment_status": "IN_PROGRESS" // Current status
}
```

##### Check Form Completion Status
(Request remains the same. Response description updated to reflect check against `ReportedMetricValue`).
```json
GET /api/esg-forms/{form_id}/check_completion/?assignment_id=1

// Response (Example reflecting new logic)
{
    "form_id": 2,
    "form_name": "Resource Use",
    "form_code": "HKEX-A2",
    "is_completed": false, // Based on ReportedMetricValue existence
    "completion_percentage": 75.0, // Based on ReportedMetricValue existence
    "total_required_metrics": 4,
    "reported_metric_count": 3, // Count of required metrics with a ReportedMetricValue
    "missing_final_reported_values": [ // List metrics lacking a final ReportedMetricValue
        {"id": 10, "name": "Wastewater consumption", "location": "HK", "expected_periods": ["2024-12-31"]} // Example detail
    ],
    "can_complete": false
}
```

##### Complete a Form
(Request remains the same. Response description updated).
```json
POST /api/esg-forms/{form_id}/complete_form/
{
    "assignment_id": 1
}

// Response (Success Example)
{
    "message": "Form successfully completed (all required reported values exist)",
    "form_id": 2,
    // ... other fields ...
    "assignment_status": "IN_PROGRESS" // Or SUBMITTED if this was the last form
}
// Response (Error Example)
{
    "error": "Cannot complete form. Final reported values are missing.",
    "missing_final_reported_values": [
         {"id": 10, "name": "Wastewater consumption", ... }
    ]
}

```

##### Submit a Template
(Request remains the same. Response description updated).
```json
POST /api/metric-submissions/submit_template/
{
    "assignment_id": 1
}

// Response (Success Example)
{
    "message": "Template successfully submitted (all required reported values exist)",
    "assignment_id": 1,
    "status": "SUBMITTED",
    "completed_at": "..."
}
// Response (Error Example)
{
    "status": "incomplete",
    "message": "Template is incomplete. Final reported values are missing.",
    "missing_final_values": [ // Details similar to check_completion missing values
         { ... }
    ]
}
```

##### Get Template Completion Status
(Request remains the same. Response description updated).
```json
GET /api/templates/{template_id}/completion_status/?assignment_id=1

// Response (Example reflecting new logic)
{
    "assignment_id": 1,
    // ... assignment details ...
    "overall_completion_percentage": 33.33, // Based on ReportedMetricValue existence
    "forms": [
        {
            "form_id": 1,
            "form_name": "Emissions",
            "form_code": "HKEX-A1",
            "is_completed": false,
            // ... completion details ...
            "reported_metric_count": 2, // Required metrics with ReportedMetricValue
            "completion_percentage": 50.0, // Based on ReportedMetricValue
            "missing_final_reported_values": [ // Metrics lacking ReportedMetricValue
                 {"id": 3, "name": "Indirect GHG emissions", ...}
            ]
        },
        {
            "form_id": 2,
            "form_name": "Resource Use",
            "is_completed": true,
             // ... completion details ...
           "reported_metric_count": 3,
           "completion_percentage": 100.0,
           "missing_final_reported_values": []
        },
       // ... other forms ...
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

### `ReportedMetricFieldValue` (New)
Stores the **aggregated value for a specific field** within a multi-value metric aggregation.

Properties:
- `reported_value`: Link to the parent `ReportedMetricValue` record.
- `field`: Link to the `MetricValueField` definition (from the input metric).
- `aggregated_numeric_value`: Stores the aggregated numeric value for this specific field.
- `aggregated_text_value`: Stores the aggregated text value for this specific field.
- `aggregation_method`: Method used for aggregation (e.g., 'SUM', 'LAST').
- `source_submission_count`: Number of source `ESGMetricSubmission` inputs contributing to *this specific field's* aggregation.
- `last_updated_at`: Timestamp when this field value was last updated.

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
- ESG Metrics (including defining multi-value fields via inlines)
- Metric Value Fields
- Metric Values (Values within raw inputs)
- Templates
- Template Assignments
- ESG Metric Submissions (Raw inputs, including viewing multi-values via inlines and the `source_identifier`)
- **Reported Metric Values** (Parent aggregation records, view metadata and single-value results)
- **Reported Metric Field Values** (Aggregated results for multi-value fields, linked to parent)
- ESG Metric Evidence (Linked to raw inputs)

Note: Access requires either superuser status or Baker Tilly admin privileges.

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
  "missing_regular_metrics": [
    {
      "id": 45,
      "name": "Water consumption",
      "location": "HK"
    }
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