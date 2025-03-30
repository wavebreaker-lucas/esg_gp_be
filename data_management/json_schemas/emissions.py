"""
Schema for emissions metrics with scope information.
"""

EMISSIONS_SCHEMA = {
    "type": "emissions",
    "name": "Emissions Metric",
    "description": "For tracking GHG emissions with scope information",
    "template": {
        "type": "object",
        "properties": {
            "value": {"type": "number"},
            "unit": {"type": "string", "enum": ["tCO2e", "kgCO2e"]},
            "scope": {"type": "string", "enum": ["Scope 1", "Scope 2", "Scope 3"]},
            "source": {"type": "string"},
            "calculation_method": {"type": "string", "enum": ["location-based", "market-based"]},
            "periods": {
                "type": "object",
                "additionalProperties": {
                    "type": "object",
                    "properties": {
                        "value": {"type": "number"},
                        "unit": {"type": "string", "enum": ["tCO2e", "kgCO2e"]},
                        "notes": {"type": "string"}
                    }
                }
            },
            "_metadata": {
                "type": "object",
                "properties": {
                    "primary_measurement": {
                        "type": "object",
                        "properties": {
                            "path": {"type": "string", "default": "value"},
                            "unit": {"type": "string", "default": "tCO2e"}
                        }
                    }
                }
            }
        },
        "required": ["value", "unit", "scope"]
    },
    "primary_path_example": "value"
} 