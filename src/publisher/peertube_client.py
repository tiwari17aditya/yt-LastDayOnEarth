"""PeerTube decentralized open-source video publisher (ActivityPub / Fediverse).

Implements BasePublisher for automated upload to any federated PeerTube instance,
expanding video reach across the global decentralized Fediverse.
"""

import json
from pathlib import Path
from typing import Dict, Any, List, Optional
import urllib.parse
import urllib.request
import urllib.error

from src.logging_config import get_logger
from src.exceptions import PublishingError
from src.publisher.youtube_client import BasePublisher, VideoPublishMetadata

logger = get_logger(component="PeerTubePublisher")

# PeerTube Category: 2 = Gaming, 1 = Music, etc.
PEERTUBE_GAMING_CATEGORY = 2
# PeerTube Licence: 1 = CC-BY, 6 = Standard
PEERTUBE_CC_BY_LICENSE = 1


class PeerTubeClient(BasePublisher):
    """Publishes videos to decentralized PeerTube instances via the PeerTube REST API v1."""

    def __init__(
        self,
        instance_url: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        access_token: Optional[str] = None,
        channel_name: Optional[str] = None,
        privacy_status: int = 1,  # 1 = Public, 2 = Unlisted, 3 = Private
    ) -> None:
        self.instance_url = (instance_url or "").rstrip("/")
        self.username = username
        self.password = password
        self.client_id = client_id
        self.client_secret = client_secret
        self.access_token = access_token
        self.channel_name = channel_name
        self.privacy_status = privacy_status
        self._cached_channel_id: Optional[int] = None

    def is_configured(self) -> bool:
        """Returns True if the required instance and authentication parameters are configured."""
        if not self.instance_url:
            return False
        return bool(self.access_token or (self.username and self.password))

    def _get_auth_token(self) -> Optional[str]:
        """Retrieves or refreshes an OAuth2 access token from the PeerTube instance."""
        if self.access_token:
            return self.access_token

        if not (self.username and self.password):
            logger.warning("PeerTube credentials missing (need username & password or access_token).")
            return None

        # PeerTube OAuth2 token endpoint
        token_url = f"{self.instance_url}/api/v1/users/token"
        
        # If client_id/secret not provided, PeerTube instances allow public client registration
        client_id = self.client_id or "peertube"
        client_secret = self.client_secret or ""

        data = {
            "grant_type": "password",
            "username": self.username,
            "password": self.password,
            "client_id": client_id,
        }
        if client_secret:
            data["client_secret"] = client_secret

        encoded_data = urllib.parse.urlencode(data).encode("utf-8")
        req = urllib.request.Request(
            token_url,
            data=encoded_data,
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "User-Agent": "LDoE-Autonomous-Pipeline/1.0",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                res_json = json.loads(resp.read().decode("utf-8"))
                self.access_token = res_json.get("access_token")
                logger.info(f"Successfully authenticated with PeerTube instance: {self.instance_url}")
                return self.access_token
        except Exception as e:
            logger.error(
                f"Failed to authenticate with PeerTube instance {self.instance_url}: {e}",
                extra_data={
                    "operation": "peertube_auth",
                    "component": "PeerTubePublisher",
                    "root_cause": str(e),
                },
            )
            return None

    def _resolve_channel_id(self, token: str) -> Optional[int]:
        """Resolves target video channel ID on the PeerTube instance."""
        if self._cached_channel_id is not None:
            return self._cached_channel_id

        if not self.channel_name:
            return None

        url = f"{self.instance_url}/api/v1/video-channels/{self.channel_name}"
        req = urllib.request.Request(
            url,
            headers={
                "Authorization": f"Bearer {token}",
                "User-Agent": "LDoE-Autonomous-Pipeline/1.0",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                self._cached_channel_id = data.get("id")
                return self._cached_channel_id
        except Exception as e:
            logger.debug(f"Could not resolve channel {self.channel_name} on PeerTube: {e}")
            return None

    def generate_metadata(
        self,
        video_title: str,
        events: List[Any],
        music_track: Optional[Dict[str, Any]] = None,
        thumbnail_path: Optional[Path] = None,
        episode_number: Optional[int] = None,
    ) -> VideoPublishMetadata:
        """Adapts video metadata for PeerTube's decentralized fediverse audience."""
        tags = ["LastDayOnEarth", "LDoE", "Survival", "Gaming", "MobileGaming", "OpenSource"]
        description = (
            f"{video_title}\n\n"
            f"Official high-efficiency automated gameplay series.\n"
            f"Federated on the Fediverse via PeerTube!\n\n"
            f"Tags: {' '.join(['#' + t for t in tags])}"
        )
        return VideoPublishMetadata(
            title=video_title[:120],
            description=description,
            tags=tags[:5],  # PeerTube supports up to 5 tags per video
            category_id=str(PEERTUBE_GAMING_CATEGORY),
            privacy_status=str(self.privacy_status),
            thumbnail_path=str(thumbnail_path) if thumbnail_path else None,
            episode_number=episode_number,
        )

    def upload_video(self, video_path: Path, metadata: VideoPublishMetadata) -> str:
        """Uploads video to PeerTube instance and returns the federated watch URL."""
        if not video_path.exists():
            raise PublishingError(
                operation="upload_video",
                root_cause=f"File not found: {video_path}",
                recovery_action="Ensure video was rendered before uploading.",
                file_path=str(video_path),
            )

        if not self.is_configured():
            logger.warning("PeerTube publishing is skipped: instance_url or credentials not configured.")
            return "N/A (PeerTube unconfigured)"

        token = self._get_auth_token()
        if not token:
            raise PublishingError(
                operation="peertube_auth",
                root_cause=f"Could not obtain access token for {self.instance_url}",
                recovery_action="Verify PEERTUBE_USERNAME, PEERTUBE_PASSWORD, and PEERTUBE_INSTANCE_URL in .env.",
                file_path=str(video_path),
            )

        channel_id = self._resolve_channel_id(token)

        logger.info(
            f"Uploading video '{metadata.title}' to PeerTube ({self.instance_url})...",
            extra_data={"file": str(video_path), "title": metadata.title},
        )

        # Multipart form data builder
        boundary = "----WebKitFormBoundaryPeerTubeUpload7MA4YWxkTrZu0gW"
        body_parts = []

        def add_field(name: str, value: str):
            body_parts.append(
                f"--{boundary}\r\n"
                f'Content-Disposition: form-data; name="{name}"\r\n\r\n'
                f"{value}\r\n"
            )

        # Truncate title to PeerTube max length (120 chars)
        add_field("name", metadata.title[:120])
        add_field("category", str(PEERTUBE_GAMING_CATEGORY))
        add_field("licence", str(PEERTUBE_CC_BY_LICENSE))
        add_field("privacy", str(self.privacy_status))
        add_field("description", metadata.description[:5000])

        if channel_id:
            add_field("channelId", str(channel_id))

        # Add up to 5 tags
        for tag in (metadata.tags or [])[:5]:
            clean_tag = tag.strip().lstrip("#")[:30]
            if clean_tag:
                add_field("tags[]", clean_tag)

        # Assemble multipart prefix
        prefix_bytes = "".join(body_parts).encode("utf-8")

        # Video file part header
        file_header = (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="videofile"; filename="{video_path.name}"\r\n'
            f"Content-Type: video/mp4\r\n\r\n"
        ).encode("utf-8")

        closing_boundary = f"\r\n--{boundary}--\r\n".encode("utf-8")

        upload_url = f"{self.instance_url}/api/v1/videos/upload"

        try:
            with open(video_path, "rb") as vf:
                file_bytes = vf.read()

            full_payload = prefix_bytes + file_header + file_bytes + closing_boundary

            req = urllib.request.Request(
                upload_url,
                data=full_payload,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": f"multipart/form-data; boundary={boundary}",
                    "User-Agent": "LDoE-Autonomous-Pipeline/1.0",
                },
                method="POST",
            )

            with urllib.request.urlopen(req, timeout=300) as resp:
                res_data = json.loads(resp.read().decode("utf-8"))
                video_info = res_data.get("video", {})
                short_uuid = video_info.get("shortUUID") or video_info.get("uuid")
                
                if short_uuid:
                    watch_url = f"{self.instance_url}/w/{short_uuid}"
                else:
                    watch_url = f"{self.instance_url}/videos/watch/{video_info.get('id', '')}"

                logger.info(
                    f"Successfully published to PeerTube: {watch_url}",
                    extra_data={"peertube_url": watch_url, "video_id": short_uuid},
                )

                # If thumbnail provided, upload thumbnail image
                if metadata.thumbnail_path and Path(metadata.thumbnail_path).exists():
                    self._upload_thumbnail(short_uuid or video_info.get("id"), Path(metadata.thumbnail_path), token)

                return watch_url

        except urllib.error.HTTPError as he:
            err_body = he.read().decode("utf-8", errors="replace")
            logger.error(f"PeerTube upload HTTP {he.code}: {err_body}")
            raise PublishingError(
                operation="peertube_upload",
                root_cause=f"PeerTube HTTP {he.code}: {err_body}",
                recovery_action="Check PeerTube instance quota, file size limits, or user permissions.",
                file_path=str(video_path),
            )
        except Exception as e:
            logger.error(f"PeerTube upload failed: {e}")
            raise PublishingError(
                operation="peertube_upload",
                root_cause=str(e),
                recovery_action="Inspect network connectivity to PeerTube instance.",
                file_path=str(video_path),
            )

    def _upload_thumbnail(self, video_identifier: Any, thumbnail_path: Path, token: str) -> bool:
        """Uploads custom thumbnail to PeerTube for the given video."""
        try:
            url = f"{self.instance_url}/api/v1/videos/{video_identifier}/thumbnail"
            boundary = "----WebKitFormBoundaryPeerTubeThumb9x8y7z"

            header = (
                f"--{boundary}\r\n"
                f'Content-Disposition: form-data; name="thumbnailfile"; filename="{thumbnail_path.name}"\r\n'
                f"Content-Type: image/jpeg\r\n\r\n"
            ).encode("utf-8")

            with open(thumbnail_path, "rb") as tf:
                thumb_bytes = tf.read()

            closing = f"\r\n--{boundary}--\r\n".encode("utf-8")
            payload = header + thumb_bytes + closing

            req = urllib.request.Request(
                url,
                data=payload,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": f"multipart/form-data; boundary={boundary}",
                    "User-Agent": "LDoE-Autonomous-Pipeline/1.0",
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=30):
                logger.info(f"Custom thumbnail uploaded to PeerTube for video {video_identifier}")
                return True
        except Exception as e:
            logger.warning(f"PeerTube thumbnail upload non-critical failure: {e}")
            return False
