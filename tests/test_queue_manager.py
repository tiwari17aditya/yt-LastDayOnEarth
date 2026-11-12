"""Unit tests for the PublishingQueueManager and scheduled YouTube release pipeline."""

import json
from datetime import datetime, timezone, time, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
try:
    from zoneinfo import ZoneInfo
    IST = ZoneInfo("Asia/Kolkata")
except Exception:
    IST = timezone(timedelta(hours=5, minutes=30))

from src.publisher.queue_manager import PublishingQueueManager, PublishingQueueItem
from src.publisher.youtube_client import YouTubeClient, VideoPublishMetadata
from src.publisher.multi_publisher import MultiPlatformPublisher


@pytest.fixture
def temp_queue_file(tmp_path):
    """Provides a temporary queue file path."""
    return tmp_path / "test_publishing_queue.json"


def test_queue_manager_init_and_file_creation(temp_queue_file):
    """Test that queue manager initializes and creates schema when file does not exist."""
    assert not temp_queue_file.exists()
    mgr = PublishingQueueManager(queue_file=temp_queue_file)
    assert temp_queue_file.exists()
    items = mgr.load_queue()
    assert items == []
    summary = mgr.format_queue_summary()
    assert "empty" in summary.lower()


def test_weekday_slot_calculation(temp_queue_file):
    """Test slot calculation on weekdays (Mon-Fri) allocates 15:00 and 19:00 IST."""
    mgr = PublishingQueueManager(queue_file=temp_queue_file, min_lead_time_minutes=10)
    
    # Wednesday 10:00 AM IST (04:30 UTC)
    wed_morning = datetime(2026, 11, 11, 4, 30, tzinfo=timezone.utc)
    slot1 = mgr.get_next_slot(reference_time=wed_morning)
    slot1_ist = slot1.astimezone(IST)
    
    assert slot1_ist.hour == 15
    assert slot1_ist.minute == 0
    assert slot1_ist.day == 11
    
    mgr.add_scheduled_video("v1", "Ep 1", 1, slot1)
    
    # Next slot should be Wednesday 19:00 IST
    slot2 = mgr.get_next_slot(reference_time=wed_morning)
    slot2_ist = slot2.astimezone(IST)
    assert slot2_ist.hour == 19
    assert slot2_ist.minute == 0
    assert slot2_ist.day == 11
    
    mgr.add_scheduled_video("v2", "Ep 2", 2, slot2)
    
    # Next slot should be Thursday 15:00 IST
    slot3 = mgr.get_next_slot(reference_time=wed_morning)
    slot3_ist = slot3.astimezone(IST)
    assert slot3_ist.hour == 15
    assert slot3_ist.minute == 0
    assert slot3_ist.day == 12


def test_weekend_slot_calculation(temp_queue_file):
    """Test slot calculation on weekends allocates 3 slots: 11:00, 16:00, 20:00 IST."""
    mgr = PublishingQueueManager(queue_file=temp_queue_file, min_lead_time_minutes=10)
    
    # Saturday 08:00 AM IST (02:30 UTC)
    sat_morning = datetime(2026, 11, 14, 2, 30, tzinfo=timezone.utc)
    
    # Slot 1: Saturday 11:00 AM IST
    slot1 = mgr.get_next_slot(reference_time=sat_morning)
    slot1_ist = slot1.astimezone(IST)
    assert slot1_ist.hour == 11
    assert slot1_ist.minute == 0
    assert slot1_ist.weekday() == 5  # Saturday
    mgr.add_scheduled_video("v1", "Ep 1", 1, slot1)
    
    # Slot 2: Saturday 04:00 PM (16:00) IST
    slot2 = mgr.get_next_slot(reference_time=sat_morning)
    slot2_ist = slot2.astimezone(IST)
    assert slot2_ist.hour == 16
    assert slot2_ist.minute == 0
    mgr.add_scheduled_video("v2", "Ep 2", 2, slot2)
    
    # Slot 3: Saturday 08:00 PM (20:00) IST
    slot3 = mgr.get_next_slot(reference_time=sat_morning)
    slot3_ist = slot3.astimezone(IST)
    assert slot3_ist.hour == 20
    assert slot3_ist.minute == 0
    mgr.add_scheduled_video("v3", "Ep 3", 3, slot3)
    
    # Slot 4: Sunday 11:00 AM IST
    slot4 = mgr.get_next_slot(reference_time=sat_morning)
    slot4_ist = slot4.astimezone(IST)
    assert slot4_ist.hour == 11
    assert slot4_ist.minute == 0
    assert slot4_ist.weekday() == 6  # Sunday


def test_sequential_slots_for_batch(temp_queue_file):
    """Verify queueing 8 videos in a batch spreads them sequentially across days."""
    mgr = PublishingQueueManager(queue_file=temp_queue_file, min_lead_time_minutes=10)
    
    start_time = datetime(2026, 11, 11, 4, 30, tzinfo=timezone.utc)  # Wednesday morning
    for i in range(1, 9):
        slot = mgr.get_next_slot(reference_time=start_time)
        mgr.add_scheduled_video(f"vid_{i}", f"Episode #{i}", i, slot)
    
    items = mgr.load_queue()
    assert len(items) == 8
    
    # Episodes should be in strictly increasing chronological order
    times = [datetime.fromisoformat(it.scheduled_publish_time_utc.replace("Z", "+00:00")) for it in items]
    for idx in range(len(times) - 1):
        assert times[idx] < times[idx + 1]


def test_queue_status_sync(temp_queue_file):
    """Verify sync_queue_status transitions past releases to PUBLISHED."""
    mgr = PublishingQueueManager(queue_file=temp_queue_file)
    
    # Add one past video and one future video
    past_utc = datetime.now(timezone.utc) - timedelta(hours=2)
    future_utc = datetime.now(timezone.utc) + timedelta(hours=5)
    
    mgr.add_scheduled_video("past_vid", "Past Ep", 1, past_utc)
    mgr.add_scheduled_video("future_vid", "Future Ep", 2, future_utc)
    
    items_before = mgr.load_queue()
    assert all(it.status == "SCHEDULED" for it in items_before)
    
    # Run sync
    synced = mgr.sync_queue_status()
    past_item = next(it for it in synced if it.video_id == "past_vid")
    future_item = next(it for it in synced if it.video_id == "future_vid")
    
    assert past_item.status == "PUBLISHED"
    assert past_item.privacy_status == "public"
    assert future_item.status == "SCHEDULED"


def test_youtube_client_upload_with_publish_at(temp_queue_file, tmp_path):
    """Test YouTubeClient.upload_video formats status payload with privacyStatus='private' and publishAt."""
    dummy_video = tmp_path / "test_render.mp4"
    dummy_video.write_bytes(b"mock video data")
    
    mgr = PublishingQueueManager(queue_file=temp_queue_file)
    mock_title_mgr = MagicMock()
    mock_title_mgr.get_current_episode.return_value = 129
    yt_client = YouTubeClient(queue_manager=mgr, title_manager=mock_title_mgr)
    
    publish_at_target = "2026-11-12T09:30:00Z"
    metadata = VideoPublishMetadata(
        title="Survival Run | LDoE #128",
        description="Episode 128 description",
        tags=["ldoe", "survival"],
        category_id="20",
        privacy_status="private",
        publish_at=publish_at_target,
        episode_number=128,
    )
    
    mock_service = MagicMock()
    mock_videos = MagicMock()
    mock_insert = MagicMock()
    
    mock_service.channels().list().execute.return_value = {"items": []}
    mock_service.videos.return_value = mock_videos
    mock_videos.insert.return_value = mock_insert
    mock_insert.next_chunk.return_value = (None, {"id": "mock_vid_128"})
    mock_service.playlists().list_next.return_value = None
    mock_service.playlistItems().list_next.return_value = None
    
    with patch("src.google_auth.get_google_credentials", return_value=MagicMock()), \
         patch("googleapiclient.discovery.build", return_value=mock_service), \
         patch.object(yt_client, "get_or_create_playlist", return_value="pl_123"), \
         patch.object(yt_client, "add_video_to_playlist", return_value=True):
        
        url = yt_client.upload_video(dummy_video, metadata)
        assert url == "https://youtu.be/mock_vid_128"
        
        # Verify the insert body payload sent to YouTube
        args, kwargs = mock_videos.insert.call_args
        body = kwargs.get("body", {})
        assert body["status"]["privacyStatus"] == "private"
        assert body["status"]["publishAt"] == publish_at_target
        
        # Verify video got queued in PublishingQueueManager
        queue_items = mgr.load_queue()
        assert len(queue_items) == 1
        assert queue_items[0].video_id == "mock_vid_128"
        assert queue_items[0].episode_number == 128
        assert queue_items[0].status == "SCHEDULED"


def test_multi_publisher_defers_social_on_scheduled_video(tmp_path):
    """Test MultiPlatformPublisher defers social broadcast when publish_at is configured."""
    mock_yt = MagicMock()
    mock_yt.upload_video.return_value = "https://youtu.be/sched_vid"
    mock_broadcaster = MagicMock()
    
    publisher = MultiPlatformPublisher(
        youtube_client=mock_yt,
        fediverse_broadcaster=mock_broadcaster,
        enable_fediverse_broadcast=True,
    )
    
    dummy_video = tmp_path / "vid.mp4"
    dummy_video.write_bytes(b"data")
    
    metadata = VideoPublishMetadata(
        title="Scheduled Ep",
        description="desc",
        tags=["tag"],
        category_id="20",
        privacy_status="private",
        publish_at="2026-11-12T09:30:00Z",
    )
    
    res = publisher.publish_all(dummy_video, metadata)
    assert res.youtube_url == "https://youtu.be/sched_vid"
    
    # Broadcast should have been deferred (not called) because video is private/scheduled
    mock_broadcaster.broadcast_release.assert_not_called()
