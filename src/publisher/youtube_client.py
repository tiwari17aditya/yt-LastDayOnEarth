"""YouTube publishing client and AI metadata generator."""

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import List, Dict, Any, Optional
from src.logging_config import get_logger
from src.exceptions import PublishingError

from src.publisher.title_manager import TitleManager, TitlePackage

logger = get_logger(component="YouTubePublisher")


@dataclass
class VideoPublishMetadata:
    title: str
    description: str
    tags: List[str]
    category_id: str
    privacy_status: str
    thumbnail_path: Optional[str] = None
    title_candidates: Optional[Dict[str, str]] = None
    episode_number: Optional[int] = None

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
        thumbnail_path: Optional[Path] = None,
        episode_number: Optional[int] = None,
    ) -> VideoPublishMetadata:
        """Create optimized title, chapters, description, tags."""
        pass

    @abstractmethod
    def upload_video(self, video_path: Path, metadata: VideoPublishMetadata) -> str:
        """Upload video to YouTube and return the video URL."""
        pass


class YouTubeClient(BasePublisher):
    """Interacts with YouTube Data API v3 for upload, metadata, and custom thumbnail application."""

    def __init__(
        self,
        client_secrets_file: str = "config/client_secrets.json",
        token_file: str = "config/token.json",
        privacy_status: str = "public",
        playlist_title: str = "Last Day on Earth: Survival — Official Gameplay Series",
        title_manager: Optional[TitleManager] = None,
    ) -> None:
        self.client_secrets_file = client_secrets_file
        self.token_file = token_file
        self.privacy_status = privacy_status
        self.playlist_title = playlist_title
        self.title_manager = title_manager or TitleManager()

    def generate_metadata(
        self,
        video_title: str,
        events: List[Any],
        music_track: Optional[Any] = None,
        thumbnail_path: Optional[Path] = None,
        episode_number: Optional[int] = None,
    ) -> VideoPublishMetadata:
        from datetime import datetime

        # Generate dynamic, high-CTR front-loaded title package
        title_pkg = self.title_manager.generate_titles(
            events=events,
            episode_number=episode_number,
        )
        selected_title = title_pkg.primary_title

        date_str = datetime.now().strftime("%d %b, %Y")

        # Top 2 lines: Front-loaded high-retention hook before YouTube's "...more" cutoff
        description_lines = [
            f"Surviving and building in Last Day on Earth: Survival! In Episode #{title_pkg.episode_number}, we focus on {title_pkg.summary}.",
            "Watch as we optimize our base layout, advance our workshop crafting, and prepare for the zombie wasteland.",
            "",
            "🔔 Subscribe for regular Last Day on Earth gameplay guides and survival runs!",
            "",
            "⏱️ TIMESTAMPS & CHAPTERS:",
        ]

        # Enforce YouTube 00:00 chapter requirement so video timeline scrubber splits into chapters
        formatted_chapters = []
        has_zero = False
        for ev in events:
            mins = int(getattr(ev, "start_time", 0) // 60)
            secs = int(getattr(ev, "start_time", 0) % 60)
            desc = getattr(ev, "description", "")
            if mins == 0 and secs == 0:
                has_zero = True
            formatted_chapters.append(f"{mins:02d}:{secs:02d} - {desc}")

        if not has_zero:
            first_event_desc = events[0].description if events else "Introduction"
            formatted_chapters.insert(0, f"00:00 - Intro & {first_event_desc}")

        description_lines.extend(formatted_chapters)

        # Curated high-engagement trending hashtags
        trending_hashtags = [
            "#LastDayOnEarth", "#LDoE", "#LastDayOnEarthSurvival", "#LDoEGameplay", "#LDoEGuide",
            "#LDoETips", "#LDoEBunker", "#LDoEBase", "#LDoERaid", "#LDoEUpdate",
            "#LDoESurvival", "#LDoESettlement", "#LDoECrafting", "#LDoEWorkshop",
            "#ZombieSurvival", "#SurvivalGame", "#ZombieApocalypse", "#SurvivalGaming",
            "#MobileGaming", "#Gaming", "#AndroidGaming", "#iOSGaming", "#LetsPlay"
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

        title_candidates = {
            "action_hook": title_pkg.action_hook,
            "curiosity": title_pkg.curiosity,
            "walkthrough": title_pkg.walkthrough,
        }

        return VideoPublishMetadata(
            title=selected_title[:100],
            description="\n".join(description_lines),
            tags=tags,
            category_id="20",
            privacy_status=self.privacy_status,
            thumbnail_path=str(thumbnail_path) if thumbnail_path else None,
            title_candidates=title_candidates,
            episode_number=title_pkg.episode_number,
        )

    def export_metadata_json(self, metadata: VideoPublishMetadata, output_json_path: Path) -> Path:
        """Saves generated metadata to JSON file alongside processed video."""
        output_json_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_json_path, "w", encoding="utf-8") as f:
            json.dump(metadata.to_dict(), f, indent=2)
        logger.info("Exported publishing metadata to JSON", extra_data={"path": str(output_json_path)})
        return output_json_path

    def get_or_create_playlist(
        self,
        youtube: Any,
        title: Optional[str] = None,
        description: Optional[str] = None,
        privacy_status: str = "public",
    ) -> Optional[str]:
        """Finds an existing playlist matching title or creates a new dedicated playlist."""
        title = title or self.playlist_title
        try:
            # Check existing playlists on the channel
            req = youtube.playlists().list(part="snippet,status", mine=True, maxResults=50)
            while req:
                res = req.execute()
                for item in res.get("items", []):
                    if item.get("snippet", {}).get("title") == title:
                        logger.info(f"Found existing YouTube playlist: '{title}' (ID: {item['id']})")
                        return item["id"]
                req = youtube.playlists().list_next(req, res)

            # Not found -> create dedicated playlist with comprehensive description
            if not description:
                description = (
                    "Welcome to the official Last Day on Earth: Survival gameplay series! 🧟‍♂️🔨\n\n"
                    "Follow our journey through the post-apocalyptic zombie wasteland as we optimize base layout, "
                    "craft advanced weapons and gear, gather survival resources, and defend against zombie hordes.\n\n"
                    "📌 In this playlist:\n"
                    "• Home base organization & woodworking workbench guides\n"
                    "• Pine & oak log processing, smelting furnaces, and resource hoarding\n"
                    "• Weapon workshop tasks, modifications, and gear optimization\n"
                    "• Base defense setup and zombie survival runs\n\n"
                    "🔔 Subscribe and check back regularly for new daily episodes!\n\n"
                    "#LastDayOnEarth #LDoE #ZombieSurvival #SurvivalGame #LDoEGameplay #SurvivalGaming"
                )

            logger.info(f"Creating new dedicated YouTube playlist: '{title}'")
            create_body = {
                "snippet": {
                    "title": title,
                    "description": description,
                    "defaultLanguage": "en",
                },
                "status": {
                    "privacyStatus": privacy_status,
                },
            }
            create_resp = youtube.playlists().insert(part="snippet,status", body=create_body).execute()
            playlist_id = create_resp.get("id")
            logger.info(f"Created dedicated YouTube playlist: '{title}' (ID: {playlist_id})")
            return playlist_id

        except Exception as e:
            logger.warning(
                f"Could not manage YouTube playlist (requires 'youtube.force-ssl' scope): {e}",
                extra_data={"playlist_title": title},
            )
            return None

    def add_video_to_playlist(
        self,
        youtube: Any,
        video_id: str,
        playlist_id: str,
    ) -> bool:
        """Adds a video to a YouTube playlist if not already present."""
        try:
            # Check items in playlist to avoid duplicates
            req = youtube.playlistItems().list(
                part="snippet",
                playlistId=playlist_id,
                maxResults=50,
            )
            while req:
                resp = req.execute()
                for item in resp.get("items", []):
                    if item.get("snippet", {}).get("resourceId", {}).get("videoId") == video_id:
                        logger.info(f"Video {video_id} is already in playlist {playlist_id}")
                        return True
                req = youtube.playlistItems().list_next(req, resp)

            body = {
                "snippet": {
                    "playlistId": playlist_id,
                    "resourceId": {
                        "kind": "youtube#video",
                        "videoId": video_id,
                    },
                }
            }
            youtube.playlistItems().insert(part="snippet", body=body).execute()
            logger.info(f"Video {video_id} added to YouTube playlist {playlist_id} successfully")
            return True

        except Exception as e:
            logger.warning(f"Could not add video {video_id} to playlist {playlist_id}: {e}")
            return False

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

            creds = get_google_credentials(
                scopes=[
                    "https://www.googleapis.com/auth/youtube.upload",
                    "https://www.googleapis.com/auth/youtube.force-ssl",
                ]
            )
            if not creds:
                logger.warning("No YouTube OAuth credentials configured; simulating upload (mock URL).")
                mock_id = "mock_ldoe_video"
                return f"https://youtu.be/{mock_id}"

            youtube = build("youtube", "v3", credentials=creds, cache_discovery=False)

            # Check if video with identical title was already uploaded recently (prevent duplicates)
            try:
                ch_resp = youtube.channels().list(mine=True, part="contentDetails").execute()
                if ch_resp.get("items"):
                    uploads_id = ch_resp["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]
                    recent_items = youtube.playlistItems().list(
                        playlistId=uploads_id,
                        part="snippet",
                        maxResults=25,
                    ).execute()
                    for item in recent_items.get("items", []):
                        snip = item.get("snippet", {})
                        if snip.get("title") == metadata.title:
                            existing_vid_id = snip.get("resourceId", {}).get("videoId")
                            logger.warning(
                                f"Video with title '{metadata.title}' already published on YouTube (ID: {existing_vid_id}). "
                                f"Skipping duplicate upload."
                            )
                            return f"https://youtu.be/{existing_vid_id}"
            except Exception as ce:
                logger.warning(f"Could not perform YouTube duplicate pre-check: {ce}")

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

            # Upload custom thumbnail if generated
            if metadata.thumbnail_path and Path(metadata.thumbnail_path).exists():
                try:
                    logger.info(f"Setting custom thumbnail for video {video_id}: {metadata.thumbnail_path}")
                    thumb_media = MediaFileUpload(
                        str(metadata.thumbnail_path),
                        mimetype="image/jpeg",
                        resumable=False,
                    )
                    youtube.thumbnails().set(
                        videoId=video_id,
                        media_body=thumb_media,
                    ).execute()
                    logger.info(f"Custom thumbnail uploaded successfully for video {video_id}")
                except Exception as te:
                    logger.warning(
                        f"Could not set custom thumbnail on YouTube (requires phone-verified channel or quota): {te}",
                        extra_data={"thumbnail_path": metadata.thumbnail_path},
                    )

            # Advance series episode tracker upon successful publish
            try:
                self.title_manager.advance_episode(title=metadata.title, job_id=video_id)
            except Exception as se:
                logger.warning(f"Could not advance episode counter in series tracker: {se}")

            # Automatically ensure dedicated playlist exists and add video to it
            try:
                playlist_id = self.get_or_create_playlist(
                    youtube=youtube,
                    privacy_status=metadata.privacy_status,
                )
                if playlist_id:
                    self.add_video_to_playlist(youtube, video_id=video_id, playlist_id=playlist_id)
            except Exception as pe:
                logger.warning(f"Playlist auto-assignment skipped: {pe}")

            return youtube_url

        except Exception as e:
            logger.error(f"Failed to upload video to YouTube: {e}")
            raise PublishingError(
                operation="youtube_upload",
                root_cause=str(e),
                recovery_action="Check YouTube API quota, channel status, or re-run scripts/setup_google_auth.py.",
                file_path=str(video_path),
            )
