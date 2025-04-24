from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html
from django.urls import reverse
from django.db.models import Count
from .models import (
    CustomUser, LayerProfile, GroupLayer, SubsidiaryLayer, 
    BranchLayer, AppUser, CSVTemplate
)

@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    list_display = ('email', 'role', 'is_baker_tilly_admin', 'is_active', 'is_staff', 'date_joined', 'last_login', 'get_layers')
    list_filter = ('role', 'is_baker_tilly_admin', 'is_active', 'is_staff', 'date_joined', 'last_login')
    search_fields = ('email', 'app_users__name', 'app_users__layer__company_name')
    ordering = ('date_joined',)
    readonly_fields = ('date_joined', 'last_login', 'password_updated_at')
    
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        (_('Permissions'), {
            'fields': ('role', 'is_baker_tilly_admin', 'is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
            'classes': ('wide',)
        }),
        (_('Password Management'), {'fields': ('must_change_password', 'password_updated_at')}),
        (_('OTP Settings'), {'fields': ('otp_code', 'otp_created_at')}),
        (_('Important dates'), {'fields': ('last_login', 'date_joined')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2', 'role', 'is_baker_tilly_admin', 'is_active', 'is_staff'),
        }),
    )

    def get_layers(self, obj):
        """Get HTML formatted list of layers the user is associated with"""
        layers = []
        for user in obj.app_users.all():
            layer = user.layer
            if layer.layer_type == 'GROUP':
                url_name = 'admin:accounts_grouplayer_change'
            elif layer.layer_type == 'SUBSIDIARY':
                url_name = 'admin:accounts_subsidiarylayer_change'
            else:  # BRANCH
                url_name = 'admin:accounts_branchlayer_change'
            
            layers.append(
                f'<a href="{reverse(url_name, args=[layer.id])}">'
                f'{layer.company_name} ({layer.get_layer_type_display()})</a>'
            )
        return format_html('<br>'.join(layers))
    get_layers.short_description = 'Associated Layers'

@admin.register(GroupLayer)
class GroupLayerAdmin(admin.ModelAdmin):
    list_display = ('company_name', 'company_location', 'company_industry', 
                   'shareholding_ratio', 'company_size', 'get_subsidiaries_count', 'get_total_users')
    search_fields = ('company_name', 'company_location')
    list_filter = ('company_industry', 'created_at')
    readonly_fields = ('created_at',)
    fieldsets = (
        ('Basic Information', {
            'fields': ('company_name', 'company_location', 'company_industry', 'shareholding_ratio', 'layer_type')
        }),
        ('ESG Profile Data', {
            'fields': ('company_size', 'annual_revenue', 'number_of_sites', 'target_customer')
        }),
        ('System Information', {
            'fields': ('created_at', 'created_by_admin')
        }),
    )

    def get_subsidiaries_count(self, obj):
        return obj.subsidiarylayer_set.count()
    get_subsidiaries_count.short_description = 'Subsidiaries'

    def get_total_users(self, obj):
        return obj.app_users.count()
    get_total_users.short_description = 'Total Users'

@admin.register(SubsidiaryLayer)
class SubsidiaryLayerAdmin(admin.ModelAdmin):
    list_display = ('company_name', 'company_industry', 'shareholding_ratio', 
                   'group_layer', 'company_size', 'get_branches_count', 'get_total_users')
    search_fields = ('company_name', 'group_layer__company_name')
    list_filter = ('company_industry', 'created_at', 'group_layer')
    raw_id_fields = ('group_layer',)
    readonly_fields = ('created_at',)
    fieldsets = (
        ('Basic Information', {
            'fields': ('company_name', 'company_location', 'company_industry', 'shareholding_ratio', 'layer_type')
        }),
        ('Hierarchy', {
            'fields': ('group_layer',)
        }),
        ('ESG Profile Data', {
            'fields': ('company_size', 'annual_revenue', 'number_of_sites', 'target_customer')
        }),
        ('System Information', {
            'fields': ('created_at', 'created_by_admin')
        }),
    )

    def get_branches_count(self, obj):
        return obj.branchlayer_set.count()
    get_branches_count.short_description = 'Branches'

    def get_total_users(self, obj):
        return obj.app_users.count()
    get_total_users.short_description = 'Total Users'

@admin.register(BranchLayer)
class BranchLayerAdmin(admin.ModelAdmin):
    list_display = ('company_name', 'company_industry', 'shareholding_ratio', 
                   'subsidiary_layer', 'company_size', 'get_total_users')
    search_fields = ('company_name', 'subsidiary_layer__company_name')
    list_filter = ('company_industry', 'created_at', 'subsidiary_layer')
    raw_id_fields = ('subsidiary_layer',)
    readonly_fields = ('created_at',)
    fieldsets = (
        ('Basic Information', {
            'fields': ('company_name', 'company_location', 'company_industry', 'shareholding_ratio', 'layer_type')
        }),
        ('Hierarchy', {
            'fields': ('subsidiary_layer',)
        }),
        ('ESG Profile Data', {
            'fields': ('company_size', 'annual_revenue', 'number_of_sites', 'target_customer')
        }),
        ('System Information', {
            'fields': ('created_at', 'created_by_admin')
        }),
    )

    def get_total_users(self, obj):
        return obj.app_users.count()
    get_total_users.short_description = 'Total Users'

@admin.register(AppUser)
class AppUserAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'title', 'layer_info', 'user_role')
    search_fields = ('name', 'user__email', 'layer__company_name')
    list_filter = ('layer__layer_type', 'title', 'user__role')
    raw_id_fields = ('user', 'layer')
    readonly_fields = ('user_role',)

    def email(self, obj):
        return obj.user.email
    
    def user_role(self, obj):
        return obj.user.get_role_display()
    user_role.short_description = 'Role'

    def layer_info(self, obj):
        return f"{obj.layer.company_name} ({obj.layer.get_layer_type_display()})"
    layer_info.short_description = 'Company Layer'

@admin.register(CSVTemplate)
class CSVTemplateAdmin(admin.ModelAdmin):
    list_display = ('template_type', 'updated_at', 'file')
    list_filter = ('template_type', 'updated_at')
    readonly_fields = ('updated_at',)

# Customize admin site
admin.site.site_header = 'ESG Platform Administration'
admin.site.site_title = 'ESG Platform Admin'
admin.site.index_title = 'Platform Administration'
