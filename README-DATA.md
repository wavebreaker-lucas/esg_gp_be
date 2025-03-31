# ESG Data Management System

## Overview

The ESG Data Management System is designed to handle ESG (Environmental, Social, and Governance) reporting requirements, with a specific focus on HKEX ESG reporting guidelines. The system uses a JSON schema-based approach for flexible and structured data collection.

## Core Data Model

### ESGMetricSubmission

The central model for storing all metric data. It uses a JSON-based approach where all metric data is stored in a structured JSON object.

Key fields:
- `assignment`: Reference to the template assignment
- `metric`: Reference to the ESG metric being reported
- `data`: JSON field containing all metric data in a structured format
- `layer`: The organizational layer this submission applies to
- `batch_submission`: Optional reference to a batch submission
- `submission_identifier`: Optional identifier to distinguish multiple submissions for the same metric/layer
- `data_source`: Source of the data (e.g., 'Invoice', 'Meter Reading').
- Metadata fields: `submitted_by`, `submitted_at`, `is_verified`, etc.

### MetricSchemaRegistry

The `MetricSchemaRegistry` model defines standard JSON schemas for different types of metrics.

Key fields:
- `name`: Name of the schema (e.g., "Emissions", "Resource Consumption")
- `description`: Description of what the schema is used for
- `schema`: JSON Schema definition that defines the structure and validation rules
- `version`: Schema version for tracking changes
- Metadata fields: `created_by`, `created_at`, `is_active`, etc.

### ESGMetricBatchSubmission

The `ESGMetricBatchSubmission` model represents a group of related metric submissions submitted together. Submissions are linked to a batch via the `batch_submission` field on `ESGMetricSubmission`.

Key fields:
- `assignment`: Reference to the template assignment
- `name`: Optional name for the batch
- `layer`: The organizational layer this batch applies to
- `submissions`: Related submissions (reverse relation via `ESGMetricSubmission.batch_submission`)
- Metadata fields: `submitted_by`, `submitted_at`, `is_verified`, `verification_notes`, etc.

### ESGMetricEvidence

The `ESGMetricEvidence` model stores supporting documentation for ESG metric submissions.

Key fields:
- `submission`: Link to ESGMetricSubmission (can be null for standalone evidence)
- `file`: Uploaded evidence file
- `filename`, `file_type`: File metadata
- `layer`: The layer this evidence is associated with
- `submission_identifier`: Identifier to link evidence to a specific submission instance when multiple exist for the same metric/layer.
- `json_path`: General JSON path this evidence relates to within the submission's `data` (e.g., 'periods.Jan-2024').
- `reference_path`: Specific JSON path used primarily for OCR context (e.g., 'periods.Jan-2024').
- `intended_metric`: The metric this evidence is intended for (useful before linking to a specific submission).
- OCR-related fields: `enable_ocr_processing`, `is_processed_by_ocr`, `extracted_value`, `ocr_period`, `ocr_data`, `extracted_data`, `was_manually_edited`, `edited_at`, `edited_by`.
- Metadata fields: `uploaded_by`, `uploaded_at`, `description`.

## ESG Metric Structure

### JSON Schema Approach

Each metric in the system has an associated JSON schema that defines:
- The structure of valid data
- Validation rules for each field
- Required fields and constraints

The schema can be defined in two ways:
1. Directly on the metric through the `data_schema` field
2. Through reference to a standard schema in the `MetricSchemaRegistry`

### Schema Types

Metrics can reference a schema type through:
- Direct reference to a `schema_registry` (foreign key)
- String reference through the `schema_type` field (e.g., 'electricity_hk', 'electricity_prc') - *Note: Ensure `schema_type` is actively used in logic if relying on it.*

### Frontend Components

The `form_component` field on ESG metrics specifies which frontend component should be used to render the input form, allowing for specialized input interfaces for different data types.

## Units in JSON and Primary Measurements

The ESG Platform uses a units-in-JSON approach where each value in the JSON data has its own unit specification.

### Units Embedded in JSON

Every measurement in the JSON data should include its own unit:

```json
{
  "value": 1500,
  "unit": "kWh",
  "comments": "Monthly electricity consumption"
}
```

This approach allows for:
1. Self-contained data that carries its own unit information
2. Multiple values with different units in the same submission
3. Clearer data contracts between frontend and backend
4. Better support for exports/imports between systems

### Complex Metrics with Multiple Values

For metrics that track multiple related values, each can have its own unit:

```json
{
  "electricity": {
    "value": 1500,
    "unit": "kWh"
  },
  "gas": {
    "value": 350,
    "unit": "m³"
  },
  "water": {
    "value": 42000,
    "unit": "liters"
  },
  "comments": "Monthly utility consumption"
}
```

### Specifying Primary Measurements

For complex metrics with multiple values, the `primary_path` field on the `ESGMetric` model indicates which value within the `data` JSON is considered the "primary" one. This path points to the relevant value (e.g., `"electricity.value"` or `"annual_total"`).

```python
# Example ESGMetric field definition:
primary_path = models.CharField(
    max_length=255,
    null=True,
    blank=True,
    help_text="Path to the primary value in the JSON data (e.g., 'electricity.value')"
)
```

If the `ESGMetric.primary_path` is set, the system uses this path to identify the primary measurement. An optional `_metadata.primary_measurement` field within the JSON data itself can also be used as a fallback or alternative mechanism, but the model field is the primary configuration point.

Example JSON data structure (assuming `primary_path` on the metric is set to `"electricity.value"`):
```json
{
  "electricity": {
    "value": 1500,
    "unit": "kWh"
  },
  "gas": {
    "value": 350,
    "unit": "m³"
  }
  // No _metadata needed here if ESGMetric.primary_path is set
}
```

The primary measurement is used for:
1. UI highlighting (which value to emphasize in the interface)
2. Default aggregation (which value to use in calculations)
3. Legacy system compatibility (where a single value is expected)
4. Reporting purposes (which value to include in summaries)

## Time-Based Data

The system supports time-based reporting with periods embedded in the JSON structure:

### Time Periods in JSON

```json
{
  "periods": {
    "Jan-2024": {
      "value": 120.5,
      "unit": "kWh",
      "comments": "January consumption"
    },
    "Feb-2024": {
      "value": 115.2,
      "unit": "kWh",
      "comments": "February consumption"
    },
    "Mar-2024": {
      "value": 130.8,
      "unit": "kWh",
      "comments": "March consumption"
    }
  },
  "annual_total": 366.5,
  "annual_unit": "kWh",
  "_metadata": {
    "primary_measurement": "annual_total"
  }
}
```

This approach allows for:
- Flexible period naming (monthly, quarterly, custom periods)
- Period-specific metadata and comments
- Storage of aggregated values alongside period details

## Evidence Linking

Evidence files can be linked to specific parts of a JSON structure using the `json_path` field on the `ESGMetricEvidence` model.

For example, to link evidence to a specific period in an emissions submission:
```python
# ESGMetricEvidence instance
evidence.json_path = "periods.Jan-2024"
```

The `reference_path` field is also available, primarily intended for use with OCR to specify the target path for extracted data.

This allows for precise evidence linking to any level of the JSON structure, including:
- Linking a bill to a specific monthly period
- Attaching evidence to a particular measurement in a complex structure
- Providing documentation for specific data points within tabular data

The `submission_identifier` field can be used to link evidence to a specific instance of `ESGMetricSubmission` if multiple submissions exist for the same metric/assignment/layer combination.

## Data Validation

All submissions are validated against their schema at submission time, ensuring data integrity and consistency.

### Validation Process

1. When a submission is created or updated, the system checks for a valid JSON schema:
   - First, it looks for a schema in the metric's `schema_registry`
   - If not found, it checks the metric's `data_schema` field
   
2. If a schema is found, the data is validated against it using the jsonschema library
   - Type validation (numbers, strings, objects)
   - Required field validation
   - Enum validation (values must be from a predefined set)
   - Range validation (min/max values)
   - Pattern validation (regex matching)

3. If validation fails, the API returns detailed error messages indicating which parts of the submission failed validation

## Example JSON Schemas and Data

### Example 1: Emissions Schema

```json
{
  "type": "object",
  "properties": {
    "value": {
      "type": "number",
      "minimum": 0
    },
    "unit": {
      "type": "string",
      "enum": ["tCO2e", "kgCO2e"]
    },
    "scope": {
      "type": "string",
      "enum": ["Scope 1", "Scope 2", "Scope 3"]
    },
    "source": {
      "type": "string"
    },
    "calculation_method": {
      "type": "string",
      "enum": ["location-based", "market-based"]
    },
    "periods": {
      "type": "object",
      "additionalProperties": {
        "type": "object",
        "properties": {
          "value": {
            "type": "number",
            "minimum": 0
          },
          "notes": {
            "type": "string"
          }
        },
        "required": ["value"]
      }
    }
  },
  "required": ["value", "unit", "scope"]
}
```

### Example 1: Emissions Data

```json
{
  "value": 500,
  "unit": "tCO2e",
  "scope": "Scope 2",
  "source": "Electricity",
  "calculation_method": "location-based",
  "periods": {
    "Jan-2024": {"value": 42, "notes": "Lower due to office closure"},
    "Feb-2024": {"value": 45, "notes": "Normal operations"},
    "Mar-2024": {"value": 38, "notes": "Energy efficiency improvements"}
  }
}
```

### Example 2: Employee Training Schema

```json
{
  "type": "object",
  "properties": {
    "total_employees": {
      "type": "integer",
      "minimum": 0
    },
    "employees_trained": {
      "type": "integer",
      "minimum": 0
    },
    "total_hours": {
      "type": "number",
      "minimum": 0
    },
    "average_hours_per_employee": {
      "type": "number",
      "minimum": 0
    },
    "training_categories": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "category": {
            "type": "string"
          },
          "participants": {
            "type": "integer",
            "minimum": 0
          },
          "hours": {
            "type": "number",
            "minimum": 0
          }
        },
        "required": ["category", "participants", "hours"]
      }
    }
  },
  "required": ["total_employees", "employees_trained", "total_hours"]
}
```

### Example 2: Employee Training Data

```json
{
  "total_employees": 250,
  "employees_trained": 220,
  "total_hours": 1320,
  "average_hours_per_employee": 5.28,
  "training_categories": [
    {
      "category": "Health & Safety",
      "participants": 250,
      "hours": 500
    },
    {
      "category": "Environmental Awareness",
      "participants": 150,
      "hours": 300
    },
    {
      "category": "Anti-corruption",
      "participants": 220,
      "hours": 520
    }
  ]
}
```

### Example 3: Supplier Assessment Schema (Tabular Data)

```json
{
  "type": "object",
  "properties": {
    "suppliers": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "name": {
            "type": "string"
          },
          "assessment": {
            "type": "object",
            "properties": {
              "compliance_status": {
                "type": "string",
                "enum": ["Compliant", "Partially Compliant", "Non-Compliant"]
              },
              "score": {
                "type": "object",
                "properties": {
                  "value": {
                    "type": "number",
                    "minimum": 0,
                    "maximum": 100
                  },
                  "unit": {
                    "type": "string",
                    "enum": ["points", "percent"]
                  }
                },
                "required": ["value", "unit"]
              },
              "date": {
                "type": "string",
                "format": "date"
              }
            },
            "required": ["compliance_status", "score"]
          }
        },
        "required": ["name", "assessment"]
      }
    },
    "_metadata": {
      "type": "object",
      "properties": {
        "primary_measurement": {
          "type": "string"
        }
      }
    }
  },
  "required": ["suppliers"]
}
```

### Example 3: Supplier Assessment Data

```json
{
  "suppliers": [
    {
      "name": "Supplier A",
      "assessment": {
        "compliance_status": "Compliant",
        "score": {
          "value": 85,
          "unit": "points"
        },
        "date": "2023-05-12"
      }
    },
    {
      "name": "Supplier B",
      "assessment": {
        "compliance_status": "Partially Compliant",
        "score": {
          "value": 65,
          "unit": "points"
        },
        "date": "2023-06-15"
      }
    }
  ],
  "_metadata": {
    "primary_measurement": "suppliers.length"
  }
}
```

## API Endpoints

Note: Base URL for API endpoints is `/api/`.

### Schema Registry

```
GET /api/schemas/
POST /api/schemas/
GET /api/schemas/{id}/
PUT /api/schemas/{id}/
GET /api/schemas/schema_types/  # Custom action (verify implementation)
GET /api/schemas/{id}/metrics/  # Custom action (verify implementation)
```

The schema registry endpoints allow management of reusable JSON schemas that can be applied to multiple metrics. This promotes consistency and reduces duplication. Managed by `SchemaRegistryViewSet`.

### Individual Submissions

```
GET /api/metric-submissions/
POST /api/metric-submissions/
GET /api/metric-submissions/{id}/
PUT /api/metric-submissions/{id}/
DELETE /api/metric-submissions/{id}/

# Custom action for filtering by assignment
GET /api/metric-submissions/by_assignment/?assignment_id={id}&form_id={form_id}
```

These endpoints handle the submission, retrieval, updating, and deletion of individual metric submissions with their JSON data. Managed by `ESGMetricSubmissionViewSet`.

*Note on `POST /api/metric-submissions/`: Based on the `ESGMetricSubmissionCreateSerializer`, this endpoint typically performs an "update-or-create". If a submission already exists for the combination of `assignment`, `metric`, and `layer` (and `submission_identifier` if provided), the existing record will be updated instead of creating a new one, unless specific flags in a batch operation override this.*

**Filtering `by_assignment`:**
- Permissions: Admins see all; regular users see submissions for their assigned/accessible layers.
- Supports filtering by `form_id`, `is_verified`, date ranges (`submitted_after`, `submitted_before`).
- Supports sorting (`sort_by`, `sort_direction`) and pagination (`page`, `page_size`).

**Example Request:**
```
GET /api/metric-submissions/by_assignment/?assignment_id=5&form_id=2&is_verified=false&page=1&page_size=50&sort_by=submitted_at&sort_direction=desc
```

**Example Response (Paginated List using `ESGMetricSubmissionSerializer`):**
```json
{
  "count": 120, // Note: Field name might be 'count' or 'total_count'
  "next": "...",
  "previous": "...",
  "results": [
    {
      "id": 1,
      "assignment": 1,
      "metric": 5,
      "metric_name": "Electricity consumption (CLP)", // From serializer
      "metric_unit": "kWh", // Derived by serializer from data
      "data": { "value": 120.5, "unit": "kWh", "source": "Bill" }, // Actual data nested here
      "batch_id": null,
      "batch_submission": null,
      "submitted_by": 3,
      "submitted_by_name": "john.doe@example.com",
      "submitted_at": "2024-04-15T10:30:00Z",
      "updated_at": "2024-04-15T10:32:00Z",
      "notes": "From March bill",
      "is_verified": false,
      "verified_by": null,
      "verified_by_name": null,
      "verified_at": null,
      "verification_notes": "",
      "layer_id": 3,
      "layer_name": "Example Corp",
      "submission_identifier": "march_clp",
      "data_source": "Bill",
      "evidence": [ // Nested evidence details (using ESGMetricEvidenceSerializer)
          {
              "id": 10,
              "file": "/media/esg_evidence/2024/04/march_clp_bill.pdf",
              "filename": "march_clp_bill.pdf",
              // ... other evidence fields ...
          }
      ]
    }
    // ... more submissions
  ]
}
```

### Batch Submissions

```
POST /api/batch-submissions/submit_batch/
GET /api/batch-submissions/{id}/
GET /api/batch-submissions/{id}/submissions/
```

Batch submission endpoints allow multiple metrics to be submitted together in a single transaction, with all submissions sharing the same metadata (layer, timestamps, etc.).

## Layer Support

The system includes comprehensive layer-based data segregation, allowing ESG data to be associated with specific organizational layers (subsidiaries, branches, etc.):

- Each ESG metric submission can be assigned to a specific layer
- Evidence files can be tagged with layer information
- Default layer settings provide fallback when no layer is specified

Layer-based functionality is integrated with the JSON schema approach, allowing you to:
- Filter submissions by layer
- Aggregate data across multiple layers
- Generate layer-specific reports

## Performance Considerations

The JSON schema approach offers flexibility but requires attention to performance:

- PostgreSQL GIN indexes are used for efficient querying of JSON data
- For complex queries, use PostgreSQL JSON path operators
- Add specific database indexes for frequently queried JSON paths
- Be mindful of deeply nested JSON structures, which can impact query performance

## OCR and Data Extraction

The system supports OCR-based data extraction from evidence files, which can populate the JSON data structure:

- OCR results are stored in the `extracted_data` field of the evidence model
- Extracted data can be linked to specific parts of the JSON structure via the `reference_path`
- The `was_manually_edited` flag tracks whether OCR results were adjusted by users

## Migration from Legacy System

The platform has migrated from a legacy approach with separate `value` and `text_value` fields to a unified JSON approach. All legacy fields have been removed to enforce a clean data model.

Benefits of the JSON schema approach over the legacy system:
1. **Flexibility**: Can accommodate any data structure, from simple values to complex nested objects
2. **Validation**: Built-in schema validation ensures data integrity
3. **Evolution**: Schemas can evolve over time while maintaining backward compatibility
4. **Metadata**: Supports rich metadata embedded directly with the values
5. **Multiple Values**: A single submission can contain multiple related values

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

#### 1. Filtered Metric Submissions

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

#### 1. ESG Data Management

##### Submit ESG Data
```json
POST /api/esg-data/
{
    "company": 1,
    "boundary_item": 1,
    "scope": "SCOPE1",
    "value": 150.5,
    "unit": "tCO2e",
    "date_recorded": "2024-03-15"
}

// Response
{
    "id": 1,
    "company": {
        "id": 1,
        "name": "Example Corp"
    },
    "boundary_item": {
        "id": 1,
        "name": "Hong Kong Office",
        "description": "Main office operations"
    },
    "scope": "SCOPE1",
    "value": 150.5,
    "unit": "tCO2e",
    "date_recorded": "2024-03-15",
    "submitted_by": {
        "id": 5,
        "email": "user@example.com"
    },
    "is_verified": false,
    "verification_date": null,
    "verified_by": null
}
```

##### Update ESG Data
```json
PUT /api/esg-data/1/
{
    "value": 160.5,
    "unit": "tCO2e"
}

// Response
{
    "id": 1,
    "company": {
        "id": 1,
        "name": "Example Corp"
    },
    "boundary_item": {
        "id": 1,
        "name": "Hong Kong Office"
    },
    "scope": "SCOPE1",
    "value": 160.5,
    "unit": "tCO2e",
    "date_recorded": "2024-03-15",
    "submitted_by": {
        "id": 5,
        "email": "user@example.com"
    },
    "is_verified": false
}
```

##### Verify ESG Data (Baker Tilly Admin only)
```json
POST /api/esg-data/1/verify/
{
    "verification_notes": "Data verified against utility bills"
}

// Response
{
    "id": 1,
    "is_verified": true,
    "verification_date": "2024-03-16T10:30:00Z",
    "verified_by": {
        "id": 2,
        "email": "baker.admin@example.com"
    }
}
```

#### 2. Template Management

##### Create Template
```json
POST /api/templates/
{
    "name": "HKEX ESG Comprehensive 2024",
    "description": "Full ESG disclosure template with all HKEX requirements",
    "selected_forms": [
        {
            "form_id": 1,
            "regions": ["HK", "PRC"],
            "order": 1
        },
        {
            "form_id": 2,
            "regions": ["HK", "PRC"],
            "order": 2
        }
    ]
}

// Response
{
    "id": 1,
    "name": "HKEX ESG Comprehensive 2024",
    "description": "Full ESG disclosure template with all HKEX requirements",
    "is_active": true,
    "version": 1,
    "created_by": {
        "id": 2,
        "email": "baker.admin@example.com"
    },
    "created_at": "2024-03-16T09:00:00Z",
    "updated_at": "2024-03-16T09:00:00Z",
    "selected_forms": [
        {
            "id": 1,
            "form": {
                "id": 1,
                "code": "HKEX-A1",
                "name": "Emissions"
            },
            "regions": ["HK", "PRC"],
            "order": 1
        },
        {
            "id": 2,
            "form": {
                "id": 2,
                "code": "HKEX-A2",
                "name": "Resource Use"
            },
            "regions": ["HK", "PRC"],
            "order": 2
        }
    ]
}
```

##### Preview Template
```json
GET /api/templates/1/preview/

// Response
{
    "template_id": 1,
    "template_name": "HKEX ESG Comprehensive 2024",
    "description": "Comprehensive ESG reporting template following HKEX guidelines",
    "forms": [
        {
            "form_id": 1,
            "form_code": "HKEX-A1",
            "form_name": "Emissions",
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
                    "name": "Direct GHG emissions",
                    "unit_type": "tCO2e",
                    "custom_unit": null,
                    "requires_evidence": true,
                    "validation_rules": {"min": 0},
                    "location": "HK",
                    "is_required": false,
                    "order": 1,
                    "requires_time_reporting": false,
                    "reporting_frequency": null
                },
                {
                    "id": 2,
                    "name": "Direct GHG emissions",
                    "unit_type": "tCO2e",
                    "custom_unit": null,
                    "requires_evidence": true,
                    "validation_rules": {"min": 0},
                    "location": "PRC",
                    "is_required": false,
                    "order": 2,
                    "requires_time_reporting": false,
                    "reporting_frequency": null
                }
            ]
        },
        {
            "form_id": 2,
            "form_code": "HKEX-A2",
            "form_name": "Resource Use",
            "regions": ["HK", "PRC"],
            "category": {
                "id": 1,
                "name": "Environmental",
                "code": "environmental",
                "icon": "leaf",
                "order": 1
            },
            "order": 2,
            "metrics": [
                {
                    "id": 8,
                    "name": "Electricity consumption (CLP)",
                    "unit_type": "kWh",
                    "custom_unit": null,
                    "requires_evidence": true,
                    "validation_rules": {"period": "monthly", "year": "2024"},
                    "location": "HK",
                    "is_required": false,
                    "order": 1,
                    "requires_time_reporting": true,
                    "reporting_frequency": "monthly"
                },
                {
                    "id": 9,
                    "name": "Electricity consumption (HKE)",
                    "unit_type": "kWh",
                    "custom_unit": null,
                    "requires_evidence": true,
                    "validation_rules": {"period": "monthly", "year": "2024"},
                    "location": "HK",
                    "is_required": false,
                    "order": 2,
                    "requires_time_reporting": true,
                    "reporting_frequency": "monthly"
                }
            ]
        }
    ]
}

// Response
{
    "id": 1,
    "assignment": 1,
    "metric": 5,
    "metric_name": "Electricity consumption (CLP)",
    "metric_unit": "kWh",
    "value": 120.5,
    "text_value": null,
    "reporting_period": "2024-03-31",
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
    "evidence": []
}

For optimal performance and user experience in enterprise settings, we recommend implementing consolidated endpoints that combine related data in a single request. This is particularly valuable for Baker Tilly admins who need to review template submissions.

### Recommended Consolidated Endpoint

```
GET /api/admin/template-submissions/{assignment_id}/
```

This endpoint would return a complete view including:
- Template structure with forms and categories
- All metric submissions with values
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

1. **View Assigned Templates**: Users view templates assigned to them using `GET /api/user-templates/`
2. **View Template Details**: Users get detailed information about a specific assignment using `GET /api/user-templates/{assignment_id}/` (which includes template structure via serializers). A dedicated template preview is also available via `GET /api/templates/{template_id}/preview/`.
3. **Submit Metric Values**: Users submit values for metrics using `POST /api/metric-submissions/`. Updates are done via `PUT /api/metric-submissions/{id}/`. Note the update-or-create behavior of POST. Batching is handled by setting the `batch_submission` field if needed.
4. **Upload Evidence**: Users upload supporting documentation using `POST /api/metric-evidence/`. They need to link it to a submission (by setting the `submission` field) or provide `intended_metric`, `layer`, `submission_identifier` for later association.
5. **Check Form Completion Status**: Users/System check if a form's requirements are met using `GET /api/esg-forms/{form_id}/check_completion/?assignment_id={assignment_id}`.
6. **Complete Forms**: Users mark forms as completed using `POST /api/esg-forms/{form_id}/complete_form/` (requires `assignment_id` in the body) when all required metrics are filled according to the check in step 5.
7. **Check Overall Assignment Status**: The status of the overall assignment (`TemplateAssignment.status`) is updated automatically (e.g., to `SUBMITTED` when all forms are complete) or potentially via specific admin actions. Users can view the current status via `GET /api/user-templates/{assignment_id}/`.
8. **Verification**: Baker Tilly admins verify submissions. This might involve verifying individual submissions (`POST /api/metric-submissions/{id}/verify/` - if implemented) or potentially verifying batches (`ESGMetricBatchSubmission` status update) or the entire assignment (`TemplateAssignment` status update).

## Best Practices

1. **Metric Organization**:
   - Keep related metrics together using order field
   - Group location-specific metrics sequentially
   - Use clear, consistent naming conventions

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

## Admin Interface

Access the admin interface at `/admin/` to manage:
- ESG Form Categories
- ESG Forms
- ESG Metrics
- Templates
- Template Assignments

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

# ESG Platform Data Model

This document outlines the data model for the ESG Platform, focusing on the JSON-based approach for metric submissions.

## Core Models

### ESGMetricSubmission

The `ESGMetricSubmission` model is the central model for storing all metric data. It uses a JSON-based approach where all metric data is stored in a structured JSON object.

Key fields:
- `assignment`: Reference to the template assignment
- `metric`: Reference to the ESG metric being reported
- `data`: JSON field containing all metric data in a structured format
- `layer`: The organizational layer this submission applies to
- `batch_submission`: Optional reference to a batch submission
- Metadata fields: `submitted_by`, `submitted_at`, `is_verified`, etc.

### MetricSchemaRegistry

The `MetricSchemaRegistry` model defines standard JSON schemas for different types of metrics.

Key fields:
- `name`: Name of the schema (e.g. "Emissions", "Resource Consumption")
- `description`: Description of what the schema is used for
- `schema`: JSON Schema definition that defines the structure and validation rules
- `version`: Schema version for tracking changes
- Metadata fields: `created_by`, `created_at`, `is_active`, etc.

### ESGMetricBatchSubmission

The `ESGMetricBatchSubmission` model represents a group of related metric submissions submitted together.

Key fields:
- `assignment`: Reference to the template assignment
- `name`: Optional name for the batch
- `layer`: The organizational layer this batch applies to
- `submissions`: Related submissions (reverse relation)
- Metadata fields: `submitted_by`, `submitted_at`, `is_verified`, etc.

## JSON Schema Structure

Each metric can have its own JSON schema defined either directly on the metric or via reference to the schema registry. 

Example schema for emissions data:
```json
{
  "type": "object",
  "properties": {
    "value": {"type": "number"},
    "unit": {"type": "string", "enum": ["tCO2e", "kgCO2e"]},
    "scope": {"type": "string", "enum": ["Scope 1", "Scope 2", "Scope 3"]},
    "source": {"type": "string"},
    "calculation_method": {"type": "string", "enum": ["location-based", "market-based"]},
    "periods": {
      "type": "object",
      "additionalProperties": {
        "type": "object",
        "properties": {
          "value": {"type": "number"},
          "notes": {"type": "string"}
        }
      }
    }
  },
  "required": ["value", "unit", "scope"]
}
```

## Units in JSON and Primary Measurements

The ESG Platform now uses a units-in-JSON approach where each value in the JSON data has its own unit specification, rather than using the separate `unit_type`/`custom_unit` fields on the ESGMetric model.

### Units Embedded in JSON

Every measurement in the JSON data should include its own unit:

```json
{
  "value": 1500,
  "unit": "kWh",
  "comments": "Monthly electricity consumption"
}
```

This approach allows for:
1. Self-contained data that carries its own unit information
2. Multiple values with different units in the same submission
3. Clearer data contracts between frontend and backend
4. Better support for exports/imports between systems

### Complex Metrics with Multiple Values

For metrics that track multiple related values, each can have its own unit:

```json
{
  "electricity": {
    "value": 1500,
    "unit": "kWh"
  },
  "gas": {
    "value": 350,
    "unit": "m³"
  },
  "water": {
    "value": 42000,
    "unit": "liters"
  },
  "comments": "Monthly utility consumption"
}
```

### Specifying Primary Measurements

For complex metrics with multiple values, the `primary_path` field on the `ESGMetric` model indicates which value within the `data` JSON is considered the "primary" one. This path points to the relevant value (e.g., `"electricity.value"` or `"annual_total"`).

```python
# Example ESGMetric field definition:
primary_path = models.CharField(
    max_length=255,
    null=True,
    blank=True,
    help_text="Path to the primary value in the JSON data (e.g., 'electricity.value')"
)
```

If the `ESGMetric.primary_path` is set, the system uses this path to identify the primary measurement. An optional `_metadata.primary_measurement` field within the JSON data itself can also be used as a fallback or alternative mechanism, but the model field is the primary configuration point.

Example JSON data structure (assuming `primary_path` on the metric is set to `"electricity.value"`):
```json
{
  "electricity": {
    "value": 1500,
    "unit": "kWh"
  },
  "gas": {
    "value": 350,
    "unit": "m³"
  }
  // No _metadata needed here if ESGMetric.primary_path is set
}
```

The primary measurement is used for:
1. UI highlighting (which value to emphasize in the interface)
2. Default aggregation (which value to use in calculations)
3. Legacy system compatibility (where a single value is expected)
4. Reporting purposes (which value to include in summaries)

### Tabular Data Example

For complex tabular data like supplier assessments or legal case registers:

```json
{
  "suppliers": [
    {
      "name": "Supplier A",
      "assessment": {
        "compliance_status": "Compliant",
        "score": {
          "value": 85,
          "unit": "points"
        },
        "date": "2023-05-12"
      }
    },
    {
      "name": "Supplier B",
      "assessment": {
        "compliance_status": "Partially Compliant",
        "score": {
          "value": 65,
          "unit": "points"
        },
        "date": "2023-06-15"
      }
    }
  ],
  "_metadata": {
    "primary_measurement": "suppliers.length"
  }
}
```

In this example, the primary measurement is set to the number of suppliers (count), but each supplier has its own assessment score with units.

### Time-Based Metrics with Embedded Units

For time-based metrics, each period includes its own value and unit:

```json
{
  "periods": {
    "Q1-2024": {
      "value": 120.5,
      "unit": "kWh",
      "comments": "January-March consumption"
    },
    "Q2-2024": {
      "value": 135.2,
      "unit": "kWh",
      "comments": "April-June consumption"
    }
  },
  "annual_total": 255.7,
  "annual_unit": "kWh",
  "_metadata": {
    "primary_measurement": "annual_total"
  }
}
```

## Example Submission Data

### Example 1: Emissions Data

```json
{
  "value": 500,
  "unit": "tCO2e",
  "scope": "Scope 2",
  "source": "Electricity",
  "calculation_method": "location-based",
  "periods": {
    "Jan-2024": {"value": 42, "notes": "Lower due to office closure"},
    "Feb-2024": {"value": 45, "notes": "Normal operations"},
    "Mar-2024": {"value": 38, "notes": "Energy efficiency improvements"}
  }
}
```

### Example 2: Employee Training Data

```json
{
  "total_employees": 250,
  "employees_trained": 220,
  "total_hours": 1320,
  "average_hours_per_employee": 5.28,
  "training_categories": [
    {
      "category": "Health & Safety",
      "participants": 250,
      "hours": 500
    },
    {
      "category": "Environmental Awareness",
      "participants": 150,
      "hours": 300
    },
    {
      "category": "Anti-corruption",
      "participants": 220,
      "hours": 520
    }
  ]
}
```

## API Endpoints

### Individual Submissions

```
POST /api/metric-submissions/
GET /api/metric-submissions/{id}/
PUT /api/metric-submissions/{id}/
DELETE /api/metric-submissions/{id}/
GET /api/metric-submissions/by_assignment/?assignment_id={id}
```

### Batch Submissions

```
POST /api/batch-submissions/submit_batch/
GET /api/batch-submissions/{id}/
GET /api/batch-submissions/{id}/submissions/
```

### Schema Registry

```
GET /api/schemas/
POST /api/schemas/
GET /api/schemas/{id}/
PUT /api/schemas/{id}/
GET /api/schemas/schema_types/
GET /api/schemas/{id}/metrics/
```

## Evidence Linking

Evidence files can be linked to specific parts of a JSON structure using the `json_path` field on the `ESGMetricEvidence` model.

For example, to link evidence to a specific period in an emissions submission:
```python
# ESGMetricEvidence instance
evidence.json_path = "periods.Jan-2024"
```

The `reference_path` field is also available, primarily intended for use with OCR to specify the target path for extracted data.

This allows for precise evidence linking to any level of the JSON structure, including:
- Linking a bill to a specific monthly period
- Attaching evidence to a particular measurement in a complex structure
- Providing documentation for specific data points within tabular data

The `submission_identifier` field can be used to link evidence to a specific instance of `ESGMetricSubmission` if multiple submissions exist for the same metric/assignment/layer combination.

## Data Validation

All submissions are validated against their schema at submission time. This ensures data integrity and consistency.

## Performance Considerations

- PostgreSQL GIN indexes are used for efficient querying of JSON data
- For complex queries, consider using the PostgreSQL JSON path operators
- For high-volume metrics, consider adding specific database indexes on commonly queried JSON paths

## Migration from Legacy System

The platform has migrated from a legacy approach with separate `value` and `text_value` fields to a unified JSON approach. All legacy fields have been removed to enforce a clean data model.