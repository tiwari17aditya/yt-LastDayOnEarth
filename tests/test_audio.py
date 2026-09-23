"""Tests for audio track catalog and ducking filter building."""

import json
from pathlib import Path
from src.audio.selector import AudioMixer


def test_audio_mixer_load_catalog():
    mixer = AudioMixer(library_path=Path("config/music_library.json"))
    assert len(mixer.tracks) == 20
    assert mixer.tracks[0]["title"] == "Survival Instinct"
    assert mixer.tracks[0]["attribution_required"] is True


def test_audio_ducking_filter():
    mixer = AudioMixer(library_path=Path("config/music_library.json"))
    filtergraph = mixer.build_ffmpeg_audio_filter(ducking_db="-22dB")
    assert "aloop=loop=-1" in filtergraph
    assert "volume=-22dB" in filtergraph
    assert "amix=inputs=2" in filtergraph
