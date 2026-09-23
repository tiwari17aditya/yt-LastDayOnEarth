"""Unified Google Cloud authentication helper for Drive, YouTube, and Gmail APIs."""

import os
from pathlib import Path
from typing import List, Optional
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google.oauth2 import service_account

from src.logging_config import get_logger
from src.exceptions import IngestionError

logger = get_logger(component="GoogleAuth")

DEFAULT_SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.force-ssl",
    "https://www.googleapis.com/auth/gmail.send",
]


def get_google_credentials(
    scopes: Optional[List[str]] = None,
    client_id: Optional[str] = None,
    client_secret: Optional[str] = None,
    refresh_token: Optional[str] = None,
    token_file: Optional[Path] = None,
    service_account_file: Optional[Path] = None,
) -> Optional[Credentials]:
    """Resolves and returns valid Google API Credentials.

    Checks sources in order:
    1. Direct Refresh Token (Environment Variables / Parameters)
    2. Local Authorized User Token File (e.g. config/token.json)
    3. Service Account Credentials File (if present)
    """
    scopes = scopes or DEFAULT_SCOPES

    # 1. Check direct Refresh Token (Ideal for GitHub Actions secrets)
    client_id = client_id or os.getenv("GCP_CLIENT_ID")
    client_secret = client_secret or os.getenv("GCP_CLIENT_SECRET")
    refresh_token = refresh_token or os.getenv("GCP_REFRESH_TOKEN") or os.getenv("GDRIVE_REFRESH_TOKEN")

    if client_id and client_secret and refresh_token:
        try:
            logger.info("Initializing credentials via direct OAuth2 Refresh Token")
            creds = Credentials(
                token=None,
                refresh_token=refresh_token,
                token_uri="https://oauth2.googleapis.com/token",
                client_id=client_id,
                client_secret=client_secret,
                scopes=scopes,
            )
            creds.refresh(Request())
            return creds
        except Exception as e:
            logger.error(f"Failed to refresh OAuth token: {e}")
            raise IngestionError(
                operation="auth_refresh",
                root_cause=str(e),
                recovery_action="Verify GCP_CLIENT_ID, GCP_CLIENT_SECRET, and GCP_REFRESH_TOKEN in .env or secrets.",
            )

    # 2. Check local token file (config/token.json)
    token_path = token_file or Path(os.getenv("GCP_TOKEN_FILE", "config/token.json"))
    if token_path.exists():
        try:
            logger.info("Initializing credentials from token file", extra_data={"path": str(token_path)})
            creds = Credentials.from_authorized_user_file(str(token_path), scopes)
            if creds.expired and creds.refresh_token:
                creds.refresh(Request())
            return creds
        except Exception as e:
            logger.warning(f"Failed to load credentials from token file: {e}")

    # 3. Check service account file
    sa_path = service_account_file or Path(os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "config/credentials.json"))
    if sa_path.exists():
        try:
            logger.info("Initializing credentials from Service Account", extra_data={"path": str(sa_path)})
            return service_account.Credentials.from_service_account_file(str(sa_path), scopes=scopes)
        except Exception as e:
            logger.warning(f"Failed to load service account: {e}")

    logger.warning("No valid Google credentials configured (GCP_CLIENT_ID/GCP_REFRESH_TOKEN or config/token.json)")
    return None
