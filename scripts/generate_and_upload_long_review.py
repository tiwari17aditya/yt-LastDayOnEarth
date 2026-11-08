#!/usr/bin/env python3
"""Generates full 15.5-minute Style 2 Casual Walkthrough video with continuous AI commentary,
low soothing ambient background music, and clean YouTube chapters without debug text."""

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
from src.audio.selector import AudioMixer
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

    temp_dir = Path("temp/long_review_continuous")
    temp_dir.mkdir(parents=True, exist_ok=True)
    output_video = Path("output/Last_Day_On_Earth_Continuous_Commentary_15Min_Review.mp4")
    output_video.parent.mkdir(parents=True, exist_ok=True)

    # 1. Probe duration
    logger.info("Probing video duration...")
    processor = VideoProcessor(output_dir=output_video.parent)
    duration = processor.get_video_duration(input_video)
    logger.info(f"Input video duration: {duration:.2f} seconds ({duration/60.0:.2f} minutes)")

    # 2. Generate Commentary Script & Synthesize Voice Audio Track
    logger.info("Step 1/4: Synthesizing continuous Style 2 Casual AI Commentary (GuyNeural, ~25s intervals)...")
    commentary_engine = CommentaryEngine(temp_dir=temp_dir / "commentary")

    # Generate continuous script with 25.0s min cue interval
    cues = commentary_engine.generate_script(
        duration=duration,
        episode_number=99,
        persona=CommentaryPersona.CASUAL,
        min_cue_interval=25.0,
    )
    logger.info(f"Generated {len(cues)} continuous commentary dialogue cues spaced across timeline:")
    for idx, c in enumerate(cues):
        mins = int(c.start_time // 60)
        secs = int(c.start_time % 60)
        logger.info(f"  Cue #{idx+1:02d} [{mins:02d}:{secs:02d}] {c.topic}: {c.text[:55]}...")

    # Synthesize all cues
    commentary_engine.synthesize_all_cues(cues=cues, persona=CommentaryPersona.CASUAL)

    # Assemble timeline track
    raw_timeline = temp_dir / "raw_timeline_voice_continuous.m4a"
    commentary_engine.build_timeline_commentary_track(
        cues=cues,
        total_duration=duration,
        output_path=raw_timeline,
    )

    # 3. Create Low-Volume Ambient Background Music Loop & Duck Behind Voice
    logger.info("Step 2/4: Generating soothing ambient BGM loop and mixing with sidechain ducking...")
    audio_mixer = AudioMixer()
    bgm_loop_path = temp_dir / "ambient_bgm_loop_15min.m4a"
    audio_mixer.create_random_loop_sequence(target_duration=duration, output_path=bgm_loop_path)

    mixed_audio_track = temp_dir / "master_commentary_ducked_bgm_15min.m4a"
    commentary_engine.mix_commentary_with_bgm(
        commentary_audio=raw_timeline,
        bgm_audio=bgm_loop_path,
        output_audio_path=mixed_audio_track,
        ducking_ratio=4.0,
        voice_volume_boost_db="+3dB",
        bgm_volume_db="-22dB",
        duration=duration,
    )
    logger.info(f"Master ducked commentary audio track ready: {mixed_audio_track}")

    # 4. Composite Video Render (Fast stream-copy)
    logger.info("Step 3/4: Muxing 15.5-minute video with continuous commentary & ambient BGM track...")
    render_start = time.time()
    commentary_engine.render_commentary_video(
        video_input=input_video,
        mixed_audio_input=mixed_audio_track,
        output_video_path=output_video,
        duration=duration,
    )
    render_time = time.time() - render_start
    file_size_mb = output_video.stat().st_size / (1024 * 1024)
    logger.info(f"Video muxed successfully in {render_time:.1f}s ({file_size_mb:.1f} MB): {output_video}")

    # 5. Upload to YouTube as Unlisted
    logger.info("Step 4/4: Uploading review video to YouTube as Unlisted...")
    title = "Last Day on Earth: Survival — Full 15-Min Continuous AI Voice Walkthrough (Review)"

    # Build description with concise, clickable chapter headings
    ts_lines = []
    for idx, c in enumerate(cues):
        if idx == 0:
            ts_lines.append(f"00:00 - {c.topic or 'Introduction & Base Prep'}")
        else:
            mins = int(c.start_time // 60)
            secs = int(c.start_time % 60)
            ts_lines.append(f"{mins:02d}:{secs:02d} - {c.topic or 'Survival Strategy'}")
    timestamps_text = "\n".join(ts_lines)

    description = (
        "Last Day on Earth: Survival — Full 15-Minute Gameplay Walkthrough featuring interactive AI voice companion commentary.\n\n"
        "CHAPTERS & WALKTHROUGH HIGHLIGHTS:\n"
        f"{timestamps_text}\n\n"
        "Enjoying the journey? Drop a like, subscribe to follow the survival progression, and let us know your favorite base setup in the comments!\n\n"
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

    # 6. Safety Cleanup: Preserve series_tracker.json & keep playlist clean
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
    print("CONTINUOUS CASUAL COMMENTARY VIDEO UPLOADED SUCCESSFULLY!")
    print("=" * 65)
    print(f"Video Title   : {title}")
    print(f"Duration      : {duration/60.0:.2f} minutes ({duration:.1f}s)")
    print(f"Voice Style   : Style 2 - Casual Companion (en-US-GuyNeural)")
    print(f"Audio Mix     : Sidechain Ducked Ambient BGM (-22dB) + Normalized Voice (+3dB, -16 LUFS)")
    print(f"Chapters Count: {len(cues)} clean chapter headings")
    print(f"Privacy Status: UNLISTED (Private for Creator Review)")
    print(f"Review URL    : {upload_url}")
    print("=" * 65 + "\n")


if __name__ == "__main__":
    main()
