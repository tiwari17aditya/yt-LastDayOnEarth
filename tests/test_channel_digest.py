"""Unit tests for ChannelGrowthMonitor module."""

from pathlib import Path
from unittest.mock import patch, MagicMock
from src.analytics.channel_digest import ChannelGrowthMonitor


def test_channel_monitor_fetch_channel_overview():
    monitor = ChannelGrowthMonitor()
    mock_youtube = MagicMock()

    mock_youtube.channels().list().execute.return_value = {
        "items": [
            {
                "id": "UC_test_channel",
                "snippet": {"title": "LDoE Survival Official"},
                "statistics": {
                    "subscriberCount": "1500",
                    "viewCount": "45000",
                    "videoCount": "12",
                },
                "contentDetails": {
                    "relatedPlaylists": {"uploads": "UU_test_uploads"}
                },
            }
        ]
    }

    overview = monitor.fetch_channel_overview(mock_youtube)
    assert overview["channel_id"] == "UC_test_channel"
    assert overview["subscriber_count"] == 1500
    assert overview["total_views"] == 45000
    assert overview["total_videos"] == 12
    assert overview["uploads_playlist_id"] == "UU_test_uploads"


def test_channel_monitor_fetch_recent_videos():
    monitor = ChannelGrowthMonitor()
    mock_youtube = MagicMock()

    # Mock playlistItems
    mock_youtube.playlistItems().list().execute.return_value = {
        "items": [
            {"contentDetails": {"videoId": "vid_101"}},
            {"contentDetails": {"videoId": "vid_102"}},
        ]
    }

    # Mock videos list
    mock_youtube.videos().list().execute.return_value = {
        "items": [
            {
                "id": "vid_101",
                "snippet": {"title": "Base Fortification", "publishedAt": "2026-09-28T12:00:00Z"},
                "statistics": {"viewCount": "1000", "likeCount": "50", "commentCount": "10"},
            },
            {
                "id": "vid_102",
                "snippet": {"title": "Bunker Raid", "publishedAt": "2026-09-29T12:00:00Z"},
                "statistics": {"viewCount": "2000", "likeCount": "120", "commentCount": "25"},
            },
        ]
    }

    videos = monitor.fetch_recent_videos(mock_youtube, "UU_test_uploads", limit=2)
    assert len(videos) == 2
    assert videos[0]["video_id"] == "vid_101"
    assert videos[0]["like_ratio"] == 5.0
    assert videos[0]["comment_ratio"] == 1.0
    assert videos[1]["video_id"] == "vid_102"
    assert videos[1]["like_ratio"] == 6.0


def test_channel_monitor_generate_markdown_report(tmp_path):
    monitor = ChannelGrowthMonitor(reports_dir=tmp_path)
    digest = {
        "timestamp": "2026-09-29T22:00:00",
        "channel": {
            "channel_title": "LDoE Survival",
            "subscriber_count": 2500,
            "total_views": 80000,
            "total_videos": 14,
        },
        "benchmarks": {
            "channel_health": "EXCELLENT",
            "average_like_ratio": 5.5,
            "average_comment_ratio": 1.2,
        },
        "recent_videos": [
            {
                "video_id": "vid_101",
                "title": "Episode 12 - Final Defense",
                "published_at": "2026-09-29",
                "views": 1500,
                "likes": 80,
                "comments": 15,
                "like_ratio": 5.33,
                "engagement_rate": 6.33,
                "url": "https://youtu.be/vid_101",
            }
        ],
    }

    out_file = tmp_path / "test_report.md"
    report_path = monitor.generate_markdown_report(digest, output_path=out_file)

    assert report_path.exists()
    content = report_path.read_text(encoding="utf-8")
    assert "YouTube Channel Growth & Performance Digest" in content
    assert "LDoE Survival" in content
    assert "2,500" in content
    assert "EXCELLENT" in content
    assert "Episode 12 - Final Defense" in content
