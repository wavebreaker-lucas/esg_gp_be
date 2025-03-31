"""
Schema for Hong Kong fresh water consumption.
Used for KPI A2.2 reporting.
"""

FRESH_WATER_HK_SCHEMA = {
    "type": "fresh_water_hk",
    "name": "Hong Kong Fresh Water Consumption",
    "description": "For tracking fresh water consumption in Hong Kong",
    "data_structure_type": "periodic_measurement",
    "requires_calculation": True,
    "calculation_type": "sum_by_period",
    "schema_version": "2.0",
    
    "calculated_fields": [
        {
            "path": "total_consumption.value", 
            "calculation": "sum(periods[*].value)",
            "description": "Total Hong Kong fresh water consumption",
            "dependency_paths": ["periods[*].value"],
            "calculation_type": "sum",
            "format": {
                "precision": 2,
                "min_value": 0
            }
        }
    ],
    
    "template": {
        "type": "object",
        "properties": {
            "periods": {
                "type": "array",
                "description": "Monthly fresh water consumption values",
                "default": [
                    {"month": "Jan-2025", "value": None, "unit": "m³"},
                    {"month": "Feb-2025", "value": None, "unit": "m³"},
                    {"month": "Mar-2025", "value": None, "unit": "m³"},
                    {"month": "Apr-2025", "value": None, "unit": "m³"},
                    {"month": "May-2025", "value": None, "unit": "m³"},
                    {"month": "Jun-2025", "value": None, "unit": "m³"},
                    {"month": "Jul-2025", "value": None, "unit": "m³"},
                    {"month": "Aug-2025", "value": None, "unit": "m³"},
                    {"month": "Sep-2025", "value": None, "unit": "m³"},
                    {"month": "Oct-2025", "value": None, "unit": "m³"},
                    {"month": "Nov-2025", "value": None, "unit": "m³"},
                    {"month": "Dec-2025", "value": None, "unit": "m³"}
                ],
                "items": {
                    "type": "object",
                    "properties": {
                        "month": {
                            "type": "string",
                            "enum": [
                                "Jan-2025", "Feb-2025", "Mar-2025", "Apr-2025",
                                "May-2025", "Jun-2025", "Jul-2025", "Aug-2025",
                                "Sep-2025", "Oct-2025", "Nov-2025", "Dec-2025"
                            ],
                            "description": "Reporting month and year"
                        },
                        "value": {
                            "type": "number", 
                            "nullable": True,
                            "minimum": 0,
                            "description": "Fresh water consumption value"
                        },
                        "unit": {
                            "type": "string", 
                            "enum": ["m³"],
                            "default": "m³",
                            "description": "Unit of measurement"
                        }
                    },
                    "required": ["month", "value", "unit"]
                }
            },
            "total_consumption": {
                "type": "object",
                "is_calculated": True,
                "x-calculated": True,
                "description": "Calculated total consumption for all months",
                "properties": {
                    "value": {
                        "type": "number",
                        "readOnly": True,
                        "description": "Total fresh water consumption"
                    },
                    "unit": {
                        "type": "string", 
                        "enum": ["m³"],
                        "default": "m³",
                        "readOnly": True,
                        "description": "Unit of measurement"
                    }
                }
            },
            "kpi_reference": {
                "type": "string",
                "default": "KPI A2.2",
                "description": "Reference to relevant KPI identifier"
            },
            "water_type": {
                "type": "string",
                "enum": ["Fresh Water"],
                "default": "Fresh Water",
                "description": "Type of water being reported"
            },
            "region": {
                "type": "string",
                "enum": ["Hong Kong"],
                "default": "Hong Kong",
                "description": "Reporting region",
                "readOnly": True
            }
        }
    },
    
    "ui_hints": {
        "form_component": "periodic-measurement-grid",
        "editable_fields": ["periods", "kpi_reference", "water_type"],
        "read_only_fields": ["total_consumption", "region"],
        "display_order": ["periods", "total_consumption", "region", "water_type", "kpi_reference"],
        "summary_fields": ["total_consumption.value"],
        "periods_display": {
            "display_type": "grid",
            "month_order": [
                "Jan-2025", "Feb-2025", "Mar-2025", "Apr-2025",
                "May-2025", "Jun-2025", "Jul-2025", "Aug-2025",
                "Sep-2025", "Oct-2025", "Nov-2025", "Dec-2025"
            ],
            "empty_value_display": "Not reported"
        },
        "formatters": {
            "value": {
                "type": "number",
                "decimal_places": 2,
                "show_thousands_separator": True
            }
        }
    }
} 