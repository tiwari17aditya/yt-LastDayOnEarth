"""Configuration settings loader for the Last Day on Earth pipeline."""

import os
from pathlib import Path
from typing import Optional, List
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# Load .env file from project root if present
load_dotenv()


class GoogleDriveSettings(BaseModel):
    parent_folder_name: str = Field(default_factory=lambda: os.getenv("GDRIVE_PARENT_FOLDER_NAME", "youtube-projects"))
    project_folder_name: str = Field(default_factory=lambda: os.getenv("GDRIVE_PROJECT_FOLDER_NAME", "LastDayOnEarth"))
    input_folder_name: str = Field(default_factory=lambda: os.getenv("GDRIVE_INPUT_FOLDER_NAME", "Input"))
    processed_folder_name: str = Field(default_factory=lambda: os.getenv("GDRIVE_PROCESSED_FOLDER_NAME", "Processed"))
    output_folder_name: str = Field(default_factory=lambda: os.getenv("GDRIVE_OUTPUT_FOLDER_NAME", "Output"))
    output_retention_days: int = Field(default_factory=lambda: int(os.getenv("GDRIVE_OUTPUT_RETENTION_DAYS", "7")))
    client_id: Optional[str] = Field(default_factory=lambda: os.getenv("GCP_CLIENT_ID"))
    client_secret: Optional[str] = Field(default_factory=lambda: os.getenv("GCP_CLIENT_SECRET"))
    refresh_token: Optional[str] = Field(default_factory=lambda: os.getenv("GCP_REFRESH_TOKEN"))
    assets_folder_name: str = Field(default_factory=lambda: os.getenv("GDRIVE_ASSETS_FOLDER_NAME", "Assets"))
    credentials_file: str = Field(
        default_factory=lambda: os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "config/credentials.json")
    )


class GmailSettings(BaseModel):
    sender: str = Field(default_factory=lambda: os.getenv("GMAIL_SENDER", "me"))
    recipients: List[str] = Field(
        default_factory=lambda: [
            r.strip()
            for r in os.getenv("NOTIFICATION_RECIPIENTS", "").split(",")
            if r.strip()
        ]
    )


class GeminiSettings(BaseModel):
    api_key: Optional[str] = Field(default_factory=lambda: os.getenv("GEMINI_API_KEY"))
    model: str = Field(default_factory=lambda: os.getenv("GEMINI_MODEL", "gemini-2.5-flash"))


class YouTubeSettings(BaseModel):
    client_id: Optional[str] = Field(default_factory=lambda: os.getenv("GCP_CLIENT_ID"))
    client_secret: Optional[str] = Field(default_factory=lambda: os.getenv("GCP_CLIENT_SECRET"))
    refresh_token: Optional[str] = Field(default_factory=lambda: os.getenv("GCP_REFRESH_TOKEN"))
    client_secrets_file: str = Field(
        default_factory=lambda: os.getenv("YOUTUBE_CLIENT_SECRETS_FILE", "config/client_secrets.json")
    )
    token_file: str = Field(default_factory=lambda: os.getenv("YOUTUBE_TOKEN_FILE", "config/token.json"))
    privacy_status: str = Field(default_factory=lambda: os.getenv("YOUTUBE_PRIVACY_STATUS", "public"))
    playlist_title: str = Field(
        default_factory=lambda: os.getenv("YOUTUBE_PLAYLIST_TITLE", "Last Day on Earth: Survival — Official Gameplay Series")
    )
    category_id: str = "20"  # Gaming category
    series_title: str = Field(
        default_factory=lambda: os.getenv("SERIES_TITLE", "Last Day on Earth: Survival")
    )
    series_prefix: str = Field(
        default_factory=lambda: os.getenv("SERIES_PREFIX", "LDoE")
    )
    title_style: str = Field(
        default_factory=lambda: os.getenv("TITLE_STYLE", "action_hook")
    )
    episode_numbering: bool = Field(
        default_factory=lambda: os.getenv("EPISODE_NUMBERING_ENABLED", "true").lower() == "true"
    )
    series_tracker_file: Path = Field(
        default_factory=lambda: Path(os.getenv("SERIES_TRACKER_FILE", "data/series_tracker.json"))
    )
    sync_episode_with_youtube: bool = Field(
        default_factory=lambda: os.getenv("SYNC_EPISODE_WITH_YOUTUBE", "true").lower() == "true"
    )
    upload_thumbnail: bool = Field(
        default_factory=lambda: os.getenv("UPLOAD_CUSTOM_THUMBNAIL", "true").lower() == "true"
    )


class SMTPSettings(BaseModel):
    host: str = Field(default_factory=lambda: os.getenv("SMTP_HOST", "smtp.gmail.com"))
    port: int = Field(default_factory=lambda: int(os.getenv("SMTP_PORT", "587")))
    user: Optional[str] = Field(default_factory=lambda: os.getenv("SMTP_USER"))
    password: Optional[str] = Field(default_factory=lambda: os.getenv("SMTP_PASSWORD"))
    recipients: List[str] = Field(
        default_factory=lambda: [
            r.strip()
            for r in os.getenv("NOTIFICATION_RECIPIENTS", "").split(",")
            if r.strip()
        ]
    )


class PeerTubeSettings(BaseModel):
    enabled: bool = Field(default_factory=lambda: os.getenv("PEERTUBE_ENABLED", "false").lower() == "true")
    instance_url: Optional[str] = Field(default_factory=lambda: os.getenv("PEERTUBE_INSTANCE_URL"))
    username: Optional[str] = Field(default_factory=lambda: os.getenv("PEERTUBE_USERNAME"))
    password: Optional[str] = Field(default_factory=lambda: os.getenv("PEERTUBE_PASSWORD"))
    client_id: Optional[str] = Field(default_factory=lambda: os.getenv("PEERTUBE_CLIENT_ID"))
    client_secret: Optional[str] = Field(default_factory=lambda: os.getenv("PEERTUBE_CLIENT_SECRET"))
    access_token: Optional[str] = Field(default_factory=lambda: os.getenv("PEERTUBE_ACCESS_TOKEN"))
    channel_name: Optional[str] = Field(default_factory=lambda: os.getenv("PEERTUBE_CHANNEL_NAME"))
    privacy_status: int = Field(default_factory=lambda: int(os.getenv("PEERTUBE_PRIVACY_STATUS", "1")))


class FediverseSettings(BaseModel):
    enabled: bool = Field(default_factory=lambda: os.getenv("FEDIVERSE_ENABLED", "false").lower() == "true")
    mastodon_instance: Optional[str] = Field(default_factory=lambda: os.getenv("MASTODON_INSTANCE_URL"))
    mastodon_access_token: Optional[str] = Field(default_factory=lambda: os.getenv("MASTODON_ACCESS_TOKEN"))
    lemmy_instance: Optional[str] = Field(default_factory=lambda: os.getenv("LEMMY_INSTANCE_URL"))
    lemmy_auth_token: Optional[str] = Field(default_factory=lambda: os.getenv("LEMMY_AUTH_TOKEN"))
    lemmy_community_id: Optional[int] = Field(
        default_factory=lambda: int(os.getenv("LEMMY_COMMUNITY_ID")) if os.getenv("LEMMY_COMMUNITY_ID") else None
    )


class ProcessingSettings(BaseModel):
    resolution: str = Field(default_factory=lambda: os.getenv("VIDEO_RESOLUTION", "1920x1080"))
    target_fps: int = Field(default_factory=lambda: int(os.getenv("VIDEO_TARGET_FPS", "60")))
    audio_ducking_db: str = Field(default_factory=lambda: os.getenv("VIDEO_AUDIO_DUCKING_DB", "-15dB"))
    video_preset: str = Field(default_factory=lambda: os.getenv("VIDEO_PRESET", "veryfast"))
    temp_dir: Path = Field(default_factory=lambda: Path(os.getenv("TEMP_PROCESSING_DIR", "temp")))
    output_dir: Path = Field(default_factory=lambda: Path(os.getenv("OUTPUT_DIR", "output")))
    music_library_file: Path = Field(default=Path("config/music_library.json"))
    history_file: Path = Field(default=Path("data/history.json"))
    delete_input_after_processing: bool = Field(
        default_factory=lambda: os.getenv("DELETE_INPUT_AFTER_PROCESSING", "true").lower() == "true"
    )
    generate_thumbnail: bool = Field(
        default_factory=lambda: os.getenv("GENERATE_THUMBNAIL", "true").lower() == "true"
    )
    outro_tail_enabled: bool = Field(
        default_factory=lambda: os.getenv("OUTRO_TAIL_ENABLED", "true").lower() == "true"
    )
    outro_tail_path: Path = Field(
        default_factory=lambda: Path(os.getenv("OUTRO_TAIL_PATH", "assets/animations/like_share_subscribe_endcredits.mp4"))
    )
    outro_tail_duration: float = Field(
        default_factory=lambda: float(os.getenv("OUTRO_TAIL_DURATION", "9.5"))
    )


class PipelineSettings(BaseModel):
    environment: str = Field(default_factory=lambda: os.getenv("ENVIRONMENT", "development"))
    log_level: str = Field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO"))
    drive: GoogleDriveSettings = Field(default_factory=GoogleDriveSettings)
    gmail: GmailSettings = Field(default_factory=GmailSettings)
    gemini: GeminiSettings = Field(default_factory=GeminiSettings)
    youtube: YouTubeSettings = Field(default_factory=YouTubeSettings)
    peertube: PeerTubeSettings = Field(default_factory=PeerTubeSettings)
    fediverse: FediverseSettings = Field(default_factory=FediverseSettings)
    smtp: SMTPSettings = Field(default_factory=SMTPSettings)
    processing: ProcessingSettings = Field(default_factory=ProcessingSettings)


def get_settings() -> PipelineSettings:
    """Return loaded settings instance."""
    return PipelineSettings()
