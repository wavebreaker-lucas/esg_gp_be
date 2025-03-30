"""
Class-based calculation handler for PRC electricity consumption.
"""

import logging
from .. import calculations
from .base import PeriodicalConsumptionHandler

logger = logging.getLogger(__name__)

class ElectricityPRCHandler(PeriodicalConsumptionHandler):
    """
    Handler for PRC electricity consumption (single value per period).
    """
    
    def validate(self, data):
        """
        Validate PRC electricity data structure.
        
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
        Calculate total electricity consumption for PRC.
        
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
        Process PRC electricity data.
        
        Args:
            data (dict): The data to process
            
        Returns:
            dict: The data with updated totals
        """
        logger.info("Processing PRC electricity consumption data")
        return super().process(data)

# Create handler instance
electricity_prc_handler = ElectricityPRCHandler()

# Wrapper function for the registry
def calculate_electricity_prc(data):
    """
    Function wrapper for the class-based handler.
    
    Args:
        data (dict): The data to process
        
    Returns:
        dict: The data with updated totals
    """
    return electricity_prc_handler.process(data)

# Register handler
calculations.register_calculation_handler('electricity_prc', calculate_electricity_prc) 