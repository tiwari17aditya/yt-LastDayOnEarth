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
        default="cyber_row",
        choices=["cyber_row", "two_tier", "cinematic_slate"],
        help="Animation style: cyber_row (7.5s), two_tier (8.5s), cinematic_slate (10.0s)",
    )
    parser.add_argument("--duration", type=float, default=None, help="Custom duration in seconds")
    parser.add_argument("--fps", type=int, default=30, help="Framerate (default: 30)")
    parser.add_argument("--output", type=str, default=None, help="Output MP4 file path")
    parser.add_argument("--force", action="store_true", help="Force re-rendering even if cached asset exists")
    parser.add_argument("--all", action="store_true", help="Render all 3 options side by side for selection")

    args = parser.parse_args()
    settings = get_settings()

    generator = OutroTailGenerator(
        assets_dir=Path("assets/animations"),
        audio_library_dir=settings.processing.music_library_file.parent / "audio",
    )

    if args.all:
        presets = [
            ("Option 1: Cyber-Survival Row", "cyber_row", 7.5, Path("assets/animations/option1_cyber_row_7.5s.mp4")),
            ("Option 2: Two-Tier Hero Studio", "two_tier", 8.5, Path("assets/animations/option2_two_tier_hero_8.5s.mp4")),
            ("Option 3: Cinematic End-Screen Slate", "cinematic_slate", 10.0, Path("assets/animations/option3_cinematic_slate_10.0s.mp4")),
        ]

        print("\n" + "=" * 70)
        print("🎬 GENERATING ALL 3 ANIMATED OUTRO TAIL OPTIONS (7 - 10s)")
        print("=" * 70)

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
            size_kb = round(clip.stat().st_size / 1024, 1)
            print(f"   ✅ Saved: {clip} ({size_kb} KB)")
            results.append((title, clip, dur))

        print("\n" + "=" * 70)
        print("🎉 ALL 3 OPTIONS GENERATED SUCCESSFULLY FOR SELECTION:")
        print("=" * 70)
        for title, clip, dur in results:
            print(f"• {title:<36} | {dur:4.1f}s | {clip.resolve()}")
        print("=" * 70 + "\n")
        return

    # Single render
    default_durs = {
        "cyber_row": 7.5,
        "two_tier": 8.5,
        "cinematic_slate": 10.0,
    }
    duration = args.duration or default_durs.get(args.style, 7.5)
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

    size_kb = round(out_file.stat().st_size / 1024, 1)
    print(f"✅ Generated successfully! ({size_kb} KB)")
    print(f"🎥 Video location: {out_file.resolve()}\n")


if __name__ == "__main__":
    main()
