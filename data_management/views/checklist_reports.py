"""
Views for generating reports from checklist data.
"""

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
import logging
import json
import openai
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

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def generate_checklist_report(request):
    """
    Generate an AI report based on checklist submission data.
    
    Expected payload:
    {
        "submission_id": 123,
        "report_type": "comprehensive" | "executive" | "improvement"
    }
    """
    submission_id = request.data.get('submission_id')
    report_type = request.data.get('report_type', 'comprehensive')
    
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
        
        # Configure prompt based on report type
        prompts = {
            "comprehensive": (
                "Generate a comprehensive ESG report based on the following compliance checklist data. "
                "Include all categories and subcategories, highlighting strengths, weaknesses, and specific "
                "recommendations for improvement. The report should be well-structured with sections for each "
                "major category and clear, actionable insights."
            ),
            "executive": (
                "Generate an executive summary of this ESG compliance checklist data. "
                "Focus on the most critical findings, overall compliance percentage, major strengths, "
                "and priority areas for improvement. Keep it concise and strategic, suitable for executive "
                "leadership review."
            ),
            "improvement": (
                "Generate a focused improvement plan based on this ESG checklist data. "
                "Identify all items marked as 'NO', prioritize them by importance, and provide specific, "
                "actionable recommendations to address each gap. Include implementation guidance and "
                "potential timelines for addressing the issues."
            )
        }
        
        prompt = prompts.get(report_type, prompts["comprehensive"])
        
        # Prepare data for OpenAI
        try:
            # Call OpenAI API
            if not settings.OPENAI_API_KEY:
                # If no API key is configured, return mock data for development
                report_text = f"[MOCK REPORT - No OpenAI API key configured]\n\n" \
                             f"ESG Report for {checklist_data['metadata']['company_name']}\n" \
                             f"Overall Compliance: {checklist_data['summary']['compliance_percentage']}%\n\n" \
                             f"This is a placeholder for the {report_type} report."
            else:
                # Configure OpenAI
                openai.api_key = settings.OPENAI_API_KEY
                
                # Call OpenAI API
                response = openai.ChatCompletion.create(
                    model="gpt-4",
                    messages=[
                        {"role": "system", "content": "You are an ESG reporting specialist who analyzes compliance data and generates professional, actionable reports."},
                        {"role": "user", "content": f"{prompt}\n\nCHECKLIST DATA:\n{json.dumps(checklist_data, indent=2)}"}
                    ],
                    temperature=0.2,  # Low temperature for more consistent reporting
                    max_tokens=4000  # Adjust based on report length needs
                )
                
                report_text = response.choices[0].message.content
            
            # Return the report
            return Response({
                "report": {
                    "title": f"{checklist_data['metadata']['checklist_type']} Compliance Report",
                    "company": checklist_data['metadata']['company_name'],
                    "generated_at": timezone.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "compliance_percentage": checklist_data['summary']['compliance_percentage'],
                    "report_type": report_type,
                    "content": report_text
                }
            })
            
        except Exception as e:
            logger.error(f"Error calling OpenAI API: {str(e)}")
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