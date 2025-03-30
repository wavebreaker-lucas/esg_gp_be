"""
Package for JSON schema definitions used across the ESG platform.
Each schema defines a structured format for specific ESG metrics.
"""

from data_management.json_schemas.electricity_hk import ELECTRICITY_HK_SCHEMA
from data_management.json_schemas.electricity_prc import ELECTRICITY_PRC_SCHEMA
from data_management.json_schemas.fresh_water import FRESH_WATER_SCHEMA
from data_management.json_schemas.wastewater import WASTEWATER_SCHEMA

# Dictionary of all available schema templates
SCHEMA_TEMPLATES = {
    "electricity_hk": ELECTRICITY_HK_SCHEMA,
    "electricity_prc": ELECTRICITY_PRC_SCHEMA,
    "fresh_water": FRESH_WATER_SCHEMA,
    "wastewater": WASTEWATER_SCHEMA,
}

__all__ = [
    "ELECTRICITY_HK_SCHEMA",
    "ELECTRICITY_PRC_SCHEMA", 
    "FRESH_WATER_SCHEMA",
    "WASTEWATER_SCHEMA",
    "SCHEMA_TEMPLATES",
] 