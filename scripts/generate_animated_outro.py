#!/usr/bin/env python3
"""Standalone CLI utility to generate and preview animated Like, Share, and Subscribe outro options (7-10s).

Usage:
  python scripts/generate_animated_outro.py --all
  python scripts/generate_animated_outro.py --style cyber_row --duration 7.5
  python scripts/generate_animated_outro.py --style two_tier --duration 8.5
  python scripts/generate_animated_outro.py --style cinematic_slate --duration 10.0
"""

import argparse
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.logging_config import get_logger
from src.config import get_settings
from src.processor.outro_generator import OutroTailGenerator

logger = get_logger(component="OutroCLI")

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Generate animated Like/Share/Subscribe outro tail video options.")
    parser.add_argument(
        "--style",
        type=str,
        default="hype_bell_zoom",
        choices=["hype_bell_zoom", "hype_studio", "cartoon_comedy"],
        help="Animation style: hype_bell_zoom (9.5s, bell zoom + fade), hype_studio (9.5s, clean static bell), cartoon_comedy (8.0s)",
    )
    parser.add_argument("--duration", type=float, default=None, help="Custom duration in seconds (7-10s)")
    parser.add_argument("--fps", type=int, default=30, help="Framerate (default: 30)")
    parser.add_argument("--output", type=str, default=None, help="Output MP4 file path")
    parser.add_argument("--force", action="store_true", help="Force re-rendering even if cached asset exists")
    parser.add_argument("--all", action="store_true", help="Render both options side by side for selection")

    args = parser.parse_args()
    settings = get_settings()

    generator = OutroTailGenerator(
        assets_dir=Path("assets/animations"),
        audio_library_dir=settings.processing.music_library_file.parent / "audio",
        fonts_dir=Path("config/fonts"),
    )

    def extract_preview_snapshot(video_path: Path, timestamp: float = 7.8) -> Path:
        preview_path = video_path.with_suffix(".preview.jpg")
        try:
            import subprocess
            cmd = [
                "ffmpeg", "-y",
                "-ss", str(timestamp),
                "-i", str(video_path),
                "-frames:v", "1",
                "-update", "1",
                "-q:v", "2",
                str(preview_path),
            ]
            subprocess.run(cmd, capture_output=True, check=True)
            return preview_path
        except Exception:
            return preview_path

    if args.all:
        presets = [
            ("Option B1: Hype Studio + Continuous Bell Zoom & Scene Fade", "hype_bell_zoom", 9.5, Path("assets/animations/optionB1_hype_bell_zoom_9.5s.mp4")),
            ("Option B2: Hype Studio Clean Static Pedestal", "hype_studio", 9.5, Path("assets/animations/optionB2_hype_studio_clean_9.5s.mp4")),
        ]

        print("\n" + "=" * 75)
        print("🎬 GENERATING ANIMATED LIKE, SHARE & SUBSCRIBE OUTRO TAIL OPTIONS (7 - 10s)")
        print("=" * 75)

        results = []
        for title, style_name, default_dur, out_path in presets:
            dur = args.duration or default_dur
            print(f"\n▶️ Rendering {title} ({dur}s @ {args.fps}fps)...")
            clip = generator.render_outro_clip(
                output_mp4_path=out_path,
                duration=dur,
                fps=args.fps,
                style=style_name,
                series_title=settings.youtube.series_title,
                force_recreate=True,
            )
            preview = extract_preview_snapshot(clip, timestamp=7.6 if "zoom" in style_name else 5.2)
            size_kb = round(clip.stat().st_size / 1024, 1)
            print(f"   ✅ Video:    {clip} ({size_kb} KB)")
            print(f"   📸 Snapshot: {preview}")
            results.append((title, clip, preview, dur))

        print("\n" + "=" * 75)
        print("🎉 ALL OUTRO TAIL OPTIONS GENERATED SUCCESSFULLY FOR SELECTION:")
        print("=" * 75)
        for title, clip, preview, dur in results:
            print(f"• {title:<58} | {dur:4.1f}s | {clip.name}")
        print("=" * 75 + "\n")
        return

    # Single render
    default_durs = {
        "hype_bell_zoom": 9.5,
        "hype_studio": 9.5,
        "cartoon_comedy": 8.0,
    }
    duration = args.duration or default_durs.get(args.style, 9.5)
    target_path = Path(args.output) if args.output else Path(f"assets/animations/outro_{args.style}_{duration}s.mp4")

    print("\n" + "=" * 65)
    print("🎬 GENERATING ANIMATED LIKE, SHARE & SUBSCRIBE OUTRO TAIL")
    print("=" * 65)
    print(f"🎨 Style:      {args.style}")
    print(f"⏱️ Duration:   {duration}s @ {args.fps}fps")
    print(f"📁 Output:     {target_path}")
    print(f"🔄 Recreate:   {args.force}")
    print("-" * 65)

    out_file = generator.render_outro_clip(
        output_mp4_path=target_path,
        duration=duration,
        fps=args.fps,
        style=args.style,
        series_title=settings.youtube.series_title,
        force_recreate=args.force,
    )
    preview = extract_preview_snapshot(out_file, timestamp=min(duration - 2.0, 5.2))

    size_kb = round(out_file.stat().st_size / 1024, 1)
    print(f"✅ Generated successfully! ({size_kb} KB)")
    print(f"🎥 Video location:    {out_file.resolve()}")
    print(f"📸 Preview snapshot:  {preview.resolve()}\n")


if __name__ == "__main__":
    main()
