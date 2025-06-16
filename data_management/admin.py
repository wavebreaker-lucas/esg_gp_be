from django.contrib import admin
import logging # Import the logging module
from django import forms
from django.db.models import Q
from django.utils.html import format_html
from .models.esg import BoundaryItem, EmissionFactor, ESGData, DataEditLog
from .models.templates import (
    ESGFormCategory, ESGForm,
    Template, TemplateFormSelection, TemplateAssignment,
    ESGMetricSubmission, ESGMetricEvidence,
    ReportedMetricValue, FormCompletionStatus
)
from polymorphic.admin import PolymorphicParentModelAdmin, PolymorphicChildModelAdmin, PolymorphicChildModelFilter
from .models.polymorphic_metrics import (
    BaseESGMetric, 
    BasicMetric, 
    TabularMetric, 
    MaterialTrackingMatrixMetric,
    TimeSeriesMetric, 
    MultiFieldTimeSeriesMetric, 
    MultiFieldMetric,
    VehicleTrackingMetric, 
    FuelConsumptionMetric,
    VehicleType, 
    FuelType, 
    FuelSourceType,
    StationaryFuelType,
    ChecklistMetric
)
from .models.submission_data import (
    BasicMetricData, 
    TimeSeriesDataPoint, 
    TabularMetricRow,
    MaterialMatrixDataPoint, 
    MultiFieldTimeSeriesDataPoint, 
    MultiFieldDataPoint,
    VehicleRecord, 
    VehicleMonthlyData, 
    VehicleDataSource, 
    FuelRecord, 
    FuelMonthlyData,
    ChecklistResponse
)
from .models.factors import GHGEmissionFactor, PollutantFactor, EnergyConversionFactor
from .models.results import CalculatedEmissionValue
from .models.reporting import ChecklistReport

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
    list_display = ['template', 'form', 'order', 'get_deprecated_notice']
    list_filter = ['template', 'form']
    search_fields = ['template__name', 'form__name']
    raw_id_fields = ['template', 'form']
    readonly_fields = ['is_completed', 'completed_at', 'completed_by']
    
    def get_deprecated_notice(self, obj):
        return "Use FormCompletionStatus" if obj.is_completed else "-"
    get_deprecated_notice.short_description = "Completion Status (Deprecated)"
    
    def get_fieldsets(self, request, obj=None):
        fieldsets = [
            ('Form Selection', {
                'fields': ('template', 'form', 'order', 'regions')
            }),
            ('Deprecated Completion Fields', {
                'fields': ('is_completed', 'completed_at', 'completed_by'),
                'classes': ('collapse',),
                'description': 'These fields are deprecated. Use FormCompletionStatus model instead.'
            })
        ]
        return fieldsets

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

# --- Add MaterialMatrix inline ---
class MaterialMatrixDataPointInline(admin.TabularInline):
    model = MaterialMatrixDataPoint
    extra = 1
    fields = ('material_type', 'period', 'value', 'unit')
    ordering = ('period', 'material_type')

# Custom form for VehicleRecord that uses the new ForeignKey relationships
class VehicleRecordForm(forms.ModelForm):
    class Meta:
        model = VehicleRecord
        fields = '__all__'
        widgets = {
            'submission': forms.HiddenInput(),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        instance = kwargs.get('instance')
        initial = kwargs.get('initial', {})
        
        submission_id = None
        if instance and instance.submission_id:
            submission_id = instance.submission_id
        elif 'submission' in initial:
            submission_id = initial.get('submission')
        
        if submission_id:
            try:
                # Get the submission and metric
                submission = ESGMetricSubmission.objects.get(pk=submission_id)
                metric = submission.metric.get_real_instance()
                
                # Only proceed if it's a VehicleTrackingMetric
                if isinstance(metric, VehicleTrackingMetric):
                    # Filter choices to only those associated with this metric
                    self.fields['vehicle_type'].queryset = metric.vehicle_types.all()
                    self.fields['fuel_type'].queryset = metric.fuel_types.all()
                    
                    logger.info(f"Loaded vehicle and fuel choices from metric {metric.pk} for submission {submission_id}")
            except Exception as e:
                logger.error(f"Error loading choices for VehicleRecordForm: {e}", exc_info=True)

class VehicleRecordInline(admin.StackedInline):
    """Inline admin for VehicleRecord objects in the ESGMetricSubmission admin."""
    model = VehicleRecord
    form = VehicleRecordForm
    extra = 1
    fields = ('brand', 'model', 'registration_number', 'vehicle_type', 'fuel_type', 'notes', 'is_active')

    def get_formset(self, request, obj=None, **kwargs):
        """Override to customize the inline formset for VehicleRecords."""
        formset = super().get_formset(request, obj, **kwargs)
        
        # Store the original __init__ method
        original_init = formset.__init__
        
        # Define a new __init__ method that sets up the vehicle and fuel type choices
        def new_init(self, *args, **kwargs):
            # Call the original __init__
            original_init(self, *args, **kwargs)
            
            # Set up vehicle and fuel type choices for each form
            if obj is not None:
                try:
                    # Get the specific metric instance
                    metric = obj.metric.get_real_instance()
                    if isinstance(metric, VehicleTrackingMetric):
                        # Get the vehicle and fuel types
                        vehicle_types = metric.vehicle_types.all()
                        fuel_types = metric.fuel_types.all()
                        
                        # Apply to each form in the formset
                        for form in self.forms:
                            form.fields['vehicle_type'].queryset = vehicle_types
                            form.fields['fuel_type'].queryset = fuel_types
                            
                        # Also set for the empty form
                        if hasattr(self, 'empty_form'):
                            self.empty_form.fields['vehicle_type'].queryset = vehicle_types
                            self.empty_form.fields['fuel_type'].queryset = fuel_types
                except Exception as e:
                    logger.error(f"Error setting up vehicle and fuel types in inline formset: {e}")
        
        # Replace the formset's __init__ method
        formset.__init__ = new_init
        
        return formset

class VehicleMonthlyDataInline(admin.TabularInline):
    model = VehicleMonthlyData
    extra = 1
    fields = ('period', 'kilometers', 'fuel_consumed', 'emission_calculated', 'emission_value', 'emission_unit')
    ordering = ('period',)

class VehicleDataSourceInline(admin.TabularInline):
    model = VehicleDataSource
    extra = 1
    fields = ('source_date', 'source_reference', 'kilometers', 'fuel_consumed', 'location', 'notes')
    ordering = ('source_date',)

class FuelMonthlyDataInline(admin.TabularInline):
    model = FuelMonthlyData
    extra = 1
    fields = ('period', 'quantity', 'emission_calculated', 'emission_value', 'emission_unit')
    ordering = ('period',)

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
            elif isinstance(metric, VehicleTrackingMetric):
                logger.info(f"Adding VehicleRecordInline for submission {obj.pk}")
                inlines.append(VehicleRecordInline)
            elif isinstance(metric, FuelConsumptionMetric):
                logger.info(f"Adding FuelRecordInline for submission {obj.pk}")
                inlines.append(FuelRecordInline)
            elif isinstance(metric, MaterialTrackingMatrixMetric):
                logger.info(f"Adding MaterialMatrixDataPointInline for submission {obj.pk}")
                inlines.append(MaterialMatrixDataPointInline)
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
            elif isinstance(metric, VehicleTrackingMetric):
                vehicle_count = obj.vehicle_records.count()
                if vehicle_count == 0:
                    return "(No vehicles)"
                return f"{vehicle_count} vehicle(s)"
            elif isinstance(metric, FuelConsumptionMetric):
                source_count = obj.fuel_records.count()
                if source_count == 0:
                    return "(No fuel sources)"
                return f"{source_count} fuel source(s)"
            elif isinstance(metric, MaterialTrackingMatrixMetric):
                return f"{obj.material_data_points.count()} material data points"
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
    list_display = ['get_submission_display', 'filename', 'file_type', 'uploaded_by', 'uploaded_at', 'is_standalone', 'get_vehicle_display']
    list_filter = ['file_type', 'is_processed_by_ocr', 'target_vehicle__vehicle_type']
    search_fields = ['filename', 'description', 'target_vehicle__registration_number']
    date_hierarchy = 'uploaded_at'
    raw_id_fields = ['uploaded_by', 'target_vehicle']
    
    def get_submission_display(self, obj):
        """Safely display metric information"""
        if obj.intended_metric:
            return f"Intended: {obj.intended_metric.name}"
        return "Standalone"
    get_submission_display.short_description = 'Metric'
    
    def is_standalone(self, obj):
        """Display if evidence is standalone (not attached to a specific metric)"""
        return obj.intended_metric is None
    is_standalone.boolean = True
    is_standalone.short_description = "Standalone"
    
    def get_vehicle_display(self, obj):
        """Display vehicle information if associated"""
        if obj.target_vehicle:
            return f"{obj.target_vehicle.registration_number} ({obj.target_vehicle.brand} {obj.target_vehicle.model})"
        return "-"
    get_vehicle_display.short_description = "Vehicle"

@admin.register(ReportedMetricValue)
class ReportedMetricValueAdmin(admin.ModelAdmin):
    list_display = (
        'metric', 'assignment', 'layer', 'reporting_period', 
        'aggregated_numeric_value', 'aggregated_text_value',
        'source_submission_count', 'last_updated_at',
        'has_emissions_calculation'
    )
    list_filter = (
        'metric__polymorphic_ctype__model',
        'metric', 'assignment__template', 
        'assignment__reporting_year', 'reporting_period', 'layer',
        'level'
    )
    search_fields = (
        'metric__name', 'assignment__template__name', 'layer__company_name', 
        'aggregated_numeric_value', 'aggregated_text_value'
    )
    readonly_fields = (
        'assignment', 'metric', 'layer', 'reporting_period', 
        'aggregated_numeric_value', 'aggregated_text_value',
        'calculated_at', 'last_updated_at',
        'source_submission_count', 'first_submission_at', 'last_submission_at',
        'emission_calculation_summary'
    )
    list_select_related = ('metric', 'assignment', 'layer')
    inlines = []
    actions = ['recalculate_emissions']
    
    def has_emissions_calculation(self, obj):
        """Check if this RPV has associated emission calculations"""
        return obj.derived_ghg_emissions.filter(is_primary_record=True).exists()
    has_emissions_calculation.boolean = True
    has_emissions_calculation.short_description = "Has Emissions"
    
    def emission_calculation_summary(self, obj):
        """Show a summary of emission calculations for this RPV"""
        from django.utils.safestring import mark_safe
        
        emissions = obj.derived_ghg_emissions.filter(is_primary_record=True)
        if not emissions.exists():
            return "No emission calculations found"
        
        # Get the primary record
        primary = emissions.first()
        
        # Check if it has related records
        related_records = []
        if primary.related_group_id:
            related_records = obj.derived_ghg_emissions.filter(
                related_group_id=primary.related_group_id,
                is_primary_record=False
            )
        
        # Build the summary HTML
        html = f"<div style='margin: 10px 0;'>"
        html += f"<p><strong>Primary Calculation:</strong> {primary.calculated_value} {primary.emission_unit} ({primary.emission_scope})</p>"
        html += f"<p><strong>Factor:</strong> {primary.emission_factor}</p>"
        
        # Show related records if any
        if related_records:
            html += f"<p><strong>Component Calculations ({related_records.count()}):</strong></p>"
            html += "<ul>"
            for record in related_records:
                vehicle_info = ""
                if record.calculation_metadata:
                    vehicle_type = record.calculation_metadata.get('vehicle_label', '')
                    fuel_type = record.calculation_metadata.get('fuel_label', '')
                    if vehicle_type and fuel_type:
                        vehicle_info = f" - {vehicle_type} / {fuel_type}"
                html += f"<li>{record.calculated_value} {record.emission_unit} ({float(record.proportion)*100:.1f}%){vehicle_info}</li>"
            html += "</ul>"
            
        html += "</div>"
        return mark_safe(html)
    emission_calculation_summary.short_description = "Emission Calculations"
    
    def recalculate_emissions(self, request, queryset):
        """Admin action to recalculate emissions for selected ReportedMetricValues"""
        from .services.emissions import calculate_emissions_for_activity_value
        
        success_count = 0
        error_count = 0
        record_count = 0
        
        for rpv in queryset:
            try:
                results = calculate_emissions_for_activity_value(rpv)
                if results:
                    success_count += 1
                    record_count += len(results)
                else:
                    error_count += 1
            except Exception as e:
                self.message_user(
                    request, 
                    f"Error calculating emissions for RPV {rpv.pk}: {str(e)}",
                    level='ERROR'
                )
                error_count += 1
                
        self.message_user(
            request,
            f"Recalculated emissions for {success_count} values ({record_count} calculation records created). {error_count} errors.",
            level='SUCCESS' if error_count == 0 else 'WARNING'
        )
    recalculate_emissions.short_description = "Recalculate emissions for selected items"

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

@admin.register(VehicleType)
class VehicleTypeAdmin(admin.ModelAdmin):
    list_display = ['value', 'label']
    search_fields = ['value', 'label']
    ordering = ['label']

@admin.register(FuelType)
class FuelTypeAdmin(admin.ModelAdmin):
    list_display = ['value', 'label']
    search_fields = ['value', 'label']
    ordering = ['label']

@admin.register(VehicleTrackingMetric)
class VehicleTrackingMetricAdmin(PolymorphicChildModelAdmin):
    base_model = VehicleTrackingMetric
    # Custom fieldsets for better organization
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'form', 'description', 'order', 'is_required', 'help_text', 'location', 'ocr_analyzer_id')
        }),
        ('Vehicle Configuration', {
            'fields': ('vehicle_types', 'fuel_types', 'emission_factor_mapping', 'reporting_year', 
                     'frequency', 'show_registration_number')
        }),
        ('Emission Configuration', {
            'fields': ('emission_category', 'emission_sub_category')
        })
    )
    filter_horizontal = ('vehicle_types', 'fuel_types')  # Makes ManyToMany fields easier to manage

@admin.register(FuelSourceType)
class FuelSourceTypeAdmin(admin.ModelAdmin):
    list_display = ['value', 'label']
    search_fields = ['value', 'label']
    ordering = ['label']

@admin.register(StationaryFuelType)
class StationaryFuelTypeAdmin(admin.ModelAdmin):
    list_display = ['value', 'label', 'unit']
    search_fields = ['value', 'label']
    ordering = ['label']

@admin.register(FuelConsumptionMetric)
class FuelConsumptionMetricAdmin(PolymorphicChildModelAdmin):
    base_model = FuelConsumptionMetric
    # Custom fieldsets for better organization
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'form', 'description', 'order', 'is_required', 'help_text', 'location', 'ocr_analyzer_id')
        }),
        ('Fuel Configuration', {
            'fields': ('source_types', 'fuel_types', 'emission_factor_mapping', 'reporting_year', 
                     'frequency')
        }),
        ('Emission Configuration', {
            'fields': ('emission_category', 'emission_sub_category')
        })
    )
    filter_horizontal = ('source_types', 'fuel_types')  # Makes ManyToMany fields easier to manage

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
        VehicleTrackingMetric,
        FuelConsumptionMetric,
        ChecklistMetric,  # Add ChecklistMetric to child models
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

@admin.register(GHGEmissionFactor)
class GHGEmissionFactorAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'sub_category', 'activity_unit', 'region', 'year', 'scope', 'value', 'factor_unit', 'source')
    list_filter = ('year', 'category', 'region', 'scope')
    search_fields = ('name', 'category', 'sub_category', 'source')
    ordering = ('-year', 'category', 'sub_category')
    
    fieldsets = (
        ('Identification', {
            'fields': ('name', 'source', 'source_url')
        }),
        ('Classification', {
            'fields': ('category', 'sub_category', 'scope', 'region', 'year')
        }),
        ('Factor Value', {
            'fields': ('value', 'factor_unit', 'activity_unit')
        }),
    )
    
    def has_delete_permission(self, request, obj=None):
        # Only superusers can delete factors to prevent accidental data loss
        return request.user.is_superuser

@admin.register(PollutantFactor)
class PollutantFactorAdmin(admin.ModelAdmin):
    list_display = ('category', 'sub_category', 'activity_unit', 'region', 'year', 'nox_factor', 'sox_factor', 'pm_factor')
    list_filter = ('year', 'category', 'region')
    search_fields = ('category', 'sub_category', 'source')
    ordering = ('-year', 'category', 'sub_category')

@admin.register(EnergyConversionFactor)
class EnergyConversionFactorAdmin(admin.ModelAdmin):
    list_display = ('category', 'sub_category', 'activity_unit', 'target_unit', 'region', 'year', 'conversion_factor')
    list_filter = ('year', 'category', 'region')
    search_fields = ('category', 'sub_category', 'source')
    ordering = ('-year', 'category', 'sub_category')

@admin.register(CalculatedEmissionValue)
class CalculatedEmissionValueAdmin(admin.ModelAdmin):
    list_display = (
        'id', 
        'calculated_value', 
        'emission_unit', 
        'emission_scope',
        'get_metric_name',
        'get_category_subcategory',
        'reporting_period', 
        'layer', 
        'is_primary_record',
        'display_proportion',
        'has_related_group',
        'calculation_timestamp'
    )
    list_filter = (
        'emission_scope', 
        'emission_unit', 
        'reporting_period',
        'source_activity_value__metric__emission_category',
        'source_activity_value__metric__emission_sub_category',
        'is_primary_record',
        'layer',
        'level'
    )
    search_fields = (
        'calculated_value', 
        'source_activity_value__metric__name', 
        'layer__company_name',
        'calculation_metadata'
    )
    readonly_fields = (
        'source_activity_value', 
        'emission_factor',
        'calculated_value', 
        'emission_unit', 
        'emission_scope',
        'assignment', 
        'layer', 
        'reporting_period',
        'level',
        'is_primary_record',
        'proportion',
        'related_group_id',
        'calculation_metadata_formatted',
        'calculation_timestamp',
        'related_records_summary'
    )
    date_hierarchy = 'reporting_period'
    actions = ['view_related_records']
    
    def get_metric_name(self, obj):
        return obj.source_activity_value.metric.name if obj.source_activity_value and obj.source_activity_value.metric else "-"
    get_metric_name.short_description = "Metric"
    get_metric_name.admin_order_field = 'source_activity_value__metric__name'
    
    def get_category_subcategory(self, obj):
        if not obj.source_activity_value or not obj.source_activity_value.metric:
            return "-"
        metric = obj.source_activity_value.metric
        return f"{metric.emission_category}/{metric.emission_sub_category}"
    get_category_subcategory.short_description = "Category/Subcategory"
    
    def display_proportion(self, obj):
        """Format the proportion as a percentage"""
        if obj.proportion == 1:
            return "100%"
        return f"{float(obj.proportion) * 100:.1f}%"
    display_proportion.short_description = "Proportion"
    
    def has_related_group(self, obj):
        """Check if this calculation is part of a group"""
        return bool(obj.related_group_id)
    has_related_group.boolean = True
    has_related_group.short_description = "In Group"
    
    def calculation_metadata_formatted(self, obj):
        """Format the JSON metadata for better display in the admin"""
        if not obj.calculation_metadata:
            return "No metadata"
            
        try:
            import json
            from django.utils.safestring import mark_safe
            
            # Format as pretty JSON with syntax highlighting
            formatted_json = json.dumps(obj.calculation_metadata, indent=2)
            
            # Basic HTML formatting for readability
            formatted_html = f"<pre>{formatted_json}</pre>"
            
            return mark_safe(formatted_html)
        except Exception as e:
            return f"Error formatting metadata: {str(e)}"
    calculation_metadata_formatted.short_description = "Calculation Metadata"
    
    def related_records_summary(self, obj):
        """Show summary of all records in the same group"""
        from django.utils.safestring import mark_safe
        
        if not obj.related_group_id:
            return "No related records (not part of a group)"
            
        # Get all records in this group
        related_records = CalculatedEmissionValue.objects.filter(related_group_id=obj.related_group_id)
        
        # Build HTML summary
        html = f"<div style='margin: 10px 0;'>"
        html += f"<p><strong>Group ID:</strong> {obj.related_group_id}</p>"
        html += f"<p><strong>Related Records ({related_records.count()}):</strong></p>"
        html += "<table style='border-collapse: collapse; width: 100%;'>"
        html += "<tr style='background-color: #f2f2f2;'>"
        html += "<th style='border: 1px solid #ddd; padding: 8px; text-align: left;'>ID</th>"
        html += "<th style='border: 1px solid #ddd; padding: 8px; text-align: left;'>Value</th>"
        html += "<th style='border: 1px solid #ddd; padding: 8px; text-align: left;'>Type</th>"
        html += "<th style='border: 1px solid #ddd; padding: 8px; text-align: left;'>Proportion</th>"
        html += "<th style='border: 1px solid #ddd; padding: 8px; text-align: left;'>Details</th>"
        html += "</tr>"
        
        for record in related_records:
            # Highlight the current record
            row_style = "background-color: #e6f7ff;" if record.id == obj.id else ""
            primary_text = " (Primary)" if record.is_primary_record else ""
            proportion = f"{float(record.proportion)*100:.1f}%" if record.proportion != 1 else "100%"
            
            # Extract details from metadata
            details = ""
            if record.calculation_metadata:
                vehicle_type = record.calculation_metadata.get('vehicle_label', '')
                fuel_type = record.calculation_metadata.get('fuel_label', '')
                if vehicle_type and fuel_type:
                    details = f"{vehicle_type} / {fuel_type}"
            
            html += f"<tr style='{row_style}'>"
            html += f"<td style='border: 1px solid #ddd; padding: 8px;'><a href='/admin/data_management/calculatedemissionvalue/{record.id}/change/'>{record.id}</a></td>"
            html += f"<td style='border: 1px solid #ddd; padding: 8px;'>{record.calculated_value} {record.emission_unit}</td>"
            html += f"<td style='border: 1px solid #ddd; padding: 8px;'>{record.emission_scope}{primary_text}</td>"
            html += f"<td style='border: 1px solid #ddd; padding: 8px;'>{proportion}</td>"
            html += f"<td style='border: 1px solid #ddd; padding: 8px;'>{details}</td>"
            html += "</tr>"
            
        html += "</table>"
        html += "</div>"
        
        return mark_safe(html)
    related_records_summary.short_description = "Related Records"
    
    def view_related_records(self, request, queryset):
        """Admin action to view all records in the same group"""
        from django.contrib.admin.helpers import ActionForm
        from django import forms
        from django.db.models import Q
        
        # Get all records with related_group_id from the selection 
        related_group_ids = [obj.related_group_id for obj in queryset if obj.related_group_id]
        
        if not related_group_ids:
            self.message_user(
                request,
                "No related group IDs found in the selected records.",
                level='WARNING'
            )
            return
            
        # Create a filter to select all records in these groups
        group_filter = Q(related_group_id__in=related_group_ids)
        
        # Set a session variable with this filter for the admin changelist to use
        request.session['_calculated_emission_value_filter'] = {'related_group_id__in': related_group_ids}
        
        # Count how many records we'll be showing
        count = CalculatedEmissionValue.objects.filter(group_filter).count()
        
        self.message_user(
            request,
            f"Showing {count} records from {len(set(related_group_ids))} groups. Records without a group ID are not included.",
            level='SUCCESS'
        )
    view_related_records.short_description = "View all related records in the same groups"
    
    def get_queryset(self, request):
        """Override to support filtering by session variables"""
        qs = super().get_queryset(request)
        
        # Check if we have a filter set in the session from the action
        if hasattr(request, 'session') and '_calculated_emission_value_filter' in request.session:
            filter_params = request.session.get('_calculated_emission_value_filter')
            
            # Apply the filter if it exists
            if filter_params:
                qs = qs.filter(**filter_params)
                
                # Clear the session variable so it doesn't persist beyond this request
                del request.session['_calculated_emission_value_filter']
                
        return qs

@admin.register(VehicleRecord)
class VehicleRecordAdmin(admin.ModelAdmin):
    form = VehicleRecordForm
    list_display = ['brand', 'model', 'registration_number', 'vehicle_type', 'fuel_type', 'submission', 'is_active']
    list_filter = ['vehicle_type__value', 'fuel_type__value', 'is_active', 'submission__metric']
    search_fields = ['brand', 'model', 'registration_number', 'notes', 'vehicle_type__label', 'fuel_type__label']
    raw_id_fields = ['submission', 'vehicle_type', 'fuel_type']
    inlines = [VehicleMonthlyDataInline]
    
    def get_form(self, request, obj=None, **kwargs):
        """Ensure our custom form is used"""
        return super().get_form(request, obj, **kwargs)

@admin.register(VehicleMonthlyData)
class VehicleMonthlyDataAdmin(admin.ModelAdmin):
    list_display = ['vehicle', 'period', 'kilometers', 'fuel_consumed', 'emission_calculated', 'emission_value']
    list_filter = ['period', 'emission_calculated', 'vehicle__vehicle_type__value', 'vehicle__fuel_type__value']
    search_fields = ['vehicle__brand', 'vehicle__model', 'vehicle__registration_number', 'vehicle__vehicle_type__label', 'vehicle__fuel_type__label']
    ordering = ['vehicle', 'period']
    date_hierarchy = 'period'
    raw_id_fields = ['vehicle']
    inlines = [VehicleDataSourceInline]

@admin.register(FuelMonthlyData)
class FuelMonthlyDataAdmin(admin.ModelAdmin):
    list_display = ['source', 'period', 'quantity', 'emission_calculated', 'emission_value']
    list_filter = ['period', 'emission_calculated', 'source__source_type__value', 'source__fuel_type__value']
    search_fields = ['source__name', 'source__source_type__label', 'source__fuel_type__label']
    ordering = ['source', 'period']
    date_hierarchy = 'period'
    raw_id_fields = ['source']

@admin.register(VehicleDataSource)
class VehicleDataSourceAdmin(admin.ModelAdmin):
    list_display = ['source_reference', 'source_date', 'get_vehicle', 'kilometers', 'fuel_consumed', 'location']
    list_filter = ['source_date', 'vehicle_monthly_data__vehicle__vehicle_type__value', 'vehicle_monthly_data__vehicle__fuel_type__value']
    search_fields = ['source_reference', 'location', 'notes', 'vehicle_monthly_data__vehicle__registration_number']
    date_hierarchy = 'source_date'
    raw_id_fields = ['vehicle_monthly_data']
    
    def get_vehicle(self, obj):
        return obj.vehicle_monthly_data.vehicle if obj.vehicle_monthly_data else None
    get_vehicle.short_description = "Vehicle"
    get_vehicle.admin_order_field = "vehicle_monthly_data__vehicle"

@admin.register(FuelRecord)
class FuelRecordAdmin(admin.ModelAdmin):
    list_display = ['name', 'source_type', 'fuel_type', 'submission', 'is_active']
    list_filter = ['source_type__value', 'fuel_type__value', 'is_active', 'submission__metric']
    search_fields = ['name', 'notes', 'source_type__label', 'fuel_type__label']
    raw_id_fields = ['submission', 'source_type', 'fuel_type']
    inlines = [FuelMonthlyDataInline]

# Custom form for FuelRecord that uses the ForeignKey relationships
class FuelRecordForm(forms.ModelForm):
    class Meta:
        model = FuelRecord
        fields = '__all__'
        widgets = {
            'submission': forms.HiddenInput(),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        instance = kwargs.get('instance')
        initial = kwargs.get('initial', {})
        
        submission_id = None
        if instance and instance.submission_id:
            submission_id = instance.submission_id
        elif 'submission' in initial:
            submission_id = initial.get('submission')
        
        if submission_id:
            try:
                # Get the submission and metric
                submission = ESGMetricSubmission.objects.get(pk=submission_id)
                metric = submission.metric.get_real_instance()
                
                # Only proceed if it's a FuelConsumptionMetric
                if isinstance(metric, FuelConsumptionMetric):
                    # Filter choices to only those associated with this metric
                    self.fields['source_type'].queryset = metric.source_types.all()
                    self.fields['fuel_type'].queryset = metric.fuel_types.all()
                    
                    logger.info(f"Loaded source type and fuel choices from metric {metric.pk} for submission {submission_id}")
            except Exception as e:
                logger.error(f"Error loading choices for FuelRecordForm: {e}", exc_info=True)

class FuelRecordInline(admin.StackedInline):
    """Inline admin for FuelRecord objects in the ESGMetricSubmission admin."""
    model = FuelRecord
    form = FuelRecordForm
    extra = 1
    fields = ('name', 'source_type', 'fuel_type', 'notes', 'is_active')

    def get_formset(self, request, obj=None, **kwargs):
        """Override to customize the inline formset for FuelRecords."""
        formset = super().get_formset(request, obj, **kwargs)
        
        # Store the original __init__ method
        original_init = formset.__init__
        
        # Define a new __init__ method that sets up the source and fuel type choices
        def new_init(self, *args, **kwargs):
            # Call the original __init__
            original_init(self, *args, **kwargs)
            
            # Set up source and fuel type choices for each form
            if obj is not None:
                try:
                    # Get the specific metric instance
                    metric = obj.metric.get_real_instance()
                    if isinstance(metric, FuelConsumptionMetric):
                        # Get the source and fuel types
                        source_types = metric.source_types.all()
                        fuel_types = metric.fuel_types.all()
                        
                        # Apply to each form in the formset
                        for form in self.forms:
                            form.fields['source_type'].queryset = source_types
                            form.fields['fuel_type'].queryset = fuel_types
                            
                        # Also set for the empty form
                        if hasattr(self, 'empty_form'):
                            self.empty_form.fields['source_type'].queryset = source_types
                            self.empty_form.fields['fuel_type'].queryset = fuel_types
                except Exception as e:
                    logger.error(f"Error setting up source and fuel types in inline formset: {e}")
        
        # Replace the formset's __init__ method
        formset.__init__ = new_init
        
        return formset

@admin.register(ChecklistMetric)
class ChecklistMetricAdmin(PolymorphicChildModelAdmin):
    base_model = ChecklistMetric
    # Custom fieldsets for better organization
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'form', 'description', 'order', 'is_required', 'help_text', 'location')
        }),
        ('Checklist Configuration', {
            'fields': ('checklist_structure', 'checklist_type', 'show_item_ids', 'allow_partial_submission', 'require_remarks_for_no')
        }),
        ('Scoring Configuration', {
            'fields': ('enable_scoring', 'scoring_method', 'scoring_weights')
        })
    )

@admin.register(ChecklistResponse)
class ChecklistResponseAdmin(admin.ModelAdmin):
    list_display = ['submission', 'category_id', 'item_id', 'response', 'remarks']
    list_filter = ['response', 'submission__metric', 'category_id']
    search_fields = ['item_text', 'remarks', 'category_id', 'item_id']
    raw_id_fields = ['submission']
    
    # Add the ability to filter by required vs. optional items
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('submission', 'submission__metric')

class ChecklistReportAdmin(admin.ModelAdmin):
    list_display = ['title', 'company', 'report_type', 'generated_at', 'overall_compliance', 'is_structured', 'word_count', 'version']
    list_filter = ['report_type', 'is_structured', 'generated_at', 'layer']
    search_fields = ['title', 'company', 'content']
    date_hierarchy = 'generated_at'
    readonly_fields = [
        'report_type', 'title', 'company', 'generated_at', 'layer',
        'primary_submission', 'overall_compliance', 'environmental_compliance',
        'social_compliance', 'governance_compliance', 'formatted_content',
        'is_structured', 'word_count', 'version', 'esg_rating', 'rating_description'
    ]
    
    fieldsets = [
        ('Report Information', {
            'fields': ['title', 'company', 'report_type', 'generated_at', 'version']
        }),
        ('Organization', {
            'fields': ['layer', 'primary_submission']
        }),
        ('Compliance Scores', {
            'fields': [
                'overall_compliance', 'environmental_compliance',
                'social_compliance', 'governance_compliance',
                'esg_rating', 'rating_description'
            ]
        }),
        ('Report Content', {
            'fields': ['formatted_content'],
            'classes': ('wide',)
        }),
        ('Metadata', {
            'fields': ['is_structured', 'word_count'],
            'classes': ('collapse',)
        })
    ]
    
    def has_add_permission(self, request, obj=None):
        # Reports should only be created via the API
        return False
        
    def formatted_content(self, obj):
        """Format the content field for better display in admin, supporting Chinese characters"""
        from django.utils.safestring import mark_safe
        
        if obj.is_structured:
            try:
                import json
                # Parse the JSON content
                parsed_content = json.loads(obj.content)
                # Format as pretty JSON with HTML formatting, ensure_ascii=False to properly handle Chinese
                formatted_json = json.dumps(parsed_content, indent=2, ensure_ascii=False)
                return mark_safe(f'<pre style="white-space: pre-wrap; font-family: monospace;">{formatted_json}</pre>')
            except Exception as e:
                return mark_safe(f'<p>Error parsing JSON: {str(e)}</p><pre>{obj.content}</pre>')
        
        # For non-JSON content or if parsing fails
        return mark_safe(f'<pre style="white-space: pre-wrap;">{obj.content}</pre>')
    
    formatted_content.short_description = "Report Content"

admin.site.register(ChecklistReport, ChecklistReportAdmin)

@admin.register(FormCompletionStatus)
class FormCompletionStatusAdmin(admin.ModelAdmin):
    list_display = ['form_selection', 'get_company', 'get_reporting_year', 'get_form_name', 'get_template_name', 
                    'get_status_display', 'is_completed', 'completed_at', 'completed_by', 
                    'is_verified', 'verified_at', 'verified_by']
    list_filter = ['is_completed', 'is_verified', 'assignment__layer', 'assignment__reporting_year', 
                   'form_selection__template', 'form_selection__form']
    search_fields = ['assignment__layer__company_name', 'form_selection__form__name', 
                     'form_selection__template__name', 'verification_notes']
    raw_id_fields = ['form_selection', 'assignment', 'completed_by', 'verified_by']
    readonly_fields = ['completed_at', 'verified_at']
    
    fieldsets = [
        ('Form Information', {
            'fields': ['form_selection', 'assignment', 'layer']
        }),
        ('Completion Status', {
            'fields': ['is_completed', 'completed_at', 'completed_by']
        }),
        ('Verification Status', {
            'fields': ['is_verified', 'verified_at', 'verified_by', 'verification_notes']
        })
    ]
    
    def get_form_name(self, obj):
        return obj.form_selection.form.name
    get_form_name.short_description = 'Form'
    get_form_name.admin_order_field = 'form_selection__form__name'
    
    def get_template_name(self, obj):
        return obj.form_selection.template.name
    get_template_name.short_description = 'Template'
    get_template_name.admin_order_field = 'form_selection__template__name'
    
    def get_company(self, obj):
        return obj.assignment.layer.company_name
    get_company.short_description = 'Company'
    get_company.admin_order_field = 'assignment__layer__company_name'
    
    def get_reporting_year(self, obj):
        return obj.assignment.reporting_year
    get_reporting_year.short_description = 'Reporting Year'
    get_reporting_year.admin_order_field = 'assignment__reporting_year'
    
    def get_status_display(self, obj):
        return obj.get_status_display()
    get_status_display.short_description = 'Status'
