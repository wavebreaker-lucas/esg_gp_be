#!/usr/bin/env python3
"""
Example script for using the Emission Factors API

This script demonstrates how Baker Tilly administrators can interact with the
emission factors API programmatically.

Requirements:
    pip install requests

Usage:
    python emission_factors_example.py

Note: You need to have a Baker Tilly admin account to use these endpoints.
"""

import requests
import json
from decimal import Decimal


class EmissionFactorAPI:
    """Client for interacting with the Emission Factors API"""
    
    def __init__(self, base_url="http://localhost:8000", email=None, password=None):
        self.base_url = base_url
        self.session = requests.Session()
        self.token = None
        
        if email and password:
            self.login(email, password)
    
    def login(self, email, password):
        """Authenticate and get JWT token"""
        response = self.session.post(f"{self.base_url}/api/token/", {
            "email": email,
            "password": password
        })
        
        if response.status_code == 200:
            data = response.json()
            self.token = data['access']
            self.session.headers.update({
                'Authorization': f'Bearer {self.token}'
            })
            print("✅ Authentication successful")
            return True
        else:
            print(f"❌ Authentication failed: {response.text}")
            return False
    
    def list_factors(self, **filters):
        """List emission factors with optional filters"""
        response = self.session.get(f"{self.base_url}/api/emission-factors/", params=filters)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Error listing factors: {response.text}")
            return None
    
    def get_factor(self, factor_id):
        """Get a specific emission factor"""
        response = self.session.get(f"{self.base_url}/api/emission-factors/{factor_id}/")
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Error getting factor {factor_id}: {response.text}")
            return None
    
    def create_factor(self, factor_data):
        """Create a new emission factor"""
        response = self.session.post(f"{self.base_url}/api/emission-factors/", json=factor_data)
        if response.status_code == 201:
            return response.json()
        else:
            print(f"Error creating factor: {response.text}")
            return None
    
    def update_factor(self, factor_id, factor_data, partial=True):
        """Update an emission factor"""
        method = 'patch' if partial else 'put'
        response = getattr(self.session, method)(
            f"{self.base_url}/api/emission-factors/{factor_id}/", 
            json=factor_data
        )
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Error updating factor {factor_id}: {response.text}")
            return None
    
    def delete_factor(self, factor_id):
        """Delete an emission factor"""
        response = self.session.delete(f"{self.base_url}/api/emission-factors/{factor_id}/")
        if response.status_code == 204:
            return True
        else:
            print(f"Error deleting factor {factor_id}: {response.text}")
            return False
    
    def bulk_create_factors(self, factors_list):
        """Bulk create emission factors"""
        response = self.session.post(f"{self.base_url}/api/emission-factors/bulk_create/", json={
            "factors": factors_list
        })
        if response.status_code == 201:
            return response.json()
        else:
            print(f"Error bulk creating factors: {response.text}")
            return None
    
    def bulk_delete_factors(self, factor_ids):
        """Bulk delete emission factors"""
        response = self.session.delete(f"{self.base_url}/api/emission-factors/bulk_delete/", json={
            "ids": factor_ids
        })
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Error bulk deleting factors: {response.text}")
            return None
    
    def get_categories(self):
        """Get all categories and subcategories"""
        response = self.session.get(f"{self.base_url}/api/emission-factors/categories/")
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Error getting categories: {response.text}")
            return None
    
    def search_factors(self, **search_params):
        """Advanced search for emission factors"""
        response = self.session.get(f"{self.base_url}/api/emission-factors/search_factors/", params=search_params)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Error searching factors: {response.text}")
            return None
    
    def download_template(self, filename="emission_factors_template.csv"):
        """Download CSV template"""
        response = self.session.get(f"{self.base_url}/api/emission-factors/export_template/")
        if response.status_code == 200:
            with open(filename, 'wb') as f:
                f.write(response.content)
            print(f"✅ Template downloaded as {filename}")
            return True
        else:
            print(f"Error downloading template: {response.text}")
            return False


def main():
    """Example usage of the Emission Factors API"""
    
    # Initialize API client
    # Replace with your Baker Tilly admin credentials
    api = EmissionFactorAPI(
        base_url="http://localhost:8000",
        email="admin@bakertilly.com",  # Replace with actual email
        password="your_password"        # Replace with actual password
    )
    
    if not api.token:
        print("❌ Failed to authenticate. Please check your credentials.")
        return
    
    print("\n" + "="*50)
    print("EMISSION FACTORS API DEMO")
    print("="*50)
    
    # 1. List all factors
    print("\n1. Listing all emission factors...")
    factors = api.list_factors()
    if factors:
        print(f"📊 Found {factors['count']} emission factors")
        if factors['results']:
            print(f"   First factor: {factors['results'][0]['name']}")
    
    # 2. Search for specific factors
    print("\n2. Searching for diesel transport factors...")
    diesel_factors = api.search_factors(category="transport", search="diesel")
    if diesel_factors:
        print(f"🔍 Found {len(diesel_factors)} diesel transport factors")
        for factor in diesel_factors[:3]:  # Show first 3
            print(f"   - {factor['name']}: {factor['value']} {factor['factor_unit']}")
    
    # 3. Get categories
    print("\n3. Getting categories and subcategories...")
    categories = api.get_categories()
    if categories:
        print("📂 Available categories:")
        for category, data in categories.items():
            print(f"   - {category}: {len(data['subcategories'])} subcategories")
    
    # 4. Create a new factor
    print("\n4. Creating a new emission factor...")
    new_factor_data = {
        "name": "Example Diesel Factor - API Test",
        "category": "transport",
        "sub_category": "transport_example_diesel",
        "activity_unit": "liters",
        "value": "2.7500",
        "factor_unit": "kgCO2e/liter",
        "year": 2025,
        "region": "ALL",
        "scope": "1",
        "source": "API Test Example",
        "source_url": "https://example.com/test"
    }
    
    created_factor = api.create_factor(new_factor_data)
    if created_factor:
        print(f"✅ Created factor: {created_factor['name']} (ID: {created_factor['id']})")
        factor_id = created_factor['id']
        
        # 5. Update the factor
        print("\n5. Updating the emission factor...")
        updated_factor = api.update_factor(factor_id, {
            "value": "2.8000",
            "source": "API Test Example - Updated"
        })
        if updated_factor:
            print(f"✅ Updated factor value to {updated_factor['value']}")
        
        # 6. Delete the test factor
        print("\n6. Deleting the test factor...")
        if api.delete_factor(factor_id):
            print("✅ Test factor deleted successfully")
    
    # 7. Bulk create example
    print("\n7. Bulk creating emission factors...")
    bulk_factors = [
        {
            "name": "Bulk Test Factor 1",
            "category": "test",
            "sub_category": "test_category_1",
            "activity_unit": "kg",
            "value": "1.2500",
            "factor_unit": "kgCO2e/kg",
            "year": 2025,
            "region": "ALL",
            "scope": "1",
            "source": "Bulk Test"
        },
        {
            "name": "Bulk Test Factor 2",
            "category": "test",
            "sub_category": "test_category_2", 
            "activity_unit": "m3",
            "value": "0.8500",
            "factor_unit": "kgCO2e/m3",
            "year": 2025,
            "region": "ALL",
            "scope": "2",
            "source": "Bulk Test"
        }
    ]
    
    bulk_result = api.bulk_create_factors(bulk_factors)
    if bulk_result:
        print(f"✅ {bulk_result['message']}")
        created_ids = [f['id'] for f in bulk_result['factors']]
        
        # Clean up bulk test factors
        print("\n8. Cleaning up bulk test factors...")
        if api.bulk_delete_factors(created_ids):
            print("✅ Bulk test factors deleted successfully")
    
    # 9. Download template
    print("\n9. Downloading CSV template...")
    api.download_template("emission_factors_template.csv")
    
    # 10. Filter examples
    print("\n10. Filter examples...")
    
    # Get only electricity factors
    electricity_factors = api.list_factors(category="electricity")
    if electricity_factors:
        print(f"⚡ Found {electricity_factors['count']} electricity factors")
    
    # Get factors for 2025
    current_factors = api.list_factors(year=2025)
    if current_factors:
        print(f"📅 Found {current_factors['count']} factors for 2025")
    
    # Get Scope 1 factors
    scope1_factors = api.list_factors(scope="1")
    if scope1_factors:
        print(f"🏭 Found {scope1_factors['count']} Scope 1 factors")
    
    print("\n" + "="*50)
    print("DEMO COMPLETED!")
    print("="*50)


if __name__ == "__main__":
    main() 