from django.db import models
from accounts.models import CustomUser, LayerProfile

class BoundaryItem(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    is_default = models.BooleanField(default=False)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Boundary Item"
        verbose_name_plural = "Boundary Items"

class EmissionFactor(models.Model):
    name = models.CharField(max_length=255)
    value = models.DecimalField(max_digits=10, decimal_places=4)
    unit = models.CharField(max_length=50)
    effective_from = models.DateField()
    effective_to = models.DateField(null=True, blank=True)
    formula = models.TextField(blank=True)
    
    def __str__(self):
        return f"{self.name} ({self.unit})"

    class Meta:
        verbose_name = "Emission Factor"
        verbose_name_plural = "Emission Factors"

class ESGData(models.Model):
    SCOPE_CHOICES = [
        ('SCOPE1', 'Scope 1'),
        ('SCOPE2', 'Scope 2'),
        ('SCOPE3', 'Scope 3'),
    ]
    
    layer = models.ForeignKey(LayerProfile, on_delete=models.CASCADE)
    boundary_item = models.ForeignKey(BoundaryItem, on_delete=models.CASCADE)
    scope = models.CharField(max_length=10, choices=SCOPE_CHOICES)
    value = models.DecimalField(max_digits=15, decimal_places=4)
    unit = models.CharField(max_length=50)
    date_recorded = models.DateField()
    submitted_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True)
    is_verified = models.BooleanField(default=False)
    verification_date = models.DateTimeField(null=True, blank=True)
    verified_by = models.ForeignKey(
        CustomUser, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='verified_data'
    )
    
    def __str__(self):
        return f"{self.layer.company_name} - {self.boundary_item.name} - {self.date_recorded}"

    class Meta:
        verbose_name = "ESG Data"
        verbose_name_plural = "ESG Data"
        indexes = [
            models.Index(fields=['layer', 'date_recorded']),
            models.Index(fields=['scope']),
        ]

class DataEditLog(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True)
    esg_data = models.ForeignKey(ESGData, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(auto_now_add=True)
    previous_value = models.TextField()
    new_value = models.TextField()
    action = models.CharField(max_length=50)

    def __str__(self):
        return f"{self.esg_data} - {self.timestamp}"

    class Meta:
        verbose_name = "Data Edit Log"
        verbose_name_plural = "Data Edit Logs"