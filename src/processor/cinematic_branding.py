"""Cinematic Last Day on Earth thumbnail branding engine."""

import math
import random
from pathlib import Path
from typing import Optional, Tuple, List
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import numpy as np

# Palette of grunge splatter badge colors (matching the sample thumbnails)
BADGE_PALETTE = [
    (215, 25, 28),    # Crimson Red (Ep 1, 2)
    (230, 160, 20),   # Amber Yellow (Ep 3)
    (34, 155, 60),    # Emerald Green (Ep 4)
    (15, 115, 215),   # Cobalt Blue (Ep 5)
    (125, 35, 165),   # Royal Purple (Ep 6)
    (235, 85, 20),    # Flame Orange (Ep 7)
    (200, 20, 40),    # Blood Red (Ep 8)
    (0, 185, 220),    # Cyan Blue (Ep 9)
    (210, 25, 30),    # Deep Crimson (Ep 10)
    (25, 165, 80),    # Toxic Green (Ep 11)
]


def _get_badge_color(episode: int) -> Tuple[int, int, int]:
    return BADGE_PALETTE[(episode - 1) % len(BADGE_PALETTE)]


def _load_font(names: List[str], size: int) -> ImageFont.ImageFont:
    font_dirs = [
        Path("C:/Windows/Fonts"),
        Path("/usr/share/fonts"),
        Path("/usr/local/share/fonts"),
    ]
    for name in names:
        for fdir in font_dirs:
            fpath = fdir / name
            if fpath.exists():
                try:
                    return ImageFont.truetype(str(fpath), size)
                except Exception:
                    pass
    return ImageFont.load_default()


def draw_paint_splatter_badge(
    draw: ImageDraw.Draw,
    center: Tuple[int, int],
    badge_text: str,
    color: Tuple[int, int, int],
    badge_w: int = 240,
    badge_h: int = 150,
) -> None:
    """Draws an authentic, weathered paint-splatter grunge badge with white distressed text."""
    cx, cy = center
    rng = random.Random(abs(hash(badge_text)))

    # Main organic paint splatter blotch using cluster of jittered circles
    num_blotches = 28
    for _ in range(num_blotches):
        bx = cx + rng.randint(-int(badge_w * 0.35), int(badge_w * 0.35))
        by = cy + rng.randint(-int(badge_h * 0.32), int(badge_h * 0.32))
        rx = rng.randint(int(badge_w * 0.15), int(badge_w * 0.32))
        ry = rng.randint(int(badge_h * 0.18), int(badge_h * 0.38))
        draw.ellipse([bx - rx, by - ry, bx + rx, by + ry], fill=(*color, 245))

    # Extended radial splatter spikes and drips
    num_spikes = 32
    for _ in range(num_spikes):
        angle = rng.uniform(0, 2 * math.pi)
        dist = rng.uniform(badge_w * 0.32, badge_w * 0.65)
        sx = cx + int(math.cos(angle) * dist)
        sy = cy + int(math.sin(angle) * dist * (badge_h / badge_w * 1.2))
        dot_rad = rng.randint(3, 14)
        draw.ellipse([sx - dot_rad, sy - dot_rad, sx + dot_rad, sy + dot_rad], fill=(*color, 230))

    # Few splatter lines radiating outwards
    for _ in range(12):
        angle = rng.uniform(0, 2 * math.pi)
        start_d = rng.uniform(badge_w * 0.25, badge_w * 0.45)
        len_d = rng.uniform(20, 60)
        x1 = cx + int(math.cos(angle) * start_d)
        y1 = cy + int(math.sin(angle) * start_d)
        x2 = cx + int(math.cos(angle) * (start_d + len_d))
        y2 = cy + int(math.sin(angle) * (start_d + len_d))
        draw.line([x1, y1, x2, y2], fill=(*color, 220), width=rng.randint(3, 7))

    # Distressed white text with dark grunge drop shadow
    font_num = _load_font(["impact.ttf", "arialbd.ttf", "segoeuib.ttf"], int(badge_h * 0.85))
    tbox = draw.textbbox((0, 0), badge_text, font=font_num)
    tw, th = tbox[2] - tbox[0], tbox[3] - tbox[1]
    tx, ty = cx - tw // 2, cy - th // 2 - int(badge_h * 0.05)

    # Black distressed shadow
    for ox, oy in [(-3, -3), (3, -3), (-3, 3), (3, 3), (0, 4), (4, 0)]:
        draw.text((tx + ox, ty + oy), badge_text, font=font_num, fill=(0, 0, 0, 220))

    # Main bold white text
    draw.text((tx, ty), badge_text, font=font_num, fill=(255, 255, 255, 255))


def draw_distressed_last_day_logo(
    draw: ImageDraw.Draw,
    top_left: Tuple[int, int],
    scale: float = 1.0,
) -> None:
    """Renders the signature LAST DAY ON EARTH distressed stencil logo."""
    x0, y0 = top_left

    font_big = _load_font(["impact.ttf", "arialbd.ttf"], int(110 * scale))
    font_on = _load_font(["impact.ttf", "arialbd.ttf"], int(50 * scale))
    font_earth = _load_font(["impact.ttf", "arialbd.ttf"], int(120 * scale))

    # Red splatter background behind 'EARTH'
    earth_y = y0 + int(210 * scale)
    rng = random.Random(42)
    for _ in range(25):
        sx = x0 + int(rng.uniform(110, 440) * scale)
        sy = earth_y + int(rng.uniform(10, 110) * scale)
        r = int(rng.uniform(12, 38) * scale)
        draw.ellipse([sx - r, sy - r, sx + r, sy + r], fill=(160, 10, 15, 200))
    for _ in range(16):
        sx = x0 + int(rng.uniform(80, 460) * scale)
        sy = earth_y + int(rng.uniform(0, 140) * scale)
        r = int(rng.uniform(4, 14) * scale)
        draw.ellipse([sx - r, sy - r, sx + r, sy + r], fill=(180, 15, 20, 220))

    def draw_text_with_shadow(txt, pos, font, fill_color, shadow_color=(0, 0, 0, 230), stroke_w=4):
        x, y = pos
        # Thick dark stroke / shadow
        for dx in range(-stroke_w, stroke_w + 1):
            for dy in range(-stroke_w, stroke_w + 1):
                if dx * dx + dy * dy <= stroke_w * stroke_w:
                    draw.text((x + dx, y + dy + 2), txt, font=font, fill=shadow_color)
        draw.text((x, y), txt, font=font, fill=fill_color)

    # Line 1: LAST
    draw_text_with_shadow("LAST", (x0, y0), font_big, (255, 255, 255, 255), stroke_w=int(5 * scale))

    # Line 2: DAY
    draw_text_with_shadow("DAY", (x0, y0 + int(98 * scale)), font_big, (255, 255, 255, 255), stroke_w=int(5 * scale))

    # Line 3: ON EARTH
    draw_text_with_shadow("ON", (x0 + int(10 * scale), earth_y + int(42 * scale)), font_on, (255, 255, 255, 255), stroke_w=int(4 * scale))
    draw_text_with_shadow("EARTH", (x0 + int(85 * scale), earth_y), font_earth, (225, 20, 25, 255), stroke_w=int(6 * scale))


def apply_cinematic_grunge_branding(
    image_path: Path,
    episode_number: Optional[int] = None,
    badge_text: Optional[str] = None,
    output_path: Optional[Path] = None,
    badge_corner: str = "top_right",
    include_logo: bool = True,
) -> Path:
    """Applies the Last Day On Earth grunge aesthetic (distressed logo & episode splatter badge)."""
    target = output_path or image_path

    with Image.open(image_path) as raw_img:
        img = raw_img.convert("RGBA").resize((1280, 720), Image.Resampling.LANCZOS)
        w, h = img.size

        # Apply cinematic edge vignette
        overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)

        # Draw Corner Episode Splatter Badge
        label = badge_text
        if not label and episode_number is not None:
            label = f"#{episode_number}"

        if label:
            ep_val = episode_number or 1
            color = _get_badge_color(ep_val)

            if badge_corner == "top_left":
                badge_center = (int(w * 0.12), int(h * 0.16))
            elif badge_corner == "bottom_right":
                badge_center = (int(w * 0.88), int(h * 0.82))
            else:  # top_right
                badge_center = (int(w * 0.90), int(h * 0.16))

            draw_paint_splatter_badge(
                draw=draw,
                center=badge_center,
                badge_text=label,
                color=color,
                badge_w=int(w * 0.16),
                badge_h=int(h * 0.18),
            )

        # Draw Distressed LAST DAY ON EARTH Logo
        if include_logo:
            # Place on left or center-left
            logo_pos = (int(w * 0.05), int(h * 0.18))
            draw_distressed_last_day_logo(draw=draw, top_left=logo_pos, scale=1.1)

        result = Image.alpha_composite(img, overlay).convert("RGB")
        target.parent.mkdir(parents=True, exist_ok=True)
        result.save(target, "JPEG", quality=93, optimize=True)
        return target
