"""Modular intro generator supporting Cinematic Intro Bumper and In-Game HUD Overlay."""

import os
import random
import re
from pathlib import Path
from typing import Optional, List, Dict, Any

from src.logging_config import get_logger

logger = get_logger(component="IntroGenerator")


def escape_drawtext(text: str) -> str:
    """Escapes special characters for FFmpeg drawtext filter parameters."""
    if not text:
        return ""
    # FFmpeg requires escaping colons, percent signs, and single quotes
    t = text.replace("\\", "\\\\")
    t = t.replace(":", "\\:")
    t = t.replace("'", "\\'")
    t = t.replace("%", "\\%")
    return t


def resolve_system_font(preferred_style: str = "bold") -> str:
    """Finds an available bold/display font on Windows or Linux."""
    candidate_fonts = [
        # Windows
        "C:/Windows/Fonts/impact.ttf" if preferred_style == "impact" else "C:/Windows/Fonts/arialbd.ttf",
        "C:/Windows/Fonts/arialbd.ttf",
        "C:/Windows/Fonts/segoeuib.ttf",
        # Linux (Ubuntu / Debian GitHub Actions)
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
    ]
    for font in candidate_fonts:
        p = Path(font)
        if p.exists():
            # For FFmpeg on Windows, colon in drive letter must be escaped
            return str(p.as_posix()).replace(":", "\\:")
    
    # Fallback to standard generic font name
    return "sans-serif"


class IntroGenerator:
    """Generates FFmpeg filtergraphs and manages intro screen assets."""

    def __init__(
        self,
        player_name: str = "adistar656",
        player_id: str = "#9045",
        clan_name: str = "Stark029",
        intro_style: str = "bumper",
        intro_duration: float = 3.5,
        bg_image_path: Optional[Path] = None,
        intros_dir: Path = Path("assets/audio/intros"),
    ) -> None:
        self.player_name = player_name
        self.player_id = player_id
        self.clan_name = clan_name
        self.intro_style = intro_style.lower() if intro_style else "none"
        self.intro_duration = intro_duration
        self.bg_image_path = bg_image_path or Path("assets/backgrounds/ldoe_cover_art.jpg")
        self.intros_dir = intros_dir

    def get_prebaked_intro_audio(self, language: str = "hi") -> Optional[Path]:
        """Selects a pre-baked studio-mastered intro audio file from the library."""
        if not self.intros_dir.exists():
            return None

        prefix = "intro_hinglish" if language in ["hi", "hi-in", "hinglish"] else "intro_english"
        candidates = list(self.intros_dir.glob(f"{prefix}_variant_*.mp3"))
        if not candidates:
            # Fallback to any intro file
            candidates = list(self.intros_dir.glob("*.mp3"))
        
        if candidates:
            selected = random.choice(candidates)
            logger.info("Selected pre-baked intro audio asset", extra_data={"asset": selected.name, "language": language})
            return selected
        return None

    def build_bumper_filters(
        self,
        episode_num: Optional[int] = None,
        episode_title: Optional[str] = None,
    ) -> List[str]:
        """Constructs FFmpeg filter list for Option A (Cinematic Intro Bumper Card)."""
        font_title = resolve_system_font("impact")
        font_body = resolve_system_font("bold")

        ep_text = f"EPISODE #{episode_num}" if episode_num else "SURVIVAL SERIES"
        if episode_title:
            clean_title = re.sub(r"[^\w\s-]", "", episode_title).strip()
            ep_line = f"{ep_text}  -  {clean_title.upper()}"
        else:
            ep_line = f"{ep_text}  -  BUNKER ALFA RAID & EXPEDITION"

        filters = [
            "scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,fps=60",
            "drawbox=x=0:y=0:w=1920:h=1080:color=black@0.45:t=fill",
            f"drawtext=fontfile='{font_body}':text='[ SURVIVOR DOSSIER & PROFILE ]':fontcolor=0xE5A93C:fontsize=28:x=(w-text_w)/2:y=240",
            f"drawtext=fontfile='{font_title}':text='LAST DAY ON EARTH \\: SURVIVAL':fontcolor=white:fontsize=76:x=(w-text_w)/2:y=290",
            f"drawtext=fontfile='{font_body}':text='{escape_drawtext(ep_line)}':fontcolor=0xE0E0E0:fontsize=38:x=(w-text_w)/2:y=400",
            "drawbox=x=260:y=500:w=1400:h=320:color=black@0.82:t=fill",
            "drawbox=x=260:y=500:w=1400:h=320:color=0xE5A93C@0.9:t=4",
            "drawbox=x=300:y=590:w=1320:h=2:color=0xE5A93C@0.5:t=fill",
            f"drawtext=fontfile='{font_body}':text='OFFICIAL SURVIVOR IDENTIFICATION':fontcolor=0xE5A93C:fontsize=26:x=300:y=535",
            f"drawtext=fontfile='{font_body}':text='STATUS\\: ACTIVE / VERIFIED':fontcolor=0x4CAF50:fontsize=26:x=1230:y=535",
            f"drawtext=fontfile='{font_body}':text='SURVIVOR\\:':fontcolor=0xAAAAAA:fontsize=24:x=300:y=630",
            f"drawtext=fontfile='{font_body}':text='{escape_drawtext(self.player_name)}':fontcolor=white:fontsize=36:x=300:y=670",
            f"drawtext=fontfile='{font_body}':text='PLAYER ID\\:':fontcolor=0xAAAAAA:fontsize=24:x=780:y=630",
            f"drawtext=fontfile='{font_body}':text='{escape_drawtext(self.player_id)}':fontcolor=white:fontsize=36:x=780:y=670",
            f"drawtext=fontfile='{font_body}':text='CLAN\\:':fontcolor=0xAAAAAA:fontsize=24:x=1200:y=630",
            f"drawtext=fontfile='{font_body}':text='{escape_drawtext(self.clan_name)}':fontcolor=0xFFD54F:fontsize=36:x=1200:y=670",
            f"drawtext=fontfile='{font_body}':text='Search Player ID {escape_drawtext(self.player_id)} or Clan {escape_drawtext(self.clan_name)} to team up in Crater & Sector 7!':fontcolor=0xCCCCCC:fontsize=24:x=300:y=760"
        ]
        return filters

    def build_overlay_filters(
        self,
        episode_num: Optional[int] = None,
        duration: float = 4.0,
        fade_out_start: float = 3.2,
        fade_out_duration: float = 0.8,
    ) -> List[str]:
        """Constructs FFmpeg filter list for Option B (In-Game Header Overlay)."""
        font_body = resolve_system_font("bold")

        ep_text = f"EPISODE #{episode_num}" if episode_num else "SURVIVAL SERIES"
        top_header = f"LAST DAY ON EARTH \\: SURVIVAL   -   {ep_text}"
        sub_bar = (
            f"SURVIVOR\\: {escape_drawtext(self.player_name)}    |    "
            f"PLAYER ID\\: {escape_drawtext(self.player_id)}    |    "
            f"CLAN\\: {escape_drawtext(self.clan_name)}"
        )

        filters = [
            f"color=c=black@0.0:s=1920x1080:d={duration:.1f},format=rgba",
            "drawbox=x=210:y=40:w=1500:h=120:color=black@0.75:t=fill",
            "drawbox=x=210:y=40:w=1500:h=120:color=0xE5A93C@0.9:t=3",
            "drawbox=x=210:y=40:w=1500:h=4:color=0xE5A93C@1.0:t=fill",
            f"drawtext=fontfile='{font_body}':text='{top_header}':fontcolor=0xE5A93C:fontsize=26:x=(w-text_w)/2:y=60",
            f"drawtext=fontfile='{font_body}':text='{sub_bar}':fontcolor=white:fontsize=34:x=(w-text_w)/2:y=105",
            f"fade=t=out:st={fade_out_start:.2f}:d={fade_out_duration:.2f}:alpha=1",
        ]
        return filters

