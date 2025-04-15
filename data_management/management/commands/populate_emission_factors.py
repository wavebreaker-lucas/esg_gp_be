from django.core.management.base import BaseCommand
from decimal import Decimal
from data_management.models.factors import GHGEmissionFactor


class Command(BaseCommand):
    help = 'Populates the GHGEmissionFactor database with sample data'

    def handle(self, *args, **options):
        self.stdout.write('Starting emission factor population...')
        
        # Clear existing factors if needed
        # Uncomment the line below to clear all existing factors
        # GHGEmissionFactor.objects.all().delete()
        
        self.populate_electricity_factors()
        self.populate_towngas_factors()
        self.populate_transport_factors()
        
        total_count = GHGEmissionFactor.objects.count()
        self.stdout.write(self.style.SUCCESS(f"Completed! Total factors in database: {total_count}"))

    def create_factor(self, name, category, sub_category, activity_unit, value, factor_unit, 
                       year, region, scope, source="", source_url=""):
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
            self.stdout.write(f"{status} factor: {name}")
            return factor
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error creating factor {name}: {e}"))
            return None

    def populate_electricity_factors(self):
        """Populate electricity emission factors"""
        # Hong Kong Electric
        self.create_factor(
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
        self.create_factor(
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
        self.create_factor(
            name="Electricity - Northern China - 2023",
            category="electricity",
            sub_category="prc_northern",
            activity_unit="kWh",
            value=0.5703,
            factor_unit="kgCO2e/kWh",
            year=2023,
            region="PRC",
            scope="2",
            source="China Ministry of Environment 2023-2025 Greenhouse Gas Emission Report",
            source_url="https://www.mee.gov.cn/xxgk2018/xxgk/xxgk06/202310/t20231018_1043427.html"
        )
        
        # Northeast China
        self.create_factor(
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
        self.create_factor(
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
        self.create_factor(
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
        self.create_factor(
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

    def populate_towngas_factors(self):
        """Populate towngas emission factors"""
        self.create_factor(
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

    def populate_transport_factors(self):
        """Populate transport emission factors"""
        # HKEX Vehicle Emission Factors - Diesel vehicles
        self.create_factor(
            name="Diesel - Passenger Car",
            category="transport",
            sub_category="transport_cars_diesel",
            activity_unit="liters",
            value=2.6460,
            factor_unit="kgCO2e/liter",
            year=2023,
            region="HK / PRC",
            scope="1",
            source="HKEX Reporting Guidance",
            source_url="https://www.hkex.com.hk/-/media/hkex-market/listing/rules-and-guidance/environmental-social-and-governance/exchanges-guidance-materials-on-esg/app2_envirokpis"
        )
        
        # ADDED: Factor for 2025 ALL region
        self.create_factor(
            name="Diesel - Passenger Car - 2025 - ALL",
            category="transport",
            sub_category="transport_cars_diesel",
            activity_unit="liters",
            value=2.6460, # Using 2023 value as placeholder
            factor_unit="kgCO2e/liter",
            year=2025,
            region="ALL",
            scope="1",
            source="Derived from HKEX 2023 Guidance",
            source_url="https://www.hkex.com.hk/-/media/hkex-market/listing/rules-and-guidance/environmental-social-and-governance/exchanges-guidance-materials-on-esg/app2_envirokpis"
        )
        
        self.create_factor(
            name="Diesel - Private Van",
            category="transport",
            sub_category="transport_vans_diesel",
            activity_unit="liters",
            value=2.7541,
            factor_unit="kgCO2e/liter",
            year=2023,
            region="HK / PRC",
            scope="1",
            source="HKEX Reporting Guidance",
            source_url="https://www.hkex.com.hk/-/media/hkex-market/listing/rules-and-guidance/environmental-social-and-governance/exchanges-guidance-materials-on-esg/app2_envirokpis"
        )
        
        self.create_factor(
            name="Diesel - Public Light Bus",
            category="transport",
            sub_category="transport_bus_diesel",
            activity_unit="liters",
            value=2.7722,
            factor_unit="kgCO2e/liter",
            year=2023,
            region="HK / PRC",
            scope="1",
            source="HKEX Reporting Guidance",
            source_url="https://www.hkex.com.hk/-/media/hkex-market/listing/rules-and-guidance/environmental-social-and-governance/exchanges-guidance-materials-on-esg/app2_envirokpis"
        )
        
        self.create_factor(
            name="Diesel - Light Goods Vehicle",
            category="transport",
            sub_category="transport_light_goods_diesel",
            activity_unit="liters",
            value=2.7541,
            factor_unit="kgCO2e/liter",
            year=2023,
            region="HK / PRC",
            scope="1",
            source="HKEX Reporting Guidance",
            source_url="https://www.hkex.com.hk/-/media/hkex-market/listing/rules-and-guidance/environmental-social-and-governance/exchanges-guidance-materials-on-esg/app2_envirokpis"
        )
        
        # Add light commercial diesel factor to match VehicleTrackingMetric mapping
        self.create_factor(
            name="Diesel - Light Commercial Vehicle",
            category="transport",
            sub_category="transport_light_commercial_diesel",
            activity_unit="liters",
            value=2.7541,  # Same as light goods diesel
            factor_unit="kgCO2e/liter",
            year=2023,
            region="HK / PRC",
            scope="1",
            source="HKEX Reporting Guidance",
            source_url="https://www.hkex.com.hk/-/media/hkex-market/listing/rules-and-guidance/environmental-social-and-governance/exchanges-guidance-materials-on-esg/app2_envirokpis"
        )
        
        self.create_factor(
            name="Diesel - Medium Goods Vehicle",
            category="transport",
            sub_category="transport_medium_goods_diesel",
            activity_unit="liters",
            value=2.6377,
            factor_unit="kgCO2e/liter",
            year=2023,
            region="HK / PRC",
            scope="1",
            source="HKEX Reporting Guidance",
            source_url="https://www.hkex.com.hk/-/media/hkex-market/listing/rules-and-guidance/environmental-social-and-governance/exchanges-guidance-materials-on-esg/app2_envirokpis"
        )
        
        self.create_factor(
            name="Diesel - Heavy Goods Vehicle",
            category="transport",
            sub_category="transport_heavy_goods_diesel",
            activity_unit="liters",
            value=2.6377,
            factor_unit="kgCO2e/liter",
            year=2023,
            region="HK / PRC",
            scope="1",
            source="HKEX Reporting Guidance",
            source_url="https://www.hkex.com.hk/-/media/hkex-market/listing/rules-and-guidance/environmental-social-and-governance/exchanges-guidance-materials-on-esg/app2_envirokpis"
        )
        
        self.create_factor(
            name="Diesel - Other Mobile Machinery",
            category="transport",
            sub_category="transport_mobile_machinery_diesel",
            activity_unit="liters",
            value=2.6166,
            factor_unit="kgCO2e/liter",
            year=2023,
            region="HK / PRC",
            scope="1",
            source="HKEX Reporting Guidance",
            source_url="https://www.hkex.com.hk/-/media/hkex-market/listing/rules-and-guidance/environmental-social-and-governance/exchanges-guidance-materials-on-esg/app2_envirokpis"
        )
        
        # HKEX Vehicle Emission Factors - Petrol/Unleaded vehicles
        self.create_factor(
            name="Petrol - Motorcycle",
            category="transport",
            sub_category="transport_motorcycle_petrol",
            activity_unit="liters",
            value=2.4122,
            factor_unit="kgCO2e/liter",
            year=2023,
            region="HK / PRC",
            scope="1",
            source="HKEX Reporting Guidance",
            source_url="https://www.hkex.com.hk/-/media/hkex-market/listing/rules-and-guidance/environmental-social-and-governance/exchanges-guidance-materials-on-esg/app2_envirokpis"
        )
        
        self.create_factor(
            name="Petrol/Unleaded - Passenger Car",
            category="transport",
            sub_category="transport_cars_petrol",
            activity_unit="liters",
            value=2.6687,
            factor_unit="kgCO2e/liter",
            year=2023,
            region="HK / PRC",
            scope="1",
            source="HKEX Reporting Guidance",
            source_url="https://www.hkex.com.hk/-/media/hkex-market/listing/rules-and-guidance/environmental-social-and-governance/exchanges-guidance-materials-on-esg/app2_envirokpis"
        )
        
        # ADDED: Factor for 2025 ALL region (Petrol Cars)
        self.create_factor(
            name="Petrol/Unleaded - Passenger Car - 2025 - ALL",
            category="transport",
            sub_category="transport_cars_petrol",
            activity_unit="liters",
            value=2.6687, # Using 2023 value as placeholder
            factor_unit="kgCO2e/liter",
            year=2025,
            region="ALL",
            scope="1",
            source="Derived from HKEX 2023 Guidance",
            source_url="https://www.hkex.com.hk/-/media/hkex-market/listing/rules-and-guidance/environmental-social-and-governance/exchanges-guidance-materials-on-esg/app2_envirokpis"
        )
        
        self.create_factor(
            name="Petrol/Unleaded - Private Van",
            category="transport",
            sub_category="transport_vans_petrol",
            activity_unit="liters",
            value=2.6769,
            factor_unit="kgCO2e/liter",
            year=2023,
            region="HK / PRC",
            scope="1",
            source="HKEX Reporting Guidance",
            source_url="https://www.hkex.com.hk/-/media/hkex-market/listing/rules-and-guidance/environmental-social-and-governance/exchanges-guidance-materials-on-esg/app2_envirokpis"
        )
        
        self.create_factor(
            name="Petrol/Unleaded - Light Goods Vehicle",
            category="transport",
            sub_category="transport_light_goods_petrol",
            activity_unit="liters",
            value=2.6673,
            factor_unit="kgCO2e/liter",
            year=2023,
            region="HK / PRC",
            scope="1",
            source="HKEX Reporting Guidance",
            source_url="https://www.hkex.com.hk/-/media/hkex-market/listing/rules-and-guidance/environmental-social-and-governance/exchanges-guidance-materials-on-esg/app2_envirokpis"
        )
        
        # HKEX Vehicle Emission Factors - LPG vehicles
        self.create_factor(
            name="LPG - Private Van",
            category="transport",
            sub_category="transport_vans_lpg",
            activity_unit="liters",
            value=1.6859,
            factor_unit="kgCO2e/liter",
            year=2023,
            region="HK / PRC",
            scope="1",
            source="HKEX Reporting Guidance",
            source_url="https://www.hkex.com.hk/-/media/hkex-market/listing/rules-and-guidance/environmental-social-and-governance/exchanges-guidance-materials-on-esg/app2_envirokpis"
        )
        
        self.create_factor(
            name="LPG - Public Light Bus",
            category="transport",
            sub_category="transport_bus_lpg",
            activity_unit="liters",
            value=1.6859,
            factor_unit="kgCO2e/liter",
            year=2023,
            region="HK / PRC",
            scope="1",
            source="HKEX Reporting Guidance",
            source_url="https://www.hkex.com.hk/-/media/hkex-market/listing/rules-and-guidance/environmental-social-and-governance/exchanges-guidance-materials-on-esg/app2_envirokpis"
        )
        
        self.create_factor(
            name="LPG - Other Mobile Machinery",
            category="transport",
            sub_category="transport_mobile_machinery_lpg",
            activity_unit="liters",
            value=1.6791,
            factor_unit="kgCO2e/liter",
            year=2023,
            region="HK / PRC",
            scope="1",
            source="HKEX Reporting Guidance",
            source_url="https://www.hkex.com.hk/-/media/hkex-market/listing/rules-and-guidance/environmental-social-and-governance/exchanges-guidance-materials-on-esg/app2_envirokpis"
        )
        
        self.create_factor(
            name="LPG - Passenger Car",
            category="transport",
            sub_category="transport_cars_lpg",
            activity_unit="liters",
            value=1.6859,  # Using the same value as LPG vans/buses
            factor_unit="kgCO2e/liter",
            year=2023,
            region="HK / PRC",
            scope="1",
            source="HKEX Reporting Guidance",
            source_url="https://www.hkex.com.hk/-/media/hkex-market/listing/rules-and-guidance/environmental-social-and-governance/exchanges-guidance-materials-on-esg/app2_envirokpis"
        )
        
        # Fallback factors for generic vehicle types
        self.create_factor(
            name="Diesel - General Mobile",
            category="transport",
            sub_category="transport_general_diesel",
            activity_unit="liters",
            value=2.6166,  # Using mobile machinery as default
            factor_unit="kgCO2e/liter",
            year=2023,
            region="HK / PRC",
            scope="1",
            source="HKEX Reporting Guidance",
            source_url="https://www.hkex.com.hk/-/media/hkex-market/listing/rules-and-guidance/environmental-social-and-governance/exchanges-guidance-materials-on-esg/app2_envirokpis"
        )
        
        self.create_factor(
            name="Petrol - General Mobile",
            category="transport",
            sub_category="transport_general_petrol",
            activity_unit="liters",
            value=2.6687,  # Using passenger car as default
            factor_unit="kgCO2e/liter",
            year=2023,
            region="HK / PRC",
            scope="1",
            source="HKEX Reporting Guidance",
            source_url="https://www.hkex.com.hk/-/media/hkex-market/listing/rules-and-guidance/environmental-social-and-governance/exchanges-guidance-materials-on-esg/app2_envirokpis"
        )
        
        self.create_factor(
            name="LPG - General Mobile",
            category="transport",
            sub_category="transport_lpg",
            activity_unit="liters",
            value=1.6859,  # Using van/bus as default
            factor_unit="kgCO2e/liter",
            year=2023,
            region="HK / PRC",
            scope="1",
            source="HKEX Reporting Guidance",
            source_url="https://www.hkex.com.hk/-/media/hkex-market/listing/rules-and-guidance/environmental-social-and-governance/exchanges-guidance-materials-on-esg/app2_envirokpis"
        )
        
        # Additional ship/vessel factors
        self.create_factor(
            name="Gas Oil - Ship",
            category="transport",
            sub_category="transport_ship_gas_oil",
            activity_unit="liters",
            value=2.9480,
            factor_unit="kgCO2e/liter",
            year=2023,
            region="HK / PRC",
            scope="1",
            source="HKEX Reporting Guidance",
            source_url="https://www.hkex.com.hk/-/media/hkex-market/listing/rules-and-guidance/environmental-social-and-governance/exchanges-guidance-materials-on-esg/app2_envirokpis"
        )
        
        # Aviation factors
        self.create_factor(
            name="Jet Kerosene - Aviation",
            category="transport",
            sub_category="transport_aviation_kerosene",
            activity_unit="liters",
            value=2.4309,
            factor_unit="kgCO2e/liter",
            year=2023,
            region="HK / PRC",
            scope="1",
            source="HKEX Reporting Guidance",
            source_url="https://www.hkex.com.hk/-/media/hkex-market/listing/rules-and-guidance/environmental-social-and-governance/exchanges-guidance-materials-on-esg/app2_envirokpis"
        )
        
        # Additional factors to match the DEFAULT_EMISSION_MAPPING in VehicleTrackingMetric
        
        # For private_cars with different fuel types
        # (Already have diesel, petrol, and LPG above)
        
        # For light_goods_lte_2_5 with different fuel types
        # For diesel_oil - using transport_light_commercial_diesel
        # This is already mapped in the emission_factor_mapping
        
        # For light_goods_lte_2_5 with petrol
        self.create_factor(
            name="Petrol - Light Goods Vehicle (<=2.5tonnes)",
            category="transport",
            sub_category="transport_light_goods_lte_2_5_petrol",
            activity_unit="liters",
            value=2.6673,  # Using standard Light Goods Vehicle petrol value
            factor_unit="kgCO2e/liter",
            year=2023,
            region="HK / PRC",
            scope="1",
            source="HKEX Reporting Guidance - Derived",
            source_url="https://www.hkex.com.hk/-/media/hkex-market/listing/rules-and-guidance/environmental-social-and-governance/exchanges-guidance-materials-on-esg/app2_envirokpis"
        )
        
        # For light_goods_lte_2_5 with unleaded_petrol
        self.create_factor(
            name="Unleaded Petrol - Light Goods Vehicle (<=2.5tonnes)",
            category="transport",
            sub_category="transport_light_goods_lte_2_5_unleaded_petrol",
            activity_unit="liters",
            value=2.6673,  # Using standard Light Goods Vehicle petrol value
            factor_unit="kgCO2e/liter",
            year=2023,
            region="HK / PRC",
            scope="1",
            source="HKEX Reporting Guidance - Derived",
            source_url="https://www.hkex.com.hk/-/media/hkex-market/listing/rules-and-guidance/environmental-social-and-governance/exchanges-guidance-materials-on-esg/app2_envirokpis"
        )
        
        # For light_goods_lte_2_5 with LPG
        self.create_factor(
            name="LPG - Light Goods Vehicle (<=2.5tonnes)",
            category="transport",
            sub_category="transport_light_goods_lte_2_5_lpg",
            activity_unit="liters",
            value=1.6859,  # Using LPG van/bus value
            factor_unit="kgCO2e/liter",
            year=2023,
            region="HK / PRC",
            scope="1",
            source="HKEX Reporting Guidance - Derived",
            source_url="https://www.hkex.com.hk/-/media/hkex-market/listing/rules-and-guidance/environmental-social-and-governance/exchanges-guidance-materials-on-esg/app2_envirokpis"
        )
        
        # For light_goods_2_5_3_5 with petrol
        self.create_factor(
            name="Petrol - Light Goods Vehicle (2.5-3.5tonnes)",
            category="transport",
            sub_category="transport_light_goods_2_5_3_5_petrol",
            activity_unit="liters",
            value=2.6673,  # Using standard Light Goods Vehicle petrol value
            factor_unit="kgCO2e/liter",
            year=2023,
            region="HK / PRC",
            scope="1",
            source="HKEX Reporting Guidance - Derived",
            source_url="https://www.hkex.com.hk/-/media/hkex-market/listing/rules-and-guidance/environmental-social-and-governance/exchanges-guidance-materials-on-esg/app2_envirokpis"
        )
        
        # For light_goods_2_5_3_5 with unleaded_petrol
        self.create_factor(
            name="Unleaded Petrol - Light Goods Vehicle (2.5-3.5tonnes)",
            category="transport",
            sub_category="transport_light_goods_2_5_3_5_unleaded_petrol",
            activity_unit="liters",
            value=2.6673,  # Using standard Light Goods Vehicle petrol value
            factor_unit="kgCO2e/liter",
            year=2023,
            region="HK / PRC",
            scope="1",
            source="HKEX Reporting Guidance - Derived",
            source_url="https://www.hkex.com.hk/-/media/hkex-market/listing/rules-and-guidance/environmental-social-and-governance/exchanges-guidance-materials-on-esg/app2_envirokpis"
        )
        
        # For light_goods_2_5_3_5 with LPG
        self.create_factor(
            name="LPG - Light Goods Vehicle (2.5-3.5tonnes)",
            category="transport",
            sub_category="transport_light_goods_2_5_3_5_lpg",
            activity_unit="liters",
            value=1.6859,  # Using LPG van/bus value
            factor_unit="kgCO2e/liter",
            year=2023,
            region="HK / PRC",
            scope="1",
            source="HKEX Reporting Guidance - Derived",
            source_url="https://www.hkex.com.hk/-/media/hkex-market/listing/rules-and-guidance/environmental-social-and-governance/exchanges-guidance-materials-on-esg/app2_envirokpis"
        )
        
        # For light_goods_3_5_5_5 with petrol
        self.create_factor(
            name="Petrol - Light Goods Vehicle (3.5-5.5tonnes)",
            category="transport",
            sub_category="transport_light_goods_3_5_5_5_petrol",
            activity_unit="liters",
            value=2.6673,  # Using standard Light Goods Vehicle petrol value
            factor_unit="kgCO2e/liter",
            year=2023,
            region="HK / PRC",
            scope="1",
            source="HKEX Reporting Guidance - Derived",
            source_url="https://www.hkex.com.hk/-/media/hkex-market/listing/rules-and-guidance/environmental-social-and-governance/exchanges-guidance-materials-on-esg/app2_envirokpis"
        )
        
        # For light_goods_3_5_5_5 with unleaded_petrol
        self.create_factor(
            name="Unleaded Petrol - Light Goods Vehicle (3.5-5.5tonnes)",
            category="transport",
            sub_category="transport_light_goods_3_5_5_5_unleaded_petrol",
            activity_unit="liters",
            value=2.6673,  # Using standard Light Goods Vehicle petrol value
            factor_unit="kgCO2e/liter",
            year=2023,
            region="HK / PRC",
            scope="1",
            source="HKEX Reporting Guidance - Derived",
            source_url="https://www.hkex.com.hk/-/media/hkex-market/listing/rules-and-guidance/environmental-social-and-governance/exchanges-guidance-materials-on-esg/app2_envirokpis"
        )
        
        # For light_goods_3_5_5_5 with LPG
        self.create_factor(
            name="LPG - Light Goods Vehicle (3.5-5.5tonnes)",
            category="transport",
            sub_category="transport_light_goods_3_5_5_5_lpg",
            activity_unit="liters",
            value=1.6859,  # Using LPG van/bus value
            factor_unit="kgCO2e/liter",
            year=2023,
            region="HK / PRC",
            scope="1",
            source="HKEX Reporting Guidance - Derived",
            source_url="https://www.hkex.com.hk/-/media/hkex-market/listing/rules-and-guidance/environmental-social-and-governance/exchanges-guidance-materials-on-esg/app2_envirokpis"
        )
        
        # For medium_heavy_goods_5_5_15 with petrol
        self.create_factor(
            name="Petrol - Medium/Heavy Goods Vehicle (5.5-15tonnes)",
            category="transport",
            sub_category="transport_medium_heavy_goods_5_5_15_petrol",
            activity_unit="liters",
            value=2.6673,  # Using Light Goods Vehicle petrol value as approximation
            factor_unit="kgCO2e/liter",
            year=2023,
            region="HK / PRC",
            scope="1",
            source="HKEX Reporting Guidance - Derived",
            source_url="https://www.hkex.com.hk/-/media/hkex-market/listing/rules-and-guidance/environmental-social-and-governance/exchanges-guidance-materials-on-esg/app2_envirokpis"
        )
        
        # For medium_heavy_goods_5_5_15 with unleaded_petrol
        self.create_factor(
            name="Unleaded Petrol - Medium/Heavy Goods Vehicle (5.5-15tonnes)",
            category="transport",
            sub_category="transport_medium_heavy_goods_5_5_15_unleaded_petrol",
            activity_unit="liters",
            value=2.6673,  # Using Light Goods Vehicle petrol value as approximation
            factor_unit="kgCO2e/liter",
            year=2023,
            region="HK / PRC",
            scope="1",
            source="HKEX Reporting Guidance - Derived",
            source_url="https://www.hkex.com.hk/-/media/hkex-market/listing/rules-and-guidance/environmental-social-and-governance/exchanges-guidance-materials-on-esg/app2_envirokpis"
        )
        
        # For medium_heavy_goods_5_5_15 with LPG
        self.create_factor(
            name="LPG - Medium/Heavy Goods Vehicle (5.5-15tonnes)",
            category="transport",
            sub_category="transport_medium_heavy_goods_5_5_15_lpg",
            activity_unit="liters",
            value=1.6859,  # Using LPG van/bus value
            factor_unit="kgCO2e/liter",
            year=2023,
            region="HK / PRC",
            scope="1",
            source="HKEX Reporting Guidance - Derived",
            source_url="https://www.hkex.com.hk/-/media/hkex-market/listing/rules-and-guidance/environmental-social-and-governance/exchanges-guidance-materials-on-esg/app2_envirokpis"
        )
        
        # For medium_heavy_goods_gte_15 with petrol
        self.create_factor(
            name="Petrol - Medium/Heavy Goods Vehicle (>=15tonnes)",
            category="transport",
            sub_category="transport_medium_heavy_goods_gte_15_petrol",
            activity_unit="liters",
            value=2.6673,  # Using Light Goods Vehicle petrol value as approximation
            factor_unit="kgCO2e/liter",
            year=2023,
            region="HK / PRC",
            scope="1",
            source="HKEX Reporting Guidance - Derived",
            source_url="https://www.hkex.com.hk/-/media/hkex-market/listing/rules-and-guidance/environmental-social-and-governance/exchanges-guidance-materials-on-esg/app2_envirokpis"
        )
        
        # For medium_heavy_goods_gte_15 with unleaded_petrol
        self.create_factor(
            name="Unleaded Petrol - Medium/Heavy Goods Vehicle (>=15tonnes)",
            category="transport",
            sub_category="transport_medium_heavy_goods_gte_15_unleaded_petrol",
            activity_unit="liters",
            value=2.6673,  # Using Light Goods Vehicle petrol value as approximation
            factor_unit="kgCO2e/liter",
            year=2023,
            region="HK / PRC",
            scope="1",
            source="HKEX Reporting Guidance - Derived",
            source_url="https://www.hkex.com.hk/-/media/hkex-market/listing/rules-and-guidance/environmental-social-and-governance/exchanges-guidance-materials-on-esg/app2_envirokpis"
        )
        
        # For medium_heavy_goods_gte_15 with LPG
        self.create_factor(
            name="LPG - Medium/Heavy Goods Vehicle (>=15tonnes)",
            category="transport",
            sub_category="transport_medium_heavy_goods_gte_15_lpg",
            activity_unit="liters",
            value=1.6859,  # Using LPG van/bus value
            factor_unit="kgCO2e/liter",
            year=2023,
            region="HK / PRC",
            scope="1",
            source="HKEX Reporting Guidance - Derived",
            source_url="https://www.hkex.com.hk/-/media/hkex-market/listing/rules-and-guidance/environmental-social-and-governance/exchanges-guidance-materials-on-esg/app2_envirokpis"
        ) 