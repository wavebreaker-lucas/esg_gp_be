from django.core.management.base import BaseCommand
from django.db import connection
from django.apps import apps

class Command(BaseCommand):
    help = 'Truncates all tables in the database managed by Django, except for migration history.'

    def handle(self, *args, **options):
        with connection.cursor() as cursor:
            # Get all models registered with Django
            all_models = apps.get_models()
            # Exclude migration history table
            table_names = [model._meta.db_table for model in all_models if model._meta.db_table != 'django_migrations']

            if not table_names:
                self.stdout.write(self.style.SUCCESS('No tables found to truncate (excluding migration history).'))
                return

            # Ensure tables exist before truncating
            cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
            existing_tables = {row[0] for row in cursor.fetchall()}

            tables_to_truncate = [name for name in table_names if name in existing_tables]

            if not tables_to_truncate:
                self.stdout.write(self.style.WARNING('Could not find any of the managed tables in the database.'))
                return

            # Generate and execute the TRUNCATE statement
            # Using CASCADE to handle foreign key constraints
            # Using RESTART IDENTITY to reset sequences
            truncate_command = f"TRUNCATE TABLE {', '.join(tables_to_truncate)} RESTART IDENTITY CASCADE;"

            try:
                self.stdout.write(f'Attempting to truncate tables: {tables_to_truncate}')
                cursor.execute(truncate_command)
                self.stdout.write(self.style.SUCCESS('Successfully truncated all specified tables.'))
            except Exception as e:
                self.stderr.write(self.style.ERROR(f'Error truncating tables: {e}'))
                self.stderr.write(self.style.WARNING('You might need to manually truncate tables or check permissions.')) 