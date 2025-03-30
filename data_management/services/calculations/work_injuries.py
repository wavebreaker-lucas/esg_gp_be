"""
Class-based null handler for work injuries metrics.
This handler doesn't perform any calculations since work injuries 
are non-periodic measurements that don't require calculations.
"""

import logging
from .. import calculations
from .base import CalculationHandler

logger = logging.getLogger(__name__)

class WorkInjuriesHandler(CalculationHandler):
    """
    Handler for work injuries metrics.
    This is essentially a null handler that just validates the data structure.
    """
    
    def validate(self, data):
        """
        Validate work injuries data structure.
        
        Args:
            data (dict): The data to validate
            
        Returns:
            bool: Whether the data is valid
        """
        if not data or not isinstance(data, dict):
            return False
            
        # Work injuries should have fiscal_year, deaths, injuries, lost_days
        required_fields = ['fiscal_year', 'deaths', 'injuries', 'lost_days']
        for field in required_fields:
            if field not in data:
                logger.warning(f"Work injuries data missing required field: {field}")
                return False
                
        return True
        
    def calculate(self, data):
        """
        No calculations needed for work injuries data.
        
        Args:
            data (dict): The data to process
            
        Returns:
            dict: The unchanged data
        """
        # Work injuries don't require any calculations
        return data
    
    def process(self, data):
        """
        Process work injuries data (just validation).
        
        Args:
            data (dict): The data to process
            
        Returns:
            dict: The unchanged data
        """
        logger.info("Processing work injuries data (null handler)")
        return super().process(data)

# Create handler instances for both HK and PRC
work_injuries_handler = WorkInjuriesHandler()

# Wrapper functions for the registry
def calculate_work_injuries_hk(data):
    """
    Function wrapper for the HK work injuries handler.
    
    Args:
        data (dict): The data to process
        
    Returns:
        dict: The unchanged data
    """
    return work_injuries_handler.process(data)

def calculate_work_injuries_prc(data):
    """
    Function wrapper for the PRC work injuries handler.
    
    Args:
        data (dict): The data to process
        
    Returns:
        dict: The unchanged data
    """
    return work_injuries_handler.process(data)

# Register handlers
calculations.register_calculation_handler('work_injuries_hk', calculate_work_injuries_hk)
calculations.register_calculation_handler('work_injuries_prc', calculate_work_injuries_prc) 