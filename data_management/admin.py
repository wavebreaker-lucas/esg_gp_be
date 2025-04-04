from django.contrib import admin
from .models.esg import BoundaryItem, EmissionFactor, ESGData, DataEditLog
from .models.templates import (
    ESGFormCategory, ESGForm, ESGMetric,
    Template, TemplateFormSelection, TemplateAssignment,
    ESGMetricSubmission, ESGMetricEvidence,
    MetricValueField, MetricValue,
    ReportedMetricValue
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

class MetricValueInline(admin.TabularInline):
    model = MetricValue
    extra = 0
    fields = ['field', 'numeric_value', 'text_value']
    raw_id_fields = ['field']

@admin.register(ESGMetric)
class ESGMetricAdmin(admin.ModelAdmin):
    list_display = ['name', 'form', 'unit_type', 'location', 'is_required', 'is_multi_value', 'aggregates_inputs', 'order']
    list_filter = ['form', 'unit_type', 'location', 'is_required', 'is_multi_value', 'aggregates_inputs']
    search_fields = ['name', 'description']
    ordering = ['form', 'order']
    
    class MetricValueFieldInline(admin.TabularInline):
        model = MetricValueField
        extra = 1
        fields = ['field_key', 'display_name', 'column_header', 'display_type', 'order', 'is_required']
    
    inlines = [MetricValueFieldInline]

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
    list_display = ['metric', 'assignment', 'value', 'text_value', 'reporting_period', 'submitted_by', 'is_verified', 'get_reported_value_link']
    list_filter = ['is_verified', 'metric__form', 'reporting_period', 'metric__is_multi_value']
    search_fields = ['metric__name', 'assignment__template__name', 'assignment__layer__company_name']
    date_hierarchy = 'submitted_at'
    raw_id_fields = ['metric', 'assignment', 'submitted_by', 'verified_by']
    readonly_fields = ['reported_value']
    list_select_related = ('metric', 'assignment', 'layer', 'submitted_by', 'reported_value')
    
    inlines = [MetricValueInline]
    
    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related('multi_values', 'reported_value')

    def get_reported_value_link(self, obj):
        from django.urls import reverse
        from django.utils.html import format_html
        if obj.reported_value:
            link = reverse("admin:data_management_reportedmetricvalue_change", args=[obj.reported_value.id])
            return format_html('<a href="{}">{}</a>', link, obj.reported_value.id)
        return "N/A"
    get_reported_value_link.short_description = 'Reported Value ID'
    get_reported_value_link.admin_order_field = 'reported_value'

@admin.register(MetricValueField)
class MetricValueFieldAdmin(admin.ModelAdmin):
    list_display = ['display_name', 'field_key', 'metric', 'display_type', 'order', 'is_required']
    list_filter = ['display_type', 'is_required', 'metric__form']
    search_fields = ['display_name', 'field_key', 'metric__name']
    ordering = ['metric', 'order']
    raw_id_fields = ['metric']

@admin.register(MetricValue)
class MetricValueAdmin(admin.ModelAdmin):
    list_display = ['get_field_display', 'submission', 'numeric_value', 'text_value']
    list_filter = ['field__metric']
    search_fields = ['field__display_name', 'submission__metric__name']
    raw_id_fields = ['submission', 'field']
    
    def get_field_display(self, obj):
        return f"{obj.field.display_name} ({obj.field.field_key})"
    get_field_display.short_description = 'Field'

@admin.register(ESGMetricEvidence)
class ESGMetricEvidenceAdmin(admin.ModelAdmin):
    list_display = ['get_submission_display', 'filename', 'file_type', 'uploaded_by', 'uploaded_at', 'is_standalone']
    list_filter = ['file_type', 'is_processed_by_ocr']
    search_fields = ['filename', 'description']
    date_hierarchy = 'uploaded_at'
    raw_id_fields = ['submission', 'uploaded_by']
    
    def get_submission_display(self, obj):
        """Safely display submission information"""
        if obj.submission:
            return f"{obj.submission.metric.name} ({obj.submission.id})"
        return "Standalone"
    get_submission_display.short_description = 'Submission'
    
    def is_standalone(self, obj):
        """Display if evidence is standalone (not attached to a submission)"""
        return obj.submission is None
    is_standalone.boolean = True
    is_standalone.short_description = "Standalone"

@admin.register(ReportedMetricValue)
class ReportedMetricValueAdmin(admin.ModelAdmin):
    list_display = ('metric', 'assignment', 'layer', 'reporting_period', 'value', 'text_value', 'is_verified', 'last_updated_at')
    list_filter = ('metric__form', 'metric', 'assignment__template', 'assignment__reporting_year', 'reporting_period', 'is_verified', 'layer')
    search_fields = ('metric__name', 'assignment__template__name', 'layer__company_name', 'text_value')
    readonly_fields = (
        'assignment', 'metric', 'layer', 'reporting_period', 
        'value', 'text_value', 'calculated_at', 'last_updated_at', 
        'verified_by', 'verified_at'
    )
    list_select_related = ('metric', 'assignment', 'layer', 'verified_by')
