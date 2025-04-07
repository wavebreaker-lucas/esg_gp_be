"""
Views for user template assignment access.
"""

from rest_framework import views, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from accounts.models import AppUser, LayerProfile
from ...models import TemplateAssignment
from ...serializers.polymorphic_metrics import ESGMetricPolymorphicSerializer
from ...serializers.templates import TemplateAssignmentSerializer


class UserTemplateAssignmentView(views.APIView):
    """
    API view for group users to access templates assigned to their group.
    Also includes templates assigned to parent groups.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, assignment_id=None):
        """
        Get template assignments for the user's groups and parent groups.
        If assignment_id is provided, return details for that specific assignment.
        """
        # Get all layers (groups) the user belongs to
        user_app_users = AppUser.objects.filter(user=request.user).select_related('layer')
        user_layers = [app_user.layer for app_user in user_app_users]
        
        # Get all accessible layer IDs including parent groups
        accessible_layer_ids = set()
        for layer in user_layers:
            # Add the current layer
            accessible_layer_ids.add(layer.id)
            
            # Add parent layers based on layer type
            if hasattr(layer, 'branchlayer'):
                # For branch layer, add subsidiary and group
                subsidiary = layer.branchlayer.subsidiary_layer
                accessible_layer_ids.add(subsidiary.id)
                accessible_layer_ids.add(subsidiary.group_layer.id)
            elif hasattr(layer, 'subsidiarylayer'):
                # For subsidiary layer, add group
                accessible_layer_ids.add(layer.subsidiarylayer.group_layer.id)
        
        if assignment_id:
            # Get specific template assignment
            try:
                assignment = TemplateAssignment.objects.get(
                    id=assignment_id,
                    layer_id__in=accessible_layer_ids
                )
                
                # Get template with forms and metrics
                template = assignment.template
                form_selections = template.templateformselection_set.select_related(
                    'form', 'form__category'
                ).prefetch_related('form__polymorphic_metrics')
                
                # Create a flat list of forms with their metrics
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
                    
                    # Iterate using the correct polymorphic related name
                    for metric in selection.form.polymorphic_metrics.all():
                        # Only include metrics that match the form's regions or are for ALL locations
                        if metric.location == 'ALL' or metric.location in selection.regions:
                            # --- REFACTORED: Use Polymorphic Serializer --- 
                            # Use the polymorphic serializer to get the correct representation
                            serializer = ESGMetricPolymorphicSerializer(metric, context=self.get_serializer_context())
                            form_data['metrics'].append(serializer.data) # Append the serialized data
                            # --- End Refactor --- 
                    
                    # Sort metrics by order (using the 'order' field from the serialized data)
                    form_data['metrics'].sort(key=lambda x: x.get('order', 0))
                    forms_data.append(form_data)
                
                # Sort forms by their selection order in the template
                forms_data.sort(key=lambda form_d: next((s.order for s in form_selections if s.form_id == form_d['form_id']), 0))
                
                response_data = {
                    'assignment_id': assignment.id,
                    'template_id': template.id,
                    'template_name': template.name,
                    'layer_id': assignment.layer.id,
                    'layer_name': assignment.layer.company_name,
                    'status': assignment.status,
                    'due_date': assignment.due_date,
                    'reporting_period_start': assignment.reporting_period_start,
                    'reporting_period_end': assignment.reporting_period_end,
                    'reporting_year': assignment.reporting_year,
                    'forms': forms_data
                }
                
                return Response(response_data)
                
            except TemplateAssignment.DoesNotExist:
                return Response(
                    {'error': 'Template assignment not found or you do not have access to it'},
                    status=status.HTTP_404_NOT_FOUND
                )
        else:
            # Get all template assignments for these layers (LIST VIEW)
            assignments = TemplateAssignment.objects.filter(
                layer_id__in=accessible_layer_ids
            ).select_related('template', 'layer')
            
            # Add layer relationship info to each assignment
            assignments_data = []
            user_direct_layers = [layer.id for layer in user_layers]
            for assignment in assignments:
                # Use the imported TemplateAssignmentSerializer
                assignment_data = TemplateAssignmentSerializer(assignment, context=self.get_serializer_context()).data
                
                # Add relationship info (direct or inherited)
                if assignment.layer_id in user_direct_layers:
                    assignment_data['relationship'] = 'direct'
                else:
                    assignment_data['relationship'] = 'inherited'
                
                assignments_data.append(assignment_data)
            
            return Response(assignments_data)

    def get_serializer_context(self):
        """Ensures request context is passed to serializers."""
        return {
            'request': self.request,
            'format': self.format_kwarg,
            'view': self
        } 