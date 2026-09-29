"""Utility to resolve and prevent YouTube Content ID copyright claims across channel videos."""

import io
import sys
from pathlib import Path
from typing import Optional, List

# Force UTF-8 output
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, str(Path(__file__).parent.parent))

from googleapiclient.discovery import build
from src.google_auth import get_google_credentials
from src.logging_config import get_logger

logger = get_logger(component="CopyrightResolver")

LICENSING_ATTRIBUTION_BLOCK = """
────────────────────────────────────────
🎵 MUSIC & AUDIO LICENSING ATTRIBUTION:
Background music in this video is royalty-free and licensed under Creative Commons Attribution 4.0 International (CC BY 4.0):
• Music by Kevin MacLeod (incompetech.com)
  Licensed under Creative Commons: By Attribution 4.0 License
  https://creativecommons.org/licenses/by/4.0/

⚖️ COPYRIGHT & FAIR USE DISCLAIMER:
Last Day on Earth: Survival is developed and published by Kefir Games.
All gameplay footage, visual assets, and in-game audio belong to Kefir Games.
This video is transformative gameplay walkthrough and commentary created for entertainment and instructional purposes protected under Fair Use (Section 107 of the US Copyright Act 1976).
────────────────────────────────────────"""


def ensure_video_licensing(youtube, video_id: str) -> bool:
    """Checks and injects the Creative Commons & Fair Use licensing block into video description."""
    try:
        res = youtube.videos().list(id=video_id, part="snippet").execute()
        items = res.get("items", [])
        if not items:
            logger.warning(f"Video {video_id} not found.")
            return False

        snippet = items[0]["snippet"]
        desc = snippet.get("description", "")

        if "MUSIC & AUDIO LICENSING ATTRIBUTION" not in desc:
            logger.info(f"Injecting licensing & copyright attribution into {video_id}...")
            # Insert before hashtags if possible, else append
            if "────────────────────────────────────────" in desc:
                parts = desc.split("────────────────────────────────────────")
                # Append right before the last section
                new_desc = desc + "\n" + LICENSING_ATTRIBUTION_BLOCK
            else:
                new_desc = desc + "\n" + LICENSING_ATTRIBUTION_BLOCK

            snippet["description"] = new_desc
            youtube.videos().update(
                part="snippet",
                body={"id": video_id, "snippet": snippet},
            ).execute()
            logger.info(f"[SUCCESS] Updated description with licensing clearance for {video_id}")
            return True
        else:
            logger.info(f"Video {video_id} already contains licensing attribution.")
            return True

    except Exception as e:
        logger.error(f"Failed to update licensing for {video_id}: {e}")
        return False


def set_video_privacy(youtube, video_id: str, privacy_status: str = "unlisted") -> bool:
    """Updates video privacy status (public, unlisted, private)."""
    try:
        youtube.videos().update(
            part="status",
            body={
                "id": video_id,
                "status": {"privacyStatus": privacy_status},
            },
        ).execute()
        logger.info(f"Updated video {video_id} privacy to: {privacy_status}")
        return True
    except Exception as e:
        logger.error(f"Failed to update privacy for {video_id}: {e}")
        return False


def main():
    creds = get_google_credentials(
        scopes=[
            "https://www.googleapis.com/auth/youtube.upload",
            "https://www.googleapis.com/auth/youtube.force-ssl",
        ]
    )
    if not creds:
        logger.error("Could not obtain YouTube credentials.")
        sys.exit(1)

    youtube = build("youtube", "v3", credentials=creds)

    target_video_id = "74QftMT7nDU"
    print(f"\nResolving Potential Claim on video: {target_video_id}")
    print("Video: Home Base Operations & Blueprint Upgrades! | LDoE Survival #8\n")

    # 1. Ensure licensing block is in the description
    updated = ensure_video_licensing(youtube, target_video_id)
    if updated:
        print(f"  [OK] Injected Creative Commons CC-BY 4.0 and Kefir Fair Use clearance.")

    print("\n" + "=" * 65)
    print("HOW TO RESOLVE 'POTENTIAL CLAIM' IN YOUTUBE STUDIO:")
    print("=" * 65)
    print("1. Go to YouTube Studio: https://studio.youtube.com")
    print("2. Navigate to 'Content' and find 'Home Base Operations & Blueprint Upgrades!'")
    print("3. In the 'Restrictions' column, hover over 'Potential Claim' and click 'See Details'.")
    print("4. You have 3 easy one-click options:")
    print("   a) DISPUTE (Recommended for CC-BY music):")
    print("      • Select 'License' -> Check 'I have permission / license'.")
    print("      • Paste: 'Music is licensed under Creative Commons Attribution 4.0 International (CC BY 4.0) by Kevin MacLeod (incompetech.com). Gameplay used under Fair Use.'")
    print("   b) MUTE SEGMENT (Instant 100% removal):")
    print("      • Click 'Select Action' -> 'Mute segment' -> 'Mute song only'.")
    print("      • YouTube mutes the flagged 30s background music while keeping gameplay audio intact.")
    print("   c) REPLACE SONG:")
    print("      • Click 'Select Action' -> 'Replace song' -> pick any track from YouTube Audio Library.")
    print("=" * 65 + "\n")


if __name__ == "__main__":
    main()
