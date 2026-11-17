"""Cloud voice cloning client with resilient automatic fallback."""

import io
from pathlib import Path
from typing import Optional
import requests

from src.logging_config import get_logger

logger = get_logger(component="VoiceCloneClient")


class VoiceCloningClient:
    """Client for remote open-source GPU voice cloning microservice (e.g. Hugging Face Spaces)."""

    def __init__(
        self,
        endpoint_url: Optional[str] = None,
        timeout_seconds: float = 10.0,
        default_reference_path: Optional[Path] = None,
    ) -> None:
        self.endpoint_url = endpoint_url.strip() if endpoint_url else None
        self.timeout_seconds = timeout_seconds
        self.default_reference_path = default_reference_path or Path("assets/voice_reference/cat_question_reference.wav")

    @property
    def is_configured(self) -> bool:
        """Returns True if a remote cloning endpoint URL is provided."""
        return bool(self.endpoint_url)

    def synthesize(
        self,
        text: str,
        output_path: Path,
        reference_audio_path: Optional[Path] = None,
        language: str = "hi",
    ) -> bool:
        """Sends text to remote cloning microservice. Returns True if successful, False on failure."""
        if not self.is_configured:
            logger.debug("Voice cloning endpoint not configured; skipping remote synthesis")
            return False

        ref_path = reference_audio_path or self.default_reference_path
        payload = {
            "text": text,
            "language": language,
        }

        try:
            logger.info(
                "Dispatching voice clone request to remote GPU microservice",
                extra_data={"endpoint": self.endpoint_url, "timeout": self.timeout_seconds}
            )

            # Check if reference audio file exists and can be attached
            files = {}
            if ref_path and ref_path.exists():
                files["reference_audio"] = open(ref_path, "rb")

            try:
                response = requests.post(
                    self.endpoint_url,
                    data=payload,
                    files=files if files else None,
                    timeout=self.timeout_seconds
                )
            finally:
                for f in files.values():
                    f.close()

            if response.status_code == 200 and len(response.content) > 1000:
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_bytes(response.content)
                logger.info(
                    "Remote voice clone successfully synthesized",
                    extra_data={"bytes": len(response.content), "destination": str(output_path)}
                )
                return True
            else:
                logger.warning(
                    f"Remote voice cloning returned status {response.status_code}; engaging fallback",
                    extra_data={"response_sample": response.text[:200] if response.text else ""}
                )
                return False

        except requests.Timeout:
            logger.warning(
                f"Voice cloning request timed out after {self.timeout_seconds}s; engaging fallback",
                extra_data={"endpoint": self.endpoint_url}
            )
            return False
        except Exception as e:
            logger.warning(
                "Voice cloning request encountered connection error; engaging fallback",
                extra_data={"error": str(e), "endpoint": self.endpoint_url}
            )
            return False

