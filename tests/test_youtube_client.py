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
    # Ensures soundtrack and licensing blocks are strictly omitted for description hygiene
    assert "SOUNDTRACK" not in meta.description
    assert "LICENSING" not in meta.description


def test_upload_video_retries_on_invalid_tags(tmp_path):
    from unittest.mock import patch
    from googleapiclient.errors import HttpError
    from httplib2 import Response
    from src.publisher.youtube_client import VideoPublishMetadata
    from src.publisher.title_manager import TitleManager

    tm = TitleManager(tracker_file=tmp_path / "tracker.json")
    client = YouTubeClient(title_manager=tm)
    video_file = tmp_path / "test.mp4"
    video_file.write_bytes(b"dummy video data")

    meta = VideoPublishMetadata(
        title="Test Title",
        description="Test Description",
        tags=["InvalidTag<1>", "Tag,With,Comma", "Tag2"],
        category_id="20",
        privacy_status="private",
    )

    mock_youtube = MagicMock()
    # Mock channel check to bypass duplicate pre-check
    mock_youtube.channels().list().execute.return_value = {"items": []}
    mock_youtube.playlists().list().execute.return_value = {"items": []}
    mock_youtube.playlists().list_next.return_value = None
    mock_youtube.playlistItems().list().execute.return_value = {"items": []}
    mock_youtube.playlistItems().list_next.return_value = None

    err_resp = Response({"status": 400, "reason": "Bad Request"})
    err_content = b'{"error": {"errors": [{"reason": "invalidTags", "message": "The request metadata specifies invalid video keywords."}]}}'
    http_err = HttpError(err_resp, err_content)

    mock_fail_req = MagicMock()
    mock_fail_req.next_chunk.side_effect = http_err

    mock_success_req = MagicMock()
    mock_success_req.next_chunk.return_value = (None, {"id": "uploaded_vid_999"})

    mock_youtube.videos().insert.side_effect = [mock_fail_req, mock_success_req]

    with patch("src.google_auth.get_google_credentials", return_value=MagicMock()), \
         patch("googleapiclient.discovery.build", return_value=mock_youtube):
        url = client.upload_video(video_path=video_file, metadata=meta)

    assert url == "https://youtu.be/uploaded_vid_999"
    assert mock_youtube.videos().insert.call_count == 2
    second_call_body = mock_youtube.videos().insert.call_args_list[1][1]["body"]
    assert second_call_body["snippet"]["tags"] == [
        "Last Day on Earth",
        "Last Day on Earth Survival",
        "LDoE Gameplay",
        "Zombie Survival",
    ]



