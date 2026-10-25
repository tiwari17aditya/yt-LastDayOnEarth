"""Unified multi-platform publisher coordinating YouTube, PeerTube, and Fediverse broadcast.

Provides a single extensible orchestration entry point to publish gaming videos
to primary platforms and cross-post to open-source decentralized networks for maximized reach.
"""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Any, List, Optional

from src.logging_config import get_logger
from src.exceptions import PublishingError
from src.publisher.youtube_client import YouTubeClient, VideoPublishMetadata, BasePublisher
from src.publisher.peertube_client import PeerTubeClient
from src.publisher.fediverse_broadcaster import FediverseBroadcaster

logger = get_logger(component="MultiPlatformPublisher")


@dataclass
class MultiPlatformPublishResult:
    """Contains results and links from multi-platform publishing and promotion."""
    youtube_url: str = ""
    peertube_url: Optional[str] = None
    social_broadcasts: Dict[str, Optional[str]] = field(default_factory=dict)
    published_platforms: List[str] = field(default_factory=list)
    errors: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "youtube_url": self.youtube_url,
            "peertube_url": self.peertube_url,
            "social_broadcasts": self.social_broadcasts,
            "published_platforms": self.published_platforms,
            "errors": self.errors,
        }


class MultiPlatformPublisher(BasePublisher):
    """Orchestrates publishing across YouTube, PeerTube, and decentralized social networks."""

    def __init__(
        self,
        youtube_client: YouTubeClient,
        peertube_client: Optional[PeerTubeClient] = None,
        fediverse_broadcaster: Optional[FediverseBroadcaster] = None,
        enable_peertube: bool = False,
        enable_fediverse_broadcast: bool = False,
    ) -> None:
        self.youtube = youtube_client
        self.peertube = peertube_client
        self.broadcaster = fediverse_broadcaster
        self.enable_peertube = enable_peertube
        self.enable_fediverse = enable_fediverse_broadcast

    def check_quota_available(self) -> bool:
        """Checks YouTube API daily quota availability."""
        if hasattr(self.youtube, "check_quota_available"):
            return self.youtube.check_quota_available()
        return True

    def generate_metadata(
        self,
        video_title: str,
        events: List[Any],
        music_track: Optional[Dict[str, Any]] = None,
        thumbnail_path: Optional[Path] = None,
        episode_number: Optional[int] = None,
    ) -> VideoPublishMetadata:
        """Delegates metadata formulation to the primary YouTube metadata generator."""
        return self.youtube.generate_metadata(
            video_title=video_title,
            events=events,
            music_track=music_track,
            thumbnail_path=thumbnail_path,
            episode_number=episode_number,
        )

    def export_metadata_json(self, metadata: VideoPublishMetadata, output_json_path: Path) -> Path:
        """Exports publishing metadata to a JSON file, delegating to the primary YouTube client."""
        if hasattr(self.youtube, "export_metadata_json"):
            return self.youtube.export_metadata_json(metadata, output_json_path)
        output_json_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_json_path, "w", encoding="utf-8") as f:
            json.dump(metadata.to_dict(), f, indent=2)
        logger.info("Exported publishing metadata to JSON", extra_data={"path": str(output_json_path)})
        return output_json_path

    def __getattr__(self, name: str) -> Any:
        """Transparently delegates any unhandled publisher attribute or method to the underlying YouTube client."""
        if hasattr(self, "youtube") and hasattr(self.youtube, name):
            return getattr(self.youtube, name)
        raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")

    def upload_video(self, video_path: Path, metadata: VideoPublishMetadata) -> str:
        """Standard BasePublisher interface: publishes to YouTube as primary and returns YouTube URL."""
        res = self.publish_all(video_path, metadata)
        return res.youtube_url

    def publish_all(
        self,
        video_path: Path,
        metadata: VideoPublishMetadata,
        skip_youtube: bool = False,
    ) -> MultiPlatformPublishResult:
        """Publishes video to YouTube and enabled open-source platforms, then triggers social broadcast."""
        result = MultiPlatformPublishResult()

        # 1. Primary Publish: YouTube
        if not skip_youtube:
            try:
                logger.info(f"Uploading to YouTube: {metadata.title}")
                yt_url = self.youtube.upload_video(video_path, metadata)
                result.youtube_url = yt_url
                result.published_platforms.append("YouTube")
            except Exception as ye:
                result.errors["YouTube"] = str(ye)
                logger.error(f"YouTube publishing failed: {ye}")
                raise ye  # Re-raise to preserve primary pipeline failure semantics

        # 2. Open-Source Federated Publish: PeerTube
        if self.enable_peertube and self.peertube and self.peertube.is_configured():
            try:
                logger.info(f"Mirroring to PeerTube: {metadata.title}")
                pt_url = self.peertube.upload_video(video_path, metadata)
                if pt_url and "http" in pt_url:
                    result.peertube_url = pt_url
                    result.published_platforms.append("PeerTube")
            except Exception as pe:
                result.errors["PeerTube"] = str(pe)
                logger.warning(
                    f"PeerTube publishing degraded: {pe}. YouTube release remains intact.",
                    extra_data={
                        "operation": "peertube_publish",
                        "component": "MultiPlatformPublisher",
                        "root_cause": str(pe),
                    },
                )
        elif self.enable_peertube:
            logger.debug("PeerTube mirror enabled but instance credentials not configured.")

        # 3. Decentralized Social Promotion: Mastodon & Lemmy
        if self.enable_fediverse and self.broadcaster:
            thumb_path = Path(metadata.thumbnail_path) if metadata.thumbnail_path else None
            try:
                logger.info("Broadcasting release to open-source social networks (Fediverse)...")
                broadcast_results = self.broadcaster.broadcast_release(
                    title=metadata.title,
                    youtube_url=result.youtube_url,
                    episode_number=metadata.episode_number,
                    peertube_url=result.peertube_url,
                    thumbnail_path=thumb_path,
                )
                result.social_broadcasts = broadcast_results
                for platform, url in broadcast_results.items():
                    if url:
                        result.published_platforms.append(f"Social:{platform}")
            except Exception as be:
                result.errors["SocialBroadcast"] = str(be)
                logger.warning(f"Social broadcast non-critical degradation: {be}")

        logger.info(
            f"Multi-platform publish complete: {result.published_platforms}",
            extra_data=result.to_dict(),
        )
        return result
