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

### 4. Custom Forms and Metrics
The system allows Baker Tilly administrators to create custom forms and metrics for specific client needs:

1. **Custom Categories**: New form categories can be created beyond the standard Environmental, Social, and Governance.
2. **Custom Forms**: Administrators can create bespoke forms for specialized reporting requirements.
3. **Custom Metrics**: Industry-specific or client-specific metrics can be defined with flexible properties:
   - Custom unit types
   - Location-specific metrics
   - Time-based reporting frequencies
   - Validation rules to ensure data quality

Custom forms and metrics can be created alongside standard forms in templates, allowing a mix of standardized and client-specific reporting within the same workflow.

### Related API Endpoints:
- `POST /api/esg-categories/`: Create custom category
- `POST /api/esg-forms/`: Create custom form
- `POST /api/esg-metrics/`: Create custom metric
- `POST /api/esg-forms/{id}/add_metric/`: Add metric to existing form

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
- `is_completed`: Whether this form has been completed
- `completed_at`: When the form was completed
- `completed_by`: User who completed the form

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
          "reporting_frequency": null
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
          "reporting_frequency": "monthly"
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
          "reporting_frequency": "monthly"
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
- `POST /api/metric-submissions/submit_template/`: Mark a template as submitted when all forms are completed
- `POST /api/metric-submissions/{id}/verify/`: Verify a metric submission (Baker Tilly admin only)

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
   - Can create and manage templates and forms

2. **Regular Users**
   - Access restricted to their assigned layers (companies/organizations)
   - Can only view and modify submissions for their own layers
   - Can't access data from other client organizations
   - Can't verify submissions (reserved for Baker Tilly admins)

For many endpoints, the system automatically filters results based on user permissions, so regular users will only see data they have access to, while Baker Tilly admins see all data.

### Enhanced Endpoints for Optimized Review

The API includes optimized endpoints that make the review process more efficient:

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
```

**Key Features:**
- Returns complete category information for each form, including:
  - `id`: The category's unique identifier
  - `name`: The display name of the category
  - `code`: The category's code (e.g., "environmental")
  - `icon`: Icon reference for frontend rendering (e.g., "leaf")
  - `order`: The display order within the category list
- Includes form `order` for sorting within categories
- Provides the same metric details as the user-templates endpoint
- Matches the format of the user-templates endpoint for frontend compatibility
- Allows the same components to be used for both preview and assigned templates

##### Get Client's Template Assignments
```json
GET /api/clients/{layer_id}/templates/

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
    "reporting_period_end": "2024-12-31",
    "reporting_year": 2025
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
    "reporting_period_end": "2024-03-31",
    "reporting_year": 2025
  }
]
```

##### Assign Template to Company
```json
POST /api/clients/{layer_id}/templates/
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
    "reporting_period_end": "2024-12-31",
    "reporting_year": 2025
}
```

**Important Notes:**
1. Templates can only be assigned to group layers
2. Any authorized user from the company can work on the template
3. Optionally, you can specify an `assigned_to` user ID if you want to assign responsibility to a specific user

##### Remove Template Assignment
```json
DELETE /api/clients/{layer_id}/templates/
{
    "assignment_id": 1
}

// Response: 204 No Content
```

#### 3. ESG Form and Metric Management

##### Create ESG Category
```json
POST /api/esg-categories/
{
    "name": "Custom Reporting",
    "code": "custom",
    "icon": "clipboard-check",
    "order": 4
}

// Response
{
    "id": 4,
    "name": "Custom Reporting",
    "code": "custom",
    "icon": "clipboard-check",
    "order": 4
}
```

##### Partially Update ESG Metric (PATCH)
```json
PATCH /api/esg-metrics/26/
{
    "name": "Updated Metric Name",
    "is_required": false
}

// Response
{
    "id": 26,
    "name": "Updated Metric Name",
    "description": "Number of waste reduction initiatives implemented",
    "unit_type": "count",
    "custom_unit": null,
    "requires_evidence": true,
    "validation_rules": {},
    "location": "ALL",
    "is_required": false,
    "order": 2,
    "requires_time_reporting": false,
    "reporting_frequency": null
}
```

##### Create ESG Form
```json
POST /api/esg-forms/
{
    "category_id": 4,
    "code": "CUSTOM-1",
    "name": "Custom Sustainability Metrics",
    "description": "Company-specific sustainability metrics",
    "order": 1,
    "is_active": true
}

// Response
{
    "id": 12,
    "code": "CUSTOM-1",
    "name": "Custom Sustainability Metrics",
    "description": "Company-specific sustainability metrics",
    "is_active": true,
    "order": 1,
    "metrics": [],
    "category": {
        "id": 4,
        "name": "Custom Reporting",
        "code": "custom",
        "icon": "clipboard-check",
        "order": 4
    }
}
```

##### Add Metric to Form
```json
POST /api/esg-forms/12/add_metric/
{
    "name": "Renewable energy usage",
    "description": "Percentage of total energy from renewable sources",
    "unit_type": "percentage",
    "requires_evidence": true,
    "validation_rules": {"min": 0, "max": 100},
    "location": "HK",
    "is_required": true,
    "order": 1,
    "requires_time_reporting": true,
    "reporting_frequency": "quarterly"
}

// Response
{
    "id": 25,
    "name": "Renewable energy usage",
    "description": "Percentage of total energy from renewable sources",
    "unit_type": "percentage",
    "custom_unit": null,
    "requires_evidence": true,
    "validation_rules": {"min": 0, "max": 100},
    "location": "HK",
    "is_required": true,
    "order": 1,
    "requires_time_reporting": true,
    "reporting_frequency": "quarterly"
}
```

##### Create ESG Metric Directly
```json
POST /api/esg-metrics/
{
    "form_id": 12,
    "name": "Waste reduction initiatives",
    "description": "Number of waste reduction initiatives implemented",
    "unit_type": "count",
    "requires_evidence": true,
    "location": "ALL",
    "is_required": true,
    "order": 2
}

// Response
{
    "id": 26,
    "name": "Waste reduction initiatives",
    "description": "Number of waste reduction initiatives implemented",
    "unit_type": "count",
    "custom_unit": null,
    "requires_evidence": true,
    "validation_rules": {},
    "location": "ALL",
    "is_required": true,
    "order": 2,
    "requires_time_reporting": false,
    "reporting_frequency": null
}
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
    ],
    "forms_completed": ["HKEX-A2: Resource Use"],
    "all_forms_completed": false,
    "assignment_status": "IN_PROGRESS"
}
```

##### Check Form Completion Status
```json
GET /api/esg-forms/{form_id}/check_completion/?assignment_id=1

// Response
{
    "form_id": 2,
    "form_name": "Resource Use",
    "form_code": "HKEX-A2",
    "is_completed": false,
    "completion_percentage": 75.0,
    "total_required_metrics": 4,
    "total_submitted_metrics": 3,
    "missing_metrics": [
        {"id": 10, "name": "Wastewater consumption", "location": "HK"}
    ],
    "can_complete": false
}
```

**Important Notes:**
- This endpoint checks if a specific form is completed or can be completed
- It returns the completion percentage and missing metrics, if any
- The `can_complete` flag indicates if the form can be marked as completed
- If the form is already completed, it includes when it was completed and by whom

##### Complete a Form
```json
POST /api/esg-forms/{form_id}/complete_form/
{
    "assignment_id": 1
}

// Response
{
    "message": "Form successfully completed",
    "form_id": 2,
    "form_name": "Resource Use",
    "form_code": "HKEX-A2",
    "assignment_id": 1,
    "all_forms_completed": false,
    "assignment_status": "IN_PROGRESS"
}
```

**Important Notes:**
- This endpoint checks if all required metrics for the form have been submitted
- If any required metrics are missing, it returns an error with the list of missing metrics
- When a form is completed, it updates the `is_completed`, `completed_at`, and `completed_by` fields in the `TemplateFormSelection` model
- If all forms in the template are completed, it automatically updates the assignment status to "SUBMITTED"

##### Submit a Template
```json
POST /api/metric-submissions/submit_template/
{
    "assignment_id": 1
}

// Response
{
    "message": "Template successfully submitted",
    "assignment_id": 1,
    "status": "SUBMITTED",
    "completed_at": "2024-04-15T11:45:00Z"
}
```

**Important Notes:**
- This endpoint checks if all forms in the template have been completed
- If any forms are incomplete, it returns an error with the list of incomplete forms
- When a template is submitted, it updates the assignment status to "SUBMITTED" and sets the `completed_at` timestamp

##### Get Template Completion Status
```json
GET /api/templates/{template_id}/completion_status/?assignment_id=1

// Response
{
    "assignment_id": 1,
    "template_id": 1,
    "template_name": "HKEX ESG Comprehensive 2024",
    "status": "IN_PROGRESS",
    "due_date": "2024-12-31",
    "completed_at": null,
    "total_forms": 3,
    "completed_forms": 1,
    "overall_completion_percentage": 33.33,
    "forms": [
        {
            "form_id": 1,
            "form_name": "Emissions",
            "form_code": "HKEX-A1",
            "is_completed": false,
            "completed_at": null,
            "completed_by": null,
            "total_required_metrics": 4,
            "total_submitted_metrics": 2,
            "completion_percentage": 50.0,
            "missing_metrics": [
                {"id": 3, "name": "Indirect GHG emissions"},
                {"id": 4, "name": "Waste produced"}
            ]
        },
        {
            "form_id": 2,
            "form_name": "Resource Use",
            "form_code": "HKEX-A2",
            "is_completed": true,
            "completed_at": "2024-04-10T15:30:00Z",
            "completed_by": "john.doe@example.com",
            "total_required_metrics": 3,
            "total_submitted_metrics": 3,
            "completion_percentage": 100.0,
            "missing_metrics": []
        },
        {
            "form_id": 3,
            "form_name": "Environment and Natural Resources",
            "form_code": "HKEX-A3",
            "is_completed": false,
            "completed_at": null,
            "completed_by": null,
            "total_required_metrics": 2,
            "total_submitted_metrics": 0,
            "completion_percentage": 0.0,
            "missing_metrics": [
                {"id": 15, "name": "Significant impacts on environment"},
                {"id": 16, "name": "Mitigation measures"}
            ]
        }
    ]
}
```

**Important Notes:**
- This endpoint provides detailed information about the completion status of each form in the template
- It calculates completion percentages for each form and for the overall template
- It lists missing metrics for each incomplete form
- This is useful for tracking progress and identifying what still needs to be completed

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

##### Verify a Metric Submission (Baker Tilly Admin only)
```json
POST /api/metric-submissions/1/verify/
{
    "verification_notes": "Verified against provided utility bills"
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

## Enterprise-Grade Consolidated Endpoints

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

1. **View Assigned Templates**: Users view templates assigned to their company using `/api/user-templates/`
2. **View Template Details**: Users get detailed information about a specific template using `/api/user-templates/{assignment_id}/`
3. **Submit Metric Values**: Users submit values for metrics using `/api/metric-submissions/` or `/api/metric-submissions/batch_submit/`
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