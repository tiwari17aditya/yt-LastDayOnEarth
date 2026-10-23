import io
import sys
import json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from googleapiclient.discovery import build
from src.google_auth import get_google_credentials

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

def main():
    creds = get_google_credentials()
    if not creds:
        print("ERROR: Could not get credentials")
        return

    yt = build("youtube", "v3", credentials=creds)

    # 1. Get channel info and uploads playlist
    ch = yt.channels().list(mine=True, part="contentDetails,snippet").execute()
    channel_title = ch["items"][0]["snippet"]["title"]
    uploads_id = ch["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]
    print(f"Channel: {channel_title} (Uploads playlist: {uploads_id})")

    # 2. Get all uploaded videos
    uploads = []
    req = yt.playlistItems().list(playlistId=uploads_id, part="snippet,contentDetails", maxResults=50)
    while req:
        res = req.execute()
        for it in res.get("items", []):
            snip = it["snippet"]
            uploads.append({
                "video_id": snip["resourceId"]["videoId"],
                "title": snip["title"],
                "published_at": snip["publishedAt"],
                "thumbnails": snip.get("thumbnails", {})
            })
        req = yt.playlistItems().list_next(req, res)

    print(f"\nTotal uploaded videos on channel: {len(uploads)}")

    # 3. Check playlists on channel
    p_req = yt.playlists().list(part="snippet,contentDetails", mine=True, maxResults=50)
    playlists = []
    while p_req:
        p_res = p_req.execute()
        for p in p_res.get("items", []):
            playlists.append({
                "id": p["id"],
                "title": p["snippet"]["title"],
                "item_count": p["contentDetails"]["itemCount"]
            })
        p_req = yt.playlists().list_next(p_req, p_res)

    print(f"\nFound {len(playlists)} playlists on channel:")
    for pl in playlists:
        print(f"  • [{pl['id']}] {pl['title']} ({pl['item_count']} items)")

    # 4. Check series playlist PLJPzVNVZwaGY
    target_playlist_id = "PLJPzVNVZwaGY"
    pl_items = []
    req = yt.playlistItems().list(playlistId=target_playlist_id, part="snippet,contentDetails", maxResults=50)
    while req:
        res = req.execute()
        for it in res.get("items", []):
            snip = it["snippet"]
            pl_items.append({
                "video_id": snip["resourceId"]["videoId"],
                "title": snip["title"],
                "position": snip["position"]
            })
        req = yt.playlistItems().list_next(req, res)

    pl_vids = {it["video_id"]: it for it in pl_items}
    print(f"\nTotal videos in target playlist ({target_playlist_id}): {len(pl_vids)}")

    missing_from_pl = [u for u in uploads if u["video_id"] not in pl_vids]
    print(f"Uploads NOT in target playlist: {len(missing_from_pl)}")
    for m in missing_from_pl:
        print(f"  - Missing: {m['video_id']} | {m['title']}")

    # 5. Detail report of LDoE videos
    ldoe_videos = [
        u for u in uploads
        if "last day on earth" in u["title"].lower() or "ldoe" in u["title"].lower()
    ]
    print("\n" + "="*80)
    print(f"LDoE SERIES VIDEOS ({len(ldoe_videos)} found on channel):")
    print("="*80)
    for i, u in enumerate(ldoe_videos, 1):
        vid = u["video_id"]
        in_pl = vid in pl_vids
        pos = pl_vids[vid]["position"] if in_pl else "N/A"
        thumbs = u["thumbnails"]
        # Print thumbnail details
        thumb_types = list(thumbs.keys())
        default_thumb_url = thumbs.get("default", {}).get("url", "")
        maxres_url = thumbs.get("maxres", {}).get("url", "")
        print(f"{i:02d}. [{vid}] in_pl={in_pl} (pos={pos}) | thumbs={thumb_types} | {u['title']}")
        if maxres_url:
            print(f"     Maxres URL: {maxres_url}")
        else:
            print(f"     Default URL: {default_thumb_url}")

if __name__ == "__main__":
    main()
