"""Cuts and removes in-game advertisement segments from video files using FFmpeg."""

import subprocess
from pathlib import Path
from typing import Any, List, Optional, Tuple

from src.logging_config import get_logger
from src.exceptions import VideoProcessingError
from src.privacy.ad_detector import AdSegment

logger = get_logger(component="AdRemover")


class AdRemover:
    """Removes detected advertisement intervals and synchronizes remaining gameplay streams."""

    def __init__(self, output_dir: Optional[Path] = None) -> None:
        self.output_dir = output_dir or Path("temp")
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def get_video_duration(self, video_path: Path) -> float:
        """Probes true video duration in seconds via ffprobe."""
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

    def compute_keep_intervals(
        self,
        total_duration: float,
        ad_segments: List[AdSegment],
        min_segment_length: float = 0.4,
    ) -> List[Tuple[float, float]]:
        """Calculates the non-ad gameplay time intervals to preserve."""
        if not ad_segments or total_duration <= 0:
            return [(0.0, total_duration)] if total_duration > 0 else []

        # Sort ads chronologically and merge overlaps
        sorted_ads = sorted(ad_segments, key=lambda a: a.start_time)
        merged_ads: List[Tuple[float, float]] = []
        for ad in sorted_ads:
            st = max(0.0, min(ad.start_time, total_duration))
            et = max(st, min(ad.end_time, total_duration))
            if et <= st:
                continue

            if not merged_ads:
                merged_ads.append((st, et))
            else:
                prev_st, prev_et = merged_ads[-1]
                if st <= prev_et + 0.5:
                    merged_ads[-1] = (prev_st, max(prev_et, et))
                else:
                    merged_ads.append((st, et))

        keep_intervals: List[Tuple[float, float]] = []
        current_time = 0.0

        for ad_st, ad_et in merged_ads:
            if ad_st - current_time >= min_segment_length:
                keep_intervals.append((round(current_time, 3), round(ad_st, 3)))
            current_time = ad_et

        if total_duration - current_time >= min_segment_length:
            keep_intervals.append((round(current_time, 3), round(total_duration, 3)))

        return keep_intervals

    def remove_ads(
        self,
        input_video: Path,
        ad_segments: List[AdSegment],
        output_video: Optional[Path] = None,
    ) -> Path:
        """Cuts out advertisement intervals from input_video using FFmpeg trim/concat."""
        if not input_video.exists():
            raise VideoProcessingError(
                operation="remove_ads",
                root_cause=f"Input video not found: {input_video}",
                recovery_action="Ensure raw video exists before attempting ad excision.",
                file_path=str(input_video),
            )

        if not ad_segments:
            logger.info("No advertisement segments specified; video remains uncut.")
            return input_video

        target_output = output_video or (self.output_dir / f"{input_video.stem}_clean{input_video.suffix}")
        total_duration = self.get_video_duration(input_video)
        keep_intervals = self.compute_keep_intervals(total_duration, ad_segments)

        if not keep_intervals:
            logger.warning("Computed 0 keep intervals; returning original video without cutting.")
            return input_video

        # If only one keep interval spanning the entire video, no cut is needed
        if len(keep_intervals) == 1 and keep_intervals[0][0] <= 0.1 and abs(keep_intervals[0][1] - total_duration) <= 0.5:
            logger.info("Ad intervals fall outside video bounds; no trimming necessary.")
            return input_video

        total_ad_duration = sum(ad.duration for ad in ad_segments)
        logger.info(
            f"Excising {len(ad_segments)} advertisement segment(s) totaling {total_ad_duration:.2f}s "
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
            logger.error(f"FFmpeg ad excision failed: {res.stderr}")
            raise VideoProcessingError(
                operation="remove_ads",
                root_cause=res.stderr[-500:] if res.stderr else "FFmpeg error during ad excision",
                recovery_action="Check FFmpeg filtergraph or video codec parameters.",
                file_path=str(input_video),
            )

        new_duration = self.get_video_duration(target_output)
        logger.info(
            f"Successfully cut advertisements! Original: {total_duration:.1f}s -> Clean: {new_duration:.1f}s "
            f"(Saved {total_duration - new_duration:.1f}s of pure gameplay)"
        )
        return target_output

    def adjust_event_timestamps(self, events: List[Any], ad_segments: List[AdSegment]) -> List[Any]:
        """Adjusts subtitle / chapter event timestamps after advertisement excision."""
        if not events or not ad_segments:
            return events

        # Sort ads chronologically
        sorted_ads = sorted(ad_segments, key=lambda a: a.start_time)
        adjusted_events = []

        for ev in events:
            st = getattr(ev, "start_time", 0.0)
            et = getattr(ev, "end_time", st)

            # Check if event falls entirely inside any ad
            in_ad = False
            for ad in sorted_ads:
                if ad.start_time <= st and et <= ad.end_time:
                    in_ad = True
                    break
            if in_ad:
                # Drop events that occurred entirely within an ad
                continue

            # Calculate total ad time excised prior to this event's start
            shift_st = sum(ad.duration for ad in sorted_ads if ad.end_time <= st)
            shift_et = sum(ad.duration for ad in sorted_ads if ad.end_time <= et)

            new_st = max(0.0, round(st - shift_st, 2))
            new_et = max(new_st, round(et - shift_et, 2))

            # Update event attributes
            if hasattr(ev, "start_time"):
                ev.start_time = new_st
            if hasattr(ev, "end_time"):
                ev.end_time = new_et

            adjusted_events.append(ev)

        return adjusted_events

