"""
Models for handling notifications in the ESG platform.
"""

from django.db import models
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from accounts.models import CustomUser

class Notification(models.Model):
    """
    Notification model for tracking user notifications.
    
    This model supports various notification types and can be linked
    to any object in the system using the generic foreign key.
    """
    
    class Type(models.TextChoices):
        APPROVAL_REQUIRED = 'APPROVAL_REQUIRED', 'Approval Required'
        SUBMISSION_APPROVED = 'SUBMISSION_APPROVED', 'Submission Approved'
        SUBMISSION_REJECTED = 'SUBMISSION_REJECTED', 'Submission Rejected'
        ASSIGNED_TASK = 'ASSIGNED_TASK', 'Task Assigned'
        DUE_DATE_REMINDER = 'DUE_DATE_REMINDER', 'Due Date Reminder'
        EVIDENCE_ADDED = 'EVIDENCE_ADDED', 'Evidence Added'
        GENERAL = 'GENERAL', 'General Notification'
    
    recipient = models.ForeignKey(
        CustomUser, 
        on_delete=models.CASCADE,
        related_name='notifications'
    )
    message = models.TextField()
    notification_type = models.CharField(
        max_length=20,
        choices=Type.choices,
        default=Type.GENERAL
    )
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)
    
    # Generic foreign key to allow linking to any model
    content_type = models.ForeignKey(
        ContentType, 
        on_delete=models.CASCADE,
        null=True, 
        blank=True
    )
    object_id = models.PositiveIntegerField(null=True, blank=True)
    related_object = GenericForeignKey('content_type', 'object_id')
    
    # Optional fields for specific notification types
    action_url = models.CharField(max_length=255, blank=True)
    expiry_date = models.DateTimeField(null=True, blank=True)
    
    # Fields for linking to related objects using simpler approach
    # These fields can be used as an alternative to the generic relation
    related_object_type = models.ForeignKey(
        ContentType, 
        on_delete=models.CASCADE,
        null=True, 
        blank=True,
        related_name='notifications_as_related'
    )
    related_object_id = models.PositiveIntegerField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient', 'is_read']),
            models.Index(fields=['notification_type']),
            models.Index(fields=['content_type', 'object_id']),
            models.Index(fields=['related_object_type', 'related_object_id']),
        ]
    
    def __str__(self):
        return f"Notification: {self.message[:50]}{'...' if len(self.message) > 50 else ''}"
    
    def mark_as_read(self):
        """Mark notification as read and save the read timestamp"""
        from django.utils import timezone
        self.is_read = True
        self.read_at = timezone.now()
        self.save()
    
    @property
    def short_message(self):
        """Return a shortened version of the message for display in lists"""
        max_length = 100
        if len(self.message) <= max_length:
            return self.message
        return self.message[:max_length] + '...' 