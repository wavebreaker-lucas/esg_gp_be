"""
JSON schemas for ESG metrics.

This package contains individual JSON schema definitions for different metric types.
Each schema file contains one schema definition, and this __init__.py file
imports and exposes all of them for easy access.
"""

from .single_value import SINGLE_VALUE_SCHEMA
from .emissions import EMISSIONS_SCHEMA
from .electricity_monthly import ELECTRICITY_MONTHLY_SCHEMA
from .electricity_provider import ELECTRICITY_PROVIDER_SCHEMA
from .water_consumption import WATER_CONSUMPTION_SCHEMA
from .utility_bundle import UTILITY_BUNDLE_SCHEMA
from .supplier_assessment import SUPPLIER_ASSESSMENT_SCHEMA
from .legal_cases import LEGAL_CASES_SCHEMA

# Collection of all schema templates for easy access
SCHEMA_TEMPLATES = [
    SINGLE_VALUE_SCHEMA,
    EMISSIONS_SCHEMA,
    ELECTRICITY_MONTHLY_SCHEMA,
    ELECTRICITY_PROVIDER_SCHEMA,
    WATER_CONSUMPTION_SCHEMA, 
    UTILITY_BUNDLE_SCHEMA,
    SUPPLIER_ASSESSMENT_SCHEMA,
    LEGAL_CASES_SCHEMA
]

__all__ = [
    'SINGLE_VALUE_SCHEMA',
    'EMISSIONS_SCHEMA',
    'ELECTRICITY_MONTHLY_SCHEMA',
    'ELECTRICITY_PROVIDER_SCHEMA',
    'WATER_CONSUMPTION_SCHEMA',
    'UTILITY_BUNDLE_SCHEMA',
    'SUPPLIER_ASSESSMENT_SCHEMA',
    'LEGAL_CASES_SCHEMA',
    'SCHEMA_TEMPLATES'
] 