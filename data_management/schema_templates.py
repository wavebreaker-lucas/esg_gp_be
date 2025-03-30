"""
Schema templates for the ESG Platform.

This module contains predefined JSON schema templates for common metric types.
These templates are used by the schema registry to provide standard patterns for metrics.
"""

# Simple metric with a single value and unit
SINGLE_VALUE_SCHEMA = {
    "type": "single_value",
    "name": "Simple Value with Unit",
    "description": "For basic metrics with a single value and unit",
    "template": {
        "type": "object",
        "properties": {
            "value": {"type": "number"},
            "unit": {"type": "string", "enum": ["count", "percentage", "tonnes", "kWh"]},
            "comments": {"type": "string"}
        },
        "required": ["value", "unit"]
    },
    "primary_path_example": "value"
}

# Emissions metric with scope information
EMISSIONS_SCHEMA = {
    "type": "emissions",
    "name": "Emissions Metric",
    "description": "For tracking GHG emissions with scope information",
    "template": {
        "type": "object",
        "properties": {
            "value": {"type": "number"},
            "unit": {"type": "string", "enum": ["tCO2e", "kgCO2e"]},
            "scope": {"type": "string", "enum": ["Scope 1", "Scope 2", "Scope 3"]},
            "source": {"type": "string"},
            "calculation_method": {"type": "string", "enum": ["location-based", "market-based"]},
            "periods": {
                "type": "object",
                "additionalProperties": {
                    "type": "object",
                    "properties": {
                        "value": {"type": "number"},
                        "unit": {"type": "string", "enum": ["tCO2e", "kgCO2e"]},
                        "notes": {"type": "string"}
                    }
                }
            },
            "_metadata": {
                "type": "object",
                "properties": {
                    "primary_measurement": {
                        "type": "object",
                        "properties": {
                            "path": {"type": "string", "default": "value"},
                            "unit": {"type": "string", "default": "tCO2e"}
                        }
                    }
                }
            }
        },
        "required": ["value", "unit", "scope"]
    },
    "primary_path_example": "value"
}

# Monthly electricity consumption
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
                    }
                },
                "additionalProperties": {
                    "type": "object",
                    "properties": {
                        "value": {"type": "number"},
                        "unit": {"type": "string", "enum": ["kWh", "MWh", "GWh"]},
                        "comments": {"type": "string"}
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

# Electricity consumption by provider (CLP, HKE)
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
                    }
                },
                "additionalProperties": {
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

# Water consumption by location (HK, PRC)
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

# Multiple utility consumption in one metric
UTILITY_BUNDLE_SCHEMA = {
    "type": "utility_bundle",
    "name": "Multiple Utility Consumption",
    "description": "For tracking multiple utility consumptions together",
    "template": {
        "type": "object",
        "properties": {
            "electricity": {
                "type": "object",
                "properties": {
                    "value": {"type": "number"},
                    "unit": {"type": "string", "enum": ["kWh", "MWh"]}
                }
            },
            "water": {
                "type": "object",
                "properties": {
                    "value": {"type": "number"},
                    "unit": {"type": "string", "enum": ["m³", "liters"]}
                }
            },
            "gas": {
                "type": "object",
                "properties": {
                    "value": {"type": "number"},
                    "unit": {"type": "string", "enum": ["m³", "BTU"]}
                }
            },
            "comments": {"type": "string"},
            "_metadata": {
                "type": "object",
                "properties": {
                    "primary_measurement": {
                        "type": "object",
                        "properties": {
                            "path": {"type": "string", "default": "electricity.value"},
                            "unit": {"type": "string", "default": "kWh"}
                        }
                    }
                }
            }
        }
    },
    "primary_path_example": "electricity.value"
}

# Supplier assessment with complex data
SUPPLIER_ASSESSMENT_SCHEMA = {
    "type": "supplier_assessment",
    "name": "Supplier Assessment",
    "description": "For tracking supplier compliance and assessments",
    "template": {
        "type": "object",
        "properties": {
            "suppliers": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "id": {"type": "string"},
                        "assessment": {
                            "type": "object",
                            "properties": {
                                "compliance_status": {
                                    "type": "string", 
                                    "enum": ["Compliant", "Partially Compliant", "Non-Compliant"]
                                },
                                "score": {
                                    "type": "object",
                                    "properties": {
                                        "value": {"type": "number"},
                                        "unit": {"type": "string", "enum": ["points", "percentage"]}
                                    }
                                },
                                "date": {"type": "string", "format": "date"}
                            }
                        },
                        "categories": {
                            "type": "array",
                            "items": {"type": "string"}
                        }
                    }
                }
            },
            "assessment_period": {"type": "string"},
            "comments": {"type": "string"},
            "_metadata": {
                "type": "object",
                "properties": {
                    "primary_measurement": {
                        "type": "object",
                        "properties": {
                            "path": {"type": "string", "default": "suppliers[0].assessment.score.value"},
                            "unit": {"type": "string", "default": "percentage"}
                        }
                    }
                }
            }
        }
    },
    "primary_path_example": "suppliers[0].assessment.score.value"
}

# Legal cases register for KPI B7.1
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

# Collection of all schema templates for easy access
SCHEMA_TEMPLATES = [
    SINGLE_VALUE_SCHEMA,
    EMISSIONS_SCHEMA,
    ELECTRICITY_MONTHLY_SCHEMA,
    ELECTRICITY_PROVIDER_SCHEMA,
    WATER_CONSUMPTION_SCHEMA, 
    UTILITY_BUNDLE_SCHEMA,
    SUPPLIER_ASSESSMENT_SCHEMA,
    LEGAL_CASES_SCHEMA
] 