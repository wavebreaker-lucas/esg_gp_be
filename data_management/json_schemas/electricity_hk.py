"""
Schema for Hong Kong electricity consumption tracking CLP and HKE separately.
Used for KPI A1.2 and A2.1 reporting.
"""

ELECTRICITY_HK_SCHEMA = {
    "type": "electricity_hk",
    "name": "Hong Kong Electricity Consumption (CLP/HKE)",
    "description": "For tracking electricity consumption in Hong Kong split by provider (CLP, HKE)",
    "data_structure_type": "periodic_measurement",
    "requires_calculation": True,
    "calculation_type": "sum_by_provider",
    "calculated_fields": [
        {
            "path": "total_consumption.CLP", 
            "calculation": "sum(periods.*.CLP.value)",
            "description": "Total CLP electricity consumption",
            "dependency_paths": ["periods.*.CLP"]
        },
        {
            "path": "total_consumption.HKE", 
            "calculation": "sum(periods.*.HKE.value)",
            "description": "Total HKE electricity consumption",
            "dependency_paths": ["periods.*.HKE"]
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
                            "CLP": {
                                "type": "object",
                                "properties": {
                                    "value": {"type": "number"},
                                    "unit": {"type": "string", "enum": ["kWh"]}
                                }
                            },
                            "HKE": {
                                "type": "object",
                                "properties": {
                                    "value": {"type": "number"},
                                    "unit": {"type": "string", "enum": ["kWh"]}
                                }
                            }
                        }
                    },
                    "Feb-2025": {
                        "type": "object",
                        "properties": {
                            "CLP": {
                                "type": "object",
                                "properties": {
                                    "value": {"type": "number"},
                                    "unit": {"type": "string", "enum": ["kWh"]}
                                }
                            },
                            "HKE": {
                                "type": "object",
                                "properties": {
                                    "value": {"type": "number"},
                                    "unit": {"type": "string", "enum": ["kWh"]}
                                }
                            }
                        }
                    },
                    "Mar-2025": {
                        "type": "object",
                        "properties": {
                            "CLP": {
                                "type": "object",
                                "properties": {
                                    "value": {"type": "number"},
                                    "unit": {"type": "string", "enum": ["kWh"]}
                                }
                            },
                            "HKE": {
                                "type": "object",
                                "properties": {
                                    "value": {"type": "number"},
                                    "unit": {"type": "string", "enum": ["kWh"]}
                                }
                            }
                        }
                    },
                    "Apr-2025": {
                        "type": "object",
                        "properties": {
                            "CLP": {
                                "type": "object",
                                "properties": {
                                    "value": {"type": "number"},
                                    "unit": {"type": "string", "enum": ["kWh"]}
                                }
                            },
                            "HKE": {
                                "type": "object",
                                "properties": {
                                    "value": {"type": "number"},
                                    "unit": {"type": "string", "enum": ["kWh"]}
                                }
                            }
                        }
                    },
                    "May-2025": {
                        "type": "object",
                        "properties": {
                            "CLP": {
                                "type": "object",
                                "properties": {
                                    "value": {"type": "number"},
                                    "unit": {"type": "string", "enum": ["kWh"]}
                                }
                            },
                            "HKE": {
                                "type": "object",
                                "properties": {
                                    "value": {"type": "number"},
                                    "unit": {"type": "string", "enum": ["kWh"]}
                                }
                            }
                        }
                    },
                    "Jun-2025": {
                        "type": "object",
                        "properties": {
                            "CLP": {
                                "type": "object",
                                "properties": {
                                    "value": {"type": "number"},
                                    "unit": {"type": "string", "enum": ["kWh"]}
                                }
                            },
                            "HKE": {
                                "type": "object",
                                "properties": {
                                    "value": {"type": "number"},
                                    "unit": {"type": "string", "enum": ["kWh"]}
                                }
                            }
                        }
                    },
                    "Jul-2025": {
                        "type": "object",
                        "properties": {
                            "CLP": {
                                "type": "object",
                                "properties": {
                                    "value": {"type": "number"},
                                    "unit": {"type": "string", "enum": ["kWh"]}
                                }
                            },
                            "HKE": {
                                "type": "object",
                                "properties": {
                                    "value": {"type": "number"},
                                    "unit": {"type": "string", "enum": ["kWh"]}
                                }
                            }
                        }
                    },
                    "Aug-2025": {
                        "type": "object",
                        "properties": {
                            "CLP": {
                                "type": "object",
                                "properties": {
                                    "value": {"type": "number"},
                                    "unit": {"type": "string", "enum": ["kWh"]}
                                }
                            },
                            "HKE": {
                                "type": "object",
                                "properties": {
                                    "value": {"type": "number"},
                                    "unit": {"type": "string", "enum": ["kWh"]}
                                }
                            }
                        }
                    },
                    "Sep-2025": {
                        "type": "object",
                        "properties": {
                            "CLP": {
                                "type": "object",
                                "properties": {
                                    "value": {"type": "number"},
                                    "unit": {"type": "string", "enum": ["kWh"]}
                                }
                            },
                            "HKE": {
                                "type": "object",
                                "properties": {
                                    "value": {"type": "number"},
                                    "unit": {"type": "string", "enum": ["kWh"]}
                                }
                            }
                        }
                    },
                    "Oct-2025": {
                        "type": "object",
                        "properties": {
                            "CLP": {
                                "type": "object",
                                "properties": {
                                    "value": {"type": "number"},
                                    "unit": {"type": "string", "enum": ["kWh"]}
                                }
                            },
                            "HKE": {
                                "type": "object",
                                "properties": {
                                    "value": {"type": "number"},
                                    "unit": {"type": "string", "enum": ["kWh"]}
                                }
                            }
                        }
                    },
                    "Nov-2025": {
                        "type": "object",
                        "properties": {
                            "CLP": {
                                "type": "object",
                                "properties": {
                                    "value": {"type": "number"},
                                    "unit": {"type": "string", "enum": ["kWh"]}
                                }
                            },
                            "HKE": {
                                "type": "object",
                                "properties": {
                                    "value": {"type": "number"},
                                    "unit": {"type": "string", "enum": ["kWh"]}
                                }
                            }
                        }
                    },
                    "Dec-2025": {
                        "type": "object",
                        "properties": {
                            "CLP": {
                                "type": "object",
                                "properties": {
                                    "value": {"type": "number"},
                                    "unit": {"type": "string", "enum": ["kWh"]}
                                }
                            },
                            "HKE": {
                                "type": "object",
                                "properties": {
                                    "value": {"type": "number"},
                                    "unit": {"type": "string", "enum": ["kWh"]}
                                }
                            }
                        }
                    }
                }
            },
            "total_consumption": {
                "type": "object",
                "is_calculated": True,
                "x-calculated": True,
                "properties": {
                    "CLP": {
                        "type": "object",
                        "properties": {
                            "value": {"type": "number"},
                            "unit": {"type": "string", "enum": ["kWh"]}
                        }
                    },
                    "HKE": {
                        "type": "object",
                        "properties": {
                            "value": {"type": "number"},
                            "unit": {"type": "string", "enum": ["kWh"]}
                        }
                    }
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