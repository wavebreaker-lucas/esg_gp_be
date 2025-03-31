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
    "template": {
        "type": "object",
        "properties": {
            "fiscal_year": {
                "type": "string",
                "default": "FY 2025"
            },
            "deaths": {
                "type": "object",
                "title": "No. of deaths due to work injury",
                "properties": {
                    "value": {"type": "integer", "minimum": 0},
                    "unit": {"type": "string", "enum": ["Person"], "default": "Person"}
                }
            },
            "injuries": {
                "type": "object",
                "title": "Number of reported injuries",
                "properties": {
                    "value": {"type": "integer", "minimum": 0},
                    "unit": {"type": "string", "enum": ["Person"], "default": "Person"}
                }
            },
            "lost_days": {
                "type": "object",
                "title": "No. of lost days due to work injury",
                "properties": {
                    "value": {"type": "integer", "minimum": 0},
                    "unit": {"type": "string", "enum": ["Days"], "default": "Days"}
                }
            },
            "region": {
                "type": "string",
                "enum": ["PRC"],
                "default": "PRC"
            },
            "kpi_reference": {
                "type": "string",
                "default": "KPI B2.1"
            }
        }
    },
    "ui_hints": {
        "editable_fields": ["fiscal_year", "deaths", "injuries", "lost_days", "kpi_reference"],
        "read_only_fields": ["region"],
        "display_order": ["fiscal_year", "deaths", "injuries", "lost_days", "region", "kpi_reference"]
    }
} 