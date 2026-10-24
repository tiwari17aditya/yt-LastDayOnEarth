"""Animated Funky 'Like, Share & Subscribe' Outro Tail Generator (5-8s).

Renders a high-energy, 1080p 60fps signature brand outro tail with animated
interactive buttons (Like, Share, Subscribe, Bell) to maximize subscriber conversions.
"""

import math
import subprocess
import shutil
from pathlib import Path
from typing import Optional, List, Tuple
from PIL import Image, ImageDraw, ImageFont

from src.logging_config import get_logger
from src.exceptions import VideoProcessingError

logger = get_logger(component="OutroGenerator")


class OutroTailGenerator:
    """Generates broadcast-quality animated Like/Share/Subscribe outro tail clips."""

    def __init__(
        self,
        assets_dir: Path = Path("assets/animations"),
        audio_library_dir: Path = Path("config/audio"),
    ) -> None:
        self.assets_dir = assets_dir
        self.assets_dir.mkdir(parents=True, exist_ok=True)
        self.audio_library_dir = audio_library_dir

    def _get_font(self, size: int, bold: bool = True) -> ImageFont.ImageFont:
        """Resolves system true-type fonts with clean fallbacks."""
        candidates = (
            ["impact.ttf", "arialbd.ttf", "segoeuib.ttf", "trebucbd.ttf", "arial.ttf"]
            if bold
            else ["segoeui.ttf", "arial.ttf", "tahoma.ttf"]
        )
        for name in candidates:
            try:
                return ImageFont.truetype(name, size)
            except Exception:
                continue
        return ImageFont.load_default()

    def _draw_button(
        self,
        draw: ImageDraw.ImageDraw,
        box: Tuple[int, int, int, int],
        bg_color: Tuple[int, int, int, int],
        border_color: Tuple[int, int, int, int],
        text: str,
        font: ImageFont.ImageFont,
        text_color: Tuple[int, int, int, int] = (255, 255, 255, 255),
        radius: int = 20,
        scale: float = 1.0,
    ) -> None:
        """Draws a styled rounded button with optional pop/pulse scaling."""
        x1, y1, x2, y2 = box
        cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
        w, h = (x2 - x1) * scale, (y2 - y1) * scale
        
        scaled_box = [cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2]
        
        # Outer glow / border
        draw.rounded_rectangle(
            [scaled_box[0] - 2, scaled_box[1] - 2, scaled_box[2] + 2, scaled_box[3] + 2],
            radius=int(radius * scale),
            fill=border_color,
        )
        draw.rounded_rectangle(
            scaled_box,
            radius=int(radius * scale),
            fill=bg_color,
        )

        # Center Text
        t_box = draw.textbbox((0, 0), text, font=font)
        tw = t_box[2] - t_box[0]
        th = t_box[3] - t_box[1]
        draw.text((cx - tw / 2, cy - th / 2 - 2), text, fill=text_color, font=font)

    def _draw_bell(
        self,
        draw: ImageDraw.ImageDraw,
        center: Tuple[int, int],
        angle_deg: float,
        ringing: bool,
        size: int = 38,
        color: Tuple[int, int, int, int] = (251, 191, 36, 255),
    ) -> None:
        """Draws an animated notification bell icon with tilt and radiating waves."""
        cx, cy = center
        rad = math.radians(angle_deg)
        cos_a = math.cos(rad)
        sin_a = math.sin(rad)

        def rotate_pt(px: float, py: float) -> Tuple[float, float]:
            dx, dy = px - cx, py - cy
            return (cx + dx * cos_a - dy * sin_a, cy + dx * sin_a + dy * cos_a)

        # Bell Dome
        top = rotate_pt(cx, cy - size)
        bottom_left = rotate_pt(cx - size * 0.8, cy + size * 0.5)
        bottom_right = rotate_pt(cx + size * 0.8, cy + size * 0.5)

        draw.polygon([top, bottom_left, bottom_right], fill=color)
        draw.ellipse([cx - size * 0.25, cy + size * 0.5, cx + size * 0.25, cy + size * 0.8], fill=(217, 119, 6, 255))

        # Radiating soundwave rings if ringing
        if ringing:
            for ring_r in [size + 12, size + 24]:
                draw.arc(
                    [cx - ring_r, cy - ring_r, cx + ring_r, cy + ring_r],
                    start=-60,
                    end=60,
                    fill=(251, 191, 36, 180),
                    width=3,
                )
                draw.arc(
                    [cx - ring_r, cy - ring_r, cx + ring_r, cy + ring_r],
                    start=120,
                    end=240,
                    fill=(251, 191, 36, 180),
                    width=3,
                )

    def render_frames(
        self,
        temp_dir: Path,
        duration: float = 6.0,
        fps: int = 30,
        series_title: str = "LAST DAY ON EARTH: SURVIVAL",
    ) -> int:
        """Renders animation frames into temp_dir using Pillow."""
        temp_dir.mkdir(parents=True, exist_ok=True)
        total_frames = int(duration * fps)

        font_header = self._get_font(52, bold=True)
        font_sub = self._get_font(26, bold=False)
        font_btn = self._get_font(30, bold=True)
        font_small = self._get_font(22, bold=True)

        for f in range(total_frames):
            t = f / fps  # Current timestamp in seconds

            # 1. Background Canvas (Apocalyptic deep slate with subtle pulsing grid)
            bg = Image.new("RGBA", (1920, 1080), (12, 14, 18, 255))
            draw = ImageDraw.Draw(bg)

            # Gradient background
            pulse = math.sin(t * 3.0) * 0.15 + 0.85
            for y in range(0, 1080, 4):
                factor = y / 1080.0
                r = int(14 + 14 * factor * pulse)
                g = int(18 + 12 * factor)
                b = int(24 + 16 * factor * pulse)
                draw.rectangle([(0, y), (1920, y + 4)], fill=(r, g, b, 255))

            # Decorative neon grid lines (Top and Bottom accent borders)
            draw.rectangle([100, 120, 1820, 124], fill=(220, 38, 38, 220))
            draw.rectangle([100, 960, 1820, 964], fill=(220, 38, 38, 220))

            # 2. Main Title Banner ("THANKS FOR WATCHING!")
            # Smooth elastic entrance (0.0 to 0.8s)
            title_progress = min(1.0, t / 0.7)
            title_y = 170 + int((1.0 - math.sin(title_progress * math.pi / 2)) * -60)
            title_alpha = int(title_progress * 255)

            title_text = "THANKS FOR WATCHING!"
            t_box = draw.textbbox((0, 0), title_text, font=font_header)
            tw = t_box[2] - t_box[0]

            # Title shadow & text
            draw.text(((1920 - tw) // 2 + 3, title_y + 3), title_text, fill=(0, 0, 0, 200), font=font_header)
            draw.text(((1920 - tw) // 2, title_y), title_text, fill=(255, 255, 255, title_alpha), font=font_header)

            # Sub-banner
            sub_text = f"🔥 {series_title} • NEW EPISODES REGULARLY"
            s_box = draw.textbbox((0, 0), sub_text, font=font_sub)
            sw = s_box[2] - s_box[0]
            draw.text(((1920 - sw) // 2, title_y + 75), sub_text, fill=(220, 38, 38, 240), font=font_sub)

            # 3. Action Buttons Row (Y: 480 - 640)
            # Button 1: LIKE BUTTON (Left, center ~500)
            like_active = t >= 1.6
            like_scale = 1.0 + (0.18 * math.sin((t - 1.6) * 12) if 1.6 <= t <= 2.2 else 0.0)
            like_bg = (6, 182, 212, 255) if like_active else (30, 41, 59, 230)
            like_border = (34, 211, 238, 255) if like_active else (71, 85, 105, 200)
            like_label = "👍 LIKED!" if like_active else "👍 LIKE"

            self._draw_button(
                draw=draw,
                box=(330, 460, 630, 560),
                bg_color=like_bg,
                border_color=like_border,
                text=like_label,
                font=font_btn,
                scale=like_scale,
            )

            # Button 2: SHARE BUTTON (Middle, center ~960)
            share_active = t >= 2.6
            share_scale = 1.0 + (0.18 * math.sin((t - 2.6) * 12) if 2.6 <= t <= 3.2 else 0.0)
            share_bg = (16, 185, 129, 255) if share_active else (30, 41, 59, 230)
            share_border = (52, 211, 153, 255) if share_active else (71, 85, 105, 200)
            share_label = "🚀 SHARED!" if share_active else "↗ SHARE"

            self._draw_button(
                draw=draw,
                box=(810, 460, 1110, 560),
                bg_color=share_bg,
                border_color=share_border,
                text=share_label,
                font=font_btn,
                scale=share_scale,
            )

            # Button 3: SUBSCRIBE BUTTON (Right, center ~1430)
            sub_active = t >= 3.6
            sub_scale = 1.0 + (0.22 * math.sin((t - 3.6) * 12) if 3.6 <= t <= 4.2 else 0.0)
            sub_bg = (15, 23, 42, 255) if sub_active else (220, 38, 38, 255)
            sub_border = (34, 197, 94, 255) if sub_active else (239, 68, 68, 255)
            sub_label = "✓ SUBSCRIBED" if sub_active else "SUBSCRIBE"

            self._draw_button(
                draw=draw,
                box=(1270, 460, 1650, 560),
                bg_color=sub_bg,
                border_color=sub_border,
                text=sub_label,
                font=font_btn,
                scale=sub_scale,
            )

            # 4. Animated Golden Notification Bell (Near Subscribe Button)
            bell_ringing = t >= 4.4
            bell_angle = math.sin((t - 4.4) * 28) * 18.0 if bell_ringing else 0.0
            bell_center = (1710, 510)
            self._draw_bell(draw=draw, center=bell_center, angle_deg=bell_angle, ringing=bell_ringing)

            # Bell subtext if active
            if bell_ringing:
                bell_note = "🔔 ALL NOTIFICATIONS ON"
                bn_box = draw.textbbox((0, 0), bell_note, font=font_small)
                bnw = bn_box[2] - bn_box[0]
                draw.text((bell_center[0] - bnw // 2 - 20, 580), bell_note, fill=(251, 191, 36, 255), font=font_small)

            # 5. Interactive Cursor Pointer Animation (Visual Guide clicking elements)
            # Timed cursor motion hitting Like (1.6s), Share (2.6s), Subscribe (3.6s), Bell (4.4s)
            cursor_pos = None
            if 1.2 <= t < 2.0:
                p = (t - 1.2) / 0.8
                cursor_pos = (int(300 + p * 180), int(620 - math.sin(p * math.pi) * 80))
            elif 2.2 <= t < 3.0:
                p = (t - 2.2) / 0.8
                cursor_pos = (int(760 + p * 200), int(620 - math.sin(p * math.pi) * 80))
            elif 3.2 <= t < 4.0:
                p = (t - 3.2) / 0.8
                cursor_pos = (int(1200 + p * 260), int(620 - math.sin(p * math.pi) * 80))
            elif 4.0 <= t < 4.8:
                p = (t - 4.0) / 0.8
                cursor_pos = (int(1620 + p * 90), int(580 - math.sin(p * math.pi) * 70))

            if cursor_pos:
                cx, cy = cursor_pos
                # Draw sleek pointer arrow
                draw.polygon([(cx, cy), (cx + 18, cy + 18), (cx + 8, cy + 18), (cx + 12, cy + 28), (cx + 6, cy + 30), (cx + 2, cy + 20), (cx, cy + 24)], fill=(255, 255, 255, 240), outline=(0, 0, 0, 255))

            # 6. Bottom Call to Action
            bottom_msg = "DROP A COMMENT • SEE YOU IN THE NEXT SURVIVAL RAID!"
            b_box = draw.textbbox((0, 0), bottom_msg, font=font_sub)
            bw = b_box[2] - b_box[0]
            draw.text(((1920 - bw) // 2, 860), bottom_msg, fill=(203, 213, 225, 230), font=font_sub)

            # 7. Smooth Fade to Black at the very end (5.2s - 6.0s)
            if t >= 5.2:
                fade_factor = (t - 5.2) / 0.8
                fade_alpha = int(fade_factor * 255)
                overlay = Image.new("RGBA", (1920, 1080), (0, 0, 0, fade_alpha))
                bg.paste(overlay, (0, 0), overlay)

            frame_path = temp_dir / f"frame_{f:04d}.jpg"
            bg.convert("RGB").save(str(frame_path), format="JPEG", quality=92)

        return total_frames

    def render_outro_clip(
        self,
        output_mp4_path: Optional[Path] = None,
        duration: float = 6.0,
        fps: int = 30,
        audio_track: Optional[Path] = None,
        series_title: str = "LAST DAY ON EARTH: SURVIVAL",
        force_recreate: bool = False,
    ) -> Path:
        """Renders the standalone 1920x1080 animated outro MP4 video."""
        target_path = output_mp4_path or (self.assets_dir / "like_share_subscribe.mp4")

        # Reuse cached animation if exists and valid
        if target_path.exists() and target_path.stat().st_size > 50000 and not force_recreate:
            logger.info(f"Using existing cached outro tail animation: {target_path}")
            return target_path

        temp_frames_dir = self.assets_dir / "temp_frames"
        logger.info(f"Rendering animated outro tail frames ({duration}s @ {fps}fps)...")

        try:
            total_frames = self.render_frames(
                temp_dir=temp_frames_dir,
                duration=duration,
                fps=fps,
                series_title=series_title,
            )

            # Select audio sting (punchy upbeat energetic music)
            selected_audio = audio_track
            if not selected_audio or not Path(selected_audio).exists():
                for candidate in ["electro_cabello.mp3", "groove_grove.mp3", "decisions.mp3"]:
                    cand_path = self.audio_library_dir / candidate
                    if cand_path.exists():
                        selected_audio = cand_path
                        break

            cmd = [
                "ffmpeg",
                "-y",
                "-framerate", str(fps),
                "-i", str(temp_frames_dir / "frame_%04d.jpg"),
            ]

            if selected_audio and Path(selected_audio).exists():
                cmd.extend([
                    "-i", str(selected_audio),
                    "-t", str(duration),
                    "-filter_complex", f"[1:a]afade=t=in:st=0:d=0.3,afade=t=out:st={duration - 1.2}:d=1.2[aout]",
                    "-map", "0:v",
                    "-map", "[aout]",
                ])
            else:
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
                "-movflags", "+faststart",
                str(target_path),
            ])

            target_path.parent.mkdir(parents=True, exist_ok=True)
            logger.info(f"Assembling animated outro tail via FFmpeg: {target_path}")
            res = subprocess.run(cmd, capture_output=True, text=True)

            if res.returncode != 0:
                logger.error(f"FFmpeg outro animation rendering failed: {res.stderr}")
                raise VideoProcessingError(
                    operation="render_outro_clip",
                    root_cause=res.stderr[-400:] if res.stderr else "FFmpeg error",
                    recovery_action="Inspect FFmpeg codecs and disk space.",
                    file_path=str(target_path),
                )

            logger.info(f"Successfully generated animated outro tail: {target_path} ({duration}s)")
            return target_path

        finally:
            # Clean up temp frames to conserve disk space
            if temp_frames_dir.exists():
                shutil.rmtree(temp_frames_dir, ignore_errors=True)
