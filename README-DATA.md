# ESG Data Management System

## Overview

The ESG Data Management System is designed to handle ESG (Environmental, Social, and Governance) reporting requirements, with a specific focus on HKEX ESG reporting guidelines. The system uses a hierarchical structure of Categories, Forms, and Metrics to organize and collect ESG data.

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
Metrics are the actual data points collected for each form. Each metric can be location-specific.

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

## Templates and Assignments

### 1. Templates
Templates combine multiple ESG forms for assignment to companies:

Properties:
- `name`: Template name
- `description`: Template description
- `reporting_period`: e.g., 'Annual 2024', 'Q1 2024'
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

### 3. Template Assignment
Assigns templates to companies for reporting:

Properties:
- `template`: Link to Template
- `company`: Link to Company (LayerProfile)
- `assigned_to`: User responsible for reporting
- `due_date`: Submission deadline
- `status`: Current status (PENDING, IN_PROGRESS, etc.)
- `reporting_period_start`: Start of reporting period
- `reporting_period_end`: End of reporting period

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
  "reporting_period": "Annual 2024",
  "layer_id": 3,
  "layer_name": "Example Corp",
  "status": "PENDING",
  "due_date": "2024-12-31",
  "reporting_period_start": "2024-01-01",
  "reporting_period_end": "2024-12-31",
  "forms": [
    {
      "form_id": 1,
      "form_code": "HKEX-A1",
      "form_name": "Environmental - Emissions",
      "regions": ["HK", "PRC"],
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
          "order": 1
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
- Requires appropriate permissions to access

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

## Time-Based Reporting

The system supports time-based reporting for metrics that require data for multiple periods:

1. **Configuring Time-Based Metrics**:
   - Set `requires_time_reporting=True` on the ESGMetric
   - Set `reporting_frequency` to 'monthly', 'quarterly', or 'annual'
   - These settings will be visible in the template preview and assignment details

2. **Submitting Time-Based Data**:
   - For metrics with `requires_time_reporting=True`, include a `reporting_period` date
   - For monthly data, use the last day of each month (e.g., "2024-01-31", "2024-02-29")
   - For quarterly data, use the last day of the quarter (e.g., "2024-03-31", "2024-06-30")

3. **Usage Example**:
   ```json
   // Monthly electricity consumption
   POST /api/metric-submissions/batch_submit/
   {
       "assignment_id": 1,
       "submissions": [
           {
               "metric_id": 5,
               "value": 120.5,
               "reporting_period": "2024-01-31",
               "notes": "January 2024 electricity consumption"
           },
           {
               "metric_id": 5,
               "value": 115.2,
               "reporting_period": "2024-02-29",
               "notes": "February 2024 electricity consumption"
           },
           {
               "metric_id": 5,
               "value": 130.8,
               "reporting_period": "2024-03-31",
               "notes": "March 2024 electricity consumption"
           }
       ]
   }
   ```

4. **Validation Rules**:
   - You can only have one submission per metric per reporting period
   - The reporting_period field is optional for metrics that don't require time-based reporting
   - For metrics with `requires_time_reporting=True`, the reporting_period is required

5. **Frontend Implementation**:
   - For metrics with `requires_time_reporting=True`, show date picker controls
   - Use the `reporting_frequency` to guide users (e.g., show a monthly calendar for monthly metrics)
   - Allow users to submit multiple entries for the same metric with different reporting periods

This allows for flexible data collection patterns while maintaining data integrity.

## API Endpoints

### ESG Data Management

#### ESG Data Endpoints
- `GET /api/esg-data/?company_id={id}`: Get ESG data entries for a company
- `POST /api/esg-data/`: Create new ESG data entry
- `PUT /api/esg-data/{data_id}/`: Update ESG data entry
- `POST /api/esg-data/{data_id}/verify/`: Verify ESG data entry (Baker Tilly admin only)

#### ESG Metric Submission Endpoints
- `GET /api/metric-submissions/`: List all accessible metric submissions
- `POST /api/metric-submissions/`: Submit a value for a single metric
- `GET /api/metric-submissions/{id}/`: Get details of a specific submission
- `PUT /api/metric-submissions/{id}/`: Update a metric submission
- `DELETE /api/metric-submissions/{id}/`: Delete a metric submission
- `GET /api/metric-submissions/by_assignment/?assignment_id={id}`: Get all submissions for a template assignment
- `POST /api/metric-submissions/batch_submit/`: Submit multiple metric values at once
- `POST /api/metric-submissions/submit_form/`: Mark a form as completed when all required metrics are filled
- `POST /api/metric-submissions/{id}/verify/`: Verify a metric submission (Baker Tilly admin only)

#### ESG Metric Evidence Endpoints
- `GET /api/metric-evidence/`: List all accessible evidence files
- `POST /api/metric-evidence/`: Upload evidence for a metric submission
- `GET /api/metric-evidence/{id}/`: Get details of a specific evidence file
- `DELETE /api/metric-evidence/{id}/`: Delete an evidence file
- `GET /api/metric-evidence/by_submission/?submission_id={id}`: Get all evidence for a submission

### Form and Template Management

#### ESG Forms (Read-only)
- `GET /api/esg-forms/`: List active ESG forms
- `GET /api/esg-forms/{id}/`: Get specific form details
- `GET /api/esg-forms/{id}/metrics/`: Get metrics for a specific form

#### ESG Categories (Read-only)
- `GET /api/esg-categories/`: List all categories with their active forms
- `GET /api/esg-categories/{id}/`: Get specific category details

#### Templates (Baker Tilly Admin only)
- `GET /api/templates/`: List all templates
- `POST /api/templates/`: Create new template
- `GET /api/templates/{id}/`: Get template details
- `PUT /api/templates/{id}/`: Update template
- `DELETE /api/templates/{id}/`: Delete template
- `GET /api/templates/{id}/preview/`: Preview template with forms and metrics

#### Template Assignments
- `GET /api/clients/{group_id}/templates/`: Get client's template assignments
- `POST /api/clients/{group_id}/templates/`: Assign template to client
- `DELETE /api/clients/{group_id}/templates/`: Remove template assignment (requires assignment_id in request body)

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
    "reporting_period": "Annual 2024",
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
    "reporting_period": "Annual 2024",
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
    "name": "HKEX ESG Comprehensive 2024",
    "reporting_period": "Annual 2024",
    "forms": [
        {
            "form_id": 1,
            "form_code": "HKEX-A1",
            "form_name": "Emissions",
            "regions": ["HK", "PRC"],
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
                    "order": 1
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
                    "order": 2
                }
            ]
        },
        {
            "form_id": 2,
            "form_code": "HKEX-A2",
            "form_name": "Resource Use",
            "regions": ["HK", "PRC"],
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
                    "order": 1
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
                    "order": 2
                }
            ]
        }
    ]
}
```

##### Get Client's Template Assignments
```json
GET /api/clients/{group_id}/templates/

// Response
[
  {
    "id": 1,
    "template": {
      "id": 1,
      "name": "HKEX ESG Comprehensive 2024"
    },
    "layer": {
      "id": 1,
      "name": "Example Corp"
    },
    "assigned_to": null,
    "status": "PENDING",
    "due_date": "2024-12-31",
    "reporting_period_start": "2024-01-01",
    "reporting_period_end": "2024-12-31"
  },
  {
    "id": 2,
    "template": {
      "id": 2,
      "name": "HKEX ESG Quarterly Report"
    },
    "layer": {
      "id": 1,
      "name": "Example Corp"
    },
    "assigned_to": null,
    "status": "IN_PROGRESS",
    "due_date": "2024-03-31",
    "reporting_period_start": "2024-01-01",
    "reporting_period_end": "2024-03-31"
  }
]
```

##### Assign Template to Company
```json
POST /api/clients/{group_id}/templates/
{
    "template_id": 1,
    "reporting_period_start": "2024-01-01",
    "reporting_period_end": "2024-12-31",
    "due_date": "2024-12-31"
}

// Response
{
    "id": 1,
    "template": {
        "id": 1,
        "name": "HKEX ESG Comprehensive 2024"
    },
    "layer": {
        "id": 1,
        "name": "Example Corp"
    },
    "assigned_to": null,
    "status": "PENDING",
    "due_date": "2024-12-31",
    "reporting_period_start": "2024-01-01",
    "reporting_period_end": "2024-12-31"
}
```

**Important Notes:**
1. Templates are assigned directly to companies without requiring a specific user
2. Any authorized user from the company can work on the template
3. Optionally, you can specify an `assigned_to` user ID if you want to assign responsibility to a specific user

##### Remove Template Assignment
```json
DELETE /api/clients/{group_id}/templates/
{
    "assignment_id": 1
}

// Response: 204 No Content
```

#### 4. ESG Metric Submissions

##### Submit a Single Metric Value
```json
POST /api/metric-submissions/
{
    "assignment": 1,
    "metric": 5,
    "value": 120.5,
    "reporting_period": "2024-03-31",
    "notes": "Value from March 2024 electricity bill"
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
```

##### Batch Submit Multiple Metric Values
```json
POST /api/metric-submissions/batch_submit/
{
    "assignment_id": 1,
    "submissions": [
        {
            "metric_id": 5,
            "value": 120.5,
            "reporting_period": "2024-03-31",
            "notes": "Value from March 2024 electricity bill"
        },
        {
            "metric_id": 5,
            "value": 115.2,
            "reporting_period": "2024-02-29",
            "notes": "Value from February 2024 electricity bill"
        },
        {
            "metric_id": 6,
            "value": 85.2,
            "notes": "Value from March 2024 water bill"
        }
    ]
}

// Response
{
    "assignment_id": 1,
    "results": [
        {
            "metric_id": 5,
            "submission_id": 1,
            "status": "success",
            "reporting_period": "2024-03-31"
        },
        {
            "metric_id": 5,
            "submission_id": 2,
            "status": "success",
            "reporting_period": "2024-02-29"
        },
        {
            "metric_id": 6,
            "submission_id": 3,
            "status": "success",
            "reporting_period": null
        }
    ]
}
```

##### Get Submissions for a Template Assignment
```json
GET /api/metric-submissions/by_assignment/?assignment_id=1

// Response
[
    {
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
        "evidence": []
    },
    {
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
        "evidence": []
    }
]
```

##### Submit a Completed Form
```json
POST /api/metric-submissions/submit_form/
{
    "assignment_id": 1
}

// Response
{
    "message": "Form successfully submitted",
    "assignment_id": 1,
    "status": "SUBMITTED",
    "completed_at": "2024-04-15T11:45:00Z"
}
```

##### Verify a Metric Submission (Baker Tilly Admin only)
```json
POST /api/metric-submissions/1/verify/
{
    "verification_notes": "Verified against provided utility bills"
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
    "submitted_by": 3,
    "submitted_by_name": "john.doe@example.com",
    "submitted_at": "2024-04-15T10:30:00Z",
    "updated_at": "2024-04-15T10:30:00Z",
    "notes": "Value from March 2024 electricity bill",
    "is_verified": true,
    "verified_by": 2,
    "verified_by_name": "admin@bakertilly.com",
    "verified_at": "2024-04-16T09:15:00Z",
    "verification_notes": "Verified against provided utility bills",
    "evidence": []
}
```

#### 5. ESG Metric Evidence

##### Upload Evidence for a Metric Submission
```json
POST /api/metric-evidence/
{
    "submission": 1,
    "file": [binary file data],
    "filename": "march_2024_electricity_bill.pdf",
    "file_type": "application/pdf",
    "description": "CLP electricity bill for March 2024"
}

// Response
{
    "id": 1,
    "file": "/media/esg_evidence/2024/04/march_2024_electricity_bill.pdf",
    "filename": "march_2024_electricity_bill.pdf",
    "file_type": "application/pdf",
    "uploaded_by": 3,
    "uploaded_by_name": "john.doe@example.com",
    "uploaded_at": "2024-04-15T10:35:00Z",
    "description": "CLP electricity bill for March 2024"
}
```

##### Get Evidence Files for a Submission
```json
GET /api/metric-evidence/by_submission/?submission_id=1

// Response
[
    {
        "id": 1,
        "file": "/media/esg_evidence/2024/04/march_2024_electricity_bill.pdf",
        "filename": "march_2024_electricity_bill.pdf",
        "file_type": "application/pdf",
        "uploaded_by": 3,
        "uploaded_by_name": "john.doe@example.com",
        "uploaded_at": "2024-04-15T10:35:00Z",
        "description": "CLP electricity bill for March 2024"
    }
]
```

## ESG Metric Submission Models

### ESGMetricSubmission
Stores user-submitted values for ESG metrics within a template assignment.

Properties:
- `assignment`: Link to TemplateAssignment
- `metric`: Link to ESGMetric
- `value`: Numeric value (for quantitative metrics)
- `text_value`: Text value (for qualitative metrics)
- `reporting_period`: Date field for time-based metrics (e.g., monthly data)
- `submitted_by`: User who submitted the value
- `submitted_at`: Submission timestamp
- `updated_at`: Last update timestamp
- `notes`: Additional notes about the submission
- `is_verified`: Whether the submission has been verified
- `verified_by`: Baker Tilly admin who verified the submission
- `verified_at`: Verification timestamp
- `verification_notes`: Notes from the verification process

**Important Note**: The combination of `assignment`, `metric`, and `reporting_period` must be unique. This allows multiple submissions for the same metric with different reporting periods (e.g., monthly data).

### ESGMetricEvidence
Stores supporting documentation for ESG metric submissions.

Properties:
- `submission`: Link to ESGMetricSubmission
- `file`: Uploaded file
- `filename`: Original filename
- `file_type`: MIME type of the file
- `uploaded_by`: User who uploaded the file
- `uploaded_at`: Upload timestamp
- `description`: Description of the evidence

## Submission Workflow

1. **View Assigned Templates**: Users view templates assigned to their company using `/api/user-templates/`
2. **View Template Details**: Users get detailed information about a specific template using `/api/user-templates/{assignment_id}/`
3. **Submit Metric Values**: Users submit values for metrics using `/api/metric-submissions/` or `/api/metric-submissions/batch_submit/`
4. **Upload Evidence**: Users upload supporting documentation using `/api/metric-evidence/`
5. **Submit Completed Form**: Users mark the form as completed using `/api/metric-submissions/submit_form/`
6. **Verification**: Baker Tilly admins verify submissions using `/api/metric-submissions/{id}/verify/`

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