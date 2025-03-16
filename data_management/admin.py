from django.contrib import admin
from .models.esg import BoundaryItem, EmissionFactor, ESGData, DataEditLog
from .models.templates import (
    ESGFormCategory, ESGForm, ESGMetric,
    Template, TemplateFormSelection, TemplateAssignment,
    ESGMetricSubmission, ESGMetricEvidence
)

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
    list_display = ['name', 'form', 'unit_type', 'location', 'is_required', 'order']
    list_filter = ['form', 'unit_type', 'location', 'is_required']
    search_fields = ['name', 'description']
    ordering = ['form', 'order']

@admin.register(Template)
class TemplateAdmin(admin.ModelAdmin):
    list_display = ['name', 'reporting_period', 'is_active', 'version', 'created_by']
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
    list_display = ['metric', 'assignment', 'value', 'text_value', 'reporting_period', 'submitted_by', 'is_verified']
    list_filter = ['is_verified', 'metric__form', 'reporting_period']
    search_fields = ['metric__name', 'assignment__template__name', 'assignment__layer__company_name']
    date_hierarchy = 'submitted_at'
    raw_id_fields = ['metric', 'assignment', 'submitted_by', 'verified_by']

@admin.register(ESGMetricEvidence)
class ESGMetricEvidenceAdmin(admin.ModelAdmin):
    list_display = ['submission', 'filename', 'file_type', 'uploaded_by', 'uploaded_at']
    list_filter = ['file_type']
    search_fields = ['filename', 'description', 'submission__metric__name']
    date_hierarchy = 'uploaded_at'
    raw_id_fields = ['submission', 'uploaded_by']
