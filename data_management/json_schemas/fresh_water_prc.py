"""
Schema for PRC fresh water consumption.
Used for KPI A2.2 reporting.
"""

FRESH_WATER_PRC_SCHEMA = {
    "type": "fresh_water_prc",
    "name": "PRC Fresh Water Consumption",
    "description": "For tracking fresh water consumption in the PRC",
    "schema_type": "periodic_measurement",
    "requires_calculation": True,
    "calculation_type": "sum_by_period",
    "calculated_fields": [
        {
            "path": "total_consumption", 
            "calculation": "sum(periods.*.value)",
            "description": "Total PRC fresh water consumption",
            "dependency_paths": ["periods.*"]
        }
    ],
    "template": {
        "type": "object",
        "properties": {
            "periods": {
                "type": "object",
                "properties": {
                    "Jan-2025": {
                        "type": "object",
                        "properties": {
                            "value": {"type": "number"},
                            "unit": {"type": "string", "enum": ["m³"]}
                        }
                    },
                    "Feb-2025": {
                        "type": "object",
                        "properties": {
                            "value": {"type": "number"},
                            "unit": {"type": "string", "enum": ["m³"]}
                        }
                    },
                    "Mar-2025": {
                        "type": "object",
                        "properties": {
                            "value": {"type": "number"},
                            "unit": {"type": "string", "enum": ["m³"]}
                        }
                    },
                    "Apr-2025": {
                        "type": "object",
                        "properties": {
                            "value": {"type": "number"},
                            "unit": {"type": "string", "enum": ["m³"]}
                        }
                    },
                    "May-2025": {
                        "type": "object",
                        "properties": {
                            "value": {"type": "number"},
                            "unit": {"type": "string", "enum": ["m³"]}
                        }
                    },
                    "Jun-2025": {
                        "type": "object",
                        "properties": {
                            "value": {"type": "number"},
                            "unit": {"type": "string", "enum": ["m³"]}
                        }
                    },
                    "Jul-2025": {
                        "type": "object",
                        "properties": {
                            "value": {"type": "number"},
                            "unit": {"type": "string", "enum": ["m³"]}
                        }
                    },
                    "Aug-2025": {
                        "type": "object",
                        "properties": {
                            "value": {"type": "number"},
                            "unit": {"type": "string", "enum": ["m³"]}
                        }
                    },
                    "Sep-2025": {
                        "type": "object",
                        "properties": {
                            "value": {"type": "number"},
                            "unit": {"type": "string", "enum": ["m³"]}
                        }
                    },
                    "Oct-2025": {
                        "type": "object",
                        "properties": {
                            "value": {"type": "number"},
                            "unit": {"type": "string", "enum": ["m³"]}
                        }
                    },
                    "Nov-2025": {
                        "type": "object",
                        "properties": {
                            "value": {"type": "number"},
                            "unit": {"type": "string", "enum": ["m³"]}
                        }
                    },
                    "Dec-2025": {
                        "type": "object",
                        "properties": {
                            "value": {"type": "number"},
                            "unit": {"type": "string", "enum": ["m³"]}
                        }
                    }
                }
            },
            "total_consumption": {
                "type": "object",
                "is_calculated": True,
                "x-calculated": True,
                "properties": {
                    "value": {"type": "number"},
                    "unit": {"type": "string", "enum": ["m³"]}
                }
            },
            "kpi_reference": {
                "type": "string",
                "default": "KPI A2.2"
            },
            "water_type": {
                "type": "string",
                "enum": ["Fresh Water"],
                "default": "Fresh Water"
            },
            "region": {
                "type": "string",
                "enum": ["PRC"],
                "default": "PRC"
            }
        }
    },
    "ui_hints": {
        "editable_fields": ["periods", "kpi_reference", "water_type"],
        "read_only_fields": ["total_consumption", "region"],
        "display_order": ["periods", "total_consumption", "region", "water_type", "kpi_reference"]
    }
} 