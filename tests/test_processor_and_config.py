from src.config import _safe_int, _safe_float, get_settings
from src.processor.video_processor import VideoProcessor


def test_safe_int_and_float_parsers():
    assert _safe_int("", 587) == 587
    assert _safe_int("   ", 587) == 587
    assert _safe_int(None, 587) == 587
    assert _safe_int("invalid", 587) == 587
    assert _safe_int("465", 587) == 465
    assert _safe_int("3.0", 1) == 3
    assert _safe_int("14.0", 7) == 14

    assert _safe_float("", 9.5) == 9.5
    assert _safe_float("   ", 9.5) == 9.5
    assert _safe_float(None, 9.5) == 9.5
    assert _safe_float("invalid", 9.5) == 9.5
    assert _safe_float("8.0", 9.5) == 8.0


def test_main_cli_safe_int_arg():
    from src.main import _safe_int_arg
    import pytest
    import argparse

    assert _safe_int_arg("3.0") == 3
    assert _safe_int_arg("1.0") == 1
    assert _safe_int_arg("10") == 10

    with pytest.raises(argparse.ArgumentTypeError):
        _safe_int_arg("invalid_number")


def test_config_with_empty_env_variables(monkeypatch):
    monkeypatch.setenv("SMTP_PORT", "")
    monkeypatch.setenv("GDRIVE_OUTPUT_RETENTION_DAYS", "")
    monkeypatch.setenv("VIDEO_TARGET_FPS", "")
    monkeypatch.setenv("PEERTUBE_PRIVACY_STATUS", "")
    monkeypatch.setenv("OUTRO_TAIL_DURATION", "")

    settings = get_settings()
    assert settings.smtp.port == 587
    assert settings.drive.output_retention_days == 7
    assert settings.processing.target_fps == 60
    assert settings.peertube.privacy_status == 1
    assert settings.processing.outro_tail_duration == 9.5


def test_video_processor_build_ffmpeg_command_single_pass_with_outro(tmp_path):
    vp = VideoProcessor(output_dir=tmp_path)
    input_v = tmp_path / "input.mp4"
    output_v = tmp_path / "output.mp4"
    music = tmp_path / "music.mp3"
    outro = tmp_path / "outro.mp4"

    input_v.touch()
    music.touch()
    outro.touch()

    cmd = vp.build_ffmpeg_command(
        input_video=input_v,
        output_video=output_v,
        music_file=music,
        outro_video=outro,
        ducking_db="-10dB",
        preset="ultrafast",
    )

    cmd_str = " ".join(cmd)
    assert "-filter_complex" in cmd_str
    assert "concat=n=2:v=1:a=1" in cmd_str
    assert "-map [vout]" in cmd_str
    assert "-map [aout]" in cmd_str
    assert str(outro) in cmd_str
    assert str(music) in cmd_str


def test_video_processor_build_ffmpeg_command_without_outro(tmp_path):
    vp = VideoProcessor(output_dir=tmp_path)
    input_v = tmp_path / "input.mp4"
    output_v = tmp_path / "output.mp4"
    music = tmp_path / "music.mp3"

    input_v.touch()
    music.touch()

    cmd = vp.build_ffmpeg_command(
        input_video=input_v,
        output_video=output_v,
        music_file=music,
        outro_video=None,
    )

    cmd_str = " ".join(cmd)
    assert "-filter_complex" in cmd_str
    assert "concat=n=2" not in cmd_str
    assert str(music) in cmd_str


def test_video_processor_mute_raw_audio(tmp_path):
    vp = VideoProcessor(output_dir=tmp_path)
    input_v = tmp_path / "input.mp4"
    output_v = tmp_path / "output.mp4"
    music = tmp_path / "music.mp3"

    input_v.touch()
    music.touch()

    # Mute raw audio enabled (clean isolated music stream)
    cmd_muted = vp.build_ffmpeg_command(
        input_video=input_v,
        output_video=output_v,
        music_file=music,
        mute_raw_audio=True,
    )
    cmd_str_muted = " ".join(cmd_muted)
    assert "[1:a]volume=0dB" in cmd_str_muted
    assert "amix" not in cmd_str_muted

    # Mute raw audio disabled (mixed audio)
    cmd_unmuted = vp.build_ffmpeg_command(
        input_video=input_v,
        output_video=output_v,
        music_file=music,
        mute_raw_audio=False,
    )
    cmd_str_unmuted = " ".join(cmd_unmuted)
    assert "amix=inputs=2" in cmd_str_unmuted


def test_youtube_client_clean_description():
    from src.publisher.youtube_client import YouTubeClient

    client = YouTubeClient()
    meta = client.generate_metadata(
        video_title="Bunker Alfa Infiltration",
        events=[],
        episode_number=110,
        music_track=[{"title": "Bossa Antigua"}, {"title": "Sneaky Snitch"}],
    )

    desc = meta.description
    assert "MUSIC & AUDIO LICENSING ATTRIBUTION" not in desc
    assert "Kevin MacLeod (incompetech.com)" not in desc
    assert "COPYRIGHT & FAIR USE DISCLAIMER" not in desc
    assert "Kefir Games" not in desc
    assert "TIMESTAMPS & CHAPTERS:" in desc


def test_drive_client_deduplication_against_history(tmp_path, monkeypatch):
    from unittest.mock import MagicMock
    from src.ingestion.drive_client import GoogleDriveClient
    from src.storage.history_tracker import HistoryTracker

    history_file = tmp_path / "history.json"
    tracker = HistoryTracker(history_file=history_file)
    tracker.record_job(
        job_id="job_test_01",
        input_filename="old_video.mp4",
        output_filename="old_video_processed.mp4",
        status="SUCCESS",
        youtube_url="https://youtu.be/test123",
        md5_checksum="md5_old_123",
    )

    client = GoogleDriveClient(input_folder_name="Input", processed_folder_name="Processed")
    client.input_folder_id = "folder_in"
    client.processed_folder_id = "folder_proc"
    client.service = MagicMock()

    mock_input_files = [
        {"id": "file_old", "name": "old_video.mp4", "size": "10000000", "mimeType": "video/mp4", "md5Checksum": "md5_old_123"},
        {"id": "file_new", "name": "new_video.mp4", "size": "20000000", "mimeType": "video/mp4", "md5Checksum": "md5_new_456"},
    ]
    mock_proc_files = []

    def mock_list(q, **kwargs):
        mock_req = MagicMock()
        if "folder_in" in q:
            mock_req.execute.return_value = {"files": mock_input_files}
        else:
            mock_req.execute.return_value = {"files": mock_proc_files}
        return mock_req

    client.service.files().list.side_effect = mock_list
    client.delete_video = MagicMock()

    monkeypatch.setattr(
        "src.storage.history_tracker.HistoryTracker.__init__",
        lambda self, history_file=history_file: setattr(self, "history_file", history_file) or self._ensure_file_exists()
    )

    pending = client.list_pending_videos()
    assert len(pending) == 1
    assert pending[0]["name"] == "new_video.mp4"
    client.delete_video.assert_called_once_with("file_old")


def test_parse_recording_timestamp():
    from src.ingestion.drive_client import parse_recording_timestamp
    from datetime import datetime

    # iOS space format
    dt1 = parse_recording_timestamp("ScreenRecording_11-05-2026 12-13-57_1.mp4")
    assert dt1 == datetime(2026, 11, 5, 12, 13, 57)

    # iOS underscore format
    dt2 = parse_recording_timestamp("ScreenRecording_09-23-2026_12-53-25_1.mp4")
    assert dt2 == datetime(2026, 9, 23, 12, 53, 25)

    # ISO format
    dt3 = parse_recording_timestamp("ScreenRecording_2026-11-08 15-30-00.mp4")
    assert dt3 == datetime(2026, 11, 8, 15, 30, 0)

    # Single-digit month and day
    dt4 = parse_recording_timestamp("ScreenRecording_5-8-2026 09-05-02.mp4")
    assert dt4 == datetime(2026, 5, 8, 9, 5, 2)

    # Compact format
    dt5 = parse_recording_timestamp("Record_20261105_121357.mp4")
    assert dt5 == datetime(2026, 11, 5, 12, 13, 57)

    # Unix epoch format
    dt6 = parse_recording_timestamp("RPReplay_Final1731580000.mp4")
    assert dt6 is not None

    # Unknown format fallback
    dt_none = parse_recording_timestamp("custom_video_without_date.mp4")
    assert dt_none is None


def test_drive_client_backfill_historical_priority(tmp_path, monkeypatch):
    """Verifies that an older video entered at any time immediately takes head of queue."""
    from unittest.mock import MagicMock
    from src.ingestion.drive_client import GoogleDriveClient
    from src.storage.history_tracker import HistoryTracker

    history_file = tmp_path / "history.json"
    tracker = HistoryTracker(history_file=history_file)

    client = GoogleDriveClient(input_folder_name="Input", processed_folder_name="Processed")
    client.input_folder_id = "folder_in"
    client.processed_folder_id = "folder_proc"
    client.service = MagicMock()

    # User uploads an older Nov 5 video after Nov 11, 13, 14 videos already exist in Input
    mock_input_files = [
        {"id": "vid_nov14", "name": "ScreenRecording_11-14-2026 13-00-00_1.mp4", "size": "10000000", "mimeType": "video/mp4", "md5Checksum": "md5_14"},
        {"id": "vid_nov11", "name": "ScreenRecording_11-11-2026 18-00-00_1.mp4", "size": "10000000", "mimeType": "video/mp4", "md5Checksum": "md5_11"},
        {"id": "vid_nov05_backfilled", "name": "ScreenRecording_11-05-2026 12-13-57_1.mp4", "size": "10000000", "mimeType": "video/mp4", "md5Checksum": "md5_05"},
    ]

    def mock_list(q, **kwargs):
        mock_req = MagicMock()
        if "folder_in" in q:
            mock_req.execute.return_value = {"files": mock_input_files}
        else:
            mock_req.execute.return_value = {"files": []}
        return mock_req

    client.service.files().list.side_effect = mock_list
    client.delete_video = MagicMock()

    monkeypatch.setattr(
        "src.storage.history_tracker.HistoryTracker.__init__",
        lambda self, history_file=history_file: setattr(self, "history_file", history_file) or self._ensure_file_exists()
    )

    pending = client.list_pending_videos()
    assert len(pending) == 3
    # The backfilled Nov 5 video MUST immediately be the first video in the queue
    assert pending[0]["name"] == "ScreenRecording_11-05-2026 12-13-57_1.mp4"
    assert pending[0]["id"] == "vid_nov05_backfilled"
    assert pending[1]["name"] == "ScreenRecording_11-11-2026 18-00-00_1.mp4"
    assert pending[2]["name"] == "ScreenRecording_11-14-2026 13-00-00_1.mp4"


def test_drive_client_chronological_sorting(tmp_path, monkeypatch):
    from unittest.mock import MagicMock
    from src.ingestion.drive_client import GoogleDriveClient
    from src.storage.history_tracker import HistoryTracker

    history_file = tmp_path / "history.json"
    tracker = HistoryTracker(history_file=history_file)

    client = GoogleDriveClient(input_folder_name="Input", processed_folder_name="Processed")
    client.input_folder_id = "folder_in"
    client.processed_folder_id = "folder_proc"
    client.service = MagicMock()

    # Out-of-order uploaded files
    mock_input_files = [
        {"id": "f3", "name": "ScreenRecording_11-14-2026 10-00-00_1.mp4", "size": "10000000", "mimeType": "video/mp4", "md5Checksum": "md5_3"},
        {"id": "f1", "name": "ScreenRecording_11-05-2026 12-00-00_1.mp4", "size": "10000000", "mimeType": "video/mp4", "md5Checksum": "md5_1"},
        {"id": "f2", "name": "ScreenRecording_11-08-2026 15-00-00_1.mp4", "size": "10000000", "mimeType": "video/mp4", "md5Checksum": "md5_2"},
    ]

    def mock_list(q, **kwargs):
        mock_req = MagicMock()
        if "folder_in" in q:
            mock_req.execute.return_value = {"files": mock_input_files}
        else:
            mock_req.execute.return_value = {"files": []}
        return mock_req

    client.service.files().list.side_effect = mock_list
    client.delete_video = MagicMock()

    monkeypatch.setattr(
        "src.storage.history_tracker.HistoryTracker.__init__",
        lambda self, history_file=history_file: setattr(self, "history_file", history_file) or self._ensure_file_exists()
    )

    pending = client.list_pending_videos()
    assert len(pending) == 3
    # Check strict chronological order
    assert pending[0]["name"] == "ScreenRecording_11-05-2026 12-00-00_1.mp4"
    assert pending[1]["name"] == "ScreenRecording_11-08-2026 15-00-00_1.mp4"
    assert pending[2]["name"] == "ScreenRecording_11-14-2026 10-00-00_1.mp4"


