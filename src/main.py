"""Main entry point and orchestrator for the Last Day on Earth video pipeline."""

import argparse
import hashlib
import sys
from pathlib import Path
from datetime import datetime

from src.config import get_settings
from src.logging_config import get_logger
from src.exceptions import PipelineError, IngestionError

def calculate_file_md5(file_path: Path) -> str:
    """Calculates MD5 hash for a local file to ensure reliable duplicate detection."""
    hasher = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()
from src.privacy.detector import PrivacyDetector
from src.subtitles.event_analyzer import SubtitleGenerator
from src.audio.selector import AudioMixer
from src.processor.video_processor import VideoProcessor
from src.publisher.youtube_client import YouTubeClient
from src.notifications.email_client import EmailNotifier
from src.notifications.gmail_client import GmailNotifier
from src.storage.history_tracker import HistoryTracker
from src.ingestion.drive_client import GoogleDriveClient

logger = get_logger(component="PipelineOrchestrator")


def get_notifier(settings):
    """Instantiates GmailNotifier if configured, with fallback to SMTP EmailNotifier."""
    recipients = settings.gmail.recipients or settings.smtp.recipients
    try:
        gmail_notifier = GmailNotifier(recipients=recipients, sender=settings.gmail.sender)
        return gmail_notifier
    except Exception as e:
        logger.warning(f"Falling back to SMTP notifier: {e}")
        return EmailNotifier(
            host=settings.smtp.host,
            port=settings.smtp.port,
            user=settings.smtp.user,
            password=settings.smtp.password,
            recipients=recipients,
        )


def run_pipeline(input_video_path: Path, local_only: bool = True, force: bool = False) -> Path:
    """Executes the complete video processing workflow for a single video file."""
    settings = get_settings()
    logger.info("Initiating video processing workflow", extra_data={"input": str(input_video_path)})

    if not input_video_path.exists():
        logger.error(f"Input file not found: {input_video_path}")
        sys.exit(1)

    # Initialize subsystems
    privacy_guard = PrivacyDetector()
    subtitle_engine = SubtitleGenerator(gemini_api_key=settings.gemini.api_key or "")
    audio_mixer = AudioMixer(library_path=settings.processing.music_library_file)
    processor = VideoProcessor(output_dir=settings.processing.output_dir)
    publisher = YouTubeClient(
        client_secrets_file=settings.youtube.client_secrets_file,
        token_file=settings.youtube.token_file,
        privacy_status=settings.youtube.privacy_status,
        playlist_title=settings.youtube.playlist_title,
    )
    notifier = get_notifier(settings)
    tracker = HistoryTracker(history_file=settings.processing.history_file)

    # Duplicate input detection
    file_md5 = calculate_file_md5(input_video_path)
    if not force and tracker.is_duplicate(input_video_path.name, md5_checksum=file_md5):
        logger.warning(
            f"Input video '{input_video_path.name}' (MD5: {file_md5}) was already successfully processed. "
            f"Skipping duplicate execution. (Use --force to reprocess)"
        )
        output_path = processor.get_output_path(input_video_path.name)
        return output_path

    try:
        # Step 1: Privacy Protection (Redacting sensitive popups, preserving username & chat)
        logger.info("Step 1/6: Scanning for sensitive personal data")
        bboxes = privacy_guard.scan_video(input_video_path)
        blur_filter = privacy_guard.generate_ffmpeg_blur_filter(bboxes)
        logger.info(f"Generated privacy filter: {blur_filter}")

        # Step 2: Gameplay Context & Subtitle Generation (Sleek 1-sec action cues)
        logger.info("Step 2/6: Analyzing gameplay events and generating styled action cues")
        events = subtitle_engine.analyze_events(input_video_path)
        settings.processing.temp_dir.mkdir(parents=True, exist_ok=True)
        sub_path = settings.processing.temp_dir / f"{input_video_path.stem}.ass"
        subtitle_engine.generate_subtitles(events, sub_path)
        logger.info(f"Subtitles generated at: {sub_path}")

        # Step 3: Soothing Royalty-Free Music Looping (Random tracks until video ends)
        logger.info("Step 3/6: Generating randomized soothing royalty-free background audio loop")
        video_duration = processor.get_video_duration(input_video_path)
        stitched_audio_path = settings.processing.temp_dir / f"{input_video_path.stem}_bgm_loop.m4a"
        music_file, track_sequence = audio_mixer.create_random_loop_sequence(
            target_duration=video_duration,
            output_path=stitched_audio_path,
        )
        logger.info(
            f"Sequenced {len(track_sequence)} random soothing tracks covering {video_duration:.1f}s loop",
            extra_data={"track_titles": [t["title"] for t in track_sequence]},
        )

        # Step 4: Video Composite Rendering via FFmpeg
        logger.info("Step 4/6: Executing FFmpeg composite video render")
        output_path = processor.get_output_path(input_video_path.name)
        logger.info(f"Target processed video: {output_path}")

        processor.render(
            input_video=input_video_path,
            output_video=output_path,
            subtitle_file=sub_path,
            music_file=music_file,
            privacy_filter=blur_filter,
            ducking_db=settings.processing.audio_ducking_db,
            preset=settings.processing.video_preset,
        )

        # Step 5: YouTube Metadata Generation & Export
        logger.info("Step 5/6: Generating YouTube publishing metadata")
        metadata = publisher.generate_metadata(input_video_path.stem, events, track_sequence)
        metadata_json_path = output_path.with_name(f"{output_path.stem}_metadata.json")
        publisher.export_metadata_json(metadata, metadata_json_path)

        youtube_url = "N/A (Local execution)"
        if not local_only:
            logger.info("Uploading video to YouTube")
            youtube_url = publisher.upload_video(output_path, metadata)
        else:
            logger.info("Local execution: Output generated in project output/ folder without upload.")

        # Step 6: History Logging & Notifications
        logger.info("Step 6/6: Recording job execution to history")
        tracker.record_job(
            job_id=f"job_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            input_filename=input_video_path.name,
            output_filename=output_path.name,
            status="SUCCESS",
            youtube_url=youtube_url,
            md5_checksum=file_md5,
            details={
                "video_output": str(output_path),
                "metadata_output": str(metadata_json_path),
                "duration_seconds": video_duration,
                "soundtrack_tracks": [t["title"] for t in track_sequence],
                "subtitles_burned": True,
                "privacy_redacted": True,
            },
        )

        notifier.send_video_published_notification(
            video_title=metadata.title,
            youtube_url=youtube_url,
            processing_date=datetime.now().strftime("%d/%m/%Y"),
            details={
                "duration_seconds": video_duration,
                "soundtrack_tracks": [t["title"] for t in track_sequence],
            },
        )

        logger.info("Workflow execution completed successfully!")
        return output_path

    except PipelineError as pe:
        logger.error(f"Pipeline error occurred: {pe}", extra_data=pe.to_dict())
        notifier.send_failure_notification(input_video_path.stem, pe.to_dict())
        raise
    except Exception as e:
        logger.critical(f"Unhandled exception during pipeline execution: {e}", exc_info=True)
        notifier.send_failure_notification(
            input_video_path.stem,
            {"component": "PipelineOrchestrator", "operation": "run_pipeline", "root_cause": str(e)},
        )
        raise


def run_drive_cron(dry_run: bool = False, limit: int = 1, upload: bool = True, force: bool = False) -> int:
    """Scheduled task runner: checks Drive Input, downloads, processes, uploads, and archives."""
    settings = get_settings()
    logger.info("=" * 60)
    logger.info("Starting Google Drive scheduled scan for new gameplay recordings")
    logger.info(f"Target path: MyDrive -> {settings.drive.parent_folder_name} -> {settings.drive.project_folder_name}")
    logger.info("=" * 60)

    drive_client = GoogleDriveClient(
        input_folder_name=settings.drive.input_folder_name,
        processed_folder_name=settings.drive.processed_folder_name,
    )

    try:
        drive_client.connect()
        pending_videos = drive_client.list_pending_videos()

        if not pending_videos:
            logger.info("✅ No pending videos found in Drive Input folder. Pipeline check complete.")
            return 0

        logger.info(f"Found {len(pending_videos)} pending video(s) ready for processing.")

        if dry_run:
            logger.info("[DRY RUN] Inspection only; no files will be downloaded or modified:")
            for v in pending_videos:
                logger.info(f" - File: {v['name']} (Size: {v['size'] / (1024 * 1024):.1f} MB, ID: {v['id']})")
            return 0

        # Process up to limit
        to_process = pending_videos[:limit]
        for video in to_process:
            file_id = video["id"]
            file_name = video["name"]
            logger.info(f"Processing remote file: {file_name} ({file_id})")

            # Download chunk-by-chunk to temp directory
            local_download_path = settings.processing.temp_dir / file_name
            drive_client.download_video(file_id=file_id, destination_path=local_download_path)

            try:
                # Run full video pipeline
                rendered_output = run_pipeline(local_download_path, local_only=not upload, force=force)

                # Upload processed video & metadata to Google Drive Output (Year -> Month -> video_ddmmyyyy)
                meta_json = rendered_output.with_name(f"{rendered_output.stem}_metadata.json")
                logger.info("Uploading processed video to Google Drive Output organized by Year/Month...")
                drive_client.upload_processed_video(
                    local_video_path=rendered_output,
                    metadata_path=meta_json if meta_json.exists() else None,
                )

                # Move raw video in Google Drive from Input -> Processed
                logger.info(f"Archiving raw video {file_name} to Drive Processed folder...")
                drive_client.mark_as_processed(file_id)

                # Clean up local raw download to save runner disk space
                if local_download_path.exists():
                    local_download_path.unlink()
                    logger.info(f"Cleaned temporary downloaded file: {local_download_path}")

            except Exception as pe:
                logger.error(f"Failed to process video {file_name}: {pe}")
                if local_download_path.exists():
                    local_download_path.unlink()
                return 1

        logger.info("All pending jobs processed successfully.")
        return 0

    except IngestionError as ie:
        logger.error(f"Google Drive Ingestion Error: {ie}")
        return 1
    except Exception as e:
        logger.critical(f"Fatal error during drive-cron execution: {e}", exc_info=True)
        return 1


def main() -> None:
    parser = argparse.ArgumentParser(description="Last Day on Earth Automated Video Pipeline")
    subparsers = parser.add_subparsers(dest="command")

    # Local processing command
    process_parser = subparsers.add_parser("process", help="Process a local gameplay video")
    process_parser.add_argument("--input", "-i", type=str, required=True, help="Path to input video file")
    process_parser.add_argument("--local", action="store_true", default=True, help="Run locally without uploading to YouTube")
    process_parser.add_argument("--upload", action="store_true", help="Upload to YouTube after processing")
    process_parser.add_argument("--force", action="store_true", help="Force processing even if duplicate is detected")

    # Scheduled Google Drive CRON command
    cron_parser = subparsers.add_parser("drive-cron", help="Poll Google Drive for pending recordings and process")
    cron_parser.add_argument("--dry-run", action="store_true", help="Inspect Drive Input folder without processing")
    cron_parser.add_argument("--limit", type=int, default=1, help="Max videos to process in this run (default: 1)")
    cron_parser.add_argument("--no-upload", action="store_true", help="Do not upload to YouTube")
    cron_parser.add_argument("--force", action="store_true", help="Force processing even if duplicate is detected")

    args = parser.parse_args()

    if args.command == "process":
        local_flag = not args.upload
        run_pipeline(Path(args.input), local_only=local_flag, force=args.force)
    elif args.command == "drive-cron":
        upload_flag = not args.no_upload
        exit_code = run_drive_cron(dry_run=args.dry_run, limit=args.limit, upload=upload_flag, force=args.force)
        sys.exit(exit_code)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
