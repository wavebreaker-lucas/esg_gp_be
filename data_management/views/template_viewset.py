"""
Views for managing ESG templates.
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from accounts.permissions import BakerTillyAdmin
from accounts.models import CustomUser, AppUser, LayerProfile
from ..models import (
    ESGFormCategory, ESGForm, ESGMetric,
    Template, TemplateFormSelection, TemplateAssignment
)
from ..models.templates import ESGMetricSubmission, ESGMetricEvidence
from ..serializers.templates import (
    ESGFormCategorySerializer, ESGFormSerializer, ESGMetricSerializer,
    TemplateSerializer, TemplateAssignmentSerializer
)
from .utils import get_required_submission_count


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
        # Update to include form__category in select_related
        form_selections = template.templateformselection_set.select_related('form', 'form__category').prefetch_related('form__metrics')
        
        # Create a flat list of forms with their metrics
        forms_data = []
        for selection in form_selections:
            form_data = {
                'form_id': selection.form.id,
                'form_code': selection.form.code,
                'form_name': selection.form.name,
                'regions': selection.regions,  # Keep the regions info at form level
                # Add category information to match the user-templates endpoint
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
            
            for metric in selection.form.metrics.all():
                # Only include metrics that match the form's regions or are for ALL locations
                if metric.location == 'ALL' or metric.location in selection.regions:
                    metric_data = {
                        'id': metric.id,
                        'name': metric.name,
                        'requires_evidence': metric.requires_evidence,
                        'validation_rules': metric.validation_rules,
                        'location': metric.location,
                        'is_required': metric.is_required,
                        'order': metric.order,
                        'requires_time_reporting': metric.requires_time_reporting,
                        'reporting_frequency': metric.reporting_frequency,
                        # Add new JSON schema related fields
                        'form_component': metric.form_component,
                        'primary_path': metric.primary_path,
                        'schema_registry_id': metric.schema_registry_id if metric.schema_registry else None,
                    }
                    
                    # Include schema details if available
                    if metric.schema_registry:
                        metric_data['schema_registry'] = {
                            'id': metric.schema_registry.id,
                            'name': metric.schema_registry.name,
                            'version': metric.schema_registry.version,
                            'schema': metric.schema_registry.schema
                        }
                        
                    form_data['metrics'].append(metric_data)
            
            # Sort metrics by order
            form_data['metrics'].sort(key=lambda x: x['order'])
            forms_data.append(form_data)
        
        # Sort forms by their selection order
        forms_data.sort(key=lambda x: next((s.order for s in form_selections if s.form.id == x['form_id']), 0))
        
        return Response({
            'template_id': template.id,
            'template_name': template.name,
            'description': template.description,
            'forms': forms_data
        })

    @action(detail=True, methods=['get'])
    def completion_status(self, request, pk=None):
        """Get the completion status of forms in a template for a specific assignment"""
        template = self.get_object()
        assignment_id = request.query_params.get('assignment_id')
        
        if not assignment_id:
            return Response(
                {"error": "assignment_id query parameter is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        try:
            assignment = TemplateAssignment.objects.get(id=assignment_id, template=template)
        except TemplateAssignment.DoesNotExist:
            return Response(
                {"error": "Template assignment not found"},
                status=status.HTTP_404_NOT_FOUND
            )
            
        # Get all form selections for this template
        form_selections = template.templateformselection_set.select_related('form').all()
        
        # Create a response with completion status for each form
        forms_status = []
        for selection in form_selections:
            # Get all required metrics for this form
            required_metrics = []
            for metric in selection.form.metrics.filter(is_required=True):
                if metric.location == 'ALL' or metric.location in selection.regions:
                    required_metrics.append(metric.id)
                    
            # Get submitted metrics for this form
            submitted_metrics = ESGMetricSubmission.objects.filter(
                assignment=assignment,
                metric__form=selection.form
            ).values_list('metric_id', flat=True)
            
            # Calculate completion percentage
            total_required = len(required_metrics)
            total_submitted = len(set(required_metrics) & set(submitted_metrics))
            
            completion_percentage = 0
            if total_required > 0:
                completion_percentage = (total_submitted / total_required) * 100
                
            # Get missing metrics if any
            missing_metrics = []
            if total_submitted < total_required:
                missing_metric_ids = set(required_metrics) - set(submitted_metrics)
                missing_metrics = ESGMetric.objects.filter(
                    id__in=missing_metric_ids
                ).values('id', 'name')
                
            forms_status.append({
                'form_id': selection.form.id,
                'form_name': selection.form.name,
                'form_code': selection.form.code,
                'is_completed': selection.is_completed,
                'completed_at': selection.completed_at,
                'completed_by': selection.completed_by.email if selection.completed_by else None,
                'total_required_metrics': total_required,
                'total_submitted_metrics': total_submitted,
                'completion_percentage': completion_percentage,
                'missing_metrics': list(missing_metrics)
            })
            
        # Calculate overall completion percentage
        total_forms = len(form_selections)
        completed_forms = sum(1 for selection in form_selections if selection.is_completed)
        
        overall_percentage = 0
        if total_forms > 0:
            overall_percentage = (completed_forms / total_forms) * 100
            
        return Response({
            'assignment_id': assignment.id,
            'template_id': template.id,
            'template_name': template.name,
            'status': assignment.status,
            'due_date': assignment.due_date,
            'completed_at': assignment.completed_at,
            'total_forms': total_forms,
            'completed_forms': completed_forms,
            'overall_completion_percentage': overall_percentage,
            'forms': forms_status
        }) 