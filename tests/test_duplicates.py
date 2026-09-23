"""Unit tests verifying duplicate detection and collision resolution across all components."""

import json
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock

from src.storage.history_tracker import HistoryTracker
from src.ingestion.drive_client import GoogleDriveClient


def test_history_tracker_is_duplicate_by_md5(tmp_path):
    history_file = tmp_path / "history.json"
    tracker = HistoryTracker(history_file=history_file)

    assert not tracker.is_duplicate("video.mp4", md5_checksum="hash123")

    tracker.record_job(
        job_id="job_1",
        input_filename="video.mp4",
        output_filename="video_Processed.mp4",
        status="SUCCESS",
        md5_checksum="hash123",
    )

    # Same MD5, different filename should be identified as duplicate
    assert tracker.is_duplicate("renamed_video.mp4", md5_checksum="hash123")

    # Different MD5, different filename should not be duplicate
    assert not tracker.is_duplicate("other_video.mp4", md5_checksum="hash999")


def test_history_tracker_is_duplicate_by_filename(tmp_path):
    history_file = tmp_path / "history.json"
    tracker = HistoryTracker(history_file=history_file)

    tracker.record_job(
        job_id="job_1",
        input_filename="recording.mp4",
        output_filename="recording_Processed.mp4",
        status="SUCCESS",
    )

    assert tracker.is_duplicate("recording.mp4")
    assert not tracker.is_duplicate("different.mp4")


def test_drive_client_skips_processed_and_twin_input_duplicates():
    """Verify that Drive client ignores duplicate files and twins, archiving them immediately."""
    client = GoogleDriveClient(input_folder_name="Input", processed_folder_name="Processed")
    mock_service = MagicMock()
    client.service = mock_service
    client.input_folder_id = "input_folder_id"
    client.processed_folder_id = "processed_folder_id"

    # 1st call: list files in Input folder
    # 3 files:
    # - vid1: MD5 "hash_already_processed" (duplicate of processed)
    # - vid2: MD5 "hash_unique_1" (unique, legitimate)
    # - vid3: MD5 "hash_unique_1" (duplicate twin of vid2)
    input_files_resp = {
        "files": [
            {"id": "file_1", "name": "vid1.mp4", "mimeType": "video/mp4", "size": 100, "md5Checksum": "hash_already_processed"},
            {"id": "file_2", "name": "vid2.mp4", "mimeType": "video/mp4", "size": 200, "md5Checksum": "hash_unique_1"},
            {"id": "file_3", "name": "vid3_twin.mp4", "mimeType": "video/mp4", "size": 200, "md5Checksum": "hash_unique_1"},
        ]
    }

    # 2nd call: list files in Processed folder
    processed_files_resp = {
        "files": [
            {"id": "proc_1", "name": "archived.mp4", "md5Checksum": "hash_already_processed"}
        ]
    }

    mock_service.files().list().execute.side_effect = [
        input_files_resp,
        processed_files_resp,
    ]

    # Mock mark_as_processed update calls
    mock_service.files().update().execute.return_value = {"id": "moved", "parents": ["processed_folder_id"]}

    pending = client.list_pending_videos()

    # Only vid2 should be returned as pending!
    assert len(pending) == 1
    assert pending[0]["id"] == "file_2"
    assert pending[0]["name"] == "vid2.mp4"

    # Both file_1 (duplicate of processed) and file_3 (duplicate twin) should be archived
    called_file_ids = [
        call.kwargs["fileId"]
        for call in mock_service.files().update.call_args_list
        if "fileId" in call.kwargs
    ]
    assert len(called_file_ids) == 2
    assert "file_1" in called_file_ids
    assert "file_3" in called_file_ids


def test_drive_client_upload_output_collision_disambiguation(tmp_path):
    """Verify that uploading to Drive auto-disambiguates if video_ddmmyyyy.mp4 already exists."""
    client = GoogleDriveClient()
    mock_service = MagicMock()
    client.service = mock_service
    client.output_folder_id = "output_root"

    dummy_video = tmp_path / "dummy.mp4"
    dummy_video.write_bytes(b"data")
    dummy_meta = tmp_path / "dummy_meta.json"
    dummy_meta.write_text('{"title": "test"}')

    # Folder hierarchy resolution:
    # 1: videos root, 2: 2026, 3: 09
    # 4: metadata root, 5: 2026, 6: 09
    # 7: list files in video_month_id -> returns existing 'video_23092026.mp4'
    mock_service.files().list().execute.side_effect = [
        {"files": [{"id": "videos_root_id", "name": "videos"}]},
        {"files": [{"id": "vid_year_id", "name": "2026"}]},
        {"files": [{"id": "vid_month_id", "name": "09"}]},
        {"files": [{"id": "metadata_root_id", "name": "metadata"}]},
        {"files": [{"id": "meta_year_id", "name": "2026"}]},
        {"files": [{"id": "meta_month_id", "name": "09"}]},
        {"files": [{"name": "video_23092026.mp4"}]}, # collision!
    ]

    mock_video_req = MagicMock()
    mock_video_req.next_chunk.return_value = (None, {"id": "uploaded_vid_id", "name": "video_23092026_1.mp4"})
    mock_meta_req = MagicMock()
    mock_meta_req.execute.return_value = {"id": "uploaded_meta_id", "name": "metadata_23092026_1.json"}

    mock_service.files().create.side_effect = [mock_video_req, mock_meta_req]

    test_date = datetime(2026, 9, 23, 12, 0, 0)
    result = client.upload_processed_video(
        local_video_path=dummy_video,
        metadata_path=dummy_meta,
        processing_date=test_date,
    )

    # Disambiguated names
    assert result["video_name"] == "video_23092026_1.mp4"
    assert result["metadata_name"] == "metadata_23092026_1.json"
