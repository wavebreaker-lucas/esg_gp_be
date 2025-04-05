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
from ...models import (
    ESGFormCategory, ESGForm,
    Template, TemplateFormSelection, TemplateAssignment
)
from ...models.polymorphic_metrics import BaseESGMetric
from ...serializers.templates import (
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
        """Get the completion status of forms in a template for a specific assignment - NEEDS REWORK"""
        # This whole method relies on the old submission structure and metric properties
        # Needs a complete rewrite based on new polymorphic structure and submission data models
        logger.warning("completion_status endpoint needs rework for polymorphic metrics")
        return Response("Completion status endpoint needs rework for polymorphic metrics", status=status.HTTP_501_NOT_IMPLEMENTED)

        # # --- Old logic (commented out) ---
        # template = self.get_object()
        # assignment_id = request.query_params.get('assignment_id')
        # ... (rest of old logic) ... 