"""
Class-based calculation handler for PRC fresh water consumption.
"""

import logging
from .. import calculations
from .base import PeriodicalConsumptionHandler

logger = logging.getLogger(__name__)

class FreshWaterPRCHandler(PeriodicalConsumptionHandler):
    """
    Handler for PRC fresh water consumption (single value per period).
    """
    
    def validate(self, data):
        """
        Validate PRC fresh water data structure.
        
        Args:
            data (dict): The data to validate
            
        Returns:
            bool: Whether the data is valid
        """
        if not super().validate(data):
            return False
            
        # Check if periods is an array and has at least one entry with a value
        periods = data.get('periods', [])
        if not isinstance(periods, list):
            return False
            
        for period in periods:
            if isinstance(period, dict) and 'value' in period and period['value'] is not None:
                return True
                
        return False
        
    def calculate(self, data):
        """
        Calculate total fresh water consumption for PRC.
        
        Args:
            data (dict): The data to process
            
        Returns:
            dict: The data with updated totals
        """
        periods = data.get('periods', [])
        
        total = {'value': 0, 'unit': None}
        
        for period in periods:
            # Sum values from each period in the array
            if isinstance(period, dict) and 'value' in period and period['value'] is not None:
                total['value'] += float(period['value'])
                # Capture unit from the first valid entry
                if total['unit'] is None and 'unit' in period:
                    total['unit'] = period['unit']
        
        # Set or update total consumption
        return self.set_total(data, total)
    
    def process(self, data):
        """
        Process PRC fresh water data.
        
        Args:
            data (dict): The data to process
            
        Returns:
            dict: The data with updated totals
        """
        logger.info("Processing PRC fresh water consumption data")
        return super().process(data)

# Create handler instance
fresh_water_prc_handler = FreshWaterPRCHandler()

# Wrapper function for the registry
def calculate_fresh_water_prc(data):
    """
    Function wrapper for the class-based handler.
    
    Args:
        data (dict): The data to process
        
    Returns:
        dict: The data with updated totals
    """
    return fresh_water_prc_handler.process(data)

# Register handler
calculations.register_calculation_handler('fresh_water_prc', calculate_fresh_water_prc) 