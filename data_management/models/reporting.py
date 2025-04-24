"""
Models for storing and managing generated reports.
"""

from django.db import models
from django.utils import timezone
import json
from .templates import ESGMetricSubmission
from accounts.models import LayerProfile

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
    
    # Direct layer association
    layer = models.ForeignKey(
        LayerProfile,
        on_delete=models.CASCADE,
        related_name='checklist_reports',
        null=True,  # Allow null initially for migration
        help_text="The organizational layer this report belongs to"
    )
    
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
    
    # ESG Rating
    esg_rating = models.CharField(
        max_length=1,
        null=True,
        blank=True,
        help_text="Overall ESG rating (A-F)"
    )
    rating_description = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="Description of the ESG rating"
    )
    
    # Report content
    content = models.TextField(
        help_text="The full text or JSON content of the AI-generated report"
    )
    
    # Flag to indicate if content is JSON structured
    is_structured = models.BooleanField(
        default=False,
        help_text="Whether the content field contains structured JSON data"
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
            layer=submission.layer,  # Set the layer directly from the submission
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
        
        # Check if content is structured (dictionary) or text
        content = report_data.get('content', '')
        is_structured = isinstance(content, dict)
        
        # If content is structured JSON, serialize it
        if is_structured:
            content_str = json.dumps(content)
            
            # Calculate word count from all sections
            word_count = 0
            try:
                word_count += len(content.get('executive_summary', '').split())
                
                # Count words in ESG pillars
                pillars = content.get('esg_pillars', {})
                for pillar in pillars.values():
                    word_count += len(pillar.split())
                    
                word_count += len(content.get('key_findings', '').split())
                word_count += len(content.get('improvement_plan', '').split())
                word_count += len(content.get('conclusion', '').split())
                
                # If there's a fallback full_text, count that instead
                if 'full_text' in content:
                    word_count = len(content['full_text'].split())
            except (AttributeError, TypeError):
                # Fallback if structure is unexpected
                word_count = len(str(content).split())
        else:
            # Plain text content
            content_str = content
            word_count = len(content_str.split())
        
        report = cls.objects.create(
            report_type='COMBINED',
            title=report_data.get('title', 'Integrated ESG Report'),
            company=report_data.get('company', 'Unknown'),
            generated_at=timezone.now(),
            primary_submission=primary_submission,
            layer=primary_submission.layer,  # Set the layer from primary submission
            overall_compliance=report_data.get('overall_compliance', 0),
            environmental_compliance=report_data.get('environmental_compliance'),
            social_compliance=report_data.get('social_compliance'),
            governance_compliance=report_data.get('governance_compliance'),
            esg_rating=report_data.get('esg_rating'),
            rating_description=report_data.get('rating_description'),
            content=content_str,
            is_structured=is_structured,
            word_count=word_count
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
        # Parse content if it's structured JSON
        if self.is_structured:
            try:
                content = json.loads(self.content)
            except json.JSONDecodeError:
                # Fallback if JSON parsing fails
                content = self.content
        else:
            content = self.content
            
        result = {
            "id": self.id,
            "report_type": self.report_type,
            "title": self.title,
            "company": self.company,
            "generated_at": self.generated_at.strftime("%Y-%m-%d %H:%M:%S"),
            "overall_compliance": self.overall_compliance,
            "content": content,
            "is_structured": self.is_structured,
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
                "esg_rating": self.esg_rating,
                "rating_description": self.rating_description
            })
            
        # Add company details from the linked layer
        if self.layer:
            result.update({
                "company_industry": self.layer.company_industry,
                "company_location": self.layer.company_location,
                "company_size": self.layer.company_size,
                "annual_revenue": self.layer.annual_revenue,
                "number_of_sites": self.layer.number_of_sites,
                "target_customer": self.layer.target_customer
            })
            
        return result 