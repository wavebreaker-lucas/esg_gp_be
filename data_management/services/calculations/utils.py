"""
Utilities for ESG metric calculations.
"""

import logging
import re
from collections import defaultdict

logger = logging.getLogger(__name__)

def get_calculation_metadata(schema_type):
    """
    Get calculation metadata for a specific schema type.
    
    Args:
        schema_type (str): The type identifier of the schema
        
    Returns:
        dict: A dictionary containing all calculation metadata from the schema
    """
    from ...json_schemas import SCHEMA_TEMPLATES
    
    # Handle case where a model object is passed instead of a string
    if hasattr(schema_type, '__class__') and not isinstance(schema_type, str):
        if hasattr(schema_type, 'schema_registry') and schema_type.schema_registry:
            # Handle ESGMetric with schema_registry
            if hasattr(schema_type.schema_registry, 'name'):
                schema_type = schema_type.schema_registry.name
            elif hasattr(schema_type.schema_registry, 'schema'):
                # Return metadata directly from the schema object
                schema = schema_type.schema_registry.schema
                return {
                    'calculated_fields': schema.get('calculated_fields', []),
                    'data_structure_type': schema.get('data_structure_type', schema.get('schema_type')),
                    'requires_calculation': schema.get('requires_calculation', False),
                    'calculation_type': schema.get('calculation_type')
                }
        return {'calculated_fields': []}
    
    if not schema_type or not isinstance(schema_type, str):
        return {'calculated_fields': []}
    
    if schema_type not in SCHEMA_TEMPLATES:
        return {'calculated_fields': []}
    
    schema = SCHEMA_TEMPLATES[schema_type]
    return {
        'calculated_fields': schema.get("calculated_fields", []),
        'data_structure_type': schema.get('data_structure_type', schema.get('schema_type')),
        'requires_calculation': schema.get('requires_calculation', False),
        'calculation_type': schema.get('calculation_type')
    }

def resolve_calculation_path(data, path_expr):
    """
    Resolve a path expression like 'periods.*.CLP.value' against data.
    
    Args:
        data (dict): The data to resolve against
        path_expr (str): Path expression with possible wildcards
        
    Returns:
        list: All values matching the path expression
    """
    parts = path_expr.split('.')
    values = []
    
    def _collect_values(current_data, remaining_parts):
        if not remaining_parts:
            # We've reached the end of the path, add value if it exists
            values.append(current_data)
            return
            
        part = remaining_parts[0]
        
        if part == '*':
            # Wildcard - iterate through all keys at this level
            if isinstance(current_data, dict):
                for key, value in current_data.items():
                    _collect_values(value, remaining_parts[1:])
        elif part in current_data:
            # Regular path component
            _collect_values(current_data[part], remaining_parts[1:])
    
    _collect_values(data, parts)
    return values

def evaluate_calculation(data, calculation_expr, path):
    """
    Evaluate a calculation expression like 'sum(periods.*.CLP.value)' 
    against the data.
    
    Args:
        data (dict): The data to evaluate against
        calculation_expr (str): Calculation expression
        path (str): Path where result should be stored
        
    Returns:
        any: The result of the calculation
    """
    # Extract the function and argument
    match = re.match(r'(\w+)\(([^)]+)\)', calculation_expr)
    if not match:
        logger.warning(f"Invalid calculation expression: {calculation_expr}")
        return None
        
    func_name, arg_path = match.groups()
    
    # Resolve the values to operate on
    values = resolve_calculation_path(data, arg_path)
    
    # Select numeric values only
    numeric_values = []
    for val in values:
        if isinstance(val, dict) and 'value' in val:
            # Extract the value if it's in a value/unit structure
            if val['value'] is not None and isinstance(val['value'], (int, float)):
                numeric_values.append(val['value'])
        elif isinstance(val, (int, float)):
            numeric_values.append(val)
    
    # Apply the requested calculation
    if func_name == 'sum':
        return sum(numeric_values) if numeric_values else 0
    elif func_name == 'avg' or func_name == 'average':
        return sum(numeric_values) / len(numeric_values) if numeric_values else 0
    elif func_name == 'max':
        return max(numeric_values) if numeric_values else 0
    elif func_name == 'min':
        return min(numeric_values) if numeric_values else 0
    elif func_name == 'count':
        return len(numeric_values)
    else:
        logger.warning(f"Unknown calculation function: {func_name}")
        return None

def set_calculated_value(data, path, value, preferred_unit=None):
    """
    Set a calculated value at the specified path in the data.
    Handles special cases like setting {value: X, unit: Y} objects.
    
    Args:
        data (dict): The data to modify
        path (str): Path where to set the value
        value: The calculated value
        preferred_unit (str, optional): Preferred unit for the value
        
    Returns:
        dict: The modified data
    """
    parts = path.split('.')
    current = data
    
    # Navigate to the parent of the target
    for i, part in enumerate(parts[:-1]):
        if part not in current:
            current[part] = {}
        current = current[part]
    
    last_part = parts[-1]
    
    # Check if target is a value/unit structure
    if isinstance(current.get(last_part), dict) and 'value' in current[last_part]:
        # Update value but preserve the unit
        current_unit = current[last_part].get('unit')
        current[last_part]['value'] = value
        
        # Use preferred unit if provided and no existing unit
        if not current_unit and preferred_unit:
            current[last_part]['unit'] = preferred_unit
    else:
        # Simple value assignment
        current[last_part] = value
    
    return data

def get_preferred_unit(data, path_expr):
    """
    Get the most common unit from a collection of records for use in totals.
    
    Args:
        data (dict): The data to analyze
        path_expr (str): Path expression identifying fields with units
        
    Returns:
        str: The most common unit
    """
    # Extract base path and get field name that holds unit
    base_path = '.'.join(path_expr.split('.')[:-1])  # Remove the last part (typically 'value')
    unit_path = f"{base_path}.unit"
    
    # Get all units matching the path
    unit_values = resolve_calculation_path(data, unit_path)
    
    # Count occurrences of each unit
    unit_counts = defaultdict(int)
    for unit in unit_values:
        if isinstance(unit, str):
            unit_counts[unit] += 1
    
    # Return most common unit
    if unit_counts:
        return max(unit_counts.items(), key=lambda x: x[1])[0]
    return None

def apply_schema_calculations(data, schema_type):
    """
    Apply all calculations defined in a schema to the data.
    
    Args:
        data (dict): The data to process
        schema_type (str): Schema type identifier
        
    Returns:
        dict: The data with all calculations applied
    """
    if not data or not isinstance(data, dict):
        return data
    
    logger.info(f"Applying schema calculations for schema_type: {schema_type}")
    
    metadata = get_calculation_metadata(schema_type)
    calculation_metadata = metadata.get('calculated_fields', [])
    requires_calculation = metadata.get('requires_calculation', False)
    
    # Early return if schema explicitly states no calculations required
    if requires_calculation is False:
        logger.info(f"Schema {schema_type} explicitly marked as not requiring calculations")
        return data
    
    if not calculation_metadata:
        # No calculations defined for this schema
        logger.info(f"No calculation metadata found for schema_type: {schema_type}")
        return data
    
    # Process each calculation
    for calc in calculation_metadata:
        path = calc.get('path')
        calculation = calc.get('calculation')
        
        if not path or not calculation:
            continue
        
        logger.info(f"Applying calculation: {calculation} for path: {path}")
        
        # Check for dependency paths to ensure required data is present
        dependency_paths = calc.get('dependency_paths', [])
        if dependency_paths:
            has_valid_dependencies = False
            for dep_path in dependency_paths:
                values = resolve_calculation_path(data, dep_path)
                if values and any(v is not None for v in values):
                    has_valid_dependencies = True
                    break
            
            if not has_valid_dependencies:
                logger.warning(f"Skipping calculation for {path} - dependencies not present")
                continue
        
        # Determine preferred unit if dealing with a value field
        preferred_unit = None
        if '.value' in calculation:
            unit_path = calculation.replace('.value', '.unit')
            preferred_unit = get_preferred_unit(data, unit_path)
        
        # Calculate the value
        result = evaluate_calculation(data, calculation, path)
        logger.info(f"Calculation result for {path}: {result}")
        
        # Set the result in the data
        if result is not None:
            data = set_calculated_value(data, path, result, preferred_unit)
    
    return data 