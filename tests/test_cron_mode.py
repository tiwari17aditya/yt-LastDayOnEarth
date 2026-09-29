"""Unit tests for scheduled drive-cron orchestrator logic."""

import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path
from src.main import run_drive_cron


@patch("src.main.GoogleDriveClient")
def test_drive_cron_exits_zero_when_no_videos(mock_drive_cls):
    """When Drive Input has no pending videos, drive-cron must exit cleanly with code 0."""
    mock_instance = MagicMock()
    mock_instance.list_pending_videos.return_value = []
    mock_drive_cls.return_value = mock_instance

    exit_code = run_drive_cron(dry_run=False, limit=1)
    assert exit_code == 0
    mock_instance.connect.assert_called_once()
    mock_instance.list_pending_videos.assert_called_once()


@patch("src.main.GoogleDriveClient")
def test_drive_cron_dry_run_does_not_download(mock_drive_cls):
    """In dry-run mode, pending videos are listed but not downloaded or marked processed."""
    mock_instance = MagicMock()
    mock_instance.list_pending_videos.return_value = [
        {"id": "vid1", "name": "sample.mp4", "size": 1000000}
    ]
    mock_drive_cls.return_value = mock_instance

    exit_code = run_drive_cron(dry_run=True, limit=1)
    assert exit_code == 0
    mock_instance.download_video.assert_not_called()
    mock_instance.mark_as_processed.assert_not_called()


@patch("src.main.run_pipeline")
@patch("src.main.GoogleDriveClient")
def test_drive_cron_preserves_input_video_when_upload_false(mock_drive_cls, mock_pipeline, tmp_path):
    """When upload=False, the raw video MUST NOT be deleted from Google Drive Input."""
    mock_instance = MagicMock()
    mock_instance.list_pending_videos.return_value = [
        {"id": "drive_vid_123", "name": "gameplay.mp4", "size": 1024}
    ]
    mock_drive_cls.return_value = mock_instance

    from src.main import RenderResult
    dummy_render = RenderResult(tmp_path / "gameplay_Processed.mp4")
    dummy_render.touch()
    dummy_render.uploaded_to_youtube = False
    dummy_render.youtube_url = "N/A (Local execution)"
    mock_pipeline.return_value = dummy_render

    exit_code = run_drive_cron(dry_run=False, limit=1, upload=False)
    assert exit_code == 0
    mock_instance.delete_video.assert_not_called()


@patch("src.main.run_pipeline")
@patch("src.main.GoogleDriveClient")
def test_drive_cron_preserves_input_video_when_pipeline_errors(mock_drive_cls, mock_pipeline):
    """When pipeline fails, the raw video MUST NOT be deleted from Google Drive Input."""
    mock_instance = MagicMock()
    mock_instance.list_pending_videos.return_value = [
        {"id": "drive_vid_999", "name": "failed.mp4", "size": 1024}
    ]
    mock_drive_cls.return_value = mock_instance
    mock_pipeline.side_effect = RuntimeError("YouTube quota exceeded or processing crashed")

    exit_code = run_drive_cron(dry_run=False, limit=1, upload=True)
    assert exit_code == 1
    mock_instance.delete_video.assert_not_called()


@patch("src.main.run_pipeline")
@patch("src.main.GoogleDriveClient")
def test_drive_cron_preserves_input_video_when_youtube_upload_not_confirmed(mock_drive_cls, mock_pipeline, tmp_path):
    """When YouTube upload cannot be verified, the raw video MUST NOT be deleted from Drive Input."""
    mock_instance = MagicMock()
    mock_instance.list_pending_videos.return_value = [
        {"id": "drive_vid_456", "name": "unconfirmed.mp4", "size": 1024}
    ]
    mock_drive_cls.return_value = mock_instance

    from src.main import RenderResult
    dummy_render = RenderResult(tmp_path / "gameplay_Processed.mp4")
    dummy_render.touch()
    dummy_render.uploaded_to_youtube = False
    mock_pipeline.return_value = dummy_render

    exit_code = run_drive_cron(dry_run=False, limit=1, upload=True)
    assert exit_code == 0
    mock_instance.delete_video.assert_not_called()


@patch("src.main.run_pipeline")
@patch("src.main.GoogleDriveClient")
def test_drive_cron_deletes_input_video_only_after_youtube_upload_confirmed(mock_drive_cls, mock_pipeline, tmp_path):
    """When video is confirmed uploaded to YouTube, the raw video IS deleted from Drive Input."""
    mock_instance = MagicMock()
    mock_instance.list_pending_videos.return_value = [
        {"id": "drive_vid_777", "name": "success.mp4", "size": 1024}
    ]
    mock_drive_cls.return_value = mock_instance

    from src.main import RenderResult
    dummy_render = RenderResult(tmp_path / "gameplay_Processed.mp4")
    dummy_render.touch()
    dummy_render.uploaded_to_youtube = True
    dummy_render.youtube_url = "https://youtu.be/real_vid_123"
    dummy_render.video_id = "real_vid_123"
    mock_pipeline.return_value = dummy_render

    exit_code = run_drive_cron(dry_run=False, limit=1, upload=True)
    assert exit_code == 0
    mock_instance.delete_video.assert_called_once_with("drive_vid_777")

