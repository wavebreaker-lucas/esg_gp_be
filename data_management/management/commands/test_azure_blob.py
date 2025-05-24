from django.core.management.base import BaseCommand
import os
from azure.storage.blob import BlobServiceClient

class Command(BaseCommand):
    help = 'Test Azure Blob Storage access'

    def handle(self, *args, **kwargs):
        account_name = os.getenv('AZURE_STORAGE_ACCOUNT_NAME')
        account_key = os.getenv('AZURE_STORAGE_ACCOUNT_KEY')
        container = os.getenv('AZURE_STORAGE_CONTAINER')
        print("Account Name:", account_name)
        print("Account Key:", "SET" if account_key else "NOT SET")
        print("Container:", container)
        try:
            conn_str = f"DefaultEndpointsProtocol=https;AccountName={account_name};AccountKey={account_key};EndpointSuffix=core.windows.net"
            client = BlobServiceClient.from_connection_string(conn_str)
            container_client = client.get_container_client(container)
            blobs = list(container_client.list_blobs())
            print("Blobs:", blobs)
        except Exception as e:
            print("Error accessing Azure Blob Storage:", e) 