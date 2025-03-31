"""
Schema for PRC electricity consumption tracking.
Used for KPI A1.2 and A2.1 reporting.
"""

ELECTRICITY_PRC_SCHEMA = {
    "type": "electricity_prc",
    "name": "PRC Electricity Consumption",
    "description": "For tracking electricity consumption in the PRC",
    "data_structure_type": "periodic_measurement",
    "requires_calculation": True,
    "calculation_type": "sum_by_period",
    "schema_version": "2.0",
    
    "calculated_fields": [
        {
            "path": "total_consumption.value", 
            "calculation": "sum(periods[*].value)",
            "description": "Total PRC electricity consumption",
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
                "description": "Monthly electricity consumption values",
                "default": [
                    {"month": "Jan-2025", "value": None, "unit": "kWh"},
                    {"month": "Feb-2025", "value": None, "unit": "kWh"},
                    {"month": "Mar-2025", "value": None, "unit": "kWh"},
                    {"month": "Apr-2025", "value": None, "unit": "kWh"},
                    {"month": "May-2025", "value": None, "unit": "kWh"},
                    {"month": "Jun-2025", "value": None, "unit": "kWh"},
                    {"month": "Jul-2025", "value": None, "unit": "kWh"},
                    {"month": "Aug-2025", "value": None, "unit": "kWh"},
                    {"month": "Sep-2025", "value": None, "unit": "kWh"},
                    {"month": "Oct-2025", "value": None, "unit": "kWh"},
                    {"month": "Nov-2025", "value": None, "unit": "kWh"},
                    {"month": "Dec-2025", "value": None, "unit": "kWh"}
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
                            "description": "Electricity consumption value"
                        },
                        "unit": {
                            "type": "string", 
                            "enum": ["kWh"],
                            "default": "kWh",
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
                        "description": "Total electricity consumption"
                    },
                    "unit": {
                        "type": "string", 
                        "enum": ["kWh"],
                        "default": "kWh",
                        "readOnly": True,
                        "description": "Unit of measurement"
                    }
                }
            },
            "kpi_reference": {
                "type": "string",
                "default": "KPI A1.2, A2.1",
                "description": "Reference to relevant KPI identifier"
            },
            "region": {
                "type": "string",
                "enum": ["PRC"],
                "default": "PRC",
                "description": "Reporting region",
                "readOnly": True
            }
        }
    },
    
    "ui_hints": {
        "form_component": "periodic-measurement-grid",
        "editable_fields": ["periods", "kpi_reference"],
        "read_only_fields": ["total_consumption", "region"],
        "display_order": ["periods", "total_consumption", "region", "kpi_reference"],
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