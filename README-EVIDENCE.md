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
     - `submission_id`: (Optional) ID of the submission to attach to
     - `metric_id`: (Optional) ID of the metric this evidence relates to
     - `enable_ocr_processing`: (Optional) Set to 'true' to enable OCR
     - `description`: (Optional) Description of the evidence
   - Response:
     - Returns the created evidence record with additional metadata
     - Includes `is_standalone: true|false` to indicate if it's attached to a submission
     - Includes `ocr_processing_url` if OCR processing is enabled

2. **Attach Standalone Evidence to Submission**
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

3. **Apply OCR Data to Submission**
   - `POST /api/metric-evidence/{id}/apply_ocr_to_submission/`
   - Applies OCR-extracted data to the linked submission
   - Optional parameters to override extracted values

## Upload and Processing Workflows

### Standard Workflow
1. Upload evidence with `submission_id` to attach directly to a submission:
   ```
   POST /api/metric-evidence/
   {
     "file": [file data],
     "submission_id": 123
   }
   ```

### OCR Workflow with Existing Submission
1. Upload evidence with OCR enabled and attach to submission:
   ```
   POST /api/metric-evidence/
   {
     "file": [file data],
     "submission_id": 123,
     "enable_ocr_processing": "true"
   }
   ```
2. Process OCR using the returned processing URL:
   ```
   POST /api/metric-evidence/{id}/process_ocr/
   ```
3. Review OCR results:
   ```
   GET /api/metric-evidence/{id}/ocr_results/
   ```

### OCR-First Workflow (Standalone Evidence)
1. Upload evidence as standalone with OCR enabled:
   ```
   POST /api/metric-evidence/
   {
     "file": [file data],
     "metric_id": 456,  # Optional but helpful for OCR analyzer selection
     "enable_ocr_processing": "true"
   }
   ```
2. Process OCR:
   ```
   POST /api/metric-evidence/{id}/process_ocr/
   ```
3. Review OCR results:
   ```
   GET /api/metric-evidence/{id}/ocr_results/
   ```
4. Create a submission with the extracted data (frontend workflow)
5. Attach evidence to the submission:
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

1. **Use the universal upload endpoint** for all evidence file uploads, with or without a submission.
2. **Process OCR** before attaching to submissions when possible to allow for review.
3. **Set appropriate analyzer IDs** for metrics to improve extraction accuracy.
4. **Review OCR results** before applying to submissions.
5. **Track manual edits** to OCR data for audit purposes.

## Technical Implementation Details

1. The OCR processing flow checks for `enable_ocr_processing=True` before attempting OCR.
2. For standalone evidence, the `ocr_data` field stores the intended metric ID.
3. When processing OCR, the system:
   - Uses the submission's metric analyzer ID if available
   - For standalone evidence, looks up the metric by ID stored in ocr_data
   - Falls back to the default analyzer
4. The OCR analyzer may extract multiple billing periods, which are returned in the API response.

## Migration Notes

1. Run migrations to update the database schema:
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```

2. Database changes:
   - New field `submission` on `ESGMetricEvidence` is now nullable
   - Field renames: `ocr_processed` → `is_processed_by_ocr`, `extracted_period` → `period` 