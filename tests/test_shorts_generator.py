"""Unit tests for ShortsGenerator module."""

from pathlib import Path
from unittest.mock import patch, MagicMock
from src.processor.shorts_generator import ShortsGenerator


def test_shorts_generator_creates_overlay_png(tmp_path):
    generator = ShortsGenerator(output_dir=tmp_path)
    overlay_path = tmp_path / "test_overlay.png"

    result = generator.create_shorts_overlay(
        output_png_path=overlay_path,
        top_title="LAST DAY ON EARTH",
        subtitle="HORDE ASSAULT",
        footer_text="WATCH EPISODE #12",
        episode_number=12,
    )

    assert result.exists()
    assert result.stat().st_size > 0


def test_auto_detect_highlight_start():
    generator = ShortsGenerator()

    class DummyEvent:
        def __init__(self, st, desc):
            self.start_time = st
            self.description = desc

    events = [
        DummyEvent(10.0, "Intro walk"),
        DummyEvent(45.0, "Crafting Wood Planks"),
        DummyEvent(120.0, "Zombie Horde Attack Wave 1"),
        DummyEvent(200.0, "Sorting inventory"),
    ]

    # Should prioritize "horde" event at 120.0
    start = generator.auto_detect_highlight_start(events, min_start=30.0)
    assert start == 120.0


@patch("subprocess.run")
def test_generate_short_invokes_ffmpeg(mock_run, tmp_path):
    generator = ShortsGenerator(output_dir=tmp_path)
    dummy_input = tmp_path / "source.mp4"
    dummy_input.write_text("dummy video")
    output_short = tmp_path / "out_short.mp4"

    mock_run.return_value = MagicMock(returncode=0)

    result = generator.generate_short(
        input_video=dummy_input,
        output_path=output_short,
        start_time=15.0,
        duration=30.0,
        headline="ZOMBIE HORDE",
        subtitle="BASE UNDER ATTACK",
        episode_number=3,
    )

    assert result == output_short
    mock_run.assert_called_once()
    cmd = mock_run.call_args[0][0]
    assert cmd[0] == "ffmpeg"
    assert "-ss" in cmd
    assert "15.0" in cmd
    assert "-t" in cmd
    assert "30.0" in cmd
    assert "scale=108:192,boxblur=2:2" in cmd[cmd.index("-filter_complex") + 1]
