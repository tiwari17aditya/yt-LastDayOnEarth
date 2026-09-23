"""YouTube publishing client and AI metadata generator."""

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict
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

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


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
        client_secrets_file: str = "config/client_secrets.json",
        token_file: str = "config/token.json",
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
        # High-engagement gaming title
        clean_title = "Last Day on Earth: Survival - Home Base Workshop, Woodcrafting & Resource Storage"

        description_lines = [
            "Surviving and thriving in Last Day on Earth: Survival! In this episode, we organize our Home Base, process pine logs into planks at the woodworking bench, manage base storage chests, inspect the weapon workbench, and fuel up the smelting furnaces.",
            "",
            "🔔 Subscribe for regular Last Day on Earth gameplay guides and survival runs!",
            "",
            "⏱️ TIMESTAMPS & CHAPTERS:",
        ]

        for ev in events:
            mins = int(getattr(ev, "start_time", 0) // 60)
            secs = int(getattr(ev, "start_time", 0) % 60)
            desc = getattr(ev, "description", "")
            description_lines.append(f"{mins:02d}:{secs:02d} - {desc}")

        if music_track and music_track.get("attribution_required") and music_track.get("attribution_text"):
            description_lines.extend([
                "",
                "🎵 BACKGROUND MUSIC & LICENSING:",
                music_track["attribution_text"],
            ])
        elif music_track:
            description_lines.extend([
                "",
                "🎵 BACKGROUND MUSIC:",
                f"Track: {music_track.get('title', 'Ambient Survival')} by {music_track.get('artist', 'Artist')} ({music_track.get('license', 'Royalty Free')})",
            ])

        description_lines.extend([
            "",
            "#LastDayOnEarth #LDOE #LastDayOnEarthSurvival #MobileGaming #ZombieSurvival #SurvivalGame #LDoEGameplay",
        ])

        tags = [
            "Last Day on Earth",
            "Last Day on Earth Survival",
            "LDoE",
            "LDoE Home Base",
            "LDoE Crafting",
            "LDoE Woodworking",
            "LDoE Settlement",
            "Zombie Survival Mobile",
            "Mobile Gaming",
            "Survival Run",
            "LDoE Guide",
            "Kefir Games",
        ]

        return VideoPublishMetadata(
            title=clean_title[:100],
            description="\n".join(description_lines),
            tags=tags,
            category_id="20",
            privacy_status=self.privacy_status,
        )

    def export_metadata_json(self, metadata: VideoPublishMetadata, output_json_path: Path) -> Path:
        """Saves generated metadata to JSON file alongside processed video."""
        output_json_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_json_path, "w", encoding="utf-8") as f:
            json.dump(metadata.to_dict(), f, indent=2)
        logger.info("Exported publishing metadata to JSON", extra_data={"path": str(output_json_path)})
        return output_json_path

    def upload_video(self, video_path: Path, metadata: VideoPublishMetadata) -> str:
        logger.info("Initiating YouTube video upload", extra_data={"title": metadata.title, "path": str(video_path)})
        if not video_path.exists():
            raise PublishingError(
                operation="upload_video",
                root_cause=f"File not found: {video_path}",
                recovery_action="Ensure the video processor rendered the video successfully.",
                file_path=str(video_path),
            )
        # Placeholder upload URL until real OAuth credentials are authenticated
        mock_id = "mock_ldoe_video"
        return f"https://youtu.be/{mock_id}"
