"""
Class-based calculation handler for Hong Kong HKE electricity consumption.
"""

import logging
from .. import calculations
from .base import PeriodicalConsumptionHandler

logger = logging.getLogger(__name__)

class ElectricityHKHKEHandler(PeriodicalConsumptionHandler):
    """
    Handler for Hong Kong HKE electricity consumption.
    """
    
    def validate(self, data):
        """
        Validate Hong Kong HKE electricity data structure.
        
        Args:
            data (dict): The data to validate
            
        Returns:
            bool: Whether the data is valid
        """
        if not super().validate(data):
            return False
            
        # Check if at least one period has value
        periods = data.get('periods', {})
        for period_key, period_data in periods.items():
            if isinstance(period_data, dict) and 'value' in period_data:
                return True
                
        return False
    
    def calculate(self, data):
        """
        Calculate total electricity consumption for HKE.
        
        Args:
            data (dict): The data to process
            
        Returns:
            dict: The data with updated totals
        """
        periods = data.get('periods', {})
        
        total = {
            'value': 0,
            'unit': None
        }
        
        for period_key, period_data in periods.items():
            # Sum values
            if isinstance(period_data, dict) and 'value' in period_data and period_data['value'] is not None:
                total['value'] += float(period_data['value'])
                # Capture unit from the first valid entry
                if total['unit'] is None and 'unit' in period_data:
                    total['unit'] = period_data['unit']
        
        # Set or update total consumption
        if 'total_consumption' not in data:
            data['total_consumption'] = {}
            
        data['total_consumption'] = total
        
        return data
    
    def process(self, data):
        """
        Process Hong Kong HKE electricity data.
        
        Args:
            data (dict): The data to process
            
        Returns:
            dict: The data with updated totals
        """
        logger.info("Processing Hong Kong HKE electricity consumption data")
        return super().process(data)


# Create handler instance
electricity_hk_hke_handler = ElectricityHKHKEHandler()

# Wrapper function for the registry
def calculate_electricity_hk_hke(data):
    """
    Function wrapper for the class-based handler.
    
    Args:
        data (dict): The data to process
        
    Returns:
        dict: The data with updated totals
    """
    return electricity_hk_hke_handler.process(data)

# Register handler
calculations.register_calculation_handler('electricity_hk_hke', calculate_electricity_hk_hke) 