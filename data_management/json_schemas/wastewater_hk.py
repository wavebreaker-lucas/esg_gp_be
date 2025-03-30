"""
Schema for Hong Kong wastewater consumption.
Used for KPI A2.2 reporting.
"""

WASTEWATER_HK_SCHEMA = {
    "type": "wastewater_hk",
    "name": "Hong Kong Wastewater Consumption",
    "description": "For tracking wastewater consumption in Hong Kong",
    "calculated_fields": [
        {
            "path": "total_consumption", 
            "calculation": "sum(periods.*.value)",
            "description": "Total Hong Kong wastewater consumption"
        }
    ],
    "template": {
        "type": "object",
        "properties": {
            "periods": {
                "type": "object",
                "properties": {
                    "Jan-2024": {
                        "type": "object",
                        "properties": {
                            "value": {"type": "number"},
                            "unit": {"type": "string", "enum": ["m³", "liters"]}
                        }
                    },
                    "Feb-2024": {
                        "type": "object",
                        "properties": {
                            "value": {"type": "number"},
                            "unit": {"type": "string", "enum": ["m³", "liters"]}
                        }
                    },
                    "Mar-2024": {
                        "type": "object",
                        "properties": {
                            "value": {"type": "number"},
                            "unit": {"type": "string", "enum": ["m³", "liters"]}
                        }
                    },
                    "Apr-2024": {
                        "type": "object",
                        "properties": {
                            "value": {"type": "number"},
                            "unit": {"type": "string", "enum": ["m³", "liters"]}
                        }
                    },
                    "May-2024": {
                        "type": "object",
                        "properties": {
                            "value": {"type": "number"},
                            "unit": {"type": "string", "enum": ["m³", "liters"]}
                        }
                    },
                    "Jun-2024": {
                        "type": "object",
                        "properties": {
                            "value": {"type": "number"},
                            "unit": {"type": "string", "enum": ["m³", "liters"]}
                        }
                    },
                    "Jul-2024": {
                        "type": "object",
                        "properties": {
                            "value": {"type": "number"},
                            "unit": {"type": "string", "enum": ["m³", "liters"]}
                        }
                    },
                    "Aug-2024": {
                        "type": "object",
                        "properties": {
                            "value": {"type": "number"},
                            "unit": {"type": "string", "enum": ["m³", "liters"]}
                        }
                    },
                    "Sep-2024": {
                        "type": "object",
                        "properties": {
                            "value": {"type": "number"},
                            "unit": {"type": "string", "enum": ["m³", "liters"]}
                        }
                    },
                    "Oct-2024": {
                        "type": "object",
                        "properties": {
                            "value": {"type": "number"},
                            "unit": {"type": "string", "enum": ["m³", "liters"]}
                        }
                    },
                    "Nov-2024": {
                        "type": "object",
                        "properties": {
                            "value": {"type": "number"},
                            "unit": {"type": "string", "enum": ["m³", "liters"]}
                        }
                    },
                    "Dec-2024": {
                        "type": "object",
                        "properties": {
                            "value": {"type": "number"},
                            "unit": {"type": "string", "enum": ["m³", "liters"]}
                        }
                    }
                }
            },
            "total_consumption": {
                "type": "object",
                "x-calculated": True,
                "properties": {
                    "value": {"type": "number"},
                    "unit": {"type": "string", "enum": ["m³", "liters"]}
                }
            },
            "kpi_reference": {
                "type": "string",
                "default": "KPI A2.2"
            },
            "water_type": {
                "type": "string",
                "enum": ["Wastewater"],
                "default": "Wastewater"
            },
            "region": {
                "type": "string",
                "enum": ["Hong Kong"],
                "default": "Hong Kong"
            }
        }
    },
    "ui_hints": {
        "editable_fields": ["periods", "kpi_reference", "water_type"],
        "read_only_fields": ["total_consumption", "region"]
    }
} 