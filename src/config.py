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
    client_id: Optional[str] = Field(default_factory=lambda: os.getenv("GCP_CLIENT_ID"))
    client_secret: Optional[str] = Field(default_factory=lambda: os.getenv("GCP_CLIENT_SECRET"))
    refresh_token: Optional[str] = Field(default_factory=lambda: os.getenv("GCP_REFRESH_TOKEN"))
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


class ProcessingSettings(BaseModel):
    resolution: str = Field(default_factory=lambda: os.getenv("VIDEO_RESOLUTION", "1920x1080"))
    target_fps: int = Field(default_factory=lambda: int(os.getenv("VIDEO_TARGET_FPS", "60")))
    audio_ducking_db: str = Field(default_factory=lambda: os.getenv("VIDEO_AUDIO_DUCKING_DB", "-8dB"))
    video_preset: str = Field(default_factory=lambda: os.getenv("VIDEO_PRESET", "veryfast"))
    temp_dir: Path = Field(default_factory=lambda: Path(os.getenv("TEMP_PROCESSING_DIR", "temp")))
    output_dir: Path = Field(default_factory=lambda: Path(os.getenv("OUTPUT_DIR", "output")))
    music_library_file: Path = Field(default=Path("config/music_library.json"))
    history_file: Path = Field(default=Path("data/history.json"))


class PipelineSettings(BaseModel):
    environment: str = Field(default_factory=lambda: os.getenv("ENVIRONMENT", "development"))
    log_level: str = Field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO"))
    drive: GoogleDriveSettings = Field(default_factory=GoogleDriveSettings)
    gmail: GmailSettings = Field(default_factory=GmailSettings)
    gemini: GeminiSettings = Field(default_factory=GeminiSettings)
    youtube: YouTubeSettings = Field(default_factory=YouTubeSettings)
    smtp: SMTPSettings = Field(default_factory=SMTPSettings)
    processing: ProcessingSettings = Field(default_factory=ProcessingSettings)


def get_settings() -> PipelineSettings:
    """Return loaded settings instance."""
    return PipelineSettings()
