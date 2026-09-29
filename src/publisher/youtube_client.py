"""YouTube publishing client and AI metadata generator."""

import json
import re
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


from src.publisher.metadata_generator import DynamicTagGenerator
from src.publisher.playlist_manager import PlaylistManager


class YouTubeClient(BasePublisher):
    """Interacts with YouTube Data API v3 for upload, metadata, and custom thumbnail application."""

    def __init__(
        self,
        client_secrets_file: str = "config/client_secrets.json",
        token_file: str = "config/token.json",
        privacy_status: str = "public",
        playlist_title: str = "Last Day on Earth: Survival — Official Gameplay Series",
        title_manager: Optional[TitleManager] = None,
        gemini_api_key: Optional[str] = None,
        gemini_model: str = "gemini-2.5-flash",
    ) -> None:
        self.client_secrets_file = client_secrets_file
        self.token_file = token_file
        self.privacy_status = privacy_status
        self.playlist_title = playlist_title
        self.title_manager = title_manager or TitleManager()
        self.playlist_manager = PlaylistManager(series_playlist_title=self.playlist_title)
        self.tag_generator = DynamicTagGenerator(
            gemini_api_key=gemini_api_key,
            gemini_model=gemini_model,
            target_hashtag_count=50,
        )

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

        # Natural, human-friendly presentation
        summary_clean = title_pkg.summary.strip()
        description_lines = [
            f"Welcome back to Last Day on Earth: Survival! In Episode #{title_pkg.episode_number}, we focus on {summary_clean}.",
            "Watch as we optimize our base layout, advance our workshop crafting, and prepare for the zombie wasteland.",
            "",
            "If you enjoyed the video, make sure to like and subscribe for more survival guides and wasteland runs! 🧟‍♂️🔨",
            "",
            "────────────────────────────────────────",
            "⏱️ TIMESTAMPS & CHAPTERS:",
        ]

        # Enforce YouTube 00:00 chapter requirement so video timeline scrubber splits into chapters
        formatted_chapters = []
        has_zero = False
        for ev in events:
            mins = int(getattr(ev, "start_time", 0) // 60)
            secs = int(getattr(ev, "start_time", 0) % 60)
            desc = getattr(ev, "description", "").strip()

            # Dynamic contextual badge based on gameplay event keywords
            desc_lower = desc.lower()
            badge = "📍"
            if any(k in desc_lower for k in ["craft", "build", "upgrade", "workbench", "smelter"]):
                badge = "🛠️"
            elif any(k in desc_lower for k in ["zombie", "attack", "defense", "horde", "fight", "kill"]):
                badge = "⚔️"
            elif any(k in desc_lower for k in ["loot", "chest", "crate", "resource", "wood", "stone", "forage"]):
                badge = "🎒"
            elif any(k in desc_lower for k in ["bunker", "raid", "alfa", "bravo", "red zone"]):
                badge = "☢️"
            elif any(k in desc_lower for k in ["intro", "start", "spawn", "beginning"]):
                badge = "🎬"
            elif any(k in desc_lower for k in ["base", "home", "perimeter", "wall"]):
                badge = "🏡"
            elif any(k in desc_lower for k in ["summary", "outro", "checkpoint", "recap"]):
                badge = "🏆"

            if mins == 0 and secs == 0:
                has_zero = True
            formatted_chapters.append(f"{mins:02d}:{secs:02d} - {badge} {desc}")

        if not has_zero:
            first_event_desc = events[0].description if events else "Wasteland Awakening"
            formatted_chapters.insert(0, f"00:00 - 🎬 Intro & {first_event_desc}")

        # Top ~50 dynamically generated trending hashtags for maximum algorithm reach
        trending_hashtags = self.tag_generator.generate_dynamic_hashtags(
            video_title=selected_title,
            events=events,
            date_str=date_str,
        )

        # Build Music Attribution & Copyright Fair Use Clearances block (100% CC0 / Content-ID Safe)
        licensing_lines = [
            "────────────────────────────────────────",
            "🎵 MUSIC & LICENSING ATTRIBUTION:",
            "Background music in this video is CC0 Public Domain / Royalty-Free and cleared for YouTube broadcast:",
        ]
        if music_track:
            tracks_list = music_track if isinstance(music_track, list) else [music_track]
            seen_attributions = set()
            for t in tracks_list:
                if isinstance(t, dict):
                    attr = t.get("attribution_text") or f"Music: '{t.get('title', 'Survival Ambient')}' (CC0 Public Domain - No Copyright)"
                    if attr not in seen_attributions:
                        seen_attributions.add(attr)
                        licensing_lines.append(f"• {attr}")
                elif isinstance(t, str):
                    licensing_lines.append(f"• Music: '{t}' (CC0 Public Domain - No Copyright)")
        else:
            licensing_lines.append("• Original Ambient Soundtrack (CC0 Public Domain - Content ID Immune)")

        licensing_lines.extend([
            "https://creativecommons.org/publicdomain/zero/1.0/",
            "",
            "⚖️ COPYRIGHT & FAIR USE DISCLAIMER:",
            "Last Day on Earth: Survival is developed and published by Kefir Games.",
            "All gameplay footage, graphics, and in-game audio belong to Kefir Games.",
            "This video is transformative gameplay walkthrough and commentary created for entertainment and guide purposes protected under Fair Use (Section 107 of the US Copyright Act 1976).",
        ])

        description_lines.extend(formatted_chapters)
        description_lines.extend(licensing_lines)
        description_lines.extend([
            "────────────────────────────────────────",
            "",
            " ".join(trending_hashtags),
        ])

        # Dynamic keyword tags for YouTube (under 500 characters)
        tags = self.tag_generator.generate_video_tags(
            video_title=selected_title,
            events=events,
            hashtags=trending_hashtags,
        )

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
        episode_number: Optional[int] = None,
    ) -> bool:
        """Adds a video to a YouTube playlist sequentially preserving chronological order."""
        return self.playlist_manager.add_video_sequentially(
            youtube=youtube,
            video_id=video_id,
            playlist_id=playlist_id,
            episode_number=episode_number,
        )

    def post_engagement_comment(
        self,
        youtube: Any,
        video_id: str,
        episode_number: Optional[int] = None,
        playlist_url: Optional[str] = None,
        custom_question: Optional[str] = None,
    ) -> Optional[str]:
        """Post a high-engagement creator comment immediately after publish to drive algorithmic engagement."""
        try:
            if not custom_question:
                next_ep_str = f"Episode #{episode_number + 1}" if episode_number else "the next episode"
                ep_prompts = [
                    f"Survivor checkpoint! 🧟‍♂️ What base upgrade or weapon craft should we tackle in {next_ep_str}?",
                    f"Drop your best survival strategies below! What zone should we raid next in {next_ep_str}?",
                    f"How would you rate our defense setup? What would you change before {next_ep_str}?",
                    f"Drop a comment: What's the rarest loot you've pulled from a red zone crate? 🎒📦",
                    f"Surviving the zombie wasteland day by day! What blueprint should we prioritize next? 🔨",
                ]
                idx = (episode_number or 1) % len(ep_prompts)
                custom_question = ep_prompts[idx]

            comment_lines = [
                f"🔥 {custom_question}",
                "",
                "Let me know in the comments below — reading and responding to all fellow survivors!",
            ]
            if playlist_url:
                comment_lines.append(f"📺 Watch the Full Series Playlist: {playlist_url}")
            comment_lines.append("🔔 Don't forget to Subscribe & turn on notifications for daily survival raids!")

            comment_text = "\n".join(comment_lines)

            body = {
                "snippet": {
                    "videoId": video_id,
                    "topLevelComment": {
                        "snippet": {
                            "textOriginal": comment_text
                        }
                    }
                }
            }
            resp = youtube.commentThreads().insert(part="snippet", body=body).execute()
            comment_id = resp.get("id")
            logger.info(f"Creator engagement comment posted successfully on video {video_id} (ID: {comment_id})")
            return comment_id
        except Exception as ce:
            logger.warning(f"Could not post engagement comment on video {video_id}: {ce}")
            return None

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
                raise PublishingError(
                    operation="upload_video",
                    root_cause="Missing YouTube OAuth credentials. Set GCP_CLIENT_ID, GCP_CLIENT_SECRET, and GCP_REFRESH_TOKEN (or GDRIVE_REFRESH_TOKEN).",
                    recovery_action="Configure YouTube OAuth credentials in .env before initiating YouTube upload.",
                    file_path=str(video_path),
                )

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

            # Sanitize and strictly enforce YouTube tag constraints (serialized length <= 400 chars)
            safe_tags: List[str] = []
            seen_tags = set()
            running_len = 0
            for tag in metadata.tags or []:
                clean_tag = re.sub(r'[<>,"]', "", str(tag)).strip()
                if not clean_tag or clean_tag.lower() in seen_tags or len(clean_tag) < 2 or len(clean_tag) > 60:
                    continue
                seen_tags.add(clean_tag.lower())
                cost = (len(clean_tag) + 2 if " " in clean_tag else len(clean_tag)) + (1 if safe_tags else 0)
                if running_len + cost > 400:
                    break
                safe_tags.append(clean_tag)
                running_len += cost

            body = {
                "snippet": {
                    "title": metadata.title,
                    "description": metadata.description,
                    "tags": safe_tags,
                    "categoryId": metadata.category_id,
                },
                "status": {
                    "privacyStatus": metadata.privacy_status,
                    "selfDeclaredMadeForKids": False,
                },
            }

            def _execute_upload(upload_body: dict):
                media = MediaFileUpload(
                    str(video_path),
                    chunksize=10 * 1024 * 1024,
                    resumable=True,
                    mimetype="video/mp4",
                )
                req = youtube.videos().insert(
                    part="snippet,status",
                    body=upload_body,
                    media_body=media,
                )
                resp = None
                while resp is None:
                    status, resp = req.next_chunk()
                    if status:
                        logger.info(f"YouTube upload progress: {int(status.progress() * 100)}%")
                return resp

            try:
                response = _execute_upload(body)
            except Exception as upload_err:
                err_str = str(upload_err)
                content_bytes = getattr(upload_err, "content", b"")
                content_str = content_bytes.decode("utf-8", errors="ignore") if isinstance(content_bytes, bytes) else str(content_bytes)
                details_str = str(getattr(upload_err, "error_details", ""))
                combined_err = f"{err_str} {content_str} {details_str}".lower()

                if "invalidtags" in combined_err or "invalid video keywords" in combined_err:
                    logger.warning(
                        "YouTube rejected tags with 'invalidTags' error. "
                        "Retrying upload with minimal safe core tags...",
                        extra_data={"original_tags": safe_tags, "error": err_str},
                    )
                    fallback_body = dict(body)
                    fallback_body["snippet"] = dict(body["snippet"])
                    fallback_body["snippet"]["tags"] = [
                        "Last Day on Earth",
                        "Last Day on Earth Survival",
                        "LDoE Gameplay",
                        "Zombie Survival",
                    ]
                    response = _execute_upload(fallback_body)
                else:
                    raise upload_err

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
                self.title_manager.advance_episode(
                    title=metadata.title,
                    video_id=video_id,
                    youtube_url=youtube_url,
                    job_id=video_id,
                )
            except Exception as se:
                logger.warning(f"Could not advance episode counter in series tracker: {se}")

            # Automatically ensure dedicated playlist exists and add video to it
            playlist_id = None
            try:
                playlist_id = self.get_or_create_playlist(
                    youtube=youtube,
                    privacy_status=metadata.privacy_status,
                )
                if playlist_id:
                    self.add_video_to_playlist(
                        youtube=youtube,
                        video_id=video_id,
                        playlist_id=playlist_id,
                        episode_number=metadata.episode_number,
                    )
            except Exception as pe:
                logger.warning(f"Playlist auto-assignment skipped: {pe}")

            # Post automated creator first comment with playlist link & discussion prompt
            try:
                playlist_url = f"https://www.youtube.com/playlist?list={playlist_id}" if playlist_id else None
                self.post_engagement_comment(
                    youtube=youtube,
                    video_id=video_id,
                    episode_number=metadata.episode_number,
                    playlist_url=playlist_url,
                )
            except Exception as ce:
                logger.warning(f"Creator engagement comment auto-posting skipped: {ce}")

            return youtube_url

        except Exception as e:
            logger.error(f"Failed to upload video to YouTube: {e}")
            raise PublishingError(
                operation="youtube_upload",
                root_cause=str(e),
                recovery_action="Check YouTube API quota, channel status, or re-run scripts/setup_google_auth.py.",
                file_path=str(video_path),
            )
