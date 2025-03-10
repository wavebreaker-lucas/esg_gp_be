from django.db import models
from django.contrib.auth.models import AbstractUser

# Create your models here.

class CustomUser(AbstractUser):
    is_management = models.BooleanField(default=False)
    is_operation = models.BooleanField(default=False)
    phone_number = models.CharField(max_length=15, blank=True)

    def __str__(self):
        return self.username

class CompanyLayer(models.Model):
    LAYER_TYPES = [
        ('GROUP', 'Group'),
        ('SUBSIDIARY', 'Subsidiary'),
        ('BRANCH', 'Branch'),
    ]
    name = models.CharField(max_length=255)
    layer_type = models.CharField(max_length=20, choices=LAYER_TYPES)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='children')
    
    def __str__(self):
        return f"{self.name} ({self.get_layer_type_display()})"

    class Meta:
        verbose_name = "Company Layer"
        verbose_name_plural = "Company Layers"
