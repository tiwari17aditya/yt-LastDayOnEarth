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
        base_filename = self.generate_output_filename(original_filename)
        candidate = self.output_dir / base_filename
        if not candidate.exists():
            return candidate

        stem = Path(base_filename).stem
        suffix = Path(base_filename).suffix
        counter = 1
        while candidate.exists():
            candidate = self.output_dir / f"{stem}_{counter}{suffix}"
            counter += 1
        logger.info(f"Resolved duplicate output name collision: {candidate.name}")
        return candidate

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
            res = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=30)
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
        cmd = ["ffmpeg", "-y", "-nostdin", "-i", str(input_video)]

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

    def get_duration(self, video_path: Path) -> float:
        """Retrieves duration of a media file in seconds using ffprobe."""
        cmd = [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(video_path),
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if res.returncode == 0 and res.stdout.strip():
            try:
                return float(res.stdout.strip())
            except ValueError:
                pass
        return 0.0

    def append_outro_tail(
        self,
        main_video: Path,
        outro_video: Path,
        output_video: Path,
        preset: str = "veryfast",
        fade_duration: float = 0.7,
    ) -> Path:
        """Seamlessly appends the animated outro tail with a smooth cinematic fade-out/fade-in dip to black."""
        if not outro_video.exists():
            logger.warning(f"Outro tail video not found at {outro_video}; skipping outro appending.")
            return main_video

        main_duration = self.get_duration(main_video)
        fade_dur = min(fade_duration, max(0.2, main_duration / 2.0)) if main_duration > 0 else 0.7
        fade_start = max(0.0, main_duration - fade_dur) if main_duration > 0 else 0.0

        if main_duration > 0:
            filter_complex = (
                f"[0:v]scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=60,fade=t=out:st={fade_start:.2f}:d={fade_dur:.2f}[v0];"
                f"[1:v]scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=60,fade=t=in:st=0:d={fade_dur:.2f}[v1];"
                f"[0:a]aformat=sample_rates=44100:channel_layouts=stereo,afade=t=out:st={fade_start:.2f}:d={fade_dur:.2f}[a0];"
                f"[1:a]aformat=sample_rates=44100:channel_layouts=stereo,afade=t=in:st=0:d={fade_dur:.2f}[a1];"
                f"[v0][a0][v1][a1]concat=n=2:v=1:a=1[v][a]"
            )
        else:
            filter_complex = (
                "[0:v]scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=60[v0];"
                "[1:v]scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=60[v1];"
                "[0:a]aformat=sample_rates=44100:channel_layouts=stereo[a0];"
                "[1:a]aformat=sample_rates=44100:channel_layouts=stereo[a1];"
                "[v0][a0][v1][a1]concat=n=2:v=1:a=1[v][a]"
            )

        cmd = [
            "ffmpeg", "-y", "-nostdin",
            "-i", str(main_video),
            "-i", str(outro_video),
            "-filter_complex", filter_complex,
            "-map", "[v]",
            "-map", "[a]",
            "-c:v", "libx264",
            "-preset", preset,
            "-crf", "20",
            "-c:a", "aac",
            "-b:a", "192k",
            "-movflags", "+faststart",
            str(output_video),
        ]

        logger.info(f"Appending animated outro tail ({outro_video.name}) to final video: {output_video.name}")
        res = subprocess.run(cmd, capture_output=True, text=True, check=False, stdin=subprocess.DEVNULL)
        if res.returncode != 0:
            raise VideoProcessingError(
                operation="append_outro_tail",
                root_cause=f"FFmpeg concat failed: {res.stderr[-400:]}",
                recovery_action="Check FFmpeg filters and input stream codecs.",
                file_path=str(output_video),
            )

        return output_video

    def render(
        self,
        input_video: Path,
        output_video: Path,
        subtitle_file: Optional[Path] = None,
        music_file: Optional[Path] = None,
        privacy_filter: Optional[str] = None,
        ducking_db: str = "-15dB",
        preset: str = "veryfast",
        outro_tail: Optional[Path] = None,
    ) -> Path:
        """Executes FFmpeg composite render and optionally appends the animated outro tail."""
        has_outro = outro_tail is not None and Path(outro_tail).exists()
        target_render_video = (
            output_video.parent / f"staged_composite_{output_video.name}"
            if has_outro
            else output_video
        )

        cmd = self.build_ffmpeg_command(
            input_video=input_video,
            output_video=target_render_video,
            subtitle_file=subtitle_file,
            music_file=music_file,
            privacy_filter=privacy_filter,
            ducking_db=ducking_db,
            preset=preset,
        )

        logger.info("Executing FFmpeg render command", extra_data={"output": str(target_render_video)})
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False,
                stdin=subprocess.DEVNULL,
            )
            if result.returncode != 0:
                raise VideoProcessingError(
                    operation="render",
                    root_cause=f"FFmpeg failed with exit code {result.returncode}: {result.stderr[-400:]}",
                    recovery_action="Check FFmpeg filters and input stream codecs.",
                    file_path=str(input_video),
                )
            if not target_render_video.exists() or target_render_video.stat().st_size == 0:
                raise VideoProcessingError(
                    operation="render",
                    root_cause="FFmpeg completed but output video file is missing or 0 bytes.",
                    recovery_action="Check disk space and FFmpeg encoder settings.",
                    file_path=str(target_render_video),
                )

            # If animated outro tail is requested, seamlessly stitch it to the tail
            if has_outro:
                try:
                    self.append_outro_tail(
                        main_video=target_render_video,
                        outro_video=Path(outro_tail),
                        output_video=output_video,
                        preset=preset,
                    )
                finally:
                    if target_render_video.exists():
                        target_render_video.unlink()
            
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
