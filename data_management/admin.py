from django.contrib import admin
import logging # Import the logging module
from .models.esg import BoundaryItem, EmissionFactor, ESGData, DataEditLog
from .models.templates import (
    ESGFormCategory, ESGForm,
    Template, TemplateFormSelection, TemplateAssignment,
    ESGMetricSubmission, ESGMetricEvidence,
    ReportedMetricValue
)
from polymorphic.admin import PolymorphicParentModelAdmin, PolymorphicChildModelAdmin, PolymorphicChildModelFilter
from .models.polymorphic_metrics import (
    BaseESGMetric, BasicMetric, TabularMetric, MaterialTrackingMatrixMetric,
    TimeSeriesMetric, MultiFieldTimeSeriesMetric, MultiFieldMetric
)
from .models.submission_data import (
    BasicMetricData, TimeSeriesDataPoint, TabularMetricRow,
    MaterialMatrixDataPoint, MultiFieldTimeSeriesDataPoint, MultiFieldDataPoint
)

# Initialize the logger
logger = logging.getLogger(__name__)

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

# --- Admin Inlines for Submission Data Models ---
class TimeSeriesDataPointInline(admin.TabularInline):
    model = TimeSeriesDataPoint
    extra = 1
    fields = ('period', 'value')
    ordering = ('period',)

class BasicMetricDataInline(admin.StackedInline):
    model = BasicMetricData
    extra = 0
    fields = ('value_numeric', 'value_text')

class TabularMetricRowInline(admin.TabularInline):
    model = TabularMetricRow
    extra = 1
    fields = ('row_index', 'row_data')
    ordering = ('row_index',)

@admin.register(ESGMetricSubmission)
class ESGMetricSubmissionAdmin(admin.ModelAdmin):
    list_display = (
        'id', 
        'assignment', 
        'metric_display',
        'get_submitted_value',
        'reporting_period', 
        'submitted_by', 
        'submitted_at',
        'is_verified',
        'layer'
    )
    list_filter = ('assignment__template', 'assignment__layer', 'metric', 'reporting_period', 'is_verified', 'submitted_by')
    search_fields = ('metric__name', 'assignment__template__name', 'assignment__layer__company_name', 'notes', 'verification_notes')
    readonly_fields = ('submitted_at', 'updated_at', 'verified_at', 'get_submitted_value')
    raw_id_fields = ['metric', 'assignment', 'submitted_by', 'verified_by']
    list_select_related = ('metric', 'assignment', 'layer', 'submitted_by', 'verified_by')
    inlines = []
    
    def get_inlines(self, request, obj=None):
        """Dynamically determine which inline(s) to include based on the metric type."""
        if obj is None:
            return []  # No inlines when creating a new submission
            
        try:
            logger.info(f"Getting inlines for submission {obj.pk}, metric ID: {obj.metric.pk}")
            metric = obj.metric.get_real_instance()
            logger.info(f"Metric type: {type(metric).__name__}")
            
            inlines = []
            
            if isinstance(metric, BasicMetric):
                logger.info(f"Adding BasicMetricDataInline for submission {obj.pk}")
                inlines.append(BasicMetricDataInline)
            elif isinstance(metric, TimeSeriesMetric):
                logger.info(f"Adding TimeSeriesDataPointInline for submission {obj.pk}")
                inlines.append(TimeSeriesDataPointInline)
            elif isinstance(metric, TabularMetric):
                logger.info(f"Adding TabularMetricRowInline for submission {obj.pk}")
                inlines.append(TabularMetricRowInline)
            # Add cases for other metric types as needed
            
            logger.info(f"Returning inlines: {[i.__name__ for i in inlines]}")
            return inlines
            
        except Exception as e:
            logger.error(f"Error determining inlines for submission {obj.pk}: {e}", exc_info=True)
            return []  # Fallback to no inlines

    def metric_display(self, obj):
        return obj.metric.name if obj.metric else "No Metric"
    metric_display.short_description = "Metric"
    
    def get_submitted_value(self, obj):
        """Display the actual submitted value based on metric type."""
        try:
            # Ensure we have the specific metric instance
            metric = obj.metric.get_real_instance()
            
            # Check metric type and fetch corresponding data
            if isinstance(metric, BasicMetric):
                try:
                    data = obj.basic_data
                    val = data.value_numeric if data.value_numeric is not None else data.value_text
                    return val
                except obj._meta.get_field('basic_data').related_model.DoesNotExist:
                    return "(No basic data)"
            elif isinstance(metric, TimeSeriesMetric):
                # Show all time series data points, regardless of count
                points = obj.timeseries_data_points.all().order_by('period')
                count = points.count()
                if count == 0:
                    return "(No data points)"
                else:
                    # Always show all points with dates and values
                    return "<br>".join([f"{p.period.strftime('%Y-%m-%d')}: {p.value}" for p in points])
            elif isinstance(metric, TabularMetric):
                return f"{obj.tabular_rows.count()} rows"
            # Add checks for other metric types (Material, MultiField, etc.) here
            else:
                return "(Data type not shown)"
        except Exception as e:
            # Catch errors like missing related objects or metric type issues
            logger.error(f"Error getting submitted value for Submission {obj.pk}: {e}")
            return "(Error)"
    get_submitted_value.short_description = "Submitted Value"

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
        elif obj.intended_metric:
            return f"Intended: {obj.intended_metric.name}"
        return "Standalone"
    get_submission_display.short_description = 'Submission/Metric'
    
    def is_standalone(self, obj):
        """Display if evidence is standalone (not attached to a submission)"""
        return obj.submission is None
    is_standalone.boolean = True
    is_standalone.short_description = "Standalone"

@admin.register(ReportedMetricValue)
class ReportedMetricValueAdmin(admin.ModelAdmin):
    list_display = (
        'metric', 'assignment', 'layer', 'reporting_period', 
        'aggregated_numeric_value', 'aggregated_text_value',
        'source_submission_count', 'last_updated_at'
    )
    list_filter = (
        'metric__polymorphic_ctype__model',
        'metric', 'assignment__template', 
        'assignment__reporting_year', 'reporting_period', 'layer'
    )
    search_fields = (
        'metric__name', 'assignment__template__name', 'layer__company_name', 
        'aggregated_numeric_value', 'aggregated_text_value'
    )
    readonly_fields = (
        'assignment', 'metric', 'layer', 'reporting_period', 
        'aggregated_numeric_value', 'aggregated_text_value',
        'calculated_at', 'last_updated_at',
        'source_submission_count', 'first_submission_at', 'last_submission_at'
    )
    list_select_related = ('metric', 'assignment', 'layer')
    inlines = []

@admin.register(BasicMetric)
class BasicMetricAdmin(PolymorphicChildModelAdmin):
    base_model = BasicMetric
    # Optional: Customize admin options specific to BasicMetric if needed
    # e.g., add 'unit_type', 'custom_unit' to list_display or fieldsets

@admin.register(TabularMetric)
class TabularMetricAdmin(PolymorphicChildModelAdmin):
    base_model = TabularMetric
    # Optional: Customize for TabularMetric (e.g., display column_definitions info)

@admin.register(MaterialTrackingMatrixMetric)
class MaterialTrackingMatrixMetricAdmin(PolymorphicChildModelAdmin):
    base_model = MaterialTrackingMatrixMetric
    # Optional: Customize

@admin.register(TimeSeriesMetric)
class TimeSeriesMetricAdmin(PolymorphicChildModelAdmin):
    base_model = TimeSeriesMetric
    # Optional: Customize (e.g., show frequency, aggregation_method)

@admin.register(MultiFieldTimeSeriesMetric)
class MultiFieldTimeSeriesMetricAdmin(PolymorphicChildModelAdmin):
    base_model = MultiFieldTimeSeriesMetric
    # Optional: Customize

@admin.register(MultiFieldMetric)
class MultiFieldMetricAdmin(PolymorphicChildModelAdmin):
    base_model = MultiFieldMetric
    # Optional: Customize

@admin.register(BaseESGMetric)
class BaseESGMetricAdmin(PolymorphicParentModelAdmin):
    base_model = BaseESGMetric
    # List all registered child models
    child_models = (
        BasicMetric,
        TabularMetric,
        MaterialTrackingMatrixMetric,
        TimeSeriesMetric,
        MultiFieldTimeSeriesMetric,
        MultiFieldMetric,
        # Add other metric types here if they are created and registered
    )
    list_display = ('name', 'form', 'polymorphic_ctype', 'order', 'location', 'is_required')
    list_filter = (PolymorphicChildModelFilter, 'form', 'location', 'is_required') # Filter by specific metric type
    search_fields = ('name', 'description', 'form__name', 'form__code')
    ordering = ('form', 'order')
    # Common fields for the list view and edit view of the base model itself

# --- Register submission data models with admin ---
@admin.register(TimeSeriesDataPoint)
class TimeSeriesDataPointAdmin(admin.ModelAdmin):
    list_display = ['submission', 'period', 'value']
    list_filter = ['period', 'submission__metric']
    search_fields = ['submission__id', 'value']
    ordering = ['period']
    date_hierarchy = 'period'
    raw_id_fields = ['submission']

@admin.register(BasicMetricData)
class BasicMetricDataAdmin(admin.ModelAdmin):
    list_display = ['submission', 'value_numeric', 'value_text']
    search_fields = ['submission__id', 'value_numeric', 'value_text']
    raw_id_fields = ['submission']

@admin.register(TabularMetricRow)
class TabularMetricRowAdmin(admin.ModelAdmin):
    list_display = ['submission', 'row_index']
    list_filter = ['submission__metric']
    search_fields = ['submission__id']
    ordering = ['submission', 'row_index']
    raw_id_fields = ['submission']
