import os
from datetime import datetime, timezone
from azure.storage.blob import BlobServiceClient
from .config import settings
import logging

logger = logging.getLogger(__name__)

try:
    if not settings.AZURE_STORAGE_CONNECTION_STRING:
        logger.warning("AZURE_STORAGE_CONNECTION_STRING not found. Snapshot feature will be disabled.")
        blob_service_client = None
    else:
        blob_service_client = BlobServiceClient.from_connection_string(settings.AZURE_STORAGE_CONNECTION_STRING)
        container_name = "snapshots"
        
        container_client = blob_service_client.get_container_client(container_name)
        if not container_client.exists():
            blob_service_client.create_container(container_name)
            logger.info(f"Blob container '{container_name}' created.")

except Exception as e:
    logger.error(f"Failed to connect to Azure Blob Storage: {e}")
    blob_service_client = None


def upload_snapshot(image_bytes: bytes, user_id: int, incident_id: int) -> str:
    """
    Uploads an image to Azure Blob Storage and returns the public URL.
    """
    if not blob_service_client:
        logger.error("Cannot upload snapshot, Blob service client is not initialized.")
        return ""

    try:
        # Create a unique blob name to avoid collisions, using the recommended datetime method
        timestamp_str = str(datetime.now(timezone.utc).timestamp()).replace('.', '_')
        blob_name = f"user_{user_id}/incident_{incident_id}/{timestamp_str}.jpg"
        
        blob_client = blob_service_client.get_blob_client(container=container_name, blob=blob_name)

        blob_client.upload_blob(image_bytes, blob_type="BlockBlob", overwrite=True)
        
        logger.info(f"Successfully uploaded snapshot to {blob_client.url}")
        return blob_client.url
    except Exception as e:
        logger.error(f"Error uploading to blob storage: {e}")
        return ""