"""Unit tests for YouTube playlist creation and video assignment."""

from unittest.mock import MagicMock
from src.publisher.youtube_client import YouTubeClient


def test_get_or_create_playlist_finds_existing():
    client = YouTubeClient()
    mock_youtube = MagicMock()

    # Mock list returning an existing playlist
    mock_list_req = MagicMock()
    mock_list_req.execute.return_value = {
        "items": [
            {"id": "existing_pl_123", "snippet": {"title": client.playlist_title}}
        ]
    }
    mock_youtube.playlists().list.return_value = mock_list_req
    mock_youtube.playlists().list_next.return_value = None

    playlist_id = client.get_or_create_playlist(mock_youtube)

    assert playlist_id == "existing_pl_123"
    mock_youtube.playlists().insert.assert_not_called()


def test_get_or_create_playlist_creates_new():
    client = YouTubeClient()
    mock_youtube = MagicMock()

    # Mock list returning empty
    mock_list_req = MagicMock()
    mock_list_req.execute.return_value = {"items": []}
    mock_youtube.playlists().list.return_value = mock_list_req
    mock_youtube.playlists().list_next.return_value = None

    # Mock insert returning new playlist id
    mock_insert_req = MagicMock()
    mock_insert_req.execute.return_value = {"id": "new_pl_456"}
    mock_youtube.playlists().insert.return_value = mock_insert_req

    playlist_id = client.get_or_create_playlist(mock_youtube, privacy_status="public")

    assert playlist_id == "new_pl_456"
    mock_youtube.playlists().insert.assert_called_once()
    call_kwargs = mock_youtube.playlists().insert.call_args[1]
    assert call_kwargs["part"] == "snippet,status"
    assert call_kwargs["body"]["snippet"]["title"] == client.playlist_title
    assert call_kwargs["body"]["status"]["privacyStatus"] == "public"


def test_add_video_to_playlist_inserts_when_not_present():
    client = YouTubeClient()
    mock_youtube = MagicMock()

    # Mock playlistItems().list returning empty
    mock_check_req = MagicMock()
    mock_check_req.execute.return_value = {"items": []}
    mock_youtube.playlistItems().list.return_value = mock_check_req
    mock_youtube.playlistItems().list_next.return_value = None

    # Mock insert
    mock_insert_req = MagicMock()
    mock_insert_req.execute.return_value = {"id": "item_789"}
    mock_youtube.playlistItems().insert.return_value = mock_insert_req

    success = client.add_video_to_playlist(mock_youtube, video_id="vid_123", playlist_id="pl_456")

    assert success is True
    mock_youtube.playlistItems().insert.assert_called_once()
    body = mock_youtube.playlistItems().insert.call_args[1]["body"]
    assert body["snippet"]["playlistId"] == "pl_456"
    assert body["snippet"]["resourceId"]["videoId"] == "vid_123"


def test_add_video_to_playlist_skips_when_already_present():
    client = YouTubeClient()
    mock_youtube = MagicMock()

    # Mock playlistItems().list returning existing item matching videoId
    mock_check_req = MagicMock()
    mock_check_req.execute.return_value = {
        "items": [{"snippet": {"resourceId": {"videoId": "vid_123"}}}]
    }
    mock_youtube.playlistItems().list.return_value = mock_check_req
    mock_youtube.playlistItems().list_next.return_value = None

    success = client.add_video_to_playlist(mock_youtube, video_id="vid_123", playlist_id="pl_456")

    assert success is True
    mock_youtube.playlistItems().insert.assert_not_called()


def test_generate_metadata_includes_candidates_and_chapters(tmp_path):
    from dataclasses import dataclass
    from src.publisher.title_manager import TitleManager

    @dataclass
    class DummyEvent:
        start_time: float
        end_time: float
        action_type: str
        description: str

    tracker = tmp_path / "tracker.json"
    tm = TitleManager(tracker_file=tracker)
    client = YouTubeClient(title_manager=tm)

    events = [
        DummyEvent(15.0, 16.0, "nav", "Entering Base"),
        DummyEvent(30.0, 31.0, "craft", "Crafting Planks"),
    ]

    meta = client.generate_metadata(
        video_title="Test Video",
        events=events,
        music_track=[{"title": "Track 1", "artist": "Artist 1"}],
        thumbnail_path=tmp_path / "thumb.jpg",
        episode_number=5,
    )

    assert meta.episode_number == 5
    assert meta.title_candidates is not None
    assert "action_hook" in meta.title_candidates
    assert meta.thumbnail_path == str(tmp_path / "thumb.jpg")
    # Ensures 00:00 chapter exists
    assert "00:00" in meta.description
    assert "🎵 SOUNDTRACK" in meta.description
    assert "Track 1 — Artist 1" in meta.description
