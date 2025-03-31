"""
Schema for PRC work injuries and safety metrics.
Used for KPI B2.1 reporting.
"""

WORK_INJURIES_PRC_SCHEMA = {
    "type": "work_injuries_prc",
    "name": "PRC Work Injuries",
    "description": "For tracking work-related injuries and fatalities in the PRC",
    "data_structure_type": "non_periodic_measurement",
    "requires_calculation": False,
    "calculation_type": "none",
    "schema_version": "2.0",
    
    "template": {
        "type": "object",
        "properties": {
            "fiscal_year": {
                "type": "string",
                "default": "FY 2025",
                "description": "Fiscal year for the reporting period"
            },
            "deaths": {
                "type": "object",
                "title": "No. of deaths due to work injury",
                "description": "Number of work-related fatalities",
                "properties": {
                    "value": {
                        "type": "integer", 
                        "minimum": 0,
                        "description": "Number of fatalities"
                    },
                    "unit": {
                        "type": "string", 
                        "enum": ["Person"], 
                        "default": "Person",
                        "description": "Unit of measurement"
                    }
                }
            },
            "injuries": {
                "type": "object",
                "title": "Number of reported injuries",
                "description": "Total number of work-related injuries",
                "properties": {
                    "value": {
                        "type": "integer", 
                        "minimum": 0,
                        "description": "Number of injuries"
                    },
                    "unit": {
                        "type": "string", 
                        "enum": ["Person"], 
                        "default": "Person",
                        "description": "Unit of measurement"
                    }
                }
            },
            "lost_days": {
                "type": "object",
                "title": "No. of lost days due to work injury",
                "description": "Total number of work days lost due to injuries",
                "properties": {
                    "value": {
                        "type": "integer", 
                        "minimum": 0,
                        "description": "Number of lost days"
                    },
                    "unit": {
                        "type": "string", 
                        "enum": ["Days"], 
                        "default": "Days",
                        "description": "Unit of measurement"
                    }
                }
            },
            "region": {
                "type": "string",
                "enum": ["PRC"],
                "default": "PRC",
                "description": "Reporting region",
                "readOnly": True
            },
            "kpi_reference": {
                "type": "string",
                "default": "KPI B2.1",
                "description": "Reference to relevant KPI identifier"
            }
        }
    },
    
    "ui_hints": {
        "form_component": "work-injuries-form",
        "editable_fields": ["fiscal_year", "deaths", "injuries", "lost_days", "kpi_reference"],
        "read_only_fields": ["region"],
        "display_order": ["fiscal_year", "deaths", "injuries", "lost_days", "region", "kpi_reference"],
        "formatters": {
            "value": {
                "type": "integer",
                "show_thousands_separator": True
            }
        }
    }
} 