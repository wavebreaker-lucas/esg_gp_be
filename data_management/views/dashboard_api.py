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

from ..services.dashboard import get_total_emissions, get_emissions_time_series, get_vehicle_emissions_breakdown

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