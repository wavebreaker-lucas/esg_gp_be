from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from accounts.models import CustomUser, LayerProfile

class Template(models.Model):
    CATEGORY_CHOICES = [
        ('ENVIRONMENTAL', 'Environmental'),
        ('SOCIAL', 'Social'),
        ('GOVERNANCE', 'Governance'),
    ]

    TEMPLATE_TYPE_CHOICES = [
        ('ASSESSMENT', 'Maturity Assessment'),
        ('DISCLOSURE', 'Data Disclosure'),
        ('COMPLIANCE', 'Compliance Check'),
    ]

    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    template_type = models.CharField(max_length=20, choices=TEMPLATE_TYPE_CHOICES, default='DISCLOSURE')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    version = models.PositiveIntegerField(default=1)
    created_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True)
    reporting_period = models.CharField(max_length=50, help_text="e.g., 'Annual 2024', 'Q1 2024'")

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['category']),
            models.Index(fields=['is_active']),
        ]

    def __str__(self):
        return f"{self.name} v{self.version}"

class Question(models.Model):
    QUESTION_TYPES = [
        ('NUMBER', 'Numeric Input'),
        ('TEXT', 'Text Description'),
        ('CHOICE', 'Single Choice'),
        ('MULTIPLE_CHOICE', 'Multiple Choice'),
        ('DATE', 'Date'),
        ('FILE', 'File Upload'),
    ]

    QUESTION_CATEGORY = [
        ('QUANTITATIVE', 'Quantitative Data'),
        ('QUALITATIVE', 'Qualitative Assessment'),
        ('EVIDENCE', 'Documentation/Evidence'),
    ]

    UNIT_TYPES = [
        # Environmental
        ('kWh', 'Kilowatt Hours'),
        ('MWh', 'Megawatt Hours'),
        ('m3', 'Cubic Meters'),
        ('tonnes', 'Tonnes'),
        ('tCO2e', 'Tonnes CO2 Equivalent'),
        # Social
        ('hours', 'Hours'),
        ('count', 'Count'),
        ('percentage', 'Percentage'),
        # Custom
        ('custom', 'Custom Unit'),
    ]

    template = models.ForeignKey(Template, related_name='questions', on_delete=models.CASCADE)
    text = models.TextField()
    help_text = models.TextField(blank=True)
    is_required = models.BooleanField(default=True)
    order = models.PositiveIntegerField()
    question_type = models.CharField(max_length=20, choices=QUESTION_TYPES)
    question_category = models.CharField(max_length=20, choices=QUESTION_CATEGORY, default='QUANTITATIVE')
    validation_rules = models.JSONField(default=dict, blank=True, help_text="Validation rules for the input")
    section = models.CharField(max_length=100, blank=True)
    unit_type = models.CharField(max_length=20, choices=UNIT_TYPES, blank=True, null=True)
    custom_unit = models.CharField(max_length=50, blank=True, null=True)
    requires_evidence = models.BooleanField(default=False)
    has_score = models.BooleanField(default=False, help_text="Whether this question contributes to template scoring")
    max_score = models.PositiveIntegerField(default=0, help_text="Maximum score if this is a scored question")

    class Meta:
        ordering = ['order']
        indexes = [
            models.Index(fields=['template', 'order']),
            models.Index(fields=['question_category']),
        ]

    def __str__(self):
        return f"{self.template.name} - Q{self.order}"

class QuestionChoice(models.Model):
    question = models.ForeignKey(Question, related_name='choices', on_delete=models.CASCADE)
    text = models.CharField(max_length=255)
    value = models.CharField(max_length=100)
    order = models.PositiveIntegerField()
    score = models.PositiveIntegerField(default=0, help_text="Score for this choice if question is scored")

    class Meta:
        ordering = ['order']
        indexes = [
            models.Index(fields=['question', 'order']),
        ]

    def __str__(self):
        return f"{self.question} - {self.text}"

class TemplateAssignment(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('IN_PROGRESS', 'In Progress'),
        ('SUBMITTED', 'Submitted'),
        ('VERIFIED', 'Verified'),
        ('REJECTED', 'Rejected')
    ]

    template = models.ForeignKey(Template, on_delete=models.CASCADE)
    company = models.ForeignKey(LayerProfile, on_delete=models.CASCADE)
    assigned_to = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    assigned_at = models.DateTimeField(auto_now_add=True)
    due_date = models.DateField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    reporting_period_start = models.DateField()
    reporting_period_end = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    total_score = models.PositiveIntegerField(null=True, blank=True, help_text="Total score if template type is ASSESSMENT")
    max_possible_score = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=['template', 'company']),
            models.Index(fields=['assigned_to']),
            models.Index(fields=['due_date']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"{self.template.name} - {self.company.name}" 