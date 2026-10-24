#!/usr/bin/env python3
"""Standalone CLI utility to publish a video directly and separately to PeerTube.

Usage:
  python scripts/publish_to_peertube.py --video output/my_video.mp4 --title "Episode #48"
  python scripts/publish_to_peertube.py --video output/my_video.mp4 --title "Episode #48" --thumbnail output/thumb.jpg
"""

import argparse
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.logging_config import get_logger
from src.config import get_settings
from src.publisher.peertube_client import PeerTubeClient
from src.publisher.youtube_client import VideoPublishMetadata

logger = get_logger(component="PeerTubeCLI")

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Upload a video independently to PeerTube.")
    parser.add_argument("--video", type=str, required=True, help="Path to .mp4 video file")
    parser.add_argument("--title", type=str, required=True, help="Video title")
    parser.add_argument("--description", type=str, default="", help="Video description")
    parser.add_argument("--thumbnail", type=str, default=None, help="Optional path to thumbnail image")
    parser.add_argument("--tags", type=str, default="LastDayOnEarth,LDoE,Survival,Gaming", help="Comma-separated tags")

    args = parser.parse_args()
    video_path = Path(args.video)

    if not video_path.exists():
        print(f"❌ Error: Video file not found: {video_path}")
        sys.exit(1)

    settings = get_settings()
    client = PeerTubeClient(
        instance_url=settings.peertube.instance_url,
        username=settings.peertube.username,
        password=settings.peertube.password,
        client_id=settings.peertube.client_id,
        client_secret=settings.peertube.client_secret,
        access_token=settings.peertube.access_token,
        channel_name=settings.peertube.channel_name,
        privacy_status=settings.peertube.privacy_status,
    )

    if not client.is_configured():
        print("❌ PeerTube is not configured in .env (PEERTUBE_INSTANCE_URL, USERNAME, PASSWORD)")
        sys.exit(1)

    tags = [t.strip() for t in args.tags.split(",") if t.strip()]
    metadata = VideoPublishMetadata(
        title=args.title,
        description=args.description or f"{args.title}\n\nLast Day on Earth Survival gameplay episode.",
        tags=tags,
        category_id="2",
        privacy_status=str(settings.peertube.privacy_status),
        thumbnail_path=args.thumbnail,
    )

    print(f"🚀 Uploading '{args.title}' to PeerTube ({settings.peertube.instance_url})...")
    url = client.upload_video(video_path=video_path, metadata=metadata)
    print(f"✅ Published successfully to PeerTube: {url}")


if __name__ == "__main__":
    main()
