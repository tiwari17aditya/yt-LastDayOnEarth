"""Utility to audit, resolve, and prevent YouTube Content ID copyright claims and regional restrictions across channel videos."""

import argparse
import io
import json
import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

# Force UTF-8 output on Windows consoles
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, str(Path(__file__).parent.parent))

from googleapiclient.discovery import build
from src.google_auth import get_google_credentials
from src.logging_config import get_logger

logger = get_logger(component="CopyrightResolver")

LICENSING_ATTRIBUTION_TEMPLATE = """────────────────────────────────────────
🎵 MUSIC & AUDIO LICENSING ATTRIBUTION:
All background music in this video is royalty-free and licensed under Creative Commons Attribution 4.0 International (CC BY 4.0):
• Music by Kevin MacLeod (incompetech.com)
{tracks_line}  Licensed under Creative Commons: By Attribution 4.0 License
  https://creativecommons.org/licenses/by/4.0/

⚖️ COPYRIGHT & FAIR USE DISCLAIMER:
Last Day on Earth: Survival is developed and published by Kefir Games.
All gameplay footage, visual assets, and in-game audio belong to Kefir Games.
This video is transformative gameplay walkthrough and commentary created for entertainment and instructional purposes protected under Fair Use (Section 107 of the US Copyright Act 1976).
────────────────────────────────────────"""


def load_history_tracks() -> Dict[str, List[str]]:
    """Builds a mapping of video_id -> list of track titles from data/history.json."""
    mapping: Dict[str, List[str]] = {}
    history_file = Path("data/history.json")
    if not history_file.exists():
        return mapping

    try:
        with open(history_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            if not isinstance(data, list):
                return mapping

            for entry in data:
                vid = entry.get("video_id")
                if not vid:
                    continue
                # Check metadata file if present
                meta_path = entry.get("details", {}).get("metadata_output")
                if meta_path and Path(meta_path).exists():
                    try:
                        with open(meta_path, "r", encoding="utf-8") as mf:
                            mdata = json.load(mf)
                            tracks = mdata.get("music_track") or []
                            if isinstance(tracks, list):
                                titles = [
                                    t.get("title") if isinstance(t, dict) else str(t)
                                    for t in tracks
                                ]
                                mapping[vid] = [t for t in titles if t]
                    except Exception:
                        pass
    except Exception as e:
        logger.warning(f"Could not load tracks from history.json: {e}")

    return mapping


def get_youtube_service():
    """Initializes YouTube API client with authorized scopes."""
    creds = get_google_credentials(
        scopes=[
            "https://www.googleapis.com/auth/youtube.upload",
            "https://www.googleapis.com/auth/youtube.force-ssl",
        ]
    )
    if not creds:
        raise RuntimeError("Failed to obtain authorized Google/YouTube credentials.")
    return build("youtube", "v3", credentials=creds)


def audit_channel_videos(
    youtube, limit: Optional[int] = None
) -> List[Dict]:
    """Fetches uploaded videos on the channel and audits their restriction and licensing status."""
    logger.info("Auditing channel videos for copyright claims and regional restrictions...")
    
    # 1. Get channel uploads playlist ID
    channels_res = youtube.channels().list(mine=True, part="contentDetails").execute()
    uploads_playlist_id = (
        channels_res["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]
    )

    # 2. Page through playlist items
    video_ids = []
    next_page_token = None
    while True:
        playlist_res = (
            youtube.playlistItems()
            .list(
                playlistId=uploads_playlist_id,
                part="contentDetails",
                maxResults=50,
                pageToken=next_page_token,
            )
            .execute()
        )
        for item in playlist_res.get("items", []):
            video_ids.append(item["contentDetails"]["videoId"])
            if limit and len(video_ids) >= limit:
                break

        if limit and len(video_ids) >= limit:
            break
        next_page_token = playlist_res.get("nextPageToken")
        if not next_page_token:
            break

    logger.info(f"Retrieved {len(video_ids)} total video IDs. Fetching video details...")

    # 3. Retrieve video details in batches of 50
    audit_results = []
    for i in range(0, len(video_ids), 50):
        chunk = video_ids[i : i + 50]
        v_res = (
            youtube.videos()
            .list(id=",".join(chunk), part="snippet,contentDetails,status")
            .execute()
        )
        for v in v_res.get("items", []):
            vid = v["id"]
            snippet = v.get("snippet", {})
            content_details = v.get("contentDetails", {})
            status = v.get("status", {})

            title = snippet.get("title", "")
            description = snippet.get("description", "")
            region_restriction = content_details.get("regionRestriction", {})
            has_licensing = "MUSIC & AUDIO LICENSING ATTRIBUTION" in description
            privacy_status = status.get("privacyStatus", "unknown")

            # Extract episode number if present
            ep_match = re.search(r"#(\d+)", title)
            episode_num = int(ep_match.group(1)) if ep_match else None

            audit_results.append({
                "video_id": vid,
                "title": title,
                "episode": episode_num,
                "has_licensing": has_licensing,
                "region_restriction": region_restriction,
                "privacy_status": privacy_status,
                "snippet": snippet,
            })

    return audit_results


def inject_licensing_to_video(
    youtube,
    video_info: Dict,
    known_tracks: Optional[List[str]] = None,
) -> bool:
    """Injects CC-BY 4.0 and Kefir Fair Use block into video description."""
    vid = video_info["video_id"]
    snippet = video_info.get("snippet")
    if not snippet:
        res = youtube.videos().list(id=vid, part="snippet").execute()
        items = res.get("items", [])
        if not items:
            logger.error(f"Video {vid} not found on YouTube.")
            return False
        snippet = items[0]["snippet"]

    current_desc = snippet.get("description", "")
    if "MUSIC & AUDIO LICENSING ATTRIBUTION" in current_desc:
        logger.info(f"Video {vid} ({snippet.get('title')}) already has licensing block.")
        return True

    tracks_line = ""
    if known_tracks:
        tracks_line = f"  Tracks Featured: {', '.join(known_tracks)}\n"

    block = LICENSING_ATTRIBUTION_TEMPLATE.format(tracks_line=tracks_line)

    # Insert before trailing hashtags if possible
    if "────────────────────────────────────────\n\n#" in current_desc:
        parts = current_desc.split("────────────────────────────────────────\n\n#")
        new_desc = parts[0] + block + "\n\n#" + parts[1]
    elif "────────────────────────────────────────" in current_desc:
        parts = current_desc.rsplit("────────────────────────────────────────", 1)
        new_desc = parts[0] + block + "\n" + parts[1]
    else:
        new_desc = current_desc + "\n\n" + block

    snippet["description"] = new_desc

    try:
        youtube.videos().update(
            part="snippet",
            body={"id": vid, "snippet": snippet},
        ).execute()
        logger.info(f"[SUCCESS] Injected licensing block into {vid}: {snippet.get('title')}")
        return True
    except Exception as e:
        logger.error(f"Failed to update description for {vid}: {e}")
        return False


def print_dispute_instructions(video_id: str, title: str):
    """Outputs dispute copy and guide for YouTube Studio."""
    print("\n" + "=" * 70)
    print(f"YOUTUBE STUDIO DISPUTE COPY FOR VIDEO: {video_id}")
    print(f"Title: {title}")
    print("=" * 70)
    print("How to lift Content ID claims and regional blocks in 60 seconds:")
    print("1. Open YouTube Studio: https://studio.youtube.com/channel/UCt154eXNnEfKtRNBrAnay7A/videos")
    print(f"2. Filter for Video ID '{video_id}' or find the video in the list.")
    print("3. In the 'Restrictions' column, hover over the restriction ('Claim' or 'Blocked in 2 territories') and click 'SEE DETAILS'.")
    print("4. Click 'SELECT ACTION' -> 'Dispute'.")
    print("5. Choose dispute reason: Select 'License' ('I have permission or a license to use this content').")
    print("6. Check the box confirming you have a valid license and click Continue.")
    print("7. Copy and paste the following official legal statement into the explanation box:")
    print("-" * 70)
    dispute_statement = (
        "The background music used in this video is composed by Kevin MacLeod (incompetech.com) "
        "and is licensed under Creative Commons Attribution 4.0 International (CC BY 4.0). "
        "Full attribution is present in the video description in compliance with license terms: "
        "https://creativecommons.org/licenses/by/4.0/\n\n"
        "Gameplay footage and assets are from 'Last Day on Earth: Survival' by Kefir Games, used under "
        "transformative Fair Use (17 U.S.C. § 107) for gameplay guide, walk-through, and entertainment purposes.\n\n"
        "Please release this automated Content ID territorial block immediately."
    )
    print(dispute_statement)
    print("-" * 70)
    print("8. Check all 3 verification boxes, sign with your full name, and submit.")
    print("Content ID blocks on Creative Commons music are routinely released within 24-48 hours without strike.")
    print("=" * 70 + "\n")


def main():
    parser = argparse.ArgumentParser(
        description="YouTube Copyright and Content ID Audit & Resolution CLI"
    )
    parser.add_argument(
        "--audit", action="store_true", help="Audit channel videos for restrictions and missing attribution."
    )
    parser.add_argument(
        "--fix", action="store_true", help="Automatically inject CC-BY 4.0 attribution into descriptions."
    )
    parser.add_argument(
        "--since-episode", type=int, default=None, help="Process only episodes >= this number."
    )
    parser.add_argument(
        "--video-id", type=str, default=None, help="Target a specific YouTube video ID."
    )
    parser.add_argument(
        "--limit", type=int, default=None, help="Limit number of videos to audit/fix."
    )
    parser.add_argument(
        "--dispute-info", type=str, default=None, help="Print YouTube Studio dispute copy for a video ID."
    )

    args = parser.parse_args()

    if args.dispute_info:
        print_dispute_instructions(args.dispute_info, "Manual Query")
        return

    youtube = get_youtube_service()
    track_map = load_history_tracks()

    if args.video_id:
        res = youtube.videos().list(id=args.video_id, part="snippet,contentDetails,status").execute()
        items = res.get("items", [])
        if not items:
            logger.error(f"Video {args.video_id} not found.")
            return
        item = items[0]
        v_info = {
            "video_id": args.video_id,
            "title": item["snippet"]["title"],
            "snippet": item["snippet"],
            "region_restriction": item["contentDetails"].get("regionRestriction", {}),
        }
        if args.fix:
            tracks = track_map.get(args.video_id)
            inject_licensing_to_video(youtube, v_info, known_tracks=tracks)
        else:
            print(f"Video ID: {v_info['video_id']}")
            print(f"Title: {v_info['title']}")
            print(f"Restrictions: {v_info['region_restriction']}")
            print(f"Has Licensing: {'MUSIC & AUDIO LICENSING ATTRIBUTION' in item['snippet']['description']}")
            if v_info["region_restriction"]:
                print_dispute_instructions(args.video_id, v_info["title"])
        return

    # Channel-wide audit/fix
    results = audit_channel_videos(youtube, limit=args.limit)

    filtered = []
    for r in results:
        if args.since_episode is not None:
            if r["episode"] is None or r["episode"] < args.since_episode:
                continue
        filtered.append(r)

    print("\n" + "=" * 70)
    print(f"AUDIT SUMMARY: {len(filtered)} videos analyzed (Total channel videos: {len(results)})")
    print("=" * 70)

    restricted_videos = [r for r in filtered if r["region_restriction"]]
    missing_licensing = [r for r in filtered if not r["has_licensing"]]

    print(f"Videos with Region Restrictions: {len(restricted_videos)}")
    for rv in restricted_videos:
        print(f"  • [{rv['video_id']}] {rv['title']} -> {rv['region_restriction']}")

    print(f"Videos missing Licensing Attribution: {len(missing_licensing)}")

    if args.fix:
        print("\nApplying licensing fixes to videos...")
        fixed_count = 0
        for r in filtered:
            if not r["has_licensing"]:
                tracks = track_map.get(r["video_id"])
                success = inject_licensing_to_video(youtube, r, known_tracks=tracks)
                if success:
                    fixed_count += 1
        print(f"\n[DONE] Updated {fixed_count} video descriptions with mandatory licensing attribution.")

    if restricted_videos:
        print("\n" + "#" * 70)
        print("ACTION REQUIRED FOR RESTRICTED VIDEOS:")
        print("#" * 70)
        for rv in restricted_videos:
            print_dispute_instructions(rv["video_id"], rv["title"])


if __name__ == "__main__":
    main()
