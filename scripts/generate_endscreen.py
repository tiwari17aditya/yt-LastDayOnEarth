#!/usr/bin/env python3
"""CLI utility to generate a cinematic YouTube End-Screen outro clip.

Usage:
  python scripts/generate_endscreen.py --duration 12 --output data/endscreens/outro_slate.mp4
"""

import argparse
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.logging_config import get_logger
from src.processor.endscreen_generator import EndScreenGenerator

logger = get_logger(component="EndScreenCLI")

# Ensure UTF-8 output encoding on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Generate cinematic YouTube EndScreen outro video.")
    parser.add_argument("--output", type=str, default="data/endscreens/outro_slate.mp4", help="Output MP4 file path")
    parser.add_argument("--duration", type=float, default=12.0, help="Duration in seconds (default: 12.0)")
    parser.add_argument("--audio", type=str, default="config/audio/wasteland_horizon.mp3", help="Audio track for outro (optional)")
    parser.add_argument("--title", type=str, default="LAST DAY ON EARTH: SURVIVAL", help="Series title")

    args = parser.parse_args()

    generator = EndScreenGenerator()
    audio_path = Path(args.audio) if args.audio and Path(args.audio).exists() else None

    try:
        out = generator.render_endscreen_clip(
            output_mp4_path=Path(args.output),
            duration=args.duration,
            audio_file=audio_path,
            series_title=args.title,
        )
        print(f"🎬 End-Screen Outro Slate generated successfully!")
        print(f"📁 File: {out}")
        print(f"⏱️ Duration: {args.duration:.1f}s | Resolution: 1920x1080 (16:9)")
        print(f"💡 YouTube Studio Template: Select 'One video, One playlist, One subscribe'")
    except Exception as e:
        logger.error(f"Failed to generate EndScreen: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
