"""YouTube publishing and metadata generation module."""

from src.publisher.youtube_client import BasePublisher, YouTubeClient, VideoPublishMetadata
from src.publisher.title_manager import TitleManager, TitlePackage
from src.publisher.metadata_generator import DynamicTagGenerator

__all__ = [
    "BasePublisher",
    "YouTubeClient",
    "VideoPublishMetadata",
    "TitleManager",
    "TitlePackage",
    "DynamicTagGenerator",
]
