"""Unit tests for ThumbnailGenerator keyframe selection and branding overlays."""

from pathlib import Path
from dataclasses import dataclass
from unittest.mock import patch, MagicMock
from PIL import Image
from src.processor.thumbnail_generator import ThumbnailGenerator


@dataclass
class DummyEvent:
    start_time: float
    end_time: float
    action_type: str
    description: str


def test_select_best_timestamp_from_events():
    gen = ThumbnailGenerator()
    events = [
        DummyEvent(0.5, 1.5, "nav", "Global Map"),
        DummyEvent(20.0, 21.0, "craft", "Crafting Planks"),
        DummyEvent(40.0, 41.0, "craft", "Weapon Bench"),
    ]
    ts = gen.select_best_timestamp(events=events, duration=180.0)
    # Should pick active base bench event (>= 30s), e.g. 40.0s + 5.0s = 45.0s
    assert ts == 45.0


def test_select_best_timestamp_fallback_duration():
    gen = ThumbnailGenerator()
    ts = gen.select_best_timestamp(events=None, duration=100.0)
    assert ts == 25.0


def test_apply_badge_overlay(tmp_path):
    gen = ThumbnailGenerator()
    img_path = tmp_path / "test_thumb.jpg"

    # Create dummy image
    img = Image.new("RGB", (1280, 720), color=(50, 50, 50))
    img.save(img_path, "JPEG")

    result_path = gen.apply_badge_overlay(img_path, badge_text="EPISODE #01")
    assert result_path.exists()

    # Verify image is valid and readable after badge overlay
    with Image.open(result_path) as modified:
        assert modified.size == (1280, 720)


@patch("subprocess.run")
def test_extract_enhanced_frame(mock_run, tmp_path):
    mock_run.return_value = MagicMock(returncode=0)
    gen = ThumbnailGenerator()
    out_path = tmp_path / "frame.jpg"
    # Create the file to simulate ffmpeg writing it
    out_path.touch()

    res = gen.extract_enhanced_frame(
        video_path=Path("dummy_video.mp4"),
        output_frame_path=out_path,
        timestamp=20.0,
    )

    assert res == out_path
    mock_run.assert_called_once()
    cmd = mock_run.call_args[0][0]
    assert "-ss" in cmd
    assert "20.0" in cmd
    assert "-vf" in cmd
