"""Unit tests for Anti-Repetition Engine Overhaul (P2).

Validates:
- 30-episode historical lookback window.
- Granular event highlight extraction (floors, bosses, weapons, crates).
- Elimination of static fallback array in favor of dynamic event-driven synthesis.
- Strict bigram overlap penalty preventing repeated core phrases across consecutive episodes.
- Strict <= 55 characters limit on all dynamically synthesized fallback titles.
"""

import json
from dataclasses import dataclass
from pathlib import Path
from src.publisher.title_manager import TitleManager


@dataclass
class DummyEvent:
    description: str
    start_time: float = 0.0


def test_anti_repetition_lookback_expanded(tmp_path):
    tracker_file = tmp_path / "series_tracker.json"
    episodes = [
        {"episode": i, "title": f"Episode Title #{i} | LDoE #{i}", "video_id": f"vid_{i}"}
        for i in range(1, 41)
    ]
    tracker_file.write_text(json.dumps({"completed_episodes": episodes}), encoding="utf-8")

    tm = TitleManager(tracker_file=tracker_file, anti_repetition_lookback=30)
    recent = tm.get_recent_published_titles()

    assert len(recent) == 30
    assert recent[0] == "Episode Title #40 | LDoE #40"
    assert recent[-1] == "Episode Title #11 | LDoE #11"


def test_granular_event_highlights_extraction():
    tm = TitleManager()
    events = [
        DummyEvent("Bunker Alfa Floor 3 Infiltration"),
        DummyEvent("Wall trick against Frenzy Giant"),
        DummyEvent("Opening Red Crate with Chopper Gas Tank"),
    ]

    highlights = tm.extract_granular_event_highlights(events)

    assert "Bunker Alfa Floor 3" in highlights
    assert "Frenzy Giant Combat" in highlights
    assert "Red Crate Unboxing" in highlights
    assert "Chopper Gas Tank Find" in highlights


def test_bigram_similarity_penalty():
    tm = TitleManager()
    t1 = "Bunker Alfa Infiltration! | LDoE #145"
    t2 = "Bunker Alfa Speed Clear! | LDoE #146"

    # Both share bigram 'bunker alfa'
    score = tm.calculate_title_similarity(t1, t2)
    assert score >= 0.55


def test_dynamic_fallback_synthesizes_unique_event_title(tmp_path):
    tracker_file = tmp_path / "series_tracker.json"
    # Seed tracker with titles that conflict with all standard formulas
    recent_titles = [
        "Base Storage Setup! | LDoE #147",
        "Can We Survive Base Storage Setup? | LDoE #147",
        "Day 147: Base Storage Setup | LDoE #147",
        "Best Base Storage Layout Guide | LDoE #147",
    ]
    completed = [{"episode": 147 - i, "title": t, "video_id": f"vid_{i}"} for i, t in enumerate(recent_titles)]
    tracker_file.write_text(json.dumps({"completed_episodes": completed}), encoding="utf-8")

    tm = TitleManager(tracker_file=tracker_file, max_title_length=55)
    events = [
        DummyEvent("Base Storage Setup"),
        DummyEvent("Frenzy Giant Combat in Red Pine Zone"),
    ]

    pkg = tm.generate_titles(events=events, episode_number=148)

    assert pkg.anti_repetition_applied is True
    # Primary title must be dynamically synthesized and NOT match any of the repetitive recent titles
    assert pkg.primary_title not in recent_titles
    assert len(pkg.primary_title) <= 55
    assert "#148" in pkg.primary_title
