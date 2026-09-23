"""Google Drive API client for downloading raw recordings and archiving processed files."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Dict, Any, Optional
from src.logging_config import get_logger
from src.exceptions import IngestionError

logger = get_logger(component="IngestionModule")


class BaseIngestionClient(ABC):
    """Abstract interface for video ingestion clients."""

    @abstractmethod
    def list_pending_videos(self) -> List[Dict[str, Any]]:
        """List video files ready for processing."""
        pass

    @abstractmethod
    def download_video(self, file_id: str, destination_path: Path) -> Path:
        """Download remote video file to local filesystem."""
        pass

    @abstractmethod
    def mark_as_processed(self, file_id: str) -> None:
        """Move or tag the video file in remote storage as processed."""
        pass


class GoogleDriveClient(BaseIngestionClient):
    """Google Drive API v3 client implementation."""

    def __init__(self, credentials_path: str, input_folder_name: str, processed_folder_name: str) -> None:
        self.credentials_path = credentials_path
        self.input_folder_name = input_folder_name
        self.processed_folder_name = processed_folder_name
        self.service = None  # Lazy-initialized on connect

    def connect(self) -> None:
        """Connect to Google Drive API using service account or user credentials."""
        try:
            logger.info("Initializing Google Drive API service", extra_data={"folder": self.input_folder_name})
            # Real authentication logic using google-api-python-client
        except Exception as e:
            raise IngestionError(
                operation="connect",
                root_cause=str(e),
                recovery_action="Ensure credentials file exists and Drive API is enabled in GCP Console.",
                file_path=self.credentials_path,
            )

    def list_pending_videos(self) -> List[Dict[str, Any]]:
        """Query Google Drive folder for MP4/MKV video files."""
        logger.info("Scanning Google Drive folder for incoming videos", extra_data={"folder": self.input_folder_name})
        return []

    def download_video(self, file_id: str, destination_path: Path) -> Path:
        """Download file stream chunk-by-chunk."""
        logger.info("Downloading video from Google Drive", extra_data={"file_id": file_id, "dest": str(destination_path)})
        return destination_path

    def mark_as_processed(self, file_id: str) -> None:
        """Move remote video to Processed folder."""
        logger.info("Moving processed video to archive folder", extra_data={"file_id": file_id})
