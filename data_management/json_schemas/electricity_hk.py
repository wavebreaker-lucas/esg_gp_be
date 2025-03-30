"""
Schema for Hong Kong electricity consumption tracking CLP and HKE separately.
Used for KPI A1.2 and A2.1 reporting.
"""

ELECTRICITY_HK_SCHEMA = {
    "type": "electricity_hk",
    "name": "Hong Kong Electricity Consumption (CLP/HKE)",
    "description": "For tracking electricity consumption in Hong Kong split by provider (CLP, HKE)",
    "calculated_fields": [
        {
            "path": "total_consumption.CLP", 
            "calculation": "sum(periods.*.CLP.value)",
            "description": "Total CLP electricity consumption"
        },
        {
            "path": "total_consumption.HKE", 
            "calculation": "sum(periods.*.HKE.value)",
            "description": "Total HKE electricity consumption"
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
                            "CLP": {
                                "type": "object",
                                "properties": {
                                    "value": {"type": "number"},
                                    "unit": {"type": "string", "enum": ["kWh", "MWh"]}
                                }
                            },
                            "HKE": {
                                "type": "object",
                                "properties": {
                                    "value": {"type": "number"},
                                    "unit": {"type": "string", "enum": ["kWh", "MWh"]}
                                }
                            }
                        }
                    },
                    "Feb-2024": {
                        "type": "object",
                        "properties": {
                            "CLP": {
                                "type": "object",
                                "properties": {
                                    "value": {"type": "number"},
                                    "unit": {"type": "string", "enum": ["kWh", "MWh"]}
                                }
                            },
                            "HKE": {
                                "type": "object",
                                "properties": {
                                    "value": {"type": "number"},
                                    "unit": {"type": "string", "enum": ["kWh", "MWh"]}
                                }
                            }
                        }
                    },
                    "Mar-2024": {
                        "type": "object",
                        "properties": {
                            "CLP": {
                                "type": "object",
                                "properties": {
                                    "value": {"type": "number"},
                                    "unit": {"type": "string", "enum": ["kWh", "MWh"]}
                                }
                            },
                            "HKE": {
                                "type": "object",
                                "properties": {
                                    "value": {"type": "number"},
                                    "unit": {"type": "string", "enum": ["kWh", "MWh"]}
                                }
                            }
                        }
                    },
                    "Apr-2024": {
                        "type": "object",
                        "properties": {
                            "CLP": {
                                "type": "object",
                                "properties": {
                                    "value": {"type": "number"},
                                    "unit": {"type": "string", "enum": ["kWh", "MWh"]}
                                }
                            },
                            "HKE": {
                                "type": "object",
                                "properties": {
                                    "value": {"type": "number"},
                                    "unit": {"type": "string", "enum": ["kWh", "MWh"]}
                                }
                            }
                        }
                    },
                    "May-2024": {
                        "type": "object",
                        "properties": {
                            "CLP": {
                                "type": "object",
                                "properties": {
                                    "value": {"type": "number"},
                                    "unit": {"type": "string", "enum": ["kWh", "MWh"]}
                                }
                            },
                            "HKE": {
                                "type": "object",
                                "properties": {
                                    "value": {"type": "number"},
                                    "unit": {"type": "string", "enum": ["kWh", "MWh"]}
                                }
                            }
                        }
                    },
                    "Jun-2024": {
                        "type": "object",
                        "properties": {
                            "CLP": {
                                "type": "object",
                                "properties": {
                                    "value": {"type": "number"},
                                    "unit": {"type": "string", "enum": ["kWh", "MWh"]}
                                }
                            },
                            "HKE": {
                                "type": "object",
                                "properties": {
                                    "value": {"type": "number"},
                                    "unit": {"type": "string", "enum": ["kWh", "MWh"]}
                                }
                            }
                        }
                    },
                    "Jul-2024": {
                        "type": "object",
                        "properties": {
                            "CLP": {
                                "type": "object",
                                "properties": {
                                    "value": {"type": "number"},
                                    "unit": {"type": "string", "enum": ["kWh", "MWh"]}
                                }
                            },
                            "HKE": {
                                "type": "object",
                                "properties": {
                                    "value": {"type": "number"},
                                    "unit": {"type": "string", "enum": ["kWh", "MWh"]}
                                }
                            }
                        }
                    },
                    "Aug-2024": {
                        "type": "object",
                        "properties": {
                            "CLP": {
                                "type": "object",
                                "properties": {
                                    "value": {"type": "number"},
                                    "unit": {"type": "string", "enum": ["kWh", "MWh"]}
                                }
                            },
                            "HKE": {
                                "type": "object",
                                "properties": {
                                    "value": {"type": "number"},
                                    "unit": {"type": "string", "enum": ["kWh", "MWh"]}
                                }
                            }
                        }
                    },
                    "Sep-2024": {
                        "type": "object",
                        "properties": {
                            "CLP": {
                                "type": "object",
                                "properties": {
                                    "value": {"type": "number"},
                                    "unit": {"type": "string", "enum": ["kWh", "MWh"]}
                                }
                            },
                            "HKE": {
                                "type": "object",
                                "properties": {
                                    "value": {"type": "number"},
                                    "unit": {"type": "string", "enum": ["kWh", "MWh"]}
                                }
                            }
                        }
                    },
                    "Oct-2024": {
                        "type": "object",
                        "properties": {
                            "CLP": {
                                "type": "object",
                                "properties": {
                                    "value": {"type": "number"},
                                    "unit": {"type": "string", "enum": ["kWh", "MWh"]}
                                }
                            },
                            "HKE": {
                                "type": "object",
                                "properties": {
                                    "value": {"type": "number"},
                                    "unit": {"type": "string", "enum": ["kWh", "MWh"]}
                                }
                            }
                        }
                    },
                    "Nov-2024": {
                        "type": "object",
                        "properties": {
                            "CLP": {
                                "type": "object",
                                "properties": {
                                    "value": {"type": "number"},
                                    "unit": {"type": "string", "enum": ["kWh", "MWh"]}
                                }
                            },
                            "HKE": {
                                "type": "object",
                                "properties": {
                                    "value": {"type": "number"},
                                    "unit": {"type": "string", "enum": ["kWh", "MWh"]}
                                }
                            }
                        }
                    },
                    "Dec-2024": {
                        "type": "object",
                        "properties": {
                            "CLP": {
                                "type": "object",
                                "properties": {
                                    "value": {"type": "number"},
                                    "unit": {"type": "string", "enum": ["kWh", "MWh"]}
                                }
                            },
                            "HKE": {
                                "type": "object",
                                "properties": {
                                    "value": {"type": "number"},
                                    "unit": {"type": "string", "enum": ["kWh", "MWh"]}
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
                    "CLP": {
                        "type": "object",
                        "properties": {
                            "value": {"type": "number"},
                            "unit": {"type": "string", "enum": ["kWh", "MWh"]}
                        }
                    },
                    "HKE": {
                        "type": "object",
                        "properties": {
                            "value": {"type": "number"},
                            "unit": {"type": "string", "enum": ["kWh", "MWh"]}
                        }
                    }
                }
            },
            "kpi_reference": {
                "type": "string",
                "default": "KPI A1.2, A2.1"
            }
        }
    },
    "ui_hints": {
        "editable_fields": ["periods", "kpi_reference"],
        "read_only_fields": ["total_consumption"]
    }
} 