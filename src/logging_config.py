"""Structured, machine-readable logging for the Last Day on Earth pipeline.

Adheres to standard:
- Default log path: logs/YYYY-MM-DD/application.log
- Structured JSON output with timestamp, level, component, operation, message, and metrics.
- Formatted console output for developer visibility.
"""

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, Any


class StructuredJsonFormatter(logging.Formatter):
    """Formats log records as newline-delimited JSON objects."""

    def format(self, record: logging.LogRecord) -> str:
        log_payload: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "component": getattr(record, "component", "General"),
            "operation": getattr(record, "operation", "Default"),
            "message": record.getMessage(),
        }

        # Include custom metadata if provided
        if hasattr(record, "extra_data") and isinstance(record.extra_data, dict):
            log_payload["data"] = record.extra_data

        if record.exc_info:
            log_payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_payload, ensure_ascii=False)


class ConsoleFormatter(logging.Formatter):
    """Formats log records with readable console output."""

    def format(self, record: logging.LogRecord) -> str:
        timestamp = datetime.now().strftime("%H:%M:%S")
        component = getattr(record, "component", record.name)
        operation = getattr(record, "operation", "-")
        return f"[{timestamp}] [{record.levelname:<7}] [{component}] ({operation}) {record.getMessage()}"


class CustomLoggerAdapter(logging.LoggerAdapter):
    """Custom adapter that safely handles extra_data kwargs."""

    def process(self, msg: str, kwargs: Dict[str, Any]) -> tuple:
        extra = kwargs.get("extra", {})
        if not isinstance(extra, dict):
            extra = {}
        extra.update(self.extra)
        if "extra_data" in kwargs:
            extra["extra_data"] = kwargs.pop("extra_data")
        kwargs["extra"] = extra
        return msg, kwargs


def setup_logger(
    base_log_dir: str = "logs",
    level: int = logging.INFO,
    component: str = "Pipeline",
) -> logging.Logger:
    """Configures structured file and console logging."""
    logger = logging.getLogger(f"ldoe.{component}")
    logger.setLevel(level)

    # Prevent duplicate handlers if already configured
    if logger.handlers:
        return logger

    # Ensure daily log directory: logs/YYYY-MM-DD/
    today_str = datetime.now().strftime("%Y-%m-%d")
    daily_log_dir = Path(base_log_dir) / today_str
    daily_log_dir.mkdir(parents=True, exist_ok=True)
    log_file_path = daily_log_dir / "application.log"

    # File Handler (JSON lines)
    file_handler = logging.FileHandler(log_file_path, encoding="utf-8")
    file_handler.setLevel(level)
    file_handler.setFormatter(StructuredJsonFormatter())
    logger.addHandler(file_handler)

    # Console Handler (Human-readable)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(ConsoleFormatter())
    logger.addHandler(console_handler)

    return logger


def get_logger(component: str = "Pipeline", operation: str = "General") -> CustomLoggerAdapter:
    """Returns a CustomLoggerAdapter with preset component and operation context."""
    base_logger = setup_logger(component=component)
    return CustomLoggerAdapter(
        base_logger,
        {"component": component, "operation": operation},
    )
