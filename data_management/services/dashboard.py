"""
Service functions for generating dashboard data related to emissions and other ESG metrics.

This module provides optimized aggregation and formatting functions for dashboard visualizations.
"""

import logging
from datetime import datetime, date
from typing import Dict, List, Optional, Any, Tuple
from decimal import Decimal
from django.db.models import Sum, Count, F, Q, Value, CharField
from django.db.models.functions import Trunc, TruncMonth, TruncQuarter, TruncYear, Coalesce
from django.utils import timezone

from ..models.results import CalculatedEmissionValue
from ..models.templates import TemplateAssignment, ReportedMetricValue
from accounts.models import LayerProfile

logger = logging.getLogger(__name__)

def get_total_emissions(
    assignment_id: Optional[int] = None,
    layer_id: Optional[int] = None,
    year: Optional[int] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    level: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Aggregate total emissions data for dashboard visualization.
    
    Args:
        assignment_id: Optional filter for specific template assignment
        layer_id: Optional filter for specific layer/organization
        year: Optional filter for reporting year
        start_date: Optional start of date range (inclusive)
        end_date: Optional end of date range (inclusive)
        level: Optional aggregation level ('M' for monthly, 'A' for annual)
        
    Returns:
        Dictionary with total emissions data and breakdowns by scope and category
    """
    logger.info(f"Generating total emissions dashboard data")
    
    # Start with base query
    queryset = CalculatedEmissionValue.objects.all()
    
    # Apply filters if provided
    if assignment_id:
        queryset = queryset.filter(assignment_id=assignment_id)
    
    if layer_id:
        queryset = queryset.filter(layer_id=layer_id)
    
    if year:
        queryset = queryset.filter(reporting_period__year=year)
    
    if start_date:
        queryset = queryset.filter(reporting_period__gte=start_date)
    
    if end_date:
        queryset = queryset.filter(reporting_period__lte=end_date)
    
    if level:
        queryset = queryset.filter(level=level)
    
    # Make sure we have data before proceeding
    if not queryset.exists():
        logger.warning("No emission data found matching the specified filters")
        return {
            "total_emissions": 0,
            "by_scope": [],
            "by_category": [],
            "by_subcategory": [],
            "filters_applied": {
                "assignment_id": assignment_id,
                "layer_id": layer_id,
                "year": year,
                "start_date": start_date.isoformat() if start_date else None,
                "end_date": end_date.isoformat() if end_date else None,
                "level": level,
            }
        }
    
    # Get the most common unit for standardization
    # This is a simplification - proper unit conversion would be needed for mixed units
    common_unit = queryset.values('emission_unit').annotate(
        count=Count('id')
    ).order_by('-count').first()['emission_unit']
    
    # Get total emissions
    total = queryset.aggregate(total=Sum('calculated_value'))['total'] or Decimal('0')
    
    # Group by scope
    scope_data = list(queryset.values('emission_scope')
        .annotate(total=Sum('calculated_value'))
        .order_by('emission_scope'))
    
    # Calculate percentages for scope data
    if total > 0:
        for item in scope_data:
            item['percentage'] = (item['total'] / total) * 100
    
    # Group by category
    category_data = list(queryset.values(
            'source_activity_value__metric__emission_category'
        )
        .annotate(
            category=F('source_activity_value__metric__emission_category'),
            total=Sum('calculated_value')
        )
        .order_by('category'))
    
    # Calculate percentages for category data
    if total > 0:
        for item in category_data:
            item['percentage'] = (item['total'] / total) * 100
    
    # Group by subcategory
    subcategory_data = list(queryset.values(
            'source_activity_value__metric__emission_category',
            'source_activity_value__metric__emission_sub_category'
        )
        .annotate(
            category=F('source_activity_value__metric__emission_category'),
            subcategory=F('source_activity_value__metric__emission_sub_category'),
            total=Sum('calculated_value')
        )
        .order_by('category', 'subcategory'))
    
    # Calculate percentages for subcategory data
    if total > 0:
        for item in subcategory_data:
            item['percentage'] = (item['total'] / total) * 100
    
    # Construct the response
    result = {
        "total_emissions": total,
        "unit": common_unit,
        "by_scope": scope_data,
        "by_category": category_data,
        "by_subcategory": subcategory_data,
        "filters_applied": {
            "assignment_id": assignment_id,
            "layer_id": layer_id,
            "year": year,
            "start_date": start_date.isoformat() if start_date else None,
            "end_date": end_date.isoformat() if end_date else None,
            "level": level,
        }
    }
    
    logger.info(f"Generated total emissions data with {len(scope_data)} scope segments, {len(category_data)} categories")
    return result

def get_emissions_time_series(
    period: str = 'monthly',
    assignment_id: Optional[int] = None,
    layer_id: Optional[int] = None,
    year: Optional[int] = None,
    scope: Optional[str] = None,
    category: Optional[str] = None,
    subcategory: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    level: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Generate time series data for emissions over time.
    
    Args:
        period: Aggregation period - 'monthly', 'quarterly', or 'annual'
        assignment_id: Optional filter for specific template assignment
        layer_id: Optional filter for specific layer/organization
        year: Optional filter for reporting year
        scope: Optional filter for specific emission scope (1, 2, 3)
        category: Optional filter for specific emission category
        subcategory: Optional filter for specific emission subcategory
        start_date: Optional start of date range (inclusive)
        end_date: Optional end of date range (inclusive)
        level: Optional aggregation level ('M' for monthly, 'A' for annual)
        
    Returns:
        Dictionary with time series data for emissions
    """
    logger.info(f"Generating emissions time series data with period: {period}")
    
    # Start with base query
    queryset = CalculatedEmissionValue.objects.all()
    
    # Apply filters if provided
    if assignment_id:
        queryset = queryset.filter(assignment_id=assignment_id)
    
    if layer_id:
        queryset = queryset.filter(layer_id=layer_id)
    
    if year:
        queryset = queryset.filter(reporting_period__year=year)
    
    if scope:
        queryset = queryset.filter(emission_scope=scope)
    
    if category:
        queryset = queryset.filter(source_activity_value__metric__emission_category=category)
    
    if subcategory:
        queryset = queryset.filter(source_activity_value__metric__emission_sub_category=subcategory)
    
    if start_date:
        queryset = queryset.filter(reporting_period__gte=start_date)
    
    if end_date:
        queryset = queryset.filter(reporting_period__lte=end_date)
    
    if level:
        queryset = queryset.filter(level=level)
    
    # Make sure we have data before proceeding
    if not queryset.exists():
        logger.warning("No emission data found matching the specified filters for time series")
        return {
            "time_series": [],
            "period": period,
            "filters_applied": {
                "assignment_id": assignment_id,
                "layer_id": layer_id,
                "year": year,
                "scope": scope,
                "category": category,
                "subcategory": subcategory,
                "start_date": start_date.isoformat() if start_date else None,
                "end_date": end_date.isoformat() if end_date else None,
                "level": level,
            }
        }
    
    # Select the appropriate truncation function based on period
    if period == 'monthly':
        trunc_func = TruncMonth('reporting_period')
        period_name = 'month'
    elif period == 'quarterly':
        trunc_func = TruncQuarter('reporting_period')
        period_name = 'quarter'
    elif period == 'annual':
        trunc_func = TruncYear('reporting_period')
        period_name = 'year'
    else:
        # Default to monthly if invalid period is provided
        trunc_func = TruncMonth('reporting_period')
        period_name = 'month'
    
    # Get the most common unit for standardization
    common_unit = queryset.values('emission_unit').annotate(
        count=Count('id')
    ).order_by('-count').first()['emission_unit']
    
    # Group by time period and scope
    time_series = list(queryset
        .annotate(period_date=trunc_func)
        .values('period_date', 'emission_scope')
        .annotate(total=Sum('calculated_value'))
        .order_by('period_date', 'emission_scope'))
    
    # Construct the response
    result = {
        "time_series": time_series,
        "unit": common_unit,
        "period": period,
        "filters_applied": {
            "assignment_id": assignment_id,
            "layer_id": layer_id,
            "year": year,
            "scope": scope,
            "category": category,
            "subcategory": subcategory,
            "start_date": start_date.isoformat() if start_date else None,
            "end_date": end_date.isoformat() if end_date else None,
            "level": level,
        }
    }
    
    logger.info(f"Generated emissions time series with {len(time_series)} data points")
    return result 