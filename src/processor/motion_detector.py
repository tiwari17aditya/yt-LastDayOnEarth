"""Automated in-game inactivity / idle motion detector and segment trimmer for Last Day on Earth."""

import re
import subprocess
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np

from src.logging_config import get_logger
from src.exceptions import VideoProcessingError

logger = get_logger(component="MotionDetector")


@dataclass
class IdleSegment:
    """Represents a detected idle/inactivity segment where no significant motion occurred."""
    start_time: float
    end_time: float
    reason: str = "inactivity"
    confidence: float = 0.95

    @property
    def duration(self) -> float:
        return max(0.0, round(self.end_time - self.start_time, 2))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "start_time": round(self.start_time, 2),
            "end_time": round(self.end_time, 2),
            "duration": self.duration,
            "reason": self.reason,
            "confidence": round(self.confidence, 2),
        }


class BaseMotionDetector(ABC):
    """Abstract interface for motion and inactivity detection."""

    @abstractmethod
    def detect_idle_segments(
        self,
        video_path: Path,
        min_idle_duration: float = 7.0,
        motion_threshold: float = 0.015,
        sample_interval: float = 0.5,
    ) -> List[IdleSegment]:
        """Detect intervals in video where player/gameplay is idle without movement."""
        pass

    @abstractmethod
    def remove_idle_segments(
        self,
        input_video: Path,
        idle_segments: List[IdleSegment],
        output_video: Optional[Path] = None,
    ) -> Path:
        """Clips out idle segments, preserving only the active movable gameplay."""
        pass


class MotionDetector(BaseMotionDetector):
    """Detects motionless/frozen video intervals via adaptive frame difference & FFmpeg fallback.

    Cuts out dead time where player stepped away, maintaining continuous gameplay flow.
    """

    def __init__(self, temp_dir: Optional[Path] = None) -> None:
        self.temp_dir = temp_dir or Path("temp")
        self.temp_dir.mkdir(parents=True, exist_ok=True)

    def get_video_duration(self, video_path: Path) -> float:
        """Probes video duration in seconds via ffprobe."""
        if not video_path.exists():
            return 0.0
        cmd = [
            "ffprobe",
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(video_path),
        ]
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=30)
            return max(0.0, float(res.stdout.strip()))
        except Exception as e:
            logger.debug(f"Could not probe duration for {video_path}: {e}")
            return 0.0

    def _detect_with_opencv(
        self,
        video_path: Path,
        min_idle_duration: float,
        motion_threshold: float,
        sample_interval: float,
    ) -> List[IdleSegment]:
        """Analyzes frame motion using adaptive grayscale frame differencing."""
        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            raise RuntimeError(f"OpenCV could not open video: {video_path}")

        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        frame_step = max(1, int(round(fps * sample_interval)))

        prev_gray: Optional[np.ndarray] = None
        idle_start: Optional[float] = None
        idle_segments: List[IdleSegment] = []

        current_frame_idx = 0
        while current_frame_idx < total_frames:
            cap.set(cv2.CAP_PROP_POS_FRAMES, current_frame_idx)
            ret, frame = cap.read()
            if not ret or frame is None:
                break

            current_timestamp = current_frame_idx / fps

            # Downscale to 160x90 for ultra-fast motion estimation
            small_frame = cv2.resize(frame, (160, 90), interpolation=cv2.INTER_AREA)
            gray = cv2.cvtColor(small_frame, cv2.COLOR_BGR2GRAY)
            gray = cv2.GaussianBlur(gray, (5, 5), 1.0)

            if prev_gray is not None:
                diff = cv2.absdiff(prev_gray, gray)
                _, thresh = cv2.threshold(diff, 18, 255, cv2.THRESH_BINARY)
                motion_ratio = float(np.count_nonzero(thresh) / thresh.size)

                is_idle = motion_ratio < motion_threshold

                if is_idle:
                    if idle_start is None:
                        # Mark beginning of candidate idle window
                        idle_start = max(0.0, current_timestamp - sample_interval)
                else:
                    if idle_start is not None:
                        idle_end = current_timestamp
                        if (idle_end - idle_start) >= min_idle_duration:
                            idle_segments.append(
                                IdleSegment(
                                    start_time=round(idle_start, 2),
                                    end_time=round(idle_end, 2),
                                    reason="player_inactivity",
                                    confidence=0.95,
                                )
                            )
                        idle_start = None

            prev_gray = gray
            current_frame_idx += frame_step

        cap.release()

        # Handle trailing idle segment at end of video
        if idle_start is not None:
            video_dur = total_frames / fps
            if (video_dur - idle_start) >= min_idle_duration:
                idle_segments.append(
                    IdleSegment(
                        start_time=round(idle_start, 2),
                        end_time=round(video_dur, 2),
                        reason="player_inactivity",
                        confidence=0.95,
                    )
                )

        return idle_segments

    def _detect_with_ffmpeg_freezedetect(
        self,
        video_path: Path,
        min_idle_duration: float,
    ) -> List[IdleSegment]:
        """Fallback idle detector utilizing FFmpeg's native freezedetect filter."""
        cmd = [
            "ffmpeg",
            "-nostdin",
            "-i", str(video_path),
            "-vf", f"freezedetect=n=-45dB:d={min_idle_duration}",
            "-map", "0:v:0",
            "-f", "null",
            "-",
        ]
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            output = res.stderr or ""
            idle_segments: List[IdleSegment] = []

            # Match freeze_start and freeze_end patterns
            starts = [float(m.group(1)) for m in re.finditer(r"freeze_start:\s*([\d\.]+)", output)]
            ends = [float(m.group(1)) for m in re.finditer(r"freeze_end:\s*([\d\.]+)", output)]

            for i in range(min(len(starts), len(ends))):
                st = starts[i]
                et = ends[i]
                if et - st >= min_idle_duration:
                    idle_segments.append(
                        IdleSegment(
                            start_time=round(st, 2),
                            end_time=round(et, 2),
                            reason="frozen_screen",
                            confidence=0.90,
                        )
                    )
            return idle_segments
        except Exception as fe:
            logger.warning(f"FFmpeg freezedetect fallback failed: {fe}")
            return []

    def detect_idle_segments(
        self,
        video_path: Path,
        min_idle_duration: float = 7.0,
        motion_threshold: float = 0.015,
        sample_interval: float = 0.5,
    ) -> List[IdleSegment]:
        """Detects idle periods where player stood still or was away from controls."""
        if not video_path.exists():
            return []

        logger.info(
            f"Scanning for idle intervals in {video_path.name} "
            f"(min_duration: {min_idle_duration}s, threshold: {motion_threshold})"
        )

        detected_segments: List[IdleSegment] = []
        try:
            detected_segments = self._detect_with_opencv(
                video_path=video_path,
                min_idle_duration=min_idle_duration,
                motion_threshold=motion_threshold,
                sample_interval=sample_interval,
            )
        except Exception as oe:
            logger.warning(f"OpenCV motion detection encountered error: {oe}. Engaging FFmpeg fallback.")
            detected_segments = self._detect_with_ffmpeg_freezedetect(
                video_path=video_path,
                min_idle_duration=min_idle_duration,
            )

        # Merge segments separated by tiny gaps (< 1.0s)
        if not detected_segments:
            return []

        sorted_segments = sorted(detected_segments, key=lambda s: s.start_time)
        merged: List[IdleSegment] = []

        for seg in sorted_segments:
            if not merged:
                merged.append(seg)
            else:
                prev = merged[-1]
                if seg.start_time <= prev.end_time + 1.0:
                    merged[-1] = IdleSegment(
                        start_time=prev.start_time,
                        end_time=max(prev.end_time, seg.end_time),
                        reason=prev.reason,
                        confidence=min(prev.confidence, seg.confidence),
                    )
                else:
                    merged.append(seg)

        total_idle_time = sum(s.duration for s in merged)
        logger.info(
            f"Idle scan complete: found {len(merged)} inactivity segment(s) "
            f"totaling {total_idle_time:.1f}s"
        )
        return merged

    def compute_keep_intervals(
        self,
        total_duration: float,
        idle_segments: List[IdleSegment],
        min_segment_length: float = 0.4,
    ) -> List[Tuple[float, float]]:
        """Calculates the active gameplay intervals to preserve."""
        if not idle_segments or total_duration <= 0:
            return [(0.0, total_duration)] if total_duration > 0 else []

        sorted_idles = sorted(idle_segments, key=lambda s: s.start_time)
        merged_idles: List[Tuple[float, float]] = []

        for seg in sorted_idles:
            st = max(0.0, min(seg.start_time, total_duration))
            et = max(st, min(seg.end_time, total_duration))
            if et <= st:
                continue

            if not merged_idles:
                merged_idles.append((st, et))
            else:
                prev_st, prev_et = merged_idles[-1]
                if st <= prev_et + 0.5:
                    merged_idles[-1] = (prev_st, max(prev_et, et))
                else:
                    merged_idles.append((st, et))

        keep_intervals: List[Tuple[float, float]] = []
        current_time = 0.0

        for idle_st, idle_et in merged_idles:
            if idle_st - current_time >= min_segment_length:
                keep_intervals.append((round(current_time, 3), round(idle_st, 3)))
            current_time = idle_et

        if total_duration - current_time >= min_segment_length:
            keep_intervals.append((round(current_time, 3), round(total_duration, 3)))

        return keep_intervals

    def remove_idle_segments(
        self,
        input_video: Path,
        idle_segments: List[IdleSegment],
        output_video: Optional[Path] = None,
    ) -> Path:
        """Cuts out idle/inactivity segments using FFmpeg, returning pure active gameplay."""
        if not input_video.exists():
            raise VideoProcessingError(
                operation="remove_idle_segments",
                root_cause=f"Input video not found: {input_video}",
                recovery_action="Ensure source video exists before attempting idle trimming.",
                file_path=str(input_video),
            )

        if not idle_segments:
            logger.info("No idle segments specified; video remains uncut.")
            return input_video

        target_output = output_video or (self.temp_dir / f"{input_video.stem}_active{input_video.suffix}")
        total_duration = self.get_video_duration(input_video)
        keep_intervals = self.compute_keep_intervals(total_duration, idle_segments)

        if not keep_intervals:
            logger.warning("Computed 0 keep intervals; preserving original video to prevent total deletion.")
            return input_video

        if len(keep_intervals) == 1 and keep_intervals[0][0] <= 0.1 and abs(keep_intervals[0][1] - total_duration) <= 0.5:
            logger.info("Idle intervals fall outside bounds; no video trimming required.")
            return input_video

        total_idle_sec = sum(s.duration for s in idle_segments)
        logger.info(
            f"Trimming {len(idle_segments)} idle segment(s) totaling {total_idle_sec:.1f}s "
            f"from {input_video.name} -> {target_output.name}"
        )

        filter_chains: List[str] = []
        v_inputs: List[str] = []
        a_inputs: List[str] = []

        for i, (st, et) in enumerate(keep_intervals):
            filter_chains.append(f"[0:v]trim=start={st:.3f}:end={et:.3f},setpts=PTS-STARTPTS[v{i}]")
            filter_chains.append(f"[0:a]atrim=start={st:.3f}:end={et:.3f},asetpts=PTS-STARTPTS[a{i}]")
            v_inputs.append(f"[v{i}]")
            a_inputs.append(f"[a{i}]")

        concat_in = "".join(f"{v}{a}" for v, a in zip(v_inputs, a_inputs))
        filter_chains.append(f"{concat_in}concat=n={len(keep_intervals)}:v=1:a=1[outv][outa]")

        cmd = [
            "ffmpeg",
            "-y",
            "-nostdin",
            "-i", str(input_video),
            "-filter_complex", ";".join(filter_chains),
            "-map", "[outv]",
            "-map", "[outa]",
            "-c:v", "libx264",
            "-preset", "veryfast",
            "-crf", "20",
            "-c:a", "aac",
            "-b:a", "192k",
            str(target_output),
        ]

        target_output.parent.mkdir(parents=True, exist_ok=True)
        res = subprocess.run(cmd, capture_output=True, text=True)

        if res.returncode != 0:
            logger.error(f"FFmpeg idle trimming failed: {res.stderr}")
            raise VideoProcessingError(
                operation="remove_idle_segments",
                root_cause=res.stderr[-500:] if res.stderr else "FFmpeg error during idle trimming",
                recovery_action="Check FFmpeg filtergraph and codecs.",
                file_path=str(input_video),
            )

        new_duration = self.get_video_duration(target_output)
        logger.info(
            f"Successfully trimmed idle footage! Original: {total_duration:.1f}s -> Active: {new_duration:.1f}s "
            f"(Excised {total_duration - new_duration:.1f}s of inactivity)"
        )
        return target_output

    def adjust_event_timestamps(self, events: List[Any], idle_segments: List[IdleSegment]) -> List[Any]:
        """Adjusts subtitle/chapter event timestamps after idle footage is trimmed."""
        if not events or not idle_segments:
            return events

        sorted_idles = sorted(idle_segments, key=lambda s: s.start_time)
        adjusted_events = []

        for ev in events:
            st = getattr(ev, "start_time", 0.0)
            et = getattr(ev, "end_time", st)

            # Check if event was entirely during idle period
            in_idle = False
            for idle in sorted_idles:
                if idle.start_time <= st and et <= idle.end_time:
                    in_idle = True
                    break
            if in_idle:
                continue

            shift_st = sum(s.duration for s in sorted_idles if s.end_time <= st)
            shift_et = sum(s.duration for s in sorted_idles if s.end_time <= et)

            new_st = max(0.0, round(st - shift_st, 2))
            new_et = max(new_st, round(et - shift_et, 2))

            if hasattr(ev, "start_time"):
                ev.start_time = new_st
            if hasattr(ev, "end_time"):
                ev.end_time = new_et

            adjusted_events.append(ev)

        return adjusted_events
