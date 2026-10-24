"""Query YouTube Data API to analyze duration distribution of all uploaded videos."""
import re
import json
from pathlib import Path
from collections import defaultdict
from googleapiclient.discovery import build
from src.google_auth import get_google_credentials

def parse_iso8601_duration(duration_str: str) -> float:
    """Parses ISO 8601 duration string (e.g., PT15M33S, PT1H2M10S) to total minutes."""
    pattern = re.compile(r'P(?:(?P<days>\d+)D)?(?:T(?:(?P<hours>\d+)H)?(?:(?P<minutes>\d+)M)?(?:(?P<seconds>\d+)S)?)?')
    match = pattern.match(duration_str)
    if not match:
        return 0.0
    parts = match.groupdict()
    days = int(parts.get('days') or 0)
    hours = int(parts.get('hours') or 0)
    minutes = int(parts.get('minutes') or 0)
    seconds = int(parts.get('seconds') or 0)
    total_seconds = days * 86400 + hours * 3600 + minutes * 60 + seconds
    return total_seconds / 60.0

def main():
    creds = get_google_credentials(scopes=[
        "https://www.googleapis.com/auth/youtube.force-ssl",
    ])
    if not creds:
        print("Could not obtain YouTube credentials.")
        return

    youtube = build("youtube", "v3", credentials=creds)

    # 1. Fetch all uploaded video IDs from the channel's uploads playlist
    channels_res = youtube.channels().list(part="contentDetails,snippet", mine=True).execute()
    items = channels_res.get("items", [])
    if not items:
        print("No YouTube channel found for current credentials.")
        return

    channel_title = items[0]["snippet"]["title"]
    uploads_playlist_id = items[0]["contentDetails"]["relatedPlaylists"]["uploads"]
    print(f"Channel: {channel_title} (Uploads Playlist: {uploads_playlist_id})")

    video_ids = []
    next_page_token = None
    while True:
        playlist_res = youtube.playlistItems().list(
            part="contentDetails",
            playlistId=uploads_playlist_id,
            maxResults=50,
            pageToken=next_page_token,
        ).execute()
        for item in playlist_res.get("items", []):
            vid = item["contentDetails"]["videoId"]
            video_ids.append(vid)

        next_page_token = playlist_res.get("nextPageToken")
        if not next_page_token:
            break

    print(f"Total uploaded videos found on channel: {len(video_ids)}")

    # 2. Query video contentDetails in batches of 50
    video_details = []
    for i in range(0, len(video_ids), 50):
        batch_ids = video_ids[i:i+50]
        v_res = youtube.videos().list(
            part="contentDetails,snippet",
            id=",".join(batch_ids),
        ).execute()
        for v in v_res.get("items", []):
            duration_iso = v["contentDetails"]["duration"]
            dur_mins = parse_iso8601_duration(duration_iso)
            video_details.append({
                "id": v["id"],
                "title": v["snippet"]["title"],
                "publishedAt": v["snippet"]["publishedAt"],
                "duration_iso": duration_iso,
                "duration_mins": dur_mins,
            })

    # 3. Categorize into duration buckets
    buckets = {
        "< 10 min": [],
        "10 - 20 min": [],
        "20 - 30 min": [],
        "30 - 40 min": [],
        "40 - 50 min": [],
        "50 - 60 min": [],
        "> 60 min (1h+)": [],
    }

    for v in video_details:
        m = v["duration_mins"]
        if m < 10.0:
            buckets["< 10 min"].append(v)
        elif 10.0 <= m < 20.0:
            buckets["10 - 20 min"].append(v)
        elif 20.0 <= m < 30.0:
            buckets["20 - 30 min"].append(v)
        elif 30.0 <= m < 40.0:
            buckets["30 - 40 min"].append(v)
        elif 40.0 <= m < 50.0:
            buckets["40 - 50 min"].append(v)
        elif 50.0 <= m < 60.0:
            buckets["50 - 60 min"].append(v)
        else:
            buckets["> 60 min (1h+)"].append(v)

    # Output formatted report
    print("\n" + "=" * 60)
    print("YOUTUBE VIDEO DURATION DISTRIBUTION SUMMARY")
    print("=" * 60)
    for b_name, b_vids in buckets.items():
        print(f"  {b_name:<18}: {len(b_vids):>3} video(s)")
    print("=" * 60)
    print(f"Total Videos Analyzed: {len(video_details)}")
    print("=" * 60)

    # Save detailed JSON for review
    out_path = Path("temp_duration_analysis.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({
            "channel_title": channel_title,
            "total_videos": len(video_details),
            "summary": {k: len(v) for k, v in buckets.items()},
            "details_by_bucket": buckets,
        }, f, indent=2)
    print(f"Detailed output saved to {out_path.name}")

if __name__ == "__main__":
    main()
