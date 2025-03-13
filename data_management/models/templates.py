from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from accounts.models import CustomUser, LayerProfile

class Template(models.Model):
    CATEGORY_CHOICES = [
        ('GENERAL', 'General Disclosure'),
        ('ENVIRONMENTAL', 'Environmental'),
        ('SOCIAL', 'Social'),
        ('GOVERNANCE', 'Governance'),
    ]

    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    version = models.PositiveIntegerField(default=1)
    created_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True)

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
        ('TEXT', 'Text'),
        ('NUMBER', 'Number'),
        ('CHOICE', 'Single Choice'),
        ('MULTIPLE_CHOICE', 'Multiple Choice'),
        ('DATE', 'Date'),
        ('FILE', 'File Upload'),
    ]

    template = models.ForeignKey(Template, related_name='questions', on_delete=models.CASCADE)
    text = models.TextField()
    help_text = models.TextField(blank=True)
    is_required = models.BooleanField(default=True)
    order = models.PositiveIntegerField()
    question_type = models.CharField(max_length=20, choices=QUESTION_TYPES)
    validation_rules = models.JSONField(default=dict, blank=True)
    section = models.CharField(max_length=100, blank=True)
    max_score = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']
        indexes = [
            models.Index(fields=['template', 'order']),
        ]

    def __str__(self):
        return f"{self.template.name} - Q{self.order}"

class QuestionChoice(models.Model):
    question = models.ForeignKey(Question, related_name='choices', on_delete=models.CASCADE)
    text = models.CharField(max_length=255)
    value = models.CharField(max_length=100)
    score = models.PositiveIntegerField(default=0)
    order = models.PositiveIntegerField()

    class Meta:
        ordering = ['order']
        indexes = [
            models.Index(fields=['question', 'order']),
        ]

    def __str__(self):
        return f"{self.question} - {self.text}"

class TemplateAssignment(models.Model):
    template = models.ForeignKey(Template, on_delete=models.CASCADE)
    company = models.ForeignKey(LayerProfile, on_delete=models.CASCADE)
    assigned_to = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    assigned_at = models.DateTimeField(auto_now_add=True)
    due_date = models.DateField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    total_score = models.PositiveIntegerField(default=0)
    max_possible_score = models.PositiveIntegerField(default=0)

    class Meta:
        indexes = [
            models.Index(fields=['template', 'company']),
            models.Index(fields=['assigned_to']),
            models.Index(fields=['due_date']),
        ]

    def __str__(self):
        return f"{self.template.name} - {self.company.name}" 