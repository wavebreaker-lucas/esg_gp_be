from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from accounts.models import CustomUser, LayerProfile
from django.utils import timezone # Import timezone
import uuid
import os
from datetime import datetime

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
    """
    Links templates to their included forms. This defines the forms included in a template.
    Note: This DOES NOT track completion status per company/assignment - that's handled by FormCompletionStatus.
    """
    template = models.ForeignKey(Template, on_delete=models.CASCADE)
    form = models.ForeignKey(ESGForm, on_delete=models.CASCADE)
    regions = models.JSONField(default=list)  # List of regions this form applies to
    order = models.PositiveIntegerField(default=0)
    
    # These completion fields will be deprecated in favor of FormCompletionStatus
    # They remain for backward compatibility only and should not be used in new code
    is_completed = models.BooleanField(default=False, help_text="DEPRECATED - Use FormCompletionStatus instead")
    completed_at = models.DateTimeField(null=True, blank=True, help_text="DEPRECATED - Use FormCompletionStatus instead")
    completed_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, 
                                     related_name='completed_forms', help_text="DEPRECATED - Use FormCompletionStatus instead")

    class Meta:
        ordering = ['template', 'order']
        unique_together = ['template', 'form']
        
    def __str__(self):
        return f"{self.template.name} - {self.form.name}"

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
    
    @property
    def verification_progress(self):
        """
        Returns dictionary with verification statistics for this assignment.
        """
        form_statuses = self.form_completion_status.all()
        return {
            'total_forms': form_statuses.count(),
            'completed_forms': form_statuses.filter(is_completed=True).count(),
            'verified_forms': form_statuses.filter(is_verified=True).count(),
            'pending_verification': form_statuses.filter(is_completed=True, is_verified=False).count(),
            'draft_forms': form_statuses.filter(is_completed=False).count()
        }
    
    @property
    def is_fully_verified(self):
        """
        True if all forms in this assignment are verified.
        """
        progress = self.verification_progress
        return progress['total_forms'] > 0 and progress['verified_forms'] == progress['total_forms']
    
    @property
    def is_fully_completed(self):
        """
        True if all forms in this assignment are completed (but may not be verified).
        """
        progress = self.verification_progress
        return progress['total_forms'] > 0 and progress['completed_forms'] == progress['total_forms']
    
    def update_status(self):
        """
        Auto-update assignment status based on form completion and verification.
        Called automatically when form statuses change.
        """
        progress = self.verification_progress
        
        if progress['total_forms'] == 0:
            # No forms assigned yet
            new_status = 'PENDING'
        elif progress['verified_forms'] == progress['total_forms']:
            # All forms verified
            new_status = 'VERIFIED'
        elif progress['completed_forms'] == progress['total_forms']:
            # All forms completed, but not all verified
            new_status = 'SUBMITTED'
        elif progress['completed_forms'] > 0:
            # Some forms completed
            new_status = 'IN_PROGRESS'
        else:
            # No forms completed yet
            new_status = 'IN_PROGRESS'
        
        if self.status != new_status:
            self.status = new_status
            if new_status == 'VERIFIED':
                self.completed_at = timezone.now()
            self.save()
    
    def get_form_verification_summary(self):
        """
        Returns a list of form verification statuses for easy display.
        """
        return [
            {
                'form_code': fs.form_selection.form.code,
                'form_name': fs.form_selection.form.name,
                'status': fs.status,
                'is_completed': fs.is_completed,
                'is_verified': fs.is_verified,
                'completed_at': fs.completed_at,
                'verified_at': fs.verified_at,
                'verified_by': fs.verified_by.username if fs.verified_by else None
            }
            for fs in self.form_completion_status.all().select_related('form_selection__form', 'verified_by')
        ]

class FormCompletionStatus(models.Model):
    """
    Tracks the completion and verification status of forms for each template assignment.
    This model provides proper data isolation between different companies
    and between different reporting periods for the same company.
    
    Workflow: Draft → User Complete → Admin Verify
    """
    form_selection = models.ForeignKey(TemplateFormSelection, on_delete=models.CASCADE, related_name='assignment_completion')
    assignment = models.ForeignKey(TemplateAssignment, on_delete=models.CASCADE, related_name='form_completion_status',
                                  help_text="The template assignment this completion status belongs to")
    layer = models.ForeignKey(
        LayerProfile,
        on_delete=models.CASCADE,
        related_name='form_completions',
        help_text="The layer this completion status applies to (could be assignment layer or child layer)"
    )
    
    # User completion fields (existing)
    is_completed = models.BooleanField(default=False, help_text="User has marked this form as complete")
    completed_at = models.DateTimeField(null=True, blank=True, help_text="When the user marked this form as complete")
    completed_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='completed_assignment_forms')
    
    # Admin verification fields (new)
    is_verified = models.BooleanField(default=False, help_text="Admin has verified this completed form")
    verified_at = models.DateTimeField(null=True, blank=True, help_text="When the admin verified this form")
    verified_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='verified_forms',
                                   help_text="Admin user who verified this form")
    verification_notes = models.TextField(blank=True, help_text="Admin notes during verification process")
    
    class Meta:
        ordering = ['assignment', 'form_selection']
        unique_together = ['form_selection', 'assignment', 'layer']
        indexes = [
            models.Index(fields=['form_selection', 'assignment']),
            models.Index(fields=['is_completed']),
            models.Index(fields=['is_verified']),  # New index for verification filtering
            models.Index(fields=['assignment']),
            models.Index(fields=['layer'], name='data_manage_layer_idx'),
        ]
        verbose_name = "Form Completion Status"
        verbose_name_plural = "Form Completion Statuses"
    
    def __str__(self):
        status_display = self.get_status_display()
        return f"{self.form_selection.form.code} - {self.layer.company_name} - {status_display}"
    
    def can_verify(self):
        """
        Check if this form can be verified.
        Only completed forms that haven't been verified yet can be verified.
        """
        return self.is_completed and not self.is_verified
    
    def can_complete(self):
        """
        Check if this form can be marked as complete.
        Forms that are already verified cannot be marked incomplete unless sent back.
        """
        return not self.is_verified
    
    def send_back_for_changes(self, admin_user, reason=""):
        """
        Admin sends form back to user for changes.
        This resets both completion and verification status.
        User must re-complete the form after making changes.
        """
        self.is_completed = False
        self.is_verified = False
        self.completed_at = None
        self.verified_at = None
        self.completed_by = None
        self.verified_by = admin_user
        self.verification_notes = f"Sent back for changes: {reason}" if reason else "Sent back for changes"
        self.save()
        
        # Trigger assignment status update
        self.assignment.update_status()
    
    def mark_completed(self, user):
        """
        Mark form as completed by user.
        """
        if not self.can_complete():
            raise ValueError("Form cannot be marked as complete - it may already be verified")
        
        self.is_completed = True
        self.completed_at = timezone.now()
        self.completed_by = user
        self.save()
        
        # Trigger assignment status update
        self.assignment.update_status()
    
    def mark_verified(self, admin_user, notes=""):
        """
        Mark form as verified by admin.
        """
        if not self.can_verify():
            raise ValueError("Form cannot be verified - it must be completed first and not already verified")
        
        self.is_verified = True
        self.verified_at = timezone.now()
        self.verified_by = admin_user
        self.verification_notes = notes
        self.save()
        
        # Trigger assignment status update
        self.assignment.update_status()
    
    @property
    def status(self):
        """
        Current status of the form based on completion and verification flags.
        """
        if not self.is_completed:
            return "DRAFT"
        elif not self.is_verified:
            return "PENDING_VERIFICATION"
        else:
            return "VERIFIED"
    
    def get_status_display(self):
        """
        Human-readable status display.
        """
        status_map = {
            "DRAFT": "Draft",
            "PENDING_VERIFICATION": "Pending Verification", 
            "VERIFIED": "Verified"
        }
        return status_map.get(self.status, self.status)
    


class ReportedMetricValue(models.Model):
    """Parent record storing aggregation results for a specific input metric context and aggregation level."""
    LEVEL_CHOICES = [
        ('M', 'Monthly'),
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
        
    def get_evidence(self):
        """
        Get evidence files relevant to this submission based on metadata matching.
        This maintains compatibility with code that previously used submission.evidence.all()
        """
        from ..services.evidence import find_relevant_evidence
        return find_relevant_evidence(self)

class ESGMetricEvidence(models.Model):
    """
    Supporting documentation for ESG metrics.
    Evidence is associated with metrics, layers, and sources via metadata rather than direct attachment.
    """
    def evidence_upload_to(instance, filename):
        now = datetime.now()
        ext = os.path.splitext(filename)[1]
        unique_id = uuid.uuid4().hex
        return f"esg_evidence/{now.year}/{now.month:02d}/{unique_id}{ext}"
    file = models.FileField(upload_to=evidence_upload_to)
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
    
    # Add source identifier field
    source_identifier = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Identifier for the source of this evidence (e.g., facility name)"
    )
    
    # New field for explicit metric relationship - updated FK
    intended_metric = models.ForeignKey(
        'data_management.BaseESGMetric', # Changed to string reference
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='intended_evidence',
        help_text="The metric this evidence is for"
    )
    
    # NEW: Direct link to a specific vehicle
    target_vehicle = models.ForeignKey(
        'data_management.VehicleRecord',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='evidence_files',
        help_text="The specific vehicle this evidence relates to, if any."
    )
    
    # NEW: Direct link to a specific fuel source
    target_fuel_source = models.ForeignKey(
        'data_management.FuelRecord',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='evidence_files',
        help_text="The specific fuel source this evidence relates to, if any."
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
        return f"Evidence for Input ID: {self.pk}"