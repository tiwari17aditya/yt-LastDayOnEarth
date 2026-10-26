"""Unit tests for the audience reach maximization features.

Covers:
- Search-friendly guide/tutorial titles (+37% retention formula).
- Context-aware pinned engagement comments and grind empathy prompts.
- Viral moments detection for YouTube Shorts (fails, panic, rare crate unboxing).
"""

from dataclasses import dataclass
from src.publisher.title_manager import TitleManager, TitlePackage
from src.publisher.youtube_client import YouTubeClient
from src.processor.shorts_generator import ShortsGenerator


@dataclass
class DummyEvent:
    description: str
    start_time: float


def test_title_manager_search_guide_formula():
    tm = TitleManager(title_style="search_guide", episode_numbering=True)

    # Test Bunker Alfa event
    events = [
        DummyEvent(description="Entering Bunker Alfa", start_time=10.0),
        DummyEvent(description="Bunker Alfa Raid Floor 2", start_time=45.0),
    ]
    pkg = tm.generate_titles(events=events, episode_number=5)

    assert "Fastest Way to Clear Bunker Alfa" in pkg.search_guide
    assert pkg.primary_title == pkg.search_guide
    assert "#5" in pkg.primary_title
    assert len(pkg.primary_title) <= 100

    # Test Chopper event
    events_chopper = [
        DummyEvent(description="Chopper Assembly", start_time=20.0),
    ]
    pkg_chopper = tm.generate_titles(events=events_chopper, episode_number=6)
    assert "How to Get the Chopper Fast" in pkg_chopper.search_guide


def test_engagement_comment_context_selection():
    client = YouTubeClient()

    # When chopper event is present
    chopper_events = [DummyEvent(description="Upgrading Chopper engine", start_time=30.0)]
    # Use fake youtube object
    class FakeCommentThreads:
        def __init__(self):
            self.posted_text = []

        def insert(self, part, body):
            self.posted_text.append(body["snippet"]["topLevelComment"]["snippet"]["textOriginal"])
            class Exec:
                def execute(self):
                    return {"id": "comment_123"}
            return Exec()

    ct_instance = FakeCommentThreads()

    class FakeYouTube:
        def commentThreads(self):
            return ct_instance

    fake_yt = FakeYouTube()

    cid = client.post_engagement_comment(
        youtube=fake_yt,
        video_id="TEST_VID",
        episode_number=7,
        events=chopper_events,
    )

    assert cid == "comment_123"
    assert len(ct_instance.posted_text) == 1
    assert "What level is your Chopper right now" in ct_instance.posted_text[0]


def test_shorts_generator_auto_detect_viral_moment():
    gen = ShortsGenerator()

    # Test fail/panic detection
    fail_events = [
        DummyEvent(description="Looting base", start_time=20.0),
        DummyEvent(description="Frenzy Giant attack and death near gate", start_time=75.0),
    ]
    viral_data = gen.auto_detect_viral_moment(fail_events, min_start=30.0)

    assert viral_data["hook_type"] == "fail_panic"
    assert viral_data["headline"] == "DISASTER MOMENT?!"
    assert viral_data["start_time"] == 75.0

    # Test rare loot drop detection
    loot_events = [
        DummyEvent(description="Running in woods", start_time=15.0),
        DummyEvent(description="Opening red crate and found titanium", start_time=60.0),
    ]
    loot_data = gen.auto_detect_viral_moment(loot_events, min_start=30.0)

    assert loot_data["hook_type"] == "rare_loot"
    assert loot_data["headline"] == "RAREST LOOT DROP?!"
    assert loot_data["start_time"] == 60.0
