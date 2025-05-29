"""
Utility views related to metric submissions, separate from the main submission CRUD operations.
"""

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from datetime import datetime
import logging
from django.db.models import Sum
from django.db import models
from django.core.exceptions import ObjectDoesNotExist

# Import specific layer types
from accounts.models import LayerProfile, AppUser, GroupLayer, SubsidiaryLayer, BranchLayer, LayerTypeChoices
from accounts.services import get_accessible_layers, has_layer_access
from ...models import BaseESGMetric, TemplateAssignment, ESGMetricSubmission

logger = logging.getLogger(__name__)

class AvailableLayersView(APIView):
    """
    Provides a list of layers accessible to the current user,
    optionally filtered by the context of a template assignment.
    """
    permission_classes = [IsAuthenticated]

    def _get_specific_instance(self, layer_proxy):
        """Helper to get the specific subclass instance from a LayerProfile proxy."""
        if not isinstance(layer_proxy, LayerProfile):
            return layer_proxy # Already specific instance
        try:
            if layer_proxy.layer_type == LayerTypeChoices.GROUP:
                # Default related name is lowercase model name
                return layer_proxy.grouplayer 
            elif layer_proxy.layer_type == LayerTypeChoices.SUBSIDIARY:
                return layer_proxy.subsidiarylayer
            elif layer_proxy.layer_type == LayerTypeChoices.BRANCH:
                return layer_proxy.branchlayer
        except ObjectDoesNotExist: # Catch if related object doesn't exist
            logger.warning(
                f"Could not find specific instance for LayerProfile ID "
                f"{layer_proxy.pk} with type {layer_proxy.layer_type}"
            )
        # Fallback if type doesn't match or related obj not found
        return layer_proxy # Return base instance

    def _get_parent(self, layer):
        """Helper to get the actual parent layer based on type."""
        # Ensure we have the specific instance before checking parent relation
        specific_layer = self._get_specific_instance(layer)
        if isinstance(specific_layer, BranchLayer):
            return specific_layer.subsidiary_layer
        elif isinstance(specific_layer, SubsidiaryLayer):
            return specific_layer.group_layer
        else: # GroupLayer or base LayerProfile
            return None

    def _get_children(self, layer):
        """Helper to get child layers based on type."""
        # Ensure we have the specific instance before checking child relation
        specific_layer = self._get_specific_instance(layer)
        if isinstance(specific_layer, GroupLayer):
            # Use the specific instance to filter
            return SubsidiaryLayer.objects.filter(group_layer=specific_layer) 
        elif isinstance(specific_layer, SubsidiaryLayer):
            # Use the specific instance to filter
            return BranchLayer.objects.filter(subsidiary_layer=specific_layer)
        else: # BranchLayer or base LayerProfile
            return LayerProfile.objects.none() # Return empty queryset

    def get(self, request):
        """
        Get all layers that the current user has access to.
        
        Optional parameters:
            assignment_id: Filter layers to those relevant for a specific assignment
        """
        user_layers_qs = get_accessible_layers(request.user) # Start with QuerySet
        assignment_id = request.query_params.get('assignment_id')

        if assignment_id:
            try:
                # Fetch the assignment and its layer
                # Use select_related to potentially fetch subclass data efficiently
                assignment = TemplateAssignment.objects.select_related(
                    'layer__grouplayer', 
                    'layer__subsidiarylayer', 
                    'layer__branchlayer'
                ).get(id=assignment_id)
                # Use the helper to get the concrete layer instance
                assignment_layer = self._get_specific_instance(assignment.layer) 
                
                if not has_layer_access(request.user, assignment_layer):
                    return Response({'error': f'You do not have access to layer {assignment_layer.id}'}, status=status.HTTP_403_FORBIDDEN)

                # Logic to determine relevant layers based on assignment
                relevant_layers = set()
                relevant_layers.add(assignment_layer)

                # Add parent layers using the helper
                parent = self._get_parent(assignment_layer)
                while parent:
                    # Parent is already specific instance from _get_parent logic
                    if has_layer_access(request.user, parent):
                        relevant_layers.add(parent)
                    parent = self._get_parent(parent) # Get next parent

                # Add child layers using the helper
                children = self._get_children(assignment_layer)
                for child in children:
                    # Child is already specific instance from _get_children logic
                    if has_layer_access(request.user, child):
                        relevant_layers.add(child)
                        # Get grandchildren
                        grandchildren = self._get_children(child)
                        for grandchild in grandchildren:
                             # Grandchild is already specific instance
                             if has_layer_access(request.user, grandchild):
                                  relevant_layers.add(grandchild)
                
                # Filter the initial accessible layers queryset
                user_layers_qs = user_layers_qs.filter(id__in=[layer.id for layer in relevant_layers])

            except TemplateAssignment.DoesNotExist:
                return Response({'error': f'Assignment with ID {assignment_id} not found'}, status=status.HTTP_404_NOT_FOUND)
            except ObjectDoesNotExist: # Catch if specific layer access fails
                 logger.error(f"Could not find specific layer instance related to assignment {assignment_id}")
                 return Response({'error': 'Internal server error resolving layer hierarchy.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            except Exception as e: # Catch other potential errors
                logger.error(f"Error determining relevant layers for assignment {assignment_id}: {type(e).__name__} - {e}")
                import traceback
                logger.error(traceback.format_exc())
                # Fallback to just showing assignment layer if accessible
                try: # Need nested try for this fallback
                    # Fetch base layer for fallback check
                    assignment_layer_fb = TemplateAssignment.objects.get(id=assignment_id).layer
                    if has_layer_access(request.user, assignment_layer_fb):
                        user_layers_qs = user_layers_qs.filter(id=assignment_layer_fb.id)
                    else:
                        user_layers_qs = LayerProfile.objects.none() 
                except TemplateAssignment.DoesNotExist:
                    user_layers_qs = LayerProfile.objects.none() 
                except Exception as fb_e:
                    logger.error(f"Error during fallback layer access check: {fb_e}")
                    user_layers_qs = LayerProfile.objects.none()


        # Prepare result format
        result = []
        layers_processed = set()

        # Order the queryset before iteration
        # Add select_related for potential performance gain when getting specific instances
        ordered_layers = user_layers_qs.select_related(
            'grouplayer', 'subsidiarylayer', 'branchlayer'
        ).order_by('layer_type', 'company_name')

        for layer_proxy in ordered_layers:
            if layer_proxy.id in layers_processed:
                continue
                
            # Get the specific subclass instance using the helper
            layer = self._get_specific_instance(layer_proxy) 
            
            parent_info = None
            parent_layer = self._get_parent(layer)
            if parent_layer:
                 # Parent is already specific instance
                 if has_layer_access(request.user, parent_layer):
                      parent_info = {
                         'id': parent_layer.id,
                         'name': parent_layer.company_name
                      }
            
            layer_data = {
                'id': layer.id,
                'name': layer.company_name,
                'type': layer.layer_type, # Use the type from the instance
                'location': layer.company_location,
                'parent': parent_info # Use the potentially found parent info
            }
            result.append(layer_data)
            layers_processed.add(layer.id)

        # Sort the final list (optional, but keeps original behavior)
        type_order = {LayerTypeChoices.GROUP: 0, LayerTypeChoices.SUBSIDIARY: 1, LayerTypeChoices.BRANCH: 2}
        result.sort(key=lambda x: (type_order.get(x['type'], 99), x['name']))

        return Response(result)


class SumSubmissionsByLayerView(APIView):
    """
    Aggregates metric submission values by layer for a given assignment.
    NEEDS REWORK for Polymorphic Metrics.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        Get aggregated values for metric submissions by layer.
        """
        assignment_id = request.query_params.get('assignment_id')
        metric_ids_param = request.query_params.get('metric_ids')
        layer_ids_param = request.query_params.get('layer_ids')
        period_str = request.query_params.get('period')

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
        
        period = None
        if period_str:
            try:
                period = datetime.strptime(period_str, '%Y-%m-%d').date()
            except ValueError:
                 return Response({'error': 'Invalid period format. Use YYYY-MM-DD.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            assignment = TemplateAssignment.objects.get(id=assignment_id)
        except TemplateAssignment.DoesNotExist:
            return Response({'error': f'Assignment with ID {assignment_id} not found'}, status=status.HTTP_404_NOT_FOUND)
        
        accessible_layer_ids = get_accessible_layers(request.user)
        user_layers = LayerProfile.objects.filter(id__in=accessible_layer_ids)
        accessible_requested_layers = [l_id for l_id in layer_ids if l_id in accessible_layer_ids]
        if not accessible_requested_layers:
             return Response({'error': 'You do not have access to any of the requested layers'}, status=status.HTTP_403_FORBIDDEN)
        
        metrics = BaseESGMetric.objects.filter(id__in=metric_ids).select_related('form')
        if metrics.count() != len(metric_ids):
            found_ids = set(metrics.values_list('id', flat=True))
            missing_ids = set(metric_ids) - found_ids
            return Response({'error': f'Metrics not found: {missing_ids}'}, status=status.HTTP_404_NOT_FOUND)
        
        period_filter = {'reporting_period': period} if period else {}

        submissions = ESGMetricSubmission.objects.filter(
            assignment_id=assignment_id,
            metric_id__in=metric_ids,
            layer_id__in=accessible_requested_layers,
            **period_filter
        ).select_related('metric', 'layer')

        result = {
            'assignment_id': assignment_id,
            'period': period,
            'metrics': {m.id: {'id': m.id, 'name': m.name, 'form_code': m.form.code} 
                        for m in metrics},
            'layers': {layer.id: {'id': layer.id, 'name': layer.company_name, 'type': layer.layer_type, 'location': layer.company_location} 
                       for layer in user_layers.filter(id__in=accessible_requested_layers)},
            'aggregation': []
        }

        for metric_id in metric_ids:
            metric_data = {'metric_id': metric_id, 'values_by_layer': {}}
            for layer_id in accessible_requested_layers:
                layer_submissions = submissions.filter(metric_id=metric_id, layer_id=layer_id)
                value = None
                submission_id = None
                
                submission = layer_submissions.first()
                value = submission.value if submission else None
                submission_id = submission.id if submission else None
                
                metric_data['values_by_layer'][layer_id] = {'value': value, 'submission_id': submission_id}
            
            result['aggregation'].append(metric_data)
            
        return Response(result) 