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
4. When a form is submitted, evidence files are automatically attached to the appropriate submissions based on the period

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
2. Users submit a complete template via `submit_template` endpoint

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
```

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
   
4. When the form is submitted, the system will:
   - Automatically attach the evidence to the appropriate submission based on matching periods
   - Apply OCR data to the submission value if not already set

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
3. **Enable OCR for utility bills** to automatically extract consumption data and period
4. **Let the system handle attachments** during form submission to reduce manual steps
5. **Set appropriate analyzer IDs** for metrics to improve extraction accuracy
6. **Review OCR results** before submitting forms
7. **Use period matching** by ensuring evidence periods match the reporting periods of submissions

## Technical Implementation Details

1. All evidence is initially created as standalone (without a submission)
2. The `metric_id` is stored in the `ocr_data` field as `intended_metric_id`
3. During form submission, evidence is matched to submissions by:
   - First matching by period (if available)
   - Falling back to first submission for that metric if no period match
4. OCR data can be automatically applied to submissions during attachment
5. The OCR analyzer is selected based on:
   - The metric's `ocr_analyzer_id` for standalone evidence
   - The submission's metric analyzer ID for attached evidence
   - A default analyzer as fallback

## Migration Notes

1. Run migrations to update the database schema:
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```

2. Database changes:
   - The `submission` field on `ESGMetricEvidence` is now nullable to support standalone evidence
   - Field renames for clarity: `ocr_processed` → `is_processed_by_ocr`, `extracted_period` → `period` 