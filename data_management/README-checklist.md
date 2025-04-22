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

## Submitting Responses

To submit responses to a checklist:

1. Create an `ESGMetricSubmission` linked to the ChecklistMetric
2. Create `ChecklistResponse` objects for each item being answered
3. Set the response to YES, NO, or NA with optional remarks

Example:

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

The checklist data structure is designed to be easily converted to input for AI report generation. The hierarchical format with clear categories and consistent YES/NO/NA responses enables detailed analysis and actionable recommendations.

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