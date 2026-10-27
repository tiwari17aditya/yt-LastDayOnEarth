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


def test_metadata_localizer_generate_srt_captions(tmp_path):
    localizer = MetadataLocalizer()

    class DummyEv:
        def __init__(self, desc, st, et):
            self.description = desc
            self.start_time = st
            self.end_time = et

    events = [
        DummyEv("Bunker Alfa Floor 2 Clearing", 0.0, 3.0),
        DummyEv("Smelting Iron & Furnaces", 5.0, 8.5),
    ]

    # Test Russian SRT
    ru_path = tmp_path / "test_ru.srt"
    localizer.generate_srt_captions(events=events, lang="ru", output_path=ru_path)
    assert ru_path.exists()
    ru_content = ru_path.read_text(encoding="utf-8")
    assert "00:00:00,000 --> 00:00:03,000" in ru_content
    assert "Бункер Альфа" in ru_content
    assert "00:00:05,000 --> 00:00:08,500" in ru_content
    assert "Плавильная печь" in ru_content

    # Test Portuguese SRT
    pt_path = tmp_path / "test_pt.srt"
    localizer.generate_srt_captions(events=events, lang="pt", output_path=pt_path)
    assert pt_path.exists()
    pt_content = pt_path.read_text(encoding="utf-8")
    assert "Bunker Alfa" in pt_content
    assert "Fornalha" in pt_content


def test_youtube_client_upload_captions(tmp_path):
    client = YouTubeClient()

    class DummyEv:
        def __init__(self, desc, st, et):
            self.description = desc
            self.start_time = st
            self.end_time = et

    events = [DummyEv("Base Building", 0.0, 4.0)]

    inserted_captions = []

    class FakeCaptions:
        def insert(self, part, body, media_body):
            inserted_captions.append(body["snippet"])
            class Exec:
                def execute(self):
                    return {"id": f"caption_{body['snippet']['language']}"}
            return Exec()

    class FakeYouTube:
        def captions(self):
            return FakeCaptions()

    fake_yt = FakeYouTube()
    result = client.upload_captions(
        youtube=fake_yt,
        video_id="TEST_VID",
        events=events,
        languages=["en", "ru", "pt"],
    )

    assert "en" in result
    assert "ru" in result
    assert "pt" in result
    assert len(inserted_captions) == 3
    langs = [c["language"] for c in inserted_captions]
    assert "en" in langs
    assert "ru" in langs
    assert "pt" in langs
