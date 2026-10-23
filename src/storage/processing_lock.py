"""Process-level lock manager to prevent overlapping video processing jobs."""

import json
import os
import platform
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional

from src.logging_config import get_logger

logger = get_logger(component="ProcessingLock")


def is_pid_running(pid: int) -> bool:
    """Checks whether a process with the given PID is currently running."""
    if pid <= 0:
        return False

    # Unix-like check
    if hasattr(os, "kill"):
        try:
            os.kill(pid, 0)
            return True
        except OSError:
            pass

    # Windows check using Windows API
    if platform.system().lower() == "windows":
        try:
            import ctypes
            PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
            STILL_ACTIVE = 259
            
            kernel32 = ctypes.windll.kernel32
            handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
            if not handle:
                return False
            try:
                exit_code = ctypes.c_ulong()
                if kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code)):
                    return exit_code.value == STILL_ACTIVE
                return False
            finally:
                kernel32.CloseHandle(handle)
        except Exception:
            pass

    return False


class ProcessingLock:
    """Coordinates execution so scheduled checks never overlap with active video processing."""

    def __init__(
        self,
        lock_file: Path = Path("data/.processing_lock.json"),
        stale_timeout_seconds: int = 7200,  # 2 hours
    ) -> None:
        self.lock_file = lock_file
        self.stale_timeout_seconds = stale_timeout_seconds
        self.acquired = False
        self.current_job_id = None

    def get_lock_info(self) -> Optional[Dict[str, Any]]:
        """Reads lock metadata from disk if present and valid JSON."""
        if not self.lock_file.exists():
            return None
        try:
            with open(self.lock_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None

    def is_locked(self) -> bool:
        """Determines if a valid, non-stale lock is currently held by an active job."""
        info = self.get_lock_info()
        if not info:
            return False

        pid = info.get("pid")
        started_str = info.get("started_at")

        # Check stale timeout
        if started_str:
            try:
                started_dt = datetime.fromisoformat(started_str)
                age = (datetime.now(timezone.utc) - started_dt).total_seconds()
                if age > self.stale_timeout_seconds:
                    logger.warning(
                        f"Found stale processing lock (Age: {age:.0f}s > {self.stale_timeout_seconds}s). Expiring lock."
                    )
                    self._force_remove()
                    return False
            except Exception:
                pass

        # Check process liveness if on the same host
        host = info.get("host")
        current_host = platform.node()
        if pid and (not host or host == current_host):
            if not is_pid_running(pid):
                logger.warning(f"Process PID {pid} holding lock is no longer running. Clearing abandoned lock.")
                self._force_remove()
                return False

        return True

    def acquire(self, job_id: str = "", video_name: Optional[str] = None) -> bool:
        """Attempts to acquire the lock. Returns True if acquired, False if another job is running."""
        if self.is_locked():
            info = self.get_lock_info() or {}
            logger.warning(
                "A video processing job is currently running. Skipping this scheduled run to prevent overlap.",
                extra_data={
                    "active_job_id": info.get("job_id"),
                    "active_pid": info.get("pid"),
                    "started_at": info.get("started_at"),
                    "video": info.get("video_name"),
                },
            )
            return False

        self.lock_file.parent.mkdir(parents=True, exist_ok=True)
        self.current_job_id = job_id or f"job_{int(time.time())}"
        payload = {
            "job_id": self.current_job_id,
            "pid": os.getpid(),
            "started_at": datetime.now(timezone.utc).isoformat(),
            "video_name": video_name or "",
            "host": platform.node(),
        }

        # Atomic write
        temp_file = self.lock_file.with_name(f"{self.lock_file.name}.tmp.{os.getpid()}")
        try:
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2)
            temp_file.replace(self.lock_file)
            self.acquired = True
            logger.info("Acquired processing lock", extra_data={"job_id": self.current_job_id, "pid": os.getpid()})
            return True
        except Exception as e:
            logger.error(f"Failed to write processing lock file: {e}")
            if temp_file.exists():
                try:
                    temp_file.unlink()
                except OSError:
                    pass
            return False

    def release(self) -> None:
        """Releases the lock if held by this instance."""
        if self.acquired:
            self._force_remove()
            self.acquired = False
            logger.info("Released processing lock", extra_data={"job_id": self.current_job_id})

    def _force_remove(self) -> None:
        if self.lock_file.exists():
            try:
                self.lock_file.unlink()
            except OSError as e:
                logger.warning(f"Could not remove lock file: {e}")

    def __enter__(self) -> "ProcessingLock":
        self.acquire()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.release()
