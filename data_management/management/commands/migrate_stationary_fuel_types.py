from django.core.management.base import BaseCommand
from django.db import transaction
from data_management.models.polymorphic_metrics import FuelConsumptionMetric, FuelSourceType, StationaryFuelType
from data_management.models.submission_data import FuelRecord


class Command(BaseCommand):
    help = 'Migrates fuel consumption data from FuelType to StationaryFuelType model'

    def handle(self, *args, **options):
        self.stdout.write('Starting migration of stationary fuel types and source types...')
        
        # Wrap everything in a transaction
        with transaction.atomic():
            # First, create all source types from across all metrics
            self.create_source_types()
            
            # Then create all stationary fuel types
            self.create_stationary_fuel_types()
            
            # Update metric relationships
            self.update_metric_relationships()
            
            # Update fuel records to use the new foreign keys
            self.update_fuel_records()
            
        self.stdout.write(self.style.SUCCESS('Successfully migrated stationary fuel types and source types!'))

    def create_source_types(self):
        """Create FuelSourceType records from JSONField data"""
        self.stdout.write('Creating source types...')
        
        # Get all unique source types from all metrics
        all_source_types = set()
        for metric in FuelConsumptionMetric.objects.all():
            for source_type in metric.source_type_choices:
                if isinstance(source_type, dict) and 'value' in source_type and 'label' in source_type:
                    all_source_types.add((source_type['value'], source_type['label']))
        
        # Create source types
        count = 0
        for value, label in all_source_types:
            source_type, created = FuelSourceType.objects.get_or_create(
                value=value,
                defaults={'label': label}
            )
            if created:
                count += 1
                
        self.stdout.write(f'Created {count} new source types')

        # Also create the default source types
        for source_type in FuelConsumptionMetric.DEFAULT_SOURCE_TYPES:
            value = source_type['value']
            label = source_type['label']
            source_type, created = FuelSourceType.objects.get_or_create(
                value=value,
                defaults={'label': label}
            )
            if created:
                count += 1
                
        self.stdout.write(f'Created a total of {count} source types')

    def create_stationary_fuel_types(self):
        """Create StationaryFuelType records from JSONField data"""
        self.stdout.write('Creating stationary fuel types...')
        
        # Get all unique fuel types from all metrics
        all_fuel_types = set()
        for metric in FuelConsumptionMetric.objects.all():
            for fuel_type in metric.fuel_type_choices:
                if isinstance(fuel_type, dict) and 'value' in fuel_type and 'label' in fuel_type:
                    # Extract unit from label if possible, otherwise use default
                    label = fuel_type['label']
                    unit = 'litre'  # Default
                    
                    # Try to extract unit from label if in parentheses
                    if '(' in label and ')' in label:
                        unit_part = label.split('(')[1].split(')')[0]
                        if unit_part.startswith('in '):
                            unit = unit_part[3:].strip().lower()
                    
                    all_fuel_types.add((fuel_type['value'], label.split(' (')[0] if ' (' in label else label, unit))
        
        # Create fuel types
        count = 0
        for value, label, unit in all_fuel_types:
            fuel_type, created = StationaryFuelType.objects.get_or_create(
                value=value,
                defaults={'label': label, 'unit': unit}
            )
            if created:
                count += 1
                
        self.stdout.write(f'Created {count} stationary fuel types from metrics')
                
        # Also create the default fuel types
        default_count = 0
        for fuel_type in FuelConsumptionMetric.DEFAULT_FUEL_TYPES:
            value = fuel_type['value']
            label = fuel_type['label']
            unit = fuel_type.get('unit', 'litre')
            
            fuel_type, created = StationaryFuelType.objects.get_or_create(
                value=value,
                defaults={'label': label, 'unit': unit}
            )
            if created:
                default_count += 1
                
        self.stdout.write(f'Created {default_count} additional stationary fuel types from defaults')
        self.stdout.write(f'Created a total of {count + default_count} stationary fuel types')

    def update_metric_relationships(self):
        """Update M2M relationships between metrics and types"""
        self.stdout.write('Updating metric relationships...')
        
        # For each metric, associate with the source types and fuel types
        count = 0
        for metric in FuelConsumptionMetric.objects.all():
            # Add source types
            for source_type_data in metric.source_type_choices:
                if isinstance(source_type_data, dict) and 'value' in source_type_data:
                    try:
                        source_type = FuelSourceType.objects.get(value=source_type_data['value'])
                        metric.source_types.add(source_type)
                    except FuelSourceType.DoesNotExist:
                        self.stderr.write(f"Source type with value '{source_type_data['value']}' not found")
            
            # Add fuel types
            for fuel_type_data in metric.fuel_type_choices:
                if isinstance(fuel_type_data, dict) and 'value' in fuel_type_data:
                    try:
                        fuel_type = StationaryFuelType.objects.get(value=fuel_type_data['value'])
                        metric.fuel_types.add(fuel_type)
                    except StationaryFuelType.DoesNotExist:
                        self.stderr.write(f"Stationary fuel type with value '{fuel_type_data['value']}' not found")
            
            count += 1
            
        self.stdout.write(f'Updated {count} metrics')

        # Also make sure all metrics have all the default fuel types
        for metric in FuelConsumptionMetric.objects.all():
            # Add any missing default source types
            for source_type_data in FuelConsumptionMetric.DEFAULT_SOURCE_TYPES:
                try:
                    source_type = FuelSourceType.objects.get(value=source_type_data['value'])
                    if not metric.source_types.filter(pk=source_type.pk).exists():
                        metric.source_types.add(source_type)
                except FuelSourceType.DoesNotExist:
                    self.stderr.write(f"Default source type '{source_type_data['value']}' not found")

            # Add any missing default fuel types
            for fuel_type_data in FuelConsumptionMetric.DEFAULT_FUEL_TYPES:
                try:
                    fuel_type = StationaryFuelType.objects.get(value=fuel_type_data['value'])
                    if not metric.fuel_types.filter(pk=fuel_type.pk).exists():
                        metric.fuel_types.add(fuel_type)
                except StationaryFuelType.DoesNotExist:
                    self.stderr.write(f"Default fuel type '{fuel_type_data['value']}' not found")

    def update_fuel_records(self):
        """Update fuel records to use the new foreign keys (for existing data)"""
        self.stdout.write('Checking for existing fuel records...')
        
        # Skip this if you're implementing this before any FuelRecord objects are created
        # But include code to migrate in case there are any
        try:
            record_count = FuelRecord.objects.count()
            if record_count > 0:
                self.stdout.write(f'Found {record_count} fuel records - manual migration required')
                self.stdout.write('You need to manually update the fuel_type field on existing FuelRecord objects')
                self.stdout.write('Existing records will need to be deleted or updated manually via SQL')
            else:
                self.stdout.write('No existing fuel records found - no migration needed')
        except Exception as e:
            self.stderr.write(f"Error checking fuel records: {e}") 