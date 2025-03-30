"""
Package for JSON schemas used in the ESG platform.
"""

import os
import importlib
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# Dictionary to hold all schema templates
SCHEMA_TEMPLATES = {}

def load_schemas():
    """
    Dynamically import all schema modules and register templates.
    """
    global SCHEMA_TEMPLATES
    
    # Get the directory of this file
    current_dir = Path(__file__).parent
    
    # Iterate through all Python files in the directory
    for file_path in current_dir.glob('*.py'):
        file_name = file_path.name
        
        # Skip __init__.py and any non-Python files
        if file_name == '__init__.py' or not file_name.endswith('.py'):
            continue
        
        # Import the module
        module_name = file_name[:-3]  # Remove .py extension
        try:
            module = importlib.import_module(f'.{module_name}', package='data_management.json_schemas')
            
            # Look for schema definitions in the module
            for attr_name in dir(module):
                # Only consider uppercase attributes that contain 'SCHEMA'
                if attr_name.isupper() and 'SCHEMA' in attr_name:
                    schema = getattr(module, attr_name)
                    
                    # Register the schema if it's a dictionary with a name
                    if isinstance(schema, dict) and 'title' in schema:
                        schema_name = schema.get('name', attr_name.lower())
                        SCHEMA_TEMPLATES[schema_name] = schema
                        
                        # Alternative registration using the title for better compatibility
                        title = schema.get('title')
                        if title and isinstance(title, str):
                            normalized_title = title.lower().replace(' ', '_')
                            if normalized_title != schema_name:
                                SCHEMA_TEMPLATES[normalized_title] = schema
                        
                        logger.debug(f"Registered schema: {schema_name}")
        except Exception as e:
            logger.error(f"Error importing schema module {module_name}: {e}")

# Load schemas when this module is imported
load_schemas()

# For convenient imports
__all__ = ['SCHEMA_TEMPLATES'] 