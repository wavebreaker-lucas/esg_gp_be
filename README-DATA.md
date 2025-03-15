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

## API Endpoints

### ESG Data Management

#### ESG Data Endpoints
- `GET /api/esg-data/?company_id={id}`: Get ESG data entries for a company
- `POST /api/esg-data/`: Create new ESG data entry
- `PUT /api/esg-data/{data_id}/`: Update ESG data entry
- `POST /api/esg-data/{data_id}/verify/`: Verify ESG data entry (Baker Tilly admin only)

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
    "regions": {
        "HK": [
            {
                "form_code": "HKEX-A1",
                "form_name": "Emissions",
                "metrics": [
                    {
                        "id": 1,
                        "name": "Direct GHG emissions",
                        "unit_type": "tCO2e",
                        "requires_evidence": true,
                        "validation_rules": {
                            "min": 0
                        }
                    }
                ]
            }
        ],
        "PRC": [
            {
                "form_code": "HKEX-A1",
                "form_name": "Emissions",
                "metrics": [
                    {
                        "id": 2,
                        "name": "Direct GHG emissions",
                        "unit_type": "tCO2e",
                        "requires_evidence": true,
                        "validation_rules": {
                            "min": 0
                        }
                    }
                ]
            }
        ]
    }
}
```

##### Assign Template to Company
```json
POST /api/clients/{group_id}/templates/
{
    "template_id": 1,
    "reporting_period_start": "2024-01-01",
    "reporting_period_end": "2024-12-31"
}

// Response
{
    "id": 1,
    "template": {
        "id": 1,
        "name": "HKEX ESG Comprehensive 2024"
    },
    "company": {
        "id": 1,
        "name": "Example Corp"
    },
    "assigned_to": {
        "id": 5,
        "email": "creator@example.com",
        "role": "CREATOR"
    },
    "status": "PENDING",
    "due_date": "2024-12-31",
    "reporting_period_start": "2024-01-01",
    "reporting_period_end": "2024-12-31"
}
```

**Important Notes:**
1. The template is always assigned to the company's CREATOR user (initial admin)
2. Each company must have a CREATOR user before templates can be assigned
3. The CREATOR user is automatically created during company setup
4. If no CREATOR user is found, the request will fail with a 400 error

##### Remove Template Assignment
```json
DELETE /api/clients/{group_id}/templates/
{
    "assignment_id": 1
}

// Response: 204 No Content
```

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