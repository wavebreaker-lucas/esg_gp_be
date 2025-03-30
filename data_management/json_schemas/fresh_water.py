"""
Schema for fresh water consumption across Hong Kong and the PRC.
Used for KPI A2.2 reporting.
"""

FRESH_WATER_SCHEMA = {
    "type": "fresh_water",
    "name": "Fresh Water Consumption by Region",
    "description": "For tracking fresh water consumption across Hong Kong and the PRC",
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
                "enum": ["Fresh Water"],
                "default": "Fresh Water"
            },
            "_metadata": {
                "type": "object",
                "properties": {
                    "primary_measurement": {
                        "type": "object",
                        "properties": {
                            "path": {"type": "string", "default": "periods.Jan-2024.HK.value"},
                            "unit": {"type": "string", "default": "m³"}
                        }
                    }
                }
            }
        }
    },
    "primary_path_example": "periods.Jan-2024.HK.value"
} 