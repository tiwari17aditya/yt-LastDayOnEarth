#!/usr/bin/env python3
"""Synchronize, brand, and repair YouTube thumbnails and playlist for all episodes."""

import io
import json
import re
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

logger = get_logger(component="PostSep29Sync")

EPISODE_TEMPLATE_MAP = {
    14: "workshop_template.jpg",
    15: "base_template.jpg",
    16: "workshop_template.jpg",
    17: "base_template.jpg",
    18: "storage_template.jpg",
    19: "workshop_template.jpg",
    20: "chopper_template.jpg",
    21: "defense_template.jpg",
    22: "defense_template.jpg",
    23: "storage_template.jpg",
    24: "bunker_template.jpg",
    25: "workshop_template.jpg",
    26: "workshop_template.jpg",
    27: "storage_template.jpg",
    28: "base_template.jpg",
    29: "base_template.jpg",
    30: "base_template.jpg",
    31: "workshop_template.jpg",
    32: "storage_template.jpg",
    33: "workshop_template.jpg",
}


def get_all_channel_ldoe_videos(youtube) -> list:
    """Retrieves all LDoE gameplay series videos on the channel."""
    ch = youtube.channels().list(mine=True, part="contentDetails").execute()
    uploads_id = ch["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]

    req = youtube.playlistItems().list(playlistId=uploads_id, part="snippet,contentDetails", maxResults=50)
    items = []
    while req:
        res = req.execute()
        for it in res.get("items", []):
            snip = it["snippet"]
            vid = snip["resourceId"]["videoId"]
            title = snip["title"]
            match = re.search(r"#(\d+)", title)
            if match and ("LDoE" in title or "Last Day on Earth" in title):
                ep_num = int(match.group(1))
                items.append({
                    "episode": ep_num,
                    "video_id": vid,
                    "title": title,
                    "published_at": snip["publishedAt"],
                })
        req = youtube.playlistItems().list_next(req, res)

    # Sort ascending by episode
    items.sort(key=lambda x: x["episode"])
    return items


def main():
    print("=" * 70)
    print("Starting Comprehensive Post-Sep 29 Video Debug & Repair Routine")
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

    youtube = build("youtube", "v3", credentials=creds)
    pm = PlaylistManager()
    template_dir = Path("data/thumbnails/templates")
    thumb_dir = Path("data/thumbnails")
    thumb_dir.mkdir(parents=True, exist_ok=True)

    videos = get_all_channel_ldoe_videos(youtube)
    print(f"Discovered {len(videos)} LDoE episodes on channel (Episodes #{videos[0]['episode']} to #{videos[-1]['episode']}).\n")

    # Step 1: Generate missing cinematic thumbnails in data/thumbnails
    print("Step 1: Generating cinematic grunge thumbnails for episodes >= 14...")
    for ep, tmpl_name in EPISODE_TEMPLATE_MAP.items():
        thumb_path = thumb_dir / f"episode_{ep:02d}.jpg"
        if not thumb_path.exists():
            tmpl_path = template_dir / tmpl_name
            if tmpl_path.exists():
                print(f"  • Generating {thumb_path.name} from {tmpl_name}...")
                apply_cinematic_grunge_branding(
                    image_path=tmpl_path,
                    episode_number=ep,
                    badge_text=f"#{ep}",
                    output_path=thumb_path,
                )
            else:
                print(f"  [WARN] Template {tmpl_path} not found for ep {ep}")
        else:
            print(f"  • {thumb_path.name} already exists.")

    # Step 2: Upload custom thumbnails to YouTube for all episodes >= 13
    print("\nStep 2: Uploading custom thumbnails to YouTube for episodes >= 13...")
    for v in videos:
        ep = v["episode"]
        if ep < 13:
            continue
        vid = v["video_id"]
        thumb_file = thumb_dir / f"episode_{ep:02d}.jpg"
        if not thumb_file.exists():
            print(f"  [WARN] No thumbnail file for Ep #{ep} ({thumb_file})")
            continue

        print(f"  • Uploading thumbnail for Ep #{ep} ({vid}): {v['title'][:45]}...")
        try:
            media = MediaFileUpload(str(thumb_file), mimetype="image/jpeg", resumable=False)
            youtube.thumbnails().set(videoId=vid, media_body=media).execute()
            print(f"    ✅ Successfully updated thumbnail for Ep #{ep}")
        except Exception as te:
            print(f"    ❌ Failed to update thumbnail for Ep #{ep}: {te}")

    # Step 3: Ensure dedicated playlist exists and populate all missing videos
    print("\nStep 3: Ensuring YouTube series playlist includes all episodes 1 to 29...")
    # Find dedicated playlist
    p_req = youtube.playlists().list(part="snippet,status", mine=True, maxResults=50)
    playlist_id = None
    while p_req:
        p_res = p_req.execute()
        for p in p_res.get("items", []):
            if "Last Day on Earth" in p["snippet"]["title"] and "Series" in p["snippet"]["title"]:
                playlist_id = p["id"]
                break
        if playlist_id:
            break
        p_req = youtube.playlists().list_next(p_req, p_res)

    if not playlist_id:
        print("[ERROR] Could not locate series playlist.")
        sys.exit(1)

    print(f"  Target Playlist ID: {playlist_id}")
    for v in videos:
        ep = v["episode"]
        vid = v["video_id"]
        # Use our enhanced add_video_sequentially
        added = pm.add_video_sequentially(
            youtube=youtube,
            video_id=vid,
            playlist_id=playlist_id,
            episode_number=ep,
        )
        status_msg = "✅ Added / Already Present" if added else "❌ Failed"
        print(f"  Ep #{ep:02d} ({vid}): {status_msg}")

    # Step 4: Reorder / Sort Playlist into strict ascending chronological order
    print("\nStep 4: Sorting playlist chronologically (Episode 1 to N)...")
    try:
        pm.sort_playlist_chronological(youtube, playlist_id)
        print("  ✅ Playlist sorting complete.")
    except Exception as se:
        print(f"  [WARN] Sorting notice: {se}")

    # Step 5: Audit Playlist
    print("\nStep 5: Verifying Playlist audit...")
    audit = pm.audit_playlist(youtube, playlist_id)
    print(f"  Total playlist items: {audit['total_items']}")
    print(f"  Unique videos: {audit['unique_videos']}")
    print(f"  Sequence: {audit['episode_order']}")

    # Step 6: Sync data/series_tracker.json
    print("\nStep 6: Syncing series_tracker.json...")
    tracker_path = Path("data/series_tracker.json")
    completed = []
    for v in videos:
        completed.append({
            "episode": v["episode"],
            "title": v["title"],
            "video_id": v["video_id"],
            "youtube_url": f"https://youtu.be/{v['video_id']}",
            "job_id": v["video_id"],
        })

    tracker_data = {
        "series_name": "Last Day on Earth: Survival",
        "current_episode": videos[-1]["episode"] + 1,
        "completed_episodes": completed,
    }
    with open(tracker_path, "w", encoding="utf-8") as f:
        json.dump(tracker_data, f, indent=2)
    print(f"  ✅ series_tracker.json updated! Current episode set to #{videos[-1]['episode'] + 1}")

    print("\n🎉 Repair and synchronization completed successfully!")


if __name__ == "__main__":
    main()
