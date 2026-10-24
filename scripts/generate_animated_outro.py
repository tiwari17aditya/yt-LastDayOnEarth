#!/usr/bin/env python3
"""Standalone CLI utility to generate and preview the animated Like, Share, and Subscribe outro tail.

Usage:
  python scripts/generate_animated_outro.py
  python scripts/generate_animated_outro.py --duration 7.0 --force
  python scripts/generate_animated_outro.py --output assets/animations/custom_outro.mp4
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
    parser = argparse.ArgumentParser(description="Generate animated Like/Share/Subscribe outro tail video.")
    parser.add_argument("--duration", type=float, default=6.0, help="Duration in seconds (default: 6.0s)")
    parser.add_argument("--fps", type=int, default=30, help="Framerate (default: 30)")
    parser.add_argument("--output", type=str, default=None, help="Output MP4 file path")
    parser.add_argument("--force", action="store_true", help="Force re-rendering even if cached asset exists")

    args = parser.parse_args()
    settings = get_settings()

    target_path = Path(args.output) if args.output else settings.processing.outro_tail_path
    generator = OutroTailGenerator(
        assets_dir=target_path.parent,
        audio_library_dir=settings.processing.music_library_file.parent / "audio",
    )

    print("\n" + "=" * 65)
    print("🎬 GENERATING ANIMATED LIKE, SHARE & SUBSCRIBE OUTRO TAIL")
    print("=" * 65)
    print(f"⏱️ Duration:   {args.duration}s @ {args.fps}fps")
    print(f"📁 Output:     {target_path}")
    print(f"🔄 Recreate:   {args.force}")
    print("-" * 65)

    out_file = generator.render_outro_clip(
        output_mp4_path=target_path,
        duration=args.duration,
        fps=args.fps,
        series_title=settings.youtube.series_title,
        force_recreate=args.force,
    )

    size_kb = round(out_file.stat().st_size / 1024, 1)
    print(f"✅ Generated successfully! ({size_kb} KB)")
    print(f"🎥 Video location: {out_file.resolve()}\n")


if __name__ == "__main__":
    main()
