from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _
from .models import (
    CustomUser, LayerProfile, GroupLayer, SubsidiaryLayer, 
    BranchLayer, AppUser, CSVTemplate
)

@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    list_display = ('email', 'role', 'is_active', 'is_staff', 'date_joined')
    list_filter = ('role', 'is_active', 'is_staff')
    search_fields = ('email',)
    ordering = ('date_joined',)
    
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        (_('Permissions'), {'fields': ('role', 'is_active', 'is_staff', 'is_superuser')}),
        (_('Password Management'), {'fields': ('must_change_password', 'password_updated_at')}),
        (_('OTP Settings'), {'fields': ('otp_code', 'otp_created_at')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2', 'role', 'is_active', 'is_staff'),
        }),
    )

@admin.register(GroupLayer)
class GroupLayerAdmin(admin.ModelAdmin):
    list_display = ('company_name', 'company_location', 'company_industry', 'shareholding_ratio')
    search_fields = ('company_name', 'company_location')
    list_filter = ('company_industry',)

@admin.register(SubsidiaryLayer)
class SubsidiaryLayerAdmin(admin.ModelAdmin):
    list_display = ('company_name', 'company_industry', 'shareholding_ratio', 'group_layer')
    search_fields = ('company_name', 'group_layer__company_name')
    list_filter = ('company_industry', 'group_layer')
    raw_id_fields = ('group_layer',)

@admin.register(BranchLayer)
class BranchLayerAdmin(admin.ModelAdmin):
    list_display = ('company_name', 'company_industry', 'shareholding_ratio', 'subsidiary_layer')
    search_fields = ('company_name', 'subsidiary_layer__company_name')
    list_filter = ('company_industry', 'subsidiary_layer')
    raw_id_fields = ('subsidiary_layer',)

@admin.register(AppUser)
class AppUserAdmin(admin.ModelAdmin):
    list_display = ('name', 'user', 'title', 'layer')
    search_fields = ('name', 'user__email', 'layer__company_name')
    list_filter = ('layer__layer_type', 'title')
    raw_id_fields = ('user', 'layer')

@admin.register(CSVTemplate)
class CSVTemplateAdmin(admin.ModelAdmin):
    list_display = ('template_type', 'updated_at')
    list_filter = ('template_type',)
