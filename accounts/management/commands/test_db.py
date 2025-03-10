from django.core.management.base import BaseCommand
from django.db import connections
from django.db.utils import OperationalError
from django.conf import settings
import sys

class Command(BaseCommand):
    help = 'Test database connection'

    def handle(self, *args, **kwargs):
        db_conn = connections['default']
        try:
            db_conn.cursor()
            self.stdout.write(
                self.style.SUCCESS('Successfully connected to the database!')
            )
            self.stdout.write(
                self.style.SUCCESS(f"Database: {settings.DATABASES['default']['NAME']}")
            )
            self.stdout.write(
                self.style.SUCCESS(f"Host: {settings.DATABASES['default']['HOST']}")
            )
        except OperationalError as e:
            self.stdout.write(
                self.style.ERROR(f'Database connection failed! Error: {e}')
            )
            sys.exit(1) 