"""Unit tests for automated motion detection, idle trimming, and YouTube CC generation."""

import numpy as np
import cv2

from src.processor.motion_detector import MotionDetector, IdleSegment
from src.subtitles.event_analyzer import GameplayEvent, SubtitleGenerator
from src.config import get_settings


def test_idle_segment_dataclass():
    segment = IdleSegment(start_time=12.5, end_time=24.0, reason="player_inactivity", confidence=0.95)
    assert segment.duration == 11.5
    d = segment.to_dict()
    assert d["start_time"] == 12.5
    assert d["end_time"] == 24.0
    assert d["duration"] == 11.5
    assert d["reason"] == "player_inactivity"
    assert d["confidence"] == 0.95


def test_compute_keep_intervals_empty():
    md = MotionDetector()
    intervals = md.compute_keep_intervals(total_duration=100.0, idle_segments=[])
    assert intervals == [(0.0, 100.0)]

    zero_intervals = md.compute_keep_intervals(total_duration=0.0, idle_segments=[])
    assert zero_intervals == []


def test_compute_keep_intervals_single_middle():
    md = MotionDetector()
    idles = [IdleSegment(start_time=20.0, end_time=35.0)]
    intervals = md.compute_keep_intervals(total_duration=60.0, idle_segments=idles)
    assert len(intervals) == 2
    assert intervals[0] == (0.0, 20.0)
    assert intervals[1] == (35.0, 60.0)


def test_compute_keep_intervals_start_and_end():
    md = MotionDetector()
    idles = [
        IdleSegment(start_time=0.0, end_time=10.0),
        IdleSegment(start_time=50.0, end_time=60.0),
    ]
    intervals = md.compute_keep_intervals(total_duration=60.0, idle_segments=idles)
    assert len(intervals) == 1
    assert intervals[0] == (10.0, 50.0)


def test_compute_keep_intervals_overlapping():
    md = MotionDetector()
    idles = [
        IdleSegment(start_time=15.0, end_time=25.0),
        IdleSegment(start_time=24.5, end_time=32.0),
    ]
    intervals = md.compute_keep_intervals(total_duration=50.0, idle_segments=idles)
    assert len(intervals) == 2
    assert intervals[0] == (0.0, 15.0)
    assert intervals[1] == (32.0, 50.0)


def test_adjust_event_timestamps():
    md = MotionDetector()
    events = [
        GameplayEvent(start_time=5.0, end_time=10.0, action_type="intro", description="Intro"),
        GameplayEvent(start_time=22.0, end_time=28.0, action_type="idle", description="In Idle"),
        GameplayEvent(start_time=40.0, end_time=45.0, action_type="combat", description="Fight"),
    ]
    idles = [IdleSegment(start_time=20.0, end_time=30.0)]  # 10s excised

    adjusted = md.adjust_event_timestamps(events, idles)
    # Event 1 unchanged
    assert adjusted[0].description == "Intro"
    assert adjusted[0].start_time == 5.0
    assert adjusted[0].end_time == 10.0

    # Event 2 dropped because inside idle
    # Event 3 shifted by 10s
    assert len(adjusted) == 2
    assert adjusted[1].description == "Fight"
    assert adjusted[1].start_time == 30.0
    assert adjusted[1].end_time == 35.0


def test_freezedetect_output_parsing(monkeypatch, tmp_path):
    md = MotionDetector(temp_dir=tmp_path)
    fake_video = tmp_path / "fake.mp4"
    fake_video.touch()

    class MockSubprocessResult:
        returncode = 0
        stderr = (
            "[Parsed_freezedetect_0 @ 00000] lavfi.freezedetect.freeze_start: 12.4\n"
            "[Parsed_freezedetect_0 @ 00000] lavfi.freezedetect.freeze_duration: 8.6\n"
            "[Parsed_freezedetect_0 @ 00000] lavfi.freezedetect.freeze_end: 21.0\n"
        )
        stdout = ""

    monkeypatch.setattr("subprocess.run", lambda *args, **kwargs: MockSubprocessResult())
    segments = md._detect_with_ffmpeg_freezedetect(fake_video, min_idle_duration=5.0)
    assert len(segments) == 1
    assert segments[0].start_time == 12.4
    assert segments[0].end_time == 21.0
    assert segments[0].duration == 8.6


def test_opencv_motion_detection_synthetic(tmp_path):
    """Generates a small synthetic video with motion, idle static frames, and motion."""
    video_path = tmp_path / "synthetic_gameplay.mp4"
    width, height = 320, 240
    fps = 10.0
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(str(video_path), fourcc, fps, (width, height))

    # Phase 1: 0.0s - 2.0s: Active motion (moving circle)
    for i in range(20):
        frame = np.zeros((height, width, 3), dtype=np.uint8)
        cv2.circle(frame, (30 + i * 10, 120), 20, (0, 255, 0), -1)
        out.write(frame)

    # Phase 2: 2.0s - 6.0s (4.0s): Completely idle static screen
    static_frame = np.zeros((height, width, 3), dtype=np.uint8)
    cv2.circle(static_frame, (230, 120), 20, (0, 255, 0), -1)
    for _ in range(40):
        out.write(static_frame)

    # Phase 3: 6.0s - 8.0s: Active motion resumes
    for i in range(20):
        frame = np.zeros((height, width, 3), dtype=np.uint8)
        cv2.circle(frame, (230 - i * 10, 120), 20, (0, 0, 255), -1)
        out.write(frame)

    out.release()

    md = MotionDetector(temp_dir=tmp_path)
    # Detect idle segments >= 3.0s
    segments = md.detect_idle_segments(
        video_path=video_path,
        min_idle_duration=3.0,
        motion_threshold=0.01,
        sample_interval=0.2,
    )

    assert len(segments) == 1
    # Idle segment should start around ~1.8s - 2.2s and end around ~5.8s - 6.2s
    assert 1.5 <= segments[0].start_time <= 2.5
    assert 5.5 <= segments[0].end_time <= 6.5
    assert segments[0].duration >= 3.0


def test_config_idle_and_subtitle_defaults():
    settings = get_settings()
    assert settings.processing.remove_idle_segments is True
    assert settings.processing.min_idle_duration == 15.0
    assert settings.processing.idle_motion_threshold == 0.015
    # In-game caption burning is disabled by default for pristine video
    assert settings.processing.burn_in_subtitles is False


def test_subtitle_generator_generate_srt(tmp_path):
    sub_gen = SubtitleGenerator()
    events = [
        GameplayEvent(start_time=0.0, end_time=4.5, action_type="intro", description="Entering Base"),
        GameplayEvent(start_time=15.2, end_time=20.8, action_type="combat", description="Bunker Alfa Infiltration"),
    ]
    srt_out = tmp_path / "test_captions.srt"
    res = sub_gen.generate_srt(events, srt_out)

    assert res.exists()
    content = srt_out.read_text(encoding="utf-8")
    assert "1\n00:00:00,000 --> 00:00:04,500\nEntering Base" in content
    assert "2\n00:00:15,200 --> 00:00:20,800\nBunker Alfa Infiltration" in content
