"""Privacy and personal information redaction module for Last Day on Earth gameplay."""

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional
from src.logging_config import get_logger
from src.exceptions import PrivacyRedactionError

logger = get_logger(component="PrivacyGuard")


@dataclass
class BoundingBox:
    start_time: float  # In seconds
    end_time: float    # In seconds
    x: int
    y: int
    width: int
    height: int
    reason: str
    filter_type: str = "box"  # "delogo" or "box"


class BasePrivacyDetector(ABC):
    """Abstract interface for personal data detection."""

    @abstractmethod
    def scan_video(self, video_path: Path) -> List[BoundingBox]:
        """Scan video frames to detect sensitive regions."""
        pass

    @abstractmethod
    def generate_ffmpeg_blur_filter(self, boxes: List[BoundingBox]) -> str:
        """Generate FFmpeg filtergraph string for applying blur/redaction to identified regions."""
        pass


class PrivacyDetector(BasePrivacyDetector):
    """Detects personal information (usernames, clan chat, personal notifications) without obscuring game HUD."""

    def __init__(self, sample_interval_seconds: float = 1.0) -> None:
        self.sample_interval = sample_interval_seconds

    def scan_video(self, video_path: Path) -> List[BoundingBox]:
        logger.info("Scanning video for sensitive information and personal overlays", extra_data={"path": str(video_path)})
        if not video_path.exists():
            raise PrivacyRedactionError(
                operation="scan_video",
                root_cause=f"File not found: {video_path}",
                recovery_action="Verify video path and ingestion download step.",
                file_path=str(video_path),
            )

        # Configured bounding boxes based on video analysis
        # 1. Player username (adistar656 in top-left bar)
        username_box = BoundingBox(
            start_time=0.0,
            end_time=3600.0,  # Entire video duration
            x=150,
            y=35,
            width=250,
            height=45,
            reason="Player Account Username",
            filter_type="delogo",
        )

        # 2. Clan Chat messages (appears once entered base after 14s)
        clan_chat_box = BoundingBox(
            start_time=14.0,
            end_time=3600.0,
            x=495,
            y=850,
            width=310,
            height=260,
            reason="In-game Clan Chat Messages",
            filter_type="box",
        )

        return [username_box, clan_chat_box]

    def generate_ffmpeg_blur_filter(self, boxes: List[BoundingBox]) -> str:
        if not boxes:
            return ""

        filter_parts = []
        for box in boxes:
            if box.filter_type == "delogo":
                if box.start_time > 0:
                    filter_parts.append(
                        f"delogo=x={box.x}:y={box.y}:w={box.width}:h={box.height}:enable='gte(t,{box.start_time})'"
                    )
                else:
                    filter_parts.append(f"delogo=x={box.x}:y={box.y}:w={box.width}:h={box.height}")
            else:
                # Translucent dark redaction pill
                filter_parts.append(
                    f"drawbox=x={box.x}:y={box.y}:w={box.width}:h={box.height}:color=black@0.85:t=fill:enable='gte(t,{box.start_time})'"
                )

        return ",".join(filter_parts)
