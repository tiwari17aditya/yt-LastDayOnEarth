"""FFmpeg wrapper for composite video processing and standardized naming."""

import re
import subprocess
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
        # Clean special chars and spaces
        clean_stem = re.sub(r"[^\w\s-]", "", stem).strip().replace(" ", "_")
        today_date = datetime.now().strftime("%d%m%Y")
        return f"{clean_stem}_Processed_{today_date}.mp4"

    def get_output_path(self, original_filename: str) -> Path:
        return self.output_dir / self.generate_output_filename(original_filename)

    def get_video_duration(self, video_path: Path) -> float:
        """Determines the duration of the video in seconds using ffprobe."""
        cmd = [
            "ffprobe",
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(video_path),
        ]
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return float(res.stdout.strip())
        except Exception as e:
            logger.warning("Could not probe video duration, defaulting to 180.0s", extra_data={"error": str(e)})
            return 180.0

    def build_ffmpeg_command(
        self,
        input_video: Path,
        output_video: Path,
        subtitle_file: Optional[Path] = None,
        music_file: Optional[Path] = None,
        privacy_filter: Optional[str] = None,
        ducking_db: str = "-8dB",
        preset: str = "veryfast",
    ) -> List[str]:
        """Assembles robust FFmpeg command for composite rendering."""
        cmd = ["ffmpeg", "-y", "-i", str(input_video)]

        has_music = music_file is not None and Path(music_file).exists()
        if has_music:
            cmd.extend(["-i", str(music_file)])

        video_filters = []
        if privacy_filter:
            video_filters.append(privacy_filter)

        if subtitle_file and Path(subtitle_file).exists():
            # Escape path for FFmpeg subtitles filter on Windows
            escaped_sub = str(subtitle_file).replace("\\", "/").replace(":", "\\:")
            video_filters.append(f"subtitles='{escaped_sub}'")

        if video_filters and has_music:
            vf_string = ",".join(video_filters)
            filter_complex = (
                f"[0:v]{vf_string}[vout];"
                f"[1:a]volume={ducking_db}[bg];"
                f"[0:a][bg]amix=inputs=2:duration=first:dropout_transition=2[aout]"
            )
            cmd.extend([
                "-filter_complex", filter_complex,
                "-map", "[vout]",
                "-map", "[aout]",
            ])
        elif video_filters:
            cmd.extend(["-vf", ",".join(video_filters)])
            cmd.extend(["-map", "0:v", "-map", "0:a?"])
        elif has_music:
            filter_complex = (
                f"[1:a]volume={ducking_db}[bg];"
                f"[0:a][bg]amix=inputs=2:duration=first:dropout_transition=2[aout]"
            )
            cmd.extend([
                "-filter_complex", filter_complex,
                "-map", "0:v",
                "-map", "[aout]",
            ])

        cmd.extend([
            "-c:v", "libx264",
            "-preset", preset,
            "-crf", "20",
            "-c:a", "aac",
            "-b:a", "192k",
            "-movflags", "+faststart",
            str(output_video),
        ])

        return cmd

    def render(
        self,
        input_video: Path,
        output_video: Path,
        subtitle_file: Optional[Path] = None,
        music_file: Optional[Path] = None,
        privacy_filter: Optional[str] = None,
        ducking_db: str = "-8dB",
        preset: str = "veryfast",
    ) -> Path:
        """Executes FFmpeg composite render."""
        cmd = self.build_ffmpeg_command(
            input_video=input_video,
            output_video=output_video,
            subtitle_file=subtitle_file,
            music_file=music_file,
            privacy_filter=privacy_filter,
            ducking_db=ducking_db,
            preset=preset,
        )

        logger.info("Executing FFmpeg render command", extra_data={"output": str(output_video)})
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode != 0:
                raise VideoProcessingError(
                    operation="render",
                    root_cause=f"FFmpeg failed with exit code {result.returncode}: {result.stderr[-400:]}",
                    recovery_action="Check FFmpeg filters and input stream codecs.",
                    file_path=str(input_video),
                )
            logger.info("FFmpeg video rendering completed successfully", extra_data={"output": str(output_video)})
            return output_video
        except Exception as e:
            if isinstance(e, VideoProcessingError):
                raise
            raise VideoProcessingError(
                operation="render",
                root_cause=str(e),
                recovery_action="Ensure FFmpeg binary is accessible in system PATH.",
                file_path=str(input_video),
            )
