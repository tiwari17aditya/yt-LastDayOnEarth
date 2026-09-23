import json
import random
import subprocess
from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from src.logging_config import get_logger
from src.exceptions import AudioProcessingError

logger = get_logger(component="AudioMixer")


class BaseAudioMixer(ABC):
    """Abstract interface for audio background music management and mixing."""

    @abstractmethod
    def select_track(self, mood: Optional[str] = None) -> Dict[str, Any]:
        """Select a suitable music track from the library."""
        pass

    @abstractmethod
    def build_ffmpeg_audio_filter(self, ducking_db: str = "-8dB") -> str:
        """Construct FFmpeg filtergraph for seamless looping and ducking."""
        pass


class AudioMixer(BaseAudioMixer):
    """Manages audio mixing with volume attenuation/ducking and seamless loop."""

    def __init__(
        self,
        library_path: Path = Path("config/music_library.json"),
        audio_dir: Path = Path("config/audio"),
    ) -> None:
        self.library_path = library_path
        self.audio_dir = audio_dir
        self.tracks = self._load_library()

    def _load_library(self) -> List[Dict[str, Any]]:
        if not self.library_path.exists():
            raise AudioProcessingError(
                operation="load_library",
                root_cause=f"Music library file not found: {self.library_path}",
                recovery_action="Ensure config/music_library.json is present.",
                file_path=str(self.library_path),
            )
        try:
            with open(self.library_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("tracks", [])
        except Exception as e:
            raise AudioProcessingError(
                operation="load_library",
                root_cause=str(e),
                recovery_action="Verify JSON syntax in music_library.json.",
                file_path=str(self.library_path),
            )

    def get_available_tracks(self) -> List[Dict[str, Any]]:
        """Returns all library tracks that have an existing audio file on disk with probed duration."""
        available = []
        for track in self.tracks:
            title_slug = track.get("title", "").lower().replace(" ", "_")
            audio_file = self.audio_dir / f"{title_slug}.mp3"
            if not audio_file.exists():
                audio_file = self.audio_dir / f"{track.get('id', '')}.mp3"
            if audio_file.exists():
                track_copy = dict(track)
                track_copy["file_path"] = str(audio_file)
                # Probe duration if not already present
                if "duration" not in track_copy or track_copy["duration"] == 30.0:
                    track_copy["duration"] = self._probe_duration(audio_file)
                available.append(track_copy)
        return available

    def _probe_duration(self, file_path: Path) -> float:
        """Determines the exact length of an audio file in seconds via ffprobe."""
        try:
            cmd = [
                "ffprobe",
                "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                str(file_path),
            ]
            res = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return round(float(res.stdout.strip()), 2)
        except Exception:
            return 90.0

    def select_track(self, mood: Optional[str] = None) -> Dict[str, Any]:
        """Find track matching mood or return ambient home base track."""
        available = self.get_available_tracks()
        pool = available if available else self.tracks

        target_track = None
        if mood:
            for track in pool:
                if track.get("mood") == mood:
                    target_track = track
                    break

        if not target_track and pool:
            for track in pool:
                if track.get("mood") in ["home_base", "scavenging"]:
                    target_track = track
                    break
            if not target_track:
                target_track = pool[0]

        if not target_track:
            raise AudioProcessingError(
                operation="select_track",
                root_cause="Music catalog is empty.",
                recovery_action="Add tracks to config/music_library.json.",
            )

        track_copy = dict(target_track)
        logger.info("Selected background track", extra_data={"title": track_copy["title"], "file": track_copy.get("file_path")})
        return track_copy

    def create_random_loop_sequence(
        self,
        target_duration: float,
        output_path: Path,
    ) -> Tuple[Path, List[Dict[str, Any]]]:
        """Randomly selects tracks from the 20-track pool one after another until

        target_duration is fully covered, concatenates them into a continuous
        audio stream via FFmpeg, and returns the list of chosen tracks with timestamps.
        """
        available = self.get_available_tracks()
        if not available:
            raise AudioProcessingError(
                operation="create_random_loop_sequence",
                root_cause="No audio tracks available in config/audio.",
                recovery_action="Ensure tracks exist in config/audio and match library.",
            )

        playlist_tracks: List[Dict[str, Any]] = []
        accumulated_duration = 0.0
        last_track_id = None

        # Continuously pick random tracks one after another until video ends
        while accumulated_duration < target_duration:
            candidates = [t for t in available if t["id"] != last_track_id] or available
            chosen = random.choice(candidates)
            last_track_id = chosen["id"]

            track_info = dict(chosen)
            track_info["start_time"] = round(accumulated_duration, 2)
            duration = float(chosen.get("duration", 30.0))
            accumulated_duration += duration
            track_info["end_time"] = round(accumulated_duration, 2)
            playlist_tracks.append(track_info)

        # Build FFmpeg concat list file
        output_path.parent.mkdir(parents=True, exist_ok=True)
        concat_file = output_path.with_name(f"{output_path.stem}_concat.txt")
        lines = []
        for item in playlist_tracks:
            posix_path = Path(item["file_path"]).resolve().as_posix()
            lines.append(f"file '{posix_path}'")
        concat_file.write_text("\n".join(lines) + "\n", encoding="utf-8")

        # Concatenate audio using FFmpeg
        cmd = [
            "ffmpeg",
            "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", str(concat_file),
            "-c:a", "aac",
            "-b:a", "192k",
            str(output_path),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if result.returncode != 0:
            raise AudioProcessingError(
                operation="create_random_loop_sequence",
                root_cause=f"FFmpeg audio concat failed: {result.stderr[-300:]}",
                recovery_action="Check audio file formats and concat file paths.",
                file_path=str(concat_file),
            )

        logger.info(
            "Created random background music sequence",
            extra_data={
                "total_tracks_used": len(playlist_tracks),
                "total_duration": accumulated_duration,
                "output_file": str(output_path),
            },
        )
        return output_path, playlist_tracks

    def build_ffmpeg_audio_filter(self, ducking_db: str = "-8dB") -> str:
        """Generates filter complex combining gameplay audio (input 0) with background music (input 1)."""
        return f"[1:a]aloop=loop=-1:size=2e+09,volume={ducking_db}[bg];[0:a][bg]amix=inputs=2:duration=first:dropout_transition=2[aout]"
