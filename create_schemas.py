#!/usr/bin/env python
import os
import sys
import importlib.util
import json

# Configure Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'esg_platform.settings')
import django
django.setup()

from django.contrib.auth import get_user_model
from data_management.models import MetricSchemaRegistry

# Get the Baker Tilly admin account to attribute schema creation
User = get_user_model()
try:
    admin_user = User.objects.filter(is_baker_tilly_admin=True).first()
    if not admin_user:
        # Fallback to superuser if no Baker Tilly admin exists
        admin_user = User.objects.filter(is_superuser=True).first()
        
    if not admin_user:
        print("No Baker Tilly admin or superuser found. Please create an admin user first.")
        sys.exit(1)
    
    print(f"Using admin user: {admin_user.email}")
except Exception as e:
    print(f"Error accessing users: {e}")
    sys.exit(1)

# Directory containing schema definitions
SCHEMAS_DIR = "data_management/json_schemas"

# Get all Python files in the schemas directory (excluding __init__.py)
schema_files = [f for f in os.listdir(SCHEMAS_DIR) 
                if f.endswith('.py') and f != '__init__.py']

print(f"Found {len(schema_files)} schema files")

# Track statistics
created_count = 0
updated_count = 0
skipped_count = 0
error_count = 0

# Process each schema file
for schema_file in schema_files:
    try:
        print(f"Processing {schema_file}...")
        file_path = os.path.join(SCHEMAS_DIR, schema_file)
        
        # Import the module dynamically
        module_name = schema_file.replace('.py', '')
        spec = importlib.util.spec_from_file_location(module_name, file_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        # Look for schema dictionary in the module
        schema_name = None
        schema_dict = None
        
        # Find the first uppercase schema variable
        for var_name in dir(module):
            if var_name.isupper() and '_SCHEMA' in var_name:
                schema_name = var_name.replace('_SCHEMA', '').title()
                schema_dict = getattr(module, var_name)
                break
        
        if not schema_dict:
            print(f"  No schema found in {schema_file}, skipping")
            skipped_count += 1
            continue
        
        # Get schema name from the dictionary if available
        if isinstance(schema_dict, dict) and 'name' in schema_dict:
            schema_name = schema_dict['name']
        
        # Register the schema if it doesn't exist
        registry_entry, created = MetricSchemaRegistry.objects.update_or_create(
            name=schema_name,
            defaults={
                'schema': schema_dict,
                'created_by': admin_user,
                'description': schema_dict.get('description', ''),
                'is_active': True
            }
        )
        
        if created:
            print(f"  Created schema: {schema_name}")
            created_count += 1
        else:
            print(f"  Updated schema: {schema_name}")
            updated_count += 1
            
    except Exception as e:
        print(f"  Error processing {schema_file}: {e}")
        error_count += 1

# Print summary
print("\nSchema Registration Summary:")
print(f"Created: {created_count}")
print(f"Updated: {updated_count}")
print(f"Skipped: {skipped_count}")
print(f"Errors: {error_count}")
print(f"Total processed: {len(schema_files)}") 