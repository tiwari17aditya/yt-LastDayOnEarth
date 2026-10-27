"""YouTube and open-source multi-platform publishing and metadata generation module."""

from src.publisher.youtube_client import BasePublisher, YouTubeClient, VideoPublishMetadata
from src.publisher.title_manager import TitleManager, TitlePackage
from src.publisher.metadata_generator import DynamicTagGenerator
from src.publisher.peertube_client import PeerTubeClient
from src.publisher.fediverse_broadcaster import FediverseBroadcaster
from src.publisher.multi_publisher import MultiPlatformPublisher, MultiPlatformPublishResult

from src.publisher.localization import MetadataLocalizer

__all__ = [
    "BasePublisher",
    "YouTubeClient",
    "VideoPublishMetadata",
    "TitleManager",
    "TitlePackage",
    "DynamicTagGenerator",
    "MetadataLocalizer",
    "PeerTubeClient",
    "FediverseBroadcaster",
    "MultiPlatformPublisher",
    "MultiPlatformPublishResult",
]
