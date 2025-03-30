"""
Schema for multiple utility consumption in one metric.
"""

UTILITY_BUNDLE_SCHEMA = {
    "type": "utility_bundle",
    "name": "Multiple Utility Consumption",
    "description": "For tracking multiple utility consumptions together",
    "template": {
        "type": "object",
        "properties": {
            "electricity": {
                "type": "object",
                "properties": {
                    "value": {"type": "number"},
                    "unit": {"type": "string", "enum": ["kWh", "MWh"]}
                }
            },
            "water": {
                "type": "object",
                "properties": {
                    "value": {"type": "number"},
                    "unit": {"type": "string", "enum": ["m³", "liters"]}
                }
            },
            "gas": {
                "type": "object",
                "properties": {
                    "value": {"type": "number"},
                    "unit": {"type": "string", "enum": ["m³", "BTU"]}
                }
            },
            "comments": {"type": "string"},
            "_metadata": {
                "type": "object",
                "properties": {
                    "primary_measurement": {
                        "type": "object",
                        "properties": {
                            "path": {"type": "string", "default": "electricity.value"},
                            "unit": {"type": "string", "default": "kWh"}
                        }
                    }
                }
            }
        }
    },
    "primary_path_example": "electricity.value"
} 