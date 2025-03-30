"""
ESG metric calculation package using class-based handlers.
This package provides a registry pattern for different schema-specific calculation handlers.
"""

import logging
import importlib
import os
from pathlib import Path

logger = logging.getLogger(__name__)

# Registry of calculation handlers
CALCULATION_HANDLERS = {}

def register_calculation_handler(schema_type, handler_function):
    """
    Register a calculation handler for a specific schema type.
    
    Args:
        schema_type (str): The type identifier of the schema
        handler_function (callable): Function that processes data for this schema
    """
    global CALCULATION_HANDLERS
    CALCULATION_HANDLERS[schema_type] = handler_function
    logger.info(f"Registered calculation handler for schema type: {schema_type}")

def validate_and_update_totals(data, schema_type=None):
    """
    Validate and update total consumption in a submission's data.
    Uses explicit schema type if provided, with fallback to structure detection.
    
    Args:
        data: The JSON data structure from an ESG metric submission
        schema_type: Optional schema type or ESGMetric object with schema_registry
        
    Returns:
        dict: The updated data with correct totals
    """
    if not data or not isinstance(data, dict):
        return data
    
    # Extract schema type if an ESGMetric object was passed
    metric_obj = None
    if hasattr(schema_type, '__class__') and hasattr(schema_type, 'schema_registry'):
        metric_obj = schema_type
        if schema_type.schema_registry:
            schema_type = schema_type.schema_registry.name
        elif hasattr(schema_type, 'schema_type') and schema_type.schema_type:
            schema_type = schema_type.schema_type
        else:
            schema_type = None
    
    # Try schema-based calculation through explicit registry
    if schema_type and schema_type in CALCULATION_HANDLERS:
        logger.info(f"Using registered calculation handler for schema type: {schema_type}")
        return CALCULATION_HANDLERS[schema_type](data)
    
    # If we have a schema_registry but no explicit handler, use calculation metadata approach
    if schema_type:
        from .utils import apply_schema_calculations
        logger.info(f"Using schema-based calculation for: {schema_type}")
        return apply_schema_calculations(data, schema_type)
    
    # Structure detection as a fallback (legacy mode)
    if 'periods' not in data:
        return data
        
    logger.warning("No schema type provided, falling back to structure detection (legacy mode)")
    periods = data.get('periods', {})
    if not isinstance(periods, dict) or not periods:
        return data
    
    # Determine the structure
    sample_period = next(iter(periods.values()), {})
    
    # Import handlers only when needed (avoiding circular imports)
    if 'CLP' in sample_period and 'HKE' in sample_period:
        from .electricity_hk import calculate_electricity_hk
        return calculate_electricity_hk(data)
    
    elif 'value' in sample_period and 'unit' in sample_period:
        from .electricity_prc import calculate_electricity_prc
        return calculate_electricity_prc(data)
    
    elif 'HK' in sample_period and 'PRC' in sample_period:
        from .water_consumption import calculate_water_consumption
        return calculate_water_consumption(data)
    
    return data

def load_handlers():
    """
    Dynamically load all calculation handlers in this package.
    This will import all modules in the calculations directory and
    automatically register any handlers they define.
    """
    current_dir = Path(__file__).parent
    for file_path in current_dir.glob('*.py'):
        if file_path.name.startswith('__'):
            continue
            
        module_name = file_path.stem
        try:
            importlib.import_module(f'.{module_name}', package='data_management.services.calculations')
            logger.info(f"Loaded calculation handler module: {module_name}")
        except Exception as e:
            logger.error(f"Error loading handler module {module_name}: {e}")

# Load all handlers when this module is imported
load_handlers()

# For convenient imports
__all__ = ['validate_and_update_totals', 'register_calculation_handler', 'CALCULATION_HANDLERS'] 