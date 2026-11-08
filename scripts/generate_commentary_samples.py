#!/usr/bin/env python3
"""Generate sample videos comparing all three AI commentary personas for Last Day on Earth.

Styles evaluated:
  1. Energetic Gamer (en-US-ChristopherNeural)
  2. Casual Walkthrough (en-US-GuyNeural)
  3. Tactical Survival Guide (en-US-AndrewNeural)

Produces individual samples as well as a single, unified 3-part comparison video.
"""

import argparse
import asyncio
import os
import subprocess
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.audio.commentary_engine import (
    CommentaryEngine,
    CommentaryPersona,
    PERSONA_PROFILES,
)
from src.audio.selector import AudioMixer
from src.logging_config import get_logger

logger = get_logger(component="CommentarySamples")

# Ensure UTF-8 output encoding on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def probe_duration(path: Path) -> float:
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(path),
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return float(res.stdout.strip())


def render_title_slate(text: str, subtitle: str, duration: float, output_path: Path) -> Path:
    """Generates a sleek 1080p intro slate with Pillow image rendering."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    from PIL import Image, ImageDraw, ImageFont

    # Create 1920x1080 dark canvas
    img = Image.new("RGB", (1920, 1080), color=(17, 22, 37))
    draw = ImageDraw.Draw(img)

    try:
        font_main = ImageFont.truetype("arialbd.ttf", 64)
        font_sub = ImageFont.truetype("arial.ttf", 36)
    except Exception:
        font_main = ImageFont.load_default()
        font_sub = ImageFont.load_default()

    # Draw main text (centered, golden yellow)
    bbox1 = draw.textbbox((0, 0), text, font=font_main)
    w1 = bbox1[2] - bbox1[0]
    draw.text(((1920 - w1) // 2, 460), text, fill=(255, 204, 0), font=font_main)

    # Draw subtitle (centered, white)
    bbox2 = draw.textbbox((0, 0), subtitle, font=font_sub)
    w2 = bbox2[2] - bbox2[0]
    draw.text(((1920 - w2) // 2, 560), subtitle, fill=(230, 230, 240), font=font_sub)

    temp_png = output_path.with_suffix(".png")
    img.save(temp_png)

    # Render PNG + silent audio to MP4
    cmd = [
        "ffmpeg", "-y",
        "-loop", "1",
        "-i", str(temp_png),
        "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
        "-c:v", "libx264",
        "-t", str(duration),
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-shortest",
        str(output_path),
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    if temp_png.exists():
        temp_png.unlink()
    return output_path


async def generate_single_sample(
    engine: CommentaryEngine,
    persona: CommentaryPersona,
    video_source: Path,
    bgm_source: Path,
    output_dir: Path,
    sample_duration: float = 45.0,
    episode_number: int = 99,
) -> Path:
    """Builds a complete, ducked commentary sample video for a single persona."""
    sample_video = output_dir / f"sample_{persona.value}.mp4"
    if sample_video.exists() and sample_video.stat().st_size > 0:
        logger.info(f"Reusing existing sample video: {sample_video}")
        return sample_video

    profile = engine.get_persona_config(persona)
    logger.info(f"Generating sample for persona: {persona.value.upper()} ({profile.voice})...")

    # 1. Generate Script Cues
    cues = engine.generate_script(
        duration=sample_duration,
        episode_number=episode_number,
        persona=persona,
    )

    # 2. Synthesize audio cues
    await engine.synthesize_all_cues_async(cues, persona=persona)

    # 3. Build Timeline Commentary Track
    comm_track = output_dir / f"commentary_{persona.value}.m4a"
    engine.build_timeline_commentary_track(
        cues=cues,
        total_duration=sample_duration,
        output_path=comm_track,
    )

    # 4. Prepare BGM segment
    sample_bgm = output_dir / f"bgm_{persona.value}.m4a"
    trim_bgm_cmd = [
        "ffmpeg", "-y",
        "-ss", "0",
        "-t", str(sample_duration),
        "-i", str(bgm_source),
        "-c:a", "aac",
        "-b:a", "192k",
        str(sample_bgm),
    ]
    subprocess.run(trim_bgm_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

    # 5. Mix Commentary with Ducked BGM
    mixed_audio = output_dir / f"mixed_{persona.value}.m4a"
    engine.mix_commentary_with_bgm(
        commentary_audio=comm_track,
        bgm_audio=sample_bgm,
        output_audio_path=mixed_audio,
        ducking_ratio=6.0,
        voice_volume_boost_db="+2dB",
    )

    # 6. Extract video clip and mux with mixed audio
    sample_video = output_dir / f"sample_{persona.value}.mp4"
    mux_cmd = [
        "ffmpeg", "-y",
        "-ss", "0",
        "-t", str(sample_duration),
        "-i", str(video_source),
        "-i", str(mixed_audio),
        "-map", "0:v:0",
        "-map", "1:a:0",
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-c:a", "aac",
        "-b:a", "192k",
        "-shortest",
        str(sample_video),
    ]
    subprocess.run(mux_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    logger.info(f"Sample completed: {sample_video} ({sample_duration:.1f}s)")
    return sample_video


def build_unified_showcase(
    samples: list[tuple[CommentaryPersona, Path]],
    output_path: Path,
    temp_dir: Path,
) -> Path:
    """Concatenates all 3 persona samples into a single comparative showcase with visual slates."""
    logger.info("Assembling unified 3-part comparison showcase video...")
    slate_list: list[Path] = []
    concat_entries: list[Path] = []

    titles = {
        CommentaryPersona.ENERGETIC: ("STYLE 1: ENERGETIC GAMER", "Voice: Christopher | High Energy & Hype"),
        CommentaryPersona.CASUAL: ("STYLE 2: CASUAL WALKTHROUGH", "Voice: Guy | Warm, Natural & Conversational"),
        CommentaryPersona.TACTICAL: ("STYLE 3: TACTICAL SURVIVAL GUIDE", "Voice: Andrew | Strategic & Focused Tips"),
    }

    for idx, (persona, video_path) in enumerate(samples):
        title, sub = titles[persona]
        slate_path = temp_dir / f"slate_{idx}.mp4"
        render_title_slate(title, sub, duration=3.0, output_path=slate_path)
        concat_entries.append(slate_path)
        concat_entries.append(video_path)

    # Concat file list
    concat_txt = temp_dir / "concat_list.txt"
    with open(concat_txt, "w", encoding="utf-8") as f:
        for entry in concat_entries:
            clean_path = str(entry.resolve()).replace("\\", "/")
            f.write(f"file '{clean_path}'\n")

    cmd = [
        "ffmpeg", "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", str(concat_txt),
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-c:a", "aac",
        str(output_path),
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    logger.info(f"Unified showcase successfully rendered: {output_path}")
    return output_path


def main():
    parser = argparse.ArgumentParser(description="Generate AI commentary samples across all personas.")
    parser.add_argument("--video", type=str, required=True, help="Input gameplay video file")
    parser.add_argument("--episode", type=int, default=99, help="Episode number context (default: 99)")
    parser.add_argument("--duration", type=float, default=40.0, help="Duration in seconds per sample (default: 40.0)")
    parser.add_argument("--output-dir", type=str, default="output/commentary_samples", help="Output directory")

    args = parser.parse_args()
    video_path = Path(args.video)
    if not video_path.exists():
        logger.error(f"Input video not found: {video_path}")
        sys.exit(1)

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    engine = CommentaryEngine(temp_dir=out_dir / "temp")

    # Pick a soothing background track from catalog
    mixer = AudioMixer()
    track_info = mixer.select_track(mood="gaming")
    bgm_path = Path(track_info["file_path"])
    if not bgm_path.exists():
        # Fallback to any available audio file
        bgm_candidates = list(Path("config/audio").glob("*.mp3"))
        if bgm_candidates:
            bgm_path = bgm_candidates[0]
        else:
            logger.error("No background music audio tracks found in config/audio.")
            sys.exit(1)

    logger.info(f"Using BGM track: {bgm_path.name}")

    personas = [
        CommentaryPersona.ENERGETIC,
        CommentaryPersona.CASUAL,
        CommentaryPersona.TACTICAL,
    ]

    samples: list[tuple[CommentaryPersona, Path]] = []
    for persona in personas:
        sample_file = asyncio.run(
            generate_single_sample(
                engine=engine,
                persona=persona,
                video_source=video_path,
                bgm_source=bgm_path,
                output_dir=out_dir,
                sample_duration=args.duration,
                episode_number=args.episode,
            )
        )
        samples.append((persona, sample_file))

    # Assemble Unified Showcase Video
    unified_showcase = out_dir / "unified_commentary_showcase_all_styles.mp4"
    build_unified_showcase(samples, unified_showcase, temp_dir=out_dir / "temp")

    print("\n" + "=" * 60)
    print("AI COMMENTARY SAMPLES GENERATED SUCCESSFULLY!")
    print("=" * 60)
    for p, s in samples:
        print(f"- {p.value.upper()}: {s}")
    print(f"\nUnified 3-in-1 Comparison Showcase: {unified_showcase}")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
