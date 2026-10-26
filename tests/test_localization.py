"""Unit tests for the multi-language metadata localizer and YouTube integration."""

import pytest
from src.publisher.localization import MetadataLocalizer
from src.publisher.youtube_client import VideoPublishMetadata, YouTubeClient
from src.publisher.title_manager import TitlePackage


def test_metadata_localizer_deterministic_generation():
    localizer = MetadataLocalizer(gemini_api_key=None)

    primary_title = "Last Day on Earth Episode #5 - Bunker Alfa Survival Guide & Chopper Build"
    primary_description = (
        "Welcome to Last Day on Earth: Survival Episode #5!\n"
        "We head to Bunker Alfa and work on our Chopper.\n\n"
        "00:00 - Intro & Base Prep\n"
        "03:45 - Bunker Alfa Floor 2\n"
        "09:15 - Opening the Red Crate\n"
    )

    localizations = localizer.generate_localizations(
        primary_title=primary_title,
        primary_description=primary_description,
        episode_number=5,
        playlist_url="https://youtube.com/playlist?list=TEST1234",
    )

    assert "ru" in localizations
    assert "pt" in localizations
    assert "es" in localizations

    # Verify length constraints
    for lang, data in localizations.items():
        assert len(data["title"]) <= 100
        assert len(data["description"]) <= 5000
        assert len(data["title"]) > 0
        assert len(data["description"]) > 0

    # Russian checks
    ru_title = localizations["ru"]["title"]
    assert "Бункер Альфа" in ru_title or "Чоппер" in ru_title or "Эпизод" in ru_title
    assert "00:00 - Intro & Base Prep" in localizations["ru"]["description"]
    assert "03:45 - Bunker Alfa Floor 2" in localizations["ru"]["description"]

    # Portuguese checks
    pt_title = localizations["pt"]["title"]
    assert "Episódio" in pt_title or "Bunker Alfa" in pt_title or "Sobrevivência" in pt_title
    assert "00:00 - Intro & Base Prep" in localizations["pt"]["description"]

    # Spanish checks
    es_title = localizations["es"]["title"]
    assert "Episodio" in es_title or "Supervivencia" in es_title or "Búnker Alfa" in es_title


def test_video_publish_metadata_localization_fields():
    metadata = VideoPublishMetadata(
        title="Test Title",
        description="Test Description",
        tags=["ldoe"],
        category_id="20",
        privacy_status="public",
        localizations={
            "ru": {"title": "Заголовок", "description": "Описание"},
            "pt": {"title": "Título", "description": "Descrição"},
        },
        default_language="en",
    )

    assert metadata.default_language == "en"
    assert metadata.localizations is not None
    assert "ru" in metadata.localizations
    assert metadata.localizations["ru"]["title"] == "Заголовок"

    d = metadata.to_dict()
    assert d["default_language"] == "en"
    assert d["localizations"]["pt"]["title"] == "Título"


def test_youtube_client_generate_metadata_includes_localizations(monkeypatch):
    client = YouTubeClient()

    # Mock title manager generate_titles
    mock_pkg = TitlePackage(
        primary_title="Last Day on Earth Episode #10 - Woodworking & Smelting Base Guide",
        action_hook="EPIC BASE UPGRADE",
        curiosity="SECRET WORKSHOP TRICK",
        walkthrough="HOW TO BUILD WORKBENCHES",
        episode_number=10,
        summary="upgrading base and furnaces",
    )
    monkeypatch.setattr(client.title_manager, "generate_titles", lambda **kwargs: mock_pkg)

    metadata = client.generate_metadata(
        video_title="Raw Video Title",
        events=[],
        episode_number=10,
    )

    assert metadata.default_language == "en"
    assert metadata.localizations is not None
    assert "ru" in metadata.localizations
    assert "pt" in metadata.localizations
    assert "es" in metadata.localizations
    assert len(metadata.localizations["ru"]["title"]) <= 100
