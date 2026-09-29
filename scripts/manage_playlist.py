#!/usr/bin/env python3
"""CLI utility for YouTube playlist management, chronological sorting, and auditing.

Usage:
  python scripts/manage_playlist.py --audit
  python scripts/manage_playlist.py --sort
  python scripts/manage_playlist.py --dedup
"""

import argparse
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.logging_config import get_logger
from src.google_auth import get_google_credentials
from src.publisher.playlist_manager import PlaylistManager
from src.publisher.youtube_client import YouTubeClient
from googleapiclient.discovery import build

logger = get_logger(component="PlaylistCLI")

# Ensure UTF-8 output encoding on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="YouTube Playlist Management CLI.")
    parser.add_argument("--playlist-id", type=str, help="Specific playlist ID (defaults to LDoE official series)")
    parser.add_argument("--audit", action="store_true", help="Audit playlist order, count, and duplicates")
    parser.add_argument("--sort", action="store_true", help="Sort playlist into strict chronological order (#1 -> #N)")
    parser.add_argument("--dedup", action="store_true", help="Remove duplicate video entries in the playlist")

    args = parser.parse_args()

    creds = get_google_credentials(
        scopes=[
            "https://www.googleapis.com/auth/youtube.upload",
            "https://www.googleapis.com/auth/youtube.force-ssl",
        ]
    )
    if not creds:
        logger.error("No valid Google credentials available. Run scripts/setup_google_auth.py.")
        sys.exit(1)

    youtube = build("youtube", "v3", credentials=creds, cache_discovery=False)
    client = YouTubeClient()
    manager = PlaylistManager()

    playlist_id = args.playlist_id
    if not playlist_id:
        playlist_id = client.get_or_create_playlist(youtube)

    if not playlist_id:
        logger.error("Could not find or create target YouTube playlist.")
        sys.exit(1)

    print(f"\n📺 Managing YouTube Playlist: {playlist_id}")

    if args.dedup:
        print("\n🧹 Deduplicating playlist...")
        removed = manager.deduplicate_playlist(youtube, playlist_id)
        print(f"✅ Removed {removed} duplicate items.")

    if args.sort:
        print("\n🔀 Sorting playlist into chronological order (Episode 1 to N)...")
        manager.sort_playlist_chronological(youtube, playlist_id)
        print("✅ Playlist sorted successfully.")

    # Default action: run audit
    print("\n🔍 Running playlist audit...")
    audit = manager.audit_playlist(youtube, playlist_id)
    print(f"📊 Total items: {audit['total_items']}")
    print(f"🎬 Unique videos: {audit['unique_videos']}")
    print(f"⏱️ Chronological order: {'✅ YES' if audit['is_chronological'] else '⚠️ NO (Needs --sort)'}")
    print(f"🔢 Episode sequence: {audit['episode_order']}")

    if audit["duplicates"]:
        print(f"⚠️ Found {len(audit['duplicates'])} duplicate(s):")
        for d in audit["duplicates"]:
            print(f"   • {d['video_id']} - {d['title']}")
    else:
        print("✨ No duplicates found.")

    print("\nCurrent Items:")
    for it in audit["items"]:
        ep_tag = f"[Ep #{it['episode_number']}]" if it["episode_number"] else "[Unnumbered]"
        print(f"  {it['position']:02d}. {ep_tag:10s} {it['video_id']} | {it['title']}")

    print("\n💡 Done.")


if __name__ == "__main__":
    main()
