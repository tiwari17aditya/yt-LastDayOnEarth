"""Unit tests for Shorts Instant Frame-1 Hook (P4).

Validates:
- Frame-1 urgency indicator banner synthesis across all viral categories.
- High-contrast 1080x1920 overlay rendering with top urgency anchor.
- Zero-delay timestamp configuration (-avoid_negative_ts make_zero).
- Backward compatibility with existing viral moment extraction.
"""

from dataclasses import dataclass
from pathlib import Path
from unittest.mock import MagicMock, patch
from PIL import Image
from src.processor.shorts_generator import ShortsGenerator


@dataclass
class DummyEvent:
    description: str
    start_time: float = 0.0


def test_viral_moments_include_frame1_urgency_badge():
    gen = ShortsGenerator()

    # Fail / Panic
    fail_events = [DummyEvent("Frenzy Giant attack and death", start_time=45.0)]
    fail_data = gen.auto_detect_viral_moment(fail_events, min_start=30.0)
    assert "urgency_badge" in fail_data
    assert "MISTAKE" in fail_data["urgency_badge"]

    # Rare Loot
    loot_events = [DummyEvent("Opening red crate and found titanium", start_time=50.0)]
    loot_data = gen.auto_detect_viral_moment(loot_events, min_start=30.0)
    assert "urgency_badge" in loot_data
    assert "DROP" in loot_data["urgency_badge"]

    # Highlight
    gen_events = [DummyEvent("Chopping pine trees and woodcraft", start_time=35.0)]
    gen_data = gen.auto_detect_viral_moment(gen_events, min_start=30.0)
    assert "urgency_badge" in gen_data
    assert "WAIT FOR IT" in gen_data["urgency_badge"]


def test_create_shorts_overlay_with_urgency_badge(tmp_path):
    gen = ShortsGenerator(output_dir=tmp_path)
    overlay_path = tmp_path / "test_overlay.png"

    result = gen.create_shorts_overlay(
        output_png_path=overlay_path,
        top_title="DISASTER MOMENT?!",
        subtitle="RED ZONE CLOSE CALL",
        footer_text="WATCH FULL EPISODE 🎬",
        episode_number=148,
        urgency_badge="⚠️ DO NOT MAKE THIS MISTAKE! ⚠️",
    )

    assert result.exists()
    assert result.stat().st_size > 0

    with Image.open(result) as img:
        assert img.size == (1080, 1920)
        assert img.mode == "RGBA"


def test_generate_short_passes_zero_delay_flags(tmp_path):
    gen = ShortsGenerator(output_dir=tmp_path)
    dummy_video = tmp_path / "source.mp4"
    dummy_video.write_bytes(b"dummy_bytes")
    target_out = tmp_path / "short_out.mp4"

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        gen.generate_short(
            input_video=dummy_video,
            output_path=target_out,
            start_time=45.0,
            duration=30.0,
            headline="DISASTER MOMENT?!",
            subtitle="RED ZONE CLOSE CALL",
            episode_number=148,
            urgency_badge="⚠️ DO NOT MAKE THIS MISTAKE! ⚠️",
        )

        assert mock_run.called
        cmd_args = mock_run.call_args[0][0]
        # Verify instant frame-1 seek and make_zero timestamp alignment
        assert "-avoid_negative_ts" in cmd_args
        assert "make_zero" in cmd_args
        assert "-ss" in cmd_args
        assert "45.0" in cmd_args
