"""YouTube publishing client and AI metadata generator."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Any, Optional
from src.logging_config import get_logger
from src.exceptions import PublishingError

logger = get_logger(component="YouTubePublisher")


@dataclass
class VideoPublishMetadata:
    title: str
    description: str
    tags: List[str]
    category_id: str
    privacy_status: str


class BasePublisher(ABC):
    """Abstract interface for video publishing."""

    @abstractmethod
    def generate_metadata(
        self,
        video_title: str,
        events: List[Any],
        music_track: Optional[Dict[str, Any]] = None,
    ) -> VideoPublishMetadata:
        """Create optimized title, chapters, description, tags."""
        pass

    @abstractmethod
    def upload_video(self, video_path: Path, metadata: VideoPublishMetadata) -> str:
        """Upload video to YouTube and return the video URL."""
        pass


class YouTubeClient(BasePublisher):
    """Interacts with YouTube Data API v3 for upload and metadata application."""

    def __init__(
        self,
        client_secrets_file: str,
        token_file: str,
        privacy_status: str = "unlisted",
    ) -> None:
        self.client_secrets_file = client_secrets_file
        self.token_file = token_file
        self.privacy_status = privacy_status

    def generate_metadata(
        self,
        video_title: str,
        events: List[Any],
        music_track: Optional[Dict[str, Any]] = None,
    ) -> VideoPublishMetadata:
        clean_title = f"Last Day on Earth: Survival - {video_title.replace('_', ' ').title()}"

        description_lines = [
            f"Gameplay run of Last Day on Earth: Survival.",
            "",
            "🔔 Don't forget to like and subscribe for more survival gameplay!",
            "",
            "--- Chapters & Key Events ---",
        ]

        for ev in events:
            mins = int(getattr(ev, "start_time", 0) // 60)
            secs = int(getattr(ev, "start_time", 0) % 60)
            description_lines.append(f"{mins:02d}:{secs:02d} - {getattr(ev, 'description', '')}")

        if music_track and music_track.get("attribution_required") and music_track.get("attribution_text"):
            description_lines.extend([
                "",
                "--- Music Attribution ---",
                music_track["attribution_text"],
            ])

        description_lines.extend([
            "",
            "#LastDayOnEarth #LDOE #ZombieSurvival #Gaming #SurvivalGame",
        ])

        tags = [
            "Last Day on Earth",
            "Last Day on Earth Survival",
            "LDoE",
            "Mobile Gaming",
            "Zombie Survival",
            "LDoE Gameplay",
            "Survival Run",
        ]

        return VideoPublishMetadata(
            title=clean_title[:100],
            description="\n".join(description_lines),
            tags=tags,
            category_id="20",
            privacy_status=self.privacy_status,
        )

    def upload_video(self, video_path: Path, metadata: VideoPublishMetadata) -> str:
        logger.info("Uploading video to YouTube", extra_data={"title": metadata.title, "path": str(video_path)})
        if not video_path.exists():
            raise PublishingError(
                operation="upload_video",
                root_cause=f"File not found: {video_path}",
                recovery_action="Ensure the video processor rendered the video successfully.",
                file_path=str(video_path),
            )
        # Mock/template upload URL for testing until real token provided
        mock_id = "mock_yt_vid_id"
        return f"https://youtu.be/{mock_id}"
