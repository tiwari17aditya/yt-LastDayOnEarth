"""Unit tests for Gemini Vision event analyzer and Title Anti-Repetition Guard."""

import json
from dataclasses import dataclass
from pathlib import Path
from unittest.mock import MagicMock, patch

from src.subtitles.event_analyzer import SubtitleGenerator, GameplayEvent
from src.publisher.title_manager import TitleManager, TitlePackage


@dataclass
class DummyEvent:
    description: str
    start_time: float
    action_type: str = "base"


def test_title_similarity_computation():
    tm = TitleManager()

    # Identical titles with different episode numbers
    t1 = "Entering Home Base & Entering Home Base Part 2! | LDoE Survival #65"
    t2 = "Entering Home Base & Entering Home Base Part 2! | LDoE Survival #66"
    assert tm.calculate_title_similarity(t1, t2) >= 0.85

    # Very similar titles (Home Base repetition)
    t3 = "Home Base Operations & Workshop Smelting! | LDoE Survival #64"
    t4 = "Home Base Operations & Storage Organization! | LDoE Survival #65"
    assert tm.calculate_title_similarity(t3, t4) >= 0.50

    # Completely distinct titles
    t5 = "Fastest Way to Clear Bunker Alfa (F2P Guide) | LDoE #66"
    assert tm.calculate_title_similarity(t1, t5) < 0.20


def test_title_anti_repetition_guard_triggers_rotation(tmp_path):
    tracker_file = tmp_path / "series_tracker.json"
    initial_tracker = {
        "series_name": "Last Day on Earth: Survival",
        "current_episode": 66,
        "completed_episodes": [
            {
                "episode": 64,
                "title": "Home Base Operations & Workshop Smelting! | LDoE Survival #64",
                "video_id": "vid64",
            },
            {
                "episode": 65,
                "title": "Entering Home Base & Base Storage Optimization! | LDoE Survival #65",
                "video_id": "vid65",
            },
        ],
    }
    tracker_file.write_text(json.dumps(initial_tracker), encoding="utf-8")

    tm = TitleManager(
        tracker_file=tracker_file,
        title_style="action_hook",
        episode_numbering=True,
    )

    # Input events that would normally produce a repetitive Home Base / Entering Base title
    events = [
        DummyEvent(description="Entering Home Base", start_time=0.0),
        DummyEvent(description="Base Storage Optimization", start_time=45.0),
    ]

    pkg = tm.generate_titles(events=events, episode_number=66)

    # Anti-repetition guard must have caught the repetition
    assert pkg.anti_repetition_applied is True
    assert pkg.similarity_score >= 0.50
    assert pkg.avoided_recent_title != ""

    # Primary title must NOT be identical to episode 65
    assert pkg.primary_title != "Entering Home Base & Base Storage Optimization! | LDoE Survival #66"
    assert "Survival #66" in pkg.primary_title or "#66" in pkg.primary_title


def test_title_anti_repetition_guard_passes_unique_title(tmp_path):
    tracker_file = tmp_path / "series_tracker.json"
    initial_tracker = {
        "series_name": "Last Day on Earth: Survival",
        "current_episode": 66,
        "completed_episodes": [
            {
                "episode": 65,
                "title": "Entering Home Base & Base Storage Optimization! | LDoE Survival #65",
                "video_id": "vid65",
            },
        ],
    }
    tracker_file.write_text(json.dumps(initial_tracker), encoding="utf-8")

    tm = TitleManager(
        tracker_file=tracker_file,
        title_style="action_hook",
        episode_numbering=True,
    )

    # Non-repetitive event: Bunker Alfa Raid
    events = [
        DummyEvent(description="Bunker Alfa Raid Floor 2", start_time=10.0),
        DummyEvent(description="Frenzied Giant Combat", start_time=60.0),
    ]

    pkg = tm.generate_titles(events=events, episode_number=66)
    assert pkg.anti_repetition_applied is False
    assert "Bunker Alfa" in pkg.primary_title


def test_gemini_vision_event_analyzer_success(tmp_path):
    video_path = tmp_path / "sample.mp4"
    video_path.touch()

    sub_engine = SubtitleGenerator(gemini_api_key="mock_api_key", model_name="gemini-2.5-flash")

    mock_json_response = json.dumps([
        {
            "timestamp": 0.0,
            "action_type": "navigation",
            "description": "Bunker Alfa Terminal Code",
        },
        {
            "timestamp": 45.0,
            "action_type": "combat",
            "description": "Wall Trick vs Frenzied Giant",
        },
        {
            "timestamp": 90.0,
            "action_type": "loot",
            "description": "Opening Red Ticket Crate",
        },
    ])

    mock_resp = MagicMock()
    mock_resp.text = mock_json_response

    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = mock_resp

    with patch("src.subtitles.event_analyzer.SubtitleGenerator.extract_frame_bytes", return_value=b"fake_jpeg_bytes"):
        with patch("google.genai.Client", return_value=mock_client):
            events = sub_engine.analyze_events(video_path)

    assert len(events) == 3
    assert events[0].description == "Bunker Alfa Terminal Code"
    assert events[0].action_type == "navigation"
    assert events[1].description == "Wall Trick vs Frenzied Giant"
    assert events[1].action_type == "combat"
    assert events[2].description == "Opening Red Ticket Crate"
    assert events[2].action_type == "loot"


def test_gemini_vision_event_analyzer_fallback_on_error(tmp_path):
    video_path = tmp_path / "sample.mp4"
    video_path.touch()

    sub_engine = SubtitleGenerator(gemini_api_key="mock_api_key", model_name="gemini-2.5-flash")

    # Simulate Gemini API raising an error (e.g. network disconnect or rate limit)
    with patch("src.subtitles.event_analyzer.SubtitleGenerator.extract_frame_bytes", return_value=b"fake_jpeg_bytes"):
        with patch("google.genai.Client", side_effect=Exception("Rate limit reached")):
            with patch("src.subtitles.event_analyzer.SubtitleGenerator.analyze_frame_signature", return_value=("Home Base Operations", "base")):
                events = sub_engine.analyze_events(video_path)

    # Must not raise an exception; must fall back gracefully to non-repetitive events
    assert len(events) > 0
    descriptions = [e.description for e in events]
    # Check that "Part 2" is not created
    assert not any("Part 2" in d for d in descriptions)
