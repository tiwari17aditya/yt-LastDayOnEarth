"""Animated Funky 'Like, Share & Subscribe' Outro Tail Generator (7-10s).

Provides multiple broadcast-quality animation styles (7.5s, 8.5s, 10.0s) with
harmonious geometry, balanced margins, integrated bell notifications, and zero crowding.
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
        radius: int = 16,
        scale: float = 1.0,
        subtext: Optional[str] = None,
        subfont: Optional[ImageFont.ImageFont] = None,
    ) -> None:
        """Draws a styled rounded button with pop/pulse scaling and optional subtext."""
        x1, y1, x2, y2 = box
        cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
        w, h = (x2 - x1) * scale, (y2 - y1) * scale

        scaled_box = [cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2]

        # Outer glow border
        draw.rounded_rectangle(
            [scaled_box[0] - 3, scaled_box[1] - 3, scaled_box[2] + 3, scaled_box[3] + 3],
            radius=int(radius * scale),
            fill=border_color,
        )
        # Inner button fill
        draw.rounded_rectangle(
            scaled_box,
            radius=int(radius * scale),
            fill=bg_color,
        )

        # Center Text
        t_box = draw.textbbox((0, 0), text, font=font)
        tw = t_box[2] - t_box[0]
        th = t_box[3] - t_box[1]

        y_offset = -10 if subtext else -2
        draw.text((cx - tw / 2, cy - th / 2 + y_offset), text, fill=text_color, font=font)

        if subtext and subfont:
            sb_box = draw.textbbox((0, 0), subtext, font=subfont)
            sbw = sb_box[2] - sb_box[0]
            draw.text((cx - sbw / 2, cy + th / 2 + 2), subtext, fill=(203, 213, 225, 230), font=subfont)

    def _draw_bell(
        self,
        draw: ImageDraw.ImageDraw,
        center: Tuple[int, int],
        angle_deg: float,
        ringing: bool,
        size: int = 34,
        color: Tuple[int, int, int, int] = (251, 191, 36, 255),
    ) -> None:
        """Draws a clean notification bell icon with rotational wobble and soundwaves."""
        cx, cy = center
        rad = math.radians(angle_deg)
        cos_a = math.cos(rad)
        sin_a = math.sin(rad)

        def rotate_pt(px: float, py: float) -> Tuple[float, float]:
            dx, dy = px - cx, py - cy
            return (cx + dx * cos_a - dy * sin_a, cy + dx * sin_a + dy * cos_a)

        # Bell Dome
        top = rotate_pt(cx, cy - size * 0.9)
        bottom_left = rotate_pt(cx - size * 0.75, cy + size * 0.45)
        bottom_right = rotate_pt(cx + size * 0.75, cy + size * 0.45)

        draw.polygon([top, bottom_left, bottom_right], fill=color)
        draw.ellipse([cx - size * 0.22, cy + size * 0.45, cx + size * 0.22, cy + size * 0.75], fill=(217, 119, 6, 255))
        draw.ellipse([cx - size * 0.15, cy - size * 1.1, cx + size * 0.15, cy - size * 0.8], fill=color)

        # Radiating soundwave rings if ringing
        if ringing:
            for ring_r in [size + 10, size + 22]:
                draw.arc(
                    [cx - ring_r, cy - ring_r, cx + ring_r, cy + ring_r],
                    start=-65,
                    end=65,
                    fill=(251, 191, 36, 200),
                    width=3,
                )
                draw.arc(
                    [cx - ring_r, cy - ring_r, cx + ring_r, cy + ring_r],
                    start=115,
                    end=245,
                    fill=(251, 191, 36, 200),
                    width=3,
                )

    def _draw_cursor(self, draw: ImageDraw.ImageDraw, pos: Tuple[int, int]) -> None:
        """Draws a smooth pointer arrow."""
        cx, cy = pos
        draw.polygon(
            [
                (cx, cy),
                (cx + 20, cy + 20),
                (cx + 9, cy + 20),
                (cx + 14, cy + 30),
                (cx + 7, cy + 32),
                (cx + 2, cy + 22),
                (cx, cy + 26),
            ],
            fill=(255, 255, 255, 255),
            outline=(15, 23, 42, 255),
        )

    # -------------------------------------------------------------------------
    # STYLE 1: Cyber-Survival Action Row (7.5s)
    # Balanced horizontal row with integrated subscribe + bell container
    # -------------------------------------------------------------------------
    def render_frames_cyber_row(
        self,
        temp_dir: Path,
        duration: float = 7.5,
        fps: int = 30,
        series_title: str = "LAST DAY ON EARTH: SURVIVAL",
    ) -> int:
        """Renders 7.5s 'Cyber Row' style: perfectly balanced row with unified Subscribe+Bell pill."""
        temp_dir.mkdir(parents=True, exist_ok=True)
        total_frames = int(duration * fps)

        font_header = self._get_font(52, bold=True)
        font_sub = self._get_font(26, bold=False)
        font_btn = self._get_font(30, bold=True)
        font_btn_lg = self._get_font(32, bold=True)
        font_small = self._get_font(20, bold=True)

        # Layout Geometry (Total width 1420px, centered from X=250 to X=1670)
        # 1. LIKE: [250, 480, 590, 580] (width 340)
        # 2. SHARE: [640, 480, 980, 580] (width 340)
        # 3. SUBSCRIBE + BELL: [1030, 480, 1670, 580] (width 640 - unified spacious container)

        for f in range(total_frames):
            t = f / fps

            bg = Image.new("RGBA", (1920, 1080), (12, 14, 18, 255))
            draw = ImageDraw.Draw(bg)

            # Gradient background
            pulse = math.sin(t * 3.0) * 0.12 + 0.88
            for y in range(0, 1080, 4):
                factor = y / 1080.0
                r = int(14 + 14 * factor * pulse)
                g = int(18 + 12 * factor)
                b = int(26 + 18 * factor * pulse)
                draw.rectangle([(0, y), (1920, y + 4)], fill=(r, g, b, 255))

            # Decorative neon accent borders
            draw.rectangle([140, 140, 1780, 143], fill=(220, 38, 38, 220))
            draw.rectangle([140, 940, 1780, 943], fill=(220, 38, 38, 220))

            # Header Banner
            title_progress = min(1.0, t / 0.8)
            title_y = 190 + int((1.0 - math.sin(title_progress * math.pi / 2)) * -50)
            title_text = "THANKS FOR WATCHING!"
            t_box = draw.textbbox((0, 0), title_text, font=font_header)
            tw = t_box[2] - t_box[0]
            draw.text(((1920 - tw) // 2 + 3, title_y + 3), title_text, fill=(0, 0, 0, 200), font=font_header)
            draw.text(((1920 - tw) // 2, title_y), title_text, fill=(255, 255, 255, 255), font=font_header)

            sub_text = f"🔥 {series_title} • NEW EPISODES REGULARLY"
            s_box = draw.textbbox((0, 0), sub_text, font=font_sub)
            sw = s_box[2] - s_box[0]
            draw.text(((1920 - sw) // 2, title_y + 75), sub_text, fill=(220, 38, 38, 240), font=font_sub)

            # --- Button 1: LIKE ---
            like_active = t >= 1.8
            like_scale = 1.0 + (0.16 * math.sin((t - 1.8) * 12) if 1.8 <= t <= 2.4 else 0.0)
            like_bg = (6, 182, 212, 255) if like_active else (30, 41, 59, 230)
            like_border = (34, 211, 238, 255) if like_active else (71, 85, 105, 200)
            like_label = "👍 LIKED!" if like_active else "👍 LIKE"
            self._draw_button(
                draw=draw,
                box=(250, 480, 590, 580),
                bg_color=like_bg,
                border_color=like_border,
                text=like_label,
                font=font_btn,
                scale=like_scale,
            )

            # --- Button 2: SHARE ---
            share_active = t >= 2.8
            share_scale = 1.0 + (0.16 * math.sin((t - 2.8) * 12) if 2.8 <= t <= 3.4 else 0.0)
            share_bg = (16, 185, 129, 255) if share_active else (30, 41, 59, 230)
            share_border = (52, 211, 153, 255) if share_active else (71, 85, 105, 200)
            share_label = "🚀 SHARED!" if share_active else "↗ SHARE"
            self._draw_button(
                draw=draw,
                box=(640, 480, 980, 580),
                bg_color=share_bg,
                border_color=share_border,
                text=share_label,
                font=font_btn,
                scale=share_scale,
            )

            # --- Button 3: UNIFIED SUBSCRIBE + BELL CONTAINER ---
            sub_active = t >= 4.0
            sub_scale = 1.0 + (0.18 * math.sin((t - 4.0) * 12) if 4.0 <= t <= 4.6 else 0.0)
            pill_box = [1030, 480, 1670, 580]
            cx, cy = (pill_box[0] + pill_box[2]) / 2, (pill_box[1] + pill_box[3]) / 2
            pw, ph = (pill_box[2] - pill_box[0]) * sub_scale, (pill_box[3] - pill_box[1]) * sub_scale
            s_box_scaled = [cx - pw / 2, cy - ph / 2, cx + pw / 2, cy + ph / 2]

            sub_bg = (15, 23, 42, 255) if sub_active else (220, 38, 38, 255)
            sub_border = (34, 197, 94, 255) if sub_active else (239, 68, 68, 255)
            draw.rounded_rectangle([s_box_scaled[0] - 3, s_box_scaled[1] - 3, s_box_scaled[2] + 3, s_box_scaled[3] + 3], radius=18, fill=sub_border)
            draw.rounded_rectangle(s_box_scaled, radius=18, fill=sub_bg)

            # Subscribe text (Left wing of container)
            sub_label = "✓ SUBSCRIBED" if sub_active else "SUBSCRIBE"
            st_box = draw.textbbox((0, 0), sub_label, font=font_btn_lg)
            st_w = st_box[2] - st_box[0]
            st_h = st_box[3] - st_box[1]
            draw.text((s_box_scaled[0] + 50, cy - st_h / 2 - 2), sub_label, fill=(255, 255, 255, 255), font=font_btn_lg)

            # Subtle vertical divider line before bell section
            divider_x = s_box_scaled[0] + pw - 150
            draw.line([(divider_x, s_box_scaled[1] + 18), (divider_x, s_box_scaled[3] - 18)], fill=(100, 116, 139, 160), width=2)

            # Bell section (Right wing of container - roomy and centered at divider_x + 75)
            bell_ringing = t >= 5.0
            bell_angle = math.sin((t - 5.0) * 26) * 16.0 if bell_ringing else 0.0
            bell_center = (int(divider_x + 75), int(cy))
            self._draw_bell(draw=draw, center=bell_center, angle_deg=bell_angle, ringing=bell_ringing, size=32)

            if bell_ringing:
                b_note = "🔔 ALL ON"
                bn_box = draw.textbbox((0, 0), b_note, font=font_small)
                bn_w = bn_box[2] - bn_box[0]
                draw.text((bell_center[0] - bn_w // 2, int(cy + 62)), b_note, fill=(251, 191, 36, 255), font=font_small)

            # Cursor Pointer Movement
            cursor_pos = None
            if 1.3 <= t < 2.0:
                p = (t - 1.3) / 0.7
                cursor_pos = (int(280 + p * 140), int(640 - math.sin(p * math.pi) * 80))
            elif 2.3 <= t < 3.0:
                p = (t - 2.3) / 0.7
                cursor_pos = (int(670 + p * 140), int(640 - math.sin(p * math.pi) * 80))
            elif 3.5 <= t < 4.2:
                p = (t - 3.5) / 0.7
                cursor_pos = (int(1060 + p * 160), int(640 - math.sin(p * math.pi) * 80))
            elif 4.6 <= t < 5.3:
                p = (t - 4.6) / 0.7
                cursor_pos = (int(divider_x + 20 + p * 55), int(620 - math.sin(p * math.pi) * 70))

            if cursor_pos:
                self._draw_cursor(draw, cursor_pos)

            # Bottom Callout
            bottom_msg = "DROP A COMMENT WITH YOUR STRATEGIES • SEE YOU IN THE NEXT RAID!"
            b_box = draw.textbbox((0, 0), bottom_msg, font=font_sub)
            bw = b_box[2] - b_box[0]
            draw.text(((1920 - bw) // 2, 850), bottom_msg, fill=(203, 213, 225, 230), font=font_sub)

            # Fade to black (last 0.8s)
            if t >= duration - 0.8:
                fade_alpha = int(((t - (duration - 0.8)) / 0.8) * 255)
                overlay = Image.new("RGBA", (1920, 1080), (0, 0, 0, fade_alpha))
                bg.paste(overlay, (0, 0), overlay)

            frame_path = temp_dir / f"frame_{f:04d}.jpg"
            bg.convert("RGB").save(str(frame_path), format="JPEG", quality=92)

        return total_frames

    # -------------------------------------------------------------------------
    # STYLE 2: Two-Tier Hero Studio (8.5s)
    # Upper tier wings (Like & Share) + Lower giant centered Hero Subscribe Bar
    # -------------------------------------------------------------------------
    def render_frames_two_tier(
        self,
        temp_dir: Path,
        duration: float = 8.5,
        fps: int = 30,
        series_title: str = "LAST DAY ON EARTH: SURVIVAL",
    ) -> int:
        """Renders 8.5s 'Two-Tier' style: symmetric floating wings + giant centered Subscribe hero bar."""
        temp_dir.mkdir(parents=True, exist_ok=True)
        total_frames = int(duration * fps)

        font_header = self._get_font(54, bold=True)
        font_sub = self._get_font(26, bold=False)
        font_btn = self._get_font(30, bold=True)
        font_hero = self._get_font(36, bold=True)
        font_small = self._get_font(22, bold=True)

        for f in range(total_frames):
            t = f / fps

            bg = Image.new("RGBA", (1920, 1080), (10, 12, 16, 255))
            draw = ImageDraw.Draw(bg)

            # Background subtle cyber grid & glow
            pulse = math.sin(t * 2.5) * 0.15 + 0.85
            for y in range(0, 1080, 4):
                factor = y / 1080.0
                r = int(12 + 16 * factor * pulse)
                g = int(15 + 14 * factor)
                b = int(24 + 20 * factor * pulse)
                draw.rectangle([(0, y), (1920, y + 4)], fill=(r, g, b, 255))

            draw.rectangle([160, 110, 1760, 113], fill=(220, 38, 38, 200))
            draw.rectangle([160, 960, 1760, 963], fill=(220, 38, 38, 200))

            # Header
            title_progress = min(1.0, t / 0.8)
            title_y = 160 + int((1.0 - math.sin(title_progress * math.pi / 2)) * -50)
            title_text = "SURVIVAL MISSION COMPLETE!"
            t_box = draw.textbbox((0, 0), title_text, font=font_header)
            tw = t_box[2] - t_box[0]
            draw.text(((1920 - tw) // 2, title_y), title_text, fill=(255, 255, 255, 255), font=font_header)

            sub_text = f"🛡️ {series_title} • JOIN THE BASE"
            s_box = draw.textbbox((0, 0), sub_text, font=font_sub)
            sw = s_box[2] - s_box[0]
            draw.text(((1920 - sw) // 2, title_y + 70), sub_text, fill=(220, 38, 38, 240), font=font_sub)

            # --- TIER 1: Upper Wings (Like & Share) centered symmetrically around 960 ---
            # LIKE on left: [460, 380, 840, 480] (width 380)
            # SHARE on right: [1080, 380, 1460, 480] (width 380)
            # Center gap: 240px; Margin left: 460px; Margin right: 460px (Perfect Symmetry!)

            like_active = t >= 1.8
            like_scale = 1.0 + (0.16 * math.sin((t - 1.8) * 12) if 1.8 <= t <= 2.4 else 0.0)
            like_bg = (6, 182, 212, 255) if like_active else (30, 41, 59, 230)
            like_border = (34, 211, 238, 255) if like_active else (71, 85, 105, 200)
            self._draw_button(
                draw=draw,
                box=(460, 380, 840, 480),
                bg_color=like_bg,
                border_color=like_border,
                text="👍 LIKED!" if like_active else "👍 LIKE EPISODE",
                font=font_btn,
                scale=like_scale,
            )

            share_active = t >= 2.8
            share_scale = 1.0 + (0.16 * math.sin((t - 2.8) * 12) if 2.8 <= t <= 3.4 else 0.0)
            share_bg = (16, 185, 129, 255) if share_active else (30, 41, 59, 230)
            share_border = (52, 211, 153, 255) if share_active else (71, 85, 105, 200)
            self._draw_button(
                draw=draw,
                box=(1080, 380, 1460, 480),
                bg_color=share_bg,
                border_color=share_border,
                text="🚀 SHARED!" if share_active else "↗ SHARE WITH CLAN",
                font=font_btn,
                scale=share_scale,
            )

            # --- TIER 2: GIANT HERO SUBSCRIBE & BELL BAR (Y: 540 - 670) ---
            # Box: [540, 540, 1380, 670] (width 840, height 130, centered exactly at X=960!)
            sub_active = t >= 4.2
            sub_scale = 1.0 + (0.18 * math.sin((t - 4.2) * 12) if 4.2 <= t <= 4.8 else 0.0)
            hero_box = [540, 540, 1380, 670]
            hcx, hcy = (hero_box[0] + hero_box[2]) / 2, (hero_box[1] + hero_box[3]) / 2
            hw, hh = (hero_box[2] - hero_box[0]) * sub_scale, (hero_box[3] - hero_box[1]) * sub_scale
            h_box_scaled = [hcx - hw / 2, hcy - hh / 2, hcx + hw / 2, hcy + hh / 2]

            sub_bg = (15, 23, 42, 255) if sub_active else (220, 38, 38, 255)
            sub_border = (34, 197, 94, 255) if sub_active else (239, 68, 68, 255)
            draw.rounded_rectangle([h_box_scaled[0] - 4, h_box_scaled[1] - 4, h_box_scaled[2] + 4, h_box_scaled[3] + 4], radius=24, fill=sub_border)
            draw.rounded_rectangle(h_box_scaled, radius=24, fill=sub_bg)

            # Hero Subscribe Text
            hero_text = "✓ SUBSCRIBED TO CHANNEL" if sub_active else "SUBSCRIBE FOR NEXT RAID"
            ht_box = draw.textbbox((0, 0), hero_text, font=font_hero)
            ht_w = ht_box[2] - ht_box[0]
            ht_h = ht_box[3] - ht_box[1]
            draw.text((h_box_scaled[0] + 60, hcy - ht_h / 2 - 2), hero_text, fill=(255, 255, 255, 255), font=font_hero)

            # Divider & Dedicated Bell Sanctuary (width 160px on right wing)
            h_divider_x = h_box_scaled[0] + hw - 170
            draw.line([(h_divider_x, h_box_scaled[1] + 20), (h_divider_x, h_box_scaled[3] - 20)], fill=(100, 116, 139, 160), width=3)

            bell_ringing = t >= 5.5
            bell_angle = math.sin((t - 5.5) * 26) * 18.0 if bell_ringing else 0.0
            bell_center = (int(h_divider_x + 85), int(hcy))
            self._draw_bell(draw=draw, center=bell_center, angle_deg=bell_angle, ringing=bell_ringing, size=38)

            if bell_ringing:
                b_note = "🔔 ALL ON"
                bn_box = draw.textbbox((0, 0), b_note, font=font_small)
                bn_w = bn_box[2] - bn_box[0]
                draw.text((bell_center[0] - bn_w // 2, int(hcy + 82)), b_note, fill=(251, 191, 36, 255), font=font_small)

            # Cursor Trajectory
            cursor_pos = None
            if 1.2 <= t < 2.0:
                p = (t - 1.2) / 0.8
                cursor_pos = (int(500 + p * 150), int(520 - math.sin(p * math.pi) * 80))
            elif 2.2 <= t < 3.0:
                p = (t - 2.2) / 0.8
                cursor_pos = (int(1120 + p * 150), int(520 - math.sin(p * math.pi) * 80))
            elif 3.6 <= t < 4.4:
                p = (t - 3.6) / 0.8
                cursor_pos = (int(620 + p * 200), int(720 - math.sin(p * math.pi) * 80))
            elif 5.0 <= t < 5.8:
                p = (t - 5.0) / 0.8
                cursor_pos = (int(h_divider_x + 30 + p * 55), int(710 - math.sin(p * math.pi) * 70))

            if cursor_pos:
                self._draw_cursor(draw, cursor_pos)

            # Bottom message
            bottom_msg = "NEW SURVIVAL EPISODES UPLOADED REGULARLY • LEAVE YOUR BASE DESIGN TIPS BELOW!"
            b_box = draw.textbbox((0, 0), bottom_msg, font=font_sub)
            bw = b_box[2] - b_box[0]
            draw.text(((1920 - bw) // 2, 870), bottom_msg, fill=(203, 213, 225, 230), font=font_sub)

            # Fade to black (last 1.0s)
            if t >= duration - 1.0:
                fade_alpha = int(((t - (duration - 1.0)) / 1.0) * 255)
                overlay = Image.new("RGBA", (1920, 1080), (0, 0, 0, fade_alpha))
                bg.paste(overlay, (0, 0), overlay)

            frame_path = temp_dir / f"frame_{f:04d}.jpg"
            bg.convert("RGB").save(str(frame_path), format="JPEG", quality=92)

        return total_frames

    # -------------------------------------------------------------------------
    # STYLE 3: Cinematic Slate with YouTube End-Card Alignment (10.0s)
    # Designed specifically for YouTube 10s End Screen Cards (Next video + Playlist)
    # -------------------------------------------------------------------------
    def render_frames_cinematic_slate(
        self,
        temp_dir: Path,
        duration: float = 10.0,
        fps: int = 30,
        series_title: str = "LAST DAY ON EARTH: SURVIVAL",
    ) -> int:
        """Renders 10.0s 'Cinematic Slate' style: YouTube card zones + animated CTA footer."""
        temp_dir.mkdir(parents=True, exist_ok=True)
        total_frames = int(duration * fps)

        font_header = self._get_font(48, bold=True)
        font_sub = self._get_font(24, bold=False)
        font_card = self._get_font(28, bold=True)
        font_btn = self._get_font(28, bold=True)
        font_small = self._get_font(20, bold=True)

        for f in range(total_frames):
            t = f / fps

            bg = Image.new("RGBA", (1920, 1080), (10, 12, 16, 255))
            draw = ImageDraw.Draw(bg)

            # Gradient background
            for y in range(0, 1080, 4):
                factor = y / 1080.0
                r = int(14 + 10 * factor)
                g = int(16 + 8 * factor)
                b = int(22 + 12 * factor)
                draw.rectangle([(0, y), (1920, y + 4)], fill=(r, g, b, 255))

            # Header Banner
            title_text = f"THANKS FOR WATCHING • {series_title.upper()}"
            t_box = draw.textbbox((0, 0), title_text, font=font_header)
            tw = t_box[2] - t_box[0]
            draw.text(((1920 - tw) // 2, 80), title_text, fill=(240, 240, 240, 255), font=font_header)

            sub_text = "WATCH NEXT SURVIVAL RAID BELOW OR SELECT THE FULL PLAYLIST"
            s_box = draw.textbbox((0, 0), sub_text, font=font_sub)
            sw = s_box[2] - s_box[0]
            draw.text(((1920 - sw) // 2, 145), sub_text, fill=(220, 38, 38, 255), font=font_sub)

            # Decorative border
            draw.rectangle([140, 195, 1780, 198], fill=(220, 38, 38, 180))

            # --- YOUTUBE END-SCREEN CARDS ZONE (Y: 240 - 580) ---
            # Card 1: Next Episode [180, 240, 840, 580] (width 660, height 340, 16:9 ratio)
            draw.rounded_rectangle([180, 240, 840, 580], radius=16, fill=(18, 22, 28, 200), outline=(220, 38, 38, 220), width=3)
            draw.text((210, 270), "🎬 NEXT SURVIVAL EPISODE", fill=(255, 255, 255, 255), font=font_card)
            draw.text((210, 315), "Click here to continue the survival series", fill=(148, 163, 184, 255), font=font_sub)

            # Card 2: Full Playlist [1080, 240, 1740, 580] (width 660, height 340, 16:9 ratio)
            draw.rounded_rectangle([1080, 240, 1740, 580], radius=16, fill=(18, 22, 28, 200), outline=(220, 38, 38, 220), width=3)
            draw.text((1110, 270), "📺 FULL SERIES PLAYLIST", fill=(255, 255, 255, 255), font=font_card)
            draw.text((1110, 315), "Watch all episodes from Day 1 in order", fill=(148, 163, 184, 255), font=font_sub)

            # Decorative border between cards and CTA row
            draw.rectangle([140, 630, 1780, 633], fill=(220, 38, 38, 180))

            # --- LOWER CTA ROW (Y: 670 - 770) ---
            # 1. LIKE: [220, 670, 560, 770] (width 340)
            # 2. SHARE: [610, 670, 950, 770] (width 340)
            # 3. SUBSCRIBE + BELL: [1000, 670, 1700, 770] (width 700 - spacious unified container)

            like_active = t >= 2.0
            like_scale = 1.0 + (0.16 * math.sin((t - 2.0) * 12) if 2.0 <= t <= 2.6 else 0.0)
            self._draw_button(
                draw=draw,
                box=(220, 670, 560, 770),
                bg_color=(6, 182, 212, 255) if like_active else (30, 41, 59, 230),
                border_color=(34, 211, 238, 255) if like_active else (71, 85, 105, 200),
                text="👍 LIKED!" if like_active else "👍 LIKE",
                font=font_btn,
                scale=like_scale,
            )

            share_active = t >= 3.4
            share_scale = 1.0 + (0.16 * math.sin((t - 3.4) * 12) if 3.4 <= t <= 4.0 else 0.0)
            self._draw_button(
                draw=draw,
                box=(610, 670, 950, 770),
                bg_color=(16, 185, 129, 255) if share_active else (30, 41, 59, 230),
                border_color=(52, 211, 153, 255) if share_active else (71, 85, 105, 200),
                text="🚀 SHARED!" if share_active else "↗ SHARE",
                font=font_btn,
                scale=share_scale,
            )

            # Subscribe + Bell Container
            sub_active = t >= 5.0
            sub_scale = 1.0 + (0.18 * math.sin((t - 5.0) * 12) if 5.0 <= t <= 5.6 else 0.0)
            sp_box = [1000, 670, 1700, 770]
            sp_cx, sp_cy = (sp_box[0] + sp_box[2]) / 2, (sp_box[1] + sp_box[3]) / 2
            sp_w, sp_h = (sp_box[2] - sp_box[0]) * sub_scale, (sp_box[3] - sp_box[1]) * sub_scale
            sp_scaled = [sp_cx - sp_w / 2, sp_cy - sp_h / 2, sp_cx + sp_w / 2, sp_cy + sp_h / 2]

            sub_bg = (15, 23, 42, 255) if sub_active else (220, 38, 38, 255)
            sub_border = (34, 197, 94, 255) if sub_active else (239, 68, 68, 255)
            draw.rounded_rectangle([sp_scaled[0] - 3, sp_scaled[1] - 3, sp_scaled[2] + 3, sp_scaled[3] + 3], radius=18, fill=sub_border)
            draw.rounded_rectangle(sp_scaled, radius=18, fill=sub_bg)

            sub_label = "✓ SUBSCRIBED TO CHANNEL" if sub_active else "SUBSCRIBE FOR NEXT RAID"
            sbt_box = draw.textbbox((0, 0), sub_label, font=font_btn)
            sbt_w = sbt_box[2] - sbt_box[0]
            sbt_h = sbt_box[3] - sbt_box[1]
            draw.text((sp_scaled[0] + 50, sp_cy - sbt_h / 2 - 2), sub_label, fill=(255, 255, 255, 255), font=font_btn)

            # Divider & Bell
            divider_x = sp_scaled[0] + sp_w - 160
            draw.line([(divider_x, sp_scaled[1] + 16), (divider_x, sp_scaled[3] - 16)], fill=(100, 116, 139, 160), width=2)

            bell_ringing = t >= 6.5
            bell_angle = math.sin((t - 6.5) * 26) * 16.0 if bell_ringing else 0.0
            bell_center = (int(divider_x + 80), int(sp_cy))
            self._draw_bell(draw=draw, center=bell_center, angle_deg=bell_angle, ringing=bell_ringing, size=32)

            if bell_ringing:
                b_note = "🔔 ALL ON"
                bn_box = draw.textbbox((0, 0), b_note, font=font_small)
                bn_w = bn_box[2] - bn_box[0]
                draw.text((bell_center[0] - bn_w // 2, int(sp_cy + 58)), b_note, fill=(251, 191, 36, 255), font=font_small)

            # Cursor Trajectory
            cursor_pos = None
            if 1.4 <= t < 2.2:
                p = (t - 1.4) / 0.8
                cursor_pos = (int(260 + p * 130), int(800 - math.sin(p * math.pi) * 80))
            elif 2.8 <= t < 3.6:
                p = (t - 2.8) / 0.8
                cursor_pos = (int(650 + p * 130), int(800 - math.sin(p * math.pi) * 80))
            elif 4.4 <= t < 5.2:
                p = (t - 4.4) / 0.8
                cursor_pos = (int(1050 + p * 170), int(800 - math.sin(p * math.pi) * 80))
            elif 5.9 <= t < 6.7:
                p = (t - 5.9) / 0.8
                cursor_pos = (int(divider_x + 25 + p * 55), int(790 - math.sin(p * math.pi) * 70))

            if cursor_pos:
                self._draw_cursor(draw, cursor_pos)

            # Bottom note
            bottom_msg = "DROP A COMMENT WITH YOUR BASE DESIGN • NEW EPISODES UPLOADED REGULARLY"
            b_box = draw.textbbox((0, 0), bottom_msg, font=font_sub)
            bw = b_box[2] - b_box[0]
            draw.text(((1920 - bw) // 2, 890), bottom_msg, fill=(148, 163, 184, 230), font=font_sub)

            # Fade to black (last 1.2s)
            if t >= duration - 1.2:
                fade_alpha = int(((t - (duration - 1.2)) / 1.2) * 255)
                overlay = Image.new("RGBA", (1920, 1080), (0, 0, 0, fade_alpha))
                bg.paste(overlay, (0, 0), overlay)

            frame_path = temp_dir / f"frame_{f:04d}.jpg"
            bg.convert("RGB").save(str(frame_path), format="JPEG", quality=92)

        return total_frames

    # -------------------------------------------------------------------------
    # Render Orchestrator
    # -------------------------------------------------------------------------
    def render_outro_clip(
        self,
        output_mp4_path: Optional[Path] = None,
        duration: float = 7.5,
        fps: int = 30,
        style: str = "cyber_row",  # "cyber_row", "two_tier", "cinematic_slate"
        audio_track: Optional[Path] = None,
        series_title: str = "LAST DAY ON EARTH: SURVIVAL",
        force_recreate: bool = False,
    ) -> Path:
        """Renders standalone animated outro MP4 video using the selected style."""
        target_path = output_mp4_path or (self.assets_dir / f"outro_{style}_{int(duration)}s.mp4")

        # Reuse cached animation if exists and valid
        if target_path.exists() and target_path.stat().st_size > 50000 and not force_recreate:
            logger.info(f"Using existing cached outro tail animation: {target_path}")
            return target_path

        temp_frames_dir = self.assets_dir / f"temp_frames_{style}"
        logger.info(f"Rendering animated outro tail frames (style={style}, {duration}s @ {fps}fps)...")

        try:
            if style == "two_tier":
                total_frames = self.render_frames_two_tier(
                    temp_dir=temp_frames_dir,
                    duration=duration,
                    fps=fps,
                    series_title=series_title,
                )
            elif style == "cinematic_slate":
                total_frames = self.render_frames_cinematic_slate(
                    temp_dir=temp_frames_dir,
                    duration=duration,
                    fps=fps,
                    series_title=series_title,
                )
            else:  # default "cyber_row"
                total_frames = self.render_frames_cyber_row(
                    temp_dir=temp_frames_dir,
                    duration=duration,
                    fps=fps,
                    series_title=series_title,
                )

            # Audio selection (upbeat punchy audio)
            selected_audio = audio_track
            if not selected_audio or not Path(selected_audio).exists():
                for candidate in ["electro_cabello.mp3", "groove_grove.mp3", "decisions.mp3"]:
                    cand_path = self.audio_library_dir / candidate
                    if cand_path.exists():
                        selected_audio = cand_path
                        break

            fadeout_len = 1.5 if duration >= 8.0 else 1.0

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
                    "-filter_complex", f"[1:a]afade=t=in:st=0:d=0.3,afade=t=out:st={duration - fadeout_len}:d={fadeout_len}[aout]",
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
            if temp_frames_dir.exists():
                shutil.rmtree(temp_frames_dir, ignore_errors=True)
