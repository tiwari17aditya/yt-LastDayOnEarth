"""Unit tests for PlaylistManager module."""

from unittest.mock import MagicMock
from src.publisher.playlist_manager import PlaylistManager


def test_extract_episode_number():
    manager = PlaylistManager()
    assert manager.extract_episode_number("LDoE Survival #12") == 12
    assert manager.extract_episode_number("Episode 5: Base Prep") == 5
    assert manager.extract_episode_number("Ep. 8 Raid") == 8
    assert manager.extract_episode_number("Random Walkthrough") is None


def test_get_playlist_items():
    manager = PlaylistManager()
    mock_youtube = MagicMock()

    mock_req = MagicMock()
    mock_req.execute.return_value = {
        "items": [
            {
                "id": "item_1",
                "snippet": {
                    "title": "Episode #1 - Awakening",
                    "position": 0,
                    "resourceId": {"videoId": "vid_1"},
                },
            },
            {
                "id": "item_2",
                "snippet": {
                    "title": "Episode #2 - Crafting",
                    "position": 1,
                    "resourceId": {"videoId": "vid_2"},
                },
            },
        ]
    }
    mock_youtube.playlistItems().list.return_value = mock_req
    mock_youtube.playlistItems().list_next.return_value = None

    items = manager.get_playlist_items(mock_youtube, "PL_test")
    assert len(items) == 2
    assert items[0]["episode_number"] == 1
    assert items[0]["video_id"] == "vid_1"
    assert items[1]["episode_number"] == 2


def test_audit_playlist_identifies_chronological_and_duplicates():
    manager = PlaylistManager()
    mock_youtube = MagicMock()

    mock_req = MagicMock()
    mock_req.execute.return_value = {
        "items": [
            {
                "id": "item_1",
                "snippet": {"title": "LDoE #1", "position": 0, "resourceId": {"videoId": "vid_1"}},
            },
            {
                "id": "item_2",
                "snippet": {"title": "LDoE #2", "position": 1, "resourceId": {"videoId": "vid_2"}},
            },
            {
                "id": "item_3",
                "snippet": {"title": "LDoE #1 Duplicate", "position": 2, "resourceId": {"videoId": "vid_1"}},
            },
        ]
    }
    mock_youtube.playlistItems().list.return_value = mock_req
    mock_youtube.playlistItems().list_next.return_value = None

    audit = manager.audit_playlist(mock_youtube, "PL_test")
    assert audit["total_items"] == 3
    assert audit["unique_videos"] == 2
    assert len(audit["duplicates"]) == 1
    assert audit["duplicates"][0]["video_id"] == "vid_1"


def test_deduplicate_playlist_removes_duplicates():
    manager = PlaylistManager()
    mock_youtube = MagicMock()

    mock_req = MagicMock()
    mock_req.execute.return_value = {
        "items": [
            {"id": "item_1", "snippet": {"title": "LDoE #1", "position": 0, "resourceId": {"videoId": "vid_1"}}},
            {"id": "item_2", "snippet": {"title": "LDoE #1 Dup", "position": 1, "resourceId": {"videoId": "vid_1"}}},
        ]
    }
    mock_youtube.playlistItems().list.return_value = mock_req
    mock_youtube.playlistItems().list_next.return_value = None

    removed = manager.deduplicate_playlist(mock_youtube, "PL_test")
    assert removed == 1
    mock_youtube.playlistItems().delete.assert_called_once_with(id="item_2")
