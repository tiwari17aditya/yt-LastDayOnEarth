"""YouTube publishing client and AI metadata generator."""

import json
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import List, Dict, Any, Optional
from src.logging_config import get_logger
from src.exceptions import PublishingError, QuotaExceededError

from src.publisher.title_manager import TitleManager, TitlePackage

logger = get_logger(component="YouTubePublisher")


def is_quota_exceeded_error(e: Exception) -> bool:
    """Checks whether an exception indicates YouTube API daily quota exhaustion."""
    err_str = str(e).lower()
    quota_keywords = [
        "quotaexceeded",
        "dailylimitexceeded",
        "ratelimitexceeded",
        "userratelimitexceeded",
        "quota limit reached",
        "exceeded your quota",
        "quota exceeded",
    ]
    return any(k in err_str for k in quota_keywords)


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
    localizations: Optional[Dict[str, Dict[str, str]]] = None
    default_language: str = "en"
    events: Optional[List[Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        if self.events:
            d["events"] = [
                {
                    "description": getattr(e, "description", str(e)),
                    "start_time": getattr(e, "start_time", 0.0),
                    "end_time": getattr(e, "end_time", 0.0),
                }
                for e in self.events
            ]
        return d


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

    def export_metadata_json(self, metadata: VideoPublishMetadata, output_json_path: Path) -> Path:
        """Saves generated metadata to JSON file alongside processed video."""
        output_json_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_json_path, "w", encoding="utf-8") as f:
            json.dump(metadata.to_dict(), f, indent=2)
        logger.info("Exported publishing metadata to JSON", extra_data={"path": str(output_json_path)})
        return output_json_path


from src.publisher.metadata_generator import DynamicTagGenerator
from src.publisher.playlist_manager import PlaylistManager
from src.publisher.localization import MetadataLocalizer


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
        self.localizer = MetadataLocalizer(
            gemini_api_key=gemini_api_key,
            gemini_model=gemini_model,
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

        description_lines.extend(formatted_chapters)
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

        full_description = "\n".join(description_lines)

        # Generate multi-language localized titles and descriptions (RU, PT, ES)
        localizations = self.localizer.generate_localizations(
            primary_title=selected_title,
            primary_description=full_description,
            episode_number=title_pkg.episode_number,
            events=events,
        )

        title_candidates = {
            "action_hook": title_pkg.action_hook,
            "curiosity": title_pkg.curiosity,
            "walkthrough": title_pkg.walkthrough,
            "search_guide": title_pkg.search_guide,
        }

        return VideoPublishMetadata(
            title=selected_title[:100],
            description=full_description,
            tags=tags,
            category_id="20",
            privacy_status=self.privacy_status,
            thumbnail_path=str(thumbnail_path) if thumbnail_path else None,
            title_candidates=title_candidates,
            episode_number=title_pkg.episode_number,
            localizations=localizations,
            default_language="en",
            events=events,
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
        events: Optional[List[Any]] = None,
    ) -> Optional[str]:
        """Post a high-engagement creator comment immediately after publish to drive algorithmic engagement."""
        try:
            if not custom_question:
                next_ep_str = f"Episode #{episode_number + 1}" if episode_number else "the next episode"
                event_text = " ".join([getattr(ev, "description", "") for ev in (events or [])]).lower()

                # Context-aware high-converting prompt selection
                if any(k in event_text for k in ["chopper", "bike", "motorcycle"]):
                    custom_question = "Survivor progress check! 🏍️ What level is your Chopper right now, and what parts are you still hunting for?"
                elif any(k in event_text for k in ["bunker", "alfa", "bravo", "farm", "crooked"]):
                    custom_question = "Combat survey! ⚔️ What's your go-to budget weapon for clearing Bunker Alfa and the Farm? Melee or guns?"
                elif any(k in event_text for k in ["smelt", "furnace", "titanium", "steel", "iron"]):
                    custom_question = "The resource grind is real! ⛏️ How long did it take you guys to farm your first stack of steel/titanium? Drop your stats below!"
                else:
                    # Rotational high-engagement prompts targeting community discussion & grind empathy
                    ep_prompts = [
                        "Survivor survey! 🏍️ What level is your Chopper right now, and what engine parts are you still hunting for?",
                        "Combat question! ⚔️ What's your absolute favorite budget weapon for clearing the Spooky Farm and Bunker Alfa?",
                        "The grind is real! 🎒📦 How many red crates or bunker runs did it take you to find your first ATV transmission or engine part?",
                        f"Survivor checkpoint! 🧟‍♂️ What base upgrade or weapon craft should we tackle in {next_ep_str}?",
                        "Loot flex check! 🏆 What is the rarest single item you've pulled from a red zone run so far? Drop your stories below!",
                        "Defense audit! 🔨 How would you rate our base layout? What would you change before the zombie horde arrives?",
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

    def upload_captions(
        self,
        youtube: Any,
        video_id: str,
        events: List[Any],
        languages: Optional[List[str]] = None,
    ) -> Dict[str, str]:
        """Uploads multi-language Closed Caption tracks (.srt) to YouTube via Data API v3."""
        if not events:
            return {}

        from googleapiclient.http import MediaFileUpload

        langs = languages or ["en", "ru", "pt", "es"]
        track_names = {
            "en": "English (Gameplay Cues)",
            "ru": "Русский (Игровые подсказки)",
            "pt": "Português (Dicas de Sobrevivência)",
            "es": "Español (Guía de Supervivencia)",
        }

        uploaded: Dict[str, str] = {}
        captions_temp_dir = Path("temp/captions")
        captions_temp_dir.mkdir(parents=True, exist_ok=True)

        for lang in langs:
            try:
                srt_path = captions_temp_dir / f"{video_id}_{lang}.srt"
                self.localizer.generate_srt_captions(
                    events=events,
                    lang=lang,
                    output_path=srt_path,
                )

                media = MediaFileUpload(
                    str(srt_path),
                    mimetype="application/x-subrip",
                    resumable=True,
                )
                body = {
                    "snippet": {
                        "videoId": video_id,
                        "language": lang,
                        "name": track_names.get(lang, lang.upper()),
                        "isDraft": False,
                    }
                }
                logger.info(f"Uploading {lang.upper()} Closed Caption track to video {video_id}...")
                resp = youtube.captions().insert(
                    part="snippet",
                    body=body,
                    media_body=media,
                ).execute()

                caption_id = resp.get("id")
                uploaded[lang] = caption_id
                logger.info(f"Closed Caption track ({lang}) uploaded successfully (ID: {caption_id})")

            except Exception as e:
                logger.warning(f"Could not upload {lang} caption track to video {video_id}: {e}")

        return uploaded

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

            insert_parts = ["snippet", "status"]
            body = {
                "snippet": {
                    "title": metadata.title,
                    "description": metadata.description,
                    "tags": safe_tags,
                    "categoryId": metadata.category_id,
                    "defaultLanguage": getattr(metadata, "default_language", "en") or "en",
                },
                "status": {
                    "privacyStatus": metadata.privacy_status,
                    "selfDeclaredMadeForKids": False,
                },
            }

            if getattr(metadata, "localizations", None):
                body["localizations"] = metadata.localizations
                insert_parts.append("localizations")

            def _execute_upload(upload_body: dict, parts: List[str]):
                media = MediaFileUpload(
                    str(video_path),
                    chunksize=10 * 1024 * 1024,
                    resumable=True,
                    mimetype="video/mp4",
                )
                req = youtube.videos().insert(
                    part=",".join(parts),
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
                response = _execute_upload(body, insert_parts)
            except Exception as upload_err:
                err_str = str(upload_err)
                content_bytes = getattr(upload_err, "content", b"")
                content_str = content_bytes.decode("utf-8", errors="ignore") if isinstance(content_bytes, bytes) else str(content_bytes)
                details_str = str(getattr(upload_err, "error_details", ""))
                combined_err = f"{err_str} {content_str} {details_str}".lower()

                if "localizations" in insert_parts and any(k in combined_err for k in ["localization", "language", "invalidvalue"]):
                    logger.warning(
                        "YouTube rejected localization metadata. Retrying upload without localizations...",
                        extra_data={"error": err_str},
                    )
                    clean_body = dict(body)
                    clean_body.pop("localizations", None)
                    response = _execute_upload(clean_body, ["snippet", "status"])
                elif "invalidtags" in combined_err or "invalid video keywords" in combined_err:
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
                    response = _execute_upload(fallback_body, insert_parts)
                else:
                    raise upload_err

            video_id = response.get("id")
            youtube_url = f"https://youtu.be/{video_id}"
            logger.info(f"Video uploaded successfully to YouTube: {youtube_url}")

            # Upload custom thumbnail if generated (Strict Compliance)
            if metadata.thumbnail_path and Path(metadata.thumbnail_path).exists():
                thumb_uploaded = False
                for attempt in range(1, 3):
                    try:
                        logger.info(f"Setting custom thumbnail for video {video_id} (Attempt {attempt}): {metadata.thumbnail_path}")
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
                        thumb_uploaded = True
                        break
                    except Exception as te:
                        logger.warning(
                            f"Thumbnail upload attempt {attempt} failed for video {video_id}: {te}",
                            extra_data={"thumbnail_path": metadata.thumbnail_path, "attempt": attempt},
                        )
                if not thumb_uploaded:
                    logger.error(f"STRICT COMPLIANCE WARNING: Could not set custom thumbnail for video {video_id}")

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

            # Automatically ensure dedicated playlist exists and strictly add video to it
            playlist_id = None
            try:
                playlist_id = self.get_or_create_playlist(
                    youtube=youtube,
                    privacy_status=metadata.privacy_status,
                )
                if playlist_id:
                    added_to_pl = self.add_video_to_playlist(
                        youtube=youtube,
                        video_id=video_id,
                        playlist_id=playlist_id,
                        episode_number=metadata.episode_number,
                    )
                    if not added_to_pl:
                        logger.warning(f"Initial playlist addition returned False. Retrying for video {video_id}...")
                        added_to_pl = self.add_video_to_playlist(
                            youtube=youtube,
                            video_id=video_id,
                            playlist_id=playlist_id,
                            episode_number=metadata.episode_number,
                        )
                    if added_to_pl:
                        logger.info(f"Confirmed: Video {video_id} is included in playlist {playlist_id}")
                    else:
                        logger.error(f"STRICT COMPLIANCE ALERT: Video {video_id} could not be confirmed in playlist {playlist_id}")
            except Exception as pe:
                logger.error(f"STRICT COMPLIANCE ALERT: Playlist auto-assignment encountered error: {pe}")

            # Upload multi-language Closed Caption tracks (.srt) to YouTube player
            if getattr(metadata, "events", None):
                try:
                    self.upload_captions(
                        youtube=youtube,
                        video_id=video_id,
                        events=metadata.events,
                    )
                except Exception as cap_err:
                    logger.warning(f"Closed Captions upload skipped: {cap_err}")

            # Post automated creator first comment with playlist link & discussion prompt
            try:
                playlist_url = f"https://www.youtube.com/playlist?list={playlist_id}" if playlist_id else None
                self.post_engagement_comment(
                    youtube=youtube,
                    video_id=video_id,
                    episode_number=metadata.episode_number,
                    playlist_url=playlist_url,
                    events=getattr(metadata, "events", None),
                )
            except Exception as ce:
                logger.warning(f"Creator engagement comment auto-posting skipped: {ce}")

            return youtube_url

        except Exception as e:
            logger.error(f"Failed to upload video to YouTube: {e}")
            if is_quota_exceeded_error(e):
                raise QuotaExceededError(
                    operation="youtube_upload",
                    root_cause=str(e),
                    recovery_action="Wait for daily YouTube Data API quota to reset at midnight PST (07:00 UTC).",
                    file_path=str(video_path),
                )
            raise PublishingError(
                operation="youtube_upload",
                root_cause=str(e),
                recovery_action="Check YouTube API quota, channel status, or re-run scripts/setup_google_auth.py.",
                file_path=str(video_path),
            )

    def check_quota_available(self) -> bool:
        """Pre-flight check: calls lightweight channels.list (costs only 1 quota unit).

        Returns True if quota is available, False if quota is exceeded.
        """
        try:
            youtube = self.get_service()
            if not youtube:
                return True
            youtube.channels().list(mine=True, part="id").execute()
            return True
        except Exception as e:
            if is_quota_exceeded_error(e):
                logger.warning(
                    "YouTube API daily quota is currently exhausted (pre-flight check). "
                    "Skipping video processing until quota resets."
                )
                return False
            # For non-quota errors (e.g. mock or transient network), don't block
            return True

