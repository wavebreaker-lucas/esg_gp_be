"""
Views for managing ESG templates.
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
import logging

from accounts.permissions import BakerTillyAdmin
from accounts.models import CustomUser, AppUser, LayerProfile
from accounts.services import has_layer_access
from ...models import (
    ESGFormCategory, ESGForm,
    Template, TemplateFormSelection, TemplateAssignment,
    ReportedMetricValue
)
from ...models.polymorphic_metrics import BaseESGMetric
from ...serializers import (
    ESGFormCategorySerializer, ESGFormSerializer,
    TemplateSerializer, TemplateAssignmentSerializer,
    ESGMetricPolymorphicSerializer
)

logger = logging.getLogger(__name__) # Initialize logger

class TemplateViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing templates created from ESG forms.
    """
    queryset = Template.objects.all()
    serializer_class = TemplateSerializer
    permission_classes = [IsAuthenticated, BakerTillyAdmin]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=['get'])
    def preview(self, request, pk=None):
        """Preview a template with all its forms and metrics"""
        template = self.get_object()
        form_selections = template.templateformselection_set.select_related(
            'form', 'form__category'
        ).prefetch_related(
            'form__polymorphic_metrics' # Use new related name
        )
        
        forms_data = []
        for selection in form_selections:
            form_data = {
                'form_id': selection.form.id,
                'form_code': selection.form.code,
                'form_name': selection.form.name,
                'regions': selection.regions,
                'category': {
                    'id': selection.form.category.id,
                    'name': selection.form.category.name,
                    'code': selection.form.category.code,
                    'icon': selection.form.category.icon,
                    'order': selection.form.category.order
                },
                'order': selection.form.order,
                'metrics': []
            }
            
            # Get relevant metrics
            relevant_metrics = []
            for metric in selection.form.polymorphic_metrics.all():
                if metric.location == 'ALL' or metric.location in selection.regions:
                    relevant_metrics.append(metric)
            
            # Sort before serializing
            relevant_metrics.sort(key=lambda m: m.order)
            
            # Serialize using the polymorphic serializer
            metric_serializer = ESGMetricPolymorphicSerializer(relevant_metrics, many=True, context={'request': request})
            form_data['metrics'] = metric_serializer.data
            
            forms_data.append(form_data)
        
        forms_data.sort(key=lambda x: next((s.order for s in form_selections if s.form.id == x['form_id']), 0))
        
        return Response({
            'template_id': template.id,
            'template_name': template.name,
            'description': template.description,
            'forms': forms_data
        })

    @action(detail=True, methods=['get'])
    def completion_status(self, request, pk=None):
        """Get the overall completion status for a template assignment.
        Aggregates the status of all forms associated with the template based on ReportedMetricValue.
        """
        template = self.get_object()
        assignment_id = request.query_params.get('assignment_id')
        if not assignment_id:
            return Response({"error": "assignment_id query parameter is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            assignment = TemplateAssignment.objects.select_related('layer', 'template').get(pk=assignment_id, template=template)
        except TemplateAssignment.DoesNotExist:
            return Response({"error": "Assignment not found for this template."}, status=status.HTTP_404_NOT_FOUND)

        # Check user access to the assignment's layer
        if not has_layer_access(request.user, assignment.layer_id):
             return Response({"detail": "You do not have permission for this assignment's layer."}, status=status.HTTP_403_FORBIDDEN)

        # Get all forms associated with this template
        forms_in_template = ESGForm.objects.filter(templateformselection__template=template)
        
        overall_total_points = 0
        overall_reported_points = 0
        form_statuses = []
        all_requirements_met = True # Assume true until proven otherwise

        # --- Period Calculation Logic (Same helper as in ESGFormViewSet) --- 
        # TODO: Refactor this into a shared service/utility function
        assignment_start = assignment.reporting_period_start
        assignment_end = assignment.reporting_period_end
        def calculate_expected_periods(metric, start_date, end_date):
             if hasattr(metric, 'frequency'):
                 freq = metric.frequency
                 if freq == 'monthly':
                     periods = []
                     current_date = start_date
                     while current_date <= end_date:
                         import calendar
                         last_day = calendar.monthrange(current_date.year, current_date.month)[1]
                         periods.append(current_date.replace(day=last_day))
                         if current_date.month == 12:
                              current_date = current_date.replace(year=current_date.year + 1, month=1, day=1)
                         else:
                              current_date = current_date.replace(month=current_date.month + 1, day=1)
                     return periods
                 elif freq == 'annual': return [end_date]
                 else: return [end_date] 
             else: return [end_date]
        # --- End Helper --- 

        for form in forms_in_template:
            required_metrics = form.polymorphic_metrics.filter(is_required=True)
            form_total_points = 0
            form_reported_points = 0
            form_missing_values = []
            form_is_complete = True # Assume complete for this form

            if not required_metrics.exists():
                form_is_complete = True # No required metrics -> complete
            else:
                for metric in required_metrics.iterator():
                    specific_metric = metric.get_real_instance()
                    expected_periods_dates = calculate_expected_periods(specific_metric, assignment_start, assignment_end)
                    expected_periods_count = len(expected_periods_dates)
                    
                    if expected_periods_count == 0: continue
                    form_total_points += expected_periods_count
                    
                    found_periods_count = ReportedMetricValue.objects.filter(
                        assignment=assignment,
                        metric_id=metric.id,
                        layer=assignment.layer, 
                        reporting_period__in=expected_periods_dates
                    ).count()
                    form_reported_points += found_periods_count
                    
                    if found_periods_count < expected_periods_count:
                        form_is_complete = False
                        # Could add details to form_missing_values if needed per-form
            
            # Check stored status
            try:
                selection = TemplateFormSelection.objects.get(template=template, form=form)
                is_marked_complete = selection.is_completed
            except TemplateFormSelection.DoesNotExist:
                is_marked_complete = False
            
            form_statuses.append({
                "form_id": form.pk,
                "form_name": form.name,
                "is_marked_complete": is_marked_complete, # Stored flag
                "is_actually_complete": form_is_complete, # Calculated based on ReportedMetricValue
                "total_required_points": form_total_points,
                "reported_points_count": form_reported_points,
            })
            
            overall_total_points += form_total_points
            overall_reported_points += form_reported_points
            if not form_is_complete:
                all_requirements_met = False
        
        overall_percentage = (overall_reported_points / overall_total_points * 100) if overall_total_points > 0 else 100
        
        return Response({
            "assignment_id": assignment.pk,
            "template_id": template.pk,
            "template_name": template.name,
            "assignment_status": assignment.get_status_display(), # Current status from DB
            "overall_completion_percentage": round(overall_percentage, 2),
            "overall_total_required_points": overall_total_points,
            "overall_reported_points_count": overall_reported_points,
            "all_requirements_met": all_requirements_met, # Based on current calculation
            "form_statuses": form_statuses
        }) 