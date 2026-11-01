"""Unit tests for automated in-game advertisement detection and excision."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from src.config import ProcessingSettings
from src.privacy.ad_detector import AdDetector, AdSegment
from src.processor.ad_remover import AdRemover


class MockEvent:
    def __init__(self, start_time: float, end_time: float, description: str):
        self.start_time = start_time
        self.end_time = end_time
        self.description = description


def test_ad_segment_dataclass():
    ad = AdSegment(start_time=10.5, end_time=40.5, ad_type="rewarded_ad", description="Royal Match")
    assert ad.duration == 30.0
    d = ad.to_dict()
    assert d["start_time"] == 10.5
    assert d["end_time"] == 40.5
    assert d["duration"] == 30.0
    assert d["ad_type"] == "rewarded_ad"


def test_config_ad_removal_defaults():
    settings = ProcessingSettings()
    assert settings.remove_ads is True
    assert settings.min_ad_duration == 4.0
    assert settings.max_ad_duration == 120.0


def test_merge_adjacent_ad_segments():
    detector = AdDetector()
    # Overlapping and close segments
    segments = [
        AdSegment(start_time=10.0, end_time=30.0, description="Ad video"),
        AdSegment(start_time=31.0, end_time=45.0, description="Ad endcard"),
        AdSegment(start_time=100.0, end_time=130.0, description="Second ad"),
    ]
    merged = detector.merge_adjacent_segments(segments, max_gap=2.0)
    assert len(merged) == 2
    assert merged[0].start_time == 10.0
    assert merged[0].end_time == 45.0
    assert merged[1].start_time == 100.0
    assert merged[1].end_time == 130.0


def test_compute_keep_intervals():
    remover = AdRemover()
    # Ad in middle of 100s video
    ads = [AdSegment(start_time=30.0, end_time=60.0)]
    intervals = remover.compute_keep_intervals(total_duration=100.0, ad_segments=ads)
    assert intervals == [(0.0, 30.0), (60.0, 100.0)]

    # Ad at beginning
    ads_start = [AdSegment(start_time=0.0, end_time=25.0)]
    intervals_start = remover.compute_keep_intervals(total_duration=100.0, ad_segments=ads_start)
    assert intervals_start == [(25.0, 100.0)]

    # Ad at end
    ads_end = [AdSegment(start_time=70.0, end_time=100.0)]
    intervals_end = remover.compute_keep_intervals(total_duration=100.0, ad_segments=ads_end)
    assert intervals_end == [(0.0, 70.0)]

    # Multiple ads
    ads_multi = [
        AdSegment(start_time=20.0, end_time=45.0),
        AdSegment(start_time=80.0, end_time=110.0),
    ]
    intervals_multi = remover.compute_keep_intervals(total_duration=150.0, ad_segments=ads_multi)
    assert intervals_multi == [(0.0, 20.0), (45.0, 80.0), (110.0, 150.0)]

    # No ads
    assert remover.compute_keep_intervals(total_duration=120.0, ad_segments=[]) == [(0.0, 120.0)]


def test_adjust_event_timestamps():
    remover = AdRemover()
    ads = [
        AdSegment(start_time=30.0, end_time=60.0),  # 30s excised
        AdSegment(start_time=120.0, end_time=140.0), # 20s excised
    ]
    events = [
        MockEvent(start_time=10.0, end_time=15.0, description="Before ad"),
        MockEvent(start_time=40.0, end_time=50.0, description="Inside ad"),
        MockEvent(start_time=70.0, end_time=80.0, description="After first ad"),
        MockEvent(start_time=150.0, end_time=160.0, description="After second ad"),
    ]

    adjusted = remover.adjust_event_timestamps(events, ads)
    assert len(adjusted) == 3
    # Event 1: untouched
    assert adjusted[0].description == "Before ad"
    assert adjusted[0].start_time == 10.0
    assert adjusted[0].end_time == 15.0

    # Event 2 (inside ad) was removed

    # Event 3: shifted by 30s
    assert adjusted[1].description == "After first ad"
    assert adjusted[1].start_time == 40.0  # 70 - 30
    assert adjusted[1].end_time == 50.0    # 80 - 30

    # Event 4: shifted by 30 + 20 = 50s
    assert adjusted[2].description == "After second ad"
    assert adjusted[2].start_time == 100.0 # 150 - 50
    assert adjusted[2].end_time == 110.0   # 160 - 50


def test_detect_ads_gemini_parsing():
    detector = AdDetector(gemini_api_key="mock_key")

    mock_response = MagicMock()
    mock_response.text = json.dumps({
        "ad_segments": [
            {
                "start_time": 45.0,
                "end_time": 75.0,
                "ad_type": "rewarded_ad",
                "description": "Royal Match 30s rewarded video",
                "confidence": 0.95
            }
        ]
    })

    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = mock_response

    with patch.object(detector, "extract_keyframes", return_value=[(10.0, b"frame1"), (50.0, b"frame2")]), \
         patch("google.genai.Client", return_value=mock_client):

        ads = detector.detect_ads_with_gemini(video_path=Path("dummy.mp4"), total_duration=120.0)
        assert len(ads) == 1
        assert ads[0].start_time == 45.0
        assert ads[0].end_time == 75.0
        assert ads[0].duration == 30.0
        assert ads[0].ad_type == "rewarded_ad"
        assert "Royal Match" in ads[0].description


def test_remove_ads_ffmpeg_call(tmp_path):
    remover = AdRemover(output_dir=tmp_path)
    dummy_input = tmp_path / "raw_video.mp4"
    dummy_input.write_bytes(b"dummy_data")
    dummy_clean = tmp_path / "clean_video.mp4"

    ads = [AdSegment(start_time=20.0, end_time=50.0)]

    with patch.object(remover, "get_video_duration", side_effect=[100.0, 70.0]), \
         patch("subprocess.run") as mock_run:

        mock_run.return_value = MagicMock(returncode=0)

        out = remover.remove_ads(
            input_video=dummy_input,
            ad_segments=ads,
            output_video=dummy_clean,
        )

        assert out == dummy_clean
        mock_run.assert_called_once()
        cmd = mock_run.call_args[0][0]
        cmd_str = " ".join(cmd)
        assert "trim=start=0.000:end=20.000" in cmd_str
        assert "trim=start=50.000:end=100.000" in cmd_str
        assert "concat=n=2:v=1:a=1" in cmd_str
