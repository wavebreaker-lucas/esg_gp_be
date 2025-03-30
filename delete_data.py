import os
import django

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'esg_platform.settings')
django.setup()

from django.db import connection

# Delete data using raw SQL
with connection.cursor() as cursor:
    # First delete evidence records that reference submissions
    print("Deleting evidence records...")
    cursor.execute("DELETE FROM data_management_esgmetricevidence WHERE submission_id IS NOT NULL;")
    evidence_count = cursor.rowcount
    print(f"Deleted {evidence_count} evidence records")
    
    # Then delete the submission records
    print("Deleting submission records...")
    cursor.execute("DELETE FROM data_management_esgmetricsubmission;")
    submission_count = cursor.rowcount
    print(f"Deleted {submission_count} submission records")
    
    print("Deletion complete!") 