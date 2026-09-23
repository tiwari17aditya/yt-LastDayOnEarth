"""Interactive setup helper to authorize Google Drive, YouTube, and Gmail APIs.

Generates unified OAuth2 credentials and outputs GitHub Secrets format.
"""

import json
import os
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials

SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.force-ssl",
    "https://www.googleapis.com/auth/gmail.send",
]


def run_auth_flow() -> None:
    print("=" * 70)
    print("  Last Day on Earth Pipeline — Unified Google OAuth Setup")
    print("=" * 70)
    print("This script configures access for:")
    print(" 1. Google Drive API (Reading Input, moving to Processed)")
    print(" 2. YouTube Data API v3 (Uploading video)")
    print(" 3. Gmail API (Sending upload notifications)")
    print("=" * 70)

    # Auto-detect config/client_secrets.json or downloaded Google client_secret_*.json
    candidate_secrets = list(Path("config").glob("client_secret*.json"))
    client_secrets_path = candidate_secrets[0] if candidate_secrets else Path("config/client_secrets.json")
    client_id = os.getenv("GCP_CLIENT_ID")
    client_secret = os.getenv("GCP_CLIENT_SECRET")

    flow = None

    if client_secrets_path.exists():
        print(f"\n[OK] Found client secrets file at {client_secrets_path}")
        flow = InstalledAppFlow.from_client_secrets_file(str(client_secrets_path), SCOPES)
    elif client_id and client_secret:
        print("\n[OK] Found GCP_CLIENT_ID and GCP_CLIENT_SECRET in environment")
        client_config = {
            "installed": {
                "client_id": client_id,
                "client_secret": client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": ["http://localhost"],
            }
        }
        flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
    else:
        print("\n[INFO] Enter your OAuth 2.0 Desktop Client credentials from Google Cloud Console:")
        client_id = input("Client ID: ").strip()
        client_secret = input("Client Secret: ").strip()

        if not client_id or not client_secret:
            print("[ERROR] Client ID and Client Secret are required.")
            sys.exit(1)

        client_config = {
            "installed": {
                "client_id": client_id,
                "client_secret": client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": ["http://localhost"],
            }
        }
        flow = InstalledAppFlow.from_client_config(client_config, SCOPES)

    print("\n[ACTION] Launching browser for one-time consent approval...")
    creds = flow.run_local_server(port=0)

    # Save to config/token.json
    token_path = Path("config/token.json")
    token_path.parent.mkdir(parents=True, exist_ok=True)
    with open(token_path, "w", encoding="utf-8") as f:
        f.write(creds.to_json())

    print(f"\n[SUCCESS] Token saved locally to {token_path}")

    # Auto-update .env if it exists
    env_path = Path(".env")
    if env_path.exists():
        content = env_path.read_text(encoding="utf-8")
        if creds.refresh_token:
            import re
            content = re.sub(
                r'GCP_REFRESH_TOKEN=.*',
                f'GCP_REFRESH_TOKEN="{creds.refresh_token}"',
                content,
            )
            env_path.write_text(content, encoding="utf-8")
            print("[SUCCESS] Updated GCP_REFRESH_TOKEN in .env")

    # Automatically sync secrets to GitHub Actions
    try:
        from scripts.sync_github_secrets import sync_secrets
        owner = "tiwari17aditya"
        repo = "yt-LastDayOnEarth"
        secrets_to_sync = {
            "GCP_CLIENT_ID": creds.client_id or os.getenv("GCP_CLIENT_ID", ""),
            "GCP_CLIENT_SECRET": creds.client_secret or os.getenv("GCP_CLIENT_SECRET", ""),
            "GCP_REFRESH_TOKEN": creds.refresh_token,
            "NOTIFICATION_RECIPIENTS": os.getenv("NOTIFICATION_RECIPIENTS", "addytiwari3@gmail.com"),
        }
        print("\n[ACTION] Auto-syncing newly generated credentials to GitHub Actions...")
        sync_secrets(owner, repo, secrets_to_sync)
    except Exception as e:
        print(f"[WARN] Automatic GitHub Secrets sync skipped: {e}")

    print("\n" + "=" * 70)
    print("  AUTHENTICATION & REPOSITORY SYNC COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    run_auth_flow()
