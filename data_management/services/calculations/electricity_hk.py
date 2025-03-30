"""
Class-based calculation handler for Hong Kong electricity consumption (CLP/HKE).
"""

import logging
from .. import calculations
from .base import PeriodicalConsumptionHandler

logger = logging.getLogger(__name__)

class ElectricityHKHandler(PeriodicalConsumptionHandler):
    """
    Handler for Hong Kong electricity consumption (CLP/HKE).
    """
    
    def validate(self, data):
        """
        Validate Hong Kong electricity data structure.
        
        Args:
            data (dict): The data to validate
            
        Returns:
            bool: Whether the data is valid
        """
        if not super().validate(data):
            return False
            
        # Check if at least one period has CLP/HKE structure
        periods = data.get('periods', {})
        for period_key, period_data in periods.items():
            if isinstance(period_data, dict) and ('CLP' in period_data or 'HKE' in period_data):
                return True
                
        return False
    
    def calculate(self, data):
        """
        Calculate total electricity consumption for CLP and HKE.
        
        Args:
            data (dict): The data to process
            
        Returns:
            dict: The data with updated totals
        """
        periods = data.get('periods', {})
        
        totals = {
            'CLP': {'value': 0, 'unit': None},
            'HKE': {'value': 0, 'unit': None}
        }
        
        for period_key, period_data in periods.items():
            # Sum CLP values
            if 'CLP' in period_data and isinstance(period_data['CLP'], dict):
                clp_data = period_data['CLP']
                if 'value' in clp_data and clp_data['value'] is not None:
                    totals['CLP']['value'] += float(clp_data['value'])
                    # Capture unit from the first valid entry
                    if totals['CLP']['unit'] is None and 'unit' in clp_data:
                        totals['CLP']['unit'] = clp_data['unit']
            
            # Sum HKE values
            if 'HKE' in period_data and isinstance(period_data['HKE'], dict):
                hke_data = period_data['HKE']
                if 'value' in hke_data and hke_data['value'] is not None:
                    totals['HKE']['value'] += float(hke_data['value'])
                    # Capture unit from the first valid entry
                    if totals['HKE']['unit'] is None and 'unit' in hke_data:
                        totals['HKE']['unit'] = hke_data['unit']
        
        # Set or update total consumption
        return self.set_total(data, totals)
    
    def process(self, data):
        """
        Process Hong Kong electricity data.
        
        Args:
            data (dict): The data to process
            
        Returns:
            dict: The data with updated totals
        """
        logger.info("Processing Hong Kong electricity consumption data")
        return super().process(data)


# Create handler instance
electricity_hk_handler = ElectricityHKHandler()

# Wrapper function for the registry
def calculate_electricity_hk(data):
    """
    Function wrapper for the class-based handler.
    
    Args:
        data (dict): The data to process
        
    Returns:
        dict: The data with updated totals
    """
    return electricity_hk_handler.process(data)

# Register handler
calculations.register_calculation_handler('electricity_hk', calculate_electricity_hk) 