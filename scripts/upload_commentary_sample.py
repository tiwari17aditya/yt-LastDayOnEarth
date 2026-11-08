#!/usr/bin/env python3
"""Upload AI commentary comparison showcase video to YouTube as Unlisted for review."""

import argparse
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.logging_config import get_logger
from src.publisher.youtube_client import VideoPublishMetadata, YouTubeClient

logger = get_logger(component="SampleUploader")

# Ensure UTF-8 output encoding on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Upload commentary showcase sample to YouTube.")
    parser.add_argument("--video", type=str, required=True, help="Path to sample video MP4")
    parser.add_argument(
        "--privacy",
        type=str,
        default="unlisted",
        choices=["unlisted", "private", "public"],
        help="Privacy status (default: unlisted)",
    )

    args = parser.parse_args()
    video_path = Path(args.video)
    if not video_path.exists():
        logger.error(f"Sample video file not found: {video_path}")
        sys.exit(1)

    title = "Last Day on Earth - Pure AI Voice Commentary Showcase (Zero BGM)"
    description = (
        "Demonstration and comparison of 3 distinct AI voice commentary styles for Last Day on Earth (PURE VOICE - NO BGM):\n\n"
        "TIMESTAMPS:\n"
        "0:00 - Style 1: Energetic Gamer (Voice: Christopher - High-energy, reactive & punchy)\n"
        "0:39 - Style 2: Casual Walkthrough (Voice: Guy - Friendly, conversational & relaxed)\n"
        "1:18 - Style 3: Tactical Survival Guide (Voice: Andrew - Strategic, tips & mechanics)\n\n"
        "Audio Configuration:\n"
        "- Pure Neural Voice Track (zero background music)\n"
        "- Spoken style intro on each title card\n"
        "- Normalized broadcast loudness (0dB peak, -17.8dB mean)\n\n"
        "This is an unlisted review sample for channel development."
    )

    metadata = VideoPublishMetadata(
        title=title,
        description=description,
        tags=["Last Day on Earth", "LDoE", "Commentary", "AI Commentary", "Gaming", "Walkthrough", "Survival"],
        category_id="20",
        privacy_status=args.privacy,
    )

    logger.info(f"Uploading commentary showcase to YouTube ({args.privacy})...")
    client = YouTubeClient()
    url = client.upload_video(video_path, metadata)

    print("\n" + "=" * 60)
    print("SAMPLE SHOWCASE VIDEO UPLOADED SUCCESSFULLY!")
    print(f"Privacy Status: {args.privacy.upper()}")
    print(f"Review URL: {url}")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()

