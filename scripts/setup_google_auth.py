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

    client_secrets_path = Path("config/client_secrets.json")
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
    print("\n" + "=" * 70)
    print("  GITHUB ACTIONS SECRETS CONFIGURATION")
    print("=" * 70)
    print("Copy and paste these 3 secret values into your GitHub Repository:")
    print("Settings -> Secrets and variables -> Actions -> New repository secret\n")
    print(f"GCP_CLIENT_ID:     {creds.client_id}")
    print(f"GCP_CLIENT_SECRET: {creds.client_secret}")
    print(f"GCP_REFRESH_TOKEN: {creds.refresh_token}")
    print("=" * 70)


if __name__ == "__main__":
    run_auth_flow()
