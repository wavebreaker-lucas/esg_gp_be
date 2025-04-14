#!/usr/bin/env python
"""
Script to run the emission factor population directly.
Run with: python manage.py runscript run_populate_factors
"""

import os
import django
import sys

# Setup Django if running as standalone script
if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "esg_platform.settings")
    django.setup()

from data_management.scripts.populate_emission_factors import (
    populate_electricity_factors,
    populate_towngas_factors,
    populate_transport_factors
)

def run():
    """Main function to be called by the Django runscript command"""
    print("Starting emission factor population...")
    
    # Run the population functions
    populate_electricity_factors()
    populate_towngas_factors()
    populate_transport_factors()
    
    # Check the total count
    from data_management.models.factors import GHGEmissionFactor
    total_count = GHGEmissionFactor.objects.count()
    print(f"Completed! Total factors in database: {total_count}")

# If running directly, call the run function
if __name__ == "__main__":
    run() 