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
        from datetime import datetime
        import hashlib

        # Dynamic date format: ( 23 Sep, 2026 )
        date_str = datetime.now().strftime("%d %b, %Y")

        # Varied engaging titles to ensure every video is distinct and fresh
        title_themes = [
            "Home Base Workshop, Woodcrafting & Storage",
            "Survival Preparation, Base Upgrades & Smelting",
            "Optimizing Base Storage, Workbench & Planks",
            "Resource Gathering, Woodworking & Gear Management",
            "Base Defense Setup, Workshop Tasks & Smelting",
            "Survival Routine: Workshop Operations & Storage",
            "Crafting Essentials: Planks, Weapon Bench & Furnaces",
            "Home Base Expansion & Resource Organization",
            "Workshop Productivity: Woodcraft & Weapon Setup",
            "Zombie Defense Prep: Workshop & Resource Hoarding",
        ]
        theme_index = int(hashlib.md5(f"{video_title}_{date_str}".encode()).hexdigest(), 16) % len(title_themes)
        selected_theme = title_themes[theme_index]
        clean_title = f"Last Day on Earth: Survival — {selected_theme} ({date_str})"

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

        # Top 50 curated high-engagement trending hashtags for maximum algorithm reach
        trending_hashtags = [
            "#LastDayOnEarth", "#LDoE", "#LastDayOnEarthSurvival", "#LDoEGameplay", "#LDoEGuide",
            "#LDoETips", "#LDoEBunker", "#LDoEBase", "#LDoERaid", "#LDoEUpdate",
            "#LDoESurvival", "#LDoESettlement", "#LDoECrafting", "#LDoEWorkshop", "#LDoEAlfa",
            "#ZombieSurvival", "#SurvivalGame", "#ZombieApocalypse", "#SurvivalGaming", "#ZombieHunter",
            "#PostApocalyptic", "#SurvivalCraft", "#ZombieGame", "#SurviveTheApocalypse", "#ZombieHorde",
            "#MobileGaming", "#Gaming", "#Gamer", "#GamingCommunity", "#GameWalkthrough",
            "#AndroidGaming", "#iOSGaming", "#GamingClips", "#Gameplay", "#LetsPlay",
            "#YouTubeGaming", "#GamingVideos", "#Trending", "#ViralGaming", "#ExplorePage",
            "#GamingLife", "#ProGamer", "#SurvivalCrafting", "#MobileGames", "#ZombieSurvivalGame",
            "#ApocalypseSurvival", "#ZombieAttack", "#BaseBuilding", "#SurvivalRun", "#ZombieSurvivalRun"
        ]

        description_lines.extend([
            "",
            " ".join(trending_hashtags),
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

        try:
            from googleapiclient.discovery import build
            from googleapiclient.http import MediaFileUpload
            from src.google_auth import get_google_credentials

            creds = get_google_credentials(scopes=["https://www.googleapis.com/auth/youtube.upload"])
            if not creds:
                logger.warning("No YouTube OAuth credentials configured; simulating upload (mock URL).")
                mock_id = "mock_ldoe_video"
                return f"https://youtu.be/{mock_id}"

            youtube = build("youtube", "v3", credentials=creds, cache_discovery=False)

            body = {
                "snippet": {
                    "title": metadata.title,
                    "description": metadata.description,
                    "tags": metadata.tags,
                    "categoryId": metadata.category_id,
                },
                "status": {
                    "privacyStatus": metadata.privacy_status,
                    "selfDeclaredMadeForKids": False,
                },
            }

            media = MediaFileUpload(
                str(video_path),
                chunksize=10 * 1024 * 1024,
                resumable=True,
                mimetype="video/mp4",
            )

            request = youtube.videos().insert(
                part="snippet,status",
                body=body,
                media_body=media,
            )

            response = None
            while response is None:
                status, response = request.next_chunk()
                if status:
                    logger.info(f"YouTube upload progress: {int(status.progress() * 100)}%")

            video_id = response.get("id")
            youtube_url = f"https://youtu.be/{video_id}"
            logger.info(f"Video uploaded successfully to YouTube: {youtube_url}")
            return youtube_url

        except Exception as e:
            logger.error(f"Failed to upload video to YouTube: {e}")
            raise PublishingError(
                operation="youtube_upload",
                root_cause=str(e),
                recovery_action="Check YouTube API quota, channel status, or re-run scripts/setup_google_auth.py.",
                file_path=str(video_path),
            )
