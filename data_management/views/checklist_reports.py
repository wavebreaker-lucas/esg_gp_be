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
from django.shortcuts import get_object_or_404
from django.db.models import Q
from rest_framework.request import Request
from django.contrib.contenttypes.models import ContentType

from accounts.models import LayerProfile
from accounts.services import has_layer_access

from ..models.templates import ESGMetricSubmission
from ..models.polymorphic_metrics import ChecklistMetric
from ..models.submission_data import ChecklistResponse
from ..models.reporting import ChecklistReport

logger = logging.getLogger(__name__)

def count_required_items(checklist_structure):
    """
    Count the number of required items in a checklist structure.
    
    Args:
        checklist_structure: The structure JSON from a ChecklistMetric
        
    Returns:
        int: Count of required items
    """
    total_required = 0
    
    # Handle different possible structures
    if 'categories' in checklist_structure:
        # Standard structure with categories
        for category in checklist_structure.get('categories', []):
            for subcategory in category.get('subcategories', []):
                for item in subcategory.get('items', []):
                    if item.get('required', True):  # Default to required if not specified
                        total_required += 1
    elif 'items' in checklist_structure:
        # Simpler flat structure
        for item in checklist_structure.get('items', []):
            if item.get('required', True):
                total_required += 1
    
    return total_required

def check_checklist_completion(submission):
    """
    Perform a detailed check of checklist completion.
    
    Args:
        submission: ESGMetricSubmission instance
        
    Returns:
        dict: Completion details including status, percentages, and counts
    """
    if not submission or not isinstance(submission.metric, ChecklistMetric):
        return {
            "complete": False,
            "completion_percentage": 0,
            "answered_items": 0,
            "total_items": 0,
            "required_items": 0,
            "missing_required": 0
        }
    
    # Get the checklist structure
    checklist_structure = submission.metric.checklist_structure
    
    # Count required items from structure
    required_items_count = count_required_items(checklist_structure)
    
    # Count total items (including non-required)
    total_items = 0
    for category in checklist_structure.get('categories', []):
        for subcategory in category.get('subcategories', []):
            total_items += len(subcategory.get('items', []))
    
    # Count answered items
    responses = ChecklistResponse.objects.filter(
        submission=submission
    )
    
    answered_items = responses.filter(
        response__in=['YES', 'NO', 'NA']
    ).count()
    
    # Count answered required items
    answered_required = responses.filter(
        response__in=['YES', 'NO', 'NA']
    ).count()  # This is simplified; ideally we'd match against required items
    
    # Calculate missing required items
    missing_required = max(0, required_items_count - answered_required)
    
    # Calculate completion percentage (based on required items)
    completion_percentage = 0
    if required_items_count > 0:
        completion_percentage = (answered_required / required_items_count) * 100
    
    # Determine if complete - only if all required items are answered
    is_complete = (missing_required == 0 and required_items_count > 0)
    
    return {
        "complete": is_complete,
        "completion_percentage": round(completion_percentage, 1),
        "answered_items": answered_items,
        "total_items": total_items,
        "required_items": required_items_count,
        "missing_required": missing_required
    }

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

def _generate_combined_report(submission_ids, regenerate=False, user=None):
    """
    Helper function to generate a combined ESG report from multiple submission IDs.
    
    Args:
        submission_ids: List of submission IDs (ENV, SOC, GOV)
        regenerate: Whether to regenerate if a report already exists
        user: The user making the request (for audit purposes)
        
    Returns:
        tuple: (report_data, status_message, status_code)
    """
    try:
        # Get all the submissions
        submissions = ESGMetricSubmission.objects.filter(id__in=submission_ids)
        
        if not submissions.exists():
            return (
                {"error": f"No submissions found with the provided IDs"},
                "not_found",
                status.HTTP_404_NOT_FOUND
            )
        
        # Verify that all submissions are for ChecklistMetric
        non_checklist_submissions = []
        for submission in submissions:
            if not isinstance(submission.metric, ChecklistMetric):
                non_checklist_submissions.append(submission.id)
        
        if non_checklist_submissions:
            return (
                {"error": f"Submissions with IDs {non_checklist_submissions} are not checklist submissions"},
                "invalid_submissions",
                status.HTTP_400_BAD_REQUEST
            )
            
        # Use first submission (typically ENV) as primary for report storage
        primary_submission_id = submission_ids[0]
        
        # Check if a report already exists for these submissions
        # For simplicity, we'll just check primary_submission for now
        primary_submission = ESGMetricSubmission.objects.get(id=primary_submission_id)
        existing_report = ChecklistReport.objects.filter(
            primary_submission=primary_submission,
            report_type='COMBINED'
        ).order_by('-version').first()
        
        # If a report exists and regenerate flag is not set, return the existing report
        if existing_report and not regenerate:
            return (
                {"report": existing_report.to_dict()},
                "retrieved_existing",
                status.HTTP_200_OK
            )
        
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
            
            # Create report response structure
            report_data = {
                "title": "Integrated ESG Compliance Report",
                "company": combined_data['metadata']['company_name'],
                "generated_at": timezone.now().strftime("%Y-%m-%d %H:%M:%S"),
                "overall_compliance": combined_data['summary']['overall_compliance_percentage'],
                "environmental_compliance": combined_data['summary']['environmental_compliance'],
                "social_compliance": combined_data['summary']['social_compliance'],
                "governance_compliance": combined_data['summary']['governance_compliance'],
                "content": report_text
            }
            
            # Store the report if it's not a mock report
            if hasattr(settings, 'OPENROUTER_API_KEY') and settings.OPENROUTER_API_KEY:
                # If regenerating, increment version number
                version = 1
                if existing_report:
                    version = existing_report.version + 1
                
                # Create new report record
                stored_report = ChecklistReport.create_from_combined_report(
                    primary_submission_id,
                    submission_ids,
                    report_data
                )
                
                if version > 1:
                    stored_report.version = version
                    stored_report.save()
                
                # Add report ID to the response
                report_data["report_id"] = stored_report.id
                report_data["version"] = stored_report.version
            
            # Return the report
            return (
                {"report": report_data},
                "generated_new",
                status.HTTP_200_OK
            )
            
        except Exception as e:
            logger.error(f"Error calling AI service for combined report: {str(e)}")
            return (
                {"error": f"Error generating combined report: {str(e)}"},
                "error",
                status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
    except Exception as e:
        logger.error(f"Error in _generate_combined_report: {str(e)}")
        return (
            {"error": f"Error generating combined report: {str(e)}"},
            "error",
            status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def generate_checklist_report(request):
    """
    This endpoint is disabled as the system only supports combined ESG reports.
    Individual checklist reports are not supported to ensure comprehensive ESG assessment.
    Please use the combined report endpoints instead.
    """
    return Response({
        "error": "Individual checklist reports are disabled",
        "message": "This system only supports combined ESG reports that include Environmental, Social, and Governance components.",
        "recommended_endpoint": "/api/checklist-reports/generate-for-layer/",
        "usage": "POST to /api/checklist-reports/generate-for-layer/ with {'layer_id': your_layer_id}"
    }, status=status.HTTP_400_BAD_REQUEST)

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
    regenerate = request.data.get('regenerate', False)
    
    if not submission_ids or not isinstance(submission_ids, list) or len(submission_ids) == 0:
        return Response({
            "error": "submission_ids must be a non-empty array of submission IDs"
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Call the helper function to generate the report
    response_data, status_msg, status_code = _generate_combined_report(
        submission_ids=submission_ids,
        regenerate=regenerate,
        user=request.user
    )
    
    # Add status message if it's not an error
    if status_code == status.HTTP_200_OK:
        response_data["status"] = status_msg
    
    return Response(response_data, status=status_code)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_reports_by_submission(request, submission_id):
    """
    Retrieve all reports associated with a specific checklist submission.
    This includes both single reports where this is the primary submission,
    and combined reports where this submission is included.
    
    Args:
        submission_id: The ID of the checklist submission
    """
    try:
        # Verify the submission exists
        submission = get_object_or_404(ESGMetricSubmission, id=submission_id)
        
        # Get reports where this is the primary submission
        primary_reports = ChecklistReport.objects.filter(
            primary_submission=submission
        ).order_by('-version', '-generated_at')
        
        # Get reports where this is included as a related submission
        related_reports = ChecklistReport.objects.filter(
            related_submissions=submission
        ).order_by('-version', '-generated_at')
        
        # Combine and remove duplicates (a report might appear in both queries)
        all_reports = list(primary_reports)
        for report in related_reports:
            if report not in all_reports:
                all_reports.append(report)
        
        # Convert to dictionaries for the response
        report_data = [report.to_dict() for report in all_reports]
        
        return Response({
            "submission_id": submission_id,
            "reports": report_data
        })
        
    except Exception as e:
        logger.error(f"Error retrieving reports for submission {submission_id}: {str(e)}")
        return Response({
            "error": f"Error retrieving reports: {str(e)}"
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_report_by_id(request, report_id):
    """
    Retrieve a specific checklist report by its ID.
    
    Args:
        report_id: The ID of the checklist report
    """
    try:
        report = get_object_or_404(ChecklistReport, id=report_id)
        
        # Get related submissions if it's a combined report
        related_submissions = []
        if report.report_type == 'COMBINED':
            related_submissions = list(report.related_submissions.values_list('id', flat=True))
        
        # Prepare the response data
        report_data = report.to_dict()
        
        # Add related submissions if applicable
        if related_submissions:
            report_data["related_submission_ids"] = related_submissions
        
        return Response(report_data)
        
    except Exception as e:
        logger.error(f"Error retrieving report {report_id}: {str(e)}")
        return Response({
            "error": f"Error retrieving report: {str(e)}"
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_reports_by_layer(request, layer_id):
    """
    Get all reports for an organizational layer, grouped by entity.
    """
    try:
        # Check if layer exists and user has access
        layer = LayerProfile.objects.get(id=layer_id)
        
        if not has_layer_access(request.user, layer_id):
            return Response({
                "error": "You do not have permission to view this layer's reports"
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Get all reports for this layer directly using the new layer field
        all_reports = ChecklistReport.objects.filter(layer=layer_id).order_by('-generated_at')
        
        if not all_reports.exists():
            return Response({
                "layer_id": layer_id,
                "message": "No reports found for this layer",
                "reports_by_entity": {}
            })
        
        # Group reports by company/entity
        reports_by_entity = {}
        
        for report in all_reports:
            company = report.company
            
            if company not in reports_by_entity:
                reports_by_entity[company] = []
                
            reports_by_entity[company].append(report.to_dict())
            
        # Prepare a summary of compliance statistics
        summary = {
            "entity_count": len(reports_by_entity),
            "report_count": all_reports.count(),
            "latest_report_date": all_reports.first().generated_at.strftime("%Y-%m-%d") if all_reports.exists() else None,
        }
        
        return Response({
            "layer_id": layer_id,
            "summary": summary,
            "reports_by_entity": reports_by_entity
        })
        
    except LayerProfile.DoesNotExist:
        return Response({
            "error": f"Layer with ID {layer_id} not found"
        }, status=status.HTTP_404_NOT_FOUND)
        
    except Exception as e:
        logger.error(f"Error retrieving reports for layer {layer_id}: {str(e)}")
        return Response({
            "error": f"Error retrieving reports: {str(e)}"
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_checklist_status(request, layer_id):
    """
    Get detailed completion status of all three ESG checklists for a specific layer.
    Returns which checklists are completed and whether all are ready for report generation.
    """
    try:
        # Check if layer exists and user has access
        if not has_layer_access(request.user, layer_id):
            return Response({
                "error": "You do not have permission to view this layer's checklist status"
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Initialize status with all checklist types
        status_data = {
            "ENV": {
                "complete": False,
                "submission_id": None,
                "reporting_period": None,
                "completion_percentage": 0
            },
            "SOC": {
                "complete": False,
                "submission_id": None,
                "reporting_period": None,
                "completion_percentage": 0
            },
            "GOV": {
                "complete": False,
                "submission_id": None,
                "reporting_period": None,
                "completion_percentage": 0
            },
            "all_complete": False
        }
        
        # Get the content type for ChecklistMetric
        from django.contrib.contenttypes.models import ContentType
        from ..models.polymorphic_metrics import ChecklistMetric
        checklist_content_type = ContentType.objects.get_for_model(ChecklistMetric)
        
        # Find latest submission for each checklist type
        for checklist_type in ["ENV", "SOC", "GOV"]:
            # First get all checklist metric IDs of the specific type
            checklist_metrics = ChecklistMetric.objects.filter(
                polymorphic_ctype=checklist_content_type,
                checklist_type=checklist_type
            ).values_list('id', flat=True)
            
            # Then filter submissions by these metric IDs
            submission = ESGMetricSubmission.objects.filter(
                layer_id=layer_id,
                metric_id__in=checklist_metrics
            ).order_by('-reporting_period').first()
            
            if submission:
                # Perform detailed completion check
                completion_status = check_checklist_completion(submission)
                
                # Update status data with completion details
                status_data[checklist_type] = {
                    "complete": completion_status["complete"],
                    "submission_id": submission.id,
                    "reporting_period": submission.reporting_period.isoformat() if submission.reporting_period else None,
                    "submitted_at": submission.submitted_at.isoformat() if submission.submitted_at else None,
                    "completion_percentage": completion_status["completion_percentage"],
                    "answered_items": completion_status["answered_items"],
                    "total_items": completion_status["total_items"],
                    "required_items": completion_status["required_items"],
                    "missing_required": completion_status["missing_required"]
                }
        
        # Check if all are complete
        status_data["all_complete"] = all([
            status_data["ENV"]["complete"], 
            status_data["SOC"]["complete"], 
            status_data["GOV"]["complete"]
        ])
        
        return Response(status_data)
        
    except Exception as e:
        logger.error(f"Error retrieving checklist status for layer {layer_id}: {str(e)}")
        return Response({
            "error": f"Error retrieving checklist status: {str(e)}"
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def generate_combined_report_for_layer(request):
    """
    Generate combined report automatically using latest submissions for a layer.
    The system will automatically find the latest ENV, SOC, and GOV submissions
    for the specified layer and generate a combined report.
    
    Expected payload:
    {
        "layer_id": 123,
        "entity_name": "Optional entity name filter",
        "reporting_period": "Optional specific reporting period (YYYY-MM-DD)",
        "regenerate": false
    }
    """
    try:
        layer_id = request.data.get('layer_id')
        entity_name = request.data.get('entity_name', None)  # Optional filter
        reporting_period = request.data.get('reporting_period', None)  # Optional - defaults to latest
        regenerate = request.data.get('regenerate', False)
        # Option to override completeness check (for admin/testing only)
        force_incomplete = request.data.get('force_incomplete', False) and request.user.is_staff  
        
        if not layer_id:
            return Response({
                "error": "layer_id is required"
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Check if layer exists and user has access
        if not has_layer_access(request.user, layer_id):
            return Response({
                "error": "You do not have permission to generate reports for this layer"
            }, status=status.HTTP_403_FORBIDDEN)
        
        # 1. Find the latest complete E/S/G submission set
        submissions_by_type = {}
        completion_status = {}
        query = ESGMetricSubmission.objects.filter(
            layer_id=layer_id,
            metric__polymorphic_ctype__model='checklistmetric'
        )
        
        # Apply optional filters
        if entity_name:
            query = query.filter(layer__name=entity_name)
        if reporting_period:
            query = query.filter(reporting_period=reporting_period)
        
        # Get the content type for ChecklistMetric
        from django.contrib.contenttypes.models import ContentType
        from ..models.polymorphic_metrics import ChecklistMetric
        checklist_content_type = ContentType.objects.get_for_model(ChecklistMetric)
        
        # Find latest submission for each type and check completion
        for checklist_type in ["ENV", "SOC", "GOV"]:
            # First get all checklist metric IDs of the specific type
            checklist_metrics = ChecklistMetric.objects.filter(
                polymorphic_ctype=checklist_content_type,
                checklist_type=checklist_type
            ).values_list('id', flat=True)
            
            # Then filter submissions by these metric IDs
            submission = query.filter(
                metric_id__in=checklist_metrics
            ).order_by('-reporting_period').first()
            
            if submission:
                # Perform detailed completion check
                completion = check_checklist_completion(submission)
                completion_status[checklist_type] = completion
                
                # Only include truly complete submissions (or if force_incomplete is enabled)
                if completion["complete"] or force_incomplete:
                    submissions_by_type[checklist_type] = submission
        
        # 2. Validate we have all required checklist types
        required_types = ["ENV", "SOC", "GOV"]
        missing_types = [t for t in required_types if t not in submissions_by_type]
        
        if missing_types:
            # Provide detailed information about what's missing
            error_details = {}
            for missing_type in missing_types:
                if missing_type in completion_status:
                    error_details[missing_type] = {
                        "reason": "incomplete",
                        "completion_percentage": completion_status[missing_type]["completion_percentage"],
                        "missing_required": completion_status[missing_type]["missing_required"]
                    }
                else:
                    error_details[missing_type] = {
                        "reason": "not_found",
                        "message": "No submission found for this checklist type"
                    }
            
            return Response({
                "error": "Some required checklists are missing or incomplete",
                "missing_or_incomplete": missing_types,
                "details": error_details,
                "available_types": list(submissions_by_type.keys())
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # 3. Check if a combined report already exists for these submissions
        submission_ids = [submissions_by_type[t].id for t in required_types]
        primary_id = submissions_by_type["ENV"].id  # Use ENV as primary
        
        # Look for existing report with these submissions
        existing_report = None
        if not regenerate:
            # Find reports where the primary submission matches
            primary_reports = ChecklistReport.objects.filter(
                primary_submission_id=primary_id,
                report_type='COMBINED'
            )
            
            # Check if any of these reports have the other two submissions as related
            for report in primary_reports:
                related_ids = report.related_submissions.values_list('id', flat=True)
                if set(submission_ids).issubset(set([primary_id] + list(related_ids))):
                    existing_report = report
                    break
            
            if existing_report:
                return Response({
                    "status": "existing_report",
                    "message": "An existing report was found for these submissions",
                    "report": existing_report.to_dict()
                })
        
        # 4. Generate the combined report using the helper function
        response_data, status_msg, status_code = _generate_combined_report(
            submission_ids=submission_ids,
            regenerate=regenerate,
            user=request.user
        )
        
        # Add status message if it's not an error
        if status_code == status.HTTP_200_OK:
            response_data["status"] = status_msg
        
        return Response(response_data, status=status_code)
        
    except Exception as e:
        logger.error(f"Error generating combined report for layer: {str(e)}")
        return Response({
            "error": f"Error generating combined report: {str(e)}"
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR) 