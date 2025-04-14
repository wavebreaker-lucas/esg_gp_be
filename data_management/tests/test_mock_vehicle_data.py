"""
Test fixtures for vehicle emissions calculation testing.
This module provides mock data for VehicleTrackingMetric testing.
"""

# Sample vehicle tracking data for tests
SAMPLE_VEHICLE_DATA = {
    "vehicles": [
        {
            "id": 1,
            "vehicle_type": "private_cars",
            "fuel_type": "diesel_oil",
            "fuel_consumed": 100.0,
            "kilometers": 1000.0,
            "registration": "AB1234",
            "brand": "Toyota",
            "model": "Corolla"
        },
        {
            "id": 2,
            "vehicle_type": "private_cars",
            "fuel_type": "petrol",
            "fuel_consumed": 120.0,
            "kilometers": 1200.0,
            "registration": "CD5678",
            "brand": "Honda",
            "model": "Civic"
        },
        {
            "id": 3,
            "vehicle_type": "light_goods_lte_2_5",
            "fuel_type": "diesel_oil",
            "fuel_consumed": 200.0,
            "kilometers": 1500.0,
            "registration": "EF9012",
            "brand": "Ford",
            "model": "Transit"
        }
    ]
}

# Sample with missing fuel data (for testing distance-based calculations)
SAMPLE_VEHICLE_DATA_NO_FUEL = {
    "vehicles": [
        {
            "id": 1,
            "vehicle_type": "private_cars",
            "fuel_type": "diesel_oil",
            "kilometers": 1000.0,
            "registration": "AB1234",
            "brand": "Toyota",
            "model": "Corolla"
        }
    ]
}

# Sample with missing data (for testing error handling)
SAMPLE_VEHICLE_DATA_INVALID = {
    "vehicles": [
        {
            "id": 1,
            # Missing vehicle_type
            "fuel_type": "diesel_oil",
            "fuel_consumed": 100.0,
            "kilometers": 1000.0
        },
        {
            "id": 2,
            "vehicle_type": "private_cars",
            # Missing fuel_type
            "fuel_consumed": 120.0,
            "kilometers": 1200.0
        }
    ]
}

# Sample emission factor mapping for testing
SAMPLE_EMISSION_MAPPING = {
    # Vehicle type + fuel type combinations
    "private_cars_diesel_oil": "transport_cars_diesel",
    "private_cars_petrol": "transport_cars_petrol", 
    "private_cars_unleaded_petrol": "transport_cars_petrol",
    "private_cars_lpg": "transport_cars_lpg",
    
    # Light goods vehicles
    "light_goods_lte_2_5_diesel_oil": "transport_light_commercial_diesel",
    "light_goods_2_5_3_5_diesel_oil": "transport_light_commercial_diesel",
    "light_goods_3_5_5_5_diesel_oil": "transport_light_commercial_diesel",
    
    # Fallbacks by fuel type only
    "diesel_oil": "transport_general_diesel",
    "petrol": "transport_general_petrol",
    "unleaded_petrol": "transport_general_petrol",
    "lpg": "transport_lpg"
}

# Sample vehicle types
SAMPLE_VEHICLE_TYPES = [
    {"value": "private_cars", "label": "Private cars"},
    {"value": "light_goods_lte_2_5", "label": "Light goods vehicles (<=2.5tonnes)"},
    {"value": "medium_heavy_goods_5_5_15", "label": "Medium & Heavy goods vehicles (5.5-15tonnes)"}
]

# Sample fuel types
SAMPLE_FUEL_TYPES = [
    {"value": "diesel_oil", "label": "Diesel oil"},
    {"value": "petrol", "label": "Petrol"},
    {"value": "lpg", "label": "LPG"}
] 