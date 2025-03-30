"""
Schema for a simple metric with a single value and unit.
"""

SINGLE_VALUE_SCHEMA = {
    "type": "single_value",
    "name": "Simple Value with Unit",
    "description": "For basic metrics with a single value and unit",
    "template": {
        "type": "object",
        "properties": {
            "value": {"type": "number"},
            "unit": {"type": "string", "enum": ["count", "percentage", "tonnes", "kWh"]},
            "comments": {"type": "string"}
        },
        "required": ["value", "unit"]
    },
    "primary_path_example": "value"
} 