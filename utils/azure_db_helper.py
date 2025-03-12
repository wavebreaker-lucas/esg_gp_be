import urllib.parse
import os
from azure.identity import DefaultAzureCredential

def get_db_connection_params():
    """
    Get database connection parameters using Azure AD authentication.
    Returns a dictionary with connection parameters for Django.
    """
    try:
        # Get Azure AD token
        credential = DefaultAzureCredential()
        token = credential.get_token("https://ossrdbms-aad.database.windows.net/.default").token

        # Get connection parameters from environment
        params = {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.getenv('DB_NAME'),
            'USER': os.getenv('DB_USER'),
            'PASSWORD': token,  # Use the Azure AD token as password
            'HOST': os.getenv('DB_HOST'),
            'PORT': os.getenv('DB_PORT'),
            'OPTIONS': {
                'sslmode': 'require',
                'client_encoding': 'UTF8'
            }
        }
        return params
    except Exception as e:
        print(f"Error getting database connection parameters: {str(e)}")
        # Fall back to standard authentication if Azure AD fails
        return {
            'ENGINE': os.getenv('DB_ENGINE'),
            'NAME': os.getenv('DB_NAME'),
            'USER': os.getenv('DB_USER'),
            'PASSWORD': os.getenv('DB_PASSWORD'),
            'HOST': os.getenv('DB_HOST'),
            'PORT': os.getenv('DB_PORT'),
            'OPTIONS': {
                'sslmode': 'require',
                'client_encoding': 'UTF8'
            }
        } 