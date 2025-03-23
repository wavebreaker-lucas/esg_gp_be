# OCR Utility Bill Processing

## Overview
The ESG Platform includes automated OCR (Optical Character Recognition) processing for utility bills, using the Azure Content Understanding API. This feature extracts consumption data and billing periods from utility bills, reducing manual data entry and improving accuracy.

## Key Components

### ESGMetric Enhancements
- **Custom Analyzer ID**: Each metric can have a specific `ocr_analyzer_id` to use a custom Azure Content Understanding analyzer tailored for specific utility bill formats.
  ```python
  class ESGMetric(models.Model):
      # ... other fields ...
      ocr_analyzer_id = models.CharField(
          max_length=100, 
          blank=True, 
          null=True,
          help_text="Custom analyzer ID for OCR processing of this metric's evidence"
      )
  ```

### ESGMetricEvidence Model
The `ESGMetricEvidence` model has been enhanced with several OCR-related fields:
```python
class ESGMetricEvidence(models.Model):
    # Standard evidence fields
    submission = models.ForeignKey(ESGMetricSubmission, on_delete=models.CASCADE, 
                                 related_name='evidence', null=True, blank=True,
                                 help_text="Can be null for standalone evidence files before attaching to a submission")
    file = models.FileField(upload_to='esg_evidence/%Y/%m/')
    filename = models.CharField(max_length=255)
    # ... other fields ...
    
    # OCR-related fields
    enable_ocr_processing = models.BooleanField(default=False, 
        help_text="User option to enable OCR data extraction for this evidence file")
    is_processed_by_ocr = models.BooleanField(default=False, 
        help_text="Whether OCR processing has been attempted")
    extracted_value = models.FloatField(null=True, blank=True, 
        help_text="Value extracted by OCR")
    period = models.DateField(null=True, blank=True, 
        help_text="Reporting period extracted by OCR")
    ocr_data = models.JSONField(null=True, blank=True, 
        help_text="Raw data extracted by OCR")
    was_manually_edited = models.BooleanField(default=False, 
        help_text="Whether the OCR result was manually edited")
    # ... other fields ...
```

### UtilityBillAnalyzer Service
The `UtilityBillAnalyzer` service is responsible for processing utility bill evidence files:
- Integrates with Azure Content Understanding API
- Extracts values and periods from utility bills
- Handles multiple billing periods in a single bill
- Updates evidence records with extracted data

## File Storage Options
Evidence files can be stored in two ways:

1. **Local Storage** (default)
   - Files are stored on the server's local filesystem
   - Configured using Django's standard file storage settings
   - Path: `settings.MEDIA_ROOT/esg_evidence/YYYY/MM/`

2. **Azure Blob Storage**
   - Enabled by setting `USE_AZURE_STORAGE = True` in settings
   - Requires additional Azure Blob Storage configuration
   - Uses the Azure Storage SDK for file operations

## API Endpoints

### Evidence Management Endpoints

1. **Upload Evidence** (Universal Upload Endpoint)
   - `POST /api/metric-evidence/`
   - Parameters:
     - `file`: The evidence file to upload (required)
     - `metric_id`: (Optional) ID of the metric this evidence relates to
     - `period`: (Optional) Reporting period in YYYY-MM-DD format
     - `enable_ocr_processing`: (Optional) Set to 'true' to enable OCR
     - `description`: (Optional) Description of the evidence
   - Response:
     - Returns the created evidence record with additional metadata
     - Includes `is_standalone: true`
     - Includes `ocr_processing_url` if OCR processing is enabled

2. **Get Evidence by Metric**
   - `GET /api/metric-evidence/by_metric/?metric_id=123`
   - Returns all evidence files (both standalone and attached) related to a specific metric
   - Useful for showing available evidence when filling out forms

3. **Attach Standalone Evidence to Submission**
   - `POST /api/metric-evidence/{id}/attach_to_submission/`
   - Requires `submission_id` parameter
   - Optional: `apply_ocr_data=true|false` to apply OCR data to the submission
   - Only works for evidence files that aren't already attached to a submission
   - When `apply_ocr_data=true`, displays warnings if overriding existing values

### OCR-Specific Endpoints

1. **Process OCR**
   - `POST /api/metric-evidence/{id}/process_ocr/`
   - Triggers OCR processing for the evidence file
   - Returns extracted data if successful

2. **OCR Results**
   - `GET /api/metric-evidence/{id}/ocr_results/`
   - Retrieves the current OCR processing status and results

## Per-Metric Evidence Upload Workflow

The system supports a streamlined workflow where users can upload evidence files directly from each metric in the form:

1. For each ESG metric, users can upload supporting evidence files
2. Users select the reporting period for each evidence file
3. All evidence is initially created as standalone (no submission association)
4. When a form is completed or when batch submitting metrics, evidence files are automatically attached to the appropriate submissions based on the period

### Evidence Attachment Architecture

Evidence attachment happens at two critical points in the workflow:

1. **Form Completion** - When a user marks a form as complete using the `complete_form` endpoint, the system automatically attaches any standalone evidence files related to the submissions in that form.

2. **Batch Submission** - When users submit multiple metric values at once via the `batch_submit` endpoint with `auto_attach_evidence=true`, the system attaches relevant evidence files to those submissions.

This approach ensures that evidence is attached at the most logical points in the user workflow, where users are actively working with specific forms or metrics.

### Frontend Implementation

```javascript
// Example: Upload evidence for a specific metric with period
function uploadEvidenceForMetric(metricId, files, period, enableOcr = true) {
  const formData = new FormData();
  formData.append('file', files[0]);
  formData.append('metric_id', metricId);
  formData.append('period', period); // Format: YYYY-MM-DD
  formData.append('enable_ocr_processing', enableOcr ? 'true' : 'false');
  
  return fetch('/api/metric-evidence/', {
    method: 'POST',
    body: formData
  }).then(response => response.json());
}

// Example: Get evidence for a specific metric
function getEvidenceForMetric(metricId) {
  return fetch(`/api/metric-evidence/by_metric/?metric_id=${metricId}`)
    .then(response => response.json());
}
```

### Automatic Evidence Attachment

The system automatically attaches standalone evidence files to submissions when:

1. Users submit individual metrics via `batch_submit` with `auto_attach_evidence=true`
2. Users complete a form via the `complete_form` endpoint

```javascript
// Example: Submit metrics with auto-attachment of evidence
function submitMetrics(assignmentId, metricsData) {
  const payload = {
    assignment_id: assignmentId,
    submissions: metricsData,
    auto_attach_evidence: true
  };
  
  return fetch('/api/metric-submissions/batch_submit/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  }).then(response => response.json());
}

// Example: Complete a form (which automatically attaches evidence)
function completeForm(formId, assignmentId) {
  const payload = {
    assignment_id: assignmentId
  };
  
  return fetch(`/api/esg-forms/${formId}/complete_form/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  }).then(response => response.json());
}
```

### Important Note on OCR Data Usage

**OCR data is never automatically applied to submissions.** This design choice ensures:

1. Users maintain complete control over their submitted data
2. OCR serves as a helpful suggestion, not an automatic decision
3. Null or zero values in submissions are respected as valid user choices
4. Data integrity is maintained by requiring explicit user action

If users want to use OCR-extracted values, they must explicitly:

1. Review the OCR results via the OCR results endpoint
2. Manually apply OCR data by calling `attach_to_submission` with `apply_ocr_data=true`

## OCR Processing Flow

### Upload with OCR Processing
1. Upload evidence for a specific metric with OCR enabled:
   ```
   POST /api/metric-evidence/
   {
     "file": [file data],
     "metric_id": 456,
     "period": "2023-04-30",
     "enable_ocr_processing": "true"
   }
   ```
   
2. Process OCR (either immediately or later):
   ```
   POST /api/metric-evidence/{id}/process_ocr/
   ```
   
3. Review OCR results:
   ```
   GET /api/metric-evidence/{id}/ocr_results/
   ```
   
4. Manually apply OCR data (optional):
   ```
   POST /api/metric-evidence/{id}/attach_to_submission/
   {
     "submission_id": 123,
     "apply_ocr_data": "true"
   }
   ```

## Testing OCR Processing

For testing OCR processing without saving to the database, use the Django management command:

```bash
python manage.py test_ocr <evidence_id> [--save] [--format json|pretty]
```

Options:
- `--save`: Save results to the database (default: don't save)
- `--format`: Display format, either 'json' or 'pretty' (default: pretty)

Example:
```bash
# Test processing without saving
python manage.py test_ocr 123

# Test and save results
python manage.py test_ocr 123 --save

# Output as JSON
python manage.py test_ocr 123 --format json
```

## Best Practices for Evidence Management

1. **Always specify the reporting period** when uploading evidence files
2. **Use per-metric uploads** to organize evidence files by the metrics they support
3. **Enable OCR for utility bills** to extract consumption data and period when appropriate
4. **Review OCR results before applying** to ensure accuracy
5. **Explicitly apply OCR data** only when needed - never rely on automatic application
6. **Set appropriate analyzer IDs** for metrics to improve extraction accuracy
7. **Use period matching** by ensuring evidence periods match the reporting periods of submissions

## Technical Implementation Details

1. All evidence is initially created as standalone (without a submission)
2. The `metric_id` is stored in the `ocr_data` field as `intended_metric_id`
3. Evidence is attached to submissions during form completion and batch submission
4. The system never automatically applies OCR data to submissions, only attaches the evidence files
5. Template submission no longer handles evidence attachment as this happens at the form level

## Migration Notes

1. Run migrations to update the database schema:
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```

2. Database changes:
   - The `submission` field on `ESGMetricEvidence` is now nullable to support standalone evidence
   - Field renames for clarity: `ocr_processed` → `is_processed_by_ocr`, `extracted_period` → `period` 