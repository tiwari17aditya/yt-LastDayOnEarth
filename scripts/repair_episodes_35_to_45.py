#!/usr/bin/env python3
"""Repair YouTube thumbnails and playlist membership for Episodes #35 to #45."""

import io
import json
import sys
from pathlib import Path

# Force UTF-8 stdout
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from src.google_auth import get_google_credentials
from src.logging_config import get_logger
from src.processor.cinematic_branding import apply_cinematic_grunge_branding
from src.publisher.playlist_manager import PlaylistManager

logger = get_logger(component="Repair35to45")

EPISODES_TO_REPAIR = [
    {
        "episode": 35,
        "video_id": "iHsJC8FD5g8",
        "title": "Blueprint Upgrades + Woodcraft & Planks! | LDoE Survival #35",
        "template": "workshop_template.jpg",
    },
    {
        "episode": 36,
        "video_id": "8mwkddL7Qx4",
        "title": "Workshop & Smelting + Home Base Operations! | LDoE Survival #36",
        "template": "workshop_template.jpg",
    },
    {
        "episode": 37,
        "video_id": "HBoSZhKI-68",
        "title": "Blueprint Upgrades & Entering Home Base! | LDoE Survival #37",
        "template": "base_template.jpg",
    },
    {
        "episode": 38,
        "video_id": "j9_0xif_IS0",
        "title": "Entering Home Base & Blueprint Upgrades! | LDoE Survival #38",
        "template": "base_template.jpg",
    },
    {
        "episode": 39,
        "video_id": "bfO1osdZWnA",
        "title": "Blueprint Upgrades & Home Base Operations! | LDoE Survival #39",
        "template": "base_template.jpg",
    },
    {
        "episode": 40,
        "video_id": "8QMUzXpLZpI",
        "title": "Blueprint Upgrades & Home Base Operations! | LDoE Survival #40",
        "template": "base_template.jpg",
    },
    {
        "episode": 41,
        "video_id": "qgJhFNqu3MA",
        "title": "Blueprint Upgrades + Woodcraft & Planks! | LDoE Survival #41",
        "template": "workshop_template.jpg",
    },
    {
        "episode": 42,
        "video_id": "ZQR3pxK1H60",
        "title": "Base Storage Optimization + Inventory & Resource Sorting! | LDoE Survival #42",
        "template": "storage_template.jpg",
    },
    {
        "episode": 43,
        "video_id": "f19_oMxA-QY",
        "title": "Base Storage Optimization & Entering Home Base! | LDoE Survival #43",
        "template": "storage_template.jpg",
    },
    {
        "episode": 44,
        "video_id": "HZw-hd4Fj5I",
        "title": "Base Storage Optimization & Blueprint Upgrades! | LDoE Survival #44",
        "template": "storage_template.jpg",
    },
    {
        "episode": 45,
        "video_id": "c8uTpFfD-ew",
        "title": "Home Base Operations & Zombie Horde Defense! | LDoE Survival #45",
        "template": "defense_template.jpg",
    },
]

TARGET_PLAYLIST_ID = "PLJPzVNVZwaGY"


def run_repair():
    print("=" * 70)
    print("REPAIR ROUTINE: Episodes #35 to #45 (Thumbnails & Playlist)")
    print("=" * 70)

    creds = get_google_credentials(
        scopes=[
            "https://www.googleapis.com/auth/youtube.upload",
            "https://www.googleapis.com/auth/youtube.force-ssl",
        ]
    )
    if not creds:
        print("[ERROR] Could not obtain valid YouTube credentials.")
        sys.exit(1)

    yt = build("youtube", "v3", credentials=creds)
    pm = PlaylistManager()

    template_dir = Path("data/thumbnails/templates")
    thumb_dir = Path("data/thumbnails")
    thumb_dir.mkdir(parents=True, exist_ok=True)

    # 1. Generate Grunge Thumbnails
    print("\n--- STEP 1: Generating Official Cinematic Grunge Thumbnails ---")
    for item in EPISODES_TO_REPAIR:
        ep = item["episode"]
        tmpl = item["template"]
        tmpl_file = template_dir / tmpl
        out_file = thumb_dir / f"episode_{ep:02d}.jpg"

        if not tmpl_file.exists():
            print(f"  [ERROR] Template not found: {tmpl_file}")
            continue

        print(f"  • Generating Ep #{ep:02d} thumbnail using {tmpl} -> {out_file.name}...")
        apply_cinematic_grunge_branding(
            image_path=tmpl_file,
            episode_number=ep,
            badge_text=f"#{ep}",
            output_path=out_file,
        )
        print(f"    Done ({out_file.stat().st_size / 1024:.1f} KB)")

    # 2. Upload Custom Thumbnails to YouTube
    print("\n--- STEP 2: Uploading Custom Thumbnails to YouTube ---")
    thumb_success = 0
    for item in EPISODES_TO_REPAIR:
        ep = item["episode"]
        vid = item["video_id"]
        out_file = thumb_dir / f"episode_{ep:02d}.jpg"

        if not out_file.exists():
            print(f"  [WARN] Thumbnail file missing: {out_file}")
            continue

        print(f"  • Uploading Ep #{ep:02d} ({vid}) thumbnail...")
        try:
            media = MediaFileUpload(str(out_file), mimetype="image/jpeg", resumable=False)
            yt.thumbnails().set(videoId=vid, media_body=media).execute()
            print(f"    ✅ Successfully set thumbnail on YouTube for Ep #{ep:02d} ({vid})")
            thumb_success += 1
        except Exception as te:
            print(f"    ❌ Failed to set thumbnail for Ep #{ep:02d} ({vid}): {te}")

    print(f"\nThumbnail Upload Summary: {thumb_success}/{len(EPISODES_TO_REPAIR)} succeeded")

    # 3. Add to Playlist sequentially
    print("\n--- STEP 3: Adding Missing Videos to Series Playlist ---")
    # First get existing playlist items
    existing_items = pm.get_playlist_items(yt, TARGET_PLAYLIST_ID)
    existing_vids = {it["video_id"] for it in existing_items}
    print(f"Target Playlist: {TARGET_PLAYLIST_ID} (currently has {len(existing_vids)} unique videos)")

    added_count = 0
    for item in EPISODES_TO_REPAIR:
        ep = item["episode"]
        vid = item["video_id"]
        title = item["title"]

        if vid in existing_vids:
            print(f"  • Ep #{ep:02d} ({vid}) already in playlist.")
            continue

        print(f"  • Adding Ep #{ep:02d} ({vid}) to playlist: {title[:40]}...")
        # Direct insert without position property to avoid manualSortRequired
        body = {
            "snippet": {
                "playlistId": TARGET_PLAYLIST_ID,
                "resourceId": {
                    "kind": "youtube#video",
                    "videoId": vid,
                },
            }
        }
        try:
            yt.playlistItems().insert(part="snippet", body=body).execute()
            print(f"    ✅ Added Ep #{ep:02d} to playlist")
            added_count += 1
        except Exception as pe:
            print(f"    ❌ Failed to add Ep #{ep:02d} to playlist: {pe}")

    print(f"\nPlaylist Insertion Summary: {added_count} new video(s) added")

    # 4. Verify & Sort Playlist Chronologically
    print("\n--- STEP 4: Verifying Playlist Chronological Ordering ---")
    audit = pm.audit_playlist(yt, TARGET_PLAYLIST_ID)
    print(f"Playlist Audit: {audit['total_items']} items total, is_chronological={audit['is_chronological']}")
    print(f"Episode sequence in playlist: {audit['episode_order']}")

    # 5. Update series_tracker.json
    print("\n--- STEP 5: Updating series_tracker.json ---")
    tracker_path = Path("data/series_tracker.json")
    if tracker_path.exists():
        with open(tracker_path, "r", encoding="utf-8") as f:
            tdata = json.load(f)

        existing_eps = {x["episode"]: x for x in tdata.get("completed_episodes", [])}
        for item in EPISODES_TO_REPAIR:
            ep = item["episode"]
            existing_eps[ep] = {
                "episode": ep,
                "title": item["title"],
                "video_id": item["video_id"],
                "youtube_url": f"https://youtu.be/{item['video_id']}",
                "job_id": item["video_id"],
            }

        sorted_completed = sorted(existing_eps.values(), key=lambda x: x["episode"])
        tdata["completed_episodes"] = sorted_completed
        tdata["current_episode"] = max(existing_eps.keys()) + 1

        with open(tracker_path, "w", encoding="utf-8") as f:
            json.dump(tdata, f, indent=2)

        print(f"  ✅ Updated series_tracker.json (current_episode={tdata['current_episode']}, completed={len(sorted_completed)})")

    print("\n" + "=" * 70)
    print("REPAIR COMPLETE!")
    print("=" * 70)


if __name__ == "__main__":
    run_repair()
