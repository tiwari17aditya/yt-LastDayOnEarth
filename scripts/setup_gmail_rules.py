"""Automated Gmail Label and Filter Setup for Last Day on Earth Pipeline.

This script uses the Gmail API to automatically:
1. Create the parent label 'lastDayOnEarth-yt'
2. Create nested sub-labels:
   - 'lastDayOnEarth-yt/Success'
   - 'lastDayOnEarth-yt/Weekly Reports'
   - 'lastDayOnEarth-yt/Monthly Reports'
   - 'lastDayOnEarth-yt/Alerts'
3. Create Gmail filters to automatically categorize incoming pipeline emails:
   - Upload success notifications -> 'lastDayOnEarth-yt/Success'
   - Weekly summary reports -> 'lastDayOnEarth-yt/Weekly Reports'
   - Monthly summary reports -> 'lastDayOnEarth-yt/Monthly Reports'
   - Critical pipeline failures -> 'lastDayOnEarth-yt/Alerts'
"""

import json
import os
import re
import sys
from pathlib import Path
from typing import Dict, Any, List

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.force-ssl",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.labels",
    "https://www.googleapis.com/auth/gmail.settings.basic",
]

TARGET_LABELS = [
    "lastDayOnEarth-yt",
    "lastDayOnEarth-yt/Success",
    "lastDayOnEarth-yt/Weekly Reports",
    "lastDayOnEarth-yt/Monthly Reports",
    "lastDayOnEarth-yt/Alerts",
]


def get_credentials() -> Credentials:
    """Load existing token or run OAuth flow if insufficient scopes."""
    token_path = Path("config/token.json")
    creds = None

    if token_path.exists():
        try:
            with open(token_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            existing_scopes = set(data.get("scopes", []))
            required_scopes = set(SCOPES)

            # Check if all required scopes are present
            if required_scopes.issubset(existing_scopes):
                creds = Credentials.from_authorized_user_info(data, SCOPES)
        except Exception:
            creds = None

    if not creds or not creds.valid:
        print("\n[INFO] Gmail Settings & Labels authorization required.")
        candidate_secrets = list(Path("config").glob("client_secret*.json"))
        client_secrets_path = candidate_secrets[0] if candidate_secrets else Path("config/client_secrets.json")

        if client_secrets_path.exists():
            print(f"[OK] Using client secret from: {client_secrets_path}")
            flow = InstalledAppFlow.from_client_secrets_file(str(client_secrets_path), SCOPES)
        else:
            client_id = os.getenv("GCP_CLIENT_ID")
            client_secret = os.getenv("GCP_CLIENT_SECRET")
            if not client_id or not client_secret:
                print("[ERROR] No client secret file or GCP_CLIENT_ID / GCP_CLIENT_SECRET found.")
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

        print("[ACTION] Opening browser for one-click approval...")
        creds = flow.run_local_server(port=0)

        # Save updated token
        token_path.parent.mkdir(parents=True, exist_ok=True)
        with open(token_path, "w", encoding="utf-8") as f:
            f.write(creds.to_json())
        print(f"[SUCCESS] Updated token saved to {token_path}")

        # Update .env refresh token
        env_path = Path(".env")
        if env_path.exists() and creds.refresh_token:
            content = env_path.read_text(encoding="utf-8")
            content = re.sub(
                r'GCP_REFRESH_TOKEN=.*',
                f'GCP_REFRESH_TOKEN="{creds.refresh_token}"',
                content,
            )
            env_path.write_text(content, encoding="utf-8")

    return creds


def ensure_labels(service: Any) -> Dict[str, str]:
    """Ensure all target labels exist in Gmail, returning a map of name -> ID."""
    print("\n--- Step 1: Checking and Creating Labels ---")
    results = service.users().labels().list(userId="me").execute()
    existing = {l["name"]: l["id"] for l in results.get("labels", [])}
    
    label_map = {}
    for label_name in TARGET_LABELS:
        if label_name in existing:
            print(f" [EXISTS] Label: {label_name} (ID: {existing[label_name]})")
            label_map[label_name] = existing[label_name]
        else:
            body = {
                "name": label_name,
                "labelListVisibility": "labelShow",
                "messageListVisibility": "show",
            }
            created = service.users().labels().create(userId="me", body=body).execute()
            print(f" [CREATED] Label: {label_name} (ID: {created['id']})")
            label_map[label_name] = created["id"]
            existing[label_name] = created["id"]

    return label_map


def ensure_filters(service: Any, label_map: Dict[str, str]) -> None:
    """Create the filters for Success, Weekly, Monthly, and Alerts."""
    print("\n--- Step 2: Creating Mail Filters ---")
    
    # Get existing filters
    existing_filters_resp = service.users().settings().filters().list(userId="me").execute()
    existing_filters = existing_filters_resp.get("filter", [])

    filters_to_create = [
        {
            "name": "Success & Published Notifications",
            "criteria": {
                "subject": '[SUCCESS] OR "Published to YouTube"',
                "query": '"Last Day on Earth" OR LastDayOnEarth',
            },
            "action": {
                "addLabelIds": [label_map["lastDayOnEarth-yt/Success"]],
                "removeLabelIds": ["SPAM"],
            },
        },
        {
            "name": "Weekly Reports",
            "criteria": {
                "subject": '"Weekly Report" OR "[WEEKLY REPORT]"',
                "query": '"Last Day on Earth" OR LastDayOnEarth',
            },
            "action": {
                "addLabelIds": [label_map["lastDayOnEarth-yt/Weekly Reports"]],
                "removeLabelIds": ["SPAM"],
            },
        },
        {
            "name": "Monthly Reports",
            "criteria": {
                "subject": '"Monthly Report" OR "[MONTHLY REPORT]"',
                "query": '"Last Day on Earth" OR LastDayOnEarth',
            },
            "action": {
                "addLabelIds": [label_map["lastDayOnEarth-yt/Monthly Reports"]],
                "removeLabelIds": ["SPAM"],
            },
        },
        {
            "name": "Pipeline Alerts & Failures",
            "criteria": {
                "subject": '[ALERT] OR [FAILED] OR "Pipeline Failed"',
                "query": '"Last Day on Earth" OR LastDayOnEarth',
            },
            "action": {
                "addLabelIds": [label_map["lastDayOnEarth-yt/Alerts"]],
                "removeLabelIds": ["SPAM"],
            },
        },
    ]

    for f_def in filters_to_create:
        # Check if identical query already exists
        target_subject = f_def["criteria"].get("subject", "")
        already_exists = False
        for ef in existing_filters:
            crit = ef.get("criteria", {})
            if crit.get("subject") == target_subject:
                already_exists = True
                break

        if already_exists:
            print(f" [EXISTS] Filter: {f_def['name']} (Subject: {target_subject})")
            continue

        try:
            body = {
                "criteria": f_def["criteria"],
                "action": f_def["action"],
            }
            res = service.users().settings().filters().create(userId="me", body=body).execute()
            print(f" [CREATED] Filter: {f_def['name']} (ID: {res.get('id')})")
        except HttpError as err:
            print(f" [ERROR] Could not create filter {f_def['name']}: {err}")


def main() -> None:
    print("=" * 65)
    print("  Last Day on Earth - Automated Gmail Rules & Folders Setup")
    print("=" * 65)
    creds = get_credentials()
    service = build("gmail", "v1", credentials=creds)

    label_map = ensure_labels(service)
    ensure_filters(service, label_map)

    print("\n" + "=" * 65)
    print("🎉 All Gmail labels and filters successfully configured!")
    print("=" * 65)


if __name__ == "__main__":
    main()
