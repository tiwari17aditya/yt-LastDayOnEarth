"""Unit tests for the AI Commentary Engine, configuration, and fail-safe error handling."""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch, AsyncMock

from src.audio.commentary_engine import (
    CommentaryEngine,
    CommentaryPersona,
    CommentaryCue,
    PERSONA_PROFILES,
    PersonaConfig,
)
from src.config import get_settings
from src.exceptions import CommentaryError
from src.subtitles.event_analyzer import GameplayEvent


def test_commentary_personas():
    """Verify all defined personas have valid configuration profiles."""
    for persona in CommentaryPersona:
        assert persona in PERSONA_PROFILES
        profile = PERSONA_PROFILES[persona]
        assert profile.voice.startswith("en-US-")
        assert "Neural" in profile.voice
        assert profile.description


def test_persona_profiles_coverage():
    """Verify voice mappings for each persona."""
    engine = CommentaryEngine(temp_dir=Path("temp/test_commentary"))
    config_energetic = engine.get_persona_config(CommentaryPersona.ENERGETIC)
    assert config_energetic.voice == "en-US-ChristopherNeural"

    config_casual = engine.get_persona_config(CommentaryPersona.CASUAL)
    assert config_casual.voice == "en-US-GuyNeural"
    assert config_casual.rate == "-3%"
    assert config_casual.pitch == "-2Hz"

    config_soft = engine.get_persona_config(CommentaryPersona.SOFT)
    assert config_soft.voice == "en-US-GuyNeural"
    assert config_soft.rate == "-4%"
    assert config_soft.pitch == "-2Hz"

    config_tactical = engine.get_persona_config(CommentaryPersona.TACTICAL)
    assert config_tactical.voice == "en-US-AndrewNeural"


def test_commentary_settings_defaults():
    """Verify CommentarySettings are present in PipelineSettings with correct soft voice defaults."""
    settings = get_settings()
    assert hasattr(settings, "commentary")
    assert settings.commentary.enabled is True
    assert settings.commentary.persona == "casual"
    assert settings.commentary.voice == "en-US-GuyNeural"
    assert settings.commentary.rate == "-3%"
    assert settings.commentary.pitch == "-2Hz"
    assert settings.commentary.volume_boost_db == "+1dB"
    assert settings.commentary.include_bgm is True
    assert settings.commentary.bgm_volume_db == "-22dB"
    assert settings.commentary.ducking_ratio == 3.5
    assert settings.commentary.min_cue_interval == 25.0


def test_commentary_error_rule_4_compliance():
    """Verify CommentaryError implements global engineering standard Rule 4 error reporting."""
    err = CommentaryError(
        operation="synthesize_cues",
        root_cause="Connection reset by peer",
        recovery_action="Fallback to standard BGM loop.",
        file_path="temp/test.m4a",
    )
    data = err.to_dict()
    assert data["component"] == "CommentaryEngine"
    assert data["operation"] == "synthesize_cues"
    assert data["root_cause"] == "Connection reset by peer"
    assert data["recovery_action"] == "Fallback to standard BGM loop."
    assert data["status"] == "DEGRADED"
    assert data["file_path"] == "temp/test.m4a"


@pytest.mark.parametrize("persona", [
    CommentaryPersona.ENERGETIC,
    CommentaryPersona.CASUAL,
    CommentaryPersona.TACTICAL,
])
def test_generate_script_structure(persona):
    """Verify script generation produces chronologically ordered cues with intro and outro."""
    engine = CommentaryEngine(temp_dir=Path("temp/test_commentary"))
    duration = 930.0  # ~15.5 minutes
    cues = engine.generate_script(
        duration=duration,
        episode_number=99,
        persona=persona,
    )

    assert len(cues) >= 4
    # Check intro exists within first 5 seconds
    assert cues[0].start_time <= 5.0
    assert "99" in cues[0].text or "Episode 99" in cues[0].text

    # Check outro exists near the end
    assert cues[-1].start_time >= duration - 30.0
    assert any(w in cues[-1].text.lower() for w in ["subscribe", "like", "comments"])

    # Check ascending start times
    for i in range(len(cues) - 1):
        assert cues[i].start_time < cues[i + 1].start_time


def test_generate_script_short_duration():
    """Verify script generation adapts gracefully to short duration videos."""
    engine = CommentaryEngine(temp_dir=Path("temp/test_commentary"))
    cues = engine.generate_script(duration=45.0, episode_number=1, persona=CommentaryPersona.ENERGETIC)
    assert len(cues) >= 2
    assert cues[0].start_time == 2.0
    assert cues[-1].start_time >= 10.0


def test_generate_script_with_gameplay_events():
    """Verify script generation incorporates detected gameplay events."""
    engine = CommentaryEngine(temp_dir=Path("temp/test_commentary"))
    events = [
        GameplayEvent(40.0, 45.0, "combat", "Spitter Pack Ambush"),
        GameplayEvent(120.0, 125.0, "craft", "Furnace Charcoal Smelting"),
        GameplayEvent(250.0, 255.0, "loot", "Red Zone Weapon Crate"),
        GameplayEvent(400.0, 405.0, "defense", "Perimeter Wall Spike Reinforcement"),
    ]
    cues = engine.generate_script(
        events=events,
        duration=600.0,
        episode_number=112,
        persona=CommentaryPersona.CASUAL,
    )

    assert len(cues) >= 5
    # Intro
    assert cues[0].start_time == 2.0
    # Cues should reflect event contexts
    cue_texts = " ".join([c.text for c in cues])
    assert "Spitter Pack Ambush" in cue_texts or "enemy movement" in cue_texts.lower()
    assert "Furnace Charcoal Smelting" in cue_texts or "production" in cue_texts.lower()
    assert "Red Zone Weapon Crate" in cue_texts or "stash" in cue_texts.lower()


def test_generate_script_long_duration():
    """Verify script generation distributes cues across a 30-minute video."""
    engine = CommentaryEngine(temp_dir=Path("temp/test_commentary"))
    cues = engine.generate_script(
        duration=1800.0,  # 30 minutes
        episode_number=115,
        persona=CommentaryPersona.CASUAL,
    )
    assert len(cues) >= 10
    # Check that cues span the timeline
    assert cues[0].start_time <= 5.0
    assert cues[-1].start_time >= 1770.0
    mid_cues = [c for c in cues if 300.0 <= c.start_time <= 1500.0]
    assert len(mid_cues) >= 5


import asyncio


def test_synthesize_single_cue_retry_failure():
    """Verify that if edge-tts fails all retries, it degrades gracefully and does not throw."""
    engine = CommentaryEngine(temp_dir=Path("temp/test_commentary"))
    cue = CommentaryCue(start_time=2.0, text="Testing failure isolation")
    config = engine.get_persona_config(CommentaryPersona.CASUAL)

    with patch("edge_tts.Communicate.save", side_effect=RuntimeError("Simulated edge-tts network error")):
        dur = asyncio.run(engine._synthesize_single_cue(cue, config, Path("temp/fail.mp3"), max_retries=1))
        assert dur == 0.0
        assert cue.audio_path is None


def test_build_timeline_empty_cues_raises_commentary_error():
    """Verify that build_timeline_commentary_track raises CommentaryError when no audio is present."""
    engine = CommentaryEngine(temp_dir=Path("temp/test_commentary"))
    with pytest.raises(CommentaryError) as exc_info:
        engine.build_timeline_commentary_track([], total_duration=60.0, output_path=Path("temp/out.m4a"))
    assert exc_info.value.component == "CommentaryEngine"
    assert exc_info.value.status == "DEGRADED"


def test_pipeline_commentary_failure_degrades_gracefully(tmp_path):
    """Verify that if commentary synthesis fails during run_pipeline, it degrades gracefully to standard BGM."""
    from src.main import run_pipeline

    input_v = tmp_path / "mock_video.mp4"
    input_v.write_bytes(b"dummy video content for testing md5")

    with patch("src.processor.video_processor.VideoProcessor.get_video_duration", return_value=60.0), \
         patch("src.privacy.detector.PrivacyDetector.scan_video", return_value=[]), \
         patch("src.privacy.detector.PrivacyDetector.generate_ffmpeg_blur_filter", return_value=None), \
         patch("src.subtitles.event_analyzer.SubtitleGenerator.analyze_events", return_value=[]), \
         patch("src.subtitles.event_analyzer.SubtitleGenerator.generate_subtitles", return_value=None), \
         patch("src.audio.selector.AudioMixer.create_random_loop_sequence", return_value=(tmp_path / "bgm.m4a", [{"title": "Ambient"}])), \
         patch("src.audio.commentary_engine.CommentaryEngine.generate_commentary_track", side_effect=CommentaryError(operation="test", root_cause="Mocked failure")), \
         patch("src.processor.video_processor.VideoProcessor.render") as mock_render, \
         patch("src.processor.video_processor.VideoProcessor.get_output_path", return_value=tmp_path / "out.mp4"), \
         patch("src.privacy.ad_detector.AdDetector.detect_ads", return_value=[]), \
         patch("src.processor.thumbnail_generator.ThumbnailGenerator.generate_thumbnail", return_value=tmp_path / "thumb.jpg"), \
         patch("src.storage.history_tracker.HistoryTracker.record_job"), \
         patch("src.publisher.title_manager.TitleManager._update_current_episode"), \
         patch("src.publisher.title_manager.TitleManager.advance_episode"), \
         patch("src.main.get_notifier"):

        (tmp_path / "out.mp4").write_bytes(b"dummy output")

        result = run_pipeline(input_video_path=input_v, local_only=True, force=True)

        assert mock_render.called
        # Verify render received the fallback BGM file, NOT failing
        called_music_file = mock_render.call_args[1].get("music_file")
        assert called_music_file == tmp_path / "bgm.m4a"


def test_generate_subtitles_creates_ass_and_srt(tmp_path):
    """Verify generate_subtitles generates valid ASS (1920x1080) and SRT caption files."""
    engine = CommentaryEngine(temp_dir=tmp_path)
    cues = [
        CommentaryCue(start_time=2.0, text="Welcome back everyone to today's calm survival run.", duration=4.5),
        CommentaryCue(start_time=10.0, text="Here we are checking our workshop storage chests.", duration=3.8),
    ]
    events = [
        GameplayEvent(start_time=0.0, end_time=1.5, action_type="base", description="Base Operations"),
    ]

    ass_out = tmp_path / "test_subs.ass"
    engine.generate_subtitles(cues=cues, output_path=ass_out, events=events)

    assert ass_out.exists()
    srt_out = tmp_path / "test_subs.srt"
    assert srt_out.exists()

    ass_content = ass_out.read_text(encoding="utf-8")
    assert "PlayResX: 1920" in ass_content
    assert "PlayResY: 1080" in ass_content
    assert "Style: Commentary" in ass_content
    assert "Style: ActionBadge" in ass_content
    assert "Welcome back everyone" in ass_content
    assert "Base Operations" in ass_content

    srt_content = srt_out.read_text(encoding="utf-8")
    assert "00:00:02,000 --> 00:00:06,500" in srt_content
    assert "Welcome back everyone" in srt_content


def test_soft_voice_persona_script_generation():
    """Verify CommentaryPersona.SOFT produces gentle, soothing intro and outro text."""
    engine = CommentaryEngine(temp_dir=Path("temp/test_commentary"))
    cues = engine.generate_script(
        duration=300.0,
        episode_number=125,
        persona=CommentaryPersona.SOFT,
    )
    assert len(cues) >= 3
    # Check soothing intro
    intro = cues[0].text.lower()
    assert "relaxed" in intro or "comfortable" in intro or "steady" in intro
    assert "125" in intro

    # Check soothing outro
    outro = cues[-1].text.lower()
    assert "relaxing" in outro or "calm" in outro


def test_main_pipeline_attaches_commentary_subtitles(tmp_path):
    """Verify that run_pipeline passes the commentary-generated ASS subtitle file to the renderer."""
    from src.main import run_pipeline

    input_v = tmp_path / "mock_video_subs.mp4"
    input_v.write_bytes(b"dummy video for subtitle pipeline test")

    mock_ass_path = tmp_path / "mock_video_subs_commentary_master.ass"
    mock_ass_path.write_text("[Script Info]\nTitle: Test Subtitles", encoding="utf-8")
    mock_audio_path = tmp_path / "mock_video_subs_commentary_master.m4a"
    mock_audio_path.write_bytes(b"dummy audio")

    with patch("src.processor.video_processor.VideoProcessor.get_video_duration", return_value=60.0), \
         patch("src.privacy.detector.PrivacyDetector.scan_video", return_value=[]), \
         patch("src.privacy.detector.PrivacyDetector.generate_ffmpeg_blur_filter", return_value=None), \
         patch("src.subtitles.event_analyzer.SubtitleGenerator.analyze_events", return_value=[]), \
         patch("src.subtitles.event_analyzer.SubtitleGenerator.generate_subtitles", return_value=None), \
         patch("src.audio.selector.AudioMixer.create_random_loop_sequence", return_value=(tmp_path / "bgm.m4a", [{"title": "Ambient"}])), \
         patch("src.audio.commentary_engine.CommentaryEngine.generate_commentary_track", return_value=mock_audio_path), \
         patch("src.processor.video_processor.VideoProcessor.render") as mock_render, \
         patch("src.processor.video_processor.VideoProcessor.get_output_path", return_value=tmp_path / "out.mp4"), \
         patch("src.privacy.ad_detector.AdDetector.detect_ads", return_value=[]), \
         patch("src.processor.thumbnail_generator.ThumbnailGenerator.generate_thumbnail", return_value=tmp_path / "thumb.jpg"), \
         patch("src.storage.history_tracker.HistoryTracker.record_job"), \
         patch("src.publisher.title_manager.TitleManager._update_current_episode"), \
         patch("src.publisher.title_manager.TitleManager.advance_episode"), \
         patch("src.main.get_notifier"):

        (tmp_path / "out.mp4").write_bytes(b"dummy output")

        result = run_pipeline(input_video_path=input_v, local_only=True, force=True)

        assert mock_render.called
        # Verify render received the commentary subtitle file
        called_sub_file = mock_render.call_args[1].get("subtitle_file")
        assert called_sub_file is not None
        assert Path(called_sub_file).name.endswith("commentary_master.ass")

