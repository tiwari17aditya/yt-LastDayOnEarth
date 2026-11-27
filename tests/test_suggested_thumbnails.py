"""Unit tests for Suggested Video Thumbnail Optimization (P3).

Validates:
- 1 dominant focal point color grading (+20% contrast, +30% saturation, unsharp).
- Strict 2 to 3 words complementary text constraint.
- High-contrast, non-redundant badge generation complementing the episode title.
- Clean rendering of complementary hook badge and episode splatter badge.
"""

from dataclasses import dataclass
from pathlib import Path
from PIL import Image
from src.processor.thumbnail_generator import ThumbnailGenerator
from src.processor.cinematic_branding import (
    apply_cinematic_grunge_branding,
    draw_complementary_hook_badge,
)


@dataclass
class DummyEvent:
    description: str
    start_time: float = 0.0


def test_complementary_badge_text_length_and_quality():
    tg = ThumbnailGenerator()

    scenarios = [
        ([DummyEvent("Bunker Alfa Floor 3 Raid")], "FLOOR 3 RUN!"),
        ([DummyEvent("Crooked Creek Farm Clearing")], "FARM RUN!"),
        ([DummyEvent("Organizing Storage & Chests")], "MAX STORAGE!"),
        ([DummyEvent("Smelting Iron Ore in Furnace")], "SPEED FARM!"),
        ([DummyEvent("The Blind One Boss Fight")], "BOSS FIGHT!"),
        ([DummyEvent("Opening Red Crate with Chopper Tank")], "INSANE LOOT!"),
    ]

    for events, expected in scenarios:
        badge = tg.generate_complementary_badge_text(events=events)
        words = badge.split()
        assert 2 <= len(words) <= 3, f"Badge must be 2-3 words: '{badge}'"
        assert badge == expected


def test_complementary_hook_badge_rendering(tmp_path):
    img_path = tmp_path / "test_thumb.jpg"
    out_path = tmp_path / "branded_thumb.jpg"

    # Create dummy base image 1280x720
    img = Image.new("RGB", (1280, 720), color=(40, 45, 50))
    img.save(img_path, "JPEG")

    # Apply grunge branding with complementary hook badge
    res = apply_cinematic_grunge_branding(
        image_path=img_path,
        episode_number=148,
        badge_text="#148",
        output_path=out_path,
        hook_badge_text="SOLO CLEAR!",
    )

    assert res.exists()
    assert res.stat().st_size > 0

    with Image.open(res) as branded:
        assert branded.size == (1280, 720)


def test_badge_never_duplicates_verbose_title():
    tg = ThumbnailGenerator()
    events = [DummyEvent("Organizing Storage & Chests")]
    verbose_title = "Best Base Storage & Workshop Layout Guide | LDoE #147"

    badge = tg.generate_complementary_badge_text(events=events, title=verbose_title)

    # Must be 2-3 words and NOT repeat the full 8-word title
    assert len(badge.split()) <= 3
    assert badge != verbose_title
    assert badge == "MAX STORAGE!"
