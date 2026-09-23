"""Persistent history tracking for processed and published videos."""

import json
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, List
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

    def record_job(
        self,
        job_id: str,
        input_filename: str,
        output_filename: str,
        status: str,
        youtube_url: str = "",
        details: Dict[str, Any] = None,
    ) -> None:
        records = self.load_records()
        new_record = {
            "job_id": job_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "input_filename": input_filename,
            "output_filename": output_filename,
            "status": status,
            "youtube_url": youtube_url,
            "details": details or {},
        }
        records.append(new_record)
        with open(self.history_file, "w", encoding="utf-8") as f:
            json.dump(records, f, indent=2)
        logger.info("Recorded job execution to history", extra_data={"job_id": job_id, "status": status})
