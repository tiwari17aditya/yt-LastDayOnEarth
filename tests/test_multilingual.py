"""Unit tests for the Multi-Language Audio and Closed Captions Engine."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch, AsyncMock
import pytest

from src.audio.commentary_engine import (
    CommentaryEngine,
    CommentaryCue,
    REGIONAL_VOICE_MAP,
)
from src.publisher.localization import MetadataLocalizer
from src.publisher.youtube_client import YouTubeClient, VideoPublishMetadata


def test_regional_voice_map_configuration():
    """Verify that all target regional languages have valid Edge-TTS voice profiles."""
    expected_languages = ["de", "es", "ru", "fr"]
    for lang in expected_languages:
        assert lang in REGIONAL_VOICE_MAP
        profile = REGIONAL_VOICE_MAP[lang]
        assert profile["voice"].endswith("Neural")
        assert profile["name"]
        assert profile["rate"]
        assert profile["pitch"]


def test_metadata_localizer_expanded_languages():
    """Verify that MetadataLocalizer supports German, French, Spanish, Russian, and Portuguese."""
    localizer = MetadataLocalizer()
    for lang in ["de", "fr", "es", "ru", "pt"]:
        assert lang in localizer.SUPPORTED_LANGUAGES


def test_translate_cues_deterministic_fallback():
    """Verify translate_cues translates LDoE vocabulary when offline/without Gemini."""
    engine = CommentaryEngine(temp_dir=Path("temp/test_multilingual"))
    cues = [
        CommentaryCue(start_time=2.0, text="Welcome to Last Day on Earth Survival Bunker Alfa run.", duration=4.0),
        CommentaryCue(start_time=10.0, text="Focusing on Base Building and Woodworking crafting.", duration=3.5),
    ]

    # German
    cues_de = engine.translate_cues(cues, target_lang="de", gemini_api_key=None)
    assert len(cues_de) == 2
    assert cues_de[0].start_time == 2.0
    text_de = " ".join([c.text for c in cues_de])
    assert "Bunker Alfa" in text_de
    assert "Basisbau" in text_de or "Last Day on Earth" in text_de

    # French
    cues_fr = engine.translate_cues(cues, target_lang="fr", gemini_api_key=None)
    assert len(cues_fr) == 2
    text_fr = " ".join([c.text for c in cues_fr])
    assert "Bunker Alfa" in text_fr

    # Spanish
    cues_es = engine.translate_cues(cues, target_lang="es", gemini_api_key=None)
    assert len(cues_es) == 2
    text_es = " ".join([c.text for c in cues_es])
    assert "Supervivencia" in text_es or "Búnker Alfa" in text_es


def test_translate_cues_gemini_mocked():
    """Verify translate_cues handles Gemini API responses accurately."""
    engine = CommentaryEngine(temp_dir=Path("temp/test_multilingual"))
    cues = [
        CommentaryCue(start_time=2.0, text="Hello survivors, welcome back to the wasteland.", duration=4.0),
    ]

    mock_gemini_resp = MagicMock()
    mock_gemini_resp.text = json.dumps(["Hallo Überlebende, willkommen zurück im Ödland."])

    with patch("google.genai.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_gemini_resp
        mock_client_cls.return_value = mock_client

        translated = engine.translate_cues(
            cues,
            target_lang="de",
            gemini_api_key="valid-mock-key-12345",
        )
        assert len(translated) == 1
        assert "Hallo Überlebende" in translated[0].text
        assert translated[0].start_time == 2.0


def test_generate_multilingual_package(tmp_path):
    """Verify generate_multilingual_package synthesizes regional audio tracks and manifest."""
    engine = CommentaryEngine(temp_dir=tmp_path / "temp")
    cues = [
        CommentaryCue(start_time=2.0, text="Calm survival walkthrough.", duration=3.0),
    ]
    out_dir = tmp_path / "multilingual_out"

    with patch.object(engine, "synthesize_all_regional_cues_async", new_callable=AsyncMock), \
         patch.object(engine, "build_timeline_commentary_track") as mock_build, \
         patch.object(engine, "normalize_pure_voice_track") as mock_norm, \
         patch.object(engine, "generate_subtitles") as mock_subs:

        # Mock normalized audio file creation
        def fake_norm(raw_voice_audio, output_audio_path, volume_boost_db="+1dB"):
            output_audio_path.parent.mkdir(parents=True, exist_ok=True)
            output_audio_path.write_bytes(b"dummy audio")
            return output_audio_path

        mock_norm.side_effect = fake_norm

        def fake_subs(cues, output_path, events=None):
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text("[Script Info]\nTitle: Test", encoding="utf-8")
            output_path.with_suffix(".srt").write_text("1\n00:00:02,000 --> 00:00:05,000\nSub", encoding="utf-8")
            return output_path

        mock_subs.side_effect = fake_subs

        package = engine.generate_multilingual_package(
            duration=30.0,
            base_cues=cues,
            output_dir=out_dir,
            target_languages=["de", "es"],
            bgm_audio=None,
        )

        assert "de" in package
        assert "es" in package
        assert package["de"]["audio"].exists()
        assert package["de"]["srt"].exists()
        assert package["es"]["audio"].exists()

        # Check manifest
        manifest_p = out_dir / "multilingual_manifest.json"
        assert manifest_p.exists()
        manifest_data = json.loads(manifest_p.read_text(encoding="utf-8"))
        assert "de" in manifest_data["languages"]
        assert manifest_data["languages"]["de"]["voice"] == "de-DE-KillianNeural"


def test_youtube_client_upload_captions_high_fidelity(tmp_path):
    """Verify YouTubeClient.upload_captions uploads caption_tracks accurately."""
    client = YouTubeClient()
    mock_youtube = MagicMock()
    mock_insert = MagicMock()
    mock_youtube.captions().insert.return_value = mock_insert
    mock_insert.execute.return_value = {"id": "caption_de_123"}

    srt_de = tmp_path / "german.srt"
    srt_de.write_text("1\n00:00:02,000 --> 00:00:05,000\nHallo\n", encoding="utf-8")

    caption_tracks = {
        "de": (srt_de, "Deutsch (Deutsche Untertitel)"),
    }

    uploaded = client.upload_captions(
        youtube=mock_youtube,
        video_id="vid_test_999",
        caption_tracks=caption_tracks,
    )

    assert "de" in uploaded
    assert uploaded["de"] == "caption_de_123"
    assert mock_youtube.captions().insert.called
