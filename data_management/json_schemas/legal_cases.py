"""
Schema for register of concluded legal cases (KPI B7.1).
"""

LEGAL_CASES_SCHEMA = {
    "type": "legal_cases_register",
    "name": "Register of Concluded Legal Cases",
    "description": "For tracking legal cases regarding corrupt practices (KPI B7.1)",
    "template": {
        "type": "object",
        "properties": {
            "cases": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "case_number": {"type": "string"},
                        "case_name": {"type": "string"},
                        "date_opened": {"type": "string", "format": "date"},
                        "date_concluded": {"type": "string", "format": "date"},
                        "nature": {"type": "string"},
                        "outcome": {"type": "string"},
                        "financial_impact": {
                            "type": "object",
                            "properties": {
                                "value": {"type": "number"},
                                "unit": {"type": "string", "enum": ["HKD", "USD", "RMB"]}
                            }
                        },
                        "region": {"type": "string", "enum": ["Hong Kong", "PRC", "Other"]}
                    }
                }
            },
            "reporting_period": {"type": "string"},
            "total_cases": {"type": "integer"},
            "_metadata": {
                "type": "object",
                "properties": {
                    "primary_measurement": {
                        "type": "object",
                        "properties": {
                            "path": {"type": "string", "default": "total_cases"},
                            "unit": {"type": "string", "default": "count"}
                        }
                    }
                }
            }
        }
    },
    "primary_path_example": "total_cases"
} 