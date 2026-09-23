"""Background music selection, looping, and audio ducking module."""

import json
from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Dict, Any, Optional
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
    def build_ffmpeg_audio_filter(self, ducking_db: str = "-20dB") -> str:
        """Construct FFmpeg filtergraph for seamless looping and ducking."""
        pass


class AudioMixer(BaseAudioMixer):
    """Manages audio mixing with volume attenuation/ducking and seamless loop."""

    def __init__(self, library_path: Path = Path("config/music_library.json")) -> None:
        self.library_path = library_path
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

    def select_track(self, mood: Optional[str] = None) -> Dict[str, Any]:
        """Find track matching mood or return default survival ambient track."""
        if mood:
            for track in self.tracks:
                if track.get("mood") == mood:
                    logger.info("Selected background track by mood", extra_data={"track": track["title"], "mood": mood})
                    return track
        if self.tracks:
            chosen = self.tracks[0]
            logger.info("Selected default background track", extra_data={"track": chosen["title"]})
            return chosen
        raise AudioProcessingError(
            operation="select_track",
            root_cause="Music catalog is empty.",
            recovery_action="Add tracks to config/music_library.json.",
        )

    def build_ffmpeg_audio_filter(self, ducking_db: str = "-20dB") -> str:
        """Generates filter complex combining gameplay audio (input 0) with background music (input 1)."""
        # [1:a]aloop=loop=-1:size=2e+09,volume=-20dB[bg];[0:a][bg]amix=inputs=2:duration=first[aout]
        return f"[1:a]aloop=loop=-1:size=2e+09,volume={ducking_db}[bg];[0:a][bg]amix=inputs=2:duration=first[aout]"
