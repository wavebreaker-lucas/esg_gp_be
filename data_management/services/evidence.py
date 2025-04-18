from ..models.templates import ESGMetricEvidence
import logging
from datetime import datetime
# Import the new polymorphic metric models
from ..models.polymorphic_metrics import (
    BaseESGMetric, TimeSeriesMetric, MaterialTrackingMatrixMetric,
    MultiFieldTimeSeriesMetric, VehicleTrackingMetric, FuelConsumptionMetric
)

# Import VehicleRecord with absolute path
from data_management.models.submission_data import VehicleRecord  # Added for direct access
from data_management.models.submission_data import FuelRecord # Added for direct access

# Configure logging to show in console
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def find_relevant_evidence(submission, user=None):
    """
    Find evidence files relevant to a specific submission based on metadata matching.
    
    Args:
        submission: An ESGMetricSubmission object
        user: Optional user to filter by uploaded_by (if None, returns all users' evidence)
        
    Returns:
        QuerySet of ESGMetricEvidence objects
    """
    # Base query on metadata matching
    evidence_query = ESGMetricEvidence.objects.filter(
        intended_metric=submission.metric,
        layer=submission.layer
    )
    
    # If submission has a source_identifier, filter by that too
    if submission.source_identifier:
        evidence_query = evidence_query.filter(source_identifier=submission.source_identifier)
        
    # For time-based metrics, filter by period if available
    if submission.reporting_period:
        evidence_query = evidence_query.filter(period=submission.reporting_period)
        
    # If user is provided, filter by that user
    if user:
        evidence_query = evidence_query.filter(uploaded_by=user)
    
    # Get specific metric instance to check if it's time-based or vehicle-based
    try:
        specific_metric = submission.metric.get_real_instance()
        
        # Check if this is a vehicle tracking metric
        if isinstance(specific_metric, VehicleTrackingMetric):
            # Get all vehicle records associated with this submission
            from django.db.models import Q
            
            # Get the existing filters
            base_query = Q(
                intended_metric=submission.metric,
                layer=submission.layer
            )
            
            # Add source_identifier if present
            if submission.source_identifier:
                base_query &= Q(source_identifier=submission.source_identifier)
                
            # Add period if present
            if submission.reporting_period:
                base_query &= Q(period=submission.reporting_period)
            
            # Add user filter if present
            if user:
                base_query &= Q(uploaded_by=user)
            
            # Create a new query that ORs the base filters with the vehicle filter
            vehicle_query = Q(target_vehicle_id__in=VehicleRecord.objects.filter(
                submission=submission
            ).values_list('id', flat=True))
            
            # Apply the combined filter
            evidence_query = ESGMetricEvidence.objects.filter(
                base_query | vehicle_query
            ).distinct()  # Ensure no duplicates
        
        # --- NEW: Add Fuel Source Check ---
        elif isinstance(specific_metric, FuelConsumptionMetric):
            # Get the base query
            from django.db.models import Q
            base_query = Q(
                intended_metric=submission.metric,
                layer=submission.layer
            )
            
            # Add source_identifier if present
            if submission.source_identifier:
                base_query &= Q(source_identifier=submission.source_identifier)
            
            # Add period if present
            if submission.reporting_period:
                base_query &= Q(period=submission.reporting_period)
            
            # Add user filter if present
            if user:
                base_query &= Q(uploaded_by=user)
            
            # Create a query for matching fuel sources
            fuel_query = Q(target_fuel_source_id__in=FuelRecord.objects.filter(
                submission=submission
            ).values_list('id', flat=True))
            
            # Apply the combined filter
            evidence_query = ESGMetricEvidence.objects.filter(
                base_query | fuel_query
            ).distinct() # Ensure no duplicates
        # --- END: Fuel Source Check ---
        
        # Determine if time-based by checking the type
        is_time_based = isinstance(specific_metric, (
            TimeSeriesMetric,
            MaterialTrackingMatrixMetric,
            MultiFieldTimeSeriesMetric
        ))
        
        # For time-based metrics, we could expand the logic to find evidence 
        # for any period within the submission's time range (if needed)
        
    except (BaseESGMetric.DoesNotExist, AttributeError):
        # If we can't determine the type, just continue with the basic matching
        pass
    
    return evidence_query.select_related('layer', 'intended_metric', 'target_vehicle', 'target_fuel_source') 