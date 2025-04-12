#!/usr/bin/env python
"""
Script to populate the GHGEmissionFactor database with sample data.
Run with: python manage.py shell < data_management/scripts/populate_emission_factors.py
"""

import sys
import os
import django
import datetime

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "esg_platform.settings")
django.setup()

from data_management.models.factors import GHGEmissionFactor
from decimal import Decimal

def create_factor(
    name, 
    category,
    sub_category,
    activity_unit,
    value,
    factor_unit,
    year,
    region,
    scope,
    source="",
    source_url="",
):
    """Helper function to create a factor with error handling"""
    try:
        factor, created = GHGEmissionFactor.objects.update_or_create(
            category=category,
            sub_category=sub_category,
            activity_unit=activity_unit,
            region=region,
            year=year,
            scope=scope,
            defaults={
                'name': name,
                'value': Decimal(str(value)),
                'factor_unit': factor_unit,
                'source': source,
                'source_url': source_url
            }
        )
        status = "Created" if created else "Updated"
        print(f"{status} factor: {name}")
        return factor
    except Exception as e:
        print(f"Error creating factor {name}: {e}")
        return None

def populate_electricity_factors():
    """Populate electricity emission factors"""
    # Hong Kong Electric
    create_factor(
        name="Electricity - HK Electric - 2023",
        category="electricity",
        sub_category="hk_hke",
        activity_unit="kWh",
        value=0.7100,
        factor_unit="kgCO2e/kWh",
        year=2023,
        region="HK",
        scope="2",
        source="HK Electric Investments Sustainability Report 2023",
        source_url="https://www.hkelectric.com/documents/zh/CorporateSocialResponsibility/CorporateSocialResponsibility_CDD/Documents/SR2023C.pdf"
    )
    
    # CLP Power
    create_factor(
        name="Electricity - CLP Power - 2023",
        category="electricity",
        sub_category="hk_clp",
        activity_unit="kWh",
        value=0.3900,
        factor_unit="kgCO2e/kWh",
        year=2023,
        region="HK",
        scope="2",
        source="CLP Holdings 2023 Sustainability Report",
        source_url="https://www.clpgroup.com/content/dam/clp-group/channels/sustainability/document/sustainability-report/2023/CLP_Sustainability_Report_2023_en.pdf.coredownload.pdf"
    )
    
    # Northern China
    create_factor(
        name="Electricity - Northern China - 2023",
        category="electricity",
        sub_category="prc_northern",
        activity_unit="kWh",
        value=0.5703,
        factor_unit="kgCO2e/kWh",
        year=2023,
        region="PRC",
        scope="2",
        source="关于做好2023—2025年部分重点行业企业温室气体排放报告与核查工作的通知",
        source_url="https://www.mee.gov.cn/xxgk2018/xxgk/xxgk06/202310/t20231018_1043427.html"
    )
    
    # Northeast China
    create_factor(
        name="Electricity - Northeast China - 2023",
        category="electricity",
        sub_category="prc_northeast",
        activity_unit="kWh",
        value=0.5703,
        factor_unit="kgCO2e/kWh",
        year=2023,
        region="PRC",
        scope="2"
    )
    
    # Eastern China
    create_factor(
        name="Electricity - Eastern China - 2023",
        category="electricity",
        sub_category="prc_eastern",
        activity_unit="kWh",
        value=0.5703,
        factor_unit="kgCO2e/kWh",
        year=2023,
        region="PRC",
        scope="2"
    )
    
    # Malaysia
    create_factor(
        name="Electricity - Malaysia - 2019",
        category="electricity",
        sub_category="my_peninsula",
        activity_unit="kWh",
        value=0.5600,
        factor_unit="kgCO2e/kWh",
        year=2019,
        region="MY",
        scope="2",
        source="TNB Sustainability Report 2019",
        source_url="https://www.tnb.com.my/assets/annual_report/TNB_Sustainability_Report_2019.pdf"
    )
    
    # Singapore
    create_factor(
        name="Electricity - Singapore - 2020",
        category="electricity",
        sub_category="sg_main",
        activity_unit="kWh",
        value=0.4085,
        factor_unit="kgCO2e/kWh",
        year=2020,
        region="SG",
        scope="2",
        source="Table of Contents for SES 2020",
        source_url="https://www.ema.gov.sg/singapore-energy-statistics/Ch02/index2"
    )

def populate_towngas_factors():
    """Populate towngas emission factors"""
    create_factor(
        name="Towngas - Hong Kong - 2021",
        category="towngas",
        sub_category="hk_indirect",
        activity_unit="Unit",
        value=0.5880,
        factor_unit="kgCO2e/Unit",
        year=2021,
        region="HK",
        scope="2",
        source="Towngas Sustainability Report 2021",
        source_url="https://www.towngas.com/getmedia/4b9ef6b8-5a59-4f07-b045-f0f6a7b08c98/TG-AR2021_eng_full.pdf.aspx?ext=.pdf"
    )

def populate_transport_factors():
    """Populate transport emission factors with both scope 1 and scope 3 examples"""
    # Company vehicles (Scope 1)
    create_factor(
        name="Gasoline - Mobile Combustion - Company Vehicles - 2023",
        category="transport",
        sub_category="company_gasoline",
        activity_unit="liters",
        value=2.33,
        factor_unit="kgCO2e/liter",
        year=2023,
        region="ALL",
        scope="1",
        source="HKEX Reporting Guidance"
    )
    
    # Employee commuting (Scope 3)
    create_factor(
        name="Gasoline - Mobile Combustion - Employee Commuting - 2023",
        category="transport",
        sub_category="employee_commuting_gasoline",
        activity_unit="liters",
        value=2.94,
        factor_unit="kgCO2e/liter",
        year=2023,
        region="ALL",
        scope="3",
        source="HKEX Reporting Guidance"
    )

def main():
    """Main function to populate all factor types"""
    print("Starting emission factor population...")
    
    # Clear existing factors if needed
    # Uncomment the line below to clear all existing factors
    # GHGEmissionFactor.objects.all().delete()
    
    populate_electricity_factors()
    populate_towngas_factors()
    populate_transport_factors()
    
    total_count = GHGEmissionFactor.objects.count()
    print(f"Completed! Total factors in database: {total_count}")

if __name__ == "__main__":
    main() 