"""
Views for user template assignment access.
"""

from rest_framework import views, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from accounts.models import AppUser # LayerProfile no longer needed directly here
from accounts.services import get_user_layers_and_parents_ids # Import the new function
from ...models import TemplateAssignment
from ...serializers.polymorphic_metrics import ESGMetricPolymorphicSerializer
from ...serializers.templates import TemplateAssignmentSerializer


class UserTemplateAssignmentView(views.APIView):
    """
    API view for group users to access templates assigned to their group.
    Retrieves list of assignments or metadata for a specific assignment.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, assignment_id=None):
        """
        Get template assignments list or metadata for a specific assignment.
        """
        accessible_layer_ids = get_user_layers_and_parents_ids(request.user)
        user_direct_layer_ids = {app_user.layer_id for app_user in AppUser.objects.filter(user=request.user)} # More efficient

        if assignment_id:
            # Get specific template assignment metadata
            try:
                assignment = TemplateAssignment.objects.select_related(
                    'template', 'layer'
                ).get(
                    id=assignment_id,
                    layer_id__in=accessible_layer_ids
                )

                # Use the TemplateAssignmentSerializer for consistency
                serializer = TemplateAssignmentSerializer(assignment, context=self.get_serializer_context())
                assignment_data = serializer.data

                # Add relationship info
                if assignment.layer_id in user_direct_layer_ids:
                    assignment_data['relationship'] = 'direct'
                else:
                    assignment_data['relationship'] = 'inherited'

                return Response(assignment_data)

            except TemplateAssignment.DoesNotExist:
                return Response(
                    {'error': 'Template assignment not found or you do not have access to it'},
                    status=status.HTTP_404_NOT_FOUND
                )
        else:
            # Get all template assignments for these layers (LIST VIEW - unchanged)
            assignments = TemplateAssignment.objects.filter(
                layer_id__in=accessible_layer_ids
            ).select_related('template', 'layer')

            assignments_data = []
            for assignment in assignments:
                assignment_data = TemplateAssignmentSerializer(assignment, context=self.get_serializer_context()).data
                if assignment.layer_id in user_direct_layer_ids:
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

# --- NEW VIEW ---

class UserTemplateAssignmentStructureView(views.APIView):
    """
    API view for group users to get the detailed form/metric structure
    of a specific template assignment they have access to.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, assignment_id):
        """
        Get the detailed form and metric structure for a specific assignment.
        """
        accessible_layer_ids = get_user_layers_and_parents_ids(request.user)

        try:
            # Fetch assignment, ensuring it exists and user has access
            assignment = TemplateAssignment.objects.select_related(
                'template', 'layer' # Include layer for potential context, though not directly returned here
            ).get(
                id=assignment_id,
                layer_id__in=accessible_layer_ids
            )

            # --- Logic moved from the original UserTemplateAssignmentView.get ---
            template = assignment.template
            form_selections = template.templateformselection_set.select_related(
                'form', 'form__category'
            ).prefetch_related('form__polymorphic_metrics') # Use the correct related name

            forms_data = []
            for selection in form_selections:
                form = selection.form # Get the related form object
                form_data = {
                    'form_id': form.id,
                    'form_code': form.code,
                    'form_name': form.name,
                    'regions': selection.regions, # Use regions from the selection
                    'category': {
                        'id': form.category.id,
                        'name': form.category.name,
                        'code': form.category.code,
                        'icon': form.category.icon,
                        'order': form.category.order
                    } if form.category else None, # Handle cases where category might be null
                    'order': form.order,
                    'metrics': []
                }

                relevant_metrics = []
                # Iterate using the correct polymorphic related name
                for metric in form.polymorphic_metrics.all():
                    # Only include metrics that match the form's regions or are for ALL locations
                    # Use regions from the TemplateFormSelection instance ('selection')
                    if metric.location == 'ALL' or metric.location in selection.regions:
                         relevant_metrics.append(metric)

                # Sort metrics by order before serialization
                relevant_metrics.sort(key=lambda m: getattr(m, 'order', 0)) # Use getattr for safety

                # Serialize using the polymorphic serializer
                # Pass context if needed by the serializer (e.g., for URLs)
                serializer = ESGMetricPolymorphicSerializer(relevant_metrics, many=True, context=self.get_serializer_context())
                form_data['metrics'] = serializer.data

                forms_data.append(form_data)

            # Sort forms by their selection order in the template
            # Create a mapping for faster lookup
            selection_order_map = {s.form_id: s.order for s in form_selections}
            forms_data.sort(key=lambda form_d: selection_order_map.get(form_d['form_id'], 0))

            # Return just the forms structure
            return Response({'forms': forms_data})
            # --- End of moved logic ---

        except TemplateAssignment.DoesNotExist:
            return Response(
                {'error': 'Template assignment not found or you do not have access to it'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
             # Basic error logging
             print(f"Error in UserTemplateAssignmentStructureView: {e}") # Replace with proper logging
             return Response(
                 {'error': 'An internal server error occurred.'},
                 status=status.HTTP_500_INTERNAL_SERVER_ERROR
             )


    def get_serializer_context(self):
        """Ensures request context is passed to serializers."""
        # Copied from UserTemplateAssignmentView, adjust if needed
        return {
            'request': self.request,
            'format': self.format_kwarg,
            'view': self
        } 