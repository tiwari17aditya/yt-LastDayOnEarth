"""Advanced YouTube playlist management, chronological sorting, and deduplication.

Ensures series playlists maintain strict chronological ordering:
Episode #1 -> Episode #2 -> ... -> Episode #N
so viewer autoplay and algorithmic binge-watching flow naturally.
"""

import re
from typing import List, Dict, Any, Optional
from src.logging_config import get_logger
from src.exceptions import PublishingError

logger = get_logger(component="PlaylistManager")


class PlaylistManager:
    """Manages YouTube series playlists, item positioning, deduplication, and synchronization."""

    def __init__(self, series_playlist_title: str = "Last Day on Earth: Survival — Official Gameplay Series") -> None:
        self.playlist_title = series_playlist_title

    def extract_episode_number(self, title: str) -> Optional[int]:
        """Extracts episode number from video title (e.g. '#12', 'Episode 12', 'Ep 12')."""
        match = re.search(r"#(\d+)", title)
        if match:
            return int(match.group(1))

        match = re.search(r"(?:Episode|Ep)\.?\s*(\d+)", title, re.IGNORECASE)
        if match:
            return int(match.group(1))

        return None

    def get_playlist_items(self, youtube: Any, playlist_id: str) -> List[Dict[str, Any]]:
        """Retrieves all items currently in a YouTube playlist with position and video details."""
        try:
            items = []
            req = youtube.playlistItems().list(
                playlistId=playlist_id,
                part="id,snippet,contentDetails",
                maxResults=50,
            )
            while req:
                resp = req.execute()
                for item in resp.get("items", []):
                    snippet = item.get("snippet", {})
                    v_id = snippet.get("resourceId", {}).get("videoId")
                    v_title = snippet.get("title", "")
                    pos = snippet.get("position", 0)
                    ep_num = self.extract_episode_number(v_title)

                    items.append({
                        "item_id": item.get("id"),
                        "video_id": v_id,
                        "title": v_title,
                        "position": pos,
                        "episode_number": ep_num,
                    })
                req = youtube.playlistItems().list_next(req, resp)

            return items
        except Exception as e:
            logger.error(f"Failed to fetch items for playlist {playlist_id}: {e}")
            raise PublishingError(
                operation="get_playlist_items",
                root_cause=str(e),
                recovery_action="Check YouTube API quota or playlist permissions.",
                file_path=playlist_id,
            )

    def audit_playlist(self, youtube: Any, playlist_id: str) -> Dict[str, Any]:
        """Audits the playlist for chronological ordering, duplicates, and missing episodes."""
        items = self.get_playlist_items(youtube, playlist_id)

        seen_videos = set()
        duplicates = []
        episode_order = []
        is_chronological = True

        last_ep = -1
        for it in items:
            vid = it["video_id"]
            ep = it["episode_number"]

            if vid in seen_videos:
                duplicates.append(it)
            seen_videos.add(vid)

            if ep is not None:
                episode_order.append(ep)
                if ep < last_ep:
                    is_chronological = False
                last_ep = ep

        return {
            "playlist_id": playlist_id,
            "total_items": len(items),
            "unique_videos": len(seen_videos),
            "is_chronological": is_chronological,
            "episode_order": episode_order,
            "duplicates": duplicates,
            "items": items,
        }

    def sort_playlist_chronological(self, youtube: Any, playlist_id: str) -> bool:
        """Reorders playlist items into strict ascending chronological order (Episode 1 to N)."""
        logger.info(f"Initiating chronological sort for playlist {playlist_id}...")
        items = self.get_playlist_items(youtube, playlist_id)
        if not items:
            logger.info("Playlist is empty; nothing to sort.")
            return True

        # Sort items: primary key = episode_number (defaulting to 9999 if unnumbered), secondary = original position
        sorted_items = sorted(
            items,
            key=lambda x: (x["episode_number"] if x["episode_number"] is not None else 9999, x["position"]),
        )

        # Update position for each item that is out of place
        updated_count = 0
        manual_sort_needed = False
        for target_pos, it in enumerate(sorted_items):
            current_pos = it["position"]
            if current_pos != target_pos:
                try:
                    update_body = {
                        "id": it["item_id"],
                        "snippet": {
                            "playlistId": playlist_id,
                            "resourceId": {
                                "kind": "youtube#video",
                                "videoId": it["video_id"],
                            },
                            "position": target_pos,
                        },
                    }
                    youtube.playlistItems().update(part="snippet", body=update_body).execute()
                    logger.info(
                        f"Moved Video '{it['title'][:40]}' to position {target_pos} (Episode #{it['episode_number']})"
                    )
                    updated_count += 1
                except Exception as ue:
                    err_str = str(ue).lower()
                    if "manualsortrequired" in err_str or "manual" in err_str:
                        logger.warning(
                            "YouTube playlist sort setting requires manual mode. "
                            "Switching to chronological re-insertion rebuild..."
                        )
                        manual_sort_needed = True
                        break
                    else:
                        logger.warning(f"Could not reposition item {it['item_id']} to {target_pos}: {ue}")

        if manual_sort_needed:
            return self.rebuild_playlist_chronological(youtube, playlist_id)

        logger.info(f"Playlist sorting complete. Repositioned {updated_count} item(s).")
        return True

    def rebuild_playlist_chronological(self, youtube: Any, playlist_id: str) -> bool:
        """Rebuilds playlist by clearing and re-inserting items sequentially from Episode 1 to N.

        Bypasses YouTube's 'manualSortRequired' restriction by inserting items in chronological order.
        """
        logger.info(f"Rebuilding playlist {playlist_id} in chronological order...")
        items = self.get_playlist_items(youtube, playlist_id)
        if not items:
            return True

        # Deduplicate and sort items by episode number ascending
        seen = set()
        unique_ordered_items = []
        # Sort items: primary key = episode_number (defaulting to 9999 if unnumbered), secondary = original position
        sorted_items = sorted(
            items,
            key=lambda x: (x["episode_number"] if x["episode_number"] is not None else 9999, x["position"]),
        )
        for it in sorted_items:
            if it["video_id"] not in seen:
                seen.add(it["video_id"])
                unique_ordered_items.append(it)

        logger.info(f"Deleting {len(items)} existing items to rebuild in ascending order...")
        for it in items:
            try:
                youtube.playlistItems().delete(id=it["item_id"]).execute()
            except Exception as de:
                logger.warning(f"Failed deleting playlist item {it['item_id']}: {de}")

        logger.info(f"Re-inserting {len(unique_ordered_items)} items in reverse order so YouTube prepending yields #1 -> #N...")
        for it in reversed(unique_ordered_items):
            try:
                body = {
                    "snippet": {
                        "playlistId": playlist_id,
                        "resourceId": {
                            "kind": "youtube#video",
                            "videoId": it["video_id"],
                        },
                    }
                }
                youtube.playlistItems().insert(part="snippet", body=body).execute()
                logger.info(f"Prepended Video {it['video_id']} (Ep #{it['episode_number']}) - {it['title'][:40]}")
            except Exception as ie:
                logger.error(f"Failed to insert video {it['video_id']} into playlist: {ie}")

        logger.info("Successfully rebuilt playlist chronologically!")
        return True

    def deduplicate_playlist(self, youtube: Any, playlist_id: str) -> int:
        """Removes any duplicate occurrences of videos in the playlist, preserving the first instance."""
        items = self.get_playlist_items(youtube, playlist_id)
        seen = set()
        removed_count = 0

        for it in items:
            vid = it["video_id"]
            if vid in seen:
                try:
                    logger.info(f"Removing duplicate playlist item: {it['item_id']} (Video ID: {vid})")
                    youtube.playlistItems().delete(id=it["item_id"]).execute()
                    removed_count += 1
                except Exception as de:
                    logger.warning(f"Could not delete duplicate playlist item {it['item_id']}: {de}")
            else:
                seen.add(vid)

        logger.info(f"Playlist deduplication complete. Removed {removed_count} duplicate item(s).")
        return removed_count

    def add_video_sequentially(
        self,
        youtube: Any,
        video_id: str,
        playlist_id: str,
        episode_number: Optional[int] = None,
    ) -> bool:
        """Adds a video at the end of the playlist to preserve chronological order without duplicate."""
        try:
            # Check existing items
            items = self.get_playlist_items(youtube, playlist_id)
            for it in items:
                if it["video_id"] == video_id:
                    logger.info(f"Video {video_id} is already in playlist {playlist_id}")
                    return True

            target_pos = len(items)
            body = {
                "snippet": {
                    "playlistId": playlist_id,
                    "resourceId": {
                        "kind": "youtube#video",
                        "videoId": video_id,
                    },
                    "position": target_pos,
                }
            }
            youtube.playlistItems().insert(part="snippet", body=body).execute()
            logger.info(
                f"Video {video_id} appended to playlist {playlist_id} at sequential position {target_pos} successfully"
            )
            return True
        except Exception as e:
            logger.warning(f"Could not add video {video_id} to playlist {playlist_id}: {e}")
            return False
