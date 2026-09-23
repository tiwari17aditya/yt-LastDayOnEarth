"""FFmpeg wrapper for composite video processing and standardized naming."""

import re
from datetime import datetime
from pathlib import Path
from typing import Optional, List
from src.logging_config import get_logger
from src.exceptions import VideoProcessingError

logger = get_logger(component="VideoProcessor")


class VideoProcessor:
    """Orchestrates FFmpeg processing, filters, subtitles, and export."""

    def __init__(self, output_dir: Path = Path("output")) -> None:
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate_output_filename(self, original_filename: str) -> str:
        """Formulate filename: <Title>_Processed_<DDMMYYYY>.mp4"""
        stem = Path(original_filename).stem
        # Clean special chars
        clean_stem = re.sub(r"[^\w\s-]", "", stem).strip().replace(" ", "_")
        today_date = datetime.now().strftime("%d%m%Y")
        return f"{clean_stem}_Processed_{today_date}.mp4"

    def get_output_path(self, original_filename: str) -> Path:
        return self.output_dir / self.generate_output_filename(original_filename)

    def build_ffmpeg_command(
        self,
        input_video: Path,
        output_video: Path,
        subtitle_file: Optional[Path] = None,
        music_file: Optional[Path] = None,
        privacy_filter: Optional[str] = None,
        ducking_db: str = "-20dB",
    ) -> List[str]:
        """Assembles robust FFmpeg command for hardware/software encoding."""
        cmd = ["ffmpeg", "-y", "-i", str(input_video)]

        if music_file and music_file.exists():
            cmd.extend(["-i", str(music_file)])

        video_filters = []
        if privacy_filter:
            video_filters.append(privacy_filter)

        if subtitle_file and subtitle_file.exists():
            # Escape path for FFmpeg subtitles filter
            escaped_sub = str(subtitle_file).replace("\\", "/").replace(":", "\\:")
            video_filters.append(f"subtitles='{escaped_sub}'")

        if video_filters:
            cmd.extend(["-vf", ",".join(video_filters)])

        if music_file and music_file.exists():
            cmd.extend([
                "-filter_complex",
                f"[1:a]aloop=loop=-1:size=2e+09,volume={ducking_db}[bg];[0:a][bg]amix=inputs=2:duration=first[aout]",
                "-map", "0:v",
                "-map", "[aout]",
            ])

        cmd.extend([
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "22",
            "-c:a", "aac",
            "-b:a", "192k",
            "-movflags", "+faststart",
            str(output_video),
        ])

        return cmd
