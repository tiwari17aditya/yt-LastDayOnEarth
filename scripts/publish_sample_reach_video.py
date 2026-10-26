#!/usr/bin/env python3
"""Publish a demonstration sample video to YouTube showcasing audience reach maximization updates.

Features demonstrated:
1. Search-intent guide title (+37% retention formula).
2. Multi-language metadata localizations (Russian, Portuguese, Spanish) via YouTube Data API v3.
3. Context-aware creator engagement comment with grind empathy & survey hook.
4. YouTube 00:00 chapter timestamps & dynamic trending hashtags.
5. Thumbnail attachment & playlist integration.
"""

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.logging_config import get_logger
from src.publisher.youtube_client import YouTubeClient, VideoPublishMetadata
from src.publisher.title_manager import TitleManager

logger = get_logger(component="SampleReachPublisher")

# Ensure UTF-8 output encoding on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


@dataclass
class SimulatedEvent:
    description: str
    start_time: float


def main():
    parser = argparse.ArgumentParser(description="Publish sample video showcasing reach maximization updates.")
    parser.add_argument("--video", type=str, default="output/sample_video_with_endcredits.mp4", help="Video path")
    parser.add_argument("--thumbnail", type=str, default="data/thumbnails/episode_55.jpg", help="Thumbnail path")
    parser.add_argument("--privacy", type=str, default="unlisted", choices=["public", "unlisted", "private"], help="YouTube privacy status")
    parser.add_argument("--episode", type=int, default=55, help="Episode number")

    args = parser.parse_args()

    video_path = Path(args.video)
    if not video_path.exists():
        logger.error(f"Sample video not found at: {video_path}")
        sys.exit(1)

    thumbnail_path = Path(args.thumbnail) if Path(args.thumbnail).exists() else None

    # High-intent gameplay events matching LDoE search demand (Bunker Alfa, Chopper, Smelting)
    events = [
        SimulatedEvent(description="Bunker Alfa Terminal & Prep", start_time=0.0),
        SimulatedEvent(description="Bunker Alfa Floor 2 Clearing", start_time=6.0),
        SimulatedEvent(description="Smelting Iron & Chopper Parts", start_time=12.0),
    ]

    print("\n" + "=" * 70)
    print("🚀 GENERATING REACH-MAXIMIZED SAMPLE VIDEO FOR YOUTUBE")
    print("=" * 70)

    # Initialize TitleManager configured for search_guide style
    tm = TitleManager(title_style="search_guide", episode_numbering=True)
    client = YouTubeClient(
        privacy_status=args.privacy,
        title_manager=tm,
    )

    print("\n[1/3] Generating SEO Search Titles, Localizations & Chapters...")
    metadata: VideoPublishMetadata = client.generate_metadata(
        video_title="Sample Gameplay Run",
        events=events,
        thumbnail_path=thumbnail_path,
        episode_number=args.episode,
    )

    print(f"\n📌 Primary English Title (Search-First):")
    print(f"   {metadata.title}")

    print(f"\n🌍 Multi-Language Native Localizations:")
    if metadata.localizations:
        for lang, loc in metadata.localizations.items():
            print(f"   [{lang.upper()}]: {loc.get('title')}")
    else:
        print("   (None generated)")

    print(f"\n⏱️ Chapter Markers:")
    for line in metadata.description.splitlines():
        if "TIMESTAMPS" in line or (":" in line and ("-" in line or "–" in line)):
            print(f"   {line}")

    print(f"\n[2/3] Uploading video to YouTube (Privacy: {args.privacy.upper()})...")
    youtube_url = client.upload_video(video_path=video_path, metadata=metadata)

    print("\n" + "=" * 70)
    print("🎉 DEMONSTRATION VIDEO PUBLISHED SUCCESSFULLY!")
    print(f"🔗 YouTube Video URL: {youtube_url}")
    print(f"🔒 Privacy Status:    {args.privacy.upper()}")
    print(f"🌎 Native Localizations Active: {', '.join(metadata.localizations.keys()) if metadata.localizations else 'N/A'}")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
