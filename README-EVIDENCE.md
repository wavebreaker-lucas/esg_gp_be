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

### 4. API Endpoints for OCR Integration

Four API endpoints have been added to the `ESGMetricEvidenceViewSet`:

- `upload_with_ocr`: Upload and process a utility bill with OCR
- `ocr_results`: Get OCR results for an evidence file
- `apply_ocr_to_submission`: Apply OCR data to a submission with edit tracking
- `apply_multiple_periods`: Apply multiple billing periods from a utility bill

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

## Best Practices

1. **Create Custom Analyzers**: For best results, create custom Azure Content Understanding analyzers for each utility provider
2. **Assign Specific Analyzers**: Set the `ocr_analyzer_id` field for metrics corresponding to specific utility providers
3. **User Verification**: Always have users verify the extracted data before final submission
4. **Track Edits**: Use the `was_manually_edited` flag to track when users have modified OCR-extracted values

## Technical Implementation

The OCR process uses Azure Content Understanding API to analyze documents. The system:

1. Creates an `AzureContentUnderstandingClient` to communicate with Azure
2. Submits the document for analysis using the appropriate analyzer ID
3. Polls for results until processing is complete
4. Extracts and standardizes the data from the API response
5. Saves the extracted data to the evidence record
6. Provides endpoints for applying the data to submissions

## Error Handling

The system includes comprehensive error handling for:
- Failed OCR processing
- Missing or invalid data in OCR results
- Date and consumption value parsing errors
- Multiple billing periods handling

All errors are logged for troubleshooting, and the raw OCR results are always stored for reference. 