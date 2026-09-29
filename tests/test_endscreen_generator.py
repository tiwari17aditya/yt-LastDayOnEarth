"""Unit tests for EndScreenGenerator module."""

from pathlib import Path
from unittest.mock import patch, MagicMock
from src.processor.endscreen_generator import EndScreenGenerator


def test_endscreen_generator_creates_frame_jpeg(tmp_path):
    generator = EndScreenGenerator(output_dir=tmp_path)
    frame_path = tmp_path / "test_frame.jpg"

    result = generator.create_endscreen_frame(
        output_image_path=frame_path,
        series_title="LAST DAY ON EARTH",
        call_to_action="SUBSCRIBE FOR DAILY RAIDS",
    )

    assert result.exists()
    assert result.stat().st_size > 0


@patch("subprocess.run")
def test_render_endscreen_clip_invokes_ffmpeg(mock_run, tmp_path):
    generator = EndScreenGenerator(output_dir=tmp_path)
    output_mp4 = tmp_path / "endscreen.mp4"
    mock_run.return_value = MagicMock(returncode=0)

    result = generator.render_endscreen_clip(
        output_mp4_path=output_mp4,
        duration=10.0,
    )

    assert result == output_mp4
    mock_run.assert_called_once()
    cmd = mock_run.call_args[0][0]
    assert cmd[0] == "ffmpeg"
    assert "-loop" in cmd
    assert "-t" in cmd
    assert "10.0" in cmd
