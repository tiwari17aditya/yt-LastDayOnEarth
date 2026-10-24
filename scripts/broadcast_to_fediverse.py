#!/usr/bin/env python3
"""Standalone CLI utility to broadcast an episode announcement directly to the Fediverse (Mastodon / Lemmy).

Usage:
  python scripts/broadcast_to_fediverse.py --title "Episode #48" --youtube-url "https://youtu.be/..."
  python scripts/broadcast_to_fediverse.py --title "Episode #48" --youtube-url "https://youtu.be/..." --thumbnail output/thumb.jpg
"""

import argparse
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.logging_config import get_logger
from src.config import get_settings
from src.publisher.fediverse_broadcaster import FediverseBroadcaster

logger = get_logger(component="FediverseBroadcastCLI")

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Broadcast an episode release announcement independently to Mastodon/Lemmy.")
    parser.add_argument("--title", type=str, required=True, help="Episode title")
    parser.add_argument("--youtube-url", type=str, required=True, help="YouTube watch URL")
    parser.add_argument("--peertube-url", type=str, default=None, help="Optional PeerTube watch URL")
    parser.add_argument("--episode", type=int, default=None, help="Optional episode number")
    parser.add_argument("--thumbnail", type=str, default=None, help="Optional path to thumbnail image")

    args = parser.parse_args()

    settings = get_settings()
    broadcaster = FediverseBroadcaster(
        mastodon_instance=settings.fediverse.mastodon_instance,
        mastodon_access_token=settings.fediverse.mastodon_access_token,
        lemmy_instance=settings.fediverse.lemmy_instance,
        lemmy_auth_token=settings.fediverse.lemmy_auth_token,
        lemmy_community_id=settings.fediverse.lemmy_community_id,
    )

    if not broadcaster.is_mastodon_enabled() and not broadcaster.is_lemmy_enabled():
        print("❌ Neither Mastodon nor Lemmy is configured in .env (check MASTODON_INSTANCE_URL and MASTODON_ACCESS_TOKEN)")
        sys.exit(1)

    thumb_path = Path(args.thumbnail) if args.thumbnail else None

    print(f"📢 Broadcasting announcement for '{args.title}' to the Fediverse...")
    results = broadcaster.broadcast_release(
        title=args.title,
        youtube_url=args.youtube_url,
        episode_number=args.episode,
        peertube_url=args.peertube_url,
        thumbnail_path=thumb_path,
    )

    if results.get("mastodon_url"):
        print(f"✅ Mastodon Post: {results['mastodon_url']}")
    if results.get("lemmy_url"):
        print(f"✅ Lemmy Post: {results['lemmy_url']}")

    if not any(results.values()):
        print("⚠️ Broadcast completed but no status URLs were returned (check credentials or logs).")


if __name__ == "__main__":
    main()
