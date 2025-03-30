from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from accounts.models import CustomUser, LayerProfile

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

class ESGMetric(models.Model):
    """Individual metrics within ESG forms"""
    UNIT_TYPES = [
        # Environmental
        ('kWh', 'Kilowatt Hours'),
        ('MWh', 'Megawatt Hours'),
        ('m3', 'Cubic Meters'),
        ('tonnes', 'Tonnes'),
        ('tCO2e', 'Tonnes CO2 Equivalent'),
        # Social
        ('person', 'Person'),
        ('hours', 'Hours'),
        ('days', 'Days'),
        ('count', 'Count'),
        ('percentage', 'Percentage'),
        # Custom
        ('custom', 'Custom Unit'),
    ]

    LOCATION_CHOICES = [
        ('HK', 'Hong Kong'),
        ('PRC', 'Mainland China'),
        ('ALL', 'All Locations'),
    ]
    
    REPORTING_FREQUENCY_CHOICES = [
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('annual', 'Annual'),
    ]

    form = models.ForeignKey(ESGForm, on_delete=models.CASCADE, related_name='metrics')
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    unit_type = models.CharField(max_length=20, choices=UNIT_TYPES)
    custom_unit = models.CharField(max_length=50, blank=True, null=True)
    requires_evidence = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)
    validation_rules = models.JSONField(default=dict, blank=True)
    location = models.CharField(max_length=3, choices=LOCATION_CHOICES, default='ALL')
    is_required = models.BooleanField(default=True, help_text="Whether this metric must be reported")
    
    # New JSON schema fields
    data_schema = models.JSONField(default=dict, blank=True, help_text="JSON Schema for this metric's data")
    schema_registry = models.ForeignKey('MetricSchemaRegistry', on_delete=models.SET_NULL, null=True, blank=True, 
                                      related_name='metrics', help_text="Reference to a registered schema for this metric")
    form_component = models.CharField(max_length=50, null=True, blank=True, help_text="Frontend component to use for this metric")
    
    # Keep these for backward compatibility during migration
    requires_time_reporting = models.BooleanField(default=False, help_text="Whether this metric requires reporting for multiple time periods")
    reporting_frequency = models.CharField(
        max_length=20, 
        choices=REPORTING_FREQUENCY_CHOICES,
        null=True, 
        blank=True,
        help_text="Required frequency of reporting for time-based metrics"
    )
    ocr_analyzer_id = models.CharField(
        max_length=100, 
        blank=True, 
        null=True,
        help_text="Custom analyzer ID for OCR processing of this metric's evidence"
    )

    class Meta:
        ordering = ['form', 'order']

    def __str__(self):
        if self.location != 'ALL':
            return f"{self.form.code} - {self.name} ({self.get_location_display()})"
        return f"{self.form.code} - {self.name}"

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

class ESGMetricSubmission(models.Model):
    """User-submitted values for ESG metrics within a template assignment"""
    assignment = models.ForeignKey(TemplateAssignment, on_delete=models.CASCADE, related_name='submissions')
    metric = models.ForeignKey(ESGMetric, on_delete=models.CASCADE)
    
    # New unified data field
    data = models.JSONField(null=True, blank=True, help_text="All metric data in structured JSON format")
    
    # Batch submission relationship
    batch_submission = models.ForeignKey('ESGMetricBatchSubmission', on_delete=models.SET_NULL, 
                                       null=True, blank=True, related_name='submissions',
                                       help_text="Batch this submission belongs to, if any")
    
    # Keep these for backward compatibility during migration
    value = models.FloatField(null=True, blank=True)
    text_value = models.TextField(null=True, blank=True, help_text="For non-numeric metrics")
    reporting_period = models.DateField(null=True, blank=True, help_text="For time-based metrics (e.g., monthly data)")
    
    # Metadata fields
    submitted_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, related_name='metric_submissions')
    submitted_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    notes = models.TextField(blank=True)
    is_verified = models.BooleanField(default=False)
    verified_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='verified_submissions')
    verified_at = models.DateTimeField(null=True, blank=True)
    verification_notes = models.TextField(blank=True)
    layer = models.ForeignKey(LayerProfile, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='submissions',
        help_text="The layer this submission's data represents"
    )

    class Meta:
        # Update uniqueness constraint to remove reporting_period
        unique_together = ['assignment', 'metric', 'layer']
        indexes = [
            models.Index(fields=['assignment', 'metric']),
            models.Index(fields=['submitted_by']),
            models.Index(fields=['is_verified']),
            # Add index for better JSON field querying if using PostgreSQL
            # If using PostgreSQL, uncomment this:
            # models.Index(fields=['data'], name='data_gin_idx', opclasses=['jsonb_path_ops'])
        ]

    def __str__(self):
        return f"{self.metric.name} - {self.assignment.layer.company_name}"

class ESGMetricEvidence(models.Model):
    """Supporting documentation for ESG metric submissions"""
    submission = models.ForeignKey(ESGMetricSubmission, on_delete=models.CASCADE, related_name='evidence', null=True, blank=True,
                                 help_text="Can be null for standalone evidence files before attaching to a submission")
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
    
    # New field for JSON reference path
    reference_path = models.CharField(max_length=255, null=True, blank=True,
                                    help_text="JSON path this evidence relates to (e.g., 'periods.Jan-2024')")
    
    intended_metric = models.ForeignKey(ESGMetric, on_delete=models.SET_NULL, null=True, blank=True, 
                                        related_name='intended_evidence',
                                        help_text="The metric this evidence is intended for, before being attached to a submission")
    
    # Update OCR-related fields
    enable_ocr_processing = models.BooleanField(default=True, help_text="Whether OCR processing is available for this evidence file")
    is_processed_by_ocr = models.BooleanField(default=False, help_text="Whether OCR processing has been attempted")
    extracted_value = models.FloatField(null=True, blank=True, help_text="Value extracted by OCR")
    period = models.DateField(null=True, blank=True, help_text="User-selected reporting period")
    ocr_period = models.DateField(null=True, blank=True, help_text="Reporting period extracted by OCR")
    ocr_data = models.JSONField(null=True, blank=True, help_text="Raw data extracted by OCR")
    extracted_data = models.JSONField(null=True, blank=True, help_text="Structured data extracted by OCR")
    was_manually_edited = models.BooleanField(default=False, help_text="Whether the OCR result was manually edited")
    edited_at = models.DateTimeField(null=True, blank=True, help_text="When the OCR result was edited")
    edited_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='edited_evidence', help_text="Who edited the OCR result")

    def __str__(self):
        if self.submission:
            return f"Evidence for {self.submission.metric.name}"
        return f"Standalone evidence: {self.filename}"

class MetricSchemaRegistry(models.Model):
    """Registry of JSON schemas for ESG metrics"""
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    schema = models.JSONField(help_text="JSON Schema definition for this metric type")
    version = models.CharField(max_length=20, default="1.0.0")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, related_name='created_schemas')
    is_active = models.BooleanField(default=True)
    
    class Meta:
        verbose_name = "Metric Schema"
        verbose_name_plural = "Metric Schemas"
        ordering = ['name']
        
    def __str__(self):
        return f"{self.name} v{self.version}"

class ESGMetricBatchSubmission(models.Model):
    """Group of related metric submissions submitted together"""
    assignment = models.ForeignKey(TemplateAssignment, on_delete=models.CASCADE, related_name='batch_submissions')
    name = models.CharField(max_length=255, blank=True, null=True, help_text="Optional name for this batch")
    submitted_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True)
    submitted_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    layer = models.ForeignKey(LayerProfile, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='batch_submissions',
        help_text="The layer this submission's data represents"
    )
    notes = models.TextField(blank=True)
    
    # These fields track the batch verification status
    is_verified = models.BooleanField(default=False)
    verified_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='verified_batches')
    verified_at = models.DateTimeField(null=True, blank=True)
    verification_notes = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-submitted_at']
        
    def __str__(self):
        if self.name:
            return f"{self.name} - {self.assignment.layer.company_name} ({self.submitted_at.strftime('%Y-%m-%d')})"
        return f"Batch {self.id} - {self.assignment.layer.company_name} ({self.submitted_at.strftime('%Y-%m-%d')})" 