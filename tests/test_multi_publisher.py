import json
import pytest
from pathlib import Path
from unittest.mock import MagicMock

from src.publisher.youtube_client import VideoPublishMetadata, BasePublisher
from src.publisher.multi_publisher import MultiPlatformPublisher


@pytest.fixture
def sample_metadata():
    return VideoPublishMetadata(
        title="Last Day on Earth - Ep 48: Zombie Raid",
        description="Epic gameplay in the bunker alpha.",
        tags=["ldoe", "survival", "zombies"],
        category_id="20",
        privacy_status="public",
        thumbnail_path="data/thumbnails/ep48.jpg",
        episode_number=48,
    )


def test_base_publisher_export_metadata_json(sample_metadata, tmp_path):
    class DummyPublisher(BasePublisher):
        def generate_metadata(self, *args, **kwargs):
            return sample_metadata

        def upload_video(self, video_path: Path, metadata: VideoPublishMetadata) -> str:
            return "https://youtu.be/dummy123"

    publisher = DummyPublisher()
    out_json = tmp_path / "video_metadata.json"
    result_path = publisher.export_metadata_json(sample_metadata, out_json)

    assert result_path == out_json
    assert out_json.exists()

    with open(out_json, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data["title"] == sample_metadata.title
    assert data["episode_number"] == 48
    assert data["tags"] == ["ldoe", "survival", "zombies"]


def test_multi_platform_publisher_export_metadata_json_delegates(sample_metadata, tmp_path):
    mock_yt = MagicMock()
    out_json = tmp_path / "metadata_del.json"
    mock_yt.export_metadata_json.return_value = out_json

    pub = MultiPlatformPublisher(youtube_client=mock_yt)
    res = pub.export_metadata_json(sample_metadata, out_json)

    mock_yt.export_metadata_json.assert_called_once_with(sample_metadata, out_json)
    assert res == out_json


def test_multi_platform_publisher_export_metadata_json_fallback(sample_metadata, tmp_path):
    mock_yt = MagicMock(spec=[])  # No export_metadata_json attribute
    out_json = tmp_path / "subdir" / "metadata_fallback.json"

    pub = MultiPlatformPublisher(youtube_client=mock_yt)
    res = pub.export_metadata_json(sample_metadata, out_json)

    assert res == out_json
    assert out_json.exists()

    with open(out_json, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data["title"] == sample_metadata.title
    assert data["privacy_status"] == "public"


def test_multi_platform_publisher_getattr_delegation():
    class DummyYouTubeClient:
        def custom_yt_helper(self):
            return "delegated_success"

    dummy_yt = DummyYouTubeClient()
    pub = MultiPlatformPublisher(youtube_client=dummy_yt)
    assert pub.custom_yt_helper() == "delegated_success"

    with pytest.raises(AttributeError):
        _ = pub.non_existent_attribute_xyz


def test_export_metadata_json_error_handling(sample_metadata, tmp_path, monkeypatch):
    """Verifies that an error during metadata export does not crash downstream logic."""
    mock_yt = MagicMock()
    mock_yt.export_metadata_json.side_effect = PermissionError("Permission denied writing json")

    pub = MultiPlatformPublisher(youtube_client=mock_yt)
    out_json = tmp_path / "protected" / "metadata.json"

    # Direct call raises PermissionError as expected
    with pytest.raises(PermissionError):
        pub.export_metadata_json(sample_metadata, out_json)
