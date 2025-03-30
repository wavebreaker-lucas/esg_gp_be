"""
Class-based calculation handler for Hong Kong fresh water consumption.
"""

import logging
from .. import calculations
from .base import PeriodicalConsumptionHandler

logger = logging.getLogger(__name__)

class FreshWaterHKHandler(PeriodicalConsumptionHandler):
    """
    Handler for Hong Kong fresh water consumption (single value per period).
    """
    
    def validate(self, data):
        """
        Validate Hong Kong fresh water data structure.
        
        Args:
            data (dict): The data to validate
            
        Returns:
            bool: Whether the data is valid
        """
        if not super().validate(data):
            return False
            
        # Check if at least one period has value/unit structure
        periods = data.get('periods', {})
        for period_key, period_data in periods.items():
            if isinstance(period_data, dict) and 'value' in period_data:
                return True
                
        return False
        
    def calculate(self, data):
        """
        Calculate total fresh water consumption for Hong Kong.
        
        Args:
            data (dict): The data to process
            
        Returns:
            dict: The data with updated totals
        """
        periods = data.get('periods', {})
        
        total = {'value': 0, 'unit': None}
        
        for period_key, period_data in periods.items():
            if isinstance(period_data, dict) and 'value' in period_data and period_data['value'] is not None:
                total['value'] += float(period_data['value'])
                # Capture unit from the first valid entry
                if total['unit'] is None and 'unit' in period_data:
                    total['unit'] = period_data['unit']
        
        # Set or update total consumption
        return self.set_total(data, total)
    
    def process(self, data):
        """
        Process Hong Kong fresh water data.
        
        Args:
            data (dict): The data to process
            
        Returns:
            dict: The data with updated totals
        """
        logger.info("Processing Hong Kong fresh water consumption data")
        return super().process(data)

# Create handler instance
fresh_water_hk_handler = FreshWaterHKHandler()

# Wrapper function for the registry
def calculate_fresh_water_hk(data):
    """
    Function wrapper for the class-based handler.
    
    Args:
        data (dict): The data to process
        
    Returns:
        dict: The data with updated totals
    """
    return fresh_water_hk_handler.process(data)

# Register handler
calculations.register_calculation_handler('fresh_water_hk', calculate_fresh_water_hk) 