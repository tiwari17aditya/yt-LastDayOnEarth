"""Unit tests for Option B: Configurable Commentary Language Switch (Hinglish / English).

Verifies:
- Configurable switch via COMMENTARY_LANGUAGE ("hi" / "en") defaulting to "hi" (Hinglish)
- Dynamic voice resolution (en-IN-PrabhatNeural for Hinglish, en-US-GuyNeural for English)
- High-engagement authentic Hinglish procedural dialogue & personas
- Strict survivor username privacy filter ensuring 'adistar656' is NEVER spoken aloud
- Backward-compatible persona configurations and multi-lingual dubbing
"""

import os
import pytest
from pathlib import Path
from unittest.mock import patch

from src.audio.commentary_engine import (
    CommentaryEngine,
    CommentaryPersona,
    REGIONAL_VOICE_MAP,
)
from src.config import CommentarySettings
from src.subtitles.event_analyzer import GameplayEvent


def test_commentary_language_default_hinglish():
    """Verify default commentary language is 'hi' (Hinglish) with Prabhat neural voice."""
    with patch.dict(os.environ, {}, clear=True):
        settings = CommentarySettings()
        assert settings.language == "hi"
        assert settings.effective_voice == "en-IN-PrabhatNeural"
        assert settings.effective_rate == "+12%"
        assert settings.effective_pitch == "+22Hz"


def test_commentary_language_switch_to_english():
    """Verify switching COMMENTARY_LANGUAGE to 'en' selects English voice and rate."""
    with patch.dict(os.environ, {"COMMENTARY_LANGUAGE": "en"}, clear=True):
        settings = CommentarySettings()
        assert settings.language == "en"
        assert settings.effective_voice == "en-US-GuyNeural"
        assert settings.effective_rate == "-3%"
        assert settings.effective_pitch == "-2Hz"


def test_commentary_voice_explicit_override_indian_voice():
    """Verify explicit Indian voice override is respected when in Hinglish mode."""
    env = {"COMMENTARY_LANGUAGE": "hi", "COMMENTARY_VOICE": "hi-IN-MadhurNeural"}
    with patch.dict(os.environ, env):
        settings = CommentarySettings()
        assert settings.effective_voice == "hi-IN-MadhurNeural"


def test_commentary_voice_explicit_override_english():
    """Verify explicit voice override is respected in English mode."""
    env = {"COMMENTARY_LANGUAGE": "en", "COMMENTARY_VOICE": "en-US-ChristopherNeural"}
    with patch.dict(os.environ, env):
        settings = CommentarySettings()
        assert settings.effective_voice == "en-US-ChristopherNeural"


def test_get_persona_config_hinglish():
    """Verify get_persona_config returns Hinglish voice profile when language is 'hi'."""
    engine = CommentaryEngine(temp_dir=Path("temp/test_lang"))
    config = engine.get_persona_config(CommentaryPersona.CASUAL, language="hi")
    assert config.voice == "en-IN-PrabhatNeural"
    assert config.rate == "+12%"
    assert config.pitch == "+22Hz"
    assert "Hinglish" in config.description


def test_get_persona_config_english_fallback():
    """Verify get_persona_config returns standard English profile when language is 'en'."""
    engine = CommentaryEngine(temp_dir=Path("temp/test_lang"))
    config = engine.get_persona_config(CommentaryPersona.CASUAL, language="en")
    assert config.voice == "en-US-GuyNeural"
    assert config.rate == "-3%"
    assert config.pitch == "-2Hz"


@pytest.mark.parametrize("persona", [
    CommentaryPersona.CASUAL,
    CommentaryPersona.SOFT,
    CommentaryPersona.ENERGETIC,
    CommentaryPersona.TACTICAL,
])
def test_generate_script_hinglish_structure(persona):
    """Verify Hinglish script generation produces authentic Romanized Hinglish cues."""
    engine = CommentaryEngine(temp_dir=Path("temp/test_lang"))
    cues = engine.generate_script(
        duration=900.0,
        episode_number=148,
        persona=persona,
        language="hi",
    )

    assert len(cues) >= 4
    # Intro cue
    intro = cues[0]
    assert intro.start_time == 2.0
    assert "Episode 148" in intro.text or "148" in intro.text
    # Contains authentic Hinglish vocabulary
    intro_lower = intro.text.lower()
    assert any(w in intro_lower for w in ["aaj", "kareinge", "karenge", "swagat", "survivors", "dekhte hain"])

    # Outro cue
    outro = cues[-1]
    outro_lower = outro.text.lower()
    assert any(w in outro_lower for w in ["thank you", "video", "like", "subscribe", "comments", "milte hain"])


def test_generate_script_english_structure():
    """Verify English script generation produces proper English dialogue when language is 'en'."""
    engine = CommentaryEngine(temp_dir=Path("temp/test_lang"))
    cues = engine.generate_script(
        duration=600.0,
        episode_number=148,
        persona=CommentaryPersona.CASUAL,
        language="en",
    )
    assert len(cues) >= 4
    intro = cues[0]
    assert "Hey everyone, welcome back to Last Day on Earth" in intro.text


def test_survivor_privacy_adistar656_sanitized():
    """STRICT PRIVACY: Verify that username 'adistar656' is NEVER included in any spoken cue."""
    engine = CommentaryEngine(temp_dir=Path("temp/test_lang"))

    # Mock gameplay event containing the username
    mock_event = GameplayEvent(
        start_time=60.0,
        end_time=62.0,
        action_type="combat",
        description="Survivor adistar656 eliminates toxic spitter",
    )

    cues = engine.generate_script(
        duration=300.0,
        episode_number=148,
        persona=CommentaryPersona.CASUAL,
        events=[mock_event],
        language="hi",
    )

    for cue in cues:
        assert "adistar656" not in cue.text.lower(), f"Privacy violation found in cue: {cue.text}"


def test_hinglish_event_cue_formatting():
    """Verify _format_event_cue returns Hinglish phrases for events when language is 'hi'."""
    engine = CommentaryEngine(temp_dir=Path("temp/test_lang"))

    # Combat event
    combat_text, combat_topic = engine._format_event_cue(
        event_type="combat",
        description="bunker frenzied giant",
        persona=CommentaryPersona.CASUAL,
        language="hi",
    )
    assert "Enemy movement" in combat_text or "spot kiya" in combat_text
    assert combat_topic == "Combat & Defense Strategy"

    # Crafting event
    craft_text, craft_topic = engine._format_event_cue(
        event_type="craft",
        description="iron smelting",
        persona=CommentaryPersona.CASUAL,
        language="hi",
    )
    assert "Production check" in craft_text or "workbenches" in craft_text
    assert craft_topic == "Crafting & Smelting Queue"


def test_regional_voice_map_has_english():
    """Verify REGIONAL_VOICE_MAP includes English for reciprocal translation."""
    assert "en" in REGIONAL_VOICE_MAP
    assert REGIONAL_VOICE_MAP["en"]["voice"] == "en-US-GuyNeural"
    assert "hi" in REGIONAL_VOICE_MAP
