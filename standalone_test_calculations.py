"""
Standalone test script for calculation handlers.
This script simulates the calculation process without requiring Django.
"""

import logging
import json
import sys
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Simulated calculation registry
CALCULATION_HANDLERS = {}

def register_calculation_handler(schema_type, handler_func):
    """Register a calculation handler"""
    CALCULATION_HANDLERS[schema_type] = handler_func
    print(f"Registered handler for {schema_type}")

class PeriodicalConsumptionHandler:
    """Base class for consumption handlers"""
    
    def validate(self, data):
        """Validate basic structure"""
        if not data or not isinstance(data, dict):
            return False
            
        if 'periods' not in data or not isinstance(data['periods'], dict):
            return False
            
        return True
    
    def get_total_field_name(self):
        """Get total field name"""
        return 'total_consumption'
        
    def set_total(self, data, total):
        """Set total consumption value"""
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
        
    def process(self, data):
        """Process the data"""
        if not self.validate(data):
            logger.warning(f"Data validation failed for {self.__class__.__name__}")
            return data
            
        return self.calculate(data)

# Electricity HK handler
class ElectricityHKHandler(PeriodicalConsumptionHandler):
    def calculate(self, data):
        """Calculate totals for HK electricity"""
        periods = data.get('periods', {})
        
        totals = {
            'CLP': {'value': 0, 'unit': 'kWh'},
            'HKE': {'value': 0, 'unit': 'kWh'}
        }
        
        for period_key, period_data in periods.items():
            # Sum CLP values
            if 'CLP' in period_data and isinstance(period_data['CLP'], dict):
                clp_data = period_data['CLP']
                if 'value' in clp_data and clp_data['value'] is not None:
                    totals['CLP']['value'] += float(clp_data['value'])
            
            # Sum HKE values
            if 'HKE' in period_data and isinstance(period_data['HKE'], dict):
                hke_data = period_data['HKE']
                if 'value' in hke_data and hke_data['value'] is not None:
                    totals['HKE']['value'] += float(hke_data['value'])
        
        return self.set_total(data, totals)

# Electricity PRC handler
class ElectricityPRCHandler(PeriodicalConsumptionHandler):
    def calculate(self, data):
        """Calculate totals for PRC electricity"""
        periods = data.get('periods', {})
        
        total = {'value': 0, 'unit': 'kWh'}
        
        for period_key, period_data in periods.items():
            if isinstance(period_data, dict) and 'value' in period_data and period_data['value'] is not None:
                total['value'] += float(period_data['value'])
        
        return self.set_total(data, total)

# Fresh Water HK handler
class FreshWaterHKHandler(PeriodicalConsumptionHandler):
    def calculate(self, data):
        """Calculate totals for HK fresh water"""
        periods = data.get('periods', {})
        
        total = {'value': 0, 'unit': 'm³'}
        
        for period_key, period_data in periods.items():
            if isinstance(period_data, dict) and 'value' in period_data and period_data['value'] is not None:
                total['value'] += float(period_data['value'])
        
        return self.set_total(data, total)

# Fresh Water PRC handler
class FreshWaterPRCHandler(PeriodicalConsumptionHandler):
    def calculate(self, data):
        """Calculate totals for PRC fresh water"""
        periods = data.get('periods', {})
        
        total = {'value': 0, 'unit': 'm³'}
        
        for period_key, period_data in periods.items():
            if isinstance(period_data, dict) and 'value' in period_data and period_data['value'] is not None:
                total['value'] += float(period_data['value'])
        
        return self.set_total(data, total)

# Wastewater HK handler
class WastewaterHKHandler(PeriodicalConsumptionHandler):
    def calculate(self, data):
        """Calculate totals for HK wastewater"""
        periods = data.get('periods', {})
        
        total = {'value': 0, 'unit': 'm³'}
        
        for period_key, period_data in periods.items():
            if isinstance(period_data, dict) and 'value' in period_data and period_data['value'] is not None:
                total['value'] += float(period_data['value'])
        
        return self.set_total(data, total)

# Wastewater PRC handler
class WastewaterPRCHandler(PeriodicalConsumptionHandler):
    def calculate(self, data):
        """Calculate totals for PRC wastewater"""
        periods = data.get('periods', {})
        
        total = {'value': 0, 'unit': 'm³'}
        
        for period_key, period_data in periods.items():
            if isinstance(period_data, dict) and 'value' in period_data and period_data['value'] is not None:
                total['value'] += float(period_data['value'])
        
        return self.set_total(data, total)

# Work Injuries handler (null handler)
class WorkInjuriesHandler:
    def process(self, data):
        """Do nothing, just return the data unchanged"""
        logger.info("Processing work injuries data (null handler)")
        return data

# Create handler instances
electricity_hk_handler = ElectricityHKHandler()
electricity_prc_handler = ElectricityPRCHandler()
fresh_water_hk_handler = FreshWaterHKHandler()
fresh_water_prc_handler = FreshWaterPRCHandler()
wastewater_hk_handler = WastewaterHKHandler()
wastewater_prc_handler = WastewaterPRCHandler()
work_injuries_handler = WorkInjuriesHandler()

# Register handlers
register_calculation_handler('electricity_hk', electricity_hk_handler.process)
register_calculation_handler('electricity_prc', electricity_prc_handler.process)
register_calculation_handler('fresh_water_hk', fresh_water_hk_handler.process)
register_calculation_handler('fresh_water_prc', fresh_water_prc_handler.process)
register_calculation_handler('wastewater_hk', wastewater_hk_handler.process)
register_calculation_handler('wastewater_prc', wastewater_prc_handler.process)
register_calculation_handler('work_injuries_hk', work_injuries_handler.process)
register_calculation_handler('work_injuries_prc', work_injuries_handler.process)

def validate_and_update_totals(data, schema_type):
    """Main calculation function"""
    if not data or not isinstance(data, dict):
        return data
        
    if schema_type in CALCULATION_HANDLERS:
        logger.info(f"Using handler for {schema_type}")
        return CALCULATION_HANDLERS[schema_type](data)
    
    logger.warning(f"No handler found for {schema_type}")
    return data

# Test functions
def test_electricity_hk():
    """Test Hong Kong electricity calculation."""
    logger.info("=== Testing Hong Kong electricity calculation ===")
    
    # Sample data with CLP and HKE values
    sample_data = {
        "periods": {
            "Jan-2025": {
                "CLP": {"value": 100, "unit": "kWh"},
                "HKE": {"value": 150, "unit": "kWh"}
            },
            "Feb-2025": {
                "CLP": {"value": 120, "unit": "kWh"},
                "HKE": {"value": 160, "unit": "kWh"}
            }
        },
        "total_consumption": {
            "CLP": {"value": 0, "unit": "kWh"},
            "HKE": {"value": 0, "unit": "kWh"}
        }
    }
    
    # Process data
    result = validate_and_update_totals(sample_data, "electricity_hk")
    
    # Print results
    print(f"CLP Total: {result['total_consumption']['CLP']['value']} {result['total_consumption']['CLP']['unit']}")
    print(f"HKE Total: {result['total_consumption']['HKE']['value']} {result['total_consumption']['HKE']['unit']}")
    
    return result

def test_electricity_prc():
    """Test PRC electricity calculation."""
    logger.info("=== Testing PRC electricity calculation ===")
    
    # Sample data
    sample_data = {
        "periods": {
            "Jan-2025": {"value": 200, "unit": "kWh"},
            "Feb-2025": {"value": 220, "unit": "kWh"}
        },
        "total_consumption": {"value": 0, "unit": "kWh"},
        "region": "PRC"
    }
    
    # Process data
    result = validate_and_update_totals(sample_data, "electricity_prc")
    
    # Print results
    print(f"Total: {result['total_consumption']['value']} {result['total_consumption']['unit']}")
    
    return result

def test_fresh_water_hk():
    """Test Hong Kong fresh water calculation."""
    logger.info("=== Testing Hong Kong fresh water calculation ===")
    
    # Sample data
    sample_data = {
        "periods": {
            "Jan-2025": {"value": 50, "unit": "m³"},
            "Feb-2025": {"value": 55, "unit": "m³"}
        },
        "total_consumption": {"value": 0, "unit": "m³"},
        "water_type": "Fresh Water",
        "region": "Hong Kong"
    }
    
    # Process data
    result = validate_and_update_totals(sample_data, "fresh_water_hk")
    
    # Print results
    print(f"Total: {result['total_consumption']['value']} {result['total_consumption']['unit']}")
    
    return result

def test_fresh_water_prc():
    """Test PRC fresh water calculation."""
    logger.info("=== Testing PRC fresh water calculation ===")
    
    # Sample data
    sample_data = {
        "periods": {
            "Jan-2025": {"value": 60, "unit": "m³"},
            "Feb-2025": {"value": 65, "unit": "m³"}
        },
        "total_consumption": {"value": 0, "unit": "m³"},
        "water_type": "Fresh Water",
        "region": "PRC"
    }
    
    # Process data
    result = validate_and_update_totals(sample_data, "fresh_water_prc")
    
    # Print results
    print(f"Total: {result['total_consumption']['value']} {result['total_consumption']['unit']}")
    
    return result

def test_wastewater_hk():
    """Test Hong Kong wastewater calculation."""
    logger.info("=== Testing Hong Kong wastewater calculation ===")
    
    # Sample data
    sample_data = {
        "periods": {
            "Jan-2025": {"value": 40, "unit": "m³"},
            "Feb-2025": {"value": 45, "unit": "m³"}
        },
        "total_consumption": {"value": 0, "unit": "m³"},
        "water_type": "Wastewater",
        "region": "Hong Kong"
    }
    
    # Process data
    result = validate_and_update_totals(sample_data, "wastewater_hk")
    
    # Print results
    print(f"Total: {result['total_consumption']['value']} {result['total_consumption']['unit']}")
    
    return result

def test_wastewater_prc():
    """Test PRC wastewater calculation."""
    logger.info("=== Testing PRC wastewater calculation ===")
    
    # Sample data
    sample_data = {
        "periods": {
            "Jan-2025": {"value": 45, "unit": "m³"},
            "Feb-2025": {"value": 50, "unit": "m³"}
        },
        "total_consumption": {"value": 0, "unit": "m³"},
        "water_type": "Wastewater",
        "region": "PRC"
    }
    
    # Process data
    result = validate_and_update_totals(sample_data, "wastewater_prc")
    
    # Print results
    print(f"Total: {result['total_consumption']['value']} {result['total_consumption']['unit']}")
    
    return result

def test_work_injuries_hk():
    """Test Hong Kong work injuries processing (null handler)."""
    logger.info("=== Testing Hong Kong work injuries processing ===")
    
    # Sample data
    sample_data = {
        "fiscal_year": "FY 2025",
        "deaths": {"value": 0, "unit": "Person"},
        "injuries": {"value": 2, "unit": "Person"},
        "lost_days": {"value": 10, "unit": "Days"},
        "region": "Hong Kong"
    }
    
    # Process data - should return unchanged
    result = validate_and_update_totals(sample_data, "work_injuries_hk")
    
    # Print results
    print(f"HK Work Injuries Data (unchanged): {json.dumps(result, indent=2)}")
    
    return result

def test_work_injuries_prc():
    """Test PRC work injuries processing (null handler)."""
    logger.info("=== Testing PRC work injuries processing ===")
    
    # Sample data
    sample_data = {
        "fiscal_year": "FY 2025",
        "deaths": {"value": 0, "unit": "Person"},
        "injuries": {"value": 2, "unit": "Person"},
        "lost_days": {"value": 10, "unit": "Days"},
        "region": "PRC"
    }
    
    # Process data - should return unchanged
    result = validate_and_update_totals(sample_data, "work_injuries_prc")
    
    # Print results
    print(f"PRC Work Injuries Data (unchanged): {json.dumps(result, indent=2)}")
    
    return result

def run_all_tests():
    """Run all calculation tests."""
    test_electricity_hk()
    print("\n")
    
    test_electricity_prc()
    print("\n")
    
    test_fresh_water_hk()
    print("\n")
    
    test_fresh_water_prc()
    print("\n")
    
    test_wastewater_hk()
    print("\n")
    
    test_wastewater_prc()
    print("\n")
    
    test_work_injuries_hk()
    print("\n")
    
    test_work_injuries_prc()
    print("\n")
    
    print("All tests completed.")

if __name__ == "__main__":
    run_all_tests() 