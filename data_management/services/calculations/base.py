"""
Base classes for ESG calculation handlers.
"""

import logging
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)

class CalculationHandler(ABC):
    """
    Base class for ESG calculation handlers.
    Provides a consistent interface for all calculation types.
    """
    
    @abstractmethod
    def calculate(self, data):
        """
        Calculate totals based on the provided data.
        
        Args:
            data (dict): The data to process
            
        Returns:
            dict: The data with updated totals
        """
        pass
    
    def validate(self, data):
        """
        Validate the structure of the data.
        Can be overridden by subclasses to perform schema-specific validation.
        
        Args:
            data (dict): The data to validate
            
        Returns:
            bool: Whether the data is valid
        """
        if not data or not isinstance(data, dict):
            return False
            
        if 'periods' not in data or not isinstance(data['periods'], dict):
            return False
            
        return True
    
    def process(self, data):
        """
        Process the data by validating and then calculating.
        
        Args:
            data (dict): The data to process
            
        Returns:
            dict: The data with updated totals
        """
        if not self.validate(data):
            logger.warning(f"Data validation failed for {self.__class__.__name__}")
            return data
            
        return self.calculate(data)

class PeriodicalConsumptionHandler(CalculationHandler):
    """
    Base handler for consumption metrics that track usage over time periods.
    """
    
    def validate(self, data):
        """
        Validate periodical consumption data.
        
        Args:
            data (dict): The data to validate
            
        Returns:
            bool: Whether the data is valid
        """
        if not super().validate(data):
            return False
            
        # Check if periods contain at least one valid entry
        periods = data.get('periods', {})
        return len(periods) > 0
    
    def get_total_field_name(self):
        """
        Get the field name where total should be stored.
        
        Returns:
            str: The field name for totals
        """
        return 'total_consumption'
    
    def set_total(self, data, total):
        """
        Set the total in the data.
        
        Args:
            data (dict): The data to update
            total: The calculated total value(s)
            
        Returns:
            dict: The updated data
        """
        total_field = self.get_total_field_name()
        
        if total_field not in data:
            data[total_field] = total
        else:
            # Update existing totals based on structure
            if isinstance(total, dict):
                if isinstance(data[total_field], dict):
                    for key, value in total.items():
                        if key not in data[total_field]:
                            data[total_field][key] = value
                        else:
                            # Update value/unit structure
                            if isinstance(value, dict) and 'value' in value:
                                if isinstance(data[total_field][key], dict):
                                    data[total_field][key]['value'] = value['value']
                                    if 'unit' not in data[total_field][key] and 'unit' in value:
                                        data[total_field][key]['unit'] = value['unit']
                                else:
                                    data[total_field][key] = value
                            else:
                                data[total_field][key] = value
            elif isinstance(data[total_field], dict) and isinstance(total, dict) and 'value' in total:
                # Update simple value/unit structure
                data[total_field]['value'] = total['value']
                if 'unit' not in data[total_field] and 'unit' in total:
                    data[total_field]['unit'] = total['unit']
            else:
                data[total_field] = total
                
        return data 