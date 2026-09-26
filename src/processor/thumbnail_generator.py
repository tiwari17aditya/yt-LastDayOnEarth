"""Automated high-CTR thumbnail generation from video gameplay keyframes."""

import subprocess
from pathlib import Path
from typing import Optional, List, Any
from PIL import Image, ImageDraw, ImageFont, ImageEnhance
from src.logging_config import get_logger
from src.exceptions import VideoProcessingError

logger = get_logger(component="ThumbnailGenerator")


class ThumbnailGenerator:
    """Extracts high-impact gameplay frames, enhances colors, and adds clean branding badges."""

    def __init__(self, output_dir: Path = Path("output")) -> None:
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def select_best_timestamp(self, events: Optional[List[Any]] = None, duration: float = 180.0) -> float:
        """Picks optimal timestamp featuring prominent gameplay action rather than loading screens."""
        if events:
            # Look for active crafting or interaction events occurring once player is in base (>= 30.0s)
            action_keywords = ["bench", "crafting", "smelting", "storage", "chests", "defense", "raid"]
            for ev in events:
                desc = getattr(ev, "description", "").lower()
                st = getattr(ev, "start_time", 0.0)
                if any(kw in desc for kw in action_keywords) and st >= 30.0:
                    return float(st + 5.0)

            # Fallback to any action event > 15.0s
            for ev in events:
                desc = getattr(ev, "description", "").lower()
                st = getattr(ev, "start_time", 0.0)
                if any(kw in desc for kw in action_keywords) and st > 15.0:
                    return float(st + 2.0)

            # Fallback to second event if first is global map
            if len(events) > 1:
                return float(getattr(events[1], "start_time", 15.0) + 1.0)

        # Default to 25% of video duration (avoiding intro screen)
        if duration > 40.0:
            return min(duration * 0.25, 45.0)
        return max(5.0, duration * 0.2)

    def extract_enhanced_frame(
        self,
        video_path: Path,
        output_frame_path: Path,
        timestamp: float,
    ) -> Path:
        """Extracts high-resolution frame and applies color-grade filter to pop in YouTube dark feed."""
        output_frame_path.parent.mkdir(parents=True, exist_ok=True)

        # Video filter: Slight contrast boost (1.12), saturation (1.25), and subtle unsharp
        vf = "eq=contrast=1.12:brightness=0.02:saturation=1.25,unsharp=5:5:0.8:5:5:0.0"

        cmd = [
            "ffmpeg",
            "-y",
            "-ss", str(max(0.0, timestamp)),
            "-i", str(video_path),
            "-vf", vf,
            "-vframes", "1",
            "-q:v", "2",
            str(output_frame_path),
        ]

        logger.info(f"Extracting thumbnail keyframe at {timestamp:.2f}s from {video_path.name}")
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, check=True)
            if not output_frame_path.exists():
                raise VideoProcessingError(
                    operation="extract_enhanced_frame",
                    root_cause=f"FFmpeg exited without writing thumbnail: {res.stderr}",
                    recovery_action="Check FFmpeg installation and video format.",
                    file_path=str(video_path),
                )
            return output_frame_path
        except subprocess.CalledProcessError as e:
            logger.error(f"FFmpeg thumbnail extraction failed: {e.stderr}")
            raise VideoProcessingError(
                operation="extract_enhanced_frame",
                root_cause=e.stderr or str(e),
                recovery_action="Ensure video has valid video stream and FFmpeg is in PATH.",
                file_path=str(video_path),
            )

    def apply_badge_overlay(
        self,
        image_path: Path,
        badge_text: str,
        series_tag: str = "LDoE SURVIVAL",
    ) -> Path:
        """Draws a sleek, modern, semi-transparent pill badge in the top-left corner."""
        try:
            with Image.open(image_path) as img:
                img = img.convert("RGBA")
                width, height = img.size

                # Create overlay canvas
                overlay = Image.new("RGBA", img.size, (255, 255, 255, 0))
                draw = ImageDraw.Draw(overlay)

                # Try loading font or fallback to default
                try:
                    font_main = ImageFont.truetype("arialbd.ttf", int(height * 0.045))
                    font_sub = ImageFont.truetype("arial.ttf", int(height * 0.028))
                except Exception:
                    font_main = ImageFont.load_default()
                    font_sub = font_main

                # Badge dimensions and positioning (Top-left, safely away from YouTube UI)
                margin_x = int(width * 0.04)
                margin_y = int(height * 0.06)
                padding = int(height * 0.02)

                text_line1 = series_tag.upper()
                text_line2 = badge_text.upper()

                # Calculate text bounding boxes
                bbox1 = draw.textbbox((0, 0), text_line1, font=font_sub)
                bbox2 = draw.textbbox((0, 0), text_line2, font=font_main)

                box_w = max(bbox1[2] - bbox1[0], bbox2[2] - bbox2[0]) + (padding * 2)
                line1_h = bbox1[3] - bbox1[1]
                line2_h = bbox2[3] - bbox2[1]
                box_h = line1_h + line2_h + (padding * 2) + 6

                pill_x0 = margin_x
                pill_y0 = margin_y
                pill_x1 = pill_x0 + box_w
                pill_y1 = pill_y0 + box_h

                # Semi-transparent dark pill background with subtle red/orange accent border
                draw.rounded_rectangle(
                    [pill_x0, pill_y0, pill_x1, pill_y1],
                    radius=12,
                    fill=(15, 17, 23, 220),
                    outline=(230, 81, 0, 240),
                    width=3,
                )

                # Series Tag (Orange/Yellow accent)
                draw.text(
                    (pill_x0 + padding, pill_y0 + padding),
                    text_line1,
                    font=font_sub,
                    fill=(255, 179, 0, 255),
                )

                # Main Badge (Episode / Action text in crisp white)
                draw.text(
                    (pill_x0 + padding, pill_y0 + padding + line1_h + 6),
                    text_line2,
                    font=font_main,
                    fill=(255, 255, 255, 255),
                )

                # Composite overlay
                final_img = Image.alpha_composite(img, overlay).convert("RGB")
                final_img.save(image_path, "JPEG", quality=92)
                logger.info(f"Burned badge '{badge_text}' into thumbnail {image_path.name}")
                return image_path

        except Exception as e:
            logger.warning(f"Could not apply badge overlay to thumbnail: {e}")
            return image_path

    def generate_thumbnail(
        self,
        video_path: Path,
        output_path: Path,
        events: Optional[List[Any]] = None,
        duration: float = 180.0,
        episode_number: Optional[int] = None,
        badge_text: Optional[str] = None,
        timestamp: Optional[float] = None,
    ) -> Path:
        """Full orchestration: keyframe extraction, color enhancement, and badge branding."""
        ts = timestamp if timestamp is not None else self.select_best_timestamp(events=events, duration=duration)
        self.extract_enhanced_frame(video_path, output_path, ts)

        # Default badge text if episode given
        label = badge_text
        if not label and episode_number is not None:
            label = f"EPISODE #{episode_number:02d}"

        if label:
            self.apply_badge_overlay(output_path, badge_text=label)

        logger.info(f"Custom YouTube thumbnail generated successfully at: {output_path}")
        return output_path
