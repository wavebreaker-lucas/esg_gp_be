"""
Schema for Hong Kong CLP electricity consumption tracking.
Used for KPI A1.2 and A2.1 reporting.
"""

ELECTRICITY_HK_CLP_SCHEMA = {
    "type": "electricity_hk_clp",
    "name": "Hong Kong CLP Electricity Consumption",
    "description": "For tracking CLP electricity consumption in Hong Kong",
    "data_structure_type": "periodic_measurement",
    "requires_calculation": True,
    "calculation_type": "sum",
    "calculated_fields": [
        {
            "path": "total_consumption", 
            "calculation": "sum(periods.*.value)",
            "description": "Total CLP electricity consumption",
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
                            "unit": {"type": "string", "enum": ["kWh"]}
                        }
                    },
                    "Feb-2025": {
                        "type": "object",
                        "properties": {
                            "value": {"type": "number"},
                            "unit": {"type": "string", "enum": ["kWh"]}
                        }
                    },
                    "Mar-2025": {
                        "type": "object",
                        "properties": {
                            "value": {"type": "number"},
                            "unit": {"type": "string", "enum": ["kWh"]}
                        }
                    },
                    "Apr-2025": {
                        "type": "object",
                        "properties": {
                            "value": {"type": "number"},
                            "unit": {"type": "string", "enum": ["kWh"]}
                        }
                    },
                    "May-2025": {
                        "type": "object",
                        "properties": {
                            "value": {"type": "number"},
                            "unit": {"type": "string", "enum": ["kWh"]}
                        }
                    },
                    "Jun-2025": {
                        "type": "object",
                        "properties": {
                            "value": {"type": "number"},
                            "unit": {"type": "string", "enum": ["kWh"]}
                        }
                    },
                    "Jul-2025": {
                        "type": "object",
                        "properties": {
                            "value": {"type": "number"},
                            "unit": {"type": "string", "enum": ["kWh"]}
                        }
                    },
                    "Aug-2025": {
                        "type": "object",
                        "properties": {
                            "value": {"type": "number"},
                            "unit": {"type": "string", "enum": ["kWh"]}
                        }
                    },
                    "Sep-2025": {
                        "type": "object",
                        "properties": {
                            "value": {"type": "number"},
                            "unit": {"type": "string", "enum": ["kWh"]}
                        }
                    },
                    "Oct-2025": {
                        "type": "object",
                        "properties": {
                            "value": {"type": "number"},
                            "unit": {"type": "string", "enum": ["kWh"]}
                        }
                    },
                    "Nov-2025": {
                        "type": "object",
                        "properties": {
                            "value": {"type": "number"},
                            "unit": {"type": "string", "enum": ["kWh"]}
                        }
                    },
                    "Dec-2025": {
                        "type": "object",
                        "properties": {
                            "value": {"type": "number"},
                            "unit": {"type": "string", "enum": ["kWh"]}
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
                    "unit": {"type": "string", "enum": ["kWh"]}
                }
            }
        }
    },
    "ui_hints": {
        "editable_fields": ["periods"],
        "read_only_fields": ["total_consumption"],
        "display_order": ["periods", "total_consumption"]
    }
} 