"""
API views for ESG dashboard data.
"""

import logging
from datetime import datetime
# Remove Django imports if present
# from django.http import JsonResponse
# from django.views.decorators.http import require_GET
# from django.contrib.auth.decorators import login_required

# Import DRF components
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView
from django.db.models import Count, Q, Max

from ..services.dashboard import get_total_emissions, get_emissions_time_series, get_vehicle_emissions_breakdown
from accounts.models import LayerTypeChoices
from accounts.services.layer_services import (
    get_full_group_layer_data,
    get_user_accessible_layer_data,
    get_layer_parent_specific,
    get_specific_layer_instance
)
from data_management.models import TemplateAssignment, ESGMetricSubmission, Template
from django.core.exceptions import ObjectDoesNotExist, PermissionDenied

logger = logging.getLogger(__name__)

@api_view(['GET']) # Use DRF decorator for allowed methods
@permission_classes([IsAuthenticated]) # Use DRF permission class
def total_emissions_api(request):
    """
    API endpoint for total emissions dashboard data.
    Uses DRF authentication and permissions.
    
    Query parameters:
    - assignment_id: Filter by template assignment
    - layer_id: Filter by organization/layer
    - year: Filter by year
    - start_date: Filter by start date (YYYY-MM-DD)
    - end_date: Filter by end date (YYYY-MM-DD)
    - level: Filter by aggregation level (M=monthly, A=annual)
    """
    try:
        # Extract query parameters using request.query_params
        assignment_id = request.query_params.get('assignment_id')
        if assignment_id:
            assignment_id = int(assignment_id)
            
        layer_id = request.query_params.get('layer_id')
        if layer_id:
            layer_id = int(layer_id)
            
        year = request.query_params.get('year')
        if year:
            year = int(year)
            
        start_date = request.query_params.get('start_date')
        if start_date:
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
            
        end_date = request.query_params.get('end_date')
        if end_date:
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
            
        level = request.query_params.get('level')
        
        # Call the service function
        result = get_total_emissions(
            assignment_id=assignment_id,
            layer_id=layer_id,
            year=year,
            start_date=start_date,
            end_date=end_date,
            level=level
        )
        
        # Use DRF Response
        return Response(result)
        
    except Exception as e:
        logger.error(f"Error generating total emissions data: {e}", exc_info=True)
        # Use DRF Response for errors
        return Response({
            'error': 'An error occurred while generating emissions data',
            'message': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET']) # Use DRF decorator
@permission_classes([IsAuthenticated]) # Use DRF permission class
def emissions_time_series_api(request):
    """
    API endpoint for emissions time series data.
    Uses DRF authentication and permissions.
    
    Query parameters:
    - period: Aggregation period (monthly, quarterly, annual)
    - assignment_id: Filter by template assignment
    - layer_id: Filter by organization/layer
    - year: Filter by year
    - scope: Filter by emission scope (1, 2, 3)
    - category: Filter by emission category
    - subcategory: Filter by emission subcategory
    - start_date: Filter by start date (YYYY-MM-DD)
    - end_date: Filter by end date (YYYY-MM-DD)
    - level: Filter by aggregation level (M=monthly, A=annual)
    """
    try:
        # Extract query parameters using request.query_params
        period = request.query_params.get('period', 'monthly')
        
        assignment_id = request.query_params.get('assignment_id')
        if assignment_id:
            assignment_id = int(assignment_id)
            
        layer_id = request.query_params.get('layer_id')
        if layer_id:
            layer_id = int(layer_id)
            
        year = request.query_params.get('year')
        if year:
            year = int(year)
            
        scope = request.query_params.get('scope')
        category = request.query_params.get('category')
        subcategory = request.query_params.get('subcategory')
        
        start_date = request.query_params.get('start_date')
        if start_date:
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
            
        end_date = request.query_params.get('end_date')
        if end_date:
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
            
        level = request.query_params.get('level')
        
        # Call the service function
        result = get_emissions_time_series(
            period=period,
            assignment_id=assignment_id,
            layer_id=layer_id,
            year=year,
            scope=scope,
            category=category,
            subcategory=subcategory,
            start_date=start_date,
            end_date=end_date,
            level=level
        )
        
        # Use DRF Response
        return Response(result)
        
    except Exception as e:
        logger.error(f"Error generating emissions time series data: {e}", exc_info=True)
        # Use DRF Response for errors
        return Response({
            'error': 'An error occurred while generating emissions time series data',
            'message': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET']) # Use DRF decorator
@permission_classes([IsAuthenticated]) # Use DRF permission class
def vehicle_emissions_breakdown_api(request):
    """
    API endpoint for vehicle emissions breakdown data.
    Uses DRF authentication and permissions.
    
    Query parameters:
    - assignment_id: Filter by template assignment
    - layer_id: Filter by organization/layer
    - year: Filter by year
    - period_date: Filter by specific date (YYYY-MM-DD)
    - level: Filter by aggregation level (M=monthly, A=annual)
    """
    try:
        # Extract query parameters using request.query_params
        assignment_id = request.query_params.get('assignment_id')
        if assignment_id:
            assignment_id = int(assignment_id)
            
        layer_id = request.query_params.get('layer_id')
        if layer_id:
            layer_id = int(layer_id)
            
        year = request.query_params.get('year')
        if year:
            year = int(year)
            
        period_date = request.query_params.get('period_date')
        if period_date:
            period_date = datetime.strptime(period_date, '%Y-%m-%d').date()
            
        level = request.query_params.get('level')
        
        # Call the service function
        result = get_vehicle_emissions_breakdown(
            assignment_id=assignment_id,
            layer_id=layer_id,
            year=year,
            period_date=period_date,
            level=level
        )
        
        # Use DRF Response
        return Response(result)
        
    except Exception as e:
        logger.error(f"Error generating vehicle emissions breakdown data: {e}", exc_info=True)
        # Use DRF Response for errors
        return Response({
            'error': 'An error occurred while generating vehicle emissions breakdown data',
            'message': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class UnifiedViewableLayersView(APIView):
    permission_classes = [IsAuthenticated]

    def _get_assignment_metadata(self, layer_ids):
        """
        Get assignment and submission metadata for given layer IDs.
        Returns a dict mapping layer_id to metadata in the frontend's desired format.
        """
        if not layer_ids:
            return {}
        
        metadata_map = {}
        
        # Initialize all layers with default values
        for layer_id in layer_ids:
            metadata_map[layer_id] = {
                'assignment_count': 0,
                'active_templates': [],
                'has_submissions': False,
                'last_activity': None
            }
        
        # Get active template assignments with template details
        active_assignments = TemplateAssignment.objects.filter(
            layer_id__in=layer_ids,
            template__is_active=True
        ).select_related('template').values(
            'layer_id', 'template__id', 'template__name', 'status', 'assigned_at'
        )
        
        # Get assignment counts per layer
        assignment_counts = TemplateAssignment.objects.filter(
            layer_id__in=layer_ids
        ).values('layer_id').annotate(
            count=Count('id'),
            last_assigned=Max('assigned_at')
        )
        
        # Check for submissions existence
        submission_exists = ESGMetricSubmission.objects.filter(
            layer_id__in=layer_ids
        ).values('layer_id').annotate(
            has_submissions=Count('id') > 0,
            last_submission=Max('submitted_at')
        )
        
        # Populate assignment counts
        for item in assignment_counts:
            layer_id = item['layer_id']
            if layer_id in metadata_map:
                metadata_map[layer_id]['assignment_count'] = item['count']
                if item['last_assigned']:
                    metadata_map[layer_id]['last_activity'] = item['last_assigned'].isoformat()
        
        # Populate active templates
        for assignment in active_assignments:
            layer_id = assignment['layer_id']
            if layer_id in metadata_map:
                metadata_map[layer_id]['active_templates'].append({
                    'id': assignment['template__id'],
                    'name': assignment['template__name'],
                    'status': assignment['status']
                })
        
        # Populate submission data
        for item in submission_exists:
            layer_id = item['layer_id']
            if layer_id in metadata_map:
                metadata_map[layer_id]['has_submissions'] = item['has_submissions']
                # Update last_activity if submission is more recent
                if item['last_submission']:
                    submission_time = item['last_submission'].isoformat()
                    current_last = metadata_map[layer_id]['last_activity']
                    if not current_last or submission_time > current_last:
                        metadata_map[layer_id]['last_activity'] = submission_time
        
        return metadata_map

    def _transform_to_flat_layer_dto(self, layer_instance, parent_id=None, metadata=None):
        """Standardized output for a layer in the frontend's desired format."""
        # Ensure we have the specific instance to access all common fields correctly
        # (company_name, company_location, layer_type are on LayerProfile and inherited)
        specific_layer = get_specific_layer_instance(layer_instance)
        
        base_dto = {
            'id': specific_layer.pk, # Use .pk for consistency across specific/proxy
            'name': specific_layer.company_name,
            'type': specific_layer.layer_type,
            'location': specific_layer.company_location,
            'parentId': parent_id,
            'assignment_count': 0,
            'active_templates': [],
            'has_submissions': False,
            'last_activity': None
        }
        
        # Add metadata if provided
        if metadata and specific_layer.pk in metadata:
            layer_metadata = metadata[specific_layer.pk]
            base_dto.update({
                'assignment_count': layer_metadata.get('assignment_count', 0),
                'active_templates': layer_metadata.get('active_templates', []),
                'has_submissions': layer_metadata.get('has_submissions', False),
                'last_activity': layer_metadata.get('last_activity')
            })
        
        return base_dto

    def get(self, request):
        view_as_group_id_str = request.query_params.get('view_as_group_id')
        assignment_id_str = request.query_params.get('assignment_id')
        include_metadata = request.query_params.get('include_metadata', '').lower() == 'true'
        filter_active_only = request.query_params.get('filter_active_only', '').lower() == 'true'
        
        user = request.user
        
        # Check if the user is a Baker Tilly Admin.
        # This assumes CustomUser model has 'is_baker_tilly_admin' attribute
        is_bt_admin = hasattr(user, 'is_baker_tilly_admin') and user.is_baker_tilly_admin

        flat_layers_list = []
        metadata_map = {}

        try:
            if is_bt_admin and view_as_group_id_str:
                try:
                    group_id = int(view_as_group_id_str)
                    raw_group_data = get_full_group_layer_data(group_id) # Service raises DoesNotExist

                    # Collect all layer IDs for metadata query
                    all_layer_ids = [raw_group_data['group'].pk]
                    for sub_obj, branches_list in raw_group_data.get('subsidiaries_with_branches', []):
                        all_layer_ids.append(sub_obj.pk)
                        all_layer_ids.extend([branch.pk for branch in branches_list])
                    
                    # Get metadata if requested
                    if include_metadata:
                        metadata_map = self._get_assignment_metadata(all_layer_ids)
                    
                    # Build response
                    group_obj = raw_group_data['group']
                    flat_layers_list.append(self._transform_to_flat_layer_dto(group_obj, None, metadata_map))
                    for sub_obj, branches_list in raw_group_data.get('subsidiaries_with_branches', []):
                        flat_layers_list.append(self._transform_to_flat_layer_dto(sub_obj, group_obj.pk, metadata_map))
                        for branch_obj in branches_list:
                            flat_layers_list.append(self._transform_to_flat_layer_dto(branch_obj, sub_obj.pk, metadata_map))
                
                except ValueError:
                    return Response({'error': 'Invalid view_as_group_id. Must be an integer.'}, status=status.HTTP_400_BAD_REQUEST)
                # GroupLayer.DoesNotExist will be caught by the broader ObjectDoesNotExist below if service raises it

            elif not is_bt_admin and view_as_group_id_str:
                return Response({'error': 'You are not authorized to use the view_as_group_id parameter.'}, status=status.HTTP_403_FORBIDDEN)
            
            else: # Company Admin, or BT Admin not "Viewing As" a specific group
                assignment_id = None
                if assignment_id_str:
                    try:
                        assignment_id = int(assignment_id_str)
                    except ValueError:
                        return Response({'error': 'Invalid assignment_id. Must be an integer.'}, status=status.HTTP_400_BAD_REQUEST)
                
                accessible_specific_layers = get_user_accessible_layer_data(user, assignment_id)
                
                # Get metadata if requested
                if include_metadata:
                    layer_ids = [layer.pk for layer in accessible_specific_layers]
                    metadata_map = self._get_assignment_metadata(layer_ids)
                
                # Create a map of specific layer instances by their ID for quick parent lookup
                # This is important if accessible_specific_layers doesn't guarantee parent presence
                layer_map_for_parent_check = {layer.pk: layer for layer in accessible_specific_layers}

                for layer_inst in accessible_specific_layers:
                    parent_id = None
                    # Resolve parent using the service helper
                    parent_specific_instance = get_layer_parent_specific(layer_inst)
                    if parent_specific_instance:
                        # Ensure the resolved parent is also in the user's accessible list
                        # before assigning its ID as parentId. This prevents showing a parent
                        # the user shouldn't necessarily see in *this specific flat list context*,
                        # though has_layer_access in the service already did checks.
                        # This check is more about constructing the hierarchy from *this* list.
                        if parent_specific_instance.pk in layer_map_for_parent_check:
                             parent_id = parent_specific_instance.pk
                    
                    layer_dto = self._transform_to_flat_layer_dto(layer_inst, parent_id, metadata_map)
                    
                    # Apply filtering if requested
                    if filter_active_only and include_metadata:
                        if not (layer_dto.get('assignment_count', 0) > 0 or layer_dto.get('has_submissions', False)):
                            continue
                    
                    flat_layers_list.append(layer_dto)

        except (ObjectDoesNotExist, TemplateAssignment.DoesNotExist) as e: # Catch specific DoesNotExist errors
            # Handle cases where GroupLayer, TemplateAssignment, or a specific layer for assignment is not found
            logger.warning(f"UnifiedViewableLayersView: Object not found - {str(e)}")
            return Response({'error': f'Resource not found: {str(e)}'}, status=status.HTTP_404_NOT_FOUND)
        except PermissionDenied as e:
            logger.warning(f"UnifiedViewableLayersView: Permission denied - {str(e)}")
            return Response({'error': str(e)}, status=status.HTTP_403_FORBIDDEN)
        except Exception as e:
            logger.error(f"UnifiedViewableLayersView: An unexpected error occurred - {type(e).__name__}: {str(e)}", exc_info=True)
            return Response({'error': 'An internal server error occurred.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Consistent sorting
        type_order = {LayerTypeChoices.GROUP: 0, LayerTypeChoices.SUBSIDIARY: 1, LayerTypeChoices.BRANCH: 2}
        # Ensure x['type'] is valid before using in get, provide a default for robustness
        flat_layers_list.sort(key=lambda x: (type_order.get(x.get('type'), 99), x.get('name', '')))
        
        return Response(flat_layers_list)

# End of file - removing test functions 