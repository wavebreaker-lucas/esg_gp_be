from django.contrib import admin
from django.db import models
from django.forms import widgets
from django.urls import reverse
from django.utils.html import format_html
from django import forms
from .models.esg import BoundaryItem, EmissionFactor, ESGData, DataEditLog
from .models.templates import (
    ESGFormCategory, ESGForm, ESGMetric,
    Template, TemplateFormSelection, TemplateAssignment,
    ESGMetricSubmission, ESGMetricEvidence
)
from .models import (
    MetricSchemaRegistry, ESGMetricBatchSubmission
)

class JSONEditorWidget(widgets.Textarea):
    """Custom widget for JSON fields that provides a better UI for editing JSON"""
    def __init__(self, attrs=None):
        default_attrs = {
            'class': 'jsoneditor-textarea',
            'rows': 20,
            'style': 'width: 100%; font-family: monospace; white-space: pre; overflow: auto;'
        }
        if attrs:
            default_attrs.update(attrs)
        super().__init__(default_attrs)
    
    class Media:
        css = {
            'all': ('admin/css/jsoneditor.css',)
        }
        js = ('admin/js/jsoneditor.min.js', 'admin/js/json-field-init.js')

class BoundaryItemAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_default')
    list_filter = ('is_default',)
    search_fields = ('name',)

admin.site.register(BoundaryItem, BoundaryItemAdmin)

class EmissionFactorAdmin(admin.ModelAdmin):
    list_display = ('name', 'value', 'unit', 'effective_from', 'effective_to')
    list_filter = ('unit',)
    search_fields = ('name',)

admin.site.register(EmissionFactor, EmissionFactorAdmin)

class ESGDataAdmin(admin.ModelAdmin):
    list_display = ('layer', 'boundary_item', 'scope', 'value', 'unit', 
                   'date_recorded', 'is_verified')
    list_filter = ('scope', 'is_verified', 'layer')
    search_fields = ('layer__company_name', 'boundary_item__name')
    date_hierarchy = 'date_recorded'

admin.site.register(ESGData, ESGDataAdmin)

class DataEditLogAdmin(admin.ModelAdmin):
    list_display = ('user', 'esg_data', 'action', 'timestamp')
    list_filter = ('action',)
    search_fields = ('user__username',)
    date_hierarchy = 'timestamp'
    readonly_fields = ('user', 'esg_data', 'previous_value', 'new_value', 
                      'action', 'timestamp')

admin.site.register(DataEditLog, DataEditLogAdmin)

@admin.register(ESGFormCategory)
class ESGFormCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'icon', 'order']
    search_fields = ['name', 'code']
    ordering = ['order']

@admin.register(ESGForm)
class ESGFormAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'category', 'is_active', 'order']
    list_filter = ['category', 'is_active']
    search_fields = ['code', 'name']
    ordering = ['category', 'order']

@admin.register(ESGMetric)
class ESGMetricAdmin(admin.ModelAdmin):
    list_display = ('name', 'form', 'requires_evidence', 'is_required')
    list_filter = ('form__category', 'form', 'requires_evidence', 'is_required')
    search_fields = ('name', 'description', 'form__name')
    filter_horizontal = ()
    fieldsets = (
        (None, {
            'fields': ('form', 'name', 'description', 'location', 
                       'order', 'requires_evidence', 'is_required')
        }),
        ('JSON Schema Configuration', {
            'fields': ('schema_registry', 'data_schema', 'form_component', 'primary_path', 'ocr_analyzer_id'),
            'classes': ('collapse',),
            'description': 'Configure the JSON schema for this metric, including the primary_path which should point to the main value.'
        }),
    )
    formfield_overrides = {
        models.JSONField: {'widget': JSONEditorWidget},
    }
    
    def get_readonly_fields(self, request, obj=None):
        # Make form field read-only in edit mode to prevent accidental changes
        if obj:  # editing an existing object
            return ('form',) + self.readonly_fields
        return self.readonly_fields

@admin.register(Template)
class TemplateAdmin(admin.ModelAdmin):
    list_display = ['name', 'is_active', 'version', 'created_by']
    list_filter = ['is_active']
    search_fields = ['name', 'description']
    ordering = ['-created_at']

@admin.register(TemplateFormSelection)
class TemplateFormSelectionAdmin(admin.ModelAdmin):
    list_display = ['template', 'form', 'order']
    list_filter = ['template', 'form']
    ordering = ['template', 'order']

@admin.register(TemplateAssignment)
class TemplateAssignmentAdmin(admin.ModelAdmin):
    list_display = ['template', 'layer', 'assigned_to', 'status', 'due_date']
    list_filter = ['status']
    search_fields = ['template__name', 'layer__company_name']
    ordering = ['-assigned_at']

@admin.register(ESGMetricSubmission)
class ESGMetricSubmissionAdmin(admin.ModelAdmin):
    list_display = ('metric', 'assignment', 'layer', 'submitted_by', 'submitted_at', 'is_verified')
    list_filter = ('is_verified', 'metric__form', 'assignment__template')
    search_fields = ('metric__name', 'notes', 'layer__company_name')
    date_hierarchy = 'submitted_at'
    formfield_overrides = {
        models.JSONField: {'widget': JSONEditorWidget},
    }
    readonly_fields = ('submitted_by', 'submitted_at', 'verified_by', 'verified_at', 'batch_submission')
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('metric', 'assignment', 'layer', 'submitted_by')

@admin.register(ESGMetricEvidence)
class ESGMetricEvidenceAdmin(admin.ModelAdmin):
    list_display = ('filename', 'submission', 'uploaded_by', 'uploaded_at', 'is_processed_by_ocr')
    list_filter = ('is_processed_by_ocr', 'uploaded_at')
    search_fields = ('filename', 'description')
    readonly_fields = ('uploaded_by', 'uploaded_at', 'file_type', 'is_processed_by_ocr')
    formfield_overrides = {
        models.JSONField: {'widget': JSONEditorWidget},
    }

@admin.register(MetricSchemaRegistry)
class MetricSchemaRegistryAdmin(admin.ModelAdmin):
    list_display = ('name', 'version', 'created_by', 'created_at', 'is_active', 'metrics_count')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name', 'description')
    readonly_fields = ('created_by', 'created_at', 'updated_at')
    formfield_overrides = {
        models.JSONField: {'widget': JSONEditorWidget},
    }
    
    def has_module_permission(self, request):
        # Allow Baker Tilly admins to see this model in admin
        if hasattr(request.user, 'is_baker_tilly_admin') and request.user.is_baker_tilly_admin:
            return True
        # Otherwise use standard permission check
        return super().has_module_permission(request)
    
    def save_model(self, request, obj, form, change):
        if not change:  # Only set created_by when creating a new object
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
    
    def metrics_count(self, obj):
        count = obj.metrics.count()
        if count > 0:
            return format_html(
                '<a href="{}?schema_registry__id__exact={}">{} metrics</a>',
                reverse('admin:data_management_esgmetric_changelist'),
                obj.pk,
                count
            )
        return '0 metrics'
    metrics_count.short_description = 'Metrics using this schema'

@admin.register(ESGMetricBatchSubmission)
class BatchSubmissionAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'assignment', 'layer', 'submitted_by', 'submitted_at', 'is_verified', 'submission_count')
    list_filter = ('is_verified', 'submitted_at')
    search_fields = ('name', 'notes', 'layer__company_name')
    readonly_fields = ('submitted_by', 'submitted_at', 'verified_by', 'verified_at')
    
    def submission_count(self, obj):
        count = obj.submissions.count()
        return format_html(
            '<a href="{}?batch_submission__id__exact={}">{} submissions</a>',
            reverse('admin:data_management_esgmetricsubmission_changelist'),
            obj.pk,
            count
        )
    submission_count.short_description = 'Submissions'
