#!/usr/bin/env python3
"""Clean YouTube video descriptions: strip Music Attribution & Copyright Disclaimers across all series episodes."""

import io
import json
import re
import sys
import time
from pathlib import Path

# Force UTF-8 stdout
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from googleapiclient.discovery import build
from src.google_auth import get_google_credentials
from src.logging_config import get_logger

logger = get_logger(component="CleanDescriptions")

ATTRIBUTION_PATTERN = re.compile(
    r"(?:\n?─{10,}\s*)?"
    r"🎵 MUSIC & LICENSING ATTRIBUTION:.*?"
    r"⚖️ COPYRIGHT & FAIR USE DISCLAIMER:.*?"
    r"protected under Fair Use \(Section 107 of the US Copyright Act 1976\)\.\s*"
    r"(?:─{10,}\s*)?",
    re.DOTALL,
)


def clean_description_text(desc: str) -> str:
    """Removes music attribution and copyright fair use disclaimer blocks."""
    # First apply primary regex pattern
    cleaned = ATTRIBUTION_PATTERN.sub("\n\n", desc)

    # In case of partial or non-standard formatting, apply fallback cleans:
    if "MUSIC & LICENSING ATTRIBUTION:" in cleaned:
        cleaned = re.sub(
            r"(?:\n?─{10,}\s*)?🎵 MUSIC & LICENSING ATTRIBUTION:.*?(?:https://creativecommons\.org/[^\s]+)\s*",
            "\n\n",
            cleaned,
            flags=re.DOTALL,
        )
    if "COPYRIGHT & FAIR USE DISCLAIMER:" in cleaned:
        cleaned = re.sub(
            r"(?:\n?─{10,}\s*)?⚖️ COPYRIGHT & FAIR USE DISCLAIMER:.*?(?:1976\)\.\s*)",
            "\n\n",
            cleaned,
            flags=re.DOTALL,
        )

    # Clean up excess consecutive dividers and multiple blank lines
    cleaned = re.sub(r"(─{10,}\s*){2,}", "────────────────────────────────────────\n\n", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


def run_cleanup():
    print("=" * 70)
    print("YOUTUBE VIDEO DESCRIPTION CLEANUP (Episodes #1 to #45)")
    print("=" * 70)

    creds = get_google_credentials()
    if not creds:
        print("[ERROR] Could not obtain valid YouTube credentials.")
        sys.exit(1)

    yt = build("youtube", "v3", credentials=creds)

    tracker_file = Path("data/series_tracker.json")
    if not tracker_file.exists():
        print(f"[ERROR] Tracker file not found: {tracker_file}")
        sys.exit(1)

    with open(tracker_file, "r", encoding="utf-8") as f:
        tracker_data = json.load(f)

    episodes = tracker_data.get("completed_episodes", [])
    print(f"Total tracked episodes in series: {len(episodes)}")

    video_ids = [ep["video_id"] for ep in episodes if "video_id" in ep]

    # Fetch YouTube snippet details in batches of 50
    all_videos = {}
    for i in range(0, len(video_ids), 50):
        chunk = video_ids[i : i + 50]
        res = yt.videos().list(part="snippet", id=",".join(chunk)).execute()
        for it in res.get("items", []):
            all_videos[it["id"]] = it

    print(f"Successfully fetched details for {len(all_videos)} live videos.\n")

    updated_count = 0
    already_clean_count = 0
    failed_count = 0

    for ep in episodes:
        ep_num = ep.get("episode")
        vid = ep.get("video_id")
        title = ep.get("title", "")

        if vid not in all_videos:
            print(f"⚠️  Ep #{ep_num:02d} ({vid}): Not found on YouTube channel.")
            continue

        item = all_videos[vid]
        snippet = item["snippet"]
        curr_desc = snippet.get("description", "")

        # Check if description has attribution content
        if "MUSIC & LICENSING" not in curr_desc and "FAIR USE DISCLAIMER" not in curr_desc:
            print(f"• Ep #{ep_num:02d} ({vid}): Already clean (no attribution text)")
            already_clean_count += 1
            continue

        new_desc = clean_description_text(curr_desc)

        print(f"• Ep #{ep_num:02d} ({vid}): Cleaning description ({title[:40]}...)...")

        update_body = {
            "id": vid,
            "snippet": {
                "title": snippet["title"],
                "categoryId": snippet.get("categoryId", "20"),
                "description": new_desc,
                "tags": snippet.get("tags", []),
                "defaultLanguage": snippet.get("defaultLanguage", "en"),
                "defaultAudioLanguage": snippet.get("defaultAudioLanguage", "en"),
            },
        }

        try:
            yt.videos().update(part="snippet", body=update_body).execute()
            print(f"  ✅ Successfully updated description on YouTube (now {len(new_desc)} chars)")
            updated_count += 1
            time.sleep(0.3)  # Rate limit prevention
        except Exception as e:
            print(f"  ❌ Failed to update Ep #{ep_num:02d} ({vid}): {e}")
            failed_count += 1

    print("\n" + "=" * 70)
    print("CLEANUP SUMMARY:")
    print(f"  • Successfully Updated: {updated_count}")
    print(f"  • Already Clean:       {already_clean_count}")
    print(f"  • Failed:              {failed_count}")
    print(f"  • Total Processed:     {len(episodes)}")
    print("=" * 70)


if __name__ == "__main__":
    run_cleanup()
