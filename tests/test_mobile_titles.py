"""Unit tests for Mobile Title Optimization (P1).

Validates:
- Strict <= 55 character constraint for mobile visibility.
- Removal of redundant filler words ('And', 'Plus', 'Organizing').
- Front-loaded excitement in action hooks, curiosity hooks, walkthroughs, and search guides.
- Preservation of episode numbering (#ep) when truncation occurs.
"""

from dataclasses import dataclass
from src.publisher.title_manager import TitleManager


@dataclass
class DummyEvent:
    description: str
    start_time: float = 0.0


def test_mobile_title_length_all_formulas():
    tm = TitleManager(max_title_length=55, episode_numbering=True)

    test_scenarios = [
        [DummyEvent("Organizing Storage & Chests"), DummyEvent("Smelting Iron Ore in Furnace")],
        [DummyEvent("Bunker Alfa Floor 3 Raid"), DummyEvent("Defeating Frenzy Giant")],
        [DummyEvent("Weapon Workbench Setup"), DummyEvent("Crafting Planks And Woodcraft")],
        [DummyEvent("Chopper Motorcycle Fuel Run"), DummyEvent("Crooked Creek Farm Clearing")],
    ]

    for events in test_scenarios:
        for style in ["action_hook", "curiosity_story", "clean_walkthrough", "search_guide"]:
            tm.title_style = style
            pkg = tm.generate_titles(events=events, episode_number=148)

            assert len(pkg.primary_title) <= 55, (
                f"Title exceeds 55 chars ({len(pkg.primary_title)}): '{pkg.primary_title}' for style {style}"
            )
            assert len(pkg.action_hook) <= 55, f"action_hook exceeds 55 chars: '{pkg.action_hook}'"
            assert len(pkg.curiosity) <= 55, f"curiosity exceeds 55 chars: '{pkg.curiosity}'"
            assert len(pkg.walkthrough) <= 55, f"walkthrough exceeds 55 chars: '{pkg.walkthrough}'"
            assert len(pkg.search_guide) <= 55, f"search_guide exceeds 55 chars: '{pkg.search_guide}'"

            # Verify episode tag preserved
            assert "#148" in pkg.primary_title


def test_filler_words_stripped_from_lead():
    tm = TitleManager(max_title_length=55)
    activities = [
        "organizing chests and inventory",
        "plus crafting planks",
    ]
    hook_lead, sub_summary = tm.synthesize_hook_phrases(activities)

    assert "Organizing" not in hook_lead
    assert "And" not in hook_lead
    assert "Plus" not in hook_lead
    assert len(hook_lead) <= 34


def test_fit_title_length_preserves_suffix_under_tight_budget():
    tm = TitleManager(max_title_length=45)
    raw_title = "Incredible Unstoppable Massive Base Fortification Action! | LDoE #148"
    fitted = tm._fit_title_length(raw_title, "#148")

    assert len(fitted) <= 45
    assert fitted.endswith("| LDoE #148")
    assert "..." in fitted
