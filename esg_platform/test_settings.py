"""
Test settings - uses SQLite database
"""

from .settings import *

# Override database settings to use SQLite
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'test_db.sqlite3',
    }
}

# Bypass Azure helper
def get_db_connection_params():
    return DATABASES['default']

# Override the Azure helper in settings
from utils import azure_db_helper
azure_db_helper.get_db_connection_params = get_db_connection_params 