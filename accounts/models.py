"""
Database tables definition for custom users
"""

import datetime, uuid
from django.utils import timezone
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils.translation import gettext_lazy as _

class RoleChoices(models.TextChoices):
    CREATOR = "CREATOR", _("Creator")
    MANAGEMENT = "MANAGEMENT", _("Management")
    OPERATION = "OPERATION", _("Operation")

class LayerTypeChoices(models.TextChoices):
    GROUP = "GROUP", _("Group")
    SUBSIDIARY = "SUBSIDIARY", _("Subsidiary")  # Fixed typo from original
    BRANCH = "BRANCH", _("Branch")

class CustomUserManager(BaseUserManager):
    """
    Class for handling custom user creation
    """

    def create_user(self, email, password, **extra_fields):
        """
        Create custom user 

        Args:
            email (string)
            password (string)

        Raises:
            ValueError: if email is missing
            ValueError: if password is missing

        Returns:
            created user
        """
        if not email:
            raise ValueError("The Email field must be set")

        if not password:
            raise ValueError("The Password field must be set")

        email = self.normalize_email(email)
        extra_fields.setdefault('is_active', False)
        extra_fields.setdefault('password_updated_at', timezone.now())
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password, **extra_fields):
        """
        Create and return a superuser with the given email and password.
        """
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('must_change_password', False)

        if not extra_fields.get('is_staff'):
            raise ValueError("Superuser must have is_staff=True.")
        if not extra_fields.get('is_superuser'):
            raise ValueError("Superuser must have is_superuser=True.")

        return self.create_user(email, password, **extra_fields)

    def make_random_password(self, length=8, 
                           allowed_chars="abcdefghjkmnpqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789"):
        """
        Generate a random password.
        """
        import random
        return ''.join(random.choice(allowed_chars) for i in range(length))

    def create_baker_tilly_admin(self, email, password, **extra_fields):
        """
        Create a Baker Tilly admin user with proper permissions.
        
        Args:
            email: Email address for the Baker Tilly admin
            password: Password for the account
            **extra_fields: Additional fields like name, etc.
            
        Returns:
            CustomUser: Created Baker Tilly admin user
            
        Raises:
            ValueError: If email or password is invalid
        """
        if not email or not password:
            raise ValueError("Email and password are required for Baker Tilly admin")
            
        # Set required flags for Baker Tilly admin
        extra_fields.setdefault('is_staff', True)  # Gives admin interface access
        extra_fields.setdefault('is_baker_tilly_admin', True)  # Gives business admin privileges
        extra_fields.setdefault('is_active', True)  # No email verification needed
        extra_fields.setdefault('must_change_password', False)  # Password is set directly
        
        # Create user with Baker Tilly admin settings
        user = self.create_user(email, password, **extra_fields)
        
        return user

class CustomUser(AbstractBaseUser, PermissionsMixin):
    """
    Custom user model where email is the unique identifier for authentication.
    """
    email = models.EmailField(unique=True)
    date_joined = models.DateTimeField(auto_now_add=True)

    is_active = models.BooleanField(default=False)
    is_staff = models.BooleanField(default=False)
    
    # OTP fields for two-factor authentication
    otp_code = models.CharField(max_length=6, blank=True, null=True)
    otp_created_at = models.DateTimeField(blank=True, null=True)
    
    # Password management
    password_updated_at = models.DateTimeField(blank=True, null=True)
    reset_token = models.UUIDField(default=uuid.uuid4, blank=True, null=True)
    reset_token_created_at = models.DateTimeField(blank=True, null=True)
    must_change_password = models.BooleanField(default=True)

    role = models.CharField(
        max_length=20,
        choices=RoleChoices.choices,
        default=RoleChoices.OPERATION
    )

    is_baker_tilly_admin = models.BooleanField(
        default=False,
        help_text="Designates whether this user is a Baker Tilly administrator with access to all client data."
    )

    objects = CustomUserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []  # Email & password are already required

    def __str__(self):
        return self.email
    
    def is_otp_expired(self, expiry_minutes=10):
        """
        Returns True if OTP has expired after expiry_minutes (default 10).
        """
        if not self.otp_created_at:
            return True
        return (timezone.now() - self.otp_created_at) > datetime.timedelta(minutes=expiry_minutes)

    @property
    def is_admin(self):
        """Check if user has any admin privileges"""
        return self.is_superuser or self.is_baker_tilly_admin

class LayerProfile(models.Model):
    """
    Base model for company hierarchy layers
    """
    company_name = models.CharField(max_length=100)
    company_industry = models.CharField(max_length=100)
    shareholding_ratio = models.DecimalField(
        max_digits=5, decimal_places=2, default=100.00)
    layer_type = models.CharField(
        max_length=20,
        choices=LayerTypeChoices.choices
    )
    company_location = models.CharField(max_length=100)
    
    # New fields for ESG metadata
    company_size = models.PositiveIntegerField(
        null=True, blank=True, 
        help_text="Number of employees"
    )
    annual_revenue = models.DecimalField(
        max_digits=14, decimal_places=2, 
        null=True, blank=True,
        help_text="Annual revenue in millions"
    )
    number_of_sites = models.PositiveIntegerField(
        null=True, blank=True, 
        help_text="Number of sites/entities"
    )
    target_customer = models.TextField(
        blank=True, null=True,
        help_text="Description of target customers"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    created_by_admin = models.ForeignKey(
        'CustomUser', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='created_layers'
    )

    class Meta:
        verbose_name = "Company Layer"
        verbose_name_plural = "Company Layers"

    def __str__(self):
        return f"{self.company_name} ({self.get_layer_type_display()})"

class GroupLayer(LayerProfile):
    """Top level in company hierarchy"""
    class Meta:
        verbose_name = "Group"
        verbose_name_plural = "Groups"

class SubsidiaryLayer(LayerProfile):  # Fixed typo in class name
    """Second level in company hierarchy"""
    group_layer = models.ForeignKey(GroupLayer, on_delete=models.CASCADE)

    class Meta:
        verbose_name = "Subsidiary"
        verbose_name_plural = "Subsidiaries"

class BranchLayer(LayerProfile):
    """Third level in company hierarchy"""
    subsidiary_layer = models.ForeignKey(SubsidiaryLayer, on_delete=models.CASCADE)  # Fixed typo in field name

    class Meta:
        verbose_name = "Branch"
        verbose_name_plural = "Branches"

class AppUser(models.Model):
    """
    Extended user profile with company layer association
    """
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="app_users")
    name = models.CharField(max_length=75)
    title = models.CharField(max_length=20, null=True, blank=True)
    layer = models.ForeignKey(LayerProfile, on_delete=models.CASCADE, related_name='app_users')

    class Meta:
        unique_together = ("user", "layer")
        verbose_name = "App User"
        verbose_name_plural = "App Users"

    def __str__(self):
        return f"{self.name} - {self.layer.company_name}"

class CSVTemplate(models.Model):
    """
    Model for managing CSV import templates
    """
    TEMPLATE_TYPE_CHOICES = (
        ('default', 'Default'),
        ('superuser', 'Superuser'),
        ('appuser', 'App User'),
    )
    template_type = models.CharField(max_length=20, choices=TEMPLATE_TYPE_CHOICES, default='default')
    file = models.FileField(upload_to='templates/', blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "CSV Template"
        verbose_name_plural = "CSV Templates"

    def __str__(self):
        return f"CSV Template ({self.template_type})"
