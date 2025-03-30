"""
Schema for wastewater consumption across Hong Kong and the PRC.
Used for KPI A2.2 reporting.
"""

WASTEWATER_SCHEMA = {
    "type": "wastewater",
    "name": "Wastewater Consumption by Region",
    "description": "For tracking wastewater consumption across Hong Kong and the PRC",
    "calculated_fields": [
        {
            "path": "total_consumption.HK", 
            "calculation": "sum(periods.*.HK.value)",
            "description": "Total Hong Kong wastewater consumption"
        },
        {
            "path": "total_consumption.PRC", 
            "calculation": "sum(periods.*.PRC.value)",
            "description": "Total PRC wastewater consumption"
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
                            "HK": {
                                "type": "object",
                                "properties": {
                                    "value": {"type": "number"},
                                    "unit": {"type": "string", "enum": ["m³", "liters"]}
                                }
                            },
                            "PRC": {
                                "type": "object",
                                "properties": {
                                    "value": {"type": "number"},
                                    "unit": {"type": "string", "enum": ["m³", "liters"]}
                                }
                            }
                        }
                    },
                    "Feb-2024": {
                        "type": "object",
                        "properties": {
                            "HK": {
                                "type": "object",
                                "properties": {
                                    "value": {"type": "number"},
                                    "unit": {"type": "string", "enum": ["m³", "liters"]}
                                }
                            },
                            "PRC": {
                                "type": "object",
                                "properties": {
                                    "value": {"type": "number"},
                                    "unit": {"type": "string", "enum": ["m³", "liters"]}
                                }
                            }
                        }
                    },
                    "Mar-2024": {
                        "type": "object",
                        "properties": {
                            "HK": {
                                "type": "object",
                                "properties": {
                                    "value": {"type": "number"},
                                    "unit": {"type": "string", "enum": ["m³", "liters"]}
                                }
                            },
                            "PRC": {
                                "type": "object",
                                "properties": {
                                    "value": {"type": "number"},
                                    "unit": {"type": "string", "enum": ["m³", "liters"]}
                                }
                            }
                        }
                    },
                    "Apr-2024": {
                        "type": "object",
                        "properties": {
                            "HK": {
                                "type": "object",
                                "properties": {
                                    "value": {"type": "number"},
                                    "unit": {"type": "string", "enum": ["m³", "liters"]}
                                }
                            },
                            "PRC": {
                                "type": "object",
                                "properties": {
                                    "value": {"type": "number"},
                                    "unit": {"type": "string", "enum": ["m³", "liters"]}
                                }
                            }
                        }
                    },
                    "May-2024": {
                        "type": "object",
                        "properties": {
                            "HK": {
                                "type": "object",
                                "properties": {
                                    "value": {"type": "number"},
                                    "unit": {"type": "string", "enum": ["m³", "liters"]}
                                }
                            },
                            "PRC": {
                                "type": "object",
                                "properties": {
                                    "value": {"type": "number"},
                                    "unit": {"type": "string", "enum": ["m³", "liters"]}
                                }
                            }
                        }
                    },
                    "Jun-2024": {
                        "type": "object",
                        "properties": {
                            "HK": {
                                "type": "object",
                                "properties": {
                                    "value": {"type": "number"},
                                    "unit": {"type": "string", "enum": ["m³", "liters"]}
                                }
                            },
                            "PRC": {
                                "type": "object",
                                "properties": {
                                    "value": {"type": "number"},
                                    "unit": {"type": "string", "enum": ["m³", "liters"]}
                                }
                            }
                        }
                    },
                    "Jul-2024": {
                        "type": "object",
                        "properties": {
                            "HK": {
                                "type": "object",
                                "properties": {
                                    "value": {"type": "number"},
                                    "unit": {"type": "string", "enum": ["m³", "liters"]}
                                }
                            },
                            "PRC": {
                                "type": "object",
                                "properties": {
                                    "value": {"type": "number"},
                                    "unit": {"type": "string", "enum": ["m³", "liters"]}
                                }
                            }
                        }
                    },
                    "Aug-2024": {
                        "type": "object",
                        "properties": {
                            "HK": {
                                "type": "object",
                                "properties": {
                                    "value": {"type": "number"},
                                    "unit": {"type": "string", "enum": ["m³", "liters"]}
                                }
                            },
                            "PRC": {
                                "type": "object",
                                "properties": {
                                    "value": {"type": "number"},
                                    "unit": {"type": "string", "enum": ["m³", "liters"]}
                                }
                            }
                        }
                    },
                    "Sep-2024": {
                        "type": "object",
                        "properties": {
                            "HK": {
                                "type": "object",
                                "properties": {
                                    "value": {"type": "number"},
                                    "unit": {"type": "string", "enum": ["m³", "liters"]}
                                }
                            },
                            "PRC": {
                                "type": "object",
                                "properties": {
                                    "value": {"type": "number"},
                                    "unit": {"type": "string", "enum": ["m³", "liters"]}
                                }
                            }
                        }
                    },
                    "Oct-2024": {
                        "type": "object",
                        "properties": {
                            "HK": {
                                "type": "object",
                                "properties": {
                                    "value": {"type": "number"},
                                    "unit": {"type": "string", "enum": ["m³", "liters"]}
                                }
                            },
                            "PRC": {
                                "type": "object",
                                "properties": {
                                    "value": {"type": "number"},
                                    "unit": {"type": "string", "enum": ["m³", "liters"]}
                                }
                            }
                        }
                    },
                    "Nov-2024": {
                        "type": "object",
                        "properties": {
                            "HK": {
                                "type": "object",
                                "properties": {
                                    "value": {"type": "number"},
                                    "unit": {"type": "string", "enum": ["m³", "liters"]}
                                }
                            },
                            "PRC": {
                                "type": "object",
                                "properties": {
                                    "value": {"type": "number"},
                                    "unit": {"type": "string", "enum": ["m³", "liters"]}
                                }
                            }
                        }
                    },
                    "Dec-2024": {
                        "type": "object",
                        "properties": {
                            "HK": {
                                "type": "object",
                                "properties": {
                                    "value": {"type": "number"},
                                    "unit": {"type": "string", "enum": ["m³", "liters"]}
                                }
                            },
                            "PRC": {
                                "type": "object",
                                "properties": {
                                    "value": {"type": "number"},
                                    "unit": {"type": "string", "enum": ["m³", "liters"]}
                                }
                            }
                        }
                    }
                }
            },
            "total_consumption": {
                "type": "object",
                "x-calculated": True,
                "properties": {
                    "HK": {
                        "type": "object",
                        "properties": {
                            "value": {"type": "number"},
                            "unit": {"type": "string", "enum": ["m³", "liters"]}
                        }
                    },
                    "PRC": {
                        "type": "object",
                        "properties": {
                            "value": {"type": "number"},
                            "unit": {"type": "string", "enum": ["m³", "liters"]}
                        }
                    }
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
            }
        }
    },
    "ui_hints": {
        "editable_fields": ["periods", "kpi_reference", "water_type"],
        "read_only_fields": ["total_consumption"]
    }
} 