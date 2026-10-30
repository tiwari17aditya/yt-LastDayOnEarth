"""YouTube Shorts (9:16) auto-clipper and generator.

Extracts peak gameplay moments and renders optimized 1080x1920 vertical video
with blurred gameplay backdrop, centered high-def gameplay, and custom branding banners.
"""

import subprocess
import shutil
from pathlib import Path
from typing import Optional, List, Dict, Any
from PIL import Image, ImageDraw, ImageFont

from src.logging_config import get_logger
from src.exceptions import VideoProcessingError

logger = get_logger(component="ShortsGenerator")


class ShortsGenerator:
    """Generates high-engagement 9:16 vertical YouTube Shorts from 16:9 gameplay footage."""

    def __init__(self, output_dir: Path = Path("data/shorts")) -> None:
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def create_shorts_overlay(
        self,
        output_png_path: Path,
        top_title: str = "LAST DAY ON EARTH",
        subtitle: str = "SURVIVAL INTENSIFIES",
        footer_text: str = "EPISODE • WATCH FULL VIDEO",
        episode_number: Optional[int] = None,
    ) -> Path:
        """Creates a high-contrast 1080x1920 transparent PNG overlay with branding and callouts."""
        img = Image.new("RGBA", (1080, 1920), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        # Header Banner background (top 380px)
        # Gradient or semi-transparent dark banner
        for y in range(400):
            alpha = int(230 * (1.0 - (y / 400.0) ** 2))
            draw.line([(0, y), (1080, y)], fill=(12, 14, 18, alpha))

        # Footer Banner background (bottom 400px)
        for y in range(1520, 1920):
            dist = (y - 1520) / 400.0
            alpha = int(235 * dist)
            draw.line([(0, y), (1080, y)], fill=(12, 14, 18, alpha))

        # Accent border lines separating gameplay box (gameplay is at y=656 to 1264)
        border_y_top = 654
        border_y_bottom = 1266
        draw.rectangle([0, border_y_top - 2, 1080, border_y_top + 1], fill=(220, 38, 38, 255))
        draw.rectangle([0, border_y_bottom - 1, 1080, border_y_bottom + 2], fill=(220, 38, 38, 255))

        # Load fonts (fallback to default if system font not available)
        def _get_font(size: int):
            for name in ["arialbd.ttf", "impact.ttf", "segoeui.ttf", "arial.ttf"]:
                try:
                    return ImageFont.truetype(name, size)
                except Exception:
                    continue
            return ImageFont.load_default()

        font_brand = _get_font(52)
        font_sub = _get_font(38)
        font_badge = _get_font(44)
        font_footer = _get_font(40)

        # Render Header Brand Text
        brand_text = top_title.upper()
        bbox = draw.textbbox((0, 0), brand_text, font=font_brand)
        w = bbox[2] - bbox[0]
        # Text shadow
        draw.text(((1080 - w) // 2 + 2, 160 + 2), brand_text, fill=(0, 0, 0, 220), font=font_brand)
        draw.text(((1080 - w) // 2, 160), brand_text, fill=(255, 255, 255, 255), font=font_brand)

        # Render Subtitle / Hook Text
        sub_text = subtitle.upper()
        bbox_sub = draw.textbbox((0, 0), sub_text, font=font_sub)
        w_sub = bbox_sub[2] - bbox_sub[0]
        draw.text(((1080 - w_sub) // 2 + 2, 235 + 2), sub_text, fill=(0, 0, 0, 200), font=font_sub)
        draw.text(((1080 - w_sub) // 2, 235), sub_text, fill=(239, 68, 68, 255), font=font_sub)

        # Render Episode Badge if available
        if episode_number:
            badge_text = f"EPISODE #{episode_number}"
            bbox_b = draw.textbbox((0, 0), badge_text, font=font_badge)
            bw = bbox_b[2] - bbox_b[0] + 40
            bh = bbox_b[3] - bbox_b[1] + 20
            bx = (1080 - bw) // 2
            by = 310
            draw.rectangle([bx, by, bx + bw, by + bh], fill=(185, 28, 28, 230), outline=(255, 255, 255, 200), width=2)
            draw.text((bx + 20, by + 8), badge_text, fill=(255, 255, 255, 255), font=font_badge)

        # Render Footer Call-To-Action
        ft_text = footer_text.upper()
        bbox_ft = draw.textbbox((0, 0), ft_text, font=font_footer)
        w_ft = bbox_ft[2] - bbox_ft[0]
        btn_w = w_ft + 60
        btn_h = bbox_ft[3] - bbox_ft[1] + 30
        btn_x = (1080 - btn_w) // 2
        btn_y = 1680

        # CTA Button
        draw.rounded_rectangle([btn_x, btn_y, btn_x + btn_w, btn_y + btn_h], radius=15, fill=(220, 38, 38, 240), outline=(255, 255, 255, 230), width=3)
        draw.text((btn_x + 30, btn_y + 12), ft_text, fill=(255, 255, 255, 255), font=font_footer)

        # Bottom channel hint
        hint = "🔴 SUBSCRIBE FOR DAILY SURVIVAL"
        bbox_h = draw.textbbox((0, 0), hint, font=font_sub)
        wh = bbox_h[2] - bbox_h[0]
        draw.text(((1080 - wh) // 2, 1780), hint, fill=(209, 213, 219, 230), font=font_sub)

        output_png_path.parent.mkdir(parents=True, exist_ok=True)
        img.save(str(output_png_path), format="PNG")
        logger.info(f"Generated Shorts overlay image at {output_png_path}")
        return output_png_path

    def get_video_duration(self, video_path: Path) -> float:
        """Probes true video duration in seconds via ffprobe."""
        if not video_path.exists():
            return 35.0
        cmd = [
            "ffprobe",
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(video_path),
        ]
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return max(5.0, float(res.stdout.strip()))
        except Exception as e:
            logger.debug(f"Could not probe duration for {video_path}: {e}")
            return 35.0

    def auto_detect_highlight_start(self, events: List[Any], min_start: float = 30.0) -> float:
        """Finds the most intense gameplay event timestamp from detected game events."""
        if not events:
            return min_start

        keywords_priority = ["horde", "zombie", "attack", "bunker", "boss", "craft", "loot"]
        for kw in keywords_priority:
            for ev in events:
                desc = getattr(ev, "description", "").lower()
                st = getattr(ev, "start_time", 0.0)
                if kw in desc and st >= min_start:
                    return float(st)

        # Fallback to the first event after min_start
        for ev in events:
            st = getattr(ev, "start_time", 0.0)
            if st >= min_start:
                return float(st)

        return min_start

    def auto_detect_viral_moment(
        self,
        events: List[Any],
        video_duration: float = 180.0,
        min_start: float = 20.0,
        default_duration: float = 35.0,
    ) -> Dict[str, Any]:
        """Detects high-emotion viral moments (fails, near-death escapes, rare crate openings)."""
        # If video is shorter than standard thresholds, adjust dynamically
        if video_duration < 45.0:
            effective_min = 0.0
            clip_len = min(video_duration, default_duration)
        else:
            effective_min = min(min_start, max(0.0, video_duration - default_duration))
            clip_len = min(default_duration, video_duration)

        if not events:
            return {
                "start_time": effective_min,
                "duration": clip_len,
                "headline": "LAST DAY ON EARTH",
                "subtitle": "SURVIVAL INTENSIFIES",
                "hook_type": "standard_gameplay",
            }

        def _clamp(start: float, dur: float) -> tuple[float, float]:
            if start + dur > video_duration:
                start = max(0.0, video_duration - dur)
            return round(start, 1), round(dur, 1)

        # Priority 1: High-stakes fail moments & intense combat panic
        fail_keywords = ["death", "dying", "frenzy", "giant", "alarm", "toxic spitter", "horde", "boss", "ambush", "blind one", "panic"]
        for ev in events:
            desc = getattr(ev, "description", "").lower()
            st = getattr(ev, "start_time", 0.0)
            if any(k in desc for k in fail_keywords) and st >= effective_min:
                s, d = _clamp(float(st), 30.0)
                return {
                    "start_time": s,
                    "duration": d,
                    "headline": "DISASTER MOMENT?!",
                    "subtitle": "RED ZONE CLOSE CALL",
                    "hook_type": "fail_panic",
                }

        # Priority 2: Rare loot unboxings and bunker raids
        loot_keywords = ["red crate", "chest", "coupon", "titanium", "transmission", "chopper gas tank", "tank", "c4", "c-4", "alfa", "bunker"]
        for ev in events:
            desc = getattr(ev, "description", "").lower()
            st = getattr(ev, "start_time", 0.0)
            if any(k in desc for k in loot_keywords) and st >= effective_min:
                s, d = _clamp(float(st), 35.0)
                return {
                    "start_time": s,
                    "duration": d,
                    "headline": "RAREST LOOT DROP?!",
                    "subtitle": "OPENING RED CHEST",
                    "hook_type": "rare_loot",
                }

        # Priority 3: Intense combat or base defense
        combat_keywords = ["combat", "clearing", "raid", "defense", "farm", "attack", "wall trick"]
        for ev in events:
            desc = getattr(ev, "description", "").lower()
            st = getattr(ev, "start_time", 0.0)
            if any(k in desc for k in combat_keywords) and st >= effective_min:
                s, d = _clamp(float(st), clip_len)
                return {
                    "start_time": s,
                    "duration": d,
                    "headline": "BASE UNDER ATTACK!",
                    "subtitle": "ZOMBIE HORDE AMBUSH",
                    "hook_type": "combat_defense",
                }

        # Priority 4: Workshop tricks & blueprints
        craft_keywords = ["craft", "blueprints", "smelt", "storage", "workshop", "planks"]
        for ev in events:
            desc = getattr(ev, "description", "").lower()
            st = getattr(ev, "start_time", 0.0)
            if any(k in desc for k in craft_keywords) and st >= effective_min:
                s, d = _clamp(float(st), clip_len)
                return {
                    "start_time": s,
                    "duration": d,
                    "headline": "PRO SURVIVAL TRICK!",
                    "subtitle": "BASE WORKSHOP GUIDE",
                    "hook_type": "pro_craft",
                }

        # Fallback to general highlight
        st = self.auto_detect_highlight_start(events, min_start=effective_min)
        s, d = _clamp(st, clip_len)
        return {
            "start_time": s,
            "duration": d,
            "headline": "LAST DAY ON EARTH",
            "subtitle": "EPIC SURVIVAL MOMENT",
            "hook_type": "highlight",
        }

    def generate_short(
        self,
        input_video: Path,
        output_path: Path,
        start_time: float = 60.0,
        duration: float = 35.0,
        headline: str = "LAST DAY ON EARTH",
        subtitle: str = "BASE SURVIVAL INTENSIFIES",
        episode_number: Optional[int] = None,
    ) -> Path:
        """Renders a vertical 1080x1920 YouTube Short clip using FFmpeg."""
        if not input_video.exists():
            raise VideoProcessingError(
                operation="generate_short",
                root_cause=f"Source video not found: {input_video}",
                recovery_action="Ensure source gameplay video exists before generating Short.",
                file_path=str(input_video),
            )

        duration = min(duration, 58.0)  # YouTube Shorts hard cap
        overlay_png = self.output_dir / f"overlay_temp_{output_path.stem}.png"
        self.create_shorts_overlay(
            output_png_path=overlay_png,
            top_title=headline,
            subtitle=subtitle,
            footer_text="WATCH FULL EPISODE 🎬",
            episode_number=episode_number,
        )

        filter_graph = (
            "[0:v]split=2[bg][fg];"
            "[bg]scale=108:192,boxblur=2:2,scale=1080:1920:flags=bicubic,eq=brightness=-0.20[bgblur];"
            "[fg]scale=1080:608:force_original_aspect_ratio=decrease,pad=1080:608:(ow-iw)/2:(oh-ih)/2[fgscaled];"
            "[bgblur][fgscaled]overlay=0:656[composed];"
            "[composed][1:v]overlay=0:0[outv]"
        )

        output_path.parent.mkdir(parents=True, exist_ok=True)

        cmd = [
            "ffmpeg",
            "-y",
            "-ss", str(start_time),
            "-t", str(duration),
            "-i", str(input_video),
            "-i", str(overlay_png),
            "-filter_complex", filter_graph,
            "-map", "[outv]",
            "-map", "0:a?",
            "-c:v", "libx264",
            "-preset", "faster",
            "-crf", "22",
            "-c:a", "aac",
            "-b:a", "192k",
            str(output_path),
        ]

        logger.info(f"Rendering YouTube Short: {output_path} (Start: {start_time}s, Duration: {duration}s)")
        result = subprocess.run(cmd, capture_output=True, text=True)

        # Cleanup overlay image
        if overlay_png.exists():
            overlay_png.unlink()

        if result.returncode != 0:
            logger.error(f"FFmpeg Shorts rendering failed: {result.stderr}")
            raise VideoProcessingError(
                operation="render_short",
                root_cause=result.stderr[-500:] if result.stderr else "Unknown FFmpeg error",
                recovery_action="Check FFmpeg installation and video codec compatibility.",
                file_path=str(input_video),
            )

        logger.info(f"Successfully generated YouTube Short: {output_path}")
        return output_path

    def generate_companion_short(
        self,
        input_video: Path,
        events: Optional[List[Any]] = None,
        episode_number: Optional[int] = None,
        parent_video_id: Optional[str] = None,
        output_dir: Optional[Path] = None,
    ) -> Dict[str, Any]:
        """High-level companion Shorts generator automatically extracting peak moments and packaging metadata."""
        target_dir = output_dir or self.output_dir
        target_dir.mkdir(parents=True, exist_ok=True)

        video_duration = self.get_video_duration(input_video)
        viral_data = self.auto_detect_viral_moment(events or [], video_duration=video_duration)

        start_time = viral_data["start_time"]
        duration = viral_data["duration"]
        headline = viral_data["headline"]
        subtitle = viral_data["subtitle"]

        ep_tag = f"_ep{episode_number}" if episode_number else ""
        short_filename = f"short{ep_tag}_{input_video.stem}.mp4"
        short_output_path = target_dir / short_filename

        rendered_path = self.generate_short(
            input_video=input_video,
            output_path=short_output_path,
            start_time=start_time,
            duration=duration,
            headline=headline,
            subtitle=subtitle,
            episode_number=episode_number,
        )

        ep_suffix = f" | LDoE Survival #{episode_number}" if episode_number else " | Last Day on Earth"
        title = f"{headline}{ep_suffix} #Shorts"
        if len(title) > 100:
            title = title[:92] + "... #Shorts"

        parent_url = f"https://youtu.be/{parent_video_id}" if parent_video_id else ""
        desc_lines = [
            f"🔥 Episode #{episode_number or ''} highlight! Watch the full uncut survival episode:",
        ]
        if parent_url:
            desc_lines.append(f"👉 Full Video: {parent_url}")
        desc_lines.extend([
            "📺 Official Series Playlist: https://www.youtube.com/playlist?list=PLJPzVNVZwaGY",
            "",
            "🔴 Subscribe for daily Last Day on Earth survival gameplay!",
            "",
            "#Shorts #LastDayOnEarth #LDoE #SurvivalGaming #ZombieSurvival #GamingShorts",
        ])

        return {
            "short_path": rendered_path,
            "title": title,
            "description": "\n".join(desc_lines),
            "start_time": start_time,
            "duration": duration,
            "headline": headline,
            "subtitle": subtitle,
            "episode_number": episode_number,
            "parent_video_id": parent_video_id,
            "hook_type": viral_data.get("hook_type", "standard_gameplay"),
            "tags": ["Shorts", "LastDayOnEarth", "LDoE", "SurvivalGaming", "ZombieSurvival", "LDoESurvival"],
        }
