#!/usr/bin/env python3
"""CLI utility to generate and optionally publish YouTube Shorts (9:16 vertical video).

Usage:
  python scripts/generate_short.py --video data/output/ep12_final.mp4 --start 60 --duration 35 --episode 12
"""

import argparse
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.logging_config import get_logger
from src.processor.shorts_generator import ShortsGenerator

logger = get_logger(component="ShortsCLI")

# Ensure UTF-8 output encoding on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Generate 9:16 YouTube Shorts from gameplay video.")
    parser.add_argument("--video", type=str, required=True, help="Path to input 16:9 MP4 video")
    parser.add_argument("--output", type=str, help="Destination path for generated Short MP4")
    parser.add_argument("--start", type=float, default=60.0, help="Start time offset in seconds (default: 60.0)")
    parser.add_argument("--duration", type=float, default=35.0, help="Duration in seconds (default: 35.0, max 58.0)")
    parser.add_argument("--headline", type=str, default="LAST DAY ON EARTH", help="Top header headline")
    parser.add_argument("--subtitle", type=str, default="SURVIVAL INTENSIFIES", help="Subtitle hook")
    parser.add_argument("--episode", type=int, help="Episode number to display")

    args = parser.parse_args()

    input_path = Path(args.video)
    if not input_path.exists():
        logger.error(f"Input video file not found: {input_path}")
        sys.exit(1)

    if args.output:
        output_path = Path(args.output)
    else:
        ep_label = f"_ep{args.episode}" if args.episode else ""
        output_path = Path(f"data/shorts/short{ep_label}_{input_path.stem}.mp4")

    generator = ShortsGenerator()

    try:
        final_short = generator.generate_short(
            input_video=input_path,
            output_path=output_path,
            start_time=args.start,
            duration=args.duration,
            headline=args.headline,
            subtitle=args.subtitle,
            episode_number=args.episode,
        )
        print(f"🎉 YouTube Short rendered successfully!")
        print(f"📁 Output file: {final_short}")
        print(f"⏱️ Length: {args.duration:.1f}s | Resolution: 1080x1920 (9:16)")
        print(f"💡 Tip: Upload to YouTube with tags: #Shorts #LastDayOnEarth #LDoE #SurvivalGaming")
    except Exception as e:
        logger.error(f"Failed to generate Short: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
