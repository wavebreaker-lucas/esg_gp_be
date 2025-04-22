# ESG Checklist System

## Overview

The ESG Checklist System provides a structured way to collect YES/NO responses for compliance assessments and ESG performance evaluations. It's designed to handle hierarchical checklists with categories, subcategories, and individual items, making it ideal for comprehensive ESG assessment frameworks.

## Core Models

### ChecklistMetric

The `ChecklistMetric` model extends `BaseESGMetric` and represents the checklist template configuration:

- **Structure Storage**: Uses a JSONField to store the hierarchical structure of categories, subcategories, and items
- **Configuration Options**: Controls appearance, validation, and scoring behavior
- **ESG Type**: Categorizes the checklist as Environmental, Social, or Governance

### ChecklistResponse

The `ChecklistResponse` model stores individual YES/NO responses for each checklist item:

- **Item Identification**: Tracks category, subcategory, and item IDs
- **Response Data**: Stores YES/NO/NA response with optional remarks
- **Scoring**: Supports optional numerical scoring for compliance measurement

## Checklist Structure Format

Checklists are stored in a structured JSON format:

```json
{
  "categories": [
    {
      "id": "1.1",
      "name": "EMS FRAMEWORK",
      "subcategories": [
        {
          "name": "EMS Framework",
          "items": [
            {
              "id": "a",
              "text": "Are environmental policies documented and accessible?",
              "required": true
            }
          ]
        },
        {
          "name": "Objectives and Targets",
          "items": [
            {
              "id": "b",
              "text": "Are environmental objectives and targets clearly defined?",
              "required": true
            },
            {
              "id": "c",
              "text": "Is there a plan to achieve these objectives and targets?",
              "required": true
            }
          ]
        }
      ]
    }
  ]
}
```

## Creating a Checklist

To create a new checklist:

1. Create a new `ChecklistMetric` instance
2. Set the `checklist_type` to the appropriate ESG category (ENV, SOC, GOV)
3. Define the checklist structure in the `checklist_structure` field
4. Configure any display or validation options

Example:

```python
from data_management.models.polymorphic_metrics import ChecklistMetric

# Create Environmental Checklist
env_checklist = ChecklistMetric.objects.create(
    form=esg_form,  # Link to your ESG form
    name="Environmental Compliance Checklist",
    description="Assessment of environmental management systems and practices",
    checklist_type="ENV",
    checklist_structure={
        "categories": [
            # ... structure as shown above
        ]
    },
    # Optional configuration
    require_remarks_for_no=True,
    enable_scoring=True,
    scoring_method="SIMPLE"
)
```

## Creating the E/S/G Checklists

The system includes a management command to create all three standard ESG checklists at once:

```bash
python manage.py create_esg_checklists --env-form-id=1 --soc-form-id=2 --gov-form-id=3
```

To see available forms:

```bash
python manage.py create_esg_checklists --list-forms
```

## API Interaction

### Submitting Checklist Responses

To submit responses to a checklist via the API, use the standard submission endpoint with a JSON payload containing all responses:

#### Create New Submission

```
POST /api/metric-submissions/
```

```json
{
  "metric": 123,
  "assignment": 456,
  "reporting_period": "2023-12-31",
  "checklist_responses": [
    {
      "category_id": "1.1",
      "subcategory_name": "EMS Framework",
      "item_id": "a",
      "item_text": "Are environmental policies documented and accessible?",
      "response": "YES",
      "remarks": "Policies available on intranet and physical copies"
    },
    {
      "category_id": "1.1",
      "subcategory_name": "Objectives and Targets",
      "item_id": "b",
      "item_text": "Are environmental objectives and targets clearly defined?",
      "response": "NO",
      "remarks": "Objectives exist but lack specific targets"
    },
    {
      "category_id": "1.1",
      "subcategory_name": "Objectives and Targets",
      "item_id": "c",
      "item_text": "Is there a plan to achieve these objectives and targets?",
      "response": "YES",
      "remarks": ""
    }
    // Include all responses in the checklist
  ]
}
```

#### Update Existing Submission

```
PUT /api/metric-submissions/789/
```

```json
{
  "id": 789,
  "metric": 123,
  "assignment": 456,
  "reporting_period": "2023-12-31",
  "checklist_responses": [
    // Include ALL responses, even unchanged ones
    // Any existing responses not included will be deleted
    // The system uses full-replacement for the responses list
  ]
}
```

### Response Processing

The serializer handles:

1. Creating or updating the `ESGMetricSubmission` record
2. For each item in `checklist_responses`:
   - If it matches an existing response (by category_id/item_id combo), update it
   - If no match exists, create a new response
3. Delete any existing responses not included in the update payload
4. Process all changes in a single transaction

### Retrieving Submissions

To retrieve a checklist submission with all its responses:

```
GET /api/metric-submissions/789/
```

Response:

```json
{
  "id": 789,
  "metric": {
    "id": 123,
    "name": "Environmental Compliance Checklist",
    "metric_subtype": "ChecklistMetric",
    // Other metric fields
  },
  "assignment": 456,
  "reporting_period": "2023-12-31",
  "submitted_at": "2023-12-15T10:30:45Z",
  "submitted_by": {
    "id": 101,
    "username": "user@example.com",
    // Other user fields
  },
  "checklist_responses": [
    {
      "id": 501,
      "category_id": "1.1",
      "subcategory_name": "EMS Framework",
      "item_id": "a",
      "item_text": "Are environmental policies documented and accessible?",
      "response": "YES",
      "remarks": "Policies available on intranet and physical copies"
    },
    // All other responses
  ]
}
```

## Python API Examples

To submit responses to a checklist through Python code:

```python
from data_management.models.templates import ESGMetricSubmission
from data_management.models.submission_data import ChecklistResponse

# Create submission
submission = ESGMetricSubmission.objects.create(
    metric=env_checklist,
    assignment=assignment,  # Link to assignment
    # Other required fields
)

# Add responses
ChecklistResponse.objects.create(
    submission=submission,
    category_id="1.1",
    subcategory_name="EMS Framework",
    item_id="a",
    item_text="Are environmental policies documented and accessible?",
    response="YES",
    remarks="Policies available on intranet and in physical copies"
)

ChecklistResponse.objects.create(
    submission=submission,
    category_id="1.1",
    subcategory_name="Objectives and Targets",
    item_id="b",
    item_text="Are environmental objectives and targets clearly defined?",
    response="NO",
    remarks="Objectives exist but lack specific targets and timelines"
)
```

## Scoring and Reporting

The `ChecklistMetric` includes a `calculate_aggregate` method that:

1. Tallies YES/NO/NA responses
2. Calculates compliance percentage
3. Returns statistics for dashboard display and reporting

Different scoring methods are available:
- **SIMPLE**: YES=1, NO=0
- **WEIGHTED**: Each item has a configurable weight
- **CUSTOM**: Custom formula (implemented in extension)

## AI Report Generation

The system provides two AI-powered report generation endpoints that analyze checklist responses and provide detailed insights and recommendations.

### Single Checklist Report

Generate a report for a single checklist submission (Environmental, Social, or Governance):

```
POST /api/checklist-reports/generate/
```

```json
{
  "submission_id": 123
}
```

This endpoint produces a comprehensive report for the specific checklist that includes:
- Executive Summary with compliance percentage
- Key Findings across all categories
- Detailed analysis of compliance gaps
- Actionable recommendations for improvement
- Overall assessment and strategic guidance

Example Response:
```json
{
  "report": {
    "title": "Environmental Compliance Report",
    "company": "Example Corp",
    "generated_at": "2023-12-15T10:30:45Z",
    "compliance_percentage": 78.5,
    "content": "Executive Summary\n\nExample Corp demonstrates a 78.5% compliance rate with environmental standards..."
  }
}
```

### Combined ESG Report

Generate a unified report that analyzes all three ESG dimensions together (Environmental, Social, and Governance):

```
POST /api/checklist-reports/generate-combined/
```

```json
{
  "submission_ids": [123, 124, 125]  // E, S, G submission IDs
}
```

This endpoint produces a holistic ESG report that includes:
- Executive Summary with integrated ESG assessment
- Comparative analysis of E, S, and G performance
- Cross-cutting patterns and systemic issues
- Strategic improvement plan across all ESG areas
- Holistic ESG maturity assessment

Example Response:
```json
{
  "report": {
    "title": "Integrated ESG Compliance Report",
    "company": "Example Corp",
    "generated_at": "2023-12-15T10:30:45Z",
    "overall_compliance": 81.3,
    "environmental_compliance": 78.5,
    "social_compliance": 85.2,
    "governance_compliance": 76.8,
    "content": "Integrated ESG Assessment\n\nExample Corp demonstrates an overall ESG compliance rate of 81.3%..."
  }
}
```

The integrated report provides additional value by identifying relationships between different ESG dimensions and providing a more strategic view of overall ESG performance.

## Report Versioning and Regeneration

The system maintains a complete history of generated reports through a versioning system:

### Report Persistence and Versioning

- Each generated report is saved in the database with a unique ID
- Reports maintain a version number, starting at 1
- Multiple reports can exist for the same submission(s)
- All versions are preserved for audit and historical analysis

### Regenerating Reports

When requesting a new report, you can choose to regenerate an existing one:

```
POST /api/checklist-reports/generate/
```

```json
{
  "submission_id": 123,
  "regenerate": true
}
```

- If `regenerate` is not provided or `false`, an existing report will be returned if one exists
- If `regenerate` is `true`, a new report will be generated with an incremented version number
- The original report remains in the database and accessible through the API

Example response when regenerating:
```json
{
  "report": {
    "title": "Environmental Compliance Report",
    "company": "Example Corp",
    "generated_at": "2023-12-16T14:45:22Z",
    "compliance_percentage": 78.5,
    "content": "...",
    "report_id": 458,
    "version": 2
  },
  "status": "generated_new"
}
```

This versioning system is useful for:
- Tracking changes in recommendations over time
- Comparing assessment approaches after updates
- Providing a complete audit trail for compliance purposes
- Generating different report styles for the same data

## Layer-Based Report Organization

The ESG Checklist System organizes reports based on organizational layers (e.g., company divisions, departments, or business units), making it easy to manage and access reports within your organizational hierarchy.

### Layer Association

Reports are directly associated with organizational layers:

- Each report is automatically linked to the same layer as its source submission(s)
- For combined reports, the layer of the primary submission is used
- This approach aligns reporting with your actual organizational structure

### Retrieving Reports by Layer

To retrieve all reports for a specific organizational layer:

```
GET /api/checklist-reports/layer/123/
```

This endpoint returns all reports associated with the specified layer, including all versions, grouped by company/entity:

```json
{
  "layer_id": 123,
  "summary": {
    "entity_count": 3,
    "report_count": 12,
    "latest_report_date": "2023-12-15"
  },
  "reports_by_entity": {
    "Division A": [
      {
        "id": 456,
        "report_type": "SINGLE",
        "title": "Environmental Compliance Report",
        "company": "Division A",
        "generated_at": "2023-12-15 10:30:45",
        "overall_compliance": 78.5,
        "content": "...",
        "word_count": 1245,
        "version": 2,
        "primary_submission_id": 789
      },
      {
        "id": 450,
        "report_type": "SINGLE",
        "title": "Environmental Compliance Report",
        "company": "Division A",
        "generated_at": "2023-12-10 09:15:30",
        "overall_compliance": 75.2,
        "content": "...",
        "word_count": 1180,
        "version": 1,
        "primary_submission_id": 789
      },
      // Other reports for Division A
    ],
    "Division B": [
      // Reports for Division B
    ],
    "Division C": [
      // Reports for Division C
    ]
  }
}
```

### Benefits of Layer-Based Organization

The layer-based approach offers several advantages:

1. **Organizational Relevance**: Reports are organized according to your actual business structure
2. **Comprehensive Views**: Managers can see all ESG reporting for their area of responsibility
3. **Simplified Access**: No need to query by submissions or templates - direct layer access
4. **Consolidated Metrics**: Summary statistics provide immediate insights into compliance across the layer
5. **Permission Integration**: Uses existing layer-based permission system for access control

## Configuration Options

| Option | Description |
|--------|-------------|
| `show_item_ids` | Whether to display item IDs in the rendered checklist |
| `allow_partial_submission` | Allow saving incomplete checklists as drafts |
| `require_remarks_for_no` | Require explanatory remarks when an item is marked NO |
| `enable_scoring` | Enable numerical scoring for compliance measurement |
| `scoring_method` | Method for calculating scores (SIMPLE, WEIGHTED, CUSTOM) |
| `scoring_weights` | Custom weights for items when using weighted scoring |

## Sample ESG Checklists

The system comes with three pre-configured checklist types:

1. **Environmental Checklist**: Covers environmental management systems, energy, water, waste, emissions, and biodiversity
2. **Social Checklist**: Covers labor practices, health & safety, diversity, community, human rights, and supply chain
3. **Governance Checklist**: Covers ethics, compliance, transparency, and stakeholder engagement

These can be customized or extended based on specific reporting requirements and industry standards.