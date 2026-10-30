"""Unit tests for Automated Companion YouTube Shorts Pipeline (Enhancement 2)."""

from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from src.config import ProcessingSettings
from src.exceptions import QuotaExceededError
from src.processor.shorts_generator import ShortsGenerator
from src.publisher.youtube_client import YouTubeClient


class MockEvent:
    def __init__(self, description: str, start_time: float, end_time: float):
        self.description = description
        self.start_time = start_time
        self.end_time = end_time


def test_companion_shorts_config_defaults():
    settings = ProcessingSettings()
    assert settings.generate_companion_shorts is True
    assert settings.upload_companion_shorts is True
    assert settings.shorts_dir == Path("data/shorts")


def test_viral_moment_detection_priority_fail():
    generator = ShortsGenerator()
    events = [
        MockEvent("Survivor gathering wood in forest", 15.0, 30.0),
        MockEvent("Zombie ambush! Frenzy giant attack and sudden death near bunker", 45.0, 75.0),
        MockEvent("Opening red crate with c4 and chopper parts", 100.0, 120.0),
    ]
    viral = generator.auto_detect_viral_moment(events, video_duration=180.0)
    assert viral["hook_type"] == "fail_panic"
    assert viral["headline"] == "DISASTER MOMENT?!"
    assert viral["start_time"] == 45.0
    assert viral["duration"] == 30.0


def test_viral_moment_detection_priority_loot():
    generator = ShortsGenerator()
    events = [
        MockEvent("Survivor walking in base", 10.0, 25.0),
        MockEvent("Opening red crate in bunker alfa containing chopper gas tank", 50.0, 85.0),
        MockEvent("Chopping pine trees for workshop", 120.0, 140.0),
    ]
    viral = generator.auto_detect_viral_moment(events, video_duration=180.0)
    assert viral["hook_type"] == "rare_loot"
    assert viral["headline"] == "RAREST LOOT DROP?!"
    assert viral["start_time"] == 50.0


def test_viral_moment_detection_priority_combat():
    generator = ShortsGenerator()
    events = [
        MockEvent("Survivor walking in base", 10.0, 25.0),
        MockEvent("Clearing infected farm with wall trick and melee weapons", 60.0, 95.0),
    ]
    viral = generator.auto_detect_viral_moment(events, video_duration=180.0)
    assert viral["hook_type"] == "combat_defense"
    assert viral["headline"] == "BASE UNDER ATTACK!"


def test_viral_moment_detection_clamping_for_short_videos():
    generator = ShortsGenerator()
    events = [
        MockEvent("Zombie attack and fight", 10.0, 20.0),
    ]
    # Video is only 25 seconds long
    viral = generator.auto_detect_viral_moment(events, video_duration=25.0, default_duration=35.0)
    assert viral["start_time"] + viral["duration"] <= 25.0
    assert viral["start_time"] >= 0.0


def test_generate_companion_short_packaging(tmp_path):
    generator = ShortsGenerator(output_dir=tmp_path)
    events = [
        MockEvent("Survivor opening red crate loot", 30.0, 60.0),
    ]
    dummy_video = tmp_path / "ep1_gameplay.mp4"
    dummy_video.write_bytes(b"dummy_video_bytes")

    with patch.object(generator, "get_video_duration", return_value=120.0), \
         patch.object(generator, "generate_short", return_value=tmp_path / "short_ep1_gameplay.mp4") as mock_render:

        package = generator.generate_companion_short(
            input_video=dummy_video,
            events=events,
            episode_number=1,
            parent_video_id="Aw80nniGs-E",
        )

        mock_render.assert_called_once()
        assert package["short_path"] == tmp_path / "short_ep1_gameplay.mp4"
        assert "#Shorts" in package["title"]
        assert "Aw80nniGs-E" in package["description"]
        assert "https://youtu.be/Aw80nniGs-E" in package["description"]
        assert "PLJPzVNVZwaGY" in package["description"]
        assert package["parent_video_id"] == "Aw80nniGs-E"
        assert package["episode_number"] == 1


def test_upload_companion_short_flow(tmp_path):
    client = YouTubeClient()
    dummy_short = tmp_path / "short.mp4"
    dummy_short.write_bytes(b"dummy")

    mock_service = MagicMock()
    mock_insert = MagicMock()
    mock_insert.next_chunk.return_value = (None, {"id": "short_vid_999"})
    mock_service.videos().insert.return_value = mock_insert

    mock_comment_thread = MagicMock()
    mock_service.commentThreads.return_value = mock_comment_thread
    mock_comment_insert = MagicMock()
    mock_comment_insert.execute.return_value = {"id": "comment_123"}
    mock_comment_thread.insert.return_value = mock_comment_insert

    with patch.object(client, "get_service", return_value=mock_service), \
         patch.object(client, "get_or_create_playlist", return_value="PL_SHORTS_999") as mock_get_pl, \
         patch.object(client, "add_video_to_playlist", return_value=True) as mock_add_pl, \
         patch("googleapiclient.http.MediaFileUpload"):

        url = client.upload_companion_short(
            short_path=dummy_short,
            title="EPIC RED ZONE LOOT",
            description="Watch episode here: https://youtu.be/parent123",
            parent_video_id="parent123",
            episode_number=5,
        )

        assert url == "https://youtu.be/short_vid_999"
        # Check snippet call arguments
        call_kwargs = mock_service.videos().insert.call_args[1]
        assert "#Shorts" in call_kwargs["body"]["snippet"]["title"]
        assert call_kwargs["body"]["snippet"]["categoryId"] == "20"
        # Check dedicated Shorts playlist was managed
        mock_get_pl.assert_called_once()
        assert mock_get_pl.call_args[1]["title"] == "Last Day on Earth: Survival — Official Gameplay Shorts"
        mock_add_pl.assert_called_once_with(
            youtube=mock_service,
            video_id="short_vid_999",
            playlist_id="PL_SHORTS_999",
            episode_number=5,
        )
        # Check backlink comment was triggered and includes both playlists
        mock_comment_thread.insert.assert_called_once()
        comment_body = mock_comment_thread.insert.call_args[1]["body"]["snippet"]["topLevelComment"]["snippet"]["textOriginal"]
        assert "PL_SHORTS_999" in comment_body
        assert "PLJPzVNVZwaGY" in comment_body


def test_upload_companion_short_quota_handling(tmp_path):
    client = YouTubeClient()
    dummy_short = tmp_path / "short.mp4"
    dummy_short.write_bytes(b"dummy")

    mock_service = MagicMock()
    mock_insert = MagicMock()
    mock_insert.next_chunk.side_effect = Exception("quotaExceeded: The request cannot be completed")
    mock_service.videos().insert.return_value = mock_insert

    with patch.object(client, "get_service", return_value=mock_service), \
         patch("googleapiclient.http.MediaFileUpload"):

        with pytest.raises(QuotaExceededError):
            client.upload_companion_short(
                short_path=dummy_short,
                title="EPIC CLASH",
                description="desc",
            )


def test_drive_upload_processed_short(tmp_path):
    from src.ingestion.drive_client import GoogleDriveClient
    client = GoogleDriveClient()
    client.output_folder_id = "folder_root_123"
    client.service = MagicMock()

    dummy_short = tmp_path / "short.mp4"
    dummy_short.write_bytes(b"dummy_short")

    with patch.object(client, "_ensure_folder", side_effect=["shorts_root_id", "year_id", "month_id"]), \
         patch("googleapiclient.http.MediaFileUpload"):

        mock_req = MagicMock()
        mock_req.next_chunk.return_value = (None, {"id": "drive_short_file_123"})
        client.service.files().create.return_value = mock_req
        client.service.files().list().execute.return_value = {"files": []}

        res = client.upload_processed_short(dummy_short)
        assert res["short_id"] == "drive_short_file_123"
        assert "short_" in res["short_name"]
        assert "Output/shorts" in res["short_folder"]
