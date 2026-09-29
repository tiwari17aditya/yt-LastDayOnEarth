"""Update YouTube thumbnails for existing videos to the new cinematic grunge style."""

import io
import sys
from pathlib import Path
from typing import Dict, Optional

# Force UTF-8 stdout
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, str(Path(__file__).parent.parent))

from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from src.google_auth import get_google_credentials
from src.logging_config import get_logger

logger = get_logger(component="ThumbnailUpdater")

# Mapping of video IDs to thumbnail files
VIDEO_THUMBNAIL_MAP = [
    {"video_id": "Aw80nniGs-E", "episode": 1, "title": "HOME BASE EXPANSION & RESOURCE ORGANIZATION! | LDoE Survival #1"},
    {"video_id": "3hWeXZ0EViQ", "episode": 2, "title": "SURVIVAL ROUTINE & WORKSHOP OPERATIONS! | LDoE Survival #2"},
    {"video_id": "sH0NspDux9k", "episode": 3, "title": "BASE DEFENSE SETUP & WORKSHOP SMELTING! | LDoE Survival #3"},
    {"video_id": "MZ6slquprUU", "episode": 4, "title": "SURVIVAL ROUTINE: WORKSHOP & STORAGE! | LDoE Survival #4"},
    {"video_id": "L-Gpmo89uHk", "episode": 5, "title": "OPTIMIZING BASE STORAGE & WOODCRAFT PLANKS! | LDoE Survival #5"},
    {"video_id": "Kqctm5n01h4", "episode": 6, "title": "BASE DEFENSE PREP & SMELTING FURNACES! | LDoE Survival #6"},
    {"video_id": "JMa211Yc4YU", "episode": 7, "title": "Workshop & Smelting + Blueprint Upgrades! | LDoE Survival #7"},
    {"video_id": "Wf50vxO0NHs", "episode": 8, "title": "Home Base Operations & Zombie Horde Defense! | LDoE Survival #8"},
    {"video_id": "74QftMT7nDU", "episode": 8, "title": "Home Base Operations & Blueprint Upgrades! | LDoE Survival #8"},
    {"video_id": "VP7g6-VqNY4", "episode": 9, "title": "Base Storage Optimization + Inventory & Resource Sorting! | LDoE Survival #9"},
    {"video_id": "eYny9FafrjI", "episode": 10, "title": "Workshop & Smelting + Entering Home Base! | LDoE Survival #10"},
    {"video_id": "E_6ayR0DyHs", "episode": 11, "title": "Blueprint Upgrades + Woodcraft & Planks! | LDoE Survival #11"},
]


def update_thumbnail(youtube, video_id: str, thumbnail_path: Path) -> bool:
    """Uploads custom thumbnail for the given YouTube video ID."""
    if not thumbnail_path.exists():
        logger.error(f"Thumbnail not found: {thumbnail_path}")
        return False

    try:
        logger.info(f"Setting custom thumbnail for video {video_id} using {thumbnail_path.name}")
        media = MediaFileUpload(
            str(thumbnail_path),
            mimetype="image/jpeg",
            resumable=False,
        )
        response = youtube.thumbnails().set(
            videoId=video_id,
            media_body=media,
        ).execute()
        logger.info(f"Successfully updated thumbnail for {video_id}: {response}")
        return True
    except Exception as e:
        logger.error(f"Failed to update thumbnail for {video_id}: {e}")
        return False


def main():
    creds = get_google_credentials(
        scopes=[
            "https://www.googleapis.com/auth/youtube.upload",
            "https://www.googleapis.com/auth/youtube.force-ssl",
        ]
    )
    if not creds:
        logger.error("Could not obtain YouTube credentials.")
        sys.exit(1)

    youtube = build("youtube", "v3", credentials=creds)
    thumb_dir = Path("data/thumbnails")

    success_count = 0
    total = len(VIDEO_THUMBNAIL_MAP)

    for item in VIDEO_THUMBNAIL_MAP:
        vid = item["video_id"]
        ep = item["episode"]
        title = item["title"]
        thumb_file = thumb_dir / f"episode_{ep:02d}.jpg"

        print(f"\nProcessing Episode #{ep:02d} ({vid}): {title}")
        if update_thumbnail(youtube, vid, thumb_file):
            success_count += 1
            print(f"  [SUCCESS] Updated thumbnail for {vid} (Episode #{ep})")
        else:
            print(f"  [FAILED] Could not update thumbnail for {vid}")

    print(f"\nCompleted! {success_count}/{total} thumbnails updated successfully on YouTube.")


if __name__ == "__main__":
    main()
