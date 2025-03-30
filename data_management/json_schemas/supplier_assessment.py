"""
Schema for supplier assessment with complex data.
"""

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