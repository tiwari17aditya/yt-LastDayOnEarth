"""Script to batch-generate unique, high-CTR, non-repetitive thumbnails up to Episode #300.

Incorporates:
- 30+ distinct base scenes (24 clean gameplay action frames + 6 survival templates + cover art)
- Procedural framing (horizontal mirroring, dynamic action zoom)
- 8 atmospheric lighting and cinematic color grading moods
- Floating particle / ember depth effects
- Distressed LAST DAY ON EARTH stencil branding
- 12-color organic paint splatter badges
- 60+ tactical survival action hook banners
"""

import argparse
import io
import math
import random
import sys
from pathlib import Path
from typing import List, Tuple, Optional

# Force UTF-8 output
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, str(Path(__file__).parent.parent))

from PIL import Image, ImageDraw, ImageFont, ImageEnhance, ImageOps
import numpy as np
from src.logging_config import get_logger

logger = get_logger(component="ThumbnailBatchGenerator")

# 12 distinct survival badge colors
BADGE_PALETTE_12 = [
    (215, 25, 28),    # Crimson Red
    (235, 140, 15),   # Amber Gold
    (30, 160, 65),    # Emerald Green
    (15, 115, 220),   # Cobalt Blue
    (135, 35, 175),   # Royal Purple
    (240, 80, 20),    # Flame Orange
    (190, 15, 45),    # Blood Burgundy
    (0, 195, 225),    # Neon Cyan
    (55, 190, 30),    # Toxic Lime
    (245, 60, 10),    # Molten Lava
    (165, 45, 225),   # Electric Violet
    (215, 115, 25),   # Sunset Bronze
]

# 8 distinct atmospheric color grading profiles
COLOR_PROFILES = [
    {"name": "Blood Moon", "contrast": 1.25, "brightness": 0.98, "saturation": 1.30, "tint": (35, -5, -15)},
    {"name": "Bio-Hazard", "contrast": 1.20, "brightness": 1.02, "saturation": 1.25, "tint": (-15, 30, -20)},
    {"name": "Cold Tundra", "contrast": 1.20, "brightness": 1.00, "saturation": 1.10, "tint": (-20, 5, 35)},
    {"name": "Golden Sunset", "contrast": 1.18, "brightness": 1.05, "saturation": 1.35, "tint": (30, 20, -10)},
    {"name": "Night Stalker", "contrast": 1.30, "brightness": 0.90, "saturation": 1.15, "tint": (-10, -5, 25)},
    {"name": "Bleach Bypass", "contrast": 1.35, "brightness": 0.98, "saturation": 0.78, "tint": (10, 10, 15)},
    {"name": "Neon Cyan Lab", "contrast": 1.22, "brightness": 1.02, "saturation": 1.25, "tint": (-25, 20, 30)},
    {"name": "Molten Smelter", "contrast": 1.26, "brightness": 1.00, "saturation": 1.30, "tint": (35, 15, -15)},
]

# 65+ rotating tactical action hooks
ACTION_HOOKS = [
    "BUNKER ALFA FL 4",
    "ZOMBIE HORDE DEFENSE",
    "CHOPPER GAS TANK",
    "BLIND ONE SHOWDOWN",
    "TITANIUM SMELTER",
    "FARM BULL CLEARANCE",
    "POLICE STATION WAVE 20",
    "AIRDROP CARGO LOOT",
    "ACID BATH COMPLETED",
    "RED PINE PERIL",
    "MILITARY CONVOY RAID",
    "SUBMARINE DOCKYARD",
    "AUTO TURRET GRID",
    "WITCH LAIR PURGE",
    "FORTIFIED BASE LVL 5",
    "SNIPER RECON MISSION",
    "DRONE WEAPONS MOD",
    "SECTOR 7 CLAN WAR",
    "RECYCLER SECRETS",
    "STORAGE VAULT 2.0",
    "SWAT SHIELD ASSAULT",
    "LABORATORY SECTOR A",
    "EXPLODER EVASION",
    "GRENADE LAUNCHER TEST",
    "COLD TUNDRA EXPEDITION",
    "MAX WEAPON BLUEPRINTS",
    "SURVIVOR RECRUITMENT",
    "IRON ORE EXTRACTION",
    "HEAVY SHOTGUN RUSH",
    "PORT SEAPLANE RETRIEVAL",
    "BUNKER BRAVO PREP",
    "GAS MASK TUNNEL RUN",
    "M16 FULL AUTO MOD",
    "TOXIC ABOMINATION PURGE",
    "SECRET PASSAGE UNLOCK",
    "OAK GLADE RESOURCE RUN",
    "REST STOP AMBUSH",
    "SNEAK ATTACK MASTERY",
    "MILITARY CRATE DROP",
    "SPIKE TRAP DEFENSE",
    "FRENZIED GIANT TACTIC",
    "FLOATER BLOAT PURGE",
    "RAID RETALIATION SHIELD",
    "MEDKIT SURVIVAL ROUTE",
    "FIBERGLASS CRAFTING",
    "ELECTRONIC CIRCUIT HUNT",
    "GENERATOR ACTIVATION",
    "RADIO TOWER SIGNAL",
    "SECTOR 7 CRATER DOME",
    "MUTANT HORDE PURGE",
    "TURRET MODIFICATION",
    "ARMORED CAR AV-4",
    "BATTLE OF SUNSET BASE",
    "ENDGAME VAULT UNLOCK",
    "ELITE CRATE REWARD",
    "KABOOM MINEFIELD",
    "CRITICAL COMBAT RUN",
    "SWAMP EXPEDITION",
    "SUBTERRANEAN DRILL",
    "SURVIVOR FINAL STAND",
    "RADAR TOWER DEFENSE",
    "MINIGUN BURST COMBAT",
    "CONCRETE VAULT EXPANSION",
    "INFECTED FOREST RECON",
    "MOLTEN COPPER CRUCIBLE",
]


def load_font(names: List[str], size: int) -> ImageFont.ImageFont:
    """Robust cross-platform font loader."""
    bundled_dirs = [
        Path("config/fonts"),
        Path("assets/fonts"),
        Path(__file__).resolve().parent.parent / "config" / "fonts",
        Path(__file__).resolve().parent.parent / "assets" / "fonts",
    ]
    extended = list(names) + [
        "impact.ttf", "arialbd.ttf", "segoeuib.ttf",
        "DejaVuSans-Bold.ttf", "LiberationSans-Bold.ttf", "FreeSansBold.ttf",
    ]
    for bdir in bundled_dirs:
        if bdir.exists():
            for name in extended:
                p = bdir / name
                if p.exists():
                    try:
                        return ImageFont.truetype(str(p), size)
                    except Exception:
                        pass

    sys_dirs = [Path("C:/Windows/Fonts"), Path("/usr/share/fonts"), Path("/usr/local/share/fonts")]
    for sdir in sys_dirs:
        if sdir.exists():
            for name in extended:
                p = sdir / name
                if p.exists():
                    try:
                        return ImageFont.truetype(str(p), size)
                    except Exception:
                        pass
                try:
                    matches = list(sdir.rglob(name))
                    if matches:
                        return ImageFont.truetype(str(matches[0]), size)
                except Exception:
                    pass
    return ImageFont.load_default()


def apply_atmospheric_grade(img: Image.Image, profile: dict) -> Image.Image:
    """Applies cinematic contrast, saturation, and atmospheric RGB color grading."""
    enh_c = ImageEnhance.Contrast(img)
    img = enh_c.enhance(profile["contrast"])
    enh_b = ImageEnhance.Brightness(img)
    img = enh_b.enhance(profile["brightness"])
    enh_s = ImageEnhance.Color(img)
    img = enh_s.enhance(profile["saturation"])

    arr = np.array(img, dtype=np.int16)
    r_tint, g_tint, b_tint = profile["tint"]
    arr[..., 0] = np.clip(arr[..., 0] + r_tint, 0, 255)
    arr[..., 1] = np.clip(arr[..., 1] + g_tint, 0, 255)
    arr[..., 2] = np.clip(arr[..., 2] + b_tint, 0, 255)
    return Image.fromarray(arr.astype(np.uint8))


def draw_cinematic_vignette_and_particles(img: Image.Image, seed: int, ember_color: Tuple[int, int, int]) -> Image.Image:
    """Adds a smooth dark edge vignette and atmospheric floating dust/ember particles."""
    w, h = img.size
    cx, cy = w / 2.0, h / 2.0
    y_idx, x_idx = np.indices((h, w), dtype=np.float32)
    dist = np.sqrt(((x_idx - cx) / (w / 1.5)) ** 2 + ((y_idx - cy) / (h / 1.5)) ** 2)
    vig_mask = np.clip((dist - 0.55) / 0.45, 0.0, 1.0)
    vig_alpha = (vig_mask * 160.0).astype(np.uint8)

    vig_arr = np.zeros((h, w, 4), dtype=np.uint8)
    vig_arr[..., 3] = vig_alpha
    vig_layer = Image.fromarray(vig_arr, mode="RGBA")
    img_with_vig = Image.alpha_composite(img.convert("RGBA"), vig_layer)

    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    rng = random.Random(seed)
    num_particles = rng.randint(20, 36)
    for _ in range(num_particles):
        px = rng.randint(int(w * 0.35), w - 20)
        py = rng.randint(int(h * 0.1), h - 20)
        pr = rng.randint(2, 6)
        p_alpha = rng.randint(120, 220)
        draw.ellipse([px - pr, py - pr, px + pr, py + pr], fill=(*ember_color, p_alpha))

    return Image.alpha_composite(img_with_vig, overlay)


def draw_distressed_last_day_logo(draw: ImageDraw.Draw, top_left: Tuple[int, int], scale: float = 1.0) -> None:
    """Renders signature distressed LAST DAY ON EARTH stencil logo."""
    x0, y0 = top_left
    font_big = load_font(["impact.ttf", "arialbd.ttf"], int(110 * scale))
    font_on = load_font(["impact.ttf", "arialbd.ttf"], int(50 * scale))
    font_earth = load_font(["impact.ttf", "arialbd.ttf"], int(120 * scale))

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

    def draw_text_with_shadow(txt, pos, font, fill_color, stroke_w=4):
        x, y = pos
        for dx in range(-stroke_w, stroke_w + 1):
            for dy in range(-stroke_w, stroke_w + 1):
                if dx * dx + dy * dy <= stroke_w * stroke_w:
                    draw.text((x + dx, y + dy + 2), txt, font=font, fill=(0, 0, 0, 240))
        draw.text((x, y), txt, font=font, fill=fill_color)

    draw_text_with_shadow("LAST", (x0, y0), font_big, (255, 255, 255, 255), stroke_w=int(5 * scale))
    draw_text_with_shadow("DAY", (x0, y0 + int(98 * scale)), font_big, (255, 255, 255, 255), stroke_w=int(5 * scale))
    draw_text_with_shadow("ON", (x0 + int(10 * scale), earth_y + int(42 * scale)), font_on, (255, 255, 255, 255), stroke_w=int(4 * scale))
    draw_text_with_shadow("EARTH", (x0 + int(85 * scale), earth_y), font_earth, (225, 20, 25, 255), stroke_w=int(6 * scale))


def draw_paint_splatter_badge(
    draw: ImageDraw.Draw,
    center: Tuple[int, int],
    badge_text: str,
    color: Tuple[int, int, int],
    badge_w: int = 240,
    badge_h: int = 150,
    seed: int = 0,
) -> None:
    """Renders organic weathered paint splatter badge with unique procedural drip geometry."""
    cx, cy = center
    rng = random.Random(seed)

    num_blotches = 30
    for _ in range(num_blotches):
        bx = cx + rng.randint(-int(badge_w * 0.35), int(badge_w * 0.35))
        by = cy + rng.randint(-int(badge_h * 0.32), int(badge_h * 0.32))
        rx = rng.randint(int(badge_w * 0.15), int(badge_w * 0.32))
        ry = rng.randint(int(badge_h * 0.18), int(badge_h * 0.38))
        draw.ellipse([bx - rx, by - ry, bx + rx, by + ry], fill=(*color, 245))

    num_spikes = 34
    for _ in range(num_spikes):
        angle = rng.uniform(0, 2 * math.pi)
        dist = rng.uniform(badge_w * 0.32, badge_w * 0.65)
        sx = cx + int(math.cos(angle) * dist)
        sy = cy + int(math.sin(angle) * dist * (badge_h / badge_w * 1.2))
        dot_rad = rng.randint(3, 14)
        draw.ellipse([sx - dot_rad, sy - dot_rad, sx + dot_rad, sy + dot_rad], fill=(*color, 230))

    for _ in range(14):
        angle = rng.uniform(0, 2 * math.pi)
        start_d = rng.uniform(badge_w * 0.25, badge_w * 0.45)
        len_d = rng.uniform(20, 65)
        x1 = cx + int(math.cos(angle) * start_d)
        y1 = cy + int(math.sin(angle) * start_d)
        x2 = cx + int(math.cos(angle) * (start_d + len_d))
        y2 = cy + int(math.sin(angle) * (start_d + len_d))
        draw.line([x1, y1, x2, y2], fill=(*color, 220), width=rng.randint(3, 7))

    font_num = load_font(["impact.ttf", "arialbd.ttf"], int(badge_h * 0.85))
    tbox = draw.textbbox((0, 0), badge_text, font=font_num)
    tw, th = tbox[2] - tbox[0], tbox[3] - tbox[1]
    tx, ty = cx - tw // 2, cy - th // 2 - int(badge_h * 0.05)

    for ox, oy in [(-3, -3), (3, -3), (-3, 3), (3, 3), (0, 4), (4, 0)]:
        draw.text((tx + ox, ty + oy), badge_text, font=font_num, fill=(0, 0, 0, 230))
    draw.text((tx, ty), badge_text, font=font_num, fill=(255, 255, 255, 255))


def draw_action_hook_banner(
    draw: ImageDraw.Draw,
    center_top: Tuple[int, int],
    hook_text: str,
    accent_color: Tuple[int, int, int],
) -> None:
    """Renders a high-contrast tactical hook banner docked beneath the splatter badge."""
    cx, cy = center_top
    font_hook = load_font(["impact.ttf", "arialbd.ttf"], 28)
    bbox = draw.textbbox((0, 0), hook_text, font=font_hook)
    hw, hh = bbox[2] - bbox[0], bbox[3] - bbox[1]

    plate_w = hw + 36
    plate_h = hh + 18
    px = cx - plate_w // 2
    py = cy

    draw.rounded_rectangle(
        [px, py, px + plate_w, py + plate_h],
        radius=8,
        fill=(12, 16, 22, 235),
        outline=(*accent_color, 240),
        width=2,
    )
    draw.rounded_rectangle([px + 6, py + 5, px + 12, py + plate_h - 5], radius=2, fill=(*accent_color, 255))

    tx = px + 22
    ty = py + (plate_h - hh) // 2 - 2
    draw.text((tx + 2, ty + 2), hook_text, font=font_hook, fill=(0, 0, 0, 230))
    draw.text((tx, ty), hook_text, font=font_hook, fill=(255, 255, 255, 255))


def generate_episode_thumbnail(
    episode: int,
    base_image_path: Path,
    output_path: Path,
    hook_text: Optional[str] = None,
) -> Path:
    """Generates an individual diverse, high-CTR thumbnail for an episode."""
    profile = COLOR_PROFILES[episode % len(COLOR_PROFILES)]
    badge_color = BADGE_PALETTE_12[(episode - 1) % len(BADGE_PALETTE_12)]
    hook = hook_text or ACTION_HOOKS[(episode - 138) % len(ACTION_HOOKS)]

    with Image.open(base_image_path) as raw:
        img = raw.convert("RGB").resize((1280, 720), Image.Resampling.LANCZOS)

        # Alternating horizontal mirror for layout variation
        if episode % 2 == 1:
            img = ImageOps.mirror(img)

        # Dynamic subtle framing zoom/shift (1.0x to 1.12x)
        zoom_factor = 1.0 + ((episode % 5) * 0.025)
        if zoom_factor > 1.0:
            zw, zh = int(1280 * zoom_factor), int(720 * zoom_factor)
            zoomed = img.resize((zw, zh), Image.Resampling.BILINEAR)
            left = (zw - 1280) // 2
            top = (zh - 720) // 2
            img = zoomed.crop((left, top, left + 1280, top + 720))

        # 1. Apply atmospheric color grade
        graded = apply_atmospheric_grade(img, profile)

        # 2. Apply dark cinematic edge vignette and atmospheric floating embers
        composite = draw_cinematic_vignette_and_particles(graded, seed=episode, ember_color=badge_color)

        # 3. Render distressed logo, episode badge, and action hook
        overlay = Image.new("RGBA", (1280, 720), (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)

        draw_distressed_last_day_logo(draw, top_left=(64, 130), scale=1.1)

        badge_center = (1120, 115)
        draw_paint_splatter_badge(
            draw=draw,
            center=badge_center,
            badge_text=f"#{episode}",
            color=badge_color,
            seed=episode,
        )

        draw_action_hook_banner(
            draw=draw,
            center_top=(1120, 195),
            hook_text=hook,
            accent_color=badge_color,
        )

        final_img = Image.alpha_composite(composite, overlay).convert("RGB")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        final_img.save(output_path, "JPEG", quality=93, optimize=True)
        return output_path


def build_base_image_pool() -> List[Path]:
    """Assembles curated, high-action gameplay captures and scenario templates."""
    pool: List[Path] = []

    # 1. High-action combat and exploration captures
    action_frames = sorted(Path("temp/gameplay_action_frames").glob("*.jpg"))
    if action_frames:
        pool.extend(action_frames)

    # 2. High-res themed templates
    templates = sorted(Path("data/thumbnails/templates").glob("*.jpg"))
    pool.extend(templates)

    # 3. Official cover art
    cover = Path("assets/backgrounds/ldoe_cover_art.jpg")
    if cover.exists():
        pool.append(cover)

    # 4. Curated loadout/inventory frame
    loadout_frame = Path("temp/clean_gameplay_frames/clean_frame_205.jpg")
    if loadout_frame.exists():
        pool.append(loadout_frame)

    return pool


def main():
    parser = argparse.ArgumentParser(description="Batch generate diverse thumbnails up to Episode #300")
    parser.add_argument("--start", type=int, default=138, help="Starting episode number (default: 138)")
    parser.add_argument("--end", type=int, default=300, help="Ending episode number (default: 300)")
    parser.add_argument("--force", action="store_true", help="Overwrite existing episode thumbnails")
    parser.add_argument("--dry-run", action="store_true", help="Simulate generation without writing files")

    args = parser.parse_args()

    pool = build_base_image_pool()
    if not pool:
        print("[ERROR] No base images found to generate thumbnails from.")
        sys.exit(1)

    print(f"Loaded {len(pool)} diverse base images for thumbnail generation pool.")
    print(f"Target Episode Range: #{args.start} -> #{args.end} ({args.end - args.start + 1} thumbnails)")

    dest_dir = Path("data/thumbnails")
    dest_dir.mkdir(parents=True, exist_ok=True)

    generated_count = 0
    skipped_count = 0

    for ep in range(args.start, args.end + 1):
        target_path = dest_dir / f"episode_{ep}.jpg"
        if target_path.exists() and not args.force:
            skipped_count += 1
            continue

        base_img = pool[ep % len(pool)]
        hook = ACTION_HOOKS[(ep - 138) % len(ACTION_HOOKS)]
        profile = COLOR_PROFILES[ep % len(COLOR_PROFILES)]

        if args.dry_run:
            print(f"[DRY-RUN] Ep #{ep}: Base={base_img.name}, Mood={profile['name']}, Hook={hook}")
            generated_count += 1
            continue

        generate_episode_thumbnail(
            episode=ep,
            base_image_path=base_img,
            output_path=target_path,
            hook_text=hook,
        )
        generated_count += 1
        if generated_count % 20 == 0 or ep == args.end:
            print(f"Generated {generated_count} thumbnails (Latest: #{ep} -> {target_path.name})...")

    print("\n==========================================")
    print("BATCH GENERATION COMPLETE:")
    print(f"  • Newly Generated: {generated_count}")
    print(f"  • Skipped (Already existed): {skipped_count}")
    print(f"  • Total Available Range: Episode #01 -> #{args.end}")
    print("==========================================\n")


if __name__ == "__main__":
    main()
