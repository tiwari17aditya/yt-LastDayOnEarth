"""Unit tests for GrowthTracker YouTube platform reach and audience engagement monitoring."""

import json
import pytest
from unittest.mock import MagicMock
from pathlib import Path

from src.monitor.growth_tracker import GrowthTracker, GrowthTrackingError


def test_growth_tracker_fetch_channel_overview_success():
    tracker = GrowthTracker()
    mock_yt = MagicMock()

    mock_resp = {
        "items": [
            {
                "id": "UC_TEST_123",
                "snippet": {"title": "Last Day on Earth Official"},
                "statistics": {
                    "subscriberCount": "1250",
                    "viewCount": "45000",
                    "videoCount": "42",
                },
            }
        ]
    }
    mock_yt.channels().list().execute.return_value = mock_resp

    metrics = tracker.fetch_channel_overview(youtube=mock_yt)
    assert metrics.channel_id == "UC_TEST_123"
    assert metrics.channel_title == "Last Day on Earth Official"
    assert metrics.subscriber_count == 1250
    assert metrics.total_views == 45000
    assert metrics.video_count == 42


def test_growth_tracker_fetch_channel_overview_no_channel():
    tracker = GrowthTracker()
    mock_yt = MagicMock()
    mock_yt.channels().list().execute.return_value = {"items": []}

    with pytest.raises(GrowthTrackingError) as exc_info:
        tracker.fetch_channel_overview(youtube=mock_yt)
    assert "No channel found" in str(exc_info.value)


def test_growth_tracker_fetch_series_metrics(tmp_path):
    series_file = tmp_path / "series_tracker.json"
    series_file.write_text(
        json.dumps({
            "completed_episodes": [
                {"episode": 1, "video_id": "vid_001"},
                {"episode": 2, "video_id": "vid_002"},
            ]
        }),
        encoding="utf-8"
    )

    tracker = GrowthTracker(series_tracker_file=str(series_file))
    mock_yt = MagicMock()

    mock_resp = {
        "items": [
            {
                "id": "vid_001",
                "snippet": {"title": "LDoE Episode 1", "publishedAt": "2026-09-01T00:00:00Z"},
                "statistics": {"viewCount": "100", "likeCount": "10", "commentCount": "5"},
            },
            {
                "id": "vid_002",
                "snippet": {"title": "LDoE Episode 2", "publishedAt": "2026-09-02T00:00:00Z"},
                "statistics": {"viewCount": "200", "likeCount": "25", "commentCount": "15"},
            },
        ]
    }
    mock_yt.videos().list().execute.return_value = mock_resp

    metrics = tracker.fetch_series_metrics(youtube=mock_yt)
    assert len(metrics) == 2
    # Sorted by view_count descending -> vid_002 (200 views) comes first
    assert metrics[0].video_id == "vid_002"
    assert metrics[0].view_count == 200
    assert metrics[0].like_count == 25
    assert metrics[0].comment_count == 15
    # (25 + 15) / 200 * 100 = 20.0%
    assert metrics[0].engagement_rate == 20.0
    assert metrics[0].episode_number == 2


def test_growth_tracker_fetch_recent_comments():
    tracker = GrowthTracker()
    mock_yt = MagicMock()

    mock_resp = {
        "items": [
            {
                "id": "comment_1",
                "snippet": {
                    "videoId": "vid_001",
                    "totalReplyCount": 0,
                    "topLevelComment": {
                        "snippet": {
                            "authorDisplayName": "Gamer123",
                            "textDisplay": "Awesome base layout!",
                            "likeCount": 3,
                            "publishedAt": "2026-09-20T12:00:00Z",
                        }
                    },
                },
            },
            {
                "id": "comment_2",
                "snippet": {
                    "videoId": "vid_001",
                    "totalReplyCount": 2,
                    "topLevelComment": {
                        "snippet": {
                            "authorDisplayName": "SurvivalPro",
                            "textDisplay": "How did you find iron?",
                            "likeCount": 1,
                            "publishedAt": "2026-09-21T14:00:00Z",
                        }
                    },
                },
            },
        ]
    }
    mock_yt.commentThreads().list().execute.return_value = mock_resp

    comments = tracker.fetch_recent_comments(video_ids=["vid_001"], limit=5, youtube=mock_yt)
    assert len(comments) == 2
    assert comments[0].author == "SurvivalPro"
    assert comments[0].reply_count == 2
    assert comments[0].is_unanswered is False
    assert comments[1].author == "Gamer123"
    assert comments[1].is_unanswered is True


def test_growth_tracker_record_snapshot_delta(tmp_path):
    history_file = tmp_path / "growth_history.json"
    history_file.write_text(
        json.dumps([
            {
                "timestamp": "2026-09-25T00:00:00Z",
                "channel": {"subscriber_count": 30},
                "total_series_views": 10,
                "total_series_likes": 2,
                "total_series_comments": 1,
            }
        ]),
        encoding="utf-8"
    )

    tracker = GrowthTracker(history_file=str(history_file))
    mock_yt = MagicMock()

    # Channel returns 35 subs (gain of 5)
    mock_yt.channels().list().execute.return_value = {
        "items": [
            {
                "id": "UC_TEST",
                "snippet": {"title": "Last Day on Earth Official"},
                "statistics": {"subscriberCount": "35", "viewCount": "500", "videoCount": "10"},
            }
        ]
    }
    # Video returns 25 views (gain of 15), 5 likes (gain of 3), 2 comments (gain of 1)
    mock_yt.videos().list().execute.return_value = {
        "items": [
            {
                "id": "vid_001",
                "snippet": {"title": "Test Ep", "publishedAt": "2026-09-26T00:00:00Z"},
                "statistics": {"viewCount": "25", "likeCount": "5", "commentCount": "2"},
            }
        ]
    }

    snap = tracker.record_snapshot(youtube=mock_yt)
    assert snap.delta_subscribers == 5
    assert snap.delta_views == 15
    assert snap.delta_likes == 3
    assert snap.delta_comments == 1

    # Verify history file has 2 entries now
    data = json.loads(history_file.read_text(encoding="utf-8"))
    assert len(data) == 2
    assert data[-1]["delta_subscribers"] == 5


def test_growth_tracker_generate_growth_report(tmp_path):
    tracker = GrowthTracker(history_file=str(tmp_path / "growth_history.json"))
    mock_yt = MagicMock()

    mock_yt.channels().list().execute.return_value = {
        "items": [
            {
                "id": "UC_TEST",
                "snippet": {"title": "Last Day on Earth Official"},
                "statistics": {"subscriberCount": "40", "viewCount": "1000", "videoCount": "12"},
            }
        ]
    }
    mock_yt.videos().list().execute.return_value = {"items": []}
    mock_yt.commentThreads().list().execute.return_value = {"items": []}

    report = tracker.generate_growth_report(youtube=mock_yt)
    assert "Last Day on Earth: Survival" in report
    assert "Executive Series Growth Overview" in report
    assert "Tactical Reach & Subscriber Acceleration Directives" in report
