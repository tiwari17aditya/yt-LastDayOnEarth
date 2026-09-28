"""Unit tests for Dynamic Tag Generator and YouTube Description Hashtag integration."""

import re
from unittest.mock import MagicMock, patch
from src.publisher.metadata_generator import DynamicTagGenerator
from src.publisher.youtube_client import YouTubeClient
from src.subtitles.event_analyzer import GameplayEvent


def test_dynamic_tag_generator_produces_50_tags():
    generator = DynamicTagGenerator(target_hashtag_count=50)
    events = [
        GameplayEvent(start_time=0.0, end_time=1.0, action_type="nav", description="Global Map"),
        GameplayEvent(start_time=10.0, end_time=11.0, action_type="craft", description="Crafting Planks"),
        GameplayEvent(start_time=20.0, end_time=21.0, action_type="craft", description="Weapon Bench"),
        GameplayEvent(start_time=30.0, end_time=31.0, action_type="smelt", description="Smelting Iron"),
    ]

    tags = generator.generate_dynamic_hashtags(
        video_title="Last_Day_on_Earth_Home_Base",
        events=events,
        date_str="27 Sep, 2026",
    )

    assert len(tags) == 50
    # Every tag must start with '#'
    assert all(t.startswith("#") for t in tags)
    # Check no duplicate tags (case-insensitive)
    lower_tags = [t.lower() for t in tags]
    assert len(lower_tags) == len(set(lower_tags))


def test_dynamic_tags_adapt_to_gameplay_content():
    generator = DynamicTagGenerator(target_hashtag_count=50)

    # Video 1: Crafting & Smelting
    crafting_events = [
        GameplayEvent(start_time=0.0, end_time=1.0, action_type="craft", description="Crafting Planks"),
        GameplayEvent(start_time=10.0, end_time=11.0, action_type="smelt", description="Smelting Iron"),
        GameplayEvent(start_time=20.0, end_time=21.0, action_type="storage", description="Organizing Chests"),
    ]
    crafting_tags = generator.generate_dynamic_hashtags(
        video_title="Base Workshop & Smelting",
        events=crafting_events,
        date_str="27 Sep, 2026",
    )

    # Video 2: Bunker Alfa Raid
    bunker_events = [
        GameplayEvent(start_time=0.0, end_time=1.0, action_type="raid", description="Bunker Alfa"),
        GameplayEvent(start_time=10.0, end_time=11.0, action_type="combat", description="Blind One Run"),
        GameplayEvent(start_time=20.0, end_time=21.0, action_type="combat", description="C4 Breach"),
    ]
    bunker_tags = generator.generate_dynamic_hashtags(
        video_title="Bunker Alfa Floor 3 Raid",
        events=bunker_events,
        date_str="27 Sep, 2026",
    )

    assert len(crafting_tags) == 50
    assert len(bunker_tags) == 50
    # They should not be identical because tags are dynamically chosen based on events
    assert crafting_tags != bunker_tags

    # Crafting tags should prioritize crafting keywords
    crafting_set = {t.lower() for t in crafting_tags}
    assert "#ldoecrafting" in crafting_set or "#woodworkingbench" in crafting_set or "#smeltingfurnace" in crafting_set

    # Bunker tags should prioritize bunker keywords
    bunker_set = {t.lower() for t in bunker_tags}
    assert "#bunkeralfa" in bunker_set or "#ldoeraid" in bunker_set or "#ldoebunker" in bunker_set


def test_generate_video_tags_under_500_chars():
    generator = DynamicTagGenerator(target_hashtag_count=50)
    events = [
        GameplayEvent(start_time=0.0, end_time=1.0, action_type="craft", description="Crafting & Planks"),
        GameplayEvent(start_time=10.0, end_time=11.0, action_type="smelt", description="Smelting <Iron> & Furnaces, Ore"),
    ]
    hashtags = generator.generate_dynamic_hashtags("LDoE Workshop", events)
    video_tags = generator.generate_video_tags("LDoE Workshop", events, hashtags)

    assert isinstance(video_tags, list)
    assert len(video_tags) > 10

    # Ensure no forbidden characters
    for tag in video_tags:
        assert "<" not in tag
        assert ">" not in tag
        assert "," not in tag
        assert '"' not in tag
        assert not tag.startswith("#")

    # YouTube serialized length: accounts for double quotes on multi-word tags and commas
    serialized_len = generator.calculate_youtube_tags_length(video_tags)
    assert serialized_len <= 400
    assert serialized_len <= 500



def test_gemini_fallback_on_api_error():
    generator = DynamicTagGenerator(
        gemini_api_key="valid-looking-key-1234567890",
        gemini_model="gemini-2.5-flash",
        target_hashtag_count=50,
    )
    events = [
        GameplayEvent(start_time=0.0, end_time=1.0, action_type="nav", description="Global Map"),
    ]

    with patch.object(generator, "_generate_gemini_hashtags", side_effect=Exception("API Quota Exceeded 429")):
        tags = generator.generate_dynamic_hashtags("LDoE Test", events)
        assert len(tags) == 50
        assert all(t.startswith("#") for t in tags)


def test_gemini_success_parses_hashtags():
    generator = DynamicTagGenerator(
        gemini_api_key="valid-looking-key-1234567890",
        gemini_model="gemini-2.5-flash",
        target_hashtag_count=50,
    )
    mock_tags = [f"#TestTag{i}" for i in range(50)]

    with patch.object(generator, "_generate_gemini_hashtags", return_value=mock_tags):
        tags = generator.generate_dynamic_hashtags("LDoE Test", [])
        assert len(tags) == 50
        assert tags[0] == "#TestTag0"


def test_youtube_client_generate_metadata_includes_50_tags_in_description():
    client = YouTubeClient()
    events = [
        GameplayEvent(start_time=0.0, end_time=1.0, action_type="craft", description="Woodworking Bench"),
        GameplayEvent(start_time=15.0, end_time=16.0, action_type="smelt", description="Smelting Iron"),
    ]

    metadata = client.generate_metadata(
        video_title="ScreenRecording_Workshop_Run",
        events=events,
    )

    # Verify description contains around 50 trending hashtags (excluding episode number like #8)
    extracted_hashtags = re.findall(r"#\w+", metadata.description)
    trending_hashtags = [h for h in extracted_hashtags if not h[1:].isdigit()]
    assert len(trending_hashtags) == 50

    # Verify metadata.tags contains dynamic tags
    assert len(metadata.tags) > 10
    total_tags_chars = sum(len(t) for t in metadata.tags) + len(metadata.tags) - 1
    assert total_tags_chars <= 500

    # Verify description mentions episode highlights
    assert "woodworking bench" in metadata.description.lower()
