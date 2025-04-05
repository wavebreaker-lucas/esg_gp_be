from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from accounts.models import CustomUser, LayerProfile
from django.utils import timezone # Import timezone

class ESGFormCategory(models.Model):
    """Categories for ESG disclosure forms (Environmental, Social, Governance)"""
    name = models.CharField(max_length=50)
    code = models.CharField(max_length=20, unique=True)  # e.g., 'environmental', 'social'
    icon = models.CharField(max_length=50, blank=True)  # e.g., 'leaf', 'users'
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']
        verbose_name = "ESG Form Category"
        verbose_name_plural = "ESG Form Categories"

    def __str__(self):
        return self.name

class ESGForm(models.Model):
    """Predefined HKEX ESG disclosure forms"""
    category = models.ForeignKey(ESGFormCategory, on_delete=models.CASCADE, related_name='forms')
    code = models.CharField(max_length=20, unique=True)  # e.g., 'HKEX-A1', 'HKEX-B2'
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['category', 'order']
        indexes = [
            models.Index(fields=['code']),
            models.Index(fields=['is_active']),
        ]

    def __str__(self):
        return f"{self.code}: {self.name}"

class Template(models.Model):
    """ESG disclosure templates created from forms"""
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    version = models.PositiveIntegerField(default=1)
    created_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True)
    selected_forms = models.ManyToManyField(ESGForm, through='TemplateFormSelection')

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['is_active']),
        ]

    def __str__(self):
        return f"{self.name} v{self.version}"

class TemplateFormSelection(models.Model):
    """Links templates to selected forms with region configuration"""
    template = models.ForeignKey(Template, on_delete=models.CASCADE)
    form = models.ForeignKey(ESGForm, on_delete=models.CASCADE)
    regions = models.JSONField(default=list)  # List of regions this form applies to
    order = models.PositiveIntegerField(default=0)
    is_completed = models.BooleanField(default=False)  # Track if this form is completed
    completed_at = models.DateTimeField(null=True, blank=True)  # When the form was completed
    completed_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='completed_forms')  # Who completed the form

    class Meta:
        ordering = ['template', 'order']
        unique_together = ['template', 'form']

class TemplateAssignment(models.Model):
    """Assignment of templates to layers (groups, subsidiaries, branches)"""
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('IN_PROGRESS', 'In Progress'),
        ('SUBMITTED', 'Submitted'),
        ('VERIFIED', 'Verified'),
        ('REJECTED', 'Rejected')
    ]

    template = models.ForeignKey(Template, on_delete=models.CASCADE)
    layer = models.ForeignKey(LayerProfile, on_delete=models.CASCADE)
    assigned_to = models.ForeignKey(CustomUser, on_delete=models.CASCADE, null=True, blank=True)
    assigned_at = models.DateTimeField(auto_now_add=True)
    due_date = models.DateField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    reporting_period_start = models.DateField()
    reporting_period_end = models.DateField()
    reporting_year = models.PositiveIntegerField(default=2025, help_text="The year this reporting data represents (e.g., 2024)")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')

    class Meta:
        indexes = [
            models.Index(fields=['template', 'layer']),
            models.Index(fields=['assigned_to']),
            models.Index(fields=['due_date']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"{self.template.name} - {self.layer.company_name}"

class ReportedMetricValue(models.Model):
    """Parent record storing aggregation results for a specific input metric context and aggregation level."""
    LEVEL_CHOICES = [
        ('M', 'Monthly'),
        ('Q', 'Quarterly'),
        ('A', 'Annual'),
        # Add others if needed ('D' daily, 'W' weekly?)
    ]
    
    assignment = models.ForeignKey(TemplateAssignment, on_delete=models.CASCADE, related_name='aggregated_records')
    metric = models.ForeignKey(
        'data_management.BaseESGMetric', # Changed to string reference
        on_delete=models.CASCADE, 
        related_name='aggregated_records'
    )
    layer = models.ForeignKey(LayerProfile, on_delete=models.CASCADE, related_name='aggregated_records')
    reporting_period = models.DateField(help_text="End date of the period this aggregated value represents") # Clarified help text
    level = models.CharField(
        max_length=1, 
        choices=LEVEL_CHOICES, 
        default='A', # Set default to Annual
        help_text="Aggregation level (Monthly, Quarterly, Annual)"
    ) # New Field

    # Aggregated value fields - these may need rethinking based on polymorphic types
    # For now, keep them, but aggregation logic will need updates
    aggregated_numeric_value = models.FloatField(null=True, blank=True, help_text="Aggregated value if the input metric is single-value numeric")
    aggregated_text_value = models.TextField(null=True, blank=True, help_text="Aggregated value if the input metric is single-value text")

    # Calculation metadata
    calculated_at = models.DateTimeField(auto_now_add=True, help_text="When this record was first created")
    last_updated_at = models.DateTimeField(auto_now=True, help_text="When this record or its fields were last updated by aggregation")

    # Aggregation metadata
    source_submission_count = models.PositiveIntegerField(default=0, help_text="Number of source submissions contributing to this aggregation")
    first_submission_at = models.DateTimeField(null=True, blank=True, help_text="Timestamp of the first submission included")
    last_submission_at = models.DateTimeField(null=True, blank=True, help_text="Timestamp of the last submission included")

    class Meta:
        # Update unique_together and index
        unique_together = ['assignment', 'metric', 'reporting_period', 'layer', 'level']
        indexes = [
            models.Index(fields=['assignment', 'metric', 'reporting_period', 'layer', 'level'], name='unique_agg_record_lvl_idx'),
            models.Index(fields=['reporting_period']),
            models.Index(fields=['level']), # Index on level
        ]
        ordering = ['assignment', 'metric', 'reporting_period', 'level'] # Add level to ordering
        verbose_name = "Aggregated Metric Record"
        verbose_name_plural = "Aggregated Metric Records"

    def __str__(self):
        return f"{self.get_level_display()} Agg for {self.metric.name} ({self.reporting_period}) - {self.layer.company_name}"

class ESGMetricSubmission(models.Model):
    """Header record for a raw input data point for an ESG metric within a template assignment.
    The actual submitted data is stored in related models (e.g., BasicMetricData, TabularMetricRow)."""
    assignment = models.ForeignKey(TemplateAssignment, on_delete=models.CASCADE, related_name='submissions')
    metric = models.ForeignKey(
        'data_management.BaseESGMetric', # Changed to string reference
        on_delete=models.CASCADE
    )
    # value & text_value are removed - data stored in related models
    # value = models.FloatField(null=True, blank=True, help_text="Raw value for single-value numeric metrics (legacy/basic)")
    # text_value = models.TextField(null=True, blank=True, help_text="Raw value for single-value text metrics (legacy/basic)")
    reporting_period = models.DateField(null=True, blank=True, help_text="For time-based metrics (e.g., monthly data), indicates the period this input applies to")
    submitted_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, related_name='metric_submissions')
    submitted_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    notes = models.TextField(blank=True, help_text="Notes specific to this raw input")

    # Verification fields now apply to the RAW INPUT
    is_verified = models.BooleanField(default=False, help_text="Verification status of this specific input")
    verified_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='verified_submissions')
    verified_at = models.DateTimeField(null=True, blank=True)
    verification_notes = models.TextField(blank=True, help_text="Verification notes for this specific input")

    layer = models.ForeignKey(
        LayerProfile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='submissions',
        help_text="The layer this input data represents (if different from assignment layer)"
    )

    # New field for source identification
    source_identifier = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        help_text="Optional identifier for the source of this input (e.g., meter ID, specific file)",
        db_index=True # Add index for potential filtering
    )
    
    # TODO: Consider making this polymorphic as well to hold type-specific data?
    # For now, keep it simple, but data for Tabular/Matrix etc. will need separate models.

    class Meta:
        indexes = [
            models.Index(fields=['assignment', 'metric']),
            models.Index(fields=['reporting_period']),
            models.Index(fields=['submitted_by']),
            models.Index(fields=['is_verified']),
            models.Index(fields=['source_identifier']), # Index for the new field
        ]
        ordering = ['assignment', 'metric', 'reporting_period', '-submitted_at']
        verbose_name = "Metric Submission Input"
        verbose_name_plural = "Metric Submission Inputs"

    def __str__(self):
        period_str = f" ({self.reporting_period})" if self.reporting_period else ""
        source_str = f" [{self.source_identifier}]" if self.source_identifier else ""
        # Reverted change: Access metric name correctly
        # Accessing metric.name should still work due to polymorphism
        return f"{self.metric.name}{period_str}{source_str} - {self.assignment.layer.company_name} (Input ID: {self.pk})"

class ESGMetricEvidence(models.Model):
    """Supporting documentation for ESG metric submission inputs"""
    submission = models.ForeignKey(ESGMetricSubmission, on_delete=models.CASCADE, related_name='evidence', null=True, blank=True,
                                 help_text="The specific submission input this evidence supports")
    file = models.FileField(upload_to='esg_evidence/%Y/%m/')
    filename = models.CharField(max_length=255)
    file_type = models.CharField(max_length=50)
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
    
    # New field for explicit metric relationship - updated FK
    intended_metric = models.ForeignKey(
        'data_management.BaseESGMetric', # Changed to string reference
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='intended_evidence',
        help_text="The metric this evidence is intended for, before being attached to a submission input"
    )
    
    # OCR-related fields remain the same, relate to the evidence file itself
    enable_ocr_processing = models.BooleanField(default=True, help_text="Whether OCR processing is available for this evidence file")
    is_processed_by_ocr = models.BooleanField(default=False, help_text="Whether OCR processing has been attempted")
    extracted_value = models.FloatField(null=True, blank=True, help_text="Value extracted by OCR")
    period = models.DateField(null=True, blank=True, help_text="User-selected reporting period")
    ocr_period = models.DateField(null=True, blank=True, help_text="Reporting period extracted by OCR")
    ocr_data = models.JSONField(null=True, blank=True, help_text="Raw data extracted by OCR")
    was_manually_edited = models.BooleanField(default=False, help_text="Whether the OCR result was manually edited")
    edited_at = models.DateTimeField(null=True, blank=True, help_text="When the OCR result was edited")
    edited_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='edited_evidence', help_text="Who edited the OCR result")

    def __str__(self):
        if self.submission:
            return f"Evidence for Input ID: {self.submission.pk}"
        return f"Standalone evidence: {self.filename}"