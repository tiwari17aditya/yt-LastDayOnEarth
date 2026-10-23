import io
import json
import re
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from googleapiclient.discovery import build
from src.google_auth import get_google_credentials
from src.logging_config import get_logger
from src.publisher.playlist_manager import PlaylistManager

logger = get_logger(component="PlaylistSync")

def sync_ldoe_playlist():
    creds = get_google_credentials()
    if not creds:
        print("[ERROR] Could not obtain valid YouTube credentials.")
        return False

    youtube = build("youtube", "v3", credentials=creds)
    pm = PlaylistManager()

    # 1. Locate Playlist
    p_req = youtube.playlists().list(part="snippet", mine=True, maxResults=50)
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
        return False

    print(f"Target Playlist ID: {playlist_id}")

    # 2. Get existing playlist items
    existing_items = pm.get_playlist_items(youtube, playlist_id)
    existing_vids = {it["video_id"] for it in existing_items}
    print(f"Currently in playlist: {len(existing_vids)} unique videos")

    # 3. Get all channel LDoE uploads
    ch = youtube.channels().list(mine=True, part="contentDetails").execute()
    uploads_id = ch["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]

    channel_videos = []
    req = youtube.playlistItems().list(playlistId=uploads_id, part="snippet", maxResults=50)
    while req:
        res = req.execute()
        for it in res.get("items", []):
            snip = it["snippet"]
            title = snip["title"]
            vid = snip["resourceId"]["videoId"]
            if "last day on earth" in title.lower() or "ldoe" in title.lower():
                m = re.search(r"#(\d+)", title)
                ep = int(m.group(1)) if m else -1
                channel_videos.append({
                    "episode": ep,
                    "video_id": vid,
                    "title": title,
                    "published_at": snip["publishedAt"],
                })
        req = youtube.playlistItems().list_next(req, res)

    # Sort ascending by episode and published date
    channel_videos.sort(key=lambda x: (x["episode"], x["published_at"]))
    print(f"Total LDoE videos on channel: {len(channel_videos)}")

    missing = [v for v in channel_videos if v["video_id"] not in existing_vids]
    print(f"Missing videos to add to playlist: {len(missing)}")

    added_count = 0
    for v in missing:
        ep = v["episode"]
        vid = v["video_id"]
        title = v["title"]
        print(f"  Adding Ep #{ep:02d} ({vid}): {title[:40]}...")
        # Direct insert without position property to avoid manualSortRequired
        body = {
            "snippet": {
                "playlistId": playlist_id,
                "resourceId": {
                    "kind": "youtube#video",
                    "videoId": vid,
                },
            }
        }
        try:
            youtube.playlistItems().insert(part="snippet", body=body).execute()
            print(f"    ✅ Successfully added Ep #{ep}")
            added_count += 1
        except Exception as e:
            print(f"    ❌ Failed adding Ep #{ep}: {e}")

    print(f"\nAdded {added_count}/{len(missing)} missing videos to playlist.")

    # 4. Audit final playlist
    final_items = pm.get_playlist_items(youtube, playlist_id)
    print(f"Final playlist count: {len(final_items)} videos.")

    # 5. Update series_tracker.json
    tracker_path = Path("data/series_tracker.json")
    completed = []
    for v in channel_videos:
        completed.append({
            "episode": v["episode"],
            "title": v["title"],
            "video_id": v["video_id"],
            "youtube_url": f"https://youtu.be/{v['video_id']}",
            "job_id": v["video_id"],
        })

    tracker_data = {
        "series_name": "Last Day on Earth: Survival",
        "current_episode": channel_videos[-1]["episode"] + 1,
        "completed_episodes": completed,
    }
    with open(tracker_path, "w", encoding="utf-8") as f:
        json.dump(tracker_data, f, indent=2)
    print(f"series_tracker.json updated! Current episode set to #{channel_videos[-1]['episode'] + 1}")

    return True

if __name__ == "__main__":
    sync_ldoe_playlist()
