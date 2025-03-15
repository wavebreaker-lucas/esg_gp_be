from rest_framework import viewsets, views, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db import transaction
from accounts.permissions import BakerTillyAdmin
from ..models import (
    ESGFormCategory, ESGForm, ESGMetric,
    Template, TemplateFormSelection, TemplateAssignment, CustomUser
)
from ..serializers.templates import (
    ESGFormCategorySerializer, ESGFormSerializer, ESGMetricSerializer,
    TemplateSerializer, TemplateAssignmentSerializer
)

class ESGFormViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing ESG forms. Forms are predefined and can only be modified
    through admin interface.
    """
    queryset = ESGForm.objects.filter(is_active=True)
    serializer_class = ESGFormSerializer
    permission_classes = [IsAuthenticated]

    @action(detail=True, methods=['get'])
    def metrics(self, request, pk=None):
        """Get metrics for a specific form"""
        form = self.get_object()
        metrics = form.metrics.all()
        serializer = ESGMetricSerializer(metrics, many=True)
        return Response(serializer.data)

class ESGFormCategoryViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing ESG form categories with their associated forms.
    """
    queryset = ESGFormCategory.objects.all()
    serializer_class = ESGFormCategorySerializer
    permission_classes = [IsAuthenticated]

    def list(self, request, *args, **kwargs):
        """List all categories with their active forms"""
        categories = self.get_queryset()
        # Prefetch related forms and metrics for performance
        categories = categories.prefetch_related(
            'forms__metrics'
        )
        serializer = self.get_serializer(categories, many=True)
        return Response(serializer.data)

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
        # Get all form selections with their forms and metrics
        form_selections = template.templateformselection_set.select_related('form').prefetch_related('form__metrics')
        
        # Organize data by region
        regions_data = {}
        for selection in form_selections:
            for region in selection.regions:
                if region not in regions_data:
                    regions_data[region] = []
                
                form_data = {
                    'form_code': selection.form.code,
                    'form_name': selection.form.name,
                    'metrics': []
                }
                
                for metric in selection.form.metrics.all():
                    form_data['metrics'].append({
                        'id': metric.id,
                        'name': metric.name,
                        'unit_type': metric.unit_type,
                        'custom_unit': metric.custom_unit,
                        'requires_evidence': metric.requires_evidence,
                        'validation_rules': metric.validation_rules
                    })
                
                regions_data[region].append(form_data)
        
        return Response({
            'template_id': template.id,
            'name': template.name,
            'reporting_period': template.reporting_period,
            'regions': regions_data
        })

class TemplateAssignmentView(views.APIView):
    """
    API view for managing template assignments to client companies.
    Templates are automatically assigned to the company's CREATOR user.
    """
    permission_classes = [IsAuthenticated, BakerTillyAdmin]

    def get(self, request, group_id):
        """Get all template assignments for a client company"""
        assignments = TemplateAssignment.objects.filter(
            company_id=group_id
        ).select_related('template', 'company', 'assigned_to')
        
        serializer = TemplateAssignmentSerializer(assignments, many=True)
        return Response(serializer.data)

    @transaction.atomic
    def post(self, request, group_id):
        """Assign a template to a client company's CREATOR user"""
        # Get the CREATOR user for this company
        creator_user = CustomUser.objects.filter(
            appuser__layer_id=group_id,
            appuser__role='CREATOR'
        ).first()
        
        if not creator_user:
            return Response(
                {'error': 'No CREATOR user found for this company'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        data = {
            **request.data,
            'company': group_id,
            'assigned_to': creator_user.id
        }
        serializer = TemplateAssignmentSerializer(data=data)
        
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @transaction.atomic
    def delete(self, request, group_id):
        """Remove a template assignment from a client company"""
        assignment_id = request.data.get('assignment_id')
        try:
            assignment = TemplateAssignment.objects.get(
                id=assignment_id,
                company_id=group_id
            )
            assignment.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except TemplateAssignment.DoesNotExist:
            return Response(
                {'error': 'Assignment not found'},
                status=status.HTTP_404_NOT_FOUND
            ) 