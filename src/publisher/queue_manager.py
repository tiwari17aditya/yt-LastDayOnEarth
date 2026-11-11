"""Publishing queue manager for automated YouTube release scheduling.

Provides queue management, slot calculation, and persistence for staged
video releases aligned with creator-specified Indian Standard Time (IST) rhythms.
- Weekdays (Mon-Fri): 2 videos per day (3:00 PM IST & 7:00 PM IST)
- Weekends (Sat-Sun): 3 videos per day (11:00 AM IST, 4:00 PM IST & 8:00 PM IST)
"""

import json
from dataclasses import dataclass, asdict
from datetime import datetime, time, timedelta, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional
try:
    from zoneinfo import ZoneInfo
    IST = ZoneInfo("Asia/Kolkata")
except Exception:
    IST = timezone(timedelta(hours=5, minutes=30))

from src.logging_config import get_logger
from src.exceptions import PublishingError

logger = get_logger(component="PublishingQueueManager")


@dataclass
class PublishingQueueItem:
    """Represents a scheduled video item waiting or published in sequence."""
    episode_number: int
    video_id: str
    title: str
    scheduled_publish_time_utc: str  # RFC 3339 format, e.g. "2026-11-12T09:30:00Z"
    scheduled_publish_time_ist: str  # Human-readable IST string
    privacy_status: str = "private"
    status: str = "SCHEDULED"        # "SCHEDULED" or "PUBLISHED"
    youtube_url: str = ""
    enqueued_at_utc: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PublishingQueueItem":
        return cls(
            episode_number=int(data.get("episode_number", 0)),
            video_id=str(data.get("video_id", "")),
            title=str(data.get("title", "")),
            scheduled_publish_time_utc=str(data.get("scheduled_publish_time_utc", "")),
            scheduled_publish_time_ist=str(data.get("scheduled_publish_time_ist", "")),
            privacy_status=str(data.get("privacy_status", "private")),
            status=str(data.get("status", "SCHEDULED")),
            youtube_url=str(data.get("youtube_url", "")),
            enqueued_at_utc=str(data.get("enqueued_at_utc", "")),
        )


class PublishingQueueManager:
    """Manages the series release schedule queue and calculates publication slots."""

    DEFAULT_WEEKDAY_SLOTS = [time(15, 0), time(19, 0)]          # 3:00 PM, 7:00 PM IST
    DEFAULT_WEEKEND_SLOTS = [time(11, 0), time(16, 0), time(20, 0)]  # 11:00 AM, 4:00 PM, 8:00 PM IST

    def __init__(
        self,
        queue_file: Path = Path("data/publishing_queue.json"),
        weekday_slots: Optional[List[time]] = None,
        weekend_slots: Optional[List[time]] = None,
        min_lead_time_minutes: int = 45,
    ) -> None:
        self.queue_file = Path(queue_file)
        self.weekday_slots = sorted(weekday_slots or self.DEFAULT_WEEKDAY_SLOTS)
        self.weekend_slots = sorted(weekend_slots or self.DEFAULT_WEEKEND_SLOTS)
        self.min_lead_time_minutes = min_lead_time_minutes
        self._ensure_queue_file()

    def _ensure_queue_file(self) -> None:
        """Ensures the queue file exists with valid JSON structure."""
        if not self.queue_file.exists():
            self.queue_file.parent.mkdir(parents=True, exist_ok=True)
            initial_data = {
                "description": "Last Day on Earth Automated YouTube Publishing Release Queue",
                "weekday_slots_ist": [s.strftime("%H:%M") for s in self.weekday_slots],
                "weekend_slots_ist": [s.strftime("%H:%M") for s in self.weekend_slots],
                "queue": [],
                "last_updated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            }
            with open(self.queue_file, "w", encoding="utf-8") as f:
                json.dump(initial_data, f, indent=2)

    def load_queue(self) -> List[PublishingQueueItem]:
        """Loads and returns the list of queued items."""
        if not self.queue_file.exists():
            return []
        try:
            with open(self.queue_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            items = [PublishingQueueItem.from_dict(it) for it in data.get("queue", [])]
            return items
        except Exception as e:
            logger.warning(
                f"Could not load publishing queue from {self.queue_file}: {e}. Returning empty queue.",
                extra_data={"file": str(self.queue_file), "error": str(e)},
            )
            return []

    def save_queue(self, items: List[PublishingQueueItem]) -> None:
        """Saves queued items back to the JSON file."""
        self.queue_file.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "description": "Last Day on Earth Automated YouTube Publishing Release Queue",
            "weekday_slots_ist": [s.strftime("%H:%M") for s in self.weekday_slots],
            "weekend_slots_ist": [s.strftime("%H:%M") for s in self.weekend_slots],
            "queue": [it.to_dict() for it in items],
            "last_updated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
        with open(self.queue_file, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)

    def get_latest_scheduled_time(self) -> Optional[datetime]:
        """Returns the latest scheduled publish time among queued items in UTC, if any."""
        items = self.load_queue()
        latest_dt: Optional[datetime] = None
        for it in items:
            if not it.scheduled_publish_time_utc:
                continue
            try:
                dt = datetime.fromisoformat(it.scheduled_publish_time_utc.replace("Z", "+00:00"))
                if latest_dt is None or dt > latest_dt:
                    latest_dt = dt
            except Exception:
                continue
        return latest_dt

    def get_next_slot(self, reference_time: Optional[datetime] = None) -> datetime:
        """Calculates the next open publication slot in UTC.

        If previous items are already queued in the future, the next slot is scheduled
        strictly after the latest queued item to preserve series order and avoid collisions.
        Otherwise, schedules starting from reference_time + lead_time buffer.

        Returns:
            datetime object in UTC.
        """
        now_utc = datetime.now(timezone.utc)
        latest_queued_utc = self.get_latest_scheduled_time()

        # Determine reference point
        if reference_time is not None:
            ref_utc = reference_time if reference_time.tzinfo else reference_time.replace(tzinfo=timezone.utc)
        else:
            ref_utc = now_utc + timedelta(minutes=self.min_lead_time_minutes)

        if latest_queued_utc and latest_queued_utc > ref_utc:
            ref_utc = latest_queued_utc + timedelta(seconds=1)

        # Convert reference point to IST for slot matching
        ref_ist = ref_utc.astimezone(IST)
        candidate_date = ref_ist.date()

        # Search for the earliest slot matching weekday/weekend matrix strictly >= ref_ist
        for _ in range(60):  # Check up to 60 days ahead
            is_weekend = candidate_date.weekday() in (5, 6)  # Saturday=5, Sunday=6
            day_slots = self.weekend_slots if is_weekend else self.weekday_slots

            for slot_time in day_slots:
                candidate_dt_ist = datetime.combine(candidate_date, slot_time, tzinfo=IST)
                if candidate_dt_ist >= ref_ist:
                    candidate_dt_utc = candidate_dt_ist.astimezone(timezone.utc)
                    logger.info(
                        f"Allocated publishing slot: {candidate_dt_ist.strftime('%d %b %Y, %I:%M %p IST')} "
                        f"({candidate_dt_utc.strftime('%Y-%m-%dT%H:%M:%SZ')})",
                        extra_data={
                            "slot_ist": candidate_dt_ist.isoformat(),
                            "slot_utc": candidate_dt_utc.isoformat(),
                            "is_weekend": is_weekend,
                        },
                    )
                    return candidate_dt_utc

            candidate_date += timedelta(days=1)

        # Fallback safeguard: ref_utc + 1 day
        return ref_utc + timedelta(days=1)

    def add_scheduled_video(
        self,
        video_id: str,
        title: str,
        episode_number: int,
        publish_at_utc: datetime,
        youtube_url: str = "",
        privacy_status: str = "private",
    ) -> PublishingQueueItem:
        """Enqueues a newly scheduled video in the persistent queue."""
        publish_at_utc = publish_at_utc if publish_at_utc.tzinfo else publish_at_utc.replace(tzinfo=timezone.utc)
        dt_ist = publish_at_utc.astimezone(IST)
        formatted_ist = dt_ist.strftime("%d %b %Y, %I:%M %p IST")
        formatted_utc = publish_at_utc.strftime("%Y-%m-%dT%H:%M:%SZ")
        now_utc_str = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        if not youtube_url and video_id:
            youtube_url = f"https://youtu.be/{video_id}"

        new_item = PublishingQueueItem(
            episode_number=episode_number,
            video_id=video_id,
            title=title,
            scheduled_publish_time_utc=formatted_utc,
            scheduled_publish_time_ist=formatted_ist,
            privacy_status=privacy_status,
            status="SCHEDULED",
            youtube_url=youtube_url,
            enqueued_at_utc=now_utc_str,
        )

        items = self.load_queue()
        # Prevent exact duplicate video_id entry
        items = [it for it in items if it.video_id != video_id]
        items.append(new_item)
        # Sort queue by episode_number and publish time
        items.sort(key=lambda x: (x.episode_number, x.scheduled_publish_time_utc))
        self.save_queue(items)

        logger.info(
            f"Successfully queued Episode #{episode_number} ('{title}') for scheduled release at {formatted_ist}",
            extra_data=new_item.to_dict(),
        )
        return new_item

    def sync_queue_status(self, youtube_service: Optional[Any] = None) -> List[PublishingQueueItem]:
        """Updates status of queued items based on current time and optional YouTube API query."""
        items = self.load_queue()
        now_utc = datetime.now(timezone.utc)
        modified = False

        for it in items:
            if it.status == "SCHEDULED":
                try:
                    dt = datetime.fromisoformat(it.scheduled_publish_time_utc.replace("Z", "+00:00"))
                    if now_utc >= dt:
                        it.status = "PUBLISHED"
                        it.privacy_status = "public"
                        modified = True
                        logger.info(f"Video {it.video_id} (Episode #{it.episode_number}) release time passed; marked as PUBLISHED.")
                except Exception:
                    pass

        # Optional YouTube API status verification
        if youtube_service and any(it.status == "SCHEDULED" for it in items):
            for it in items:
                if it.status == "SCHEDULED" and it.video_id:
                    try:
                        resp = youtube_service.videos().list(id=it.video_id, part="status").execute()
                        items_resp = resp.get("items", [])
                        if items_resp:
                            stat = items_resp[0].get("status", {})
                            current_privacy = stat.get("privacyStatus")
                            if current_privacy == "public":
                                it.status = "PUBLISHED"
                                it.privacy_status = "public"
                                modified = True
                    except Exception as yt_err:
                        logger.debug(f"Could not verify YouTube status for video {it.video_id}: {yt_err}")

        if modified:
            self.save_queue(items)

        return items

    def get_scheduled_videos(self) -> List[PublishingQueueItem]:
        """Returns all videos currently scheduled (not yet published)."""
        return [it for it in self.load_queue() if it.status == "SCHEDULED"]

    def format_ist_time(self, dt: datetime) -> str:
        """Converts any datetime to readable IST format."""
        dt_ist = dt.astimezone(IST) if dt.tzinfo else dt.replace(tzinfo=timezone.utc).astimezone(IST)
        return dt_ist.strftime("%d %b %Y, %I:%M %p IST")

    def format_queue_summary(self) -> str:
        """Returns a formatted human-readable summary of the publishing queue."""
        items = self.load_queue()
        if not items:
            return "Publishing release queue is currently empty."

        lines = [
            f"YouTube Publishing Release Queue ({len(items)} items tracked):",
            "Weekday Cadence: 2 videos/day (3:00 PM & 7:00 PM IST)",
            "Weekend Cadence: 3 videos/day (11:00 AM, 4:00 PM & 8:00 PM IST)",
            "-" * 65,
        ]
        for it in items:
            status_symbol = "⏳ [SCHEDULED]" if it.status == "SCHEDULED" else "✅ [PUBLISHED]"
            lines.append(
                f"{status_symbol} Ep #{it.episode_number:03d} | {it.scheduled_publish_time_ist} | {it.video_id} | {it.title[:35]}..."
            )
        lines.append("-" * 65)
        return "\n".join(lines)
