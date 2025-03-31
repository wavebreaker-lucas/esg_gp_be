# ESG Platform Evidence Management

## Overview

The ESG Platform includes a comprehensive evidence management system for supporting ESG metric submissions. The system allows users to upload evidence files (such as utility bills), automatically process them with OCR (Optical Character Recognition), and link them to specific parts of JSON data structures within submissions.

## JSON-Centric Data Structure

### Core Concepts

All metric submissions use a `data` JSON field rather than separate value fields:

1. **Regular metrics** - Simple structure:
   ```json
   {
     "value": 42.5,
     "comments": "Additional information"
   }
   ```

2. **Time-based metrics** - Nested period structure:
   ```json
   {
     "periods": {
       "01/2024": { "value": 120.5, "date": "2024-01-31" },
       "02/2024": { "value": 135.2, "date": "2024-02-29" }
     },
     "annual_total": 255.7
   }
   ```

### Evidence and JSON Path Association

Evidence files are associated with specific parts of the JSON data structure using the `reference_path` and `supports_multiple_periods` fields:

```python
# ESGMetricEvidence model includes:
reference_path = models.CharField(
    max_length=255, 
    null=True, 
    blank=True,
    help_text="JSON path this evidence relates to in the submission's data structure (e.g., 'periods.Jan-2024')"
)
supports_multiple_periods = models.BooleanField(
    default=False,
    help_text="Indicates this evidence supports multiple periods or values across different paths"
)
source_type = models.CharField(
    max_length=30,
    choices=SOURCE_TYPE_CHOICES, # Defined in the model
    default='OTHER',
    help_text="Type of source document this evidence represents"
)
```

- The `reference_path` specifies the JSON path the evidence supports.
- The `supports_multiple_periods` flag indicates if the evidence covers multiple periods/values. If true, the `reference_path` should be a base path (e.g., `"periods"`); if false, it should be a specific path (e.g., `"periods.01/2024.value"`).
- The `source_type` field categorizes the evidence (e.g., 'UTILITY_BILL', 'METER_READING').

Common `reference_path` values:
- Regular metrics: `"value"` (with `supports_multiple_periods=False`)
- Specific period in time-based metrics: `"periods.01/2024.value"` (with `supports_multiple_periods=False`)
- Evidence covering multiple periods: `"periods"` (with `supports_multiple_periods=True`)

## API Endpoints

### Evidence Upload

```
POST /api/metric-evidence/
```

Upload a new evidence file (must use `multipart/form-data`):
- `file`: The evidence file (required)
- `metric_id`: ID of the related metric (recommended)
- `layer_id`: ID of the organizational layer this evidence belongs to
- `reference_path`: JSON path this evidence supports.
- `supports_multiple_periods`: Boolean flag (`true`/`false`) indicating if the evidence covers multiple periods/values.
- `source_type`: Type of source document (e.g., 'UTILITY_BILL').
- `description`: Optional description of the evidence

### Process OCR

```
POST /api/metric-evidence/{id}/process_ocr/
```

Extracts data from the evidence file using OCR:
- Sets `extracted_value` and `ocr_period` on the evidence record
- Returns a URL to check OCR results

### Get OCR Results

```
GET /api/metric-evidence/{id}/ocr_results/
```

Retrieves OCR results, including:
- Extracted value
- Period information
- Additional periods found in the document

### Set Target Path (Deprecated - use Upload with correct path instead)

~~`POST /api/metric-evidence/{id}/set_target_path/`~~ 
This endpoint is deprecated. The `reference_path` should be set during the initial upload.

### Attach to Submission

```
POST /api/metric-evidence/{id}/attach_to_submission/
```

Parameters:
- `submission_id`: ID of the submission to attach to (required)
- `apply_ocr_data`: Whether to apply OCR data to the submission's JSON structure (`"true"` or `"false"`)

### Get Evidence by Metric

```
GET /api/metric-evidence/by_metric/?metric_id=123
```

Returns all evidence for a specific metric (both standalone and attached to submissions).

Optional parameter:
- `layer_id`: Filter by organizational layer

### Get Evidence by Submission

```
GET /api/metric-evidence/by_submission/?submission_id=123
```

Returns all evidence attached to a specific submission.

### Batch Evidence Retrieval

```
GET /api/metric-evidence/batch_evidence/?submission_ids=1,2,3
```

Returns evidence for multiple submissions in a single API call, optimized for better performance.
Response is a dictionary mapping submission IDs to their data and associated evidence files.

### Apply Multiple Periods

```
POST /api/metric-evidence/{id}/apply_multiple_periods/
```

Applies OCR-extracted data for multiple billing periods to a submission's JSON structure. This should only be used for evidence where `supports_multiple_periods` is true.

Parameters:
- `submission_id`: ID of the submission to apply periods to
- `base_path`: Base path in the JSON (default: `"periods"`) - Should match the evidence's `reference_path`.
- `value_field`: Name of the field for consumption values (default: `"value"`)

## Evidence Workflow

### 1. Initial Upload

All evidence is initially created as standalone, not associated with any submission.

**Example 1: Single Period Evidence**
```
POST /api/metric-evidence/
{
  "file": [file data],
  "metric_id": 123,
  "layer_id": 7,
  "reference_path": "periods.01/2024.value",
  "supports_multiple_periods": false,
  "source_type": "METER_READING"
}
```

**Example 2: Multi-Period Evidence (e.g., Utility Bill)**
```
POST /api/metric-evidence/
{
  "file": [file data],
  "metric_id": 123,
  "layer_id": 7,
  "reference_path": "periods",
  "supports_multiple_periods": true,
  "source_type": "UTILITY_BILL"
}
```

### 2. OCR Processing (Optional)

Start OCR processing:

```
POST /api/metric-evidence/42/process_ocr/
```

Check results:

```
GET /api/metric-evidence/42/ocr_results/
```

### 3. Attachment to Submission

Attach evidence to a submission with or without applying OCR data:

```
POST /api/metric-evidence/42/attach_to_submission/
{
  "submission_id": 123,
  "apply_ocr_data": "true" // Only applies single primary value if set
}
```

For multi-period evidence, use the `apply_multiple_periods` endpoint after attaching.

### 4. Automatic Attachment

Evidence can be automatically attached during batch submission or form completion based on matching logic (identifier, path, layer).

```
POST /api/batch-submissions/submit_batch/
{
  "assignment_id": 42,
  "submissions": [...],
  "auto_attach_evidence": true
}
```

## Layer-Based Organization

Evidence files can be associated with specific organizational layers (subsidiaries, branches, etc.):

```python
# ESGMetricEvidence model includes:
layer = models.ForeignKey(
    LayerProfile, 
    on_delete=models.SET_NULL, 
    null=True, 
    blank=True,
    related_name='evidence_files',
    help_text="The layer this evidence is from"
)
```

Benefits:
- Organization by business unit
- Layer-specific filtering
- Better data governance
- Enhanced reporting

## Best Practices

1. **Always specify the `metric_id`** when uploading standalone evidence.
2. **Set `reference_path` and `supports_multiple_periods` correctly** during upload to define the evidence scope (specific value vs. multiple values).
3. **Select the appropriate `source_type`** to categorize the evidence.
4. **Include a layer association** for better organization.
5. **Review OCR results** before applying them to submissions.
6. **Use standardized paths** for consistent data structure.
7. **Prefer batch operations** for better performance when working with multiple submissions.
8. **Use `supports_multiple_periods=true` and a base path** for evidence covering multiple time periods or data points (like a comprehensive utility bill).

## Error Handling

Common errors:
- `400 Bad Request`: Missing required parameter or invalid input
- `403 Forbidden`: Insufficient permissions to access the resource
- `404 Not Found`: Resource not found (e.g., submission, metric)

## Technical Implementation Notes

1. The evidence system is fully integrated with the JSON data structure
2. OCR data is never automatically applied to submissions without explicit request
3. The `reference_path` field clarifies which part of the JSON structure the evidence supports
4. The `source_type` field categorizes the evidence
5. Batch operations are now supported through direct actions on the `ESGMetricEvidenceViewSet` 
6. The standalone `BatchEvidenceView` has been removed in favor of the more RESTful action-based approach

## Migration Notes

Recent changes:
1. Consolidated `json_path` and `reference_path` into a single `reference_path` field.
2. Added `supports_multiple_periods` boolean flag to explicitly handle evidence covering multiple periods/values.
3. Added `source_type` field to `ESGMetricEvidence` to categorize source documents.
4. Removed `data_source` field from `ESGMetricSubmission`.
5. Improved OCR processing to better handle multiple billing periods.
6. Enhanced evidence attachment logic for time-based metrics using the new fields.
7. Added schema validation when applying OCR data.
8. Replaced standalone `BatchEvidenceView` with the `batch_evidence` action on `ESGMetricEvidenceViewSet`.
9. Changed URL from `/api/metric-evidence/batch/` to the router-generated `/api/metric-evidence/batch_evidence/`. 