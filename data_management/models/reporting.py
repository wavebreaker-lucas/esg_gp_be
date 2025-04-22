"""
Models for storing and managing generated reports.
"""

from django.db import models
from django.utils import timezone
import json
from .templates import ESGMetricSubmission

class ChecklistReport(models.Model):
    """
    Stores generated AI reports from checklist submissions for later reference.
    """
    # Report type and creation metadata
    REPORT_TYPE_CHOICES = [
        ('SINGLE', 'Single Checklist Report'),
        ('COMBINED', 'Combined ESG Report'),
    ]
    
    report_type = models.CharField(max_length=20, choices=REPORT_TYPE_CHOICES)
    title = models.CharField(max_length=255)
    company = models.CharField(max_length=255)
    generated_at = models.DateTimeField(default=timezone.now)
    
    # Submission references
    primary_submission = models.ForeignKey(
        ESGMetricSubmission, 
        on_delete=models.CASCADE,
        related_name='primary_reports'
    )
    related_submissions = models.ManyToManyField(
        ESGMetricSubmission,
        related_name='related_reports',
        blank=True,
        help_text="Additional submissions included in a combined report"
    )
    
    # Performance metrics
    overall_compliance = models.FloatField(
        help_text="Overall compliance percentage"
    )
    environmental_compliance = models.FloatField(
        null=True, 
        blank=True,
        help_text="Environmental compliance percentage (for combined reports)"
    )
    social_compliance = models.FloatField(
        null=True, 
        blank=True,
        help_text="Social compliance percentage (for combined reports)"
    )
    governance_compliance = models.FloatField(
        null=True, 
        blank=True,
        help_text="Governance compliance percentage (for combined reports)"
    )
    
    # Report content
    content = models.TextField(
        help_text="The full text content of the AI-generated report"
    )
    
    # Metadata
    word_count = models.PositiveIntegerField(
        default=0,
        help_text="Word count of the generated report"
    )
    
    # Version tracking
    version = models.PositiveIntegerField(
        default=1,
        help_text="Report version number (increments when regenerated for same submission)"
    )
    
    class Meta:
        ordering = ['-generated_at']
        verbose_name = "Checklist Report"
        verbose_name_plural = "Checklist Reports"
    
    def __str__(self):
        return f"{self.title} - {self.company} ({self.generated_at.strftime('%Y-%m-%d')})"
    
    def save(self, *args, **kwargs):
        # Calculate word count if not set
        if not self.word_count and self.content:
            self.word_count = len(self.content.split())
        super().save(*args, **kwargs)
    
    @classmethod
    def create_from_single_report(cls, submission_id, report_data):
        """
        Create a report record from a single checklist report response.
        
        Args:
            submission_id: The submission ID
            report_data: Report data dictionary from the API response
            
        Returns:
            The created ChecklistReport instance
        """
        submission = ESGMetricSubmission.objects.get(id=submission_id)
        
        return cls.objects.create(
            report_type='SINGLE',
            title=report_data.get('title', 'Checklist Report'),
            company=report_data.get('company', 'Unknown'),
            generated_at=timezone.now(),
            primary_submission=submission,
            overall_compliance=report_data.get('compliance_percentage', 0),
            content=report_data.get('content', ''),
        )
    
    @classmethod
    def create_from_combined_report(cls, primary_submission_id, submission_ids, report_data):
        """
        Create a report record from a combined ESG report response.
        
        Args:
            primary_submission_id: The primary submission ID (typically ENV)
            submission_ids: List of all submission IDs included in the report
            report_data: Report data dictionary from the API response
            
        Returns:
            The created ChecklistReport instance
        """
        primary_submission = ESGMetricSubmission.objects.get(id=primary_submission_id)
        
        report = cls.objects.create(
            report_type='COMBINED',
            title=report_data.get('title', 'Integrated ESG Report'),
            company=report_data.get('company', 'Unknown'),
            generated_at=timezone.now(),
            primary_submission=primary_submission,
            overall_compliance=report_data.get('overall_compliance', 0),
            environmental_compliance=report_data.get('environmental_compliance'),
            social_compliance=report_data.get('social_compliance'),
            governance_compliance=report_data.get('governance_compliance'),
            content=report_data.get('content', ''),
        )
        
        # Add related submissions (excluding the primary which is already linked)
        for submission_id in submission_ids:
            if submission_id != primary_submission_id:
                try:
                    submission = ESGMetricSubmission.objects.get(id=submission_id)
                    report.related_submissions.add(submission)
                except ESGMetricSubmission.DoesNotExist:
                    pass
                    
        return report
    
    def to_dict(self):
        """Convert report to dictionary for API responses"""
        result = {
            "id": self.id,
            "report_type": self.report_type,
            "title": self.title,
            "company": self.company,
            "generated_at": self.generated_at.strftime("%Y-%m-%d %H:%M:%S"),
            "overall_compliance": self.overall_compliance,
            "content": self.content,
            "word_count": self.word_count,
            "version": self.version,
            "primary_submission_id": self.primary_submission_id,
        }
        
        # Add ESG-specific compliance metrics for combined reports
        if self.report_type == 'COMBINED':
            result.update({
                "environmental_compliance": self.environmental_compliance,
                "social_compliance": self.social_compliance,
                "governance_compliance": self.governance_compliance,
            })
            
        return result 