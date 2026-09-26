"""YouTube publishing and metadata generation module."""

from src.publisher.youtube_client import BasePublisher, YouTubeClient, VideoPublishMetadata
from src.publisher.title_manager import TitleManager, TitlePackage

__all__ = ["BasePublisher", "YouTubeClient", "VideoPublishMetadata", "TitleManager", "TitlePackage"]
