"""
Test script to verify that calculation handlers work properly with sample data.
This script imports and uses the calculation handlers directly rather than going
through the Django models.
"""

import logging
import json
from data_management.services import calculations

# Configure logging to show in console
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def print_divider():
    print("=" * 50)

def test_electricity_hk_clp():
    print_divider()
    print("Testing Hong Kong CLP Electricity Consumption")
    
    sample_data = {
        "periods": {
            "Jan-2024": {
                "value": 100,
                "unit": "kWh"
            },
            "Feb-2024": {
                "value": 120,
                "unit": "kWh"
            },
            "Mar-2024": {
                "value": 150,
                "unit": "kWh"
            }
        }
    }
    
    # Process the data
    result = calculations.validate_and_update_totals(sample_data, "electricity_hk_clp")
    
    # Print the result
    print("Input:")
    print(json.dumps(sample_data, indent=2))
    print("\nOutput:")
    print(json.dumps(result, indent=2))
    return result

def test_electricity_hk_hke():
    print_divider()
    print("Testing Hong Kong HKE Electricity Consumption")
    
    sample_data = {
        "periods": {
            "Jan-2024": {
                "value": 200,
                "unit": "kWh"
            },
            "Feb-2024": {
                "value": 220,
                "unit": "kWh"
            },
            "Mar-2024": {
                "value": 250,
                "unit": "kWh"
            }
        }
    }
    
    # Process the data
    result = calculations.validate_and_update_totals(sample_data, "electricity_hk_hke")
    
    # Print the result
    print("Input:")
    print(json.dumps(sample_data, indent=2))
    print("\nOutput:")
    print(json.dumps(result, indent=2))
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
    result = calculations.validate_and_update_totals(sample_data, "electricity_prc")
    
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
    result = calculations.validate_and_update_totals(sample_data, "fresh_water_hk")
    
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
    result = calculations.validate_and_update_totals(sample_data, "fresh_water_prc")
    
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
    result = calculations.validate_and_update_totals(sample_data, "wastewater_hk")
    
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
    result = calculations.validate_and_update_totals(sample_data, "wastewater_prc")
    
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
    result = calculations.validate_and_update_totals(sample_data, "work_injuries_hk")
    
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
    result = calculations.validate_and_update_totals(sample_data, "work_injuries_prc")
    
    # Print results
    print(f"PRC Work Injuries Data (unchanged): {json.dumps(result, indent=2)}")
    
    return result

def run_all_tests():
    """Run all calculation tests."""
    test_electricity_hk_clp()
    test_electricity_hk_hke()
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