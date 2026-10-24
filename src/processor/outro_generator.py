"""Animated Funky 'Like, Share & Subscribe' Outro Tail Generator (7-10s).

Features expressive creator fonts (Luckiest Guy, Bangers, Russo One), an oversized
standalone bell icon with exaggerated cartoon wobble, comedic survival hooks,
and synchronized sound effect chimes.
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
    """Generates broadcast-quality animated Like/Share/Subscribe outro tail clips with comic creator aesthetics."""

    def __init__(
        self,
        assets_dir: Path = Path("assets/animations"),
        audio_library_dir: Path = Path("config/audio"),
        fonts_dir: Path = Path("config/fonts"),
    ) -> None:
        self.assets_dir = assets_dir
        self.assets_dir.mkdir(parents=True, exist_ok=True)
        self.audio_library_dir = audio_library_dir
        self.fonts_dir = fonts_dir

    def _get_font(self, size: int, style: str = "luckiest") -> ImageFont.ImageFont:
        """Resolves expressive typography: Luckiest Guy, Bangers, or Russo One."""
        font_files = {
            "luckiest": self.fonts_dir / "LuckiestGuy.ttf",
            "bangers": self.fonts_dir / "Bangers.ttf",
            "russo": self.fonts_dir / "RussoOne.ttf",
            "impact": self.fonts_dir / "impact.ttf",
        }
        target_path = font_files.get(style, font_files["luckiest"])
        if target_path.exists():
            try:
                return ImageFont.truetype(str(target_path), size)
            except Exception:
                pass

        # Fallback to system fonts
        for name in ["impact.ttf", "arialbd.ttf", "segoeuib.ttf", "arial.ttf"]:
            try:
                return ImageFont.truetype(name, size)
            except Exception:
                continue
        return ImageFont.load_default()

    def _draw_comic_text(
        self,
        draw: ImageDraw.ImageDraw,
        pos: Tuple[int, int],
        text: str,
        font: ImageFont.ImageFont,
        fill_color: Tuple[int, int, int, int] = (255, 255, 255, 255),
        stroke_color: Tuple[int, int, int, int] = (0, 0, 0, 255),
        stroke_width: int = 4,
        shadow_offset: Tuple[int, int] = (4, 4),
    ) -> Tuple[int, int]:
        """Renders punchy comic-style typography with heavy outline and 3D shadow."""
        x, y = pos
        sx, sy = shadow_offset

        # 3D shadow
        if sx or sy:
            draw.text((x + sx, y + sy), text, font=font, fill=(15, 23, 42, 220), stroke_width=stroke_width, stroke_fill=(0, 0, 0, 220))

        # Outline & main text
        draw.text((x, y), text, font=font, fill=fill_color, stroke_width=stroke_width, stroke_fill=stroke_color)

        t_box = draw.textbbox((0, 0), text, font=font, stroke_width=stroke_width)
        return t_box[2] - t_box[0], t_box[3] - t_box[1]

    def _draw_button(
        self,
        draw: ImageDraw.ImageDraw,
        box: Tuple[int, int, int, int],
        bg_color: Tuple[int, int, int, int],
        border_color: Tuple[int, int, int, int],
        text: str,
        font: ImageFont.ImageFont,
        text_color: Tuple[int, int, int, int] = (255, 255, 255, 255),
        radius: int = 24,
        scale: float = 1.0,
        badge_text: Optional[str] = None,
        badge_font: Optional[ImageFont.ImageFont] = None,
    ) -> None:
        """Draws a bold, punchy cartoon button with squash/stretch scaling and optional comic badge."""
        x1, y1, x2, y2 = box
        cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
        w, h = (x2 - x1) * scale, (y2 - y1) * scale
        scaled_box = [cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2]

        # Heavy 3D Drop Shadow
        draw.rounded_rectangle(
            [scaled_box[0] + 4, scaled_box[1] + 6, scaled_box[2] + 4, scaled_box[3] + 6],
            radius=int(radius * scale),
            fill=(0, 0, 0, 180),
        )

        # Thick Comic Border
        draw.rounded_rectangle(
            [scaled_box[0] - 4, scaled_box[1] - 4, scaled_box[2] + 4, scaled_box[3] + 4],
            radius=int(radius * scale),
            fill=(0, 0, 0, 255),
        )

        # Inner Accent Border
        draw.rounded_rectangle(
            [scaled_box[0] - 1, scaled_box[1] - 1, scaled_box[2] + 1, scaled_box[3] + 1],
            radius=int(radius * scale),
            fill=border_color,
        )

        # Button Face
        draw.rounded_rectangle(
            scaled_box,
            radius=int(radius * scale),
            fill=bg_color,
        )

        # Center Text with Outline
        t_box = draw.textbbox((0, 0), text, font=font, stroke_width=3)
        tw = t_box[2] - t_box[0]
        th = t_box[3] - t_box[1]
        draw.text(
            (cx - tw / 2, cy - th / 2 - 3),
            text,
            fill=text_color,
            font=font,
            stroke_width=3,
            stroke_fill=(0, 0, 0, 255),
        )

        # Floating comic pill badge on top corner
        if badge_text and badge_font:
            bw_box = draw.textbbox((0, 0), badge_text, font=badge_font)
            bw = bw_box[2] - bw_box[0]
            bh = bw_box[3] - bw_box[1]
            bx = scaled_box[2] - bw - 15
            by = scaled_box[1] - 16
            draw.rounded_rectangle([bx - 8, by - 4, bx + bw + 8, by + bh + 4], radius=8, fill=(245, 158, 11, 255), outline=(0, 0, 0, 255), width=2)
            draw.text((bx, by), badge_text, fill=(0, 0, 0, 255), font=badge_font)

    def _draw_standalone_bell(
        self,
        draw: ImageDraw.ImageDraw,
        center: Tuple[int, int],
        angle_deg: float,
        ringing: bool,
        scale: float = 1.0,
        size: int = 56,  # Significantly larger standalone bell
    ) -> None:
        """Draws an oversized, highly animated standalone golden bell with sound ripples."""
        cx, cy = center
        rad = math.radians(angle_deg)
        cos_a = math.cos(rad)
        sin_a = math.sin(rad)
        eff_size = size * scale

        def rotate_pt(px: float, py: float) -> Tuple[float, float]:
            dx, dy = px - cx, py - cy
            return (cx + dx * cos_a - dy * sin_a, cy + dx * sin_a + dy * cos_a)

        # Giant Floating Pedestal / Glow Aura
        glow_r = int(eff_size * 1.5)
        glow_color = (251, 191, 36, 60) if ringing else (30, 41, 59, 100)
        draw.ellipse([cx - glow_r, cy - glow_r, cx + glow_r, cy + glow_r], fill=glow_color)

        # Bell Clapper Dome
        top = rotate_pt(cx, cy - eff_size * 0.95)
        bottom_left = rotate_pt(cx - eff_size * 0.85, cy + eff_size * 0.5)
        bottom_right = rotate_pt(cx + eff_size * 0.85, cy + eff_size * 0.5)

        # Bell 3D shadow
        draw.polygon(
            [(p[0] + 4, p[1] + 4) for p in [top, bottom_left, bottom_right]],
            fill=(0, 0, 0, 160),
        )

        # Bell Body (Vibrant Gold)
        bell_gold = (251, 191, 36, 255) if not ringing else (253, 224, 71, 255)
        draw.polygon([top, bottom_left, bottom_right], fill=bell_gold, outline=(0, 0, 0, 255))

        # Bottom Rim
        rim_y = cy + eff_size * 0.5
        draw.ellipse(
            [cx - eff_size * 0.85, rim_y - eff_size * 0.15, cx + eff_size * 0.85, rim_y + eff_size * 0.15],
            fill=(245, 158, 11, 255),
            outline=(0, 0, 0, 255),
            width=2,
        )

        # Clapper Ball
        clapper_pt = rotate_pt(cx, cy + eff_size * 0.65)
        cr = eff_size * 0.22
        draw.ellipse([clapper_pt[0] - cr, clapper_pt[1] - cr, clapper_pt[0] + cr, clapper_pt[1] + cr], fill=(180, 83, 9, 255), outline=(0, 0, 0, 255), width=2)

        # Top Loop Ring
        loop_pt = rotate_pt(cx, cy - eff_size * 1.1)
        lr = eff_size * 0.18
        draw.ellipse([loop_pt[0] - lr, loop_pt[1] - lr, loop_pt[0] + lr, loop_pt[1] + lr], outline=(0, 0, 0, 255), width=3)

        # Exaggerated Radiating Comic Soundwave Arcs if ringing
        if ringing:
            for ring_r in [eff_size + 18, eff_size + 36, eff_size + 54]:
                draw.arc(
                    [cx - ring_r, cy - ring_r, cx + ring_r, cy + ring_r],
                    start=-60,
                    end=60,
                    fill=(251, 191, 36, 230),
                    width=4,
                )
                draw.arc(
                    [cx - ring_r, cy - ring_r, cx + ring_r, cy + ring_r],
                    start=120,
                    end=240,
                    fill=(251, 191, 36, 230),
                    width=4,
                )

    def _draw_cartoon_hand(self, draw: ImageDraw.ImageDraw, pos: Tuple[int, int], clicking: bool = False) -> None:
        """Draws a funny white cartoon glove pointing/clicking."""
        cx, cy = pos
        scale = 0.9 if clicking else 1.0

        # Glove Body Points
        points = [
            (cx, cy),                           # Pointer tip
            (cx + 24 * scale, cy + 24 * scale), # Index base
            (cx + 12 * scale, cy + 24 * scale), # Inward notch
            (cx + 22 * scale, cy + 44 * scale), # Palm right
            (cx - 2 * scale, cy + 48 * scale),  # Wrist right
            (cx - 16 * scale, cy + 44 * scale), # Wrist left
            (cx - 14 * scale, cy + 28 * scale), # Thumb base
            (cx - 6 * scale, cy + 22 * scale),  # Thumb tip
            (cx - 2 * scale, cy + 18 * scale),  # Index inner
        ]

        # 3D shadow
        shadow_pts = [(p[0] + 4, p[1] + 4) for p in points]
        draw.polygon(shadow_pts, fill=(0, 0, 0, 160))

        # Main Glove Fill
        draw.polygon(points, fill=(255, 255, 255, 255), outline=(0, 0, 0, 255))
        # Comic creases
        draw.line([(cx + 4 * scale, cy + 32 * scale), (cx + 14 * scale, cy + 34 * scale)], fill=(203, 213, 225, 255), width=2)

    # -------------------------------------------------------------------------
    # STYLE 1: Cartoon Comedy Show (8.0s)
    # Features Luckiest Guy font, funny survival hooks, and giant elevated bell
    # -------------------------------------------------------------------------
    def render_frames_cartoon_comedy(
        self,
        temp_dir: Path,
        duration: float = 8.0,
        fps: int = 30,
        series_title: str = "LAST DAY ON EARTH: SURVIVAL",
    ) -> int:
        """Renders 8.0s Comedy Outro with big separated bell and funny gaming copy."""
        temp_dir.mkdir(parents=True, exist_ok=True)
        total_frames = int(duration * fps)

        font_header = self._get_font(56, style="luckiest")
        font_sub = self._get_font(28, style="bangers")
        font_btn = self._get_font(34, style="luckiest")
        font_btn_lg = self._get_font(38, style="luckiest")
        font_badge = self._get_font(20, style="russo")
        font_comic = self._get_font(30, style="bangers")

        # Layout Geometry:
        # Left Side (Y=420): LIKE [180, 420, 600, 530] (width 420)
        # Left Side (Y=570): SHARE [180, 570, 600, 680] (width 420)
        # Center-Right: GIANT SUBSCRIBE [670, 570, 1370, 680] (width 700)
        # UPPER-RIGHT SEPARATE STAGE: STANDALONE GIANT BELL [X=1560, Y=510] (Completely isolated!)

        for f in range(total_frames):
            t = f / fps

            bg = Image.new("RGBA", (1920, 1080), (14, 18, 26, 255))
            draw = ImageDraw.Draw(bg)

            # Gradient background with pulsing survival grid
            pulse = math.sin(t * 3.5) * 0.15 + 0.85
            for y in range(0, 1080, 4):
                factor = y / 1080.0
                r = int(14 + 18 * factor * pulse)
                g = int(20 + 14 * factor)
                b = int(32 + 22 * factor * pulse)
                draw.rectangle([(0, y), (1920, y + 4)], fill=(r, g, b, 255))

            # Comic Accent Lines
            draw.rectangle([120, 110, 1800, 116], fill=(239, 68, 68, 255))
            draw.rectangle([120, 970, 1800, 976], fill=(239, 68, 68, 255))

            # Header Drop-in
            title_progress = min(1.0, t / 0.7)
            title_y = 150 + int((1.0 - math.sin(title_progress * math.pi / 2)) * -60)

            # Main Humorous Header
            h_text = "WAIT! BEFORE YOU LEAVE..."
            self._draw_comic_text(
                draw=draw,
                pos=((1920 - draw.textbbox((0, 0), h_text, font=font_header)[2]) // 2, title_y),
                text=h_text,
                font=font_header,
                fill_color=(255, 230, 0, 255),
            )

            sub_text = "DON'T LEAVE YOUR BASE UNPROTECTED • UPGRADE YOUR FEED!"
            self._draw_comic_text(
                draw=draw,
                pos=((1920 - draw.textbbox((0, 0), sub_text, font=font_sub)[2]) // 2, title_y + 80),
                text=sub_text,
                font=font_sub,
                fill_color=(255, 255, 255, 240),
                stroke_width=2,
            )

            # --- 1. LIKE BUTTON (Squash & Pop) ---
            like_active = t >= 1.6
            like_squash = 1.0 + (0.18 * math.sin((t - 1.6) * 14) if 1.6 <= t <= 2.2 else 0.0)
            self._draw_button(
                draw=draw,
                box=(180, 390, 680, 510),
                bg_color=(6, 182, 212, 255) if like_active else (30, 41, 59, 240),
                border_color=(34, 211, 238, 255) if like_active else (100, 116, 139, 220),
                text="LIKED! (+100 IQ)" if like_active else "SMASH LIKE!",
                font=font_btn,
                scale=like_squash,
                badge_text="FREE BUFF" if not like_active else "BUFF ACTIVATED",
                badge_font=font_badge,
            )

            # --- 2. SHARE BUTTON (Squash & Pop) ---
            share_active = t >= 2.6
            share_squash = 1.0 + (0.18 * math.sin((t - 2.6) * 14) if 2.6 <= t <= 3.2 else 0.0)
            self._draw_button(
                draw=draw,
                box=(740, 390, 1240, 510),
                bg_color=(16, 185, 129, 255) if share_active else (30, 41, 59, 240),
                border_color=(52, 211, 153, 255) if share_active else (100, 116, 139, 220),
                text="SHARED TO CLAN!" if share_active else "SHARE TO CLAN",
                font=font_btn,
                scale=share_squash,
                badge_text="REINFORCE" if not share_active else "SENT!",
                badge_font=font_badge,
            )

            # --- 3. GIANT SUBSCRIBE BUTTON ---
            sub_active = t >= 3.8
            sub_squash = 1.0 + (0.22 * math.sin((t - 3.8) * 12) if 3.8 <= t <= 4.5 else 0.0)
            sub_box = (180, 560, 1240, 710)
            self._draw_button(
                draw=draw,
                box=sub_box,
                bg_color=(15, 23, 42, 255) if sub_active else (220, 38, 38, 255),
                border_color=(34, 197, 94, 255) if sub_active else (239, 68, 68, 255),
                text="BASE DEFENDED!" if sub_active else "SUBSCRIBE NOW!",
                font=font_btn_lg,
                scale=sub_squash,
                badge_text="ZOMBIE-PROOF" if not sub_active else "100% IMMUNITY",
                badge_font=font_badge,
            )

            # --- 4. STANDALONE OVERSIZED BELL TOWER (X: 1540, Y: 550) ---
            # Completely separated from subscribe button with dedicated stage
            bell_ringing = t >= 5.0
            bell_angle = math.sin((t - 5.0) * 28) * 25.0 if bell_ringing else 0.0
            bell_center = (1540, 550)

            # Circular Spotlight Pedestal
            draw.ellipse([bell_center[0] - 120, bell_center[1] - 120, bell_center[0] + 120, bell_center[1] + 120], fill=(24, 30, 42, 240), outline=(251, 191, 36, 230), width=4)
            self._draw_standalone_bell(draw=draw, center=bell_center, angle_deg=bell_angle, ringing=bell_ringing, size=58)

            # Comic Callout above or below the bell
            if bell_ringing:
                callout_text = "DING DING DING!"
                self._draw_comic_text(
                    draw=draw,
                    pos=(bell_center[0] - 120, bell_center[1] + 95),
                    text=callout_text,
                    font=font_comic,
                    fill_color=(253, 224, 71, 255),
                    stroke_color=(0, 0, 0, 255),
                )
            else:
                self._draw_comic_text(
                    draw=draw,
                    pos=(bell_center[0] - 90, bell_center[1] + 95),
                    text="RING THE BELL!",
                    font=font_comic,
                    fill_color=(241, 245, 249, 220),
                    stroke_color=(0, 0, 0, 255),
                )

            # --- 5. Cartoon Hand Pointer Trajectory ---
            cursor_pos = None
            is_clicking = False
            if 1.1 <= t < 1.9:
                p = (t - 1.1) / 0.8
                cursor_pos = (int(300 + p * 130), int(510 - math.sin(p * math.pi) * 60))
                is_clicking = 1.5 <= t <= 1.8
            elif 2.1 <= t < 2.9:
                p = (t - 2.1) / 0.8
                cursor_pos = (int(430 + p * 560), int(450 - math.sin(p * math.pi) * 60))
                is_clicking = 2.5 <= t <= 2.8
            elif 3.1 <= t < 4.1:
                p = (t - 3.1) / 1.0
                cursor_pos = (int(990 - p * 280), int(450 + p * 185 - math.sin(p * math.pi) * 40))
                is_clicking = 3.7 <= t <= 4.0
            elif 4.4 <= t < 5.3:
                p = (t - 4.4) / 0.9
                cursor_pos = (int(710 + p * 830), int(635 - p * 85 - math.sin(p * math.pi) * 80))
                is_clicking = 4.9 <= t <= 5.2

            if cursor_pos:
                self._draw_cartoon_hand(draw, cursor_pos, clicking=is_clicking)

            # Bottom Comic Footer
            bottom_msg = "DROP A COMMENT BELOW WITH YOUR BASE LAYOUT • NEXT RAID DROPS SOON!"
            self._draw_comic_text(
                draw=draw,
                pos=((1920 - draw.textbbox((0, 0), bottom_msg, font=font_sub)[2]) // 2, 870),
                text=bottom_msg,
                font=font_sub,
                fill_color=(203, 213, 225, 230),
                stroke_width=2,
            )

            # Fade to black (last 0.8s)
            if t >= duration - 0.8:
                fade_alpha = int(((t - (duration - 0.8)) / 0.8) * 255)
                overlay = Image.new("RGBA", (1920, 1080), (0, 0, 0, fade_alpha))
                bg.paste(overlay, (0, 0), overlay)

            frame_path = temp_dir / f"frame_{f:04d}.jpg"
            bg.convert("RGB").save(str(frame_path), format="JPEG", quality=92)

        return total_frames

    # -------------------------------------------------------------------------
    # STYLE 2: MrBeast-Style High-Impact Hype Studio (9.5s)
    # Bangers / Russo One typography, massive buttons, giant bell pedestal
    # -------------------------------------------------------------------------
    def render_frames_hype_studio(
        self,
        temp_dir: Path,
        duration: float = 9.5,
        fps: int = 30,
        series_title: str = "LAST DAY ON EARTH: SURVIVAL",
    ) -> int:
        """Renders 9.5s MrBeast-Style Outro with giant elevated Bell Pedestal and intense pacing."""
        temp_dir.mkdir(parents=True, exist_ok=True)
        total_frames = int(duration * fps)

        font_header = self._get_font(62, style="bangers")
        font_sub = self._get_font(28, style="russo")
        font_btn = self._get_font(36, style="bangers")
        font_hero = self._get_font(44, style="bangers")
        font_badge = self._get_font(22, style="russo")
        font_comic = self._get_font(32, style="luckiest")

        for f in range(total_frames):
            t = f / fps

            bg = Image.new("RGBA", (1920, 1080), (10, 12, 16, 255))
            draw = ImageDraw.Draw(bg)

            # Dark red survival atmosphere
            pulse = math.sin(t * 3.0) * 0.16 + 0.84
            for y in range(0, 1080, 4):
                factor = y / 1080.0
                r = int(18 + 22 * factor * pulse)
                g = int(12 + 10 * factor)
                b = int(18 + 14 * factor)
                draw.rectangle([(0, y), (1920, y + 4)], fill=(r, g, b, 255))

            draw.rectangle([140, 110, 1780, 115], fill=(220, 38, 38, 230))
            draw.rectangle([140, 970, 1780, 975], fill=(220, 38, 38, 230))

            # Header
            title_progress = min(1.0, t / 0.8)
            title_y = 150 + int((1.0 - math.sin(title_progress * math.pi / 2)) * -50)
            h_text = "SURVIVAL MISSION COMPLETE!"
            self._draw_comic_text(
                draw=draw,
                pos=((1920 - draw.textbbox((0, 0), h_text, font=font_header)[2]) // 2, title_y),
                text=h_text,
                font=font_header,
                fill_color=(255, 255, 255, 255),
            )

            sub_text = "SUBSCRIBE IN THE NEXT 5 SECONDS TO BEAT BUNKER ALFA!"
            self._draw_comic_text(
                draw=draw,
                pos=((1920 - draw.textbbox((0, 0), sub_text, font=font_sub)[2]) // 2, title_y + 80),
                text=sub_text,
                font=font_sub,
                fill_color=(239, 68, 68, 255),
                stroke_width=2,
            )

            # --- UPPER TIER WINGS (LIKE & SHARE) centered around X=750 ---
            # LIKE [240, 380, 680, 490] (width 440)
            # SHARE [740, 380, 1180, 490] (width 440)
            like_active = t >= 1.8
            like_scale = 1.0 + (0.16 * math.sin((t - 1.8) * 12) if 1.8 <= t <= 2.5 else 0.0)
            self._draw_button(
                draw=draw,
                box=(240, 380, 680, 490),
                bg_color=(6, 182, 212, 255) if like_active else (30, 41, 59, 230),
                border_color=(34, 211, 238, 255) if like_active else (71, 85, 105, 200),
                text="LIKED! (+100 AURA)" if like_active else "SMASH LIKE!",
                font=font_btn,
                scale=like_scale,
                badge_text="+100 XP" if not like_active else "CLAIMED!",
                badge_font=font_badge,
            )

            share_active = t >= 3.0
            share_scale = 1.0 + (0.16 * math.sin((t - 3.0) * 12) if 3.0 <= t <= 3.7 else 0.0)
            self._draw_button(
                draw=draw,
                box=(740, 380, 1180, 490),
                bg_color=(16, 185, 129, 255) if share_active else (30, 41, 59, 230),
                border_color=(52, 211, 153, 255) if share_active else (71, 85, 105, 200),
                text="SHARED TO CLAN!" if share_active else "SHARE EPISODE",
                font=font_btn,
                scale=share_scale,
                badge_text="RAID TEAM" if not share_active else "DISPATCHED!",
                badge_font=font_badge,
            )

            # --- LOWER TIER: GIANT HERO SUBSCRIBE SLAM BAR ---
            # [240, 560, 1180, 710] (width 940, massive impact!)
            sub_active = t >= 4.5
            sub_scale = 1.0 + (0.22 * math.sin((t - 4.5) * 12) if 4.5 <= t <= 5.3 else 0.0)
            self._draw_button(
                draw=draw,
                box=(240, 560, 1180, 710),
                bg_color=(15, 23, 42, 255) if sub_active else (220, 38, 38, 255),
                border_color=(34, 197, 94, 255) if sub_active else (239, 68, 68, 255),
                text="BASE SAVED! SUBSCRIBED" if sub_active else "SUBSCRIBE OR ELSE!",
                font=font_hero,
                scale=sub_scale,
                badge_text="ALPHA RAIDER" if sub_active else "SURVIVAL RANK #1",
                badge_font=font_badge,
            )

            # --- DEDICATED ELEVATED BELL SANCTUARY (X: 1520, Y: 545) ---
            # Completely separated from subscribe on the right wing
            bell_ringing = t >= 6.2
            bell_angle = math.sin((t - 6.2) * 28) * 26.0 if bell_ringing else 0.0
            bell_center = (1520, 545)

            # Glowing circular pedestal
            draw.ellipse([bell_center[0] - 125, bell_center[1] - 125, bell_center[0] + 125, bell_center[1] + 125], fill=(22, 27, 34, 240), outline=(251, 191, 36, 240), width=4)
            self._draw_standalone_bell(draw=draw, center=bell_center, angle_deg=bell_angle, ringing=bell_ringing, size=60)

            # Speech bubble / callout
            if bell_ringing:
                self._draw_comic_text(
                    draw=draw,
                    pos=(bell_center[0] - 135, bell_center[1] + 105),
                    text="ALL NOTIFICATIONS ON!",
                    font=font_comic,
                    fill_color=(253, 224, 71, 255),
                )
            else:
                self._draw_comic_text(
                    draw=draw,
                    pos=(bell_center[0] - 85, bell_center[1] + 105),
                    text="RING THE BELL!",
                    font=font_comic,
                    fill_color=(255, 255, 255, 230),
                )

            # --- Cursor Movement ---
            cursor_pos = None
            is_clicking = False
            if 1.2 <= t < 2.0:
                p = (t - 1.2) / 0.8
                cursor_pos = (int(200 + p * 240), int(500 - math.sin(p * math.pi) * 80))
                is_clicking = 1.6 <= t <= 1.9
            elif 2.4 <= t < 3.2:
                p = (t - 2.4) / 0.8
                cursor_pos = (int(700 + p * 240), int(500 - math.sin(p * math.pi) * 80))
                is_clicking = 2.8 <= t <= 3.1
            elif 3.8 <= t < 4.8:
                p = (t - 3.8) / 1.0
                cursor_pos = (int(500 + p * 350), int(730 - math.sin(p * math.pi) * 90))
                is_clicking = 4.4 <= t <= 4.7
            elif 5.5 <= t < 6.5:
                p = (t - 5.5) / 1.0
                cursor_pos = (int(1350 + p * 160), int(680 - math.sin(p * math.pi) * 90))
                is_clicking = 6.1 <= t <= 6.4

            if cursor_pos:
                self._draw_cartoon_hand(draw, cursor_pos, clicking=is_clicking)

            # Footer
            bottom_msg = "NEW SURVIVAL RAIDS UPLOADED DAILY • LEAVE YOUR SURVIVAL TIPS IN THE COMMENTS!"
            self._draw_comic_text(
                draw=draw,
                pos=((1920 - draw.textbbox((0, 0), bottom_msg, font=font_sub)[2]) // 2, 885),
                text=bottom_msg,
                font=font_sub,
                fill_color=(203, 213, 225, 230),
                stroke_width=2,
            )

            # Fade to black (last 1.0s)
            if t >= duration - 1.0:
                fade_alpha = int(((t - (duration - 1.0)) / 1.0) * 255)
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
        duration: float = 8.0,
        fps: int = 30,
        style: str = "cartoon_comedy",  # "cartoon_comedy" (8.0s), "hype_studio" (9.5s)
        audio_track: Optional[Path] = None,
        series_title: str = "LAST DAY ON EARTH: SURVIVAL",
        force_recreate: bool = False,
    ) -> Path:
        """Renders standalone animated outro MP4 video with sound cues."""
        target_path = output_mp4_path or (self.assets_dir / f"outro_{style}_{duration}s.mp4")

        # Reuse cached animation if exists and valid
        if target_path.exists() and target_path.stat().st_size > 50000 and not force_recreate:
            logger.info(f"Using existing cached outro tail animation: {target_path}")
            return target_path

        temp_frames_dir = self.assets_dir / f"temp_frames_{style}"
        logger.info(f"Rendering animated outro tail frames (style={style}, {duration}s @ {fps}fps)...")

        try:
            if style == "hype_studio":
                total_frames = self.render_frames_hype_studio(
                    temp_dir=temp_frames_dir,
                    duration=duration,
                    fps=fps,
                    series_title=series_title,
                )
            else:  # default "cartoon_comedy"
                total_frames = self.render_frames_cartoon_comedy(
                    temp_dir=temp_frames_dir,
                    duration=duration,
                    fps=fps,
                    series_title=series_title,
                )

            # Select audio track
            selected_audio = audio_track
            if not selected_audio or not Path(selected_audio).exists():
                for candidate in ["electro_cabello.mp3", "groove_grove.mp3", "decisions.mp3"]:
                    cand_path = self.audio_library_dir / candidate
                    if cand_path.exists():
                        selected_audio = cand_path
                        break

            fadeout_len = 1.2

            # FFmpeg Command with background music + high-pitch bell chime chime SFX
            # Bell ding occurs at 5.0s (for cartoon_comedy) or 6.2s (for hype_studio)
            bell_time = 5.0 if style != "hype_studio" else 6.2

            filter_complex = (
                f"[1:a]afade=t=in:st=0:d=0.3,afade=t=out:st={duration - fadeout_len}:d={fadeout_len},volume=0.85[bg];"
                f"[2:a]adelay={int(bell_time * 1000)}|{int(bell_time * 1000)},volume=1.4[chime];"
                f"[bg][chime]amix=inputs=2:duration=first:dropout_transition=0[aout]"
            )

            cmd = [
                "ffmpeg",
                "-y",
                "-framerate", str(fps),
                "-i", str(temp_frames_dir / "frame_%04d.jpg"),
                "-i", str(selected_audio),
                "-f", "lavfi", "-i", "sine=frequency=1760:duration=0.8",  # High-pitch bell ding
                "-t", str(duration),
                "-filter_complex", filter_complex,
                "-map", "0:v",
                "-map", "[aout]",
                "-c:v", "libx264",
                "-preset", "faster",
                "-pix_fmt", "yuv420p",
                "-c:a", "aac",
                "-b:a", "192k",
                "-movflags", "+faststart",
                str(target_path),
            ]

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
