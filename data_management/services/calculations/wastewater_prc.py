"""
Class-based calculation handler for PRC wastewater consumption.
"""

import logging
from .. import calculations

logger = logging.getLogger(__name__)

class WastewaterPRCCalculationHandler:
    """Calculation handler for PRC wastewater data."""

    def __init__(self):
        self.calculation_type = "sum_by_period"

    def validate(self, data):
        """Validate the data before performing calculations."""
        if not data or not isinstance(data, dict):
            return False

        periods = data.get('periods', [])
        
        # Ensure periods is an array and has at least one entry with a valid value
        if not isinstance(periods, list) or len(periods) == 0:
            return False
        
        # Check if at least one period has a valid numerical value
        has_valid_value = False
        for period in periods:
            if period and isinstance(period, dict) and 'value' in period:
                value = period.get('value')
                if isinstance(value, (int, float)) and value >= 0:
                    has_valid_value = True
                    break
        
        return has_valid_value

    def calculate(self, data):
        """Calculate total consumption from the periods data."""
        if not self.validate(data):
            return data

        periods = data.get('periods', [])
        total = 0
        unit = None

        # Sum up the values from each period
        for period in periods:
            if period and isinstance(period, dict) and 'value' in period:
                value = period.get('value')
                if isinstance(value, (int, float)) and value >= 0:
                    total += value
                    # Capture unit from the first valid entry
                    if unit is None and 'unit' in period:
                        unit = period.get('unit')

        # Set or update the total consumption field
        if 'total_consumption' not in data:
            data['total_consumption'] = {'value': total}
            if unit:
                data['total_consumption']['unit'] = unit
        else:
            data['total_consumption']['value'] = total
            if unit and 'unit' not in data['total_consumption']:
                data['total_consumption']['unit'] = unit

        return data

# Create handler instance
wastewater_prc_handler = WastewaterPRCCalculationHandler()

# Wrapper function for the registry
def calculate_wastewater_prc(data):
    """
    Function wrapper for the calculation handler.
    
    Args:
        data (dict): The data to process
        
    Returns:
        dict: The data with updated totals
    """
    return wastewater_prc_handler.calculate(data)

# Register handler
calculations.register_calculation_handler('wastewater_prc', calculate_wastewater_prc) 