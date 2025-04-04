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
    is_multi_value = models.BooleanField(
        default=False,
        help_text="Whether this metric requires multiple related values"
    )
    aggregates_inputs = models.BooleanField(
        default=False,
        help_text="Does this metric's final value come from aggregating multiple raw inputs?"
    )

    class Meta:
        ordering = ['form', 'order']

    def __str__(self):
        if self.location != 'ALL':
            return f"{self.form.code} - {self.name} ({self.get_location_display()})"
        return f"{self.form.code} - {self.name}"

    def create_value_field(self, field_key, display_name, **kwargs):
        """Helper method to create a value field for this metric"""
        if not self.is_multi_value:
            self.is_multi_value = True
            self.save()
            
        return MetricValueField.objects.create(
            metric=self,
            field_key=field_key,
            display_name=display_name,
            **kwargs
        )

class MetricValueField(models.Model):
    """Fields for multi-value metrics"""
    DISPLAY_TYPES = [
        ('TEXT', 'Text Input'),
        ('NUMBER', 'Number Input'),
        ('SELECT', 'Dropdown Selection'),
    ]
    
    metric = models.ForeignKey(ESGMetric, on_delete=models.CASCADE, related_name='value_fields')
    field_key = models.CharField(max_length=50, help_text="Unique identifier for this field")
    display_name = models.CharField(max_length=100, help_text="User-friendly name")
    description = models.TextField(blank=True)
    column_header = models.CharField(max_length=50, blank=True, help_text="For tabular display (e.g., 'A', 'B')")
    display_type = models.CharField(max_length=20, choices=DISPLAY_TYPES, default='NUMBER')
    order = models.PositiveSmallIntegerField(default=0)
    options = models.JSONField(blank=True, null=True, help_text="Options for dropdown fields")
    is_required = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['metric', 'order']
        unique_together = ['metric', 'field_key']
        
    def __str__(self):
        return f"{self.metric.name} - {self.display_name}"

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
    """Stores the final, aggregated/official value for a metric submission period."""
    assignment = models.ForeignKey(TemplateAssignment, on_delete=models.CASCADE, related_name='reported_values')
    metric = models.ForeignKey(ESGMetric, on_delete=models.CASCADE, related_name='reported_values')
    layer = models.ForeignKey(LayerProfile, on_delete=models.CASCADE, related_name='reported_values') # Enforce layer for uniqueness
    reporting_period = models.DateField(help_text="The specific period this aggregated value represents (e.g., month-end, quarter-end)")

    # Value fields
    value = models.FloatField(null=True, blank=True)
    text_value = models.TextField(null=True, blank=True)

    # Calculation metadata
    calculated_at = models.DateTimeField(auto_now_add=True, help_text="When this value was first calculated/created")
    last_updated_at = models.DateTimeField(auto_now=True, help_text="When this value was last updated")
    # calculation_method = models.CharField(max_length=50, blank=True, help_text="e.g., SUM, AVERAGE, LATEST") # Consider adding later

    # Verification fields for the FINAL value
    is_verified = models.BooleanField(default=False)
    verified_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='verified_reported_values')
    verified_at = models.DateTimeField(null=True, blank=True)
    verification_notes = models.TextField(blank=True)

    class Meta:
        unique_together = ['assignment', 'metric', 'reporting_period', 'layer']
        indexes = [
            models.Index(fields=['assignment', 'metric', 'reporting_period', 'layer'], name='unique_reported_value_idx'), # Added name for clarity
            models.Index(fields=['reporting_period']),
            models.Index(fields=['is_verified']),
        ]
        ordering = ['assignment', 'metric', 'reporting_period']
        verbose_name = "Reported Metric Value"
        verbose_name_plural = "Reported Metric Values"

    def __str__(self):
        return f"{self.metric.name} ({self.reporting_period}) - {self.layer.company_name} [Final]"

class ESGMetricSubmission(models.Model):
    """Raw input data point for an ESG metric within a template assignment."""
    assignment = models.ForeignKey(TemplateAssignment, on_delete=models.CASCADE, related_name='submissions')
    metric = models.ForeignKey(ESGMetric, on_delete=models.CASCADE)
    value = models.FloatField(null=True, blank=True)
    text_value = models.TextField(null=True, blank=True, help_text="For non-numeric metrics or raw text input")
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

    layer = models.ForeignKey(LayerProfile, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='submissions',
        help_text="The layer this input data represents (if different from assignment layer)"
    )
    # --- New Field for Approach B ---
    reported_value = models.ForeignKey(
        ReportedMetricValue,
        on_delete=models.SET_NULL, # Keep input even if final value deleted
        null=True,
        blank=True,
        related_name='source_submissions',
        help_text="The final reported value this input contributed to"
    )
    # ------------------------------

    class Meta:
        # REMOVED: unique_together = ['assignment', 'metric', 'reporting_period']
        indexes = [
            models.Index(fields=['assignment', 'metric']), # Still useful for querying inputs
            models.Index(fields=['reporting_period']),
            models.Index(fields=['submitted_by']),
            models.Index(fields=['is_verified']), # Index for input verification status
            models.Index(fields=['reported_value']) # Index FK to final value
        ]
        ordering = ['assignment', 'metric', 'reporting_period', '-submitted_at'] # Added submit time
        verbose_name = "Metric Submission Input"
        verbose_name_plural = "Metric Submission Inputs"

    def __str__(self):
        period_str = f" ({self.reporting_period})" if self.reporting_period else ""
        # Updated to indicate it's an input
        return f"{self.metric.name}{period_str} - {self.assignment.layer.company_name} (Input ID: {self.pk})"
        
    # add_value helper method remains relevant for multi-value INPUTS
    def add_value(self, field_key, value):
        """Add a value for a multi-value field *to this input record*"""
        if not self.metric.is_multi_value:
            raise ValueError("This metric is not configured for multiple values")
            
        try:
            field = self.metric.value_fields.get(field_key=field_key)
        except MetricValueField.DoesNotExist:
            raise ValueError(f"Field '{field_key}' does not exist for this metric")
            
        # Determine if value is numeric or text
        if isinstance(value, (int, float)) or (isinstance(value, str) and value.replace('.', '', 1).isdigit()):
            numeric_value = float(value)
            text_value = None
        else:
            numeric_value = None
            text_value = str(value)
            
        # Create or update the MetricValue linked to this ESGMetricSubmission input
        return MetricValue.objects.update_or_create(
            submission=self, # Links to this specific input record
            field=field,
            defaults={
                'numeric_value': numeric_value,
                'text_value': text_value
            }
        )[0]

class MetricValue(models.Model):
    """Individual values for multi-value metrics, linked to a specific submission input"""
    submission = models.ForeignKey(ESGMetricSubmission, on_delete=models.CASCADE, related_name='multi_values')
    field = models.ForeignKey(MetricValueField, on_delete=models.CASCADE)
    numeric_value = models.FloatField(null=True, blank=True)
    text_value = models.TextField(null=True, blank=True)
    
    class Meta:
        unique_together = ['submission', 'field']
        
    def __str__(self):
        value = self.numeric_value if self.numeric_value is not None else self.text_value
        return f"{self.field.display_name}: {value} (for Input ID: {self.submission.pk})"

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
    
    # New field for explicit metric relationship
    intended_metric = models.ForeignKey(ESGMetric, on_delete=models.SET_NULL, null=True, blank=True, 
                                        related_name='intended_evidence',
                                        help_text="The metric this evidence is intended for, before being attached to a submission input")
    
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