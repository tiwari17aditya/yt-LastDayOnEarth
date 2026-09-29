#!/usr/bin/env python3
"""Post high-engagement creator comments to YouTube videos.

Can be run for:
1. A specific video ID: python scripts/post_engagement_comments.py --video-id <ID>
2. All published episodes in the series tracker: python scripts/post_engagement_comments.py --all-episodes
"""

import argparse
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.logging_config import get_logger
from src.publisher.youtube_client import YouTubeClient
from src.publisher.title_manager import TitleManager
from src.google_auth import get_google_credentials
from googleapiclient.discovery import build

logger = get_logger(component="EngagementCommentCLI")

# Ensure UTF-8 output encoding on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Post creator engagement comments to YouTube videos.")
    parser.add_argument("--video-id", type=str, help="Specific YouTube Video ID to comment on")
    parser.add_argument("--episode", type=int, help="Episode number (optional, will auto-detect if omitted)")
    parser.add_argument("--all-episodes", action="store_true", help="Post engagement comments to all published episodes in series tracker")
    parser.add_argument("--custom-text", type=str, help="Custom prompt or question text")

    args = parser.parse_args()

    creds = get_google_credentials(
        scopes=[
            "https://www.googleapis.com/auth/youtube.upload",
            "https://www.googleapis.com/auth/youtube.force-ssl",
        ]
    )
    if not creds:
        logger.error("Failed to acquire YouTube credentials. Verify Google auth.")
        sys.exit(1)

    youtube = build("youtube", "v3", credentials=creds, cache_discovery=False)
    client = YouTubeClient()
    tm = TitleManager()
    tracker_data = {}
    if tm.tracker_file.exists():
        try:
            tracker_data = json.loads(tm.tracker_file.read_text(encoding="utf-8"))
        except Exception:
            pass

    # Determine playlist URL
    playlist_id = client.get_or_create_playlist(youtube)
    playlist_url = f"https://www.youtube.com/playlist?list={playlist_id}" if playlist_id else None

    targets = []
    if args.video_id:
        targets.append((args.video_id, args.episode or 1))
    elif args.all_episodes:
        for ep in tracker_data.get("completed_episodes", []):
            vid = ep.get("video_id")
            num = ep.get("episode_number")
            if vid:
                targets.append((vid, num))
    else:
        # Default: last published episode
        completed = tracker_data.get("completed_episodes", [])
        if completed:
            last = completed[-1]
            targets.append((last.get("video_id"), last.get("episode_number")))
        else:
            logger.error("No target specified and no completed episodes found. Use --video-id or --all-episodes.")
            sys.exit(1)

    for vid, ep_num in targets:
        logger.info(f"Posting engagement comment to Video {vid} (Episode #{ep_num})...")
        cid = client.post_engagement_comment(
            youtube=youtube,
            video_id=vid,
            episode_number=ep_num,
            playlist_url=playlist_url,
            custom_question=args.custom_text,
        )
        if cid:
            print(f"✅ Comment posted to https://youtu.be/{vid} (Comment ID: {cid})")
        else:
            print(f"⚠️ Failed or skipped commenting on {vid}")


if __name__ == "__main__":
    main()
