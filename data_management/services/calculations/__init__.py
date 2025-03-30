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

def get_schema_type_from_metric(metric):
    """
    Extract schema type from a metric object.
    
    Args:
        metric: An ESGMetric object or similar with schema information
        
    Returns:
        str: The schema type
    """
    if not metric:
        return None
        
    # Try to get from schema_registry
    if hasattr(metric, 'schema_registry') and metric.schema_registry:
        if hasattr(metric.schema_registry, 'name'):
            return metric.schema_registry.name
        elif hasattr(metric.schema_registry, 'schema') and 'type' in metric.schema_registry.schema:
            return metric.schema_registry.schema['type']
            
    # Try to get from schema_type attribute
    if hasattr(metric, 'schema_type') and metric.schema_type:
        return metric.schema_type
        
    return None

def validate_and_update_totals(data, schema_type=None):
    """
    Validate and update total consumption in a submission's data.
    Uses explicit schema type if provided.
    
    Args:
        data: The JSON data structure from an ESG metric submission
        schema_type: Optional schema type or ESGMetric object with schema_registry
        
    Returns:
        dict: The updated data with correct totals
    """
    if not data or not isinstance(data, dict):
        return data
    
    # Extract schema type if a metric object was passed
    if schema_type and not isinstance(schema_type, str):
        schema_type = get_schema_type_from_metric(schema_type)
    
    # If no schema type could be determined, return data unchanged
    if not schema_type:
        logger.warning("No schema type provided and no way to determine it. Returning data unchanged.")
        return data
    
    # Try schema-based calculation through explicit registry
    if schema_type in CALCULATION_HANDLERS:
        logger.info(f"Using registered calculation handler for schema type: {schema_type}")
        return CALCULATION_HANDLERS[schema_type](data)
    
    # If handler not found, use calculation metadata approach
    from .utils import apply_schema_calculations, get_calculation_metadata
    
    # Get schema metadata to determine if calculation is needed
    metadata = get_calculation_metadata(schema_type)
    requires_calculation = metadata.get('requires_calculation', False)
    
    # Skip calculation if explicitly marked as not requiring it
    if requires_calculation is False:
        logger.info(f"Schema {schema_type} is marked as not requiring calculations")
        return data
        
    logger.info(f"Using schema-based metadata calculation for: {schema_type}")
    return apply_schema_calculations(data, schema_type)

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