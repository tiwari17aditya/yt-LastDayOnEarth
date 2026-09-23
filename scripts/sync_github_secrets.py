"""Automated script to sync project secrets directly with GitHub Actions via GitHub API."""

import base64
import json
import os
import subprocess
import sys
import urllib.request
from pathlib import Path
from typing import Dict, Optional

from dotenv import load_dotenv
from nacl import encoding, public

# Load .env
load_dotenv()


def get_git_credentials(host: str = "github.com") -> Optional[str]:
    """Retrieves GitHub token from local Git Credential Manager or environment."""
    token = os.getenv("GITHUB_TOKEN") or os.getenv("GH_TOKEN")
    if token:
        return token

    try:
        proc = subprocess.run(
            ["git", "credential", "fill"],
            input=f"protocol=https\nhost={host}\n",
            capture_output=True,
            text=True,
            check=True,
        )
        for line in proc.stdout.splitlines():
            if line.startswith("password="):
                return line.split("=", 1)[1].strip()
    except Exception as e:
        print(f"[WARN] Could not retrieve credentials from git credential manager: {e}")
    return None


def encrypt_secret(public_key_b64: str, secret_value: str) -> str:
    """Encrypts a plaintext secret using the repository's libsodium public key."""
    public_key = public.PublicKey(public_key_b64.encode("utf-8"), encoding.Base64Encoder)
    sealed_box = public.SealedBox(public_key)
    encrypted = sealed_box.encrypt(secret_value.encode("utf-8"))
    return base64.b64encode(encrypted).decode("utf-8")


def sync_secrets(
    repo_owner: str,
    repo_name: str,
    secrets: Dict[str, str],
    token: Optional[str] = None,
) -> bool:
    """Fetches repository public key and uploads all encrypted secrets to GitHub Actions."""
    token = token or get_git_credentials()
    if not token:
        print("[ERROR] No GitHub token found. Please set GITHUB_TOKEN environment variable.")
        return False

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "LDoE-Pipeline-Secrets-Sync",
    }

    # 1. Fetch Repo Public Key
    key_url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/actions/secrets/public-key"
    try:
        req = urllib.request.Request(key_url, headers=headers)
        with urllib.request.urlopen(req) as resp:
            key_data = json.loads(resp.read().decode("utf-8"))
            public_key_b64 = key_data["key"]
            key_id = key_data["key_id"]
            print(f"[OK] Fetched repository public key (Key ID: {key_id})")
    except Exception as e:
        print(f"[ERROR] Failed to fetch repository public key: {e}")
        return False

    # 2. Encrypt & Upload Each Secret
    success_count = 0
    for secret_name, secret_val in secrets.items():
        if not secret_val:
            print(f"[SKIP] Empty value for secret: {secret_name}")
            continue

        encrypted_val = encrypt_secret(public_key_b64, secret_val)
        put_url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/actions/secrets/{secret_name}"
        payload = json.dumps({"encrypted_value": encrypted_val, "key_id": key_id}).encode("utf-8")

        req = urllib.request.Request(
            put_url,
            data=payload,
            headers={**headers, "Content-Type": "application/json"},
            method="PUT",
        )
        try:
            with urllib.request.urlopen(req) as resp:
                if resp.status in (201, 204):
                    print(f" [SUCCESS] Synced secret: {secret_name}")
                    success_count += 1
                else:
                    print(f" [WARN] Response {resp.status} for {secret_name}")
        except Exception as e:
            print(f" [FAIL] Failed to upload {secret_name}: {e}")

    print("=" * 60)
    print(f"Successfully synced {success_count}/{len(secrets)} secrets to GitHub repository {repo_owner}/{repo_name}!")
    print("=" * 60)
    return success_count == len(secrets)


if __name__ == "__main__":
    owner = "tiwari17aditya"
    repo = "yt-LastDayOnEarth"

    # Read dynamically from .env or token file (no hardcoded secrets)
    secrets_to_sync = {
        "GCP_CLIENT_ID": os.getenv("GCP_CLIENT_ID", ""),
        "GCP_CLIENT_SECRET": os.getenv("GCP_CLIENT_SECRET", ""),
        "GCP_REFRESH_TOKEN": os.getenv("GCP_REFRESH_TOKEN", ""),
        "NOTIFICATION_RECIPIENTS": os.getenv("NOTIFICATION_RECIPIENTS", "addytiwari3@gmail.com"),
    }

    print("=" * 60)
    print(f"Syncing {len(secrets_to_sync)} secrets to GitHub Actions ({owner}/{repo})...")
    print("=" * 60)
    ok = sync_secrets(owner, repo, secrets_to_sync)
    if not ok:
        sys.exit(1)
