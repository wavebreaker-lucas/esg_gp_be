"""
Schema for water consumption by location (HK, PRC).
"""

WATER_CONSUMPTION_SCHEMA = {
    "type": "water_consumption",
    "name": "Water Consumption by Location",
    "description": "For tracking water consumption across different locations",
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