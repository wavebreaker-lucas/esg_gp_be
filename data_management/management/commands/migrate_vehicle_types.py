from django.core.management.base import BaseCommand
from django.db import transaction
from data_management.models.polymorphic_metrics import VehicleTrackingMetric, VehicleType, FuelType
from data_management.models.submission_data import VehicleRecord


class Command(BaseCommand):
    help = 'Migrates VehicleTrackingMetric data from JSONFields to relational models'

    def handle(self, *args, **options):
        self.stdout.write('Starting migration of vehicle types and fuel types...')
        
        # Wrap everything in a transaction
        with transaction.atomic():
            # First, create all vehicle types from across all metrics
            self.create_vehicle_types()
            
            # Then create all fuel types
            self.create_fuel_types()
            
            # Update metric relationships
            self.update_metric_relationships()
            
            # Update vehicle records to use the new foreign keys
            self.update_vehicle_records()
            
        self.stdout.write(self.style.SUCCESS('Successfully migrated vehicle types and fuel types!'))

    def create_vehicle_types(self):
        """Create VehicleType records from JSONField data"""
        self.stdout.write('Creating vehicle types...')
        
        # Get all unique vehicle types from all metrics
        all_vehicle_types = set()
        for metric in VehicleTrackingMetric.objects.all():
            for vehicle_type in metric.vehicle_type_choices:
                if isinstance(vehicle_type, dict) and 'value' in vehicle_type and 'label' in vehicle_type:
                    all_vehicle_types.add((vehicle_type['value'], vehicle_type['label']))
        
        # Create vehicle types
        count = 0
        for value, label in all_vehicle_types:
            vehicle_type, created = VehicleType.objects.get_or_create(
                value=value,
                defaults={'label': label}
            )
            if created:
                count += 1
                
        self.stdout.write(f'Created {count} new vehicle types')

    def create_fuel_types(self):
        """Create FuelType records from JSONField data"""
        self.stdout.write('Creating fuel types...')
        
        # Get all unique fuel types from all metrics
        all_fuel_types = set()
        for metric in VehicleTrackingMetric.objects.all():
            for fuel_type in metric.fuel_type_choices:
                if isinstance(fuel_type, dict) and 'value' in fuel_type and 'label' in fuel_type:
                    all_fuel_types.add((fuel_type['value'], fuel_type['label']))
        
        # Create fuel types
        count = 0
        for value, label in all_fuel_types:
            fuel_type, created = FuelType.objects.get_or_create(
                value=value,
                defaults={'label': label}
            )
            if created:
                count += 1
                
        self.stdout.write(f'Created {count} new fuel types')

    def update_metric_relationships(self):
        """Update M2M relationships between metrics and types"""
        self.stdout.write('Updating metric relationships...')
        
        # For each metric, associate with the vehicle types and fuel types
        count = 0
        for metric in VehicleTrackingMetric.objects.all():
            # Add vehicle types
            for vehicle_type_data in metric.vehicle_type_choices:
                if isinstance(vehicle_type_data, dict) and 'value' in vehicle_type_data:
                    try:
                        vehicle_type = VehicleType.objects.get(value=vehicle_type_data['value'])
                        metric.vehicle_types.add(vehicle_type)
                    except VehicleType.DoesNotExist:
                        self.stderr.write(f"Vehicle type with value '{vehicle_type_data['value']}' not found")
            
            # Add fuel types
            for fuel_type_data in metric.fuel_type_choices:
                if isinstance(fuel_type_data, dict) and 'value' in fuel_type_data:
                    try:
                        fuel_type = FuelType.objects.get(value=fuel_type_data['value'])
                        metric.fuel_types.add(fuel_type)
                    except FuelType.DoesNotExist:
                        self.stderr.write(f"Fuel type with value '{fuel_type_data['value']}' not found")
            
            count += 1
            
        self.stdout.write(f'Updated {count} metrics')

    def update_vehicle_records(self):
        """Update vehicle records to use the new foreign keys"""
        self.stdout.write('Updating vehicle records...')
        
        # For each vehicle record, update the foreign keys
        count = 0
        errors = 0
        for vehicle in VehicleRecord.objects.all():
            try:
                # Store the original values for backward compatibility
                vehicle.vehicle_type_code = vehicle.vehicle_type
                vehicle.fuel_type_code = vehicle.fuel_type
                
                # Get the vehicle type and fuel type instances
                vehicle_type = VehicleType.objects.get(value=vehicle.vehicle_type_code)
                fuel_type = FuelType.objects.get(value=vehicle.fuel_type_code)
                
                # Update the vehicle
                vehicle.vehicle_type = vehicle_type
                vehicle.fuel_type = fuel_type
                vehicle.save()
                
                count += 1
            except (VehicleType.DoesNotExist, FuelType.DoesNotExist) as e:
                self.stderr.write(f"Error updating vehicle {vehicle.pk}: {e}")
                errors += 1
                
        self.stdout.write(f'Updated {count} vehicle records, {errors} errors') 