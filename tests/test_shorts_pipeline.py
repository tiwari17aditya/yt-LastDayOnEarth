"""Unit tests for YouTube Shorts Automated Scheduling & Pipeline Hook (Priority 8)."""

from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from src.processor.shorts_generator import ShortsGenerator
from src.publisher.youtube_client import YouTubeClient


class MockEvent:
    def __init__(self, description: str, start_time: float, duration: float = 10.0):
        self.description = description
        self.start_time = start_time
        self.duration = duration


def test_auto_detect_highlights_single():
    gen = ShortsGenerator(output_dir=Path("temp/test_shorts"))
    events = [
        MockEvent("Player walking through forest", 15.0),
        MockEvent("Zombie horde attacking perimeter wall", 75.0),
        MockEvent("Opening red crate with chopper parts", 160.0),
    ]

    highlights = gen.auto_detect_highlights(events, count=1)
    assert len(highlights) == 1
    assert highlights[0]["start_time"] == 75.0
    assert highlights[0]["hook_type"] == "fail_panic"


def test_auto_detect_highlights_multiple_non_overlapping():
    gen = ShortsGenerator(output_dir=Path("temp/test_shorts"))
    events = [
        MockEvent("Frenzy Giant ambush and near death escape", 60.0),
        MockEvent("Opening red crate rare chopper gas tank", 150.0),
        MockEvent("Smelting titanium bars at advanced furnace", 240.0),
    ]

    highlights = gen.auto_detect_highlights(events, count=2, video_duration=300.0)
    assert len(highlights) == 2
    # Check that they are separated by at least 45 seconds
    assert abs(highlights[1]["start_time"] - highlights[0]["start_time"]) >= 45.0


def test_upload_short_metadata_and_scheduling(tmp_path):
    client = YouTubeClient()
    mock_service = MagicMock()
    client.get_service = MagicMock(return_value=mock_service)

    # Mock insert and execute
    mock_insert = MagicMock()
    mock_insert.next_chunk.return_value = (None, {"id": "short_mock_123"})
    mock_service.videos().insert.return_value = mock_insert

    # Mock commentThreads insert
    mock_comment_insert = MagicMock()
    mock_comment_insert.execute.return_value = {"id": "comment_mock_123"}
    mock_service.commentThreads().insert.return_value = mock_comment_insert

    dummy_video = tmp_path / "test_short.mp4"
    dummy_video.write_bytes(b"dummy mp4 content")

    schedule_time = datetime(2026, 11, 10, 15, 30, 0, tzinfo=timezone.utc)

    result = client.upload_short(
        short_video_path=dummy_video,
        parent_video_title="Fortifying the Base",
        parent_video_id="parent_vid_456",
        short_info={"headline": "ZOMBIE HORDE ASSAULT?!"},
        episode_number=48,
        schedule_time=schedule_time,
    )

    assert result["video_id"] == "short_mock_123"
    assert "https://youtube.com/shorts/short_mock_123" in result["url"]
    assert result["scheduled_for"] == "2026-11-10T15:30:00Z"

    # Verify upload body parameters
    call_args = mock_service.videos().insert.call_args[1]
    body = call_args["body"]
    assert "#Shorts" in body["snippet"]["title"]
    assert len(body["snippet"]["title"]) <= 100
    assert "https://youtu.be/parent_vid_456" in body["snippet"]["description"]
    assert body["status"]["privacyStatus"] == "private"  # Scheduled requires private
    assert body["status"]["publishAt"] == "2026-11-10T15:30:00Z"

    # Verify pinned comment was posted
    comment_call_args = mock_service.commentThreads().insert.call_args[1]
    comment_body = comment_call_args["body"]
    assert "https://youtu.be/parent_vid_456" in comment_body["snippet"]["topLevelComment"]["snippet"]["textOriginal"]


def test_pipeline_shorts_integration(tmp_path):
    from src.main import run_pipeline

    input_video = tmp_path / "sample_gameplay.mp4"
    input_video.write_bytes(b"sample video bytes for testing")

    with patch("src.main.get_settings") as mock_settings, \
         patch("src.main.VideoProcessor") as mock_vp, \
         patch("src.main.AudioMixer") as mock_am, \
         patch("src.main.YouTubeClient") as mock_yt, \
         patch("src.main.ShortsGenerator") as mock_sg, \
         patch("src.main.HistoryTracker") as mock_ht, \
         patch("src.main.get_notifier") as mock_notif, \
         patch("src.main.calculate_file_md5", return_value="mock_md5_123"):

        settings_inst = MagicMock()
        settings_inst.processing.delete_input_after_processing = False
        settings_inst.processing.remove_ads = False
        settings_inst.processing.outro_tail_enabled = False
        settings_inst.processing.generate_thumbnail = False
        settings_inst.processing.shorts_automation_enabled = True
        settings_inst.processing.shorts_per_episode = 1
        settings_inst.processing.shorts_schedule_delay_hours = 6.0
        settings_inst.processing.shorts_privacy_status = "scheduled"
        settings_inst.processing.temp_dir = tmp_path
        settings_inst.processing.output_dir = tmp_path
        settings_inst.youtube.episode_numbering = True
        mock_settings.return_value = settings_inst

        # Mock video processor
        vp_inst = MagicMock()
        vp_output = tmp_path / "sample_gameplay_processed.mp4"
        vp_output.write_bytes(b"processed video bytes")
        vp_inst.get_output_path.return_value = vp_output
        mock_vp.return_value = vp_inst

        # Mock shorts generator
        sg_inst = MagicMock()
        short_file = tmp_path / "sample_short_1.mp4"
        short_file.write_bytes(b"short bytes")
        sg_inst.generate_shorts_for_episode.return_value = [{
            "video_path": short_file,
            "headline": "INSANE ZOMBIE AMBUSH",
            "subtitle": "RED ZONE ESCAPE",
            "start_time": 45.0,
            "duration": 35.0,
            "hook_type": "combat",
            "index": 1,
        }]
        mock_sg.return_value = sg_inst

        # Mock YouTube upload
        yt_inst = MagicMock()
        yt_inst.upload_video.return_value = "https://youtu.be/main_vid_789"
        yt_inst.upload_short.return_value = {
            "video_id": "short_vid_999",
            "url": "https://youtube.com/shorts/short_vid_999",
            "scheduled_for": "2026-11-04T12:00:00Z",
        }
        mock_yt.return_value = yt_inst

        # Run pipeline in upload mode
        res = run_pipeline(input_video, local_only=False, force=True)

        assert res.uploaded_to_youtube is True
        assert len(res.shorts) == 1
        assert res.shorts[0]["headline"] == "INSANE ZOMBIE AMBUSH"
        assert res.shorts[0]["upload"]["video_id"] == "short_vid_999"
        yt_inst.upload_short.assert_called_once()
