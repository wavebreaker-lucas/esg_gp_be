"""
Schema for PRC electricity consumption tracking.
Used for KPI A1.2 and A2.1 reporting.
"""

ELECTRICITY_PRC_SCHEMA = {
    "type": "electricity_prc",
    "name": "PRC Electricity Consumption",
    "description": "For tracking electricity consumption in the PRC",
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
                            "unit": {"type": "string", "enum": ["kWh", "MWh"]}
                        }
                    },
                    "Feb-2024": {
                        "type": "object",
                        "properties": {
                            "value": {"type": "number"},
                            "unit": {"type": "string", "enum": ["kWh", "MWh"]}
                        }
                    },
                    "Mar-2024": {
                        "type": "object",
                        "properties": {
                            "value": {"type": "number"},
                            "unit": {"type": "string", "enum": ["kWh", "MWh"]}
                        }
                    },
                    "Apr-2024": {
                        "type": "object",
                        "properties": {
                            "value": {"type": "number"},
                            "unit": {"type": "string", "enum": ["kWh", "MWh"]}
                        }
                    },
                    "May-2024": {
                        "type": "object",
                        "properties": {
                            "value": {"type": "number"},
                            "unit": {"type": "string", "enum": ["kWh", "MWh"]}
                        }
                    },
                    "Jun-2024": {
                        "type": "object",
                        "properties": {
                            "value": {"type": "number"},
                            "unit": {"type": "string", "enum": ["kWh", "MWh"]}
                        }
                    },
                    "Jul-2024": {
                        "type": "object",
                        "properties": {
                            "value": {"type": "number"},
                            "unit": {"type": "string", "enum": ["kWh", "MWh"]}
                        }
                    },
                    "Aug-2024": {
                        "type": "object",
                        "properties": {
                            "value": {"type": "number"},
                            "unit": {"type": "string", "enum": ["kWh", "MWh"]}
                        }
                    },
                    "Sep-2024": {
                        "type": "object",
                        "properties": {
                            "value": {"type": "number"},
                            "unit": {"type": "string", "enum": ["kWh", "MWh"]}
                        }
                    },
                    "Oct-2024": {
                        "type": "object",
                        "properties": {
                            "value": {"type": "number"},
                            "unit": {"type": "string", "enum": ["kWh", "MWh"]}
                        }
                    },
                    "Nov-2024": {
                        "type": "object",
                        "properties": {
                            "value": {"type": "number"},
                            "unit": {"type": "string", "enum": ["kWh", "MWh"]}
                        }
                    },
                    "Dec-2024": {
                        "type": "object",
                        "properties": {
                            "value": {"type": "number"},
                            "unit": {"type": "string", "enum": ["kWh", "MWh"]}
                        }
                    }
                }
            },
            "total_consumption": {
                "type": "object",
                "properties": {
                    "value": {"type": "number"},
                    "unit": {"type": "string", "enum": ["kWh", "MWh"]}
                }
            },
            "kpi_reference": {
                "type": "string",
                "default": "KPI A1.2, A2.1"
            }
        }
    }
} 