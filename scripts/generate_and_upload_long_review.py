#!/usr/bin/env python3
"""Generates full 15.5-minute Style 2 Casual Walkthrough video and uploads to YouTube as Unlisted for review."""

import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.logging_config import get_logger
from src.audio.commentary_engine import CommentaryEngine, CommentaryPersona
from src.processor.video_processor import VideoProcessor
from src.publisher.youtube_client import VideoPublishMetadata, YouTubeClient
from src.google_auth import get_google_credentials
from googleapiclient.discovery import build

logger = get_logger(component="LongReviewGenerator")

# Ensure UTF-8 output encoding on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def main():
    input_video = Path("temp/ep99_15min_input.mp4")
    if not input_video.exists():
        logger.error(f"Input video not found: {input_video}")
        sys.exit(1)

    temp_dir = Path("temp/long_review")
    temp_dir.mkdir(parents=True, exist_ok=True)
    output_video = Path("output/Last_Day_On_Earth_Casual_Walkthrough_15Min_Review.mp4")
    output_video.parent.mkdir(parents=True, exist_ok=True)

    # 1. Probe duration
    logger.info("Probing video duration...")
    processor = VideoProcessor(output_dir=output_video.parent)
    duration = processor.get_video_duration(input_video)
    logger.info(f"Input video duration: {duration:.2f} seconds ({duration/60.0:.2f} minutes)")

    # 2. Generate Commentary Script & Synthesize Pure Voice Audio Track
    logger.info("Step 1/3: Synthesizing full 15.5-minute Style 2 Casual AI Commentary (GuyNeural)...")
    commentary_engine = CommentaryEngine(temp_dir=temp_dir / "commentary")

    master_commentary_track = temp_dir / "master_casual_commentary_15min.m4a"

    # Generate full timeline script
    cues = commentary_engine.generate_script(
        duration=duration,
        episode_number=99,
        persona=CommentaryPersona.CASUAL,
    )
    logger.info(f"Generated {len(cues)} commentary dialogue cues spaced across timeline:")
    for idx, c in enumerate(cues):
        mins = int(c.start_time // 60)
        secs = int(c.start_time % 60)
        logger.info(f"  Cue #{idx+1:02d} [{mins:02d}:{secs:02d}] {c.text[:70]}...")

    # Check if already synthesized
    if master_commentary_track.exists() and master_commentary_track.stat().st_size > 500 * 1024:
        logger.info(f"Using pre-synthesized master commentary audio: {master_commentary_track}")
    else:
        # Synthesize all cues
        commentary_engine.synthesize_all_cues(cues=cues, persona=CommentaryPersona.CASUAL)

        # Assemble timeline track
        raw_timeline = temp_dir / "raw_timeline_voice.m4a"
        commentary_engine.build_timeline_commentary_track(
            cues=cues,
            total_duration=duration,
            output_path=raw_timeline,
        )

        # Normalize pure voice audio to broadcast standards (-16 LUFS, +3dB boost)
        commentary_engine.normalize_pure_voice_track(
            raw_voice_audio=raw_timeline,
            output_audio_path=master_commentary_track,
            volume_boost_db="+3dB",
        )
        logger.info(f"Master pure voice commentary track ready: {master_commentary_track}")

    # 3. Composite Video Render (Fast stream-copy or check existing)
    if output_video.exists() and output_video.stat().st_size > 50 * 1024 * 1024:
        logger.info(f"Using pre-rendered composite video: {output_video} ({output_video.stat().st_size / (1024*1024):.1f} MB)")
    else:
        logger.info("Step 2/3: Muxing 15.5-minute video with pure voice commentary track...")
        render_start = time.time()
        commentary_engine.render_commentary_video(
            video_input=input_video,
            mixed_audio_input=master_commentary_track,
            output_video_path=output_video,
        )
        render_time = time.time() - render_start
        file_size_mb = output_video.stat().st_size / (1024 * 1024)
        logger.info(f"Video muxed successfully in {render_time:.1f}s ({file_size_mb:.1f} MB): {output_video}")

    # 4. Upload to YouTube as Unlisted
    logger.info("Step 3/3: Uploading long review video to YouTube as Unlisted...")
    title = "Last Day on Earth: Survival — Full 15-Min Casual AI Voice Walkthrough (Review)"

    # Build description with clickable timestamps
    ts_lines = []
    for c in cues:
        mins = int(c.start_time // 60)
        secs = int(c.start_time % 60)
        ts_lines.append(f"{mins:02d}:{secs:02d} - {c.text[:65]}...")
    timestamps_text = "\n".join(ts_lines)

    description = (
        "Full 15-Minute Gameplay Walkthrough featuring Style 2 (Casual AI Voice Commentary Companion).\n\n"
        "TIMESTAMPS & COMMENTARY TOPICS:\n"
        f"{timestamps_text}\n\n"
        "AUDIO & PIPELINE CONFIGURATION:\n"
        "- Voice Model: en-US-GuyNeural (Casual, friendly walkthrough style)\n"
        "- Pure Spoken Voice Track (Zero added BGM per creator preference)\n"
        "- Broadcast Normalization: -16 LUFS, +3dB boost, true peak limiter -1.5dB\n"
        "- Sleek 1-sec Action Subtitle Overlays\n"
        "- Full 1080p 60 FPS Composite Render\n\n"
        "This is an unlisted full-length review video for channel development and testing."
    )

    metadata = VideoPublishMetadata(
        title=title,
        description=description,
        tags=["Last Day on Earth", "LDoE", "Commentary", "AI Commentary", "Gaming", "Walkthrough", "Survival", "LDoE Guide"],
        category_id="20",
        privacy_status="unlisted",
    )

    client = YouTubeClient()
    upload_url = client.upload_video(output_video, metadata)

    # 5. Safety Cleanup: Preserve series_tracker.json & keep playlist clean
    logger.info("Performing safety cleanups on series_tracker.json and public playlist...")
    try:
        tracker_file = Path("data/series_tracker.json")
        if tracker_file.exists():
            with open(tracker_file, "r", encoding="utf-8") as f:
                tracker = json.load(f)

            # Extract video ID
            vid_id = ""
            if "youtu.be/" in upload_url:
                vid_id = upload_url.split("youtu.be/")[-1].split("?")[0]
            elif "v=" in upload_url:
                vid_id = upload_url.split("v=")[-1].split("&")[0]

            # Remove review video from completed episodes
            tracker["completed_episodes"] = [
                ep for ep in tracker.get("completed_episodes", [])
                if ep.get("video_id") != vid_id
            ]
            tracker["current_episode"] = 111

            with open(tracker_file, "w", encoding="utf-8") as f:
                json.dump(tracker, f, indent=2)
            logger.info("Restored series_tracker.json: current_episode is 111.")

            # Remove from playlist PLJPzVNVZwaGY if added
            if vid_id:
                try:
                    creds = get_google_credentials()
                    youtube = build("youtube", "v3", credentials=creds)
                    playlist_id = "PLJPzVNVZwaGY"
                    req = youtube.playlistItems().list(part="id,snippet", playlistId=playlist_id, maxResults=50)
                    resp = req.execute()
                    for item in resp.get("items", []):
                        if item.get("snippet", {}).get("resourceId", {}).get("videoId") == vid_id:
                            youtube.playlistItems().delete(id=item["id"]).execute()
                            logger.info(f"Removed unlisted review video {vid_id} from public playlist {playlist_id}.")
                except Exception as ple:
                    logger.warning(f"Playlist cleanup skipped: {ple}")

    except Exception as e:
        logger.warning(f"Error during safety cleanup: {e}")

    print("\n" + "=" * 65)
    print("FULL 15-MINUTE CASUAL COMMENTARY VIDEO UPLOADED SUCCESSFULLY!")
    print("=" * 65)
    print(f"Video Title   : {title}")
    print(f"Duration      : {duration/60.0:.2f} minutes ({duration:.1f}s)")
    print(f"Voice Style   : Style 2 - Casual Walkthrough (en-US-GuyNeural)")
    print(f"Audio Mix     : Pure Voice (Zero BGM, +3dB Boost, -16 LUFS)")
    print(f"Privacy Status: UNLISTED (Private for Creator Review)")
    print(f"Review URL    : {upload_url}")
    print("=" * 65 + "\n")


if __name__ == "__main__":
    main()
