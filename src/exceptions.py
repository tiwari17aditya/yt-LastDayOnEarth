"""Unified structured error handling for the Last Day on Earth pipeline.

Every significant operation failure must capture:
- Operation: Action being attempted
- Component: Subsystem / module
- File: Path to the affected file (if applicable)
- Root Cause: Underlying error message or exception
- Recovery Action: Mitigation or user action needed
- Execution Status: Status string (FAILED, ABORTED, DEGRADED, RETRYING)
"""

from typing import Optional, Dict, Any


class PipelineError(Exception):
    """Base exception for all pipeline errors adhering to global engineering standards."""

    def __init__(
        self,
        operation: str,
        component: str,
        root_cause: str,
        recovery_action: str,
        file_path: Optional[str] = None,
        status: str = "FAILED",
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.operation = operation
        self.component = component
        self.root_cause = root_cause
        self.recovery_action = recovery_action
        self.file_path = file_path or "N/A"
        self.status = status
        self.details = details or {}

        message = (
            f"[{self.status}] Component: {self.component} | Operation: {self.operation} | "
            f"File: {self.file_path} | Cause: {self.root_cause} | "
            f"Action: {self.recovery_action}"
        )
        super().__init__(message)

    def to_dict(self) -> Dict[str, Any]:
        """Convert the error into a structured dictionary for machine-readable logging & email alerts."""
        return {
            "status": self.status,
            "component": self.component,
            "operation": self.operation,
            "file_path": self.file_path,
            "root_cause": self.root_cause,
            "recovery_action": self.recovery_action,
            "details": self.details,
        }


class ConfigurationError(PipelineError):
    """Raised when configuration values, credentials, or environment variables are missing/invalid."""

    def __init__(
        self,
        operation: str,
        root_cause: str,
        recovery_action: str = "Review .env and config/settings.yaml for missing parameters.",
        file_path: Optional[str] = ".env",
        status: str = "FAILED",
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(
            operation=operation,
            component="ConfigurationManager",
            root_cause=root_cause,
            recovery_action=recovery_action,
            file_path=file_path,
            status=status,
            details=details,
        )


class IngestionError(PipelineError):
    """Raised during Google Drive scanning, downloading, or file moving operations."""

    def __init__(
        self,
        operation: str,
        root_cause: str,
        recovery_action: str,
        file_path: Optional[str] = None,
        status: str = "FAILED",
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(
            operation=operation,
            component="IngestionModule",
            root_cause=root_cause,
            recovery_action=recovery_action,
            file_path=file_path,
            status=status,
            details=details,
        )


class PrivacyRedactionError(PipelineError):
    """Raised when OCR or frame redaction processes encounter an unrecoverable failure."""

    def __init__(
        self,
        operation: str,
        root_cause: str,
        recovery_action: str,
        file_path: Optional[str] = None,
        status: str = "FAILED",
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(
            operation=operation,
            component="PrivacyGuard",
            root_cause=root_cause,
            recovery_action=recovery_action,
            file_path=file_path,
            status=status,
            details=details,
        )


class SubtitleGenerationError(PipelineError):
    """Raised during AI event recognition, subtitle generation or ASS formatting."""

    def __init__(
        self,
        operation: str,
        root_cause: str,
        recovery_action: str,
        file_path: Optional[str] = None,
        status: str = "FAILED",
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(
            operation=operation,
            component="SubtitleEngine",
            root_cause=root_cause,
            recovery_action=recovery_action,
            file_path=file_path,
            status=status,
            details=details,
        )


class AudioProcessingError(PipelineError):
    """Raised during track selection, audio ducking, looping, or audio filter assembly."""

    def __init__(
        self,
        operation: str,
        root_cause: str,
        recovery_action: str,
        file_path: Optional[str] = None,
        status: str = "FAILED",
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(
            operation=operation,
            component="AudioMixer",
            root_cause=root_cause,
            recovery_action=recovery_action,
            file_path=file_path,
            status=status,
            details=details,
        )


class VideoProcessingError(PipelineError):
    """Raised when FFmpeg video encoding, transcoding, or composite rendering fails."""

    def __init__(
        self,
        operation: str,
        root_cause: str,
        recovery_action: str,
        file_path: Optional[str] = None,
        status: str = "FAILED",
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(
            operation=operation,
            component="VideoProcessor",
            root_cause=root_cause,
            recovery_action=recovery_action,
            file_path=file_path,
            status=status,
            details=details,
        )


class PublishingError(PipelineError):
    """Raised when YouTube API metadata generation, quota check, or video upload fails."""

    def __init__(
        self,
        operation: str,
        root_cause: str,
        recovery_action: str,
        file_path: Optional[str] = None,
        status: str = "FAILED",
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(
            operation=operation,
            component="YouTubePublisher",
            root_cause=root_cause,
            recovery_action=recovery_action,
            file_path=file_path,
            status=status,
            details=details,
        )


class NotificationError(PipelineError):
    """Raised when SMTP email dispatch or reporting aggregation fails."""

    def __init__(
        self,
        operation: str,
        root_cause: str,
        recovery_action: str,
        file_path: Optional[str] = None,
        status: str = "FAILED",
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(
            operation=operation,
            component="NotificationSystem",
            root_cause=root_cause,
            recovery_action=recovery_action,
            file_path=file_path,
            status=status,
            details=details,
        )


class GrowthTrackingError(PipelineError):
    """Raised when YouTube platform reach, statistics, or comment fetching fails."""

    def __init__(
        self,
        operation: str,
        root_cause: str,
        recovery_action: str,
        file_path: Optional[str] = None,
        status: str = "FAILED",
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(
            operation=operation,
            component="GrowthTracker",
            root_cause=root_cause,
            recovery_action=recovery_action,
            file_path=file_path,
            status=status,
            details=details,
        )
