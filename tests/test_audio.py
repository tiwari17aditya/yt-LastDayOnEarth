"""Tests for audio track catalog and ducking filter building."""

import json
from pathlib import Path
from src.audio.selector import AudioMixer


def test_audio_mixer_load_catalog():
    mixer = AudioMixer(library_path=Path("config/music_library.json"))
    assert len(mixer.tracks) == 20
    assert mixer.tracks[0]["title"] == "Carefree"
    assert mixer.tracks[0]["attribution_required"] is True


def test_audio_ducking_filter():
    mixer = AudioMixer(library_path=Path("config/music_library.json"))
    filtergraph = mixer.build_ffmpeg_audio_filter(ducking_db="-22dB")
    assert "aloop=loop=-1" in filtergraph
    assert "volume=-22dB" in filtergraph
    assert "amix=inputs=2" in filtergraph


def test_random_loop_sequence(tmp_path):
    mixer = AudioMixer(library_path=Path("config/music_library.json"))
    out_audio = tmp_path / "stitched.m4a"
    # 600 seconds guarantees multiple tracks since the longest single track is 336s
    result_path, tracks = mixer.create_random_loop_sequence(target_duration=600.0, output_path=out_audio)
    
    assert result_path.exists()
    assert len(tracks) >= 2
    assert tracks[0]["start_time"] == 0.0
    assert tracks[1]["start_time"] > 0.0
    # Ensure no consecutive duplicates
    for i in range(len(tracks) - 1):
        assert tracks[i]["id"] != tracks[i+1]["id"]
