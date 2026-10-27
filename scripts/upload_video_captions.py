#!/usr/bin/env python3
"""CLI tool to upload multi-language Closed Caption tracks (.srt) to an existing YouTube video.

Usage:
  python scripts/upload_video_captions.py --video-id <VIDEO_ID>
"""

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.logging_config import get_logger
from src.google_auth import get_google_credentials
from src.publisher.youtube_client import YouTubeClient
from googleapiclient.discovery import build

logger = get_logger(component="CaptionsCLI")

# Ensure UTF-8 output encoding on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


@dataclass
class SimulatedEvent:
    description: str
    start_time: float
    end_time: float


def main():
    parser = argparse.ArgumentParser(description="Upload multi-language Closed Caption tracks to a YouTube video.")
    parser.add_argument("--video-id", type=str, default="ULP9BZ5S1cg", help="YouTube video ID")
    parser.add_argument("--languages", nargs="+", default=["en", "ru", "pt", "es"], help="Languages to upload (en, ru, pt, es)")

    args = parser.parse_args()

    creds = get_google_credentials(
        scopes=[
            "https://www.googleapis.com/auth/youtube.upload",
            "https://www.googleapis.com/auth/youtube.force-ssl",
        ]
    )
    if not creds:
        logger.error("Failed to acquire Google credentials. Verify Google auth.")
        sys.exit(1)

    youtube = build("youtube", "v3", credentials=creds, cache_discovery=False)
    client = YouTubeClient()

    # Define high-intent tutorial events with timestamps
    events = [
        SimulatedEvent(description="Bunker Alfa Terminal & Prep", start_time=0.0, end_time=4.5),
        SimulatedEvent(description="Bunker Alfa Floor 2 Clearing & Combat", start_time=5.0, end_time=11.5),
        SimulatedEvent(description="Smelting Iron & Chopper Parts Assembly", start_time=12.0, end_time=18.0),
    ]

    print("\n" + "=" * 65)
    print(f"🎬 UPLOADING MULTI-LANGUAGE CLOSED CAPTIONS TO VIDEO {args.video_id}")
    print("=" * 65)

    results = client.upload_captions(
        youtube=youtube,
        video_id=args.video_id,
        events=events,
        languages=args.languages,
    )

    print("\n📊 CAPTION UPLOAD RESULTS:")
    for lang, cap_id in results.items():
        print(f"   ✅ [{lang.upper()}] Caption Track Created (ID: {cap_id})")

    if not results:
        print("   ⚠️ No caption tracks could be uploaded. Check API logs.")

    print(f"\n🔗 View interactive captions on video: https://youtu.be/{args.video_id}")
    print("=" * 65 + "\n")


if __name__ == "__main__":
    main()
