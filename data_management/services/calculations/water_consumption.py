"""
Class-based calculation handler for water consumption by region (HK/PRC).
"""

import logging
from .. import calculations
from .base import PeriodicalConsumptionHandler

logger = logging.getLogger(__name__)

class WaterConsumptionHandler(PeriodicalConsumptionHandler):
    """
    Handler for water consumption tracking (HK/PRC regions).
    """
    
    def validate(self, data):
        """
        Validate water consumption data structure.
        
        Args:
            data (dict): The data to validate
            
        Returns:
            bool: Whether the data is valid
        """
        if not super().validate(data):
            return False
            
        # Check if at least one period has HK/PRC structure
        periods = data.get('periods', {})
        for period_key, period_data in periods.items():
            if isinstance(period_data, dict) and ('HK' in period_data or 'PRC' in period_data):
                return True
                
        return False
        
    def calculate(self, data):
        """
        Calculate total water consumption for HK and PRC regions.
        
        Args:
            data (dict): The data to process
            
        Returns:
            dict: The data with updated totals
        """
        periods = data.get('periods', {})
        
        totals = {
            'HK': {'value': 0, 'unit': None},
            'PRC': {'value': 0, 'unit': None}
        }
        
        for period_key, period_data in periods.items():
            # Sum HK values
            if 'HK' in period_data and isinstance(period_data['HK'], dict):
                hk_data = period_data['HK']
                if 'value' in hk_data and hk_data['value'] is not None:
                    totals['HK']['value'] += float(hk_data['value'])
                    # Capture unit from the first valid entry
                    if totals['HK']['unit'] is None and 'unit' in hk_data:
                        totals['HK']['unit'] = hk_data['unit']
            
            # Sum PRC values
            if 'PRC' in period_data and isinstance(period_data['PRC'], dict):
                prc_data = period_data['PRC']
                if 'value' in prc_data and prc_data['value'] is not None:
                    totals['PRC']['value'] += float(prc_data['value'])
                    # Capture unit from the first valid entry
                    if totals['PRC']['unit'] is None and 'unit' in prc_data:
                        totals['PRC']['unit'] = prc_data['unit']
        
        # Set or update total consumption
        return self.set_total(data, totals)
    
    def process(self, data):
        """
        Process water consumption data.
        
        Args:
            data (dict): The data to process
            
        Returns:
            dict: The data with updated totals
        """
        logger.info("Processing water consumption data")
        return super().process(data)

# Create handler instance
water_consumption_handler = WaterConsumptionHandler()

# Wrapper function for the registry 
def calculate_water_consumption(data):
    """
    Function wrapper for the class-based handler.
    
    Args:
        data (dict): The data to process
        
    Returns:
        dict: The data with updated totals
    """
    return water_consumption_handler.process(data)

# Register for multiple schema types
calculations.register_calculation_handler('fresh_water', calculate_water_consumption)
calculations.register_calculation_handler('wastewater', calculate_water_consumption)
calculations.register_calculation_handler('water_consumption', calculate_water_consumption) 