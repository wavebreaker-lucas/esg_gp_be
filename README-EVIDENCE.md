# OCR Utility Bill Processing

## Overview

The ESG Platform now includes automated OCR (Optical Character Recognition) processing for utility bills using Azure Content Understanding API. This feature extracts consumption data and billing periods from uploaded utility bills, making data entry more efficient and accurate.

## Key Components

### 1. ESGMetric Model Enhancement

The `ESGMetric` model has been enhanced with a custom analyzer ID field:

```python
ocr_analyzer_id = models.CharField(
    max_length=100, 
    blank=True, 
    null=True,
    help_text="Custom analyzer ID for OCR processing of this metric's evidence"
)
```

This allows specific Azure Content Understanding analyzers to be assigned to different metrics, providing tailored data extraction for various utility bill formats.

### 2. ESGMetricEvidence Model OCR Fields

The `ESGMetricEvidence` model includes fields for OCR processing:

```python
enable_ocr_processing = models.BooleanField(default=False, 
    help_text="User option to enable OCR data extraction for this evidence file")
ocr_processed = models.BooleanField(default=False, 
    help_text="Whether OCR processing has been attempted")
extracted_value = models.FloatField(null=True, blank=True, 
    help_text="Value extracted by OCR")
extracted_period = models.DateField(null=True, blank=True, 
    help_text="Reporting period extracted by OCR")
ocr_data = models.JSONField(null=True, blank=True, 
    help_text="Raw data extracted by OCR")
was_manually_edited = models.BooleanField(default=False, 
    help_text="Whether the OCR result was manually edited")
edited_at = models.DateTimeField(null=True, blank=True, 
    help_text="When the OCR result was edited")
edited_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, 
    null=True, blank=True, related_name='edited_evidence', 
    help_text="Who edited the OCR result")
```

These fields track the OCR processing status and store extracted data.

### 3. UtilityBillAnalyzer Service

The `UtilityBillAnalyzer` class in `data_management/services/bill_analyzer.py` is responsible for:

- Processing utility bill evidence files with Azure OCR
- Using metric-specific analyzers based on the `ocr_analyzer_id` field
- Extracting consumption values and billing periods
- Standardizing extracted data
- Handling multiple billing periods for time-based metrics
- Saving extracted data back to the `ESGMetricEvidence` record

### 4. API Endpoints for Evidence Management

#### Standard Evidence Endpoints

- `GET /api/metric-evidence/`: List all accessible evidence files
- `POST /api/metric-evidence/`: Upload evidence for a metric submission
- `GET /api/metric-evidence/{id}/`: Get details of a specific evidence file
- `DELETE /api/metric-evidence/{id}/`: Delete an evidence file
- `GET /api/metric-evidence/by_submission/?submission_id={id}`: Get all evidence for a submission

#### OCR-Specific Endpoints

- `POST /api/metric-evidence/upload_with_ocr/`: Upload and process a utility bill with OCR
- `GET /api/metric-evidence/{id}/ocr_results/`: Get OCR results for an evidence file
- `POST /api/metric-evidence/{id}/apply_ocr_to_submission/`: Apply OCR data to a submission with edit tracking
- `POST /api/metric-evidence/{id}/apply_multiple_periods/`: Apply multiple billing periods from a utility bill

## Usage

### Setting Custom Analyzer IDs

#### Option 1: Through Django Admin
1. Navigate to Admin > Data Management > ESG Metrics
2. Edit the desired metric
3. Set the "OCR analyzer ID" field
4. Save changes

#### Option 2: Programmatically
```python
from data_management.models import ESGMetric

# Update a specific metric
metric = ESGMetric.objects.get(id=5)  # CLP Electricity consumption
metric.ocr_analyzer_id = "clp-analyzer"
metric.save()

# Update multiple metrics
ESGMetric.objects.filter(name__contains="Electricity").update(
    ocr_analyzer_id="electricity-analyzer"
)
```

### Processing Flow

1. **Upload**: User uploads a file and enables OCR processing
2. **Processing**: The system processes the file with the appropriate analyzer
3. **Extraction**: Consumption values and billing periods are extracted
4. **Application**: The data can be applied to metric submissions
5. **Verification**: Users can verify and edit the extracted data if needed

### Handling Multiple Billing Periods

For utility bills that contain consumption history (like electricity bills with multiple months):

1. The system extracts all billing periods and consumption values
2. These can be applied to create multiple submissions with different reporting periods
3. This is particularly useful for metrics that require monthly or quarterly reporting

#### How Multiple Periods Work

When a utility bill contains data for multiple billing periods:

1. The OCR system looks for a field called "MultipleBillingPeriods" in the analyzer output
2. It parses this field as a JSON list of periods, each with a date and consumption value
3. For database storage, only the first period is automatically applied to the `extracted_value` and `extracted_period` fields
4. All periods are returned in the API response in the `all_periods` field
5. Users can selectively apply specific periods to different submissions using the `apply_multiple_periods` endpoint

This means you can upload a single utility bill file (e.g., a quarterly or annual statement) once, and then apply different billing periods to the appropriate monthly submissions.

#### Evidence-Submission Relationship

The `ESGMetricEvidence` model links to a specific `ESGMetricSubmission` via a foreign key:

```python
submission = models.ForeignKey(ESGMetricSubmission, on_delete=models.CASCADE, related_name='evidence')
```

This means:
- For single-period bills: One evidence file is linked to one submission record
- For multi-period bills: Users have two options:
  1. Upload separate bills for each period (one evidence per submission)
  2. Upload one bill with multiple periods and selectively apply periods to different submissions

The second approach is more efficient as it requires only one file upload and OCR processing operation.

## Best Practices

### Evidence Management

1. **File Organization**: 
   - Use descriptive filenames for utility bills (e.g., "clp_electricity_jan2023.pdf")
   - Consider standardizing naming conventions for easier identification

2. **OCR Processing**:
   - Enable OCR processing only for structured documents like utility bills
   - For unstructured documents, manual data entry may be more reliable

3. **Evidence Types**:
   - Utility bills: Enable OCR processing for automated data extraction
   - Reports and certificates: Use standard file uploads without OCR
   - Raw data files: Consider custom import tools instead of OCR

4. **Custom Analyzers**: For best results, create custom Azure Content Understanding analyzers for each utility provider

5. **User Verification**: Always have users verify the extracted data before final submission

6. **Track Edits**: Use the `was_manually_edited` flag to track when users have modified OCR-extracted values

### For Time-Based Metrics

1. **Multiple Periods**:
   - For metrics requiring monthly data, upload quarterly bills that contain multiple months
   - Use the `apply_multiple_periods` endpoint to create separate submissions for each month
   - This reduces the number of file uploads needed

2. **Period Verification**:
   - Ensure the extracted periods match your reporting periods
   - The system attempts to standardize dates to MM/YYYY format
   - Manual verification is still recommended for critical data

3. **Single vs. Multiple Uploads**:
   - Single upload with multiple periods: More efficient, requires less storage, one OCR operation
   - Multiple individual uploads: Simpler tracking, but requires more storage and processing

## Technical Implementation

The OCR process uses Azure Content Understanding API to analyze documents. The system:

1. Creates an `AzureContentUnderstandingClient` to communicate with Azure
2. Submits the document for analysis using the appropriate analyzer ID
3. Polls for results until processing is complete
4. Extracts and standardizes the data from the API response
5. Saves the extracted data to the evidence record
6. Provides endpoints for applying the data to submissions

### Multiple Period Extraction Logic

The core logic for extracting multiple billing periods is in the `_extract_data_from_analyzer` method:

```python
# Try to extract multiple billing periods
if "MultipleBillingPeriods" in fields and "valueString" in fields["MultipleBillingPeriods"]:
    multiple_periods_str = fields["MultipleBillingPeriods"]["valueString"]
    
    # Try to parse as JSON
    try:
        multiple_periods = json.loads(multiple_periods_str)
        if isinstance(multiple_periods, list) and multiple_periods:
            standardized_data = []
            for period in multiple_periods:
                # Process each period and standardize the format
                # Extract period date and consumption value
                # Add to standardized_data list
            
            if standardized_data:
                result['periods'] = standardized_data
```

This extracts a list of periods from the OCR result, each with a standardized period date and consumption value.

## API Endpoints

### Standard Evidence Management

#### 1. List Evidence Files

```
GET /api/metric-evidence/
```

Returns a list of all evidence files the user has access to. Can be filtered by various parameters.

Parameters:
- `submission_id` (optional): Filter by submission ID
- `uploaded_by` (optional): Filter by uploader ID

Response:
```json
[
  {
    "id": 1,
    "file": "/media/esg_evidence/2023/04/electricity_bill.pdf",
    "filename": "electricity_bill.pdf",
    "file_type": "application/pdf",
    "uploaded_by": 3,
    "uploaded_by_name": "john.doe@example.com",
    "uploaded_at": "2023-04-15T10:35:00Z",
    "description": "Electricity bill for April 2023",
    "enable_ocr_processing": true,
    "ocr_processed": true,
    "extracted_value": 120.5,
    "extracted_period": "2023-04-30"
  },
  {
    "id": 2,
    "file": "/media/esg_evidence/2023/05/water_bill.pdf",
    "filename": "water_bill.pdf",
    "file_type": "application/pdf",
    "uploaded_by": 3,
    "uploaded_by_name": "john.doe@example.com",
    "uploaded_at": "2023-05-15T10:35:00Z",
    "description": "Water bill for May 2023",
    "enable_ocr_processing": false,
    "ocr_processed": false,
    "extracted_value": null,
    "extracted_period": null
  }
]
```

#### 2. Upload Evidence File (Standard)

```
POST /api/metric-evidence/
```

Uploads an evidence file for a metric submission without OCR processing.

Parameters:
- `submission_id`: ID of the metric submission
- `file`: The file to upload
- `description` (optional): Description of the evidence

Response:
```json
{
  "id": 3,
  "file": "/media/esg_evidence/2023/06/gas_bill.pdf",
  "filename": "gas_bill.pdf",
  "file_type": "application/pdf",
  "uploaded_by": 3,
  "uploaded_by_name": "john.doe@example.com",
  "uploaded_at": "2023-06-15T10:35:00Z",
  "description": "Gas bill for June 2023",
  "enable_ocr_processing": false,
  "ocr_processed": false
}
```

#### 3. Get Evidence Details

```
GET /api/metric-evidence/{id}/
```

Returns details for a specific evidence file.

Response:
```json
{
  "id": 1,
  "file": "/media/esg_evidence/2023/04/electricity_bill.pdf",
  "filename": "electricity_bill.pdf",
  "file_type": "application/pdf",
  "uploaded_by": 3,
  "uploaded_by_name": "john.doe@example.com",
  "uploaded_at": "2023-04-15T10:35:00Z",
  "description": "Electricity bill for April 2023",
  "submission": {
    "id": 1,
    "metric": {
      "id": 5,
      "name": "Electricity consumption (CLP)",
      "unit_type": "kWh"
    }
  },
  "enable_ocr_processing": true,
  "ocr_processed": true,
  "extracted_value": 120.5,
  "extracted_period": "2023-04-30",
  "was_manually_edited": false
}
```

#### 4. Delete Evidence File

```
DELETE /api/metric-evidence/{id}/
```

Deletes an evidence file. Returns a 204 No Content response on success.

#### 5. Get Evidence Files by Submission

```
GET /api/metric-evidence/by_submission/?submission_id={id}
```

Returns all evidence files for a specific submission.

Response:
```json
[
  {
    "id": 1,
    "file": "/media/esg_evidence/2023/04/electricity_bill.pdf",
    "filename": "electricity_bill.pdf",
    "file_type": "application/pdf",
    "uploaded_by": 3,
    "uploaded_by_name": "john.doe@example.com",
    "uploaded_at": "2023-04-15T10:35:00Z",
    "description": "Electricity bill for April 2023",
    "enable_ocr_processing": true,
    "ocr_processed": true,
    "extracted_value": 120.5,
    "extracted_period": "2023-04-30"
  }
]
```

### OCR-Specific Endpoints

#### 1. Upload with OCR

```
POST /api/metric-evidence/upload_with_ocr/
```

Parameters:
- `submission_id`: ID of the metric submission
- `file`: The file to upload
- `enable_ocr_processing`: Boolean to enable OCR (default: true)
- `description`: Optional description

Response:
```json
{
  "id": 1,
  "file": "/media/evidence/bill.pdf",
  "ocr_status": "processing",
  "message": "File uploaded successfully. OCR processing started."
}
```

#### 2. Get OCR Results

```
GET /api/metric-evidence/{id}/ocr_results/
```

Response:
```json
{
  "status": "success",
  "value": 120.5,
  "period": "2023-01-31",
  "all_periods": [
    {"period": "01/2023", "consumption": 120.5},
    {"period": "02/2023", "consumption": 115.2},
    {"period": "03/2023", "consumption": 130.8}
  ]
}
```

#### 3. Apply OCR Data to Submission

```
POST /api/metric-evidence/{id}/apply_ocr_to_submission/
```

Parameters:
- `value`: Optional value to override extracted value
- `reporting_period`: Optional period to override extracted period

Response:
```json
{
  "submission_id": 1,
  "metric_id": 5,
  "value": 120.5,
  "reporting_period": "2023-01-31",
  "was_manually_edited": false,
  "message": "OCR data applied successfully"
}
```

#### 4. Apply Multiple Periods

```
POST /api/metric-evidence/{id}/apply_multiple_periods/
```

Parameters:
- `periods`: List of periods to apply with submission details
  ```json
  [
    {
      "period_index": 0,
      "reporting_period": "2023-01-31",
      "override_value": null
    },
    {
      "period_index": 1,
      "reporting_period": "2023-02-28",
      "override_value": 116.0
    }
  ]
  ```

Response:
```json
{
  "message": "Multiple periods applied successfully",
  "results": [
    {
      "submission_id": 1,
      "metric_id": 5,
      "value": 120.5,
      "reporting_period": "2023-01-31",
      "was_manually_edited": false
    },
    {
      "submission_id": 2,
      "metric_id": 5,
      "value": 116.0,
      "reporting_period": "2023-02-28",
      "was_manually_edited": true
    }
  ]
}
```

## Error Handling

The system includes comprehensive error handling for:
- Failed OCR processing
- Missing or invalid data in OCR results
- Date and consumption value parsing errors
- Multiple billing periods handling

All errors are logged for troubleshooting, and the raw OCR results are always stored for reference.

## User Experience Considerations

1. **Upload Process**:
   - Present a clear option to enable OCR processing for appropriate file types
   - Show processing status and feedback during OCR operations

2. **Reviewing OCR Results**:
   - Display extracted data clearly with original values
   - Allow users to verify and correct extracted data before applying
   - For multi-period bills, show all extracted periods with a selection mechanism

3. **Time-Based Reporting**:
   - For metrics with `requires_time_reporting=True`, show calendar controls
   - Integrate OCR period selection with reporting period selection
   - When applying multiple periods, show the mapping between extracted periods and reporting periods

4. **Error Handling**:
   - Provide clear error messages when OCR fails or extracts incomplete data
   - Offer fallback to manual data entry when needed
   - Log OCR processing attempts for troubleshooting 