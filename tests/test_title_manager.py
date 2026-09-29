"""Unit tests for TitleManager dynamic event synthesis and episode tracking."""

import json
from pathlib import Path
from dataclasses import dataclass
from src.publisher.title_manager import TitleManager


@dataclass
class DummyEvent:
    start_time: float
    end_time: float
    action_type: str
    description: str


def test_title_manager_initializes_tracker(tmp_path):
    tracker_file = tmp_path / "series_tracker.json"
    mgr = TitleManager(tracker_file=tracker_file)

    assert tracker_file.exists()
    assert mgr.get_current_episode() == 1


def test_title_manager_advances_episode(tmp_path):
    tracker_file = tmp_path / "series_tracker.json"
    mgr = TitleManager(tracker_file=tracker_file)

    next_ep = mgr.advance_episode(title="Test Episode 1", job_id="job_001")
    assert next_ep == 2
    assert mgr.get_current_episode() == 2

    # Check file persistence
    data = json.loads(tracker_file.read_text(encoding="utf-8"))
    assert data["current_episode"] == 2
    assert len(data["completed_episodes"]) == 1
    assert data["completed_episodes"][0]["title"] == "Test Episode 1"


def test_title_manager_synthesizes_action_hook(tmp_path):
    tracker_file = tmp_path / "series_tracker.json"
    mgr = TitleManager(tracker_file=tracker_file, title_style="action_hook", series_prefix="LDoE")

    events = [
        DummyEvent(start_time=0.0, end_time=1.0, action_type="nav", description="Global Map"),
        DummyEvent(start_time=20.0, end_time=21.0, action_type="craft", description="Crafting Planks"),
        DummyEvent(start_time=128.0, end_time=129.0, action_type="craft", description="Smelting Iron"),
    ]

    pkg = mgr.generate_titles(events=events, episode_number=1)

    assert "WOODCRAFT & PLANKS" in pkg.action_hook.upper() or "FURNACE SMELTING" in pkg.action_hook.upper()
    assert "#1" in pkg.action_hook
    assert pkg.primary_title == pkg.action_hook
    assert len(pkg.primary_title) <= 100
    assert pkg.episode_number == 1
    assert "Can We" in pkg.curiosity
    assert "Surviving Day 1" in pkg.walkthrough


def test_title_manager_respects_title_styles(tmp_path):
    tracker_file = tmp_path / "series_tracker.json"
    events = [DummyEvent(0.0, 1.0, "craft", "Crafting Planks")]

    mgr_curiosity = TitleManager(tracker_file=tracker_file, title_style="curiosity_story")
    pkg1 = mgr_curiosity.generate_titles(events, episode_number=3)
    assert pkg1.primary_title == pkg1.curiosity

    mgr_walkthrough = TitleManager(tracker_file=tracker_file, title_style="clean_walkthrough")
    pkg2 = mgr_walkthrough.generate_titles(events, episode_number=3)
    assert pkg2.primary_title == pkg2.walkthrough


def test_title_manager_length_truncation(tmp_path):
    tracker_file = tmp_path / "series_tracker.json"
    mgr = TitleManager(tracker_file=tracker_file, max_title_length=40)

    events = [
        DummyEvent(0.0, 1.0, "craft", "Massive Woodcraft Planks Storage Overhaul Furnaces"),
        DummyEvent(10.0, 11.0, "craft", "Extreme Zombie Horde Defense And Base Fortification"),
    ]

    pkg = mgr.generate_titles(events, episode_number=99)
    assert len(pkg.primary_title) <= 40
    assert "#99" in pkg.primary_title


def test_title_manager_sync_with_youtube_service(tmp_path):
    from unittest.mock import MagicMock
    tracker_file = tmp_path / "series_tracker.json"
    mgr = TitleManager(tracker_file=tracker_file)

    mock_yt = MagicMock()
    mock_yt.playlists().list().execute.return_value = {
        "items": [
            {"id": "p_ldoe", "snippet": {"title": "Last Day on Earth Series"}}
        ]
    }
    mock_yt.playlistItems().list().execute.return_value = {
        "items": [
            {"snippet": {"title": "Base Defense #10"}},
            {"snippet": {"title": "Smelting Planks #9"}},
        ]
    }
    mock_yt.playlistItems().list_next.return_value = None

    next_ep = mgr.sync_with_youtube(youtube_service=mock_yt)
    assert next_ep == 11
    assert mgr.get_current_episode() == 11


def test_title_manager_sync_does_not_regress_if_tracker_higher(tmp_path):
    from unittest.mock import MagicMock
    tracker_file = tmp_path / "series_tracker.json"
    tracker_file.write_text(json.dumps({"series_name": "LDoE", "current_episode": 15}), encoding="utf-8")
    mgr = TitleManager(tracker_file=tracker_file)

    mock_yt = MagicMock()
    mock_yt.playlists().list().execute.return_value = {
        "items": [{"id": "p_ldoe", "snippet": {"title": "Last Day on Earth Series"}}]
    }
    mock_yt.playlistItems().list().execute.return_value = {
        "items": [{"snippet": {"title": "Base Defense #10"}}]
    }
    mock_yt.playlistItems().list_next.return_value = None

    next_ep = mgr.sync_with_youtube(youtube_service=mock_yt)
    assert next_ep == 15
    assert mgr.get_current_episode() == 15


def test_title_manager_sync_graceful_on_no_creds(tmp_path, monkeypatch):
    tracker_file = tmp_path / "series_tracker.json"
    mgr = TitleManager(tracker_file=tracker_file)
    monkeypatch.setattr("src.google_auth.get_google_credentials", lambda *a, **kw: None)

    # Should safely return tracker value without error
    ep = mgr.get_current_episode(sync_youtube=True)
    assert ep == 1

