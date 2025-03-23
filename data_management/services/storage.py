from datetime import datetime, timedelta, timezone
from django.conf import settings
from storages.backends.azure_storage import AzureStorage
from azure.storage.blob import generate_blob_sas, BlobSasPermissions
import logging

logger = logging.getLogger(__name__)

class ESGAzureStorage(AzureStorage):
    """
    Custom Azure storage class that generates signed URLs (SAS tokens)
    for accessing blobs without requiring public access on the storage account.
    """
    
    def url(self, name, expire=None):
        """
        Generate a signed URL with a SAS token that expires after the specified time.
        
        Args:
            name: Name of the blob (file path)
            expire: Expiration time in seconds from now (default: 86400 seconds = 24 hours)
        
        Returns:
            Signed URL with SAS token for secure blob access
        """
        # Default expiration: 24 hours
        if expire is None:
            expire = 86400  # 24 hours in seconds
        
        # Get the account name and key from settings
        account_name = self.account_name
        account_key = self.account_key
        
        # Check if we have the required credentials
        if not account_name or not account_key:
            logger.error("Azure Storage credentials not properly configured")
            return super().url(name)  # Fall back to default behavior
        
        try:
            # Create start and expiry times for the SAS token
            # Use datetime.now(timezone.utc) instead of the deprecated utcnow()
            start_time = datetime.now(timezone.utc)
            expiry_time = start_time + timedelta(seconds=expire)
            
            # Generate SAS token with read permission
            sas_token = generate_blob_sas(
                account_name=account_name,
                container_name=self.azure_container,
                blob_name=name,
                account_key=account_key,
                permission=BlobSasPermissions(read=True),
                start=start_time,
                expiry=expiry_time
            )
            
            # Create the full URL with SAS token
            blob_url = f"https://{account_name}.blob.core.windows.net/{self.azure_container}/{name}?{sas_token}"
            return blob_url
            
        except Exception as e:
            # Log the error and fall back to default behavior
            logger.exception(f"Error generating SAS token for {name}: {str(e)}")
            return super().url(name) 