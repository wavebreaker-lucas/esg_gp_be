"""
Views for generating reports from checklist data.
"""

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
import logging
import json
from openai import OpenAI
from django.conf import settings
from django.utils import timezone

from ..models.templates import ESGMetricSubmission
from ..models.polymorphic_metrics import ChecklistMetric
from ..models.submission_data import ChecklistResponse

logger = logging.getLogger(__name__)

def prepare_checklist_data_for_ai(submission):
    """
    Prepare checklist submission data in a format optimized for AI processing.
    
    Args:
        submission: An ESGMetricSubmission instance for a ChecklistMetric
        
    Returns:
        A structured dictionary with checklist data
    """
    # Get the metric and verify it's a ChecklistMetric
    metric = submission.metric
    if not isinstance(metric, ChecklistMetric):
        raise ValueError("Submission must be for a ChecklistMetric")
    
    # Get all responses for this submission
    responses = ChecklistResponse.objects.filter(submission=submission)
    
    # Prepare metadata
    metadata = {
        "submission_id": submission.id,
        "company_name": submission.assignment.entity.name if hasattr(submission.assignment, 'entity') else "Unknown",
        "reporting_period": submission.reporting_period.strftime("%Y-%m-%d") if submission.reporting_period else "Unknown",
        "submitted_at": submission.submitted_at.strftime("%Y-%m-%d %H:%M:%S") if submission.submitted_at else "Unknown",
        "submitted_by": str(submission.submitted_by) if submission.submitted_by else "Unknown",
        "checklist_type": metric.get_checklist_type_display(),
        "checklist_name": metric.name
    }
    
    # Group responses by category and subcategory
    categorized_responses = {}
    
    for response in responses:
        category_id = response.category_id
        subcategory_name = response.subcategory_name
        
        if category_id not in categorized_responses:
            categorized_responses[category_id] = {
                "name": "",  # Will be set from checklist structure
                "subcategories": {}
            }
            
        if subcategory_name not in categorized_responses[category_id]["subcategories"]:
            categorized_responses[category_id]["subcategories"][subcategory_name] = {
                "items": []
            }
            
        categorized_responses[category_id]["subcategories"][subcategory_name]["items"].append({
            "id": response.item_id,
            "text": response.item_text,
            "response": response.response,
            "remarks": response.remarks
        })
    
    # Find category names from the checklist structure
    for category in metric.checklist_structure.get("categories", []):
        category_id = category.get("id")
        if category_id in categorized_responses:
            categorized_responses[category_id]["name"] = category.get("name", "")
    
    # Convert the nested dict to a list structure for easier processing
    categories = []
    for category_id, category_data in categorized_responses.items():
        subcategories = []
        for subcategory_name, subcategory_data in category_data["subcategories"].items():
            subcategories.append({
                "name": subcategory_name,
                "items": subcategory_data["items"]
            })
            
        categories.append({
            "id": category_id,
            "name": category_data["name"],
            "subcategories": subcategories
        })
    
    # Calculate summary statistics
    total_items = 0
    yes_count = 0
    no_count = 0
    na_count = 0
    
    for category in categories:
        for subcategory in category["subcategories"]:
            for item in subcategory["items"]:
                total_items += 1
                if item["response"] == "YES":
                    yes_count += 1
                elif item["response"] == "NO":
                    no_count += 1
                elif item["response"] == "NA":
                    na_count += 1
    
    compliance_percentage = round((yes_count / total_items) * 100, 2) if total_items > 0 else 0
    
    # Final structure
    return {
        "metadata": metadata,
        "summary": {
            "total_items": total_items,
            "yes_count": yes_count,
            "no_count": no_count,
            "na_count": na_count,
            "compliance_percentage": compliance_percentage
        },
        "categories": categories
    }

def prepare_combined_checklist_data(submissions):
    """
    Prepare and combine data from multiple checklist submissions (E, S, G).
    
    Args:
        submissions: A list of ESGMetricSubmission instances
        
    Returns:
        A structured dictionary with combined checklist data
    """
    if not submissions:
        raise ValueError("No submissions provided")
    
    # Organize by checklist type (ENV, SOC, GOV)
    organized_data = {
        "ENV": None,
        "SOC": None,
        "GOV": None
    }
    
    # Process each submission
    total_items = 0
    total_yes = 0
    total_no = 0
    total_na = 0
    
    # Determine company and reporting period from first submission
    company_name = "Unknown"
    reporting_period = "Unknown"
    submission_ids = []
    
    for submission in submissions:
        if not isinstance(submission.metric, ChecklistMetric):
            continue
            
        checklist_type = submission.metric.checklist_type
        submission_data = prepare_checklist_data_for_ai(submission)
        
        # Store the submission data by type
        organized_data[checklist_type] = submission_data
        
        # Update overall statistics
        total_items += submission_data["summary"]["total_items"]
        total_yes += submission_data["summary"]["yes_count"]
        total_no += submission_data["summary"]["no_count"]
        total_na += submission_data["summary"]["na_count"]
        
        # Collect metadata from the first valid submission
        if company_name == "Unknown" and "company_name" in submission_data["metadata"]:
            company_name = submission_data["metadata"]["company_name"]
            
        if reporting_period == "Unknown" and "reporting_period" in submission_data["metadata"]:
            reporting_period = submission_data["metadata"]["reporting_period"]
            
        submission_ids.append(submission.id)
    
    # Calculate overall compliance percentage
    overall_compliance = round((total_yes / total_items) * 100, 2) if total_items > 0 else 0
    
    # Create combined structure
    combined_data = {
        "metadata": {
            "submission_ids": submission_ids,
            "company_name": company_name,
            "reporting_period": reporting_period,
            "generated_at": timezone.now().strftime("%Y-%m-%d %H:%M:%S")
        },
        "summary": {
            "total_items": total_items,
            "yes_count": total_yes,
            "no_count": total_no,
            "na_count": total_na,
            "overall_compliance_percentage": overall_compliance,
            "environmental_compliance": organized_data["ENV"]["summary"]["compliance_percentage"] if organized_data["ENV"] else None,
            "social_compliance": organized_data["SOC"]["summary"]["compliance_percentage"] if organized_data["SOC"] else None,
            "governance_compliance": organized_data["GOV"]["summary"]["compliance_percentage"] if organized_data["GOV"] else None
        },
        "checklists": {
            "environmental": organized_data["ENV"],
            "social": organized_data["SOC"],
            "governance": organized_data["GOV"]
        }
    }
    
    return combined_data

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def generate_checklist_report(request):
    """
    Generate an AI report based on checklist submission data.
    
    Expected payload:
    {
        "submission_id": 123
    }
    """
    submission_id = request.data.get('submission_id')
    
    if not submission_id:
        return Response({
            "error": "submission_id is required"
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        # Get the submission
        submission = ESGMetricSubmission.objects.get(id=submission_id)
        
        # Check if the submission is for a ChecklistMetric
        if not isinstance(submission.metric, ChecklistMetric):
            return Response({
                "error": "Submission must be for a ChecklistMetric"
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Prepare checklist data for AI
        checklist_data = prepare_checklist_data_for_ai(submission)
        
        # Unified prompt that combines elements from all three report types
        unified_prompt = (
            "Generate a comprehensive ESG report based on the following compliance checklist data. "
            "The report should include:\n\n"
            "1. Executive Summary: Provide a concise overview of the overall compliance status, "
            "highlighting the compliance percentage, major strengths, and critical areas for improvement.\n\n"
            "2. Key Findings: Analyze the performance in each major category, identifying patterns "
            "and notable observations.\n\n"
            "3. Improvement Plan: Identify items marked as 'NO', prioritize them by importance, "
            "and provide specific, actionable recommendations to address each gap.\n\n"
            "4. Conclusion: Summarize the overall ESG performance and provide strategic recommendations "
            "for ongoing improvement.\n\n"
            "The report should be well-structured, professional, and provide actionable insights. "
            "Focus on practical implementation guidance for addressing compliance gaps."
        )
        
        # Prepare data for OpenAI
        try:
            # If no API settings are configured, return mock data for development
            if not hasattr(settings, 'OPENROUTER_API_KEY') or not settings.OPENROUTER_API_KEY:
                report_text = f"[MOCK REPORT - No OpenRouter API key configured]\n\n" \
                             f"ESG Report for {checklist_data['metadata']['company_name']}\n" \
                             f"Overall Compliance: {checklist_data['summary']['compliance_percentage']}%\n\n" \
                             f"This is a placeholder for the unified ESG report."
            else:
                # Configure OpenAI client with OpenRouter settings
                client = OpenAI(
                    base_url="https://openrouter.ai/api/v1",
                    api_key=settings.OPENROUTER_API_KEY,
                )
                
                # Call OpenAI API (with OpenRouter configuration)
                completion = client.chat.completions.create(
                    extra_headers={
                        "HTTP-Referer": settings.SITE_URL if hasattr(settings, 'SITE_URL') else "https://esg-platform.example.com",
                        "X-Title": "ESG Platform API" 
                    },
                    # Choose an appropriate model - using a default if not specified
                    model=getattr(settings, 'OPENROUTER_MODEL', "google/gemini-pro"),
                    messages=[
                        {"role": "system", "content": "You are an ESG reporting specialist who analyzes compliance data and generates professional, actionable reports."},
                        {"role": "user", "content": f"{unified_prompt}\n\nCHECKLIST DATA:\n{json.dumps(checklist_data, indent=2)}"}
                    ],
                    temperature=0.2,  # Low temperature for more consistent reporting
                    max_tokens=4000  # Adjust based on report length needs
                )
                
                report_text = completion.choices[0].message.content
            
            # Return the report
            return Response({
                "report": {
                    "title": f"{checklist_data['metadata']['checklist_type']} Compliance Report",
                    "company": checklist_data['metadata']['company_name'],
                    "generated_at": timezone.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "compliance_percentage": checklist_data['summary']['compliance_percentage'],
                    "content": report_text
                }
            })
            
        except Exception as e:
            logger.error(f"Error calling AI service: {str(e)}")
            return Response({
                "error": f"Error generating report: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
    except ESGMetricSubmission.DoesNotExist:
        return Response({
            "error": f"Submission with ID {submission_id} not found"
        }, status=status.HTTP_404_NOT_FOUND)
    
    except Exception as e:
        logger.error(f"Error in generate_checklist_report: {str(e)}")
        return Response({
            "error": f"Error generating report: {str(e)}"
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def generate_combined_checklist_report(request):
    """
    Generate a comprehensive ESG report that combines data from multiple checklist submissions.
    Typically this would include Environmental, Social, and Governance checklists.
    
    Expected payload:
    {
        "submission_ids": [123, 124, 125]  // E, S, G submission IDs
    }
    """
    submission_ids = request.data.get('submission_ids', [])
    
    if not submission_ids or not isinstance(submission_ids, list) or len(submission_ids) == 0:
        return Response({
            "error": "submission_ids must be a non-empty array of submission IDs"
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        # Get all the submissions
        submissions = ESGMetricSubmission.objects.filter(id__in=submission_ids)
        
        if not submissions.exists():
            return Response({
                "error": f"No submissions found with the provided IDs"
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Verify that all submissions are for ChecklistMetric
        non_checklist_submissions = []
        for submission in submissions:
            if not isinstance(submission.metric, ChecklistMetric):
                non_checklist_submissions.append(submission.id)
        
        if non_checklist_submissions:
            return Response({
                "error": f"Submissions with IDs {non_checklist_submissions} are not checklist submissions"
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Prepare combined checklist data
        combined_data = prepare_combined_checklist_data(submissions)
        
        # Unified prompt for combined ESG report
        combined_prompt = (
            "Generate a comprehensive integrated ESG report that analyzes data from Environmental, "
            "Social, and Governance checklists together. The report should include:\n\n"
            "1. Executive Summary: Provide a concise overview of the overall ESG compliance status, "
            "with separate sections highlighting Environmental, Social, and Governance performance. "
            "Include the overall compliance percentage and comparison between E, S, and G areas.\n\n"
            "2. Performance by ESG Pillar: Analyze each pillar (Environmental, Social, Governance) "
            "separately, highlighting key strengths and weaknesses in each area.\n\n"
            "3. Key Findings: Identify patterns across all three pillars, noting any correlations or "
            "systemic issues that span multiple ESG areas.\n\n"
            "4. Strategic Improvement Plan: Prioritize the most critical gaps across all three areas, "
            "providing specific, actionable recommendations with implementation guidance.\n\n"
            "5. Conclusion: Provide a holistic assessment of the company's ESG maturity and strategic "
            "recommendations for integrated ESG improvement.\n\n"
            "The report should be well-structured, professional, and provide actionable insights "
            "while considering the interconnections between Environmental, Social, and Governance factors."
        )
        
        # Prepare data for OpenAI
        try:
            # If no API settings are configured, return mock data for development
            if not hasattr(settings, 'OPENROUTER_API_KEY') or not settings.OPENROUTER_API_KEY:
                report_text = f"[MOCK REPORT - No OpenRouter API key configured]\n\n" \
                             f"Integrated ESG Report for {combined_data['metadata']['company_name']}\n" \
                             f"Overall Compliance: {combined_data['summary']['overall_compliance_percentage']}%\n" \
                             f"Environmental: {combined_data['summary']['environmental_compliance']}%\n" \
                             f"Social: {combined_data['summary']['social_compliance']}%\n" \
                             f"Governance: {combined_data['summary']['governance_compliance']}%\n\n" \
                             f"This is a placeholder for the combined ESG report."
            else:
                # Configure OpenAI client with OpenRouter settings
                client = OpenAI(
                    base_url="https://openrouter.ai/api/v1",
                    api_key=settings.OPENROUTER_API_KEY,
                )
                
                # Call OpenAI API (with OpenRouter configuration)
                completion = client.chat.completions.create(
                    extra_headers={
                        "HTTP-Referer": settings.SITE_URL if hasattr(settings, 'SITE_URL') else "https://esg-platform.example.com",
                        "X-Title": "ESG Platform API" 
                    },
                    # Choose an appropriate model - using a default if not specified
                    model=getattr(settings, 'OPENROUTER_MODEL', "google/gemini-pro"),
                    messages=[
                        {"role": "system", "content": "You are an ESG reporting specialist who analyzes environmental, social, and governance compliance data to generate comprehensive, integrated ESG reports."},
                        {"role": "user", "content": f"{combined_prompt}\n\nCOMBINED ESG DATA:\n{json.dumps(combined_data, indent=2)}"}
                    ],
                    temperature=0.2,  # Low temperature for more consistent reporting
                    max_tokens=4000  # Adjust based on report length needs
                )
                
                report_text = completion.choices[0].message.content
            
            # Return the report
            return Response({
                "report": {
                    "title": "Integrated ESG Compliance Report",
                    "company": combined_data['metadata']['company_name'],
                    "generated_at": timezone.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "overall_compliance": combined_data['summary']['overall_compliance_percentage'],
                    "environmental_compliance": combined_data['summary']['environmental_compliance'],
                    "social_compliance": combined_data['summary']['social_compliance'],
                    "governance_compliance": combined_data['summary']['governance_compliance'],
                    "content": report_text
                }
            })
            
        except Exception as e:
            logger.error(f"Error calling AI service for combined report: {str(e)}")
            return Response({
                "error": f"Error generating combined report: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
    except Exception as e:
        logger.error(f"Error in generate_combined_checklist_report: {str(e)}")
        return Response({
            "error": f"Error generating combined report: {str(e)}"
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR) 