"""
Services for calculating and validating ESG metric data.
This module provides consistent calculation functions used across the platform.
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
        list: A list of calculation definitions from the schema
    """
    from ..json_schemas import SCHEMA_TEMPLATES
    
    # Handle case where a model object is passed instead of a string
    if hasattr(schema_type, '__class__') and not isinstance(schema_type, str):
        if hasattr(schema_type, 'schema_registry') and schema_type.schema_registry:
            # Handle ESGMetric with schema_registry
            if hasattr(schema_type.schema_registry, 'name'):
                schema_type = schema_type.schema_registry.name
            elif hasattr(schema_type.schema_registry, 'schema') and 'calculated_fields' in schema_type.schema_registry.schema:
                # Return calculated fields directly from the schema object
                return schema_type.schema_registry.schema.get('calculated_fields', [])
    
    if not schema_type or not isinstance(schema_type, str):
        return []
    
    if schema_type not in SCHEMA_TEMPLATES:
        return []
    
    schema = SCHEMA_TEMPLATES[schema_type]
    return schema.get("calculated_fields", [])

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
            if isinstance(val['value'], (int, float)):
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
    
    calculation_metadata = get_calculation_metadata(schema_type)
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

def validate_and_update_totals(data, schema_type=None):
    """
    Validate and update total consumption in a submission's data.
    If schema_type is provided, use schema-specific calculations.
    Otherwise fall back to schema structure detection.
    
    Args:
        data: The JSON data structure from an ESG metric submission
        schema_type: Optional schema type for specific calculation rules
        
    Returns:
        dict: The updated data with correct totals
    """
    if not data or not isinstance(data, dict) or 'periods' not in data:
        return data
    
    # If schema_type is provided, use schema-specific calculations
    if schema_type:
        return apply_schema_calculations(data, schema_type)
    
    # Otherwise, fall back to old behavior that detects schema structure
    periods = data.get('periods', {})
    if not isinstance(periods, dict) or not periods:
        return data
    
    # Determine the structure (Hong Kong electricity, PRC electricity, or water by region)
    sample_period = next(iter(periods.values()), {})
    
    # Handle electricity_hk schema (CLP/HKE providers)
    if 'CLP' in sample_period and 'HKE' in sample_period:
        totals = {
            'CLP': {'value': 0, 'unit': None},
            'HKE': {'value': 0, 'unit': None}
        }
        
        for period_key, period_data in periods.items():
            # Sum CLP values
            if 'CLP' in period_data and isinstance(period_data['CLP'], dict):
                clp_data = period_data['CLP']
                if 'value' in clp_data and clp_data['value'] is not None:
                    totals['CLP']['value'] += float(clp_data['value'])
                    # Capture unit from the first valid entry
                    if totals['CLP']['unit'] is None and 'unit' in clp_data:
                        totals['CLP']['unit'] = clp_data['unit']
            
            # Sum HKE values
            if 'HKE' in period_data and isinstance(period_data['HKE'], dict):
                hke_data = period_data['HKE']
                if 'value' in hke_data and hke_data['value'] is not None:
                    totals['HKE']['value'] += float(hke_data['value'])
                    # Capture unit from the first valid entry
                    if totals['HKE']['unit'] is None and 'unit' in hke_data:
                        totals['HKE']['unit'] = hke_data['unit']
        
        # Set or update total consumption
        if 'total_consumption' not in data:
            data['total_consumption'] = totals
        else:
            # Update existing totals
            for key in ['CLP', 'HKE']:
                if key not in data['total_consumption']:
                    data['total_consumption'][key] = totals[key]
                else:
                    data['total_consumption'][key]['value'] = totals[key]['value']
                    if 'unit' not in data['total_consumption'][key] and totals[key]['unit']:
                        data['total_consumption'][key]['unit'] = totals[key]['unit']
    
    # Handle electricity_prc schema (single value per period)
    elif 'value' in sample_period and 'unit' in sample_period:
        total = {'value': 0, 'unit': None}
        
        for period_key, period_data in periods.items():
            if isinstance(period_data, dict) and 'value' in period_data and period_data['value'] is not None:
                total['value'] += float(period_data['value'])
                # Capture unit from the first valid entry
                if total['unit'] is None and 'unit' in period_data:
                    total['unit'] = period_data['unit']
        
        # Set or update total consumption
        if 'total_consumption' not in data:
            data['total_consumption'] = total
        else:
            if isinstance(data['total_consumption'], dict):
                data['total_consumption']['value'] = total['value']
                if 'unit' not in data['total_consumption'] and total['unit']:
                    data['total_consumption']['unit'] = total['unit']
    
    # Handle water schemas (HK/PRC regions)
    elif 'HK' in sample_period and 'PRC' in sample_period:
        totals = {
            'HK': {'value': 0, 'unit': None},
            'PRC': {'value': 0, 'unit': None}
        }
        
        for period_key, period_data in periods.items():
            # Sum HK values
            if 'HK' in period_data and isinstance(period_data['HK'], dict):
                hk_data = period_data['HK']
                if 'value' in hk_data and hk_data['value'] is not None:
                    totals['HK']['value'] += float(hk_data['value'])
                    # Capture unit from the first valid entry
                    if totals['HK']['unit'] is None and 'unit' in hk_data:
                        totals['HK']['unit'] = hk_data['unit']
            
            # Sum PRC values
            if 'PRC' in period_data and isinstance(period_data['PRC'], dict):
                prc_data = period_data['PRC']
                if 'value' in prc_data and prc_data['value'] is not None:
                    totals['PRC']['value'] += float(prc_data['value'])
                    # Capture unit from the first valid entry
                    if totals['PRC']['unit'] is None and 'unit' in prc_data:
                        totals['PRC']['unit'] = prc_data['unit']
        
        # Set or update total consumption
        if 'total_consumption' not in data:
            data['total_consumption'] = totals
        else:
            for key in ['HK', 'PRC']:
                if key not in data['total_consumption']:
                    data['total_consumption'][key] = totals[key]
                else:
                    data['total_consumption'][key]['value'] = totals[key]['value']
                    if 'unit' not in data['total_consumption'][key] and totals[key]['unit']:
                        data['total_consumption'][key]['unit'] = totals[key]['unit']
    
    return data 