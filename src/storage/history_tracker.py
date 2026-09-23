"""Persistent history tracking for processed and published videos."""

import json
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from src.logging_config import get_logger

logger = get_logger(component="HistoryTracker")


class HistoryTracker:
    """Manages appending and querying historical video processing records."""

    def __init__(self, history_file: Path = Path("data/history.json")) -> None:
        self.history_file = history_file
        self._ensure_file_exists()

    def _ensure_file_exists(self) -> None:
        self.history_file.parent.mkdir(parents=True, exist_ok=True)
        if not self.history_file.exists():
            with open(self.history_file, "w", encoding="utf-8") as f:
                json.dump([], f, indent=2)

    def load_records(self) -> List[Dict[str, Any]]:
        try:
            with open(self.history_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error("Failed to read history file", extra_data={"error": str(e)})
            return []

    def is_duplicate(self, input_filename: str, md5_checksum: Optional[str] = None) -> bool:
        """Checks if a video with the same MD5 checksum or input filename was successfully processed."""
        records = self.load_records()
        for r in records:
            if r.get("status") != "SUCCESS":
                continue
            # Match by MD5 checksum (strongest guarantee)
            if md5_checksum and r.get("details", {}).get("md5_checksum") == md5_checksum:
                logger.info(f"Duplicate detected by MD5 checksum: {md5_checksum} (Job: {r.get('job_id')})")
                return True
            # Match by filename
            if input_filename and r.get("input_filename") == input_filename:
                logger.info(f"Duplicate detected by filename: {input_filename} (Job: {r.get('job_id')})")
                return True
        return False

    def record_job(
        self,
        job_id: str,
        input_filename: str,
        output_filename: str,
        status: str,
        youtube_url: str = "",
        details: Dict[str, Any] = None,
        md5_checksum: Optional[str] = None,
    ) -> None:
        records = self.load_records()
        details = details or {}
        if md5_checksum:
            details["md5_checksum"] = md5_checksum

        new_record = {
            "job_id": job_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "input_filename": input_filename,
            "output_filename": output_filename,
            "status": status,
            "youtube_url": youtube_url,
            "details": details,
        }
        records.append(new_record)
        with open(self.history_file, "w", encoding="utf-8") as f:
            json.dump(records, f, indent=2)
        logger.info("Recorded job execution to history", extra_data={"job_id": job_id, "status": status})

