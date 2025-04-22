"""
Fixture data for ESG Checklists.
This module contains the structured data for creating Environmental, Social, and Governance checklists.
"""

ENVIRONMENTAL_CHECKLIST = {
    "categories": [
        {
            "id": "1.1",
            "name": "EMS FRAMEWORK",
            "subcategories": [
                {
                    "name": "EMS Framework",
                    "items": [
                        {
                            "id": "a",
                            "text": "Are environmental policies documented and accessible?",
                            "required": True
                        }
                    ]
                },
                {
                    "name": "Objectives and Targets",
                    "items": [
                        {
                            "id": "b",
                            "text": "Are environmental objectives and targets clearly defined?",
                            "required": True
                        },
                        {
                            "id": "c",
                            "text": "Is there a plan to achieve these objectives and targets?",
                            "required": True
                        }
                    ]
                },
                {
                    "name": "Monitoring and Review",
                    "items": [
                        {
                            "id": "d",
                            "text": "Are environmental performance indicators tracked regularly?",
                            "required": True
                        }
                    ]
                }
            ]
        },
        {
            "id": "1.2",
            "name": "ENERGY MANAGEMENT",
            "subcategories": [
                {
                    "name": "Energy Policy",
                    "items": [
                        {
                            "id": "a",
                            "text": "Is there an energy policy that outlines goals and strategies?",
                            "required": True
                        },
                        {
                            "id": "b",
                            "text": "Is energy consumption being monitored and tracked?",
                            "required": True
                        }
                    ]
                },
                {
                    "name": "Energy Efficiency Measures",
                    "items": [
                        {
                            "id": "c",
                            "text": "Are energy efficiency projects identified and implemented? (e.g., LED lighting upgrades or energy-efficient equipment)",
                            "required": True
                        }
                    ]
                },
                {
                    "name": "Renewable Energy",
                    "items": [
                        {
                            "id": "d",
                            "text": "Is there a strategy to increase the use of renewable energy sources?",
                            "required": True
                        }
                    ]
                }
            ]
        },
        {
            "id": "1.3",
            "name": "WATER MANAGEMENT",
            "subcategories": [
                {
                    "name": "Water Conservation Policy",
                    "items": [
                        {
                            "id": "a",
                            "text": "Is there a water conservation policy in place?",
                            "required": True
                        },
                        {
                            "id": "b",
                            "text": "Are water conservation goals set and communicated?",
                            "required": True
                        }
                    ]
                },
                {
                    "name": "Water Usage Tracking",
                    "items": [
                        {
                            "id": "c",
                            "text": "Is water usage data collected and monitored regularly?",
                            "required": True
                        },
                        {
                            "id": "d",
                            "text": "Are benchmarks established for water usage reduction?",
                            "required": True
                        }
                    ]
                }
            ]
        },
        {
            "id": "1.4",
            "name": "WASTE MANAGEMENT",
            "subcategories": [
                {
                    "name": "Waste Policy",
                    "items": [
                        {
                            "id": "a",
                            "text": "Is there a waste management policy/reduction and recycling programme in place?",
                            "required": True
                        },
                        {
                            "id": "b",
                            "text": "Are waste reduction targets defined?",
                            "required": True
                        }
                    ]
                },
                {
                    "name": "Recycling Programs",
                    "items": [
                        {
                            "id": "c",
                            "text": "Are recycling programs in place and effective?",
                            "required": True
                        },
                        {
                            "id": "d",
                            "text": "Is the percentage of waste diverted from landfill tracked?",
                            "required": True
                        }
                    ]
                }
            ]
        },
        {
            "id": "1.5",
            "name": "POLLUTION AND EMISSIONS & CLIMATE CHANGE",
            "subcategories": [
                {
                    "name": "Emission Inventory",
                    "items": [
                        {
                            "id": "a",
                            "text": "Have you calculated your organization's carbon footprint?",
                            "required": True
                        }
                    ]
                },
                {
                    "name": "Pollution Control Measures",
                    "items": [
                        {
                            "id": "b",
                            "text": "Are pollution control technologies and practices implemented?",
                            "required": True
                        },
                        {
                            "id": "c",
                            "text": "Are there measures in place to prevent or mitigate pollution (air, water, soil)?",
                            "required": True
                        }
                    ]
                },
                {
                    "name": "GHG Reduction Strategy",
                    "items": [
                        {
                            "id": "d",
                            "text": "Is the GHG emissions being tracked and aimed to reduce?",
                            "required": True
                        },
                        {
                            "id": "e",
                            "text": "Is there a strategy to reduce GHG emissions?",
                            "required": True
                        }
                    ]
                },
                {
                    "name": "Climate Adaptation",
                    "items": [
                        {
                            "id": "f",
                            "text": "Does the organization have strategies in place to adapt to the impacts of climate change?",
                            "required": True
                        }
                    ]
                }
            ]
        },
        {
            "id": "1.6",
            "name": "BIODIVERSITY AND LAND USE",
            "subcategories": [
                {
                    "name": "Biodiversity Assessment",
                    "items": [
                        {
                            "id": "a",
                            "text": "Are biodiversity impacts assessed for all operations?",
                            "required": True
                        },
                        {
                            "id": "b",
                            "text": "Are baseline biodiversity data collected?",
                            "required": True
                        }
                    ]
                },
                {
                    "name": "Habitat Protection",
                    "items": [
                        {
                            "id": "c",
                            "text": "Are measures in place to protect local habitats and species?",
                            "required": True
                        },
                        {
                            "id": "d",
                            "text": "Are restoration projects undertaken for degraded areas?",
                            "required": True
                        }
                    ]
                }
            ]
        },
        {
            "id": "1.7",
            "name": "OTHER ENVIRONMENTAL INDICATORS",
            "subcategories": [
                {
                    "name": "Circular Economy",
                    "items": [
                        {
                            "id": "a",
                            "text": "Are there initiatives to promote a circular economy, such as product lifecycle management and resource recovery?",
                            "required": True
                        }
                    ]
                },
                {
                    "name": "Eco-Innovation",
                    "items": [
                        {
                            "id": "b",
                            "text": "Are there initiatives to develop and implement eco-friendly technologies and innovations?",
                            "required": True
                        }
                    ]
                }
            ]
        }
    ]
}

SOCIAL_CHECKLIST = {
    "categories": [
        {
            "id": "2.1",
            "name": "LABOR PRACTICES",
            "subcategories": [
                {
                    "name": "Employment Policy",
                    "items": [
                        {
                            "id": "a",
                            "text": "Is there a clear employment policy that ensures fair labor practices?",
                            "required": True
                        },
                        {
                            "id": "b",
                            "text": "Are employment contracts compliant with labor laws?",
                            "required": True
                        }
                    ]
                },
                {
                    "name": "Working Conditions",
                    "items": [
                        {
                            "id": "c",
                            "text": "Are working conditions safe and healthy?",
                            "required": True
                        },
                        {
                            "id": "d",
                            "text": "Are working hours and conditions monitored for compliance?",
                            "required": True
                        }
                    ]
                },
                {
                    "name": "Employee Rights",
                    "items": [
                        {
                            "id": "e",
                            "text": "Are employee rights and benefits protected and communicated?",
                            "required": True
                        },
                        {
                            "id": "f",
                            "text": "Is there a grievance mechanism for employees?",
                            "required": True
                        }
                    ]
                }
            ]
        },
        {
            "id": "2.2",
            "name": "HEALTH & SAFETY AND CUSTOMER",
            "subcategories": [
                {
                    "name": "Health and Safety Policy",
                    "items": [
                        {
                            "id": "a",
                            "text": "Is there a health and safety policy in place?",
                            "required": True
                        },
                        {
                            "id": "b",
                            "text": "Are health and safety responsibilities assigned?",
                            "required": True
                        },
                        {
                            "id": "c",
                            "text": "Are there programmes in place to support employee physical and mental health and well-being?",
                            "required": True
                        }
                    ]
                },
                {
                    "name": "Incident Reporting",
                    "items": [
                        {
                            "id": "f",
                            "text": "Is there a system for reporting and investigating incidents?",
                            "required": True
                        },
                        {
                            "id": "g",
                            "text": "Are incident data analyzed to prevent recurrence?",
                            "required": True
                        }
                    ]
                }
            ]
        },
        {
            "id": "2.3",
            "name": "DIVERSITY AND INCLUSION",
            "subcategories": [
                {
                    "name": "Diversity Policy",
                    "items": [
                        {
                            "id": "a",
                            "text": "Is there a diversity and inclusion policy in place?",
                            "required": True
                        },
                        {
                            "id": "b",
                            "text": "Are diversity goals set, communicated and tracked?",
                            "required": True
                        }
                    ]
                }
            ]
        },
        {
            "id": "2.4",
            "name": "COMMUNITY ENGAGEMENT",
            "subcategories": [
                {
                    "name": "Community Policy",
                    "items": [
                        {
                            "id": "a",
                            "text": "Is there a policy for engaging with local communities?",
                            "required": True
                        },
                        {
                            "id": "b",
                            "text": "Are community engagement goals defined?",
                            "required": True
                        }
                    ]
                },
                {
                    "name": "Impact Assessments",
                    "items": [
                        {
                            "id": "c",
                            "text": "Are community impacts assessed and documented?",
                            "required": True
                        },
                        {
                            "id": "d",
                            "text": "Are mitigation measures implemented for negative impacts?",
                            "required": True
                        }
                    ]
                },
                {
                    "name": "Community Programs",
                    "items": [
                        {
                            "id": "e",
                            "text": "Are community development and support programs in place?",
                            "required": True
                        },
                        {
                            "id": "f",
                            "text": "Is there a process to track and report community engagement outcomes?",
                            "required": True
                        }
                    ]
                }
            ]
        },
        {
            "id": "2.5",
            "name": "HUMAN RIGHTS & SUPPLY CHAIN",
            "subcategories": [
                {
                    "name": "Human Rights Policy",
                    "items": [
                        {
                            "id": "a",
                            "text": "Is there a human rights policy in place?",
                            "required": True
                        },
                        {
                            "id": "b",
                            "text": "Is the policy aligned with international human rights standards?",
                            "required": True
                        }
                    ]
                },
                {
                    "name": "Supply Chain Due Diligence",
                    "items": [
                        {
                            "id": "c",
                            "text": "Are suppliers required to adhere to human rights standards/ethical labor standards?",
                            "required": True
                        },
                        {
                            "id": "d",
                            "text": "Are all the sourced materials and products sustainable?",
                            "required": True
                        }
                    ]
                }
            ]
        },
        {
            "id": "2.6",
            "name": "STAFF, TRAINING AND DEVELOPMENT",
            "subcategories": [
                {
                    "name": "Training Programs",
                    "items": [
                        {
                            "id": "a",
                            "text": "Are training and development programs available for employees?",
                            "required": True
                        },
                        {
                            "id": "b",
                            "text": "Are training needs assessed regularly?",
                            "required": True
                        }
                    ]
                },
                {
                    "name": "Career Development",
                    "items": [
                        {
                            "id": "c",
                            "text": "Are career development opportunities provided?",
                            "required": True
                        }
                    ]
                },
                {
                    "name": "Staff Engagement and Ownership",
                    "items": [
                        {
                            "id": "d",
                            "text": "Does the organization have programmes that promote employee ownership and participation in decision-making?",
                            "required": True
                        }
                    ]
                }
            ]
        },
        {
            "id": "2.7",
            "name": "SUPPLY CHAIN MANAGEMENT",
            "subcategories": [
                {
                    "name": "Supplier Selection",
                    "items": [
                        {
                            "id": "a",
                            "text": "Are ESG criteria included in supplier selection processes?",
                            "required": True
                        },
                        {
                            "id": "b",
                            "text": "Are suppliers evaluated on their ESG performance?",
                            "required": True
                        }
                    ]
                },
                {
                    "name": "Supply Chain Monitoring",
                    "items": [
                        {
                            "id": "c",
                            "text": "Is the supply chain monitored for ESG compliance?",
                            "required": True
                        },
                        {
                            "id": "d",
                            "text": "Are audits of suppliers conducted regularly?",
                            "required": True
                        }
                    ]
                }
            ]
        },
        {
            "id": "2.8",
            "name": "PRODUCT RESPONSIBILITY",
            "subcategories": [
                {
                    "name": "Product Assessment",
                    "items": [
                        {
                            "id": "a",
                            "text": "Are products/services assessed for environmental and social impacts throughout their lifecycle?",
                            "required": True
                        },
                        {
                            "id": "b",
                            "text": "Are product/service impact assessments documented?",
                            "required": True
                        }
                    ]
                },
                {
                    "name": "Product Safety",
                    "items": [
                        {
                            "id": "c",
                            "text": "Are product safety standards in place and followed?",
                            "required": True
                        },
                        {
                            "id": "d",
                            "text": "Are safety incidents tracked and addressed promptly?",
                            "required": True
                        }
                    ]
                },
                {
                    "name": "Customer Feedback",
                    "items": [
                        {
                            "id": "e",
                            "text": "Is there a process for collecting and addressing customer feedback?",
                            "required": True
                        },
                        {
                            "id": "f",
                            "text": "Are customer complaints managed effectively?",
                            "required": True
                        }
                    ]
                }
            ]
        }
    ]
}

GOVERNANCE_CHECKLIST = {
    "categories": [
        {
            "id": "3.2",
            "name": "ETHICS AND COMPLIANCE",
            "subcategories": [
                {
                    "name": "Ethics Policy",
                    "items": [
                        {
                            "id": "a",
                            "text": "Is there a code of ethics or conduct?",
                            "required": True
                        },
                        {
                            "id": "b",
                            "text": "Are ethics policies communicated to all employees?",
                            "required": True
                        }
                    ]
                },
                {
                    "name": "Compliance Programs",
                    "items": [
                        {
                            "id": "c",
                            "text": "Are there programs to ensure compliance with laws and regulations?",
                            "required": True
                        },
                        {
                            "id": "d",
                            "text": "Is there a whistleblower policy and mechanism in place?",
                            "required": True
                        }
                    ]
                },
                {
                    "name": "Anti-corruption Measures",
                    "items": [
                        {
                            "id": "e",
                            "text": "Are anti-corruption policies implemented?",
                            "required": True
                        },
                        {
                            "id": "f",
                            "text": "Are corruption risks assessed and mitigated?",
                            "required": True
                        }
                    ]
                }
            ]
        },
        {
            "id": "3.4",
            "name": "TRANSPARENCY AND DISCLOSURE",
            "subcategories": [
                {
                    "name": "Financial Reporting",
                    "items": [
                        {
                            "id": "a",
                            "text": "Are financial statements transparent and accurate?",
                            "required": True
                        },
                        {
                            "id": "b",
                            "text": "Are financial reports audited by independent auditors?",
                            "required": True
                        }
                    ]
                },
                {
                    "name": "Stakeholder Communication",
                    "items": [
                        {
                            "id": "c",
                            "text": "Is there a strategy for communicating with stakeholders?",
                            "required": True
                        },
                        {
                            "id": "d",
                            "text": "Are stakeholder concerns and feedback addressed transparently?",
                            "required": True
                        }
                    ]
                }
            ]
        },
        {
            "id": "3.5",
            "name": "STAKEHOLDER ENGAGEMENT",
            "subcategories": [
                {
                    "name": "Stakeholder Identification",
                    "items": [
                        {
                            "id": "a",
                            "text": "Are the key stakeholders identified and mapped?",
                            "required": True
                        },
                        {
                            "id": "b",
                            "text": "Are stakeholder interests and concerns documented?",
                            "required": True
                        }
                    ]
                },
                {
                    "name": "Feedback Mechanisms",
                    "items": [
                        {
                            "id": "c",
                            "text": "Are feedback mechanisms in place for stakeholders?",
                            "required": True
                        },
                        {
                            "id": "d",
                            "text": "Is stakeholder feedback used to inform decision-making?",
                            "required": True
                        }
                    ]
                }
            ]
        }
    ]
}

# Function to create the checklist instances
def create_esg_checklists(env_form_id=None, soc_form_id=None, gov_form_id=None):
    """
    Create the three ESG checklist metrics. If form IDs are not provided,
    this function will only return the data structures without creating database records.
    
    Args:
        env_form_id: Optional ID of the Environmental form
        soc_form_id: Optional ID of the Social form  
        gov_form_id: Optional ID of the Governance form
        
    Returns:
        If form IDs are provided: The three ChecklistMetric instances
        If form IDs are not provided: The three data structures
    """
    from data_management.models.polymorphic_metrics import ChecklistMetric
    from data_management.models.templates import ESGForm
    
    if all([env_form_id, soc_form_id, gov_form_id]):
        try:
            env_form = ESGForm.objects.get(id=env_form_id)
            soc_form = ESGForm.objects.get(id=soc_form_id)
            gov_form = ESGForm.objects.get(id=gov_form_id)
            
            # Create Environmental Checklist
            env_checklist = ChecklistMetric.objects.create(
                name="Environmental Compliance Checklist",
                description="Assessment of environmental policies, systems, and practices",
                checklist_type="ENV",
                form=env_form,
                checklist_structure=ENVIRONMENTAL_CHECKLIST,
                require_remarks_for_no=True,
                enable_scoring=True,
                scoring_method="SIMPLE"
            )
            
            # Create Social Checklist
            soc_checklist = ChecklistMetric.objects.create(
                name="Social Compliance Checklist",
                description="Assessment of social responsibility practices and policies",
                checklist_type="SOC",
                form=soc_form,
                checklist_structure=SOCIAL_CHECKLIST,
                require_remarks_for_no=True,
                enable_scoring=True,
                scoring_method="SIMPLE"
            )
            
            # Create Governance Checklist
            gov_checklist = ChecklistMetric.objects.create(
                name="Governance Compliance Checklist",
                description="Assessment of governance policies and practices",
                checklist_type="GOV",
                form=gov_form,
                checklist_structure=GOVERNANCE_CHECKLIST,
                require_remarks_for_no=True,
                enable_scoring=True,
                scoring_method="SIMPLE"
            )
            
            return env_checklist, soc_checklist, gov_checklist
            
        except ESGForm.DoesNotExist:
            print("One or more of the provided form IDs does not exist.")
            return None
    
    # If no form IDs provided, just return the data structures
    return ENVIRONMENTAL_CHECKLIST, SOCIAL_CHECKLIST, GOVERNANCE_CHECKLIST 