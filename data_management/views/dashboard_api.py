"""
API views for ESG dashboard data.
"""

import logging
from datetime import datetime
from django.http import JsonResponse
from django.views.decorators.http import require_GET
from django.contrib.auth.decorators import login_required

from ..services.dashboard import get_total_emissions, get_emissions_time_series

logger = logging.getLogger(__name__)

@require_GET
@login_required
def total_emissions_api(request):
    """
    API endpoint for total emissions dashboard data.
    
    Query parameters:
    - assignment_id: Filter by template assignment
    - layer_id: Filter by organization/layer
    - year: Filter by year
    - start_date: Filter by start date (YYYY-MM-DD)
    - end_date: Filter by end date (YYYY-MM-DD)
    - level: Filter by aggregation level (M=monthly, A=annual)
    """
    try:
        # Extract query parameters
        assignment_id = request.GET.get('assignment_id')
        if assignment_id:
            assignment_id = int(assignment_id)
            
        layer_id = request.GET.get('layer_id')
        if layer_id:
            layer_id = int(layer_id)
            
        year = request.GET.get('year')
        if year:
            year = int(year)
            
        start_date = request.GET.get('start_date')
        if start_date:
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
            
        end_date = request.GET.get('end_date')
        if end_date:
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
            
        level = request.GET.get('level')
        
        # Call the service function
        result = get_total_emissions(
            assignment_id=assignment_id,
            layer_id=layer_id,
            year=year,
            start_date=start_date,
            end_date=end_date,
            level=level
        )
        
        return JsonResponse(result, safe=True)
        
    except Exception as e:
        logger.error(f"Error generating total emissions data: {e}", exc_info=True)
        return JsonResponse({
            'error': 'An error occurred while generating emissions data',
            'message': str(e)
        }, status=500)

@require_GET
@login_required
def emissions_time_series_api(request):
    """
    API endpoint for emissions time series data.
    
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
        # Extract query parameters
        period = request.GET.get('period', 'monthly')
        
        assignment_id = request.GET.get('assignment_id')
        if assignment_id:
            assignment_id = int(assignment_id)
            
        layer_id = request.GET.get('layer_id')
        if layer_id:
            layer_id = int(layer_id)
            
        year = request.GET.get('year')
        if year:
            year = int(year)
            
        scope = request.GET.get('scope')
        category = request.GET.get('category')
        subcategory = request.GET.get('subcategory')
        
        start_date = request.GET.get('start_date')
        if start_date:
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
            
        end_date = request.GET.get('end_date')
        if end_date:
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
            
        level = request.GET.get('level')
        
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
        
        return JsonResponse(result, safe=True)
        
    except Exception as e:
        logger.error(f"Error generating emissions time series data: {e}", exc_info=True)
        return JsonResponse({
            'error': 'An error occurred while generating emissions time series data',
            'message': str(e)
        }, status=500) 