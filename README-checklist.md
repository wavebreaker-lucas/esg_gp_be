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

### Planned Change: Exclude NA from Compliance Percentage Calculation

> **Planned (not yet implemented):**
>
> The compliance percentage calculation will be updated so that items marked as 'NA' (not applicable) are excluded from the denominator. This means compliance will be calculated as:
>
>     compliance_percentage = (YES responses) / (Total items - NA responses) * 100
>
> This change will ensure that organizations are not penalized for checklist items that do not apply to them. The ESG rating and all compliance statistics will be based only on applicable items (YES/NO), not on NA or unanswered items. This is currently under review and will be implemented after client approval.

## AI Report Generation

The system provides AI-powered report generation that analyzes checklist responses across all three ESG dimensions (Environmental, Social, and Governance) and provides detailed insights and recommendations in a comprehensive report. The report content is returned in a structured JSON format, allowing for flexible presentation on the frontend.

> **Note:** The system only supports combined ESG reports that include all three ESG dimensions (Environmental, Social, and Governance). Individual checklist reports are disabled to ensure comprehensive and balanced ESG assessment.

### Combined ESG Report Generation

Generate a unified report that analyzes all three ESG dimensions together:

```
POST /api/checklist-reports/generate-combined/
```

```json
{
  "submission_ids": [123, 124, 125]  // E, S, G submission IDs
}
```

This endpoint produces a holistic ESG report that includes:
- Company overview and executive summary of ESG performance
- Detailed analysis of Environmental, Social, and Governance pillars with strengths and weaknesses
- Cross-cutting patterns and systemic issues
- Actionable, prioritized improvement plan tailored to the company's context
- Holistic ESG maturity assessment

The report content is returned as a structured JSON object:

```json
{
  "content": {
    "executive_summary": "Text summary including company overview...",
    "esg_pillars": {
      "environmental": "Text analysis of Environmental pillar, strengths, weaknesses...",
      "social": "Text analysis of Social pillar, strengths, weaknesses...",
      "governance": "Text analysis of Governance pillar, strengths, weaknesses..."
    },
    "key_findings": "Text identifying cross-pillar patterns...",
    "improvement_plan": "Text outlining recommendations for E, S, and G...",
    "conclusion": "Text assessing overall maturity and strategic recommendations..."
  },
  "is_structured": true,
  // ... other report metadata ...
}
```

The API response also includes a programmatically calculated ESG rating (A-F) and a description based on the overall compliance percentage.

Example Response:
```json
{
  "report": {
    "id": 458,
    "report_type": "COMBINED",
    "title": "Integrated ESG Compliance Report",
    "company": "Example Corp",
    "generated_at": "2023-12-15T10:30:45Z",
    "overall_compliance": 63.5,
    "environmental_compliance": 55.2,
    "social_compliance": 71.8,
    "governance_compliance": 68.0,
    "esg_rating": "B", // Calculated rating
    "rating_description": "Above-average ESG performance with room for strategic improvements", // Calculated description
    "content": {
      "executive_summary": "Example Corp, a tech company with 500 employees...",
      "esg_pillars": {
        "environmental": "ENVIRONMENTAL (15/28, 55.2%)\nStrengths:\n• Well-documented environmental policies...",
        "social": "SOCIAL (26/37, 71.8%)\nStrengths:\n• Strong labor practices...",
        "governance": "GOVERNANCE (9/14, 68.0%)\nStrengths:\n• Strong code of ethics..."
      },
      "key_findings": "Key patterns observed include...",
      "improvement_plan": "Environmental Improvements:\n• Implement environmental performance tracking...",
      "conclusion": "The company shows strong governance and social practices but needs..."
    },
    "is_structured": true,
    "word_count": 2850,
    "version": 1
  }
}
```

The integrated report provides significant value by identifying relationships between different ESG dimensions and providing a strategic view of overall ESG performance.

## Automated Combined Report Generation

For a more streamlined reporting workflow, the system provides endpoints that automatically find and combine the appropriate ESG checklists based on organizational structure:

### Checking Checklist Status

To check which checklists are completed for a specific layer:

```
GET /api/checklist-status/123/
```

This endpoint performs a comprehensive check of completion status, verifying that all required checklist items have been answered:

```json
{
  "ENV": {
    "complete": true,
    "submission_id": 456,
    "reporting_period": "2023-12-31",
    "submitted_at": "2023-12-15T10:30:45Z",
    "completion_percentage": 100.0,
    "answered_items": 42,
    "total_items": 50,
    "required_items": 42,
    "missing_required": 0
  },
  "SOC": {
    "complete": false,
    "submission_id": 457,
    "reporting_period": "2023-12-31",
    "submitted_at": "2023-12-16T14:20:30Z",
    "completion_percentage": 85.7,
    "answered_items": 30,
    "total_items": 35,
    "required_items": 35,
    "missing_required": 5
  },
  "GOV": {
    "complete": false,
    "submission_id": null,
    "reporting_period": null,
    "submitted_at": null,
    "completion_percentage": 0.0,
    "answered_items": 0,
    "total_items": 0,
    "required_items": 0,
    "missing_required": 0
  },
  "all_complete": false
}
```

The system considers a checklist "complete" only when all required items have been answered with a valid response (YES, NO, or NA). The completion percentage is calculated based on the number of required items that have been answered.

### Automated Combined Report Generation

Once all three checklists are properly completed, you can generate a combined report with a single API call:

```
POST /api/checklist-reports/generate-for-layer/
```

```json
{
  "layer_id": 123,
  "regenerate": false
}
```

This endpoint:
1. Automatically finds the latest ENV, SOC, and GOV checklist submissions for the layer
2. Validates that all three checklist types are complete
3. Checks if a report already exists for these submissions (returns it if found)
4. Generates a new combined report if needed or if regenerate=true is specified. The generated report will have structured JSON content and a calculated ESG rating.

Optional parameters:
- `entity_name`: Filter for a specific entity name within the layer
- `reporting_period`: Use submissions from a specific reporting period
- `regenerate`: Force generation of a new report even if one exists

Example response (updated to reflect structured content and rating):
```json
{
  "report": {
    "id": 458,
    "report_type": "COMBINED",
    "title": "Integrated ESG Compliance Report",
    "company": "Division A",
    "generated_at": "2023-12-16T14:45:22Z",
    "overall_compliance": 81.3,
    "environmental_compliance": 78.5,
    "social_compliance": 85.2,
    "governance_compliance": 76.8,
    "esg_rating": "A", // Calculated rating
    "rating_description": "Excellent ESG performance with industry-leading practices", // Calculated description
    "content": {
      "executive_summary": "Division A demonstrates strong overall ESG performance...",
      "esg_pillars": {
        // ... detailed pillar analysis ...
      },
      "key_findings": "...",
      "improvement_plan": "...",
      "conclusion": "..."
    },
    "is_structured": true,
    "word_count": 3245,
    "version": 1
  },
  "status": "generated_new"
}
```

This approach eliminates the need for users to manually specify which submissions to include in the combined report.

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