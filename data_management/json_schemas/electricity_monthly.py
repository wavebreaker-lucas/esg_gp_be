"""
Schema for monthly electricity consumption metrics.
"""

ELECTRICITY_MONTHLY_SCHEMA = {
    "type": "electricity_monthly",
    "name": "Monthly Electricity Consumption",
    "description": "For tracking monthly electricity usage with unit information",
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
                            "unit": {"type": "string", "enum": ["kWh", "MWh", "GWh"]},
                            "comments": {"type": "string"}
                        }
                    },
                    "Feb-2024": {
                        "type": "object",
                        "properties": {
                            "value": {"type": "number"},
                            "unit": {"type": "string", "enum": ["kWh", "MWh", "GWh"]},
                            "comments": {"type": "string"}
                        }
                    },
                    "Mar-2024": {
                        "type": "object",
                        "properties": {
                            "value": {"type": "number"},
                            "unit": {"type": "string", "enum": ["kWh", "MWh", "GWh"]},
                            "comments": {"type": "string"}
                        }
                    },
                    "Apr-2024": {
                        "type": "object",
                        "properties": {
                            "value": {"type": "number"},
                            "unit": {"type": "string", "enum": ["kWh", "MWh", "GWh"]},
                            "comments": {"type": "string"}
                        }
                    },
                    "May-2024": {
                        "type": "object",
                        "properties": {
                            "value": {"type": "number"},
                            "unit": {"type": "string", "enum": ["kWh", "MWh", "GWh"]},
                            "comments": {"type": "string"}
                        }
                    },
                    "Jun-2024": {
                        "type": "object",
                        "properties": {
                            "value": {"type": "number"},
                            "unit": {"type": "string", "enum": ["kWh", "MWh", "GWh"]},
                            "comments": {"type": "string"}
                        }
                    },
                    "Jul-2024": {
                        "type": "object",
                        "properties": {
                            "value": {"type": "number"},
                            "unit": {"type": "string", "enum": ["kWh", "MWh", "GWh"]},
                            "comments": {"type": "string"}
                        }
                    },
                    "Aug-2024": {
                        "type": "object",
                        "properties": {
                            "value": {"type": "number"},
                            "unit": {"type": "string", "enum": ["kWh", "MWh", "GWh"]},
                            "comments": {"type": "string"}
                        }
                    },
                    "Sep-2024": {
                        "type": "object",
                        "properties": {
                            "value": {"type": "number"},
                            "unit": {"type": "string", "enum": ["kWh", "MWh", "GWh"]},
                            "comments": {"type": "string"}
                        }
                    },
                    "Oct-2024": {
                        "type": "object",
                        "properties": {
                            "value": {"type": "number"},
                            "unit": {"type": "string", "enum": ["kWh", "MWh", "GWh"]},
                            "comments": {"type": "string"}
                        }
                    },
                    "Nov-2024": {
                        "type": "object",
                        "properties": {
                            "value": {"type": "number"},
                            "unit": {"type": "string", "enum": ["kWh", "MWh", "GWh"]},
                            "comments": {"type": "string"}
                        }
                    },
                    "Dec-2024": {
                        "type": "object",
                        "properties": {
                            "value": {"type": "number"},
                            "unit": {"type": "string", "enum": ["kWh", "MWh", "GWh"]},
                            "comments": {"type": "string"}
                        }
                    }
                }
            },
            "_metadata": {
                "type": "object",
                "properties": {
                    "primary_measurement": {
                        "type": "object",
                        "properties": {
                            "path": {"type": "string", "default": "periods.Jan-2024.value"},
                            "unit": {"type": "string", "default": "kWh"}
                        }
                    },
                    "total_consumption": {"type": "number"}
                }
            }
        }
    },
    "primary_path_example": "periods.Jan-2024.value"
} 