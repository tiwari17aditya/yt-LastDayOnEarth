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
            f"from {input_video.name} -> {target_output.name} across {len(keep_intervals)} keep interval(s)"
        )

        target_output.parent.mkdir(parents=True, exist_ok=True)

        # Single keep interval: extract directly with input seeking
        if len(keep_intervals) == 1:
            st, et = keep_intervals[0]
            cmd = [
                "ffmpeg",
                "-y",
                "-nostdin",
                "-ss", f"{st:.3f}",
                "-to", f"{et:.3f}",
                "-i", str(input_video),
                "-c:v", "libx264",
                "-preset", "ultrafast",
                "-crf", "20",
                "-c:a", "aac",
                "-b:a", "192k",
                str(target_output),
            ]
            res = subprocess.run(cmd, capture_output=True, text=True)
            if res.returncode != 0:
                logger.error(f"FFmpeg single-interval ad excision failed: {res.stderr}")
                raise VideoProcessingError(
                    operation="remove_ads",
                    root_cause=res.stderr[-500:] if res.stderr else "FFmpeg error during single-interval ad excision",
                    recovery_action="Check FFmpeg filtergraph or video codec parameters.",
                    file_path=str(input_video),
                )
        else:
            # Multi-interval: Extract each keep segment sequentially with zero-RAM buffering,
            # then stitch together in 1-2 seconds with the stream-copy Concat Demuxer.
            segment_files: List[Path] = []
            concat_list_file = self.output_dir / f"concat_ad_{input_video.stem}.txt"

            try:
                for idx, (st, et) in enumerate(keep_intervals):
                    seg_path = self.output_dir / f"seg_ad_{idx}_{input_video.stem}{input_video.suffix}"
                    segment_files.append(seg_path)

                    seg_cmd = [
                        "ffmpeg",
                        "-y",
                        "-nostdin",
                        "-ss", f"{st:.3f}",
                        "-to", f"{et:.3f}",
                        "-i", str(input_video),
                        "-c:v", "libx264",
                        "-preset", "ultrafast",
                        "-crf", "20",
                        "-c:a", "aac",
                        "-b:a", "192k",
                        str(seg_path),
                    ]
                    seg_res = subprocess.run(seg_cmd, capture_output=True, text=True)
                    if seg_res.returncode != 0:
                        logger.error(f"FFmpeg trim for ad keep segment {idx} ({st:.1f}s-{et:.1f}s) failed: {seg_res.stderr}")
                        raise VideoProcessingError(
                            operation="remove_ads",
                            root_cause=seg_res.stderr[-500:] if seg_res.stderr else f"FFmpeg ad segment {idx} failed",
                            recovery_action="Check input video integrity and storage.",
                            file_path=str(input_video),
                        )

                # Write concat demuxer manifest
                lines = [f"file '{p.resolve().as_posix()}'" for p in segment_files]
                concat_list_file.write_text("\n".join(lines) + "\n", encoding="utf-8")

                # Concat with stream-copy: instantaneous, no re-encoding, constant O(1) RAM
                concat_cmd = [
                    "ffmpeg",
                    "-y",
                    "-nostdin",
                    "-f", "concat",
                    "-safe", "0",
                    "-i", str(concat_list_file),
                    "-c", "copy",
                    str(target_output),
                ]
                concat_res = subprocess.run(concat_cmd, capture_output=True, text=True)
                if concat_res.returncode != 0:
                    logger.error(f"FFmpeg concat demuxer failed: {concat_res.stderr}")
                    raise VideoProcessingError(
                        operation="remove_ads",
                        root_cause=concat_res.stderr[-500:] if concat_res.stderr else "FFmpeg concat failed",
                        recovery_action="Verify segment codecs match.",
                        file_path=str(input_video),
                    )
            finally:
                # Always clean up temporary segment files and manifest
                for sf in segment_files:
                    if sf.exists():
                        try:
                            sf.unlink()
                        except Exception:
                            pass
                if concat_list_file.exists():
                    try:
                        concat_list_file.unlink()
                    except Exception:
                        pass

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

