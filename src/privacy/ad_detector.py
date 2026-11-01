"""Automated in-game mobile advertisement detector for Last Day on Earth gameplay."""

import json
import re
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from src.logging_config import get_logger
from src.exceptions import PrivacyRedactionError

logger = get_logger(component="AdDetector")


@dataclass
class AdSegment:
    """Represents a detected in-game advertisement segment."""
    start_time: float
    end_time: float
    ad_type: str = "rewarded_ad"
    description: str = ""
    confidence: float = 0.9

    @property
    def duration(self) -> float:
        return max(0.0, round(self.end_time - self.start_time, 2))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "start_time": round(self.start_time, 2),
            "end_time": round(self.end_time, 2),
            "duration": self.duration,
            "ad_type": self.ad_type,
            "description": self.description,
            "confidence": round(self.confidence, 2),
        }


class AdDetector:
    """Detects in-game rewarded video ads, interstitial promos, and commercial breaks.

    Combines Gemini 2.5 Flash Vision Multimodal analysis with OCR / heuristic fallback.
    """

    # Common mobile ad keywords appearing in overlays, countdowns, and buttons
    AD_KEYWORDS = [
        "reward in",
        "reward will be given in",
        "ad 1 of",
        "ad 2 of",
        "ad ends in",
        "skip ad in",
        "skip in",
        "install now",
        "install",
        "download now",
        "download",
        "play now",
        "play store",
        "google play",
        "app store",
        "advertisement",
        "playable",
    ]

    def __init__(
        self,
        gemini_api_key: Optional[str] = None,
        gemini_model: str = "gemini-2.5-flash",
        sample_interval: float = 3.0,
        min_ad_duration: float = 4.0,
        max_ad_duration: float = 120.0,
    ) -> None:
        self.gemini_api_key = gemini_api_key
        self.gemini_model = gemini_model
        self.sample_interval = sample_interval
        self.min_ad_duration = min_ad_duration
        self.max_ad_duration = max_ad_duration

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
            return float(res.stdout.strip())
        except Exception as e:
            logger.debug(f"Could not probe duration for {video_path}: {e}")
            return 0.0

    def detect_ads(self, video_path: Path) -> List[AdSegment]:
        """Scans video to identify all mobile advertisement segments."""
        if not video_path.exists():
            raise PrivacyRedactionError(
                operation="detect_ads",
                root_cause=f"File not found: {video_path}",
                recovery_action="Ensure source video exists before running ad detection.",
                file_path=str(video_path),
            )

        logger.info(f"Scanning video for in-game advertisements: {video_path}")
        total_duration = self.get_video_duration(video_path)
        if total_duration <= 0.0:
            logger.warning(f"Video duration is 0.0s, skipping ad detection for {video_path}")
            return []

        detected_ads: List[AdSegment] = []

        # 1. Try Gemini Vision multimodal detection if API key configured
        if self.gemini_api_key:
            try:
                detected_ads = self.detect_ads_with_gemini(video_path, total_duration)
                logger.info(
                    f"Gemini Vision detected {len(detected_ads)} advertisement segment(s)",
                    extra_data={"ad_count": len(detected_ads)},
                )
            except Exception as ge:
                logger.warning(
                    f"Gemini Vision ad detection encountered error: {ge}. Falling back to heuristic OCR.",
                    extra_data={"root_cause": str(ge)},
                )
                detected_ads = []

        # 2. Heuristic fallback if Gemini returned nothing or wasn't available
        if not detected_ads:
            try:
                detected_ads = self.detect_ads_heuristically(video_path, total_duration)
                logger.info(
                    f"Heuristic scanner identified {len(detected_ads)} advertisement segment(s)",
                    extra_data={"ad_count": len(detected_ads)},
                )
            except Exception as he:
                logger.warning(f"Heuristic ad detection failed: {he}")
                detected_ads = []

        # 3. Post-processing: Merge overlapping or closely adjacent segments (<2.0s apart)
        cleaned_ads = self.merge_adjacent_segments(detected_ads)

        # 4. Filter by duration bounds
        valid_ads = [
            ad for ad in cleaned_ads
            if self.min_ad_duration <= ad.duration <= self.max_ad_duration
        ]

        if valid_ads:
            total_ad_time = sum(ad.duration for ad in valid_ads)
            logger.info(
                f"Ad detection completed: {len(valid_ads)} ad(s) found totaling {total_ad_time:.1f}s to be cut",
                extra_data={"ads": [a.to_dict() for a in valid_ads]},
            )
        else:
            logger.info("Ad detection completed: No advertisements found in video.")

        return valid_ads

    def extract_keyframes(
        self,
        video_path: Path,
        interval_seconds: float = 3.0,
        max_frames: int = 40,
    ) -> List[Tuple[float, bytes]]:
        """Extracts sequential 720p JPEG frames from video at fixed intervals."""
        duration = self.get_video_duration(video_path)
        if duration <= 0:
            return []

        # Adjust interval if video is very long to prevent exceeding max_frames
        effective_interval = max(interval_seconds, duration / max(1, max_frames))

        timestamps = []
        t = 1.0
        while t < duration - 1.0 and len(timestamps) < max_frames:
            timestamps.append(round(t, 1))
            t += effective_interval

        extracted: List[Tuple[float, bytes]] = []
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            for i, ts in enumerate(timestamps):
                out_frame = tmp_path / f"frame_{i:04d}.jpg"
                cmd = [
                    "ffmpeg",
                    "-y",
                    "-ss", str(ts),
                    "-i", str(video_path),
                    "-vframes", "1",
                    "-vf", "scale=-2:720",
                    "-q:v", "4",
                    str(out_frame),
                ]
                try:
                    subprocess.run(cmd, capture_output=True, check=True, timeout=15)
                    if out_frame.exists() and out_frame.stat().st_size > 0:
                        extracted.append((ts, out_frame.read_bytes()))
                except Exception as fe:
                    logger.debug(f"Frame extraction failed at {ts}s: {fe}")

        return extracted

    def detect_ads_with_gemini(self, video_path: Path, total_duration: float) -> List[AdSegment]:
        """Identifies mobile ad time ranges using Gemini Vision keyframe analysis."""
        try:
            from google import genai
            from google.genai import types
        except ImportError:
            raise RuntimeError("google-genai package not installed.")

        keyframes = self.extract_keyframes(video_path, interval_seconds=self.sample_interval, max_frames=35)
        if not keyframes:
            return []

        client = genai.Client(api_key=self.gemini_api_key)

        prompt_text = (
            "You are an expert video editor specializing in mobile gameplay recordings for 'Last Day on Earth: Survival'.\n"
            "Your task is to identify and timestamps all commercial mobile advertisements, rewarded video ad breaks, "
            "and app install endcards that interrupt the game.\n\n"
            "Characteristics of in-game advertisements:\n"
            "1. Third-party mobile games or commercial products (e.g. Royal Match, Hero Wars, Monopoly GO, Casino apps, Playable mini-games).\n"
            "2. Ad UI elements: 'Reward in Xs', 'Ad: Xs', 'Install Now', 'Google Play', countdown timers, skip buttons ('>>'), or close 'X' buttons.\n"
            "3. COMPLETE ABSENCE of the Last Day on Earth game HUD (character HP bar, top-right minimap radar, virtual movement joystick, weapon quickslots).\n\n"
            "Analyze the provided sequential video frames (labeled with timestamps in seconds) and return a JSON object listing every detected advertisement interval:\n"
            "{\n"
            '  "ad_segments": [\n'
            '    {\n'
            '      "start_time": 45.0,\n'
            '      "end_time": 75.0,\n'
            '      "ad_type": "rewarded_ad",\n'
            '      "description": "Royal Match rewarded video ad with 30s countdown timer"\n'
            "    }\n"
            "  ]\n"
            "}\n"
            "If no advertisements appear in the video, return:\n"
            '{"ad_segments": []}\n'
            "Return valid JSON only."
        )

        contents: List[Any] = [prompt_text]
        for ts, frame_bytes in keyframes:
            contents.append(f"[Timestamp: {ts:.1f}s]")
            contents.append(
                types.Part.from_bytes(
                    data=frame_bytes,
                    mime_type="image/jpeg",
                )
            )

        response = client.models.generate_content(
            model=self.gemini_model,
            contents=contents,
            config=types.GenerateContentConfig(
                temperature=0.1,
                response_mime_type="application/json",
            ),
        )

        resp_text = (response.text or "").strip()
        data = json.loads(resp_text)

        ad_list = []
        for item in data.get("ad_segments", []):
            st = float(item.get("start_time", 0.0))
            et = float(item.get("end_time", 0.0))
            if et > st and (et - st) >= self.min_ad_duration:
                # Clamp within video bounds
                st = max(0.0, min(st, total_duration))
                et = max(st, min(et, total_duration))
                ad_list.append(
                    AdSegment(
                        start_time=st,
                        end_time=et,
                        ad_type=item.get("ad_type", "rewarded_ad"),
                        description=item.get("description", "In-game advertisement"),
                        confidence=float(item.get("confidence", 0.95)),
                    )
                )

        return ad_list

    def _run_windows_native_ocr(self, frame_paths: List[Path]) -> Dict[str, str]:
        """Runs Windows Native OCR (Windows.Media.Ocr) across given image files."""
        import platform
        if platform.system() != "Windows":
            return {}

        script_path = Path(__file__).parent / "windows_ocr.ps1"
        if not script_path.exists():
            return {}

        with tempfile.NamedTemporaryFile("w", delete=False, suffix=".txt") as tf:
            tf.write("\n".join(str(p.resolve()) for p in frame_paths))
            tmp_in = tf.name

        tmp_out = tmp_in + ".json"
        cmd = [
            "powershell",
            "-ExecutionPolicy", "Bypass",
            "-File", str(script_path),
            "-FileList", tmp_in,
            "-OutputFile", tmp_out,
        ]

        try:
            subprocess.run(cmd, capture_output=True, check=True, timeout=30)
            if Path(tmp_out).exists():
                with open(tmp_out, "r", encoding="utf-8-sig") as f:
                    return json.load(f)
        except Exception as e:
            logger.debug(f"Windows Native OCR execution error: {e}")
        finally:
            Path(tmp_in).unlink(missing_ok=True)
            Path(tmp_out).unlink(missing_ok=True)

        return {}

    def detect_ads_heuristically(self, video_path: Path, total_duration: float) -> List[AdSegment]:
        """Detects advertisements heuristically using OCR text matching and HUD signature checks."""
        keyframes = self.extract_keyframes(video_path, interval_seconds=2.0, max_frames=60)
        if not keyframes:
            return []

        ad_timestamps: List[float] = []

        # Save keyframe bytes temporarily for batch OCR
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            frame_files = []
            ts_by_file = {}
            for i, (ts, frame_bytes) in enumerate(keyframes):
                frame_file = tmp_path / f"kf_{i:04d}_{ts:.1f}s.jpg"
                frame_file.write_bytes(frame_bytes)
                frame_files.append(frame_file)
                ts_by_file[str(frame_file.resolve())] = ts

            # 1. Try Windows Native OCR
            ocr_results = self._run_windows_native_ocr(frame_files)

            # 2. Try EasyOCR fallback if Windows OCR returned nothing or not on Windows
            if not ocr_results:
                try:
                    import easyocr  # type: ignore
                    reader = easyocr.Reader(["en"], gpu=False, verbose=False)
                    for f in frame_files:
                        res = reader.readtext(str(f), detail=0)
                        ocr_results[str(f.resolve())] = " ".join(res)
                except Exception:
                    pass

            # Analyze OCR results
            for file_path_str, raw_text in ocr_results.items():
                text_lower = raw_text.lower()
                ts = ts_by_file.get(file_path_str, 0.0)

                # Game indicators: if player username, inventory, or bunker are present, it's gameplay
                is_gameplay = any(
                    gw in text_lower
                    for gw in ["adistar", "inventory", "bunker", "global map", "military locker", "skills", "warming", "scorcher"]
                )

                # Ad indicators
                has_ad_keyword = any(kw in text_lower for kw in self.AD_KEYWORDS)

                if has_ad_keyword and not is_gameplay:
                    ad_timestamps.append(ts)

        if not ad_timestamps:
            return []

        # Cluster timestamps within 5.0 seconds of each other into contiguous ranges
        clusters: List[List[float]] = []
        for t in sorted(ad_timestamps):
            if not clusters or (t - clusters[-1][-1]) > 5.0:
                clusters.append([t])
            else:
                clusters[-1].append(t)

        ad_segments: List[AdSegment] = []
        for cluster in clusters:
            st = max(0.0, cluster[0] - 1.5)
            et = min(total_duration, cluster[-1] + 2.0)
            if et - st >= self.min_ad_duration:
                ad_segments.append(
                    AdSegment(
                        start_time=round(st, 1),
                        end_time=round(et, 1),
                        ad_type="rewarded_ad",
                        description="Detected in-game commercial advertisement",
                        confidence=0.88,
                    )
                )

        return ad_segments

    def merge_adjacent_segments(self, segments: List[AdSegment], max_gap: float = 2.5) -> List[AdSegment]:
        """Merges overlapping or closely adjacent ad segments."""
        if not segments:
            return []

        sorted_segs = sorted(segments, key=lambda s: s.start_time)
        merged: List[AdSegment] = [sorted_segs[0]]

        for current in sorted_segs[1:]:
            prev = merged[-1]
            if current.start_time <= (prev.end_time + max_gap):
                # Extend previous segment
                new_end = max(prev.end_time, current.end_time)
                prev.end_time = new_end
                if current.description and current.description not in prev.description:
                    prev.description = f"{prev.description} + {current.description}".strip(" + ")
            else:
                merged.append(current)

        return merged

