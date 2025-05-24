# OCR Utility Bill Processing

## Overview
The ESG Platform includes automated OCR (Optical Character Recognition) processing for utility bills, using the Azure Content Understanding API. This feature extracts consumption data and billing periods from utility bills, reducing manual data entry and improving accuracy.

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
  file: [file data],
  metric_id: 123, // BaseESGMetric ID
  layer_id: 3,  // Layer association
  period: "2024-06-30"
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
The evidence model has been updated with a layer field:

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
    ...
```

## Key Components

### Polymorphic Metric Enhancements (`BaseESGMetric`)
- **Custom Analyzer ID**: Each polymorphic metric (`BaseESGMetric`) can have a specific `ocr_analyzer_id` to use a custom Azure Content Understanding analyzer tailored for specific utility bill formats.
  ```python
  class BaseESGMetric(PolymorphicModel):
      # ... other fields ...
      ocr_analyzer_id = models.CharField(
          max_length=100, 
          blank=True, 
          null=True,
          help_text="Custom Azure Form Recognizer model ID for evidence processing (if applicable)"
      )
  ```

### ESGMetricEvidence Model
The `ESGMetricEvidence` model has been enhanced with several OCR-related fields:
```python
class ESGMetricEvidence(models.Model):
    # Standard evidence fields
    # NOTE: The direct submission ForeignKey has been removed.
    # Evidence is now linked via metadata (intended_metric, layer, period, source_identifier).
    file = models.FileField(upload_to='esg_evidence/%Y/%m/')
    filename = models.CharField(max_length=255)
    file_type = models.CharField(max_length=50) # Added field
    uploaded_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    description = models.TextField(blank=True)
    layer = models.ForeignKey(LayerProfile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='evidence_files',
        help_text="The layer this evidence is from"
    )
    source_identifier = models.CharField( # Added field
        max_length=100,
        blank=True,
        null=True,
        help_text="Identifier for the source of this evidence (e.g., facility name)"
    )

    # Direct metric relationship for standalone evidence
    intended_metric = models.ForeignKey(BaseESGMetric, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='intended_evidence',
        help_text="The metric this evidence is intended for")

    # OCR-related fields
    enable_ocr_processing = models.BooleanField(default=True, help_text="Whether OCR processing is available for this evidence file") # Added field
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
    edited_at = models.DateTimeField(null=True, blank=True, help_text="When the OCR result was edited") # Added field
    edited_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='edited_evidence', help_text="Who edited the OCR result") # Added field
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

## File Storage Approach (Current)

All evidence files uploaded to the ESG Platform are now stored **exclusively in Azure Blob Storage**. There is no fallback to local or temporary storage. This ensures:
- High durability and availability of evidence files
- No risk of file loss during app restarts or redeployments
- Centralized, secure, and scalable storage for all uploads

### How It Works
- When a user uploads evidence (e.g., via `POST /api/metric-evidence/`), the file is saved directly to Azure Blob Storage in the configured container (e.g., `esg-evidence`).
- The Django backend uses the Azure Storage account name, account key, and container name, all provided via environment variables.
- The storage backend generates secure, time-limited URLs for file access using SAS tokens.

### Required Environment Variables
To enable Azure Blob Storage, the following environment variables **must** be set in your Azure App Service configuration:

- `AZURE_STORAGE_ACCOUNT_NAME` — The name of your Azure Storage account (e.g., `esgplatformstore`)
- `AZURE_STORAGE_ACCOUNT_KEY` — The full access key for your storage account (not a connection string or SAS token)
- `AZURE_STORAGE_CONTAINER` — The name of the blob container for evidence files (e.g., `esg-evidence`)

**Note:**
- The account key must be kept secure and up to date. If you rotate keys, update the app settings and restart the service.
- No evidence files are stored on the local filesystem or `/tmp` directories.

### Security
- Anonymous access to the blob container is disabled.
- All file access is via secure, time-limited SAS URLs generated by the backend.
- Only authenticated users can upload or retrieve evidence files through the API.

### Troubleshooting
- If evidence files do not appear in Azure Blob Storage, check that all environment variables are set correctly and that the account key is valid.
- Authentication errors (e.g., `AuthenticationFailed`) almost always mean the account key is missing, incorrect, or expired.
- After updating environment variables, always restart the App Service.

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
     - `metric_id`: (Optional) ID of the *BaseESGMetric* this evidence relates to; sets the `intended_metric` field for easier association with submissions
     - `period`: (Optional) Reporting period in YYYY-MM-DD format
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
   - Returns all evidence files related to a specific metric (using `intended_metric` or `submission.metric`):
     - Files directly uploaded for this metric (standalone)
     - Files attached to submissions for this metric
   - Response includes:
     - File URLs (with SAS tokens if using Azure storage)
     - Upload dates and times
     - Filename and description
     - OCR processing status and results if available
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
         "is_processed_by_ocr": false,
         "uploaded_by": "user@example.com",
         "intended_metric": 123 // BaseESGMetric ID
       }
     ]
     ```

3. **Get Evidence by Submission** (Finding Related Evidence)
   - `GET /api/metric-evidence/by_submission/?submission_id=456`
   - Finds evidence relevant to a specific submission based on matching metadata:
     - `intended_metric` must match `submission.metric`
     - `layer` must match `submission.layer`
     - `period` (if available) must match `submission.reporting_period`
     - `source_identifier` (if available) must match `submission.source_identifier`
   - This endpoint is used to display relevant supporting documents for a given submission input.

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

3. **Apply OCR Data to a Submission**
   - `POST /api/metric-evidence/{id}/apply_ocr/`
   - Applies the OCR results (`extracted_value`, `period`/`ocr_period`) from a specific evidence file (`{id}`) to a *different* target submission.
   - Request Body Parameters:
     - `submission_id`: The ID of the `ESGMetricSubmission` record to apply the data to (required).
   - Functionality:
     - Retrieves the target `ESGMetricSubmission` using the provided `submission_id`.
     - Checks if the evidence file (`{id}`) has been processed by OCR and has an `extracted_value`.
     - Checks if the target submission's metric (`submission.metric.get_real_instance()`) is a non-text `BasicMetric`.
     - If compatible:
       - Finds or creates the associated `BasicMetricData` record for the target submission.
       - Updates `BasicMetricData.value_numeric` with `evidence.extracted_value`.
       - Updates the target `submission.reporting_period` if `evidence.period` or `evidence.ocr_period` is available and differs from the submission's current period.
       - Returns warnings if overriding existing submission values or if the metric type is incompatible.
     - Returns a response detailing success/failure, updated values, and any warnings.
   - **Key Change**: This endpoint *uses* data from one evidence record to potentially *update* a separate submission record and its associated data model (`BasicMetricData`). It does not create a direct link between the evidence and the submission.

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
   - User can review the extracted data.

4. **Applying OCR Data (Manual Step)**
   - If the user wants to apply the extracted OCR data to a specific submission input:
     - The frontend calls the `apply_ocr` endpoint (`POST /api/metric-evidence/{evidence_id}/apply_ocr/`).
     - The request **must** include the `submission_id` of the target submission record.
     - The system checks metric compatibility (must be non-text `BasicMetric` on the *target submission*).
     - The system warns if applying OCR data would override existing values in the target submission's data.
     - The target submission's specific data record (`BasicMetricData`) is updated if OCR data is applied and compatible. The evidence record itself remains unchanged regarding its link to submissions.

## Direct Vehicle Linking

The system now supports direct linking between evidence files and specific vehicles, providing a more precise way to associate supporting documentation with vehicle records.

### ESGMetricEvidence Model Enhancement

The evidence model has been updated with a target_vehicle field:

```python
class ESGMetricEvidence(models.Model):
    # Other fields...
    
    # NEW: Direct link to a specific vehicle
    target_vehicle = models.ForeignKey(
        'data_management.VehicleRecord',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='evidence_files',
        help_text="The specific vehicle this evidence relates to, if any."
    )
```

### Uploading Evidence with Vehicle Association

When uploading evidence, users can specify a target vehicle:

```
POST /api/metric-evidence/
{
  file: [file data],
  metric_id: 123,
  layer_id: 3,
  period: "2024-06-30",
  target_vehicle_id: 45  // ID of the specific VehicleRecord
}
```

### Retrieving Vehicle-Specific Evidence

Find evidence files linked to a specific vehicle:

```
GET /api/metric-evidence/by_vehicle/?vehicle_id=45&period=2024-06-30
```

- Retrieves evidence files directly linked to the specified vehicle
- Optional period parameter to filter by reporting period
- Returns 404 if the vehicle doesn't exist
- Returns 400 if vehicle_id is not provided

### Enhanced Evidence Finding Logic

The `find_relevant_evidence()` function now checks for vehicle records when working with VehicleTrackingMetric:

1. Identifies when a submission is for a VehicleTrackingMetric
2. Retrieves all vehicles associated with the submission
3. Includes evidence linked to any of these vehicles in the results
4. Automatically merges vehicle-specific evidence with standard metadata-matching evidence

### Benefits of Direct Vehicle Linking

- **Precise Documentation**: Link receipts, registration documents, or maintenance records directly to specific vehicles
- **Improved Traceability**: Clear audit trail connecting evidence to individual assets
- **Better User Experience**: Users can see all evidence for a specific vehicle in one place
- **Enhanced Data Integrity**: Maintain vehicle-document relationships even if submission details change

### Admin Interface Enhancements

The admin interface has been updated to support the new vehicle linking:

- Added vehicle information display in the evidence list view
- Added vehicle-based filters and search capabilities
- Improved the evidence detail view to show associated vehicle information
- Added raw_id_fields for easier vehicle selection

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

1. **Always specify the reporting period (`period`)** when uploading evidence files.
2. **Always specify the intended metric (`metric_id`)** when uploading to set the `intended_metric` field correctly.
3. **Specify the correct `layer_id`** for organizational context.
4. **Use `source_identifier`** when applicable for the metric type.
5. **Enable OCR for utility bills** where appropriate.
6. **Review OCR results** for accuracy.
7. **Explicitly apply OCR data to specific submissions** using the `apply_ocr` endpoint when needed. Never assume automatic application of OCR *values* to submission *data*.
8. **Set appropriate `ocr_analyzer_id`** on `BaseESGMetric` instances for custom OCR models.

## Technical Implementation Details

1. All evidence is created standalone, linked to a metric via `intended_metric` and associated with context via `layer`, `period`, `source_identifier`.
2. Evidence relevant to a submission is found dynamically using metadata matching. There is no direct ForeignKey link.
3. The system never automatically applies OCR *values* to submission data models. Applying OCR data requires an explicit call to the `apply_ocr` endpoint, specifying the target `submission_id`.

## Migration Notes

1. Run migrations to update the database schema:
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```

2. Database changes included:
   - The `submission` ForeignKey on `ESGMetricEvidence` was removed.
   - Fields like `intended_metric` (pointing to `BaseESGMetric`), `layer`, and `source_identifier` are used for context.
   - Various OCR and metadata fields were added or updated.

## Evidence-Metric Association

### Metadata-Based Association

Evidence files are associated with metrics and submission context using metadata fields on the `ESGMetricEvidence` model:

1. **`intended_metric`**: A ForeignKey to `BaseESGMetric` directly linking the evidence to the metric it's intended for.
2. **`layer`**: ForeignKey to `LayerProfile` indicating the organizational unit.
3. **`period` / `ocr_period`**: Date fields indicating the reporting period.
4. **`source_identifier`**: A string for further context (e.g., facility name, meter ID).

When displaying evidence for a submission or finding supporting documents, the system queries `ESGMetricEvidence` filtering by these fields based on the corresponding fields in the `ESGMetricSubmission` record.

### Benefits of the New Approach

- **Decoupled models**: Evidence and Submissions are not directly tied, increasing flexibility.
- **Clearer context**: Metadata fields provide explicit context for each evidence file.
- **Improved performance**: Filtering on indexed metadata fields is generally efficient.
- **Reliability**: Matching is based on defined data attributes.

### Finding Relevant Evidence

The system finds relevant evidence dynamically when needed:

1. Via the `find_relevant_evidence(submission)` service function.
2. Via API endpoints like `GET /api/metric-evidence/by_submission/?submission_id=...`
3. Via API endpoints like `GET /api/batch-evidence/?submission_ids=...`

These mechanisms query the `ESGMetricEvidence` table using the `metric`, `layer`, `reporting_period`, and `source_identifier` from the submission(s) as filter criteria.
