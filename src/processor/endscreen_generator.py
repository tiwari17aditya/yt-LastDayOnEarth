"""Cinematic End-Screen & Outro Slate Generator for YouTube videos.

Renders a 1920x1080 10-15 second outro video with visually aligned
card bounding boxes for YouTube Studio's interactive elements:
- Video / Next Episode card (left)
- Series Playlist card (right)
- Channel Subscribe circular pill (center)
"""

import subprocess
from pathlib import Path
from typing import Optional
from PIL import Image, ImageDraw, ImageFont

from src.logging_config import get_logger
from src.exceptions import VideoProcessingError

logger = get_logger(component="EndScreenGenerator")


class EndScreenGenerator:
    """Generates 1920x1080 cinematic outro slates matching YouTube End Screen templates."""

    def __init__(self, output_dir: Path = Path("data/endscreens")) -> None:
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def create_endscreen_frame(
        self,
        output_image_path: Path,
        series_title: str = "LAST DAY ON EARTH: SURVIVAL",
        call_to_action: str = "THANKS FOR WATCHING • SUBSCRIBE FOR NEXT RAID",
    ) -> Path:
        """Generates a high-res 1920x1080 PNG frame with styled YouTube card placement guides."""
        img = Image.new("RGBA", (1920, 1080), (10, 12, 16, 255))
        draw = ImageDraw.Draw(img)

        # Subtle dark apocalyptic gradient background
        for y in range(1080):
            factor = y / 1080.0
            r = int(14 + 10 * factor)
            g = int(16 + 8 * factor)
            b = int(22 + 10 * factor)
            draw.line([(0, y), (1920, y)], fill=(r, g, b, 255))

        # Fonts
        def _get_font(size: int):
            for name in ["arialbd.ttf", "impact.ttf", "segoeui.ttf", "arial.ttf"]:
                try:
                    return ImageFont.truetype(name, size)
                except Exception:
                    continue
            return ImageFont.load_default()

        font_title = _get_font(48)
        font_sub = _get_font(28)
        font_card = _get_font(26)

        # Header Title
        t_box = draw.textbbox((0, 0), series_title, font=font_title)
        tw = t_box[2] - t_box[0]
        draw.text(((1920 - tw) // 2 + 2, 90 + 2), series_title, fill=(0, 0, 0, 200), font=font_title)
        draw.text(((1920 - tw) // 2, 90), series_title, fill=(240, 240, 240, 255), font=font_title)

        # Subtitle CTA
        sub_box = draw.textbbox((0, 0), call_to_action, font=font_sub)
        sw = sub_box[2] - sub_box[0]
        draw.text(((1920 - sw) // 2, 160), call_to_action, fill=(220, 38, 38, 255), font=font_sub)

        # Decorative Top & Bottom Borders
        draw.rectangle([120, 220, 1800, 222], fill=(220, 38, 38, 180))
        draw.rectangle([120, 960, 1800, 962], fill=(220, 38, 38, 180))

        # Left Card (Video / Next Episode) - 610 x 343 (Standard YouTube ratio)
        left_box = [160, 350, 770, 693]
        draw.rounded_rectangle(left_box, radius=12, fill=(18, 22, 28, 200), outline=(220, 38, 38, 220), width=3)
        draw.text((left_box[0] + 30, left_box[1] + 25), "🎬 NEXT EPISODE", fill=(255, 255, 255, 255), font=font_card)
        draw.text((left_box[0] + 30, left_box[1] + 70), "Click to continue watching", fill=(156, 163, 175, 255), font=font_sub)

        # Right Card (Playlist) - 610 x 343
        right_box = [1150, 350, 1760, 693]
        draw.rounded_rectangle(right_box, radius=12, fill=(18, 22, 28, 200), outline=(220, 38, 38, 220), width=3)
        draw.text((right_box[0] + 30, right_box[1] + 25), "📺 FULL SERIES PLAYLIST", fill=(255, 255, 255, 255), font=font_card)
        draw.text((right_box[0] + 30, right_box[1] + 70), "Watch all survival raids in order", fill=(156, 163, 175, 255), font=font_sub)

        # Center Subscribe Circle Pill - radius ~95px centered at (960, 520)
        cx, cy, r_circ = 960, 520, 95
        draw.ellipse([cx - r_circ, cy - r_circ, cx + r_circ, cy + r_circ], fill=(24, 28, 36, 230), outline=(220, 38, 38, 255), width=4)
        sub_pill = "SUBSCRIBE"
        sp_box = draw.textbbox((0, 0), sub_pill, font=font_sub)
        spw = sp_box[2] - sp_box[0]
        draw.text((cx - spw // 2, cy - 14), sub_pill, fill=(255, 255, 255, 255), font=font_sub)

        # Bottom Reminder
        bottom_note = "Leave a comment with your survival strategies! New episodes upload regularly."
        b_box = draw.textbbox((0, 0), bottom_note, font=font_sub)
        bw = b_box[2] - b_box[0]
        draw.text(((1920 - bw) // 2, 880), bottom_note, fill=(156, 163, 175, 240), font=font_sub)

        output_image_path.parent.mkdir(parents=True, exist_ok=True)
        img.convert("RGB").save(str(output_image_path), format="JPEG", quality=95)
        logger.info(f"Generated EndScreen background frame at {output_image_path}")
        return output_image_path

    def render_endscreen_clip(
        self,
        output_mp4_path: Path,
        duration: float = 12.0,
        audio_file: Optional[Path] = None,
        series_title: str = "LAST DAY ON EARTH: SURVIVAL",
    ) -> Path:
        """Renders a standalone 1920x1080 MP4 video clip for the EndScreen outro."""
        temp_frame = self.output_dir / f"endscreen_frame_{output_mp4_path.stem}.jpg"
        self.create_endscreen_frame(temp_frame, series_title=series_title)

        cmd = [
            "ffmpeg",
            "-y",
            "-loop", "1",
            "-i", str(temp_frame),
        ]

        if audio_file and Path(audio_file).exists():
            cmd.extend([
                "-i", str(audio_file),
                "-t", str(duration),
                "-filter_complex", f"[1:a]afade=t=out:st={duration - 2.5}:d=2.5[aout]",
                "-map", "0:v",
                "-map", "[aout]",
            ])
        else:
            # Generate silent audio track
            cmd.extend([
                "-f", "lavfi",
                "-i", "anullsrc=channel_layout=stereo:sample_rate=44100",
                "-t", str(duration),
                "-map", "0:v",
                "-map", "1:a",
            ])

        cmd.extend([
            "-c:v", "libx264",
            "-preset", "faster",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            "-b:a", "192k",
            str(output_mp4_path),
        ])

        output_mp4_path.parent.mkdir(parents=True, exist_ok=True)
        logger.info(f"Rendering EndScreen outro video: {output_mp4_path} ({duration}s)")
        res = subprocess.run(cmd, capture_output=True, text=True)

        if temp_frame.exists():
            temp_frame.unlink()

        if res.returncode != 0:
            logger.error(f"FFmpeg EndScreen rendering failed: {res.stderr}")
            raise VideoProcessingError(
                operation="render_endscreen_clip",
                root_cause=res.stderr[-500:] if res.stderr else "FFmpeg error",
                recovery_action="Check FFmpeg installation.",
                file_path=str(output_mp4_path),
            )

        logger.info(f"Successfully generated EndScreen video: {output_mp4_path}")
        return output_mp4_path
