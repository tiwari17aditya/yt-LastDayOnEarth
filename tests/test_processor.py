"""Tests for video naming conventions and FFmpeg pipeline generation."""

from datetime import datetime
from pathlib import Path
from src.processor.video_processor import VideoProcessor


def test_standardized_filename_generation():
    processor = VideoProcessor(output_dir=Path("output"))
    today_str = datetime.now().strftime("%d%m%Y")
    
    filename = processor.generate_output_filename("Last Day on Earth Motel Run.mp4")
    assert filename == f"Last_Day_on_Earth_Motel_Run_Processed_{today_str}.mp4"


def test_ffmpeg_command_generation():
    processor = VideoProcessor(output_dir=Path("output"))
    input_path = Path("sample.mp4")
    output_path = Path("output/sample_Processed_23092026.mp4")

    cmd = processor.build_ffmpeg_command(
        input_video=input_path,
        output_video=output_path,
        privacy_filter="boxblur=10",
        ducking_db="-18dB",
    )

    assert "ffmpeg" in cmd
    assert "-y" in cmd
    assert str(input_path) in cmd
    assert str(output_path) in cmd
    assert "-movflags" in cmd
    assert "+faststart" in cmd
