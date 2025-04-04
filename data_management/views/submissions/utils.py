"""
Utility views related to metric submissions, separate from the main submission CRUD operations.
"""

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from datetime import datetime

from accounts.models import LayerProfile
from accounts.services import get_accessible_layers, has_layer_access
from ...models import ESGMetric, TemplateAssignment, ESGMetricSubmission


class AvailableLayersView(APIView):
    """
    Provides a list of layers accessible to the current user,
    optionally filtered by the context of a template assignment.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        Get all layers that the current user has access to.
        
        Optional parameters:
            assignment_id: Filter layers to those relevant for a specific assignment
        """
        user_layers = get_accessible_layers(request.user)
        assignment_id = request.query_params.get('assignment_id')

        if assignment_id:
            try:
                assignment = TemplateAssignment.objects.get(id=assignment_id)
                assignment_layer = assignment.layer

                if not has_layer_access(request.user, assignment_layer):
                    return Response({'error': f'You do not have access to layer {assignment_layer.id}'}, status=status.HTTP_403_FORBIDDEN)

                # Logic to determine relevant layers based on assignment
                # (This is a simplified version of the original logic for clarity)
                # You might want to refine this based on your exact hierarchy needs
                relevant_layers = set()
                relevant_layers.add(assignment_layer)

                # Add parent layers
                parent = assignment_layer.get_parent_layer()
                while parent:
                    if has_layer_access(request.user, parent):
                        relevant_layers.add(parent)
                    parent = parent.get_parent_layer()

                # Add child layers
                for child in assignment_layer.get_child_layers():
                    if has_layer_access(request.user, child):
                        relevant_layers.add(child)
                        # Optionally add grandchildren etc. recursively
                        # for grandchild in child.get_child_layers(): ...
                
                user_layers = user_layers.filter(id__in=[layer.id for layer in relevant_layers])

            except TemplateAssignment.DoesNotExist:
                return Response({'error': f'Assignment with ID {assignment_id} not found'}, status=status.HTTP_404_NOT_FOUND)
            except Exception as e: # Catch potential errors from get_parent/child methods if they don't exist
                # Log the error
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Error determining relevant layers for assignment {assignment_id}: {e}")
                # Fallback to just showing assignment layer if accessible
                if has_layer_access(request.user, assignment.layer):
                     user_layers = user_layers.filter(id=assignment.layer.id)
                else:
                     user_layers = LayerProfile.objects.none() # Should not happen due to initial check

        # Prepare result format (similar to original logic)
        result = []
        layers_processed = set()
        
        # Helper to add layer and its parents recursively
        def add_layer_and_parents(layer, parent_data=None):
            if layer.id in layers_processed:
                return
            
            current_parent_data = None
            parent_layer = layer.get_parent_layer()
            if parent_layer and has_layer_access(request.user, parent_layer):
                 current_parent_data = {
                     'id': parent_layer.id,
                     'name': parent_layer.company_name
                 }
                 add_layer_and_parents(parent_layer) # Recursive call for parent
            
            layer_data = {
                'id': layer.id,
                'name': layer.company_name,
                'type': layer.layer_type,
                'location': layer.company_location,
                'parent': parent_data or current_parent_data
            }
            if layer.id not in layers_processed:
                 result.append(layer_data)
                 layers_processed.add(layer.id)
        
        # Add all accessible layers ensuring hierarchy is represented
        # Order by type then name
        ordered_layers = user_layers.order_by('layer_type', 'company_name')
        for layer in ordered_layers:
             # The recursive helper might have already added this layer when processing a child
             if layer.id not in layers_processed:
                  parent = layer.get_parent_layer()
                  parent_info = None
                  if parent and has_layer_access(request.user, parent):
                       parent_info = {'id': parent.id, 'name': parent.company_name}
                  
                  # Check again if processed, as parent call might add it
                  if layer.id not in layers_processed:
                        result.append({
                             'id': layer.id,
                             'name': layer.company_name,
                             'type': layer.layer_type,
                             'location': layer.company_location,
                             'parent': parent_info
                        })
                        layers_processed.add(layer.id)

        # Ensure consistent sorting for the final list if needed
        # Example: sort by type index, then name
        type_order = {'GROUP': 0, 'SUBSIDIARY': 1, 'BRANCH': 2}
        result.sort(key=lambda x: (type_order.get(x['type'], 99), x['name']))

        return Response(result)


class SumSubmissionsByLayerView(APIView):
    """
    Aggregates metric submission values by layer for a given assignment.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        Get aggregated values for metric submissions by layer.

        Parameters:
            assignment_id: Required. The template assignment to aggregate data for.
            metric_ids: Comma-separated list of metric IDs to include.
            layer_ids: Comma-separated list of layer IDs to include.
            period: Optional. Filter submissions to this specific period (YYYY-MM-DD).
        """
        assignment_id = request.query_params.get('assignment_id')
        metric_ids_param = request.query_params.get('metric_ids')
        layer_ids_param = request.query_params.get('layer_ids')

        if not assignment_id:
            return Response({'error': 'assignment_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        if not metric_ids_param:
            return Response({'error': 'metric_ids is required'}, status=status.HTTP_400_BAD_REQUEST)
        if not layer_ids_param:
            return Response({'error': 'layer_ids is required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            metric_ids = [int(id.strip()) for id in metric_ids_param.split(',') if id.strip()]
            layer_ids = [int(id.strip()) for id in layer_ids_param.split(',') if id.strip()]
            if not metric_ids or not layer_ids:
                raise ValueError("No valid IDs provided")
        except ValueError:
            return Response({'error': 'Invalid metric_ids or layer_ids format. Use comma-separated integers.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            assignment = TemplateAssignment.objects.get(id=assignment_id)
        except TemplateAssignment.DoesNotExist:
            return Response({'error': f'Assignment with ID {assignment_id} not found'}, status=status.HTTP_404_NOT_FOUND)

        # Check permissions for assignment and layers
        user_layers = get_accessible_layers(request.user)
        accessible_layer_ids = set(user_layers.values_list('id', flat=True))
        if not has_layer_access(request.user, assignment.layer):
             # Check if user has access via parent/child relationship if needed based on your rules
             # Simplified check: Does user have access to the assignment's specific layer?
             # You might need more complex logic depending on hierarchy access rules
             if assignment.layer.id not in accessible_layer_ids: 
                  return Response({'error': 'You do not have permission to view this assignment'}, status=status.HTTP_403_FORBIDDEN)

        inaccessible_layers = set(layer_ids) - accessible_layer_ids
        if inaccessible_layers:
            return Response({'error': f'You do not have access to the following layers: {", ".join(map(str, inaccessible_layers))}'}, status=status.HTTP_403_FORBIDDEN)

        metrics = ESGMetric.objects.filter(id__in=metric_ids)
        if metrics.count() != len(metric_ids):
            found_ids = set(metrics.values_list('id', flat=True))
            missing_ids = set(metric_ids) - found_ids
            return Response({'error': f'The following metrics were not found: {", ".join(map(str, missing_ids))}'}, status=status.HTTP_404_NOT_FOUND)

        period_filter = {}
        period = request.query_params.get('period')
        if period:
            try:
                period_date = datetime.strptime(period, '%Y-%m-%d').date()
                period_filter['reporting_period'] = period_date
            except ValueError:
                return Response({'error': 'Invalid period format. Use YYYY-MM-DD'}, status=status.HTTP_400_BAD_REQUEST)

        submissions = ESGMetricSubmission.objects.filter(
            assignment_id=assignment_id,
            metric_id__in=metric_ids,
            layer_id__in=layer_ids,
            **period_filter
        ).select_related('metric', 'layer')

        result = {
            'assignment_id': assignment_id,
            'period': period,
            'metrics': {m.id: {'id': m.id, 'name': m.name, 'unit_type': m.unit_type, 'custom_unit': m.custom_unit, 'requires_time_reporting': m.requires_time_reporting, 'form_code': m.form.code} for m in metrics},
            'layers': {layer.id: {'id': layer.id, 'name': layer.company_name, 'type': layer.layer_type, 'location': layer.company_location} for layer in user_layers.filter(id__in=layer_ids)},
            'aggregation': []
        }

        for metric_id in metric_ids:
            metric_data = {'metric_id': metric_id, 'values_by_layer': {}}
            metric_info = result['metrics'][metric_id]

            for layer_id in layer_ids:
                layer_submissions = submissions.filter(metric_id=metric_id, layer_id=layer_id)
                value = None
                submission_id = None
                
                if period:
                    submission = layer_submissions.first()
                    value = submission.value if submission else None
                    submission_id = submission.id if submission else None
                else:
                    if metric_info['requires_time_reporting']:
                        values = [sub.value for sub in layer_submissions if sub.value is not None]
                        value = sum(values) if values else None
                    else:
                        submission = layer_submissions.first()
                        value = submission.value if submission else None
                        submission_id = submission.id if submission else None

                metric_data['values_by_layer'][layer_id] = {'value': value, 'submission_id': submission_id}
            
            result['aggregation'].append(metric_data)
            
        return Response(result) 