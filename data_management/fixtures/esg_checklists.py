"""
Fixture data for ESG Checklists.
This module contains the structured data for creating Environmental, Social, and Governance checklists.
"""

ENVIRONMENTAL_CHECKLIST = {
    "categories": [
        {
            "id": "1.1",
            "name": "EMS管理体系",
            "subcategories": [
                {
                    "name": "EMS管理体系",
                    "items": [
                        {
                            "id": "a",
                            "text": "环境政策是否文件化并易于获取？",
                            "required": True
                        }
                    ]
                },
                {
                    "name": "目标与指标",
                    "items": [
                        {
                            "id": "b",
                            "text": "环境目标与指标是否明确定义？",
                            "required": True
                        },
                        {
                            "id": "c",
                            "text": "是否有达成目标的行动计划？",
                            "required": True
                        }
                    ]
                },
                {
                    "name": "监测与审核",
                    "items": [
                        {
                            "id": "d",
                            "text": "是否定期跟踪环境绩效指标？",
                            "required": True
                        }
                    ]
                }
            ]
        },
        {
            "id": "1.2",
            "name": "能源管理",
            "subcategories": [
                {
                    "name": "能源政策",
                    "items": [
                        {
                            "id": "a",
                            "text": "是否制定能源政策并明确目标与策略？",
                            "required": True
                        },
                        {
                            "id": "b",
                            "text": "是否监测并记录能源消耗情况？",
                            "required": True
                        }
                    ]
                },
                {
                    "name": "能效措施",
                    "items": [
                        {
                            "id": "c",
                            "text": "是否识别并实施能效项目？（如LED照明升级或能源高效设备）",
                            "required": True
                        }
                    ]
                },
                {
                    "name": "可再生能源",
                    "items": [
                        {
                            "id": "d",
                            "text": "是否有增加可再生能源使用的策略？",
                            "required": True
                        }
                    ]
                }
            ]
        },
        {
            "id": "1.3",
            "name": "水资源管理",
            "subcategories": [
                {
                    "name": "节水政策",
                    "items": [
                        {
                            "id": "a",
                            "text": "是否制定节水政策？",
                            "required": True
                        },
                        {
                            "id": "b",
                            "text": "是否设定并传达节水目标？",
                            "required": True
                        }
                    ]
                },
                {
                    "name": "用水监测",
                    "items": [
                        {
                            "id": "c",
                            "text": "是否定期收集并监测用水数据？",
                            "required": True
                        },
                        {
                            "id": "d",
                            "text": "是否设定用水削减基准？",
                            "required": True
                        }
                    ]
                }
            ]
        },
        {
            "id": "1.4",
            "name": "废弃物管理",
            "subcategories": [
                {
                    "name": "废弃物政策",
                    "items": [
                        {
                            "id": "a",
                            "text": "是否制定废弃物管理/减量与回收计划？",
                            "required": True
                        },
                        {
                            "id": "b",
                            "text": "是否定义废弃物减量目标？",
                            "required": True
                        }
                    ]
                },
                {
                    "name": "回收计划",
                    "items": [
                        {
                            "id": "c",
                            "text": "是否实施有效回收计划？",
                            "required": True
                        },
                        {
                            "id": "d",
                            "text": "是否跟踪填埋转移废弃物的比例？",
                            "required": True
                        }
                    ]
                }
            ]
        },
        {
            "id": "1.5",
            "name": "污染排放与气候变化",
            "subcategories": [
                {
                    "name": "排放清单",
                    "items": [
                        {
                            "id": "a",
                            "text": "是否计算组织碳足迹？",
                            "required": True
                        }
                    ]
                },
                {
                    "name": "污染控制措施",
                    "items": [
                        {
                            "id": "b",
                            "text": "是否采用污染控制技术与实践？",
                            "required": True
                        },
                        {
                            "id": "c",
                            "text": "是否有预防或减轻污染（空气、水、土壤）的措施？",
                            "required": True
                        }
                    ]
                },
                {
                    "name": "温室气体减排策略",
                    "items": [
                        {
                            "id": "d",
                            "text": "是否跟踪并计划减少温室气体排放？",
                            "required": True
                        },
                        {
                            "id": "e",
                            "text": "是否有温室气体减排策略？",
                            "required": True
                        }
                    ]
                },
                {
                    "name": "气候适应",
                    "items": [
                        {
                            "id": "f",
                            "text": "组织是否制定适应气候影响的策略？",
                            "required": True
                        }
                    ]
                }
            ]
        },
        {
            "id": "1.6",
            "name": "生物多样性与土地利用",
            "subcategories": [
                {
                    "name": "生物多样性评估",
                    "items": [
                        {
                            "id": "a",
                            "text": "是否对所有运营活动进行生物多样性影响评估？",
                            "required": True
                        },
                        {
                            "id": "b",
                            "text": "是否收集了生物多样性基线数据？",
                            "required": True
                        }
                    ]
                },
                {
                    "name": "栖息地保护",
                    "items": [
                        {
                            "id": "c",
                            "text": "是否制定措施保护当地栖息地和物种？",
                            "required": True
                        },
                        {
                            "id": "d",
                            "text": "是否对退化区域开展生态修复项目？",
                            "required": True
                        }
                    ]
                }
            ]
        },
        {
            "id": "1.7",
            "name": "其他环境指标",
            "subcategories": [
                {
                    "name": "循环经济",
                    "items": [
                        {
                            "id": "a",
                            "text": "是否推行循环经济举措（如产品生命周期管理、资源回收利用）？",
                            "required": True
                        }
                    ]
                },
                {
                    "name": "生态创新",
                    "items": [
                        {
                            "id": "b",
                            "text": "是否开展生态友好型技术与创新研发应用？",
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
            "name": "劳工实践",
            "subcategories": [
                {
                    "name": "雇佣政策",
                    "items": [
                        {
                            "id": "a",
                            "text": "是否制定保障公平劳工的明确雇佣政策？",
                            "required": True
                        },
                        {
                            "id": "b",
                            "text": "劳动合同是否符合劳动法规？",
                            "required": True
                        }
                    ]
                },
                {
                    "name": "工作条件",
                    "items": [
                        {
                            "id": "c",
                            "text": "工作环境是否安全健康？",
                            "required": True
                        },
                        {
                            "id": "d",
                            "text": "是否监控工时与工作条件的合规性？",
                            "required": True
                        }
                    ]
                },
                {
                    "name": "员工权益",
                    "items": [
                        {
                            "id": "e",
                            "text": "员工权益与福利是否得到保障并有效传达？",
                            "required": True
                        },
                        {
                            "id": "f",
                            "text": "是否建立员工申诉机制？",
                            "required": True
                        }
                    ]
                }
            ]
        },
        {
            "id": "2.2",
            "name": "健康安全与客户",
            "subcategories": [
                {
                    "name": "健康安全政策",
                    "items": [
                        {
                            "id": "a",
                            "text": "是否制定健康安全政策？",
                            "required": True
                        },
                        {
                            "id": "b",
                            "text": "是否明确健康安全管理职责？",
                            "required": True
                        },
                        {
                            "id": "c",
                            "text": "是否实施员工身心健康支持计划？",
                            "required": True
                        }
                    ]
                },
                {
                    "name": "事故报告",
                    "items": [
                        {
                            "id": "f",
                            "text": "是否建立事故报告与调查体系？",
                            "required": True
                        },
                        {
                            "id": "g",
                            "text": "是否分析事故数据以预防复发？",
                            "required": True
                        }
                    ]
                }
            ]
        },
        {
            "id": "2.3",
            "name": "多元与包容",
            "subcategories": [
                {
                    "name": "多元化政策",
                    "items": [
                        {
                            "id": "a",
                            "text": "是否制定多元化与包容性政策？",
                            "required": True
                        },
                        {
                            "id": "b",
                            "text": "是否设定、传达并追踪多元化目标？",
                            "required": True
                        }
                    ]
                }
            ]
        },
        {
            "id": "2.4",
            "name": "社区参与",
            "subcategories": [
                {
                    "name": "社区政策",
                    "items": [
                        {
                            "id": "a",
                            "text": "是否制定社区参与政策？",
                            "required": True
                        },
                        {
                            "id": "b",
                            "text": "是否定义社区参与目标？",
                            "required": True
                        }
                    ]
                },
                {
                    "name": "影响评估",
                    "items": [
                        {
                            "id": "c",
                            "text": "是否评估并记录社区影响？",
                            "required": True
                        },
                        {
                            "id": "d",
                            "text": "是否对负面影响实施缓解措施？",
                            "required": True
                        }
                    ]
                },
                {
                    "name": "社区计划",
                    "items": [
                        {
                            "id": "e",
                            "text": "是否开展社区发展支持计划？",
                            "required": True
                        },
                        {
                            "id": "f",
                            "text": "是否建立社区参与成果追踪与报告机制？",
                            "required": True
                        }
                    ]
                }
            ]
        },
        {
            "id": "2.5",
            "name": "人权与供应链",
            "subcategories": [
                {
                    "name": "人权政策",
                    "items": [
                        {
                            "id": "a",
                            "text": "是否制定人权政策？",
                            "required": True
                        },
                        {
                            "id": "b",
                            "text": "政策是否符合国际人权标准？",
                            "required": True
                        }
                    ]
                },
                {
                    "name": "供应链尽职调查",
                    "items": [
                        {
                            "id": "c",
                            "text": "是否要求供应商遵守人权/道德劳工标准？",
                            "required": True
                        },
                        {
                            "id": "d",
                            "text": "所有采购材料及产品是否可持续？",
                            "required": True
                        }
                    ]
                }
            ]
        },
        {
            "id": "2.6",
            "name": "员工培训与发展",
            "subcategories": [
                {
                    "name": "培训计划",
                    "items": [
                        {
                            "id": "a",
                            "text": "是否为员工提供培训发展计划？",
                            "required": True
                        },
                        {
                            "id": "b",
                            "text": "是否定期评估培训需求？",
                            "required": True
                        }
                    ]
                },
                {
                    "name": "职业发展",
                    "items": [
                        {
                            "id": "c",
                            "text": "是否提供职业发展机会？",
                            "required": True
                        }
                    ]
                },
                {
                    "name": "员工参与",
                    "items": [
                        {
                            "id": "d",
                            "text": "是否推行员工持股和决策参与机制？",
                            "required": True
                        }
                    ]
                }
            ]
        },
        {
            "id": "2.7",
            "name": "供应链管理",
            "subcategories": [
                {
                    "name": "供应商选择",
                    "items": [
                        {
                            "id": "a",
                            "text": "供应商筛选是否包含ESG标准？",
                            "required": True
                        },
                        {
                            "id": "b",
                            "text": "是否评估供应商ESG绩效？",
                            "required": True
                        }
                    ]
                },
                {
                    "name": "供应链监控",
                    "items": [
                        {
                            "id": "c",
                            "text": "是否监控供应链ESG合规性？",
                            "required": True
                        },
                        {
                            "id": "d",
                            "text": "是否定期开展供应商审计？",
                            "required": True
                        }
                    ]
                }
            ]
        },
        {
            "id": "2.8",
            "name": "产品责任",
            "subcategories": [
                {
                    "name": "产品评估",
                    "items": [
                        {
                            "id": "a",
                            "text": "是否评估产品/服务全生命周期环境与社会影响？",
                            "required": True
                        },
                        {
                            "id": "b",
                            "text": "是否记录产品/服务影响评估结果？",
                            "required": True
                        }
                    ]
                },
                {
                    "name": "产品安全",
                    "items": [
                        {
                            "id": "c",
                            "text": "是否制定并执行产品安全标准？",
                            "required": True
                        },
                        {
                            "id": "d",
                            "text": "是否及时追踪处理安全事故？",
                            "required": True
                        }
                    ]
                },
                {
                    "name": "客户反馈",
                    "items": [
                        {
                            "id": "e",
                            "text": "是否建立客户反馈收集与处理流程？",
                            "required": True
                        },
                        {
                            "id": "f",
                            "text": "客户投诉是否得到有效管理？",
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
            "name": "道德与合规",
            "subcategories": [
                {
                    "name": "道德政策",
                    "items": [
                        {
                            "id": "a",
                            "text": "是否制定《道德行为准则》或类似规范？",
                            "required": True
                        },
                        {
                            "id": "b",
                            "text": "是否向全体员工宣贯道德政策？",
                            "required": True
                        }
                    ]
                },
                {
                    "name": "合规计划",
                    "items": [
                        {
                            "id": "c",
                            "text": "是否建立确保法律法规合规的程序？",
                            "required": True
                        },
                        {
                            "id": "d",
                            "text": "是否设立举报人政策及保护机制？",
                            "required": True
                        }
                    ]
                },
                {
                    "name": "反腐败措施",
                    "items": [
                        {
                            "id": "e",
                            "text": "是否实施反腐败政策？",
                            "required": True
                        },
                        {
                            "id": "f",
                            "text": "是否评估并防控腐败风险？",
                            "required": True
                        }
                    ]
                }
            ]
        },
        {
            "id": "3.4",
            "name": "透明度与信息披露",
            "subcategories": [
                {
                    "name": "财务报告",
                    "items": [
                        {
                            "id": "a",
                            "text": "财务报表是否透明准确？",
                            "required": True
                        },
                        {
                            "id": "b",
                            "text": "财务报告是否经独立审计机构审计？",
                            "required": True
                        }
                    ]
                },
                {
                    "name": "利益相关方沟通",
                    "items": [
                        {
                            "id": "c",
                            "text": "利益相关方沟通",
                            "required": True
                        },
                        {
                            "id": "d",
                            "text": "是否透明回应利益相关方诉求与反馈？",
                            "required": True
                        }
                    ]
                }
            ]
        },
        {
            "id": "3.5",
            "name": "利益相关方参与",
            "subcategories": [
                {
                    "name": "利益相关方识别",
                    "items": [
                        {
                            "id": "a",
                            "text": "是否识别并梳理关键利益相关方？",
                            "required": True
                        },
                        {
                            "id": "b",
                            "text": "是否记录利益相关方关注议题？",
                            "required": True
                        }
                    ]
                },
                {
                    "name": "反馈机制",
                    "items": [
                        {
                            "id": "c",
                            "text": "是否建立利益相关方反馈渠道？",
                            "required": True
                        },
                        {
                            "id": "d",
                            "text": "是否将反馈意见纳入决策考量？",
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
                name="ESG绩效评估清单 - 环境标准",
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
                name="ESG绩效评估清单 - 社会标准",
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
                name="ESG绩效评估清单 - 治理标准",
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