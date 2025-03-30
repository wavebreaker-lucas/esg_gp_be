"""
Schema for electricity consumption split by provider (CLP, HKE).
"""

ELECTRICITY_PROVIDER_SCHEMA = {
    "type": "electricity_provider",
    "name": "Electricity Consumption by Provider",
    "description": "For tracking electricity usage by different providers (e.g., CLP, HKE)",
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
            "_metadata": {
                "type": "object",
                "properties": {
                    "primary_measurement": {
                        "type": "object",
                        "properties": {
                            "path": {"type": "string", "default": "periods.Jan-2024.CLP.value"},
                            "unit": {"type": "string", "default": "kWh"}
                        }
                    }
                }
            }
        }
    },
    "primary_path_example": "periods.Jan-2024.CLP.value"
} 