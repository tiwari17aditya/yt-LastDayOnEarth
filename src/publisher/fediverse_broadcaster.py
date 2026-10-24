"""Fediverse & Open-Source Social Broadcast Module (Mastodon / Lemmy / ActivityPub).

Automatically shares newly published episodes to decentralized social networks
to drive organic reach, community discovery, and Fediverse engagement.
"""

import json
from pathlib import Path
from typing import Dict, Any, List, Optional
import urllib.parse
import urllib.request
import urllib.error

from src.logging_config import get_logger
from src.exceptions import PipelineError

logger = get_logger(component="FediverseBroadcaster")


class FediverseBroadcaster:
    """Dispatches episode release announcements to Mastodon, Lemmy, and ActivityPub networks."""

    def __init__(
        self,
        mastodon_instance: Optional[str] = None,
        mastodon_access_token: Optional[str] = None,
        lemmy_instance: Optional[str] = None,
        lemmy_auth_token: Optional[str] = None,
        lemmy_community_id: Optional[int] = None,
        default_hashtags: Optional[List[str]] = None,
    ) -> None:
        self.mastodon_instance = (mastodon_instance or "").rstrip("/")
        self.mastodon_token = mastodon_access_token
        self.lemmy_instance = (lemmy_instance or "").rstrip("/")
        self.lemmy_token = lemmy_auth_token
        self.lemmy_community_id = lemmy_community_id
        self.default_hashtags = default_hashtags or [
            "LastDayOnEarth",
            "LDoE",
            "SurvivalGaming",
            "Gaming",
            "Gameplay",
            "MobileGaming",
            "FediverseGaming",
        ]

    def is_mastodon_enabled(self) -> bool:
        """Returns True if Mastodon instance and token are configured."""
        return bool(self.mastodon_instance and self.mastodon_token)

    def is_lemmy_enabled(self) -> bool:
        """Returns True if Lemmy instance, community, and token are configured."""
        return bool(self.lemmy_instance and self.lemmy_token and self.lemmy_community_id)

    def _upload_mastodon_media(self, image_path: Path) -> Optional[str]:
        """Uploads thumbnail image to Mastodon to attach to the status post."""
        if not self.is_mastodon_enabled() or not image_path.exists():
            return None

        upload_url = f"{self.mastodon_instance}/api/v1/media"
        boundary = "----WebKitFormBoundaryMastodonMedia389271"

        header = (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="file"; filename="{image_path.name}"\r\n'
            f"Content-Type: image/jpeg\r\n\r\n"
        ).encode("utf-8")

        with open(image_path, "rb") as f:
            file_bytes = f.read()

        closing = f"\r\n--{boundary}--\r\n".encode("utf-8")
        payload = header + file_bytes + closing

        req = urllib.request.Request(
            upload_url,
            data=payload,
            headers={
                "Authorization": f"Bearer {self.mastodon_token}",
                "Content-Type": f"multipart/form-data; boundary={boundary}",
                "User-Agent": "LDoE-Autonomous-Pipeline/1.0",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                media_id = data.get("id")
                logger.info(f"Thumbnail uploaded to Mastodon (Media ID: {media_id})")
                return media_id
        except Exception as e:
            logger.warning(f"Mastodon media attachment upload failed (proceeding without image): {e}")
            return None

    def broadcast_to_mastodon(
        self,
        title: str,
        youtube_url: str,
        episode_number: Optional[int] = None,
        peertube_url: Optional[str] = None,
        thumbnail_path: Optional[Path] = None,
        custom_hashtags: Optional[List[str]] = None,
    ) -> Optional[str]:
        """Posts an episode announcement status to Mastodon."""
        if not self.is_mastodon_enabled():
            logger.debug("Mastodon broadcast skipped: instance or token not configured.")
            return None

        ep_tag = f" #Episode{episode_number}" if episode_number else ""
        tags = set(self.default_hashtags + (custom_hashtags or []))
        hashtags_str = " ".join([f"#{t.lstrip('#')}" for t in tags if t.strip()])

        lines = [
            f"🎬 NEW SURVIVAL EPISODE RELEASED!{ep_tag}",
            f"",
            f"🔥 {title}",
            f"",
            f"▶️ Watch on YouTube: {youtube_url}",
        ]

        if peertube_url and "http" in peertube_url:
            lines.append(f"🌐 Decentralized Mirror: {peertube_url}")

        lines.extend([
            f"",
            f"{hashtags_str}",
        ])

        status_text = "\n".join(lines)

        # Upload thumbnail if available
        media_id = None
        if thumbnail_path and thumbnail_path.exists():
            media_id = self._upload_mastodon_media(thumbnail_path)

        post_url = f"{self.mastodon_instance}/api/v1/statuses"
        post_data = {
            "status": status_text,
            "visibility": "public",
        }
        if media_id:
            post_data["media_ids[]"] = [media_id]

        encoded_data = urllib.parse.urlencode(post_data, doseq=True).encode("utf-8")
        req = urllib.request.Request(
            post_url,
            data=encoded_data,
            headers={
                "Authorization": f"Bearer {self.mastodon_token}",
                "Content-Type": "application/x-www-form-urlencoded",
                "User-Agent": "LDoE-Autonomous-Pipeline/1.0",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                status_url = data.get("url")
                logger.info(
                    f"Successfully broadcasted episode to Mastodon: {status_url}",
                    extra_data={"mastodon_url": status_url, "title": title},
                )
                return status_url
        except Exception as e:
            logger.error(
                f"Failed to post broadcast to Mastodon: {e}",
                extra_data={
                    "operation": "mastodon_broadcast",
                    "component": "FediverseBroadcaster",
                    "root_cause": str(e),
                },
            )
            return None

    def broadcast_to_lemmy(
        self,
        title: str,
        video_url: str,
        body_text: Optional[str] = None,
    ) -> Optional[str]:
        """Submits video link post to a Lemmy federated community."""
        if not self.is_lemmy_enabled():
            logger.debug("Lemmy broadcast skipped: lemmy credentials not configured.")
            return None

        post_url = f"{self.lemmy_instance}/api/v3/post"
        payload = {
            "auth": self.lemmy_token,
            "community_id": self.lemmy_community_id,
            "name": title[:100],
            "url": video_url,
            "body": body_text or f"New Last Day on Earth automated gameplay survival episode: {title}",
        }

        req = urllib.request.Request(
            post_url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "User-Agent": "LDoE-Autonomous-Pipeline/1.0",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                post_view = data.get("post_view", {})
                post_id = post_view.get("post", {}).get("id")
                lemmy_url = f"{self.lemmy_instance}/post/{post_id}" if post_id else None
                logger.info(f"Successfully posted to Lemmy community: {lemmy_url}")
                return lemmy_url
        except Exception as e:
            logger.warning(f"Lemmy post submission failed: {e}")
            return None

    def broadcast_release(
        self,
        title: str,
        youtube_url: str,
        episode_number: Optional[int] = None,
        peertube_url: Optional[str] = None,
        thumbnail_path: Optional[Path] = None,
    ) -> Dict[str, Optional[str]]:
        """Unified broadcast trigger for all configured open-source social networks."""
        results = {
            "mastodon_url": None,
            "lemmy_url": None,
        }

        # 1. Mastodon / Fediverse
        if self.is_mastodon_enabled():
            results["mastodon_url"] = self.broadcast_to_mastodon(
                title=title,
                youtube_url=youtube_url,
                episode_number=episode_number,
                peertube_url=peertube_url,
                thumbnail_path=thumbnail_path,
            )

        # 2. Lemmy Community
        if self.is_lemmy_enabled():
            target_url = peertube_url or youtube_url
            results["lemmy_url"] = self.broadcast_to_lemmy(
                title=title,
                video_url=target_url,
            )

        return results
