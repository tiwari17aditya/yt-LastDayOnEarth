"""Unit tests for Google Drive client strict path boundaries and operations."""

import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path
from datetime import datetime
from src.ingestion.drive_client import GoogleDriveClient
from src.exceptions import IngestionError


@pytest.fixture
def mock_drive_service():
    """Mock Google Drive v3 API service."""
    service = MagicMock()
    return service


def test_drive_client_fails_if_parent_folder_missing(mock_drive_service):
    """Client must fail safely if 'youtube-projects' does not exist in Drive root."""
    client = GoogleDriveClient()
    client.service = mock_drive_service

    # Simulate empty response for 'youtube-projects'
    mock_drive_service.files().list().execute.return_value = {"files": []}

    with pytest.raises(IngestionError) as exc_info:
        client._resolve_safety_folders()

    assert "youtube-projects" in str(exc_info.value)
    assert exc_info.value.operation == "resolve_folders"


def test_drive_client_fails_if_project_folder_missing(mock_drive_service):
    """Client must fail safely if 'LastDayOnEarth' does not exist inside 'youtube-projects'."""
    client = GoogleDriveClient()
    client.service = mock_drive_service

    # First call returns 'youtube-projects', second call returns empty for 'LastDayOnEarth'
    mock_drive_service.files().list().execute.side_effect = [
        {"files": [{"id": "yt_projects_123", "name": "youtube-projects"}]},
        {"files": []},
    ]

    with pytest.raises(IngestionError) as exc_info:
        client._resolve_safety_folders()

    assert "LastDayOnEarth" in str(exc_info.value)


def test_drive_client_resolves_safety_folders_successfully(mock_drive_service):
    """Client strictly binds to input, processed, and output folder IDs inside LastDayOnEarth."""
    client = GoogleDriveClient()
    client.service = mock_drive_service

    mock_drive_service.files().list().execute.side_effect = [
        {"files": [{"id": "parent_id", "name": "youtube-projects"}]},
        {"files": [{"id": "project_id", "name": "LastDayOnEarth"}]},
        {"files": [{"id": "input_id", "name": "Input"}]},
        {"files": [{"id": "processed_id", "name": "Processed"}]},
        {"files": [{"id": "output_id", "name": "Output"}]},
    ]

    client._resolve_safety_folders()

    assert client.project_root_id == "project_id"
    assert client.input_folder_id == "input_id"
    assert client.processed_folder_id == "processed_id"
    assert client.output_folder_id == "output_id"


def test_list_pending_videos_filters_videos_only(mock_drive_service):
    """Ensure non-video files (.txt, .json) are excluded from pending list."""
    client = GoogleDriveClient()
    client.service = mock_drive_service
    client.input_folder_id = "input_123"

    mock_drive_service.files().list().execute.return_value = {
        "files": [
            {"id": "v1", "name": "recording_1.mp4", "size": "10485760", "mimeType": "video/mp4", "createdTime": "2026-09-23T10:00:00Z"},
            {"id": "doc1", "name": "notes.txt", "size": "500", "mimeType": "text/plain", "createdTime": "2026-09-23T10:01:00Z"},
            {"id": "v2", "name": "clip_2.mov", "size": "20971520", "mimeType": "video/quicktime", "createdTime": "2026-09-23T10:02:00Z"},
        ]
    }

    pending = client.list_pending_videos()
    assert len(pending) == 2
    assert pending[0]["name"] == "recording_1.mp4"
    assert pending[1]["name"] == "clip_2.mov"


def test_mark_as_processed_moves_file(mock_drive_service):
    """Ensure mark_as_processed updates parents in Google Drive API."""
    client = GoogleDriveClient()
    client.service = mock_drive_service
    client.input_folder_id = "input_123"
    client.processed_folder_id = "processed_456"

    client.mark_as_processed("video_999")

    mock_drive_service.files().update.assert_called_once_with(
        fileId="video_999",
        addParents="processed_456",
        removeParents="input_123",
        fields="id, parents",
    )


def test_upload_processed_video_year_month_structure(mock_drive_service, tmp_path):
    """Ensure upload_processed_video organizes Output -> (videos & metadata) -> Year -> Month."""
    client = GoogleDriveClient()
    client.service = mock_drive_service
    client.output_folder_id = "output_root"

    # Create dummy local files
    dummy_video = tmp_path / "test_video.mp4"
    dummy_video.write_bytes(b"dummy_video_bytes")
    dummy_meta = tmp_path / "test_video_metadata.json"
    dummy_meta.write_text('{"title": "Test"}')

    # Mock folder listing for videos, year, month, metadata, year, month
    mock_drive_service.files().list().execute.side_effect = [
        {"files": [{"id": "videos_root_id", "name": "videos"}]},
        {"files": [{"id": "vid_year_id", "name": "2026"}]},
        {"files": [{"id": "vid_month_id", "name": "09"}]},
        {"files": [{"id": "metadata_root_id", "name": "metadata"}]},
        {"files": [{"id": "meta_year_id", "name": "2026"}]},
        {"files": [{"id": "meta_month_id", "name": "09"}]},
    ]

    # Mock chunked upload create request for video
    mock_video_req = MagicMock()
    mock_video_req.next_chunk.return_value = (None, {"id": "uploaded_vid_id", "name": "video_23092026.mp4"})
    
    # Mock metadata create request
    mock_meta_req = MagicMock()
    mock_meta_req.execute.return_value = {"id": "uploaded_meta_id", "name": "metadata_23092026.json"}

    mock_drive_service.files().create.side_effect = [mock_video_req, mock_meta_req]

    test_date = datetime(2026, 9, 23, 12, 0, 0)
    result = client.upload_processed_video(
        local_video_path=dummy_video,
        metadata_path=dummy_meta,
        processing_date=test_date,
    )

    assert result["video_id"] == "uploaded_vid_id"
    assert result["video_name"] == "video_23092026.mp4"
    assert result["video_folder"] == "Output/videos/2026/09"
    assert result["metadata_id"] == "uploaded_meta_id"
    assert result["metadata_folder"] == "Output/metadata/2026/09"


def test_delete_video_permanent_success(mock_drive_service):
    """Test successful permanent deletion of a video file."""
    client = GoogleDriveClient()
    client.service = mock_drive_service

    client.delete_video("file_xyz_123")
    mock_drive_service.files().delete.assert_called_once_with(fileId="file_xyz_123")


def test_delete_video_fallback_to_trash(mock_drive_service):
    """Test fallback to trash when permanent delete raises an exception."""
    client = GoogleDriveClient()
    client.service = mock_drive_service

    files_mock = MagicMock()
    mock_drive_service.files.return_value = files_mock
    files_mock.delete.return_value.execute.side_effect = Exception("Permission denied for delete")
    files_mock.update.return_value.execute.return_value = {"id": "file_xyz_123", "trashed": True}

    client.delete_video("file_xyz_123")
    files_mock.update.assert_called_once_with(fileId="file_xyz_123", body={"trashed": True})


def test_delete_video_fails_when_both_fail(mock_drive_service):
    """Test that IngestionError is raised when both permanent delete and trash fail."""
    client = GoogleDriveClient()
    client.service = mock_drive_service

    files_mock = MagicMock()
    mock_drive_service.files.return_value = files_mock
    files_mock.delete.return_value.execute.side_effect = Exception("Delete failed")
    files_mock.update.return_value.execute.side_effect = Exception("Trash failed")

    with pytest.raises(IngestionError) as exc_info:
        client.delete_video("file_xyz_123")

    assert exc_info.value.operation == "delete_video"


def test_cleanup_processed_folder(mock_drive_service):
    """Test purging all files from Drive Processed folder."""
    client = GoogleDriveClient()
    client.service = mock_drive_service
    client.processed_folder_id = "proc_123"

    mock_drive_service.files().list().execute.return_value = {
        "files": [
            {"id": "p1", "name": "processed_video_1.mp4", "mimeType": "video/mp4"},
            {"id": "p2", "name": "processed_video_2.mp4", "mimeType": "video/mp4"},
        ]
    }

    with patch.object(client, "delete_video") as mock_delete:
        deleted = client.cleanup_processed_folder()
        assert deleted == 2
        assert mock_delete.call_count == 2
        mock_delete.assert_any_call("p1")
        mock_delete.assert_any_call("p2")


def test_cleanup_old_output_videos(mock_drive_service):
    """Test deleting output videos older than 7 days while preserving newer videos."""
    from datetime import datetime, timezone, timedelta

    client = GoogleDriveClient()
    client.service = mock_drive_service
    client.output_folder_id = "out_root"

    # Mock finding 'videos' folder in output_folder_id
    # Call 1: _find_single_folder("videos", parent_id="out_root")
    # Call 2: list year folders
    # Call 3: list month folders
    # Call 4: list files in month folder
    # Call 5: scan videos_root
    # Call 6: scan output_folder_id root
    old_time = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat().replace("+00:00", "Z")
    new_time = (datetime.now(timezone.utc) - timedelta(days=2)).isoformat().replace("+00:00", "Z")
    old_name = f"video_{(datetime.now(timezone.utc) - timedelta(days=10)).strftime('%d%m%Y')}.mp4"
    new_name = f"video_{(datetime.now(timezone.utc) - timedelta(days=2)).strftime('%d%m%Y')}.mp4"

    mock_drive_service.files().list().execute.side_effect = [
        # _find_single_folder("videos")
        {"files": [{"id": "vid_root_id", "name": "videos"}]},
        # Year folders
        {"files": [{"id": "year_2026", "name": "2026"}]},
        # Month folders
        {"files": [{"id": "month_09", "name": "09"}]},
        # Files in month folder: 1 old, 1 new
        {"files": [
            {"id": "old_vid_1", "name": old_name, "mimeType": "video/mp4", "createdTime": old_time},
            {"id": "new_vid_2", "name": new_name, "mimeType": "video/mp4", "createdTime": new_time},
        ]},
        # Scan vid_root_id directly
        {"files": []},
        # Scan out_root directly
        {"files": []},
    ]

    with patch.object(client, "delete_video") as mock_delete:
        deleted = client.cleanup_old_output_videos(retention_days=7)
        assert deleted == 1
        mock_delete.assert_called_once_with("old_vid_1")

