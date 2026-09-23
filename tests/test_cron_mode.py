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
