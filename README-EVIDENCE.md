# OCR Utility Bill Processing

## Overview
The ESG Platform includes automated OCR (Optical Character Recognition) processing for utility bills, using the Azure Content Understanding API. This feature extracts consumption data and billing periods from utility bills, reducing manual data entry and improving accuracy.

## JSON Data Approach and Evidence Integration

The ESG Platform now uses a JSON-based approach for all metric submissions, with evidence files linked to specific parts of the JSON data structure using the `reference_path` field.

### JSON Data Structure

All metric submissions now use a single `data` JSON field instead of separate value/text_value/reporting_period fields:

- **Regular metrics** use a simple structure like:
  ```json
  {
    "value": 42.5,
    "comments": "Additional information"
  }
  ```

- **Time-based metrics** use a nested structure like:
  ```json
  {
    "periods": {
      "Q1-2024": { "value": 120.5, "comments": "January-March consumption" },
      "Q2-2024": { "value": 135.2, "comments": "April-June consumption" }
    },
    "annual_total": 255.7
  }
  ```

### Reference Path for Evidence

The `reference_path` field specifies which part of the JSON data structure an evidence file relates to:

```python
class ESGMetricEvidence(models.Model):
    # ... other fields ...
    reference_path = models.CharField(
        max_length=255, 
        null=True, 
        blank=True,
        help_text="JSON path this evidence relates to (e.g., 'periods.Q1-2024')"
    )
```

- For regular metrics, the reference path might be simply `"value"`
- For time-based metrics, it could be `"periods.Q1-2024"` to link to a specific reporting period

### Automatic Evidence Attachment

When submissions are created or updated, the system can automatically attach relevant standalone evidence files:

1. For regular metrics:
   - System finds standalone evidence files for the metric
   - Matches them primarily by layer
   - Attaches them to the submission

2. For time-based metrics:
   - System uses the `reference_path` to match evidence to the right part of the data
   - Checks if the path exists in the submission's JSON data
   - Prioritizes matches with the same layer
   - Perfect matches occur when both reference path and layer match

### Evidence Upload with Reference Path

When uploading evidence, you can specify a reference path:

```
POST /api/metric-evidence/
{
  "file": [file data],
  "metric_id": 123,
  "layer_id": 3,
  "reference_path": "periods.Q1-2024",
  "description": "Q1 2024 utility bill"
}
```

## Evidence Layer Support

The system now includes layer-based organization for evidence files, enabling better categorization and filtering of evidence by organizational units:

### Layer-Based Evidence Management
Evidence files can now be associated with specific organizational layers (subsidiaries, branches, etc.), providing several benefits:
- **Organization by Business Unit**: Evidence files can be categorized by the business unit they belong to
- **Layer-Specific Filtering**: Evidence can be filtered by layer when viewing or processing
- **Better Data Governance**: Clearer ownership and responsibility for evidence files
- **Enhanced Reporting**: Generate reports that properly attribute evidence to organizational structures

### Evidence Upload with Layer Specification
When uploading evidence, users can specify a layer:

```
POST /api/metric-evidence/
{
  "file": [file data],
  "metric_id": 123,
  "layer_id": 3,  // Layer association
  "reference_path": "periods.Q1-2024"
}
```

### Filtering Evidence by Layer
The evidence listing endpoints now support filtering by layer:

```
GET /api/metric-evidence/by_metric/?metric_id=123&layer_id=3
```

- Filters evidence files to show only those associated with the specified layer
- System validates that the user has access to the requested layer
- Unauthorized layer access attempts return appropriate error responses
- Improves navigation and organization in complex multi-layer organizations

For available layers, use the layers endpoint:
```
GET /api/metric-submissions/available_layers/
```

### Layer Defaults and Validation
- If no layer is specified, the system uses a configurable default layer (from `DEFAULT_LAYER_ID` setting)
- The system validates that users have access to the specified layer
- Only authorized users can upload evidence for a given layer
- Evidence files without a specified layer use a fallback mechanism:
  1. Use the layer specified in settings (`DEFAULT_LAYER_ID`)
  2. Use the first available group layer
  3. Continue without a layer if needed

### ESGMetricEvidence Model Enhancement
The evidence model has been updated with layer and reference path fields:

```python
class ESGMetricEvidence(models.Model):
    # Standard evidence fields
    ...
    # Layer association
    layer = models.ForeignKey(
        LayerProfile, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='evidence_files',
        help_text="The layer this evidence is from"
    )
    # Reference path for JSON data
    reference_path = models.CharField(
        max_length=255, 
        null=True, 
        blank=True,
        help_text="JSON path this evidence relates to (e.g., 'periods.Q1-2024')"
    )
    ...
```

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
    
    # Direct metric relationship for standalone evidence
    intended_metric = models.ForeignKey(ESGMetric, on_delete=models.SET_NULL, 
        null=True, blank=True, related_name='intended_evidence',
        help_text="The metric this evidence is intended for, before being attached to a submission")
    
    # OCR-related fields
    is_processed_by_ocr = models.BooleanField(default=False, 
        help_text="Whether OCR processing has been attempted")
    extracted_value = models.FloatField(null=True, blank=True, 
        help_text="Value extracted by OCR")
    period = models.DateField(null=True, blank=True, 
        help_text="User-selected reporting period for the evidence")
    ocr_period = models.DateField(null=True, blank=True, 
        help_text="Reporting period extracted by OCR, separate from user-selected period")
    ocr_data = models.JSONField(null=True, blank=True, 
        help_text="Raw data extracted by OCR")
    was_manually_edited = models.BooleanField(default=False, 
        help_text="Whether the OCR result was manually edited")
    # ... other fields ...
```

The model now includes a new `ocr_period` field that stores the reporting period extracted by OCR processing, separate from the user-selected `period` field. This separation allows for:
1. Clear distinction between user-selected periods and OCR-extracted periods
2. Better handling of cases where OCR might extract a different period than what the user intended
3. More accurate period matching when attaching evidence to submissions

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
   - **Important Request Requirements:**
     - Must use `multipart/form-data` content type
     - File must be included in a field named exactly `file`
     - Do NOT manually set the Content-Type header - let the browser/client handle it
   - Parameters:
     - `file`: The evidence file to upload (required)
     - `metric_id`: (Optional) ID of the metric this evidence relates to; sets the `intended_metric` field for easier association with submissions
     - `reference_path`: (Optional) JSON path this evidence relates to (e.g., 'periods.Q1-2024')
     - `layer_id`: (Optional) ID of the layer this evidence belongs to
     - `description`: (Optional) Description of the evidence
   - Response:
     - Returns the created evidence record with additional metadata
     - Includes `is_standalone: true`
     - Includes `ocr_processing_url` for initiating OCR processing
   - Common Errors:
     - `400 Bad Request`: Check if you're missing the required file field or using incorrect content type
     - `413 Request Entity Too Large`: File exceeds size limit (default 10MB, configurable in settings)
     - `net::ERR_CONNECTION_RESET`: May indicate network issues or proxy limitations

2. **Get Evidence by Metric** (Confirmation Endpoint)
   - `GET /api/metric-evidence/by_metric/?metric_id=123`
   - **Use for user confirmation:** This is the primary endpoint to let users confirm their uploads
   - Returns all evidence files related to a specific metric:
     - Files directly uploaded for this metric (standalone)
     - Files attached to submissions for this metric
   - Response includes:
     - File URLs (with SAS tokens if using Azure storage)
     - Upload dates and times
     - Filename and description
     - OCR processing status and results if available
     - Reference path and layer information
   - Perfect for showing users the evidence they've just uploaded
   - Example response:
     ```json
     [
       {
         "id": 1,
         "file": "https://storage-url.com/esg-evidence/file1.jpg?token=...",
         "filename": "file1.jpg",
         "uploaded_at": "2025-03-24T01:03:25Z",
         "is_standalone": true,
         "description": "",
         "reference_path": "periods.Q1-2024",
         "layer_id": 3,
         "layer_name": "Subsidiary A",
         "is_processed_by_ocr": false,
         "uploaded_by": "user@example.com",
         "metric_id": 123
       }
     ]
     ```

3. **Attach Standalone Evidence to Submission**
   - `POST /api/metric-evidence/{id}/attach_to_submission/`
   - Requires `submission_id` parameter
   - Optional: `apply_ocr_data=true|false` to apply OCR data to the submission
   - Only works for evidence files that aren't already attached to a submission
   - When `apply_ocr_data=true`, displays warnings if overriding existing values

### Batch Submission with Auto Evidence Attachment

When submitting multiple metric values at once, you can automatically attach standalone evidence files:

```
POST /api/metric-submissions/batch_submit/
{
  "assignment_id": 42,
  "submissions": [
    {
      "metric_id": 123,
      "data": {
        "periods": {
          "Q1-2024": { "value": 120.5 },
          "Q2-2024": { "value": 135.2 }
        }
      }
    }
  ],
  "auto_attach_evidence": true
}
```

The `auto_attach_evidence` parameter triggers automatic attachment of relevant standalone evidence files:
- For each submission, the system finds standalone evidence with matching metric ID
- For time-based metrics, it uses the `reference_path` to match with the correct period
- For regular metrics, it primarily matches by layer
- Returns the number of evidence files attached in the response

### OCR-Specific Endpoints

1. **Process OCR**
   - `POST /api/metric-evidence/{id}/process_ocr/`
   - Triggers OCR processing for the evidence file
   - Returns extracted data if successful
   - Response includes:
     - Success message
     - URL to check OCR results
     - Extracted value and period if available

2. **OCR Results**
   - `GET /api/metric-evidence/{id}/ocr_results/`
   - Retrieves the current OCR processing status and results
   - Response includes:
     - Extracted value
     - OCR-extracted period (in MM/YYYY format)
     - Additional periods found in the document
     - Raw OCR data
     - Processing status
   - Example response:
     ```json
     {
       "id": 1,
       "filename": "utility_bill.pdf",
       "extracted_value": 1234.56,
       "period": "06/2023",
       "additional_periods": [
         {
           "period": "05/2023",
           "consumption": 1111.11
         },
         {
           "period": "04/2023",
           "consumption": 999.99
         }
       ],
       "raw_ocr_data": { ... },
       "is_processed_by_ocr": true
     }
     ```

### OCR Processing Flow

1. **Initial Upload**
   - User uploads evidence file through the universal upload endpoint
   - File is stored and a standalone evidence record is created
   - Response includes an `ocr_processing_url` for initiating OCR processing

2. **OCR Processing**
   - Frontend calls the `ocr_processing_url` to start OCR processing
   - Processing runs asynchronously
   - Frontend receives a URL to check OCR results
   - Frontend polls the results URL until processing is complete

3. **Results Review**
   - Frontend retrieves OCR results using the results URL
   - Results include extracted value, period, and any additional periods found
   - User can review and optionally apply the OCR data to a submission

4. **Evidence Attachment**
   - When attaching evidence to a submission, user can choose to apply OCR data
   - System warns if applying OCR data would override existing values
   - Evidence is attached to the submission with or without OCR data

### File Upload Best Practices

1. **Always use FormData for file uploads**
   - Create a FormData object and append your file to it
   - The file field must be named exactly `file`
   - Include other parameters as needed (metric_id, period, etc.)

2. **Let the client handle Content-Type headers**
   - Do not manually set Content-Type when using FormData
   - The browser/client will automatically set the correct headers with boundary

3. **Request structure checklist:**
   - Using multipart/form-data format
   - File is in a field named 'file'
   - All parameters have correct data types (strings for IDs, date in YYYY-MM-DD format)
   - FormData is properly constructed
   - Not manually setting Content-Type header

4. **Troubleshooting uploads:**
   - Use browser dev tools to inspect the actual request format
   - Verify file size is within limits
   - Check for any CORS issues if uploading from different domains
   - Ensure your authentication tokens are included

### Sample Upload Request (Pseudocode)

```
// Create FormData object
var formData = new FormData();

// Add file - MUST be named 'file'
formData.append('file', fileObject);

// Add other parameters
formData.append('metric_id', '123');
formData.append('reference_path', 'periods.Q1-2024');

// Send request - DO NOT set Content-Type header
POST /api/metric-evidence/
Body: formData
```

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

The system uses a smart period matching strategy when attaching evidence:
1. First attempts to match using the reference path
2. If reference path matches, prioritizes evidence with matching layer
3. If no match is found with reference path, falls back to matching by layer and metric

This approach ensures that evidence is attached at the most logical points in the user workflow, where users are actively working with specific forms or metrics.

#### Implementation Architecture

The evidence attachment functionality has been modularized to improve maintainability:

1. **Evidence Upload Service**
   - Handles file storage and initial evidence record creation
   - Supports both local and Azure Blob storage
   - Manages file naming and organization

2. **OCR Processing Service**
   - Handles asynchronous OCR processing
   - Manages Azure Content Understanding API integration
   - Extracts and standardizes data from OCR results

3. **Evidence Attachment Service**
   - Manages the attachment of evidence to submissions
   - Handles reference path matching logic
   - Supports both manual and automatic attachment

4. **Frontend Integration**
   - Provides clear feedback on upload status
   - Manages OCR processing state
   - Handles user interactions for evidence management

## OCR Processing Flow

### Upload with OCR Processing
1. Upload evidence for a specific metric with OCR enabled:
   ```
   POST /api/metric-evidence/
   {
     "file": [file data],
     "metric_id": 456,
     "reference_path": "periods.Q1-2024",
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

1. **Always specify the reference path** when uploading evidence files
2. **Use per-metric uploads** to organize evidence files by the metrics they support
3. **Enable OCR for utility bills** to extract consumption data and period when appropriate
4. **Review OCR results before applying** to ensure accuracy
5. **Explicitly apply OCR data** only when needed - never rely on automatic application
6. **Set appropriate analyzer IDs** for metrics to improve extraction accuracy
7. **Use reference path matching** by ensuring evidence reference paths match the JSON data structure of submissions

## Technical Implementation Details

1. All evidence is initially created as standalone (without a submission)
2. Evidence is attached to submissions during form completion and batch submission
3. The system never automatically applies OCR data to submissions, only attaches the evidence files
4. Template submission no longer handles evidence attachment as this happens at the form level

## Migration Notes

1. Run migrations to update the database schema:
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```

2. Database changes:
   - The `submission` field on `ESGMetricEvidence` is now nullable to support standalone evidence
   - Field renames for clarity: `ocr_processed` → `is_processed_by_ocr`, `extracted_period` → `period` 

## Evidence-Metric Association

### Direct Metric Association

Evidence files can be directly associated with metrics in two ways:

1. **When attached to a submission**: Evidence inherits the metric association from the submission it's attached to.

2. **Standalone evidence (new approach)**: Evidence can be directly associated with a metric via the `intended_metric` field, making it easier and more reliable to find and attach evidence to submissions later.

Before the standalone evidence is attached to a submission, the system uses the `intended_metric` field to identify which metric the evidence belongs to. This replaces the previous approach of storing the metric ID in the `ocr_data` JSON field.

### Benefits of the New Approach

- **Explicit relationship**: Direct database relationship instead of storing in JSON
- **Better performance**: Proper database indexing for faster queries
- **Improved reliability**: No need to parse or search within JSON content
- **Cleaner model semantics**: Separates relationship data from OCR processing data

### Automatic Evidence Attachment

The system automatically attaches standalone evidence files to submissions when:

1. Users submit individual metrics via `batch_submit` with `auto_attach_evidence=true`
