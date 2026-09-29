"""Main entry point and orchestrator for the Last Day on Earth video pipeline."""

import argparse
import hashlib
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional

from src.config import get_settings
from src.logging_config import get_logger
from src.exceptions import (
    PipelineError,
    ConfigurationError,
    IngestionError,
    PrivacyRedactionError,
    SubtitleGenerationError,
    AudioProcessingError,
    VideoProcessingError,
    PublishingError,
    NotificationError,
)

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
from src.processor.thumbnail_generator import ThumbnailGenerator
from src.publisher.youtube_client import YouTubeClient
from src.publisher.title_manager import TitleManager
from src.notifications.email_client import EmailNotifier
from src.notifications.gmail_client import GmailNotifier
from src.storage.history_tracker import HistoryTracker
from src.ingestion.drive_client import GoogleDriveClient

logger = get_logger(component="PipelineOrchestrator")


class RenderResult(type(Path())):
    """Path subclass returned by run_pipeline carrying YouTube upload verification details."""
    youtube_url: str = ""
    uploaded_to_youtube: bool = False
    video_id: str = ""


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


def run_pipeline(
    input_video_path: Path,
    local_only: bool = True,
    force: bool = False,
    delete_input: Optional[bool] = None,
) -> RenderResult:
    """Executes the complete video processing workflow for a single video file."""
    settings = get_settings()
    if delete_input is None:
        delete_input = settings.processing.delete_input_after_processing
    logger.info("Initiating video processing workflow", extra_data={"input": str(input_video_path)})

    if not input_video_path.exists():
        logger.error(f"Input file not found: {input_video_path}")
        sys.exit(1)

    # Initialize subsystems
    privacy_guard = PrivacyDetector()
    subtitle_engine = SubtitleGenerator(gemini_api_key=settings.gemini.api_key or "")
    audio_mixer = AudioMixer(library_path=settings.processing.music_library_file)
    processor = VideoProcessor(output_dir=settings.processing.output_dir)
    title_mgr = TitleManager(
        tracker_file=settings.youtube.series_tracker_file,
        series_name=settings.youtube.series_title,
        series_prefix=settings.youtube.series_prefix,
        title_style=settings.youtube.title_style,
        episode_numbering=settings.youtube.episode_numbering,
        sync_youtube=settings.youtube.sync_episode_with_youtube,
    )
    thumbnail_gen = ThumbnailGenerator(output_dir=settings.processing.output_dir)
    publisher = YouTubeClient(
        client_secrets_file=settings.youtube.client_secrets_file,
        token_file=settings.youtube.token_file,
        privacy_status=settings.youtube.privacy_status,
        playlist_title=settings.youtube.playlist_title,
        title_manager=title_mgr,
        gemini_api_key=settings.gemini.api_key,
        gemini_model=settings.gemini.model,
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
        blur_filter = None
        try:
            logger.info("Step 1/6: Scanning for sensitive personal data")
            bboxes = privacy_guard.scan_video(input_video_path)
            blur_filter = privacy_guard.generate_ffmpeg_blur_filter(bboxes)
            logger.info(f"Generated privacy filter: {blur_filter}")
        except Exception as pe:
            logger.warning(
                f"Privacy scan degraded: {pe}. Proceeding without frame blur.",
                extra_data={
                    "operation": "privacy_scan",
                    "component": "PrivacyDetector",
                    "file": str(input_video_path),
                    "root_cause": str(pe),
                    "recovery_action": "Check easyocr dependencies; continuing execution without redaction.",
                    "status": "DEGRADED",
                },
            )
            blur_filter = None

        # Step 2: Gameplay Context & Subtitle Generation (Sleek 1-sec action cues)
        sub_path = None
        events = []
        try:
            logger.info("Step 2/6: Analyzing gameplay events and generating styled action cues")
            events = subtitle_engine.analyze_events(input_video_path)
            settings.processing.temp_dir.mkdir(parents=True, exist_ok=True)
            sub_path = settings.processing.temp_dir / f"{input_video_path.stem}.ass"
            subtitle_engine.generate_subtitles(events, sub_path)
            logger.info(f"Subtitles generated at: {sub_path}")
        except Exception as se:
            logger.warning(
                f"Subtitle generation degraded: {se}. Using fallback event markers.",
                extra_data={
                    "operation": "subtitle_generation",
                    "component": "SubtitleEngine",
                    "file": str(input_video_path),
                    "root_cause": str(se),
                    "recovery_action": "Check Gemini API quota or network connection. Using default events.",
                    "status": "DEGRADED",
                },
            )
            from src.subtitles.event_analyzer import GameplayEvent
            events = [
                GameplayEvent(0.0, 5.0, "nav", "Entering Wasteland Base"),
                GameplayEvent(30.0, 35.0, "craft", "Workshop & Inventory Management"),
                GameplayEvent(90.0, 95.0, "defense", "Perimeter Defense & Survival Run"),
            ]
            sub_path = None

        # Step 3: Soothing Royalty-Free Music Looping (Random tracks until video ends)
        video_duration = processor.get_video_duration(input_video_path)
        music_file = None
        track_sequence = []
        try:
            logger.info("Step 3/6: Generating randomized soothing royalty-free background audio loop")
            stitched_audio_path = settings.processing.temp_dir / f"{input_video_path.stem}_bgm_loop.m4a"
            music_file, track_sequence = audio_mixer.create_random_loop_sequence(
                target_duration=video_duration,
                output_path=stitched_audio_path,
            )
            logger.info(
                f"Sequenced {len(track_sequence)} random soothing tracks covering {video_duration:.1f}s loop",
                extra_data={"track_titles": [t["title"] for t in track_sequence]},
            )
        except Exception as ae:
            logger.warning(
                f"Audio loop synthesis failed: {ae}. Falling back to default ambient track.",
                extra_data={
                    "operation": "audio_loop_sequence",
                    "component": "AudioMixer",
                    "file": str(input_video_path),
                    "root_cause": str(ae),
                    "recovery_action": "Check config/music_library.json and audio directory. Falling back to default track.",
                    "status": "DEGRADED",
                },
            )
            default_ambient = Path("config/audio/wasteland_horizon.mp3")
            if default_ambient.exists():
                music_file = default_ambient
                track_sequence = [{"title": "Wasteland Horizon", "attribution_text": "Original CC0 Ambient Theme"}]

        # Step 4: Video Composite Rendering via FFmpeg
        logger.info("Step 4/6: Executing FFmpeg composite video render")
        output_path = processor.get_output_path(input_video_path.name)
        logger.info(f"Target processed video: {output_path}")

        try:
            processor.render(
                input_video=input_video_path,
                output_video=output_path,
                subtitle_file=sub_path,
                music_file=music_file,
                privacy_filter=blur_filter,
                ducking_db=settings.processing.audio_ducking_db,
                preset=settings.processing.video_preset,
            )
        except Exception as ve:
            raise VideoProcessingError(
                operation="composite_render",
                root_cause=str(ve),
                recovery_action="Check FFmpeg filters, codecs, input video corruption, and disk space.",
                file_path=str(input_video_path),
                status="FAILED",
                details={"sub_path": str(sub_path), "music_file": str(music_file)},
            )

        # Step 5: Custom HD Thumbnail & YouTube Publishing Metadata Generation
        logger.info("Step 5/6: Generating custom HD thumbnail and YouTube publishing metadata")
        current_ep = title_mgr.get_current_episode()
        ep_num_for_publishing = current_ep if settings.youtube.episode_numbering else None

        thumbnail_path = None
        if settings.processing.generate_thumbnail and output_path.exists():
            thumbnail_path = output_path.with_name(f"{output_path.stem}_thumbnail.jpg")
            try:
                thumbnail_gen.generate_thumbnail(
                    video_path=output_path,
                    output_path=thumbnail_path,
                    events=events,
                    duration=video_duration,
                    episode_number=ep_num_for_publishing,
                )
                logger.info(f"Custom YouTube thumbnail saved at: {thumbnail_path}")
            except Exception as te:
                logger.warning(
                    f"Could not generate custom thumbnail: {te}. Proceeding without custom thumbnail.",
                    extra_data={
                        "operation": "generate_thumbnail",
                        "component": "ThumbnailGenerator",
                        "file": str(thumbnail_path),
                        "root_cause": str(te),
                        "recovery_action": "Check Pillow font dependencies or pre-rendered thumbnail assets.",
                        "status": "DEGRADED",
                    },
                )
                thumbnail_path = None

        try:
            metadata = publisher.generate_metadata(
                video_title=input_video_path.stem,
                events=events,
                music_track=track_sequence,
                thumbnail_path=thumbnail_path,
                episode_number=ep_num_for_publishing,
            )
            metadata_json_path = output_path.with_name(f"{output_path.stem}_metadata.json")
            publisher.export_metadata_json(metadata, metadata_json_path)
        except Exception as me:
            raise PublishingError(
                operation="generate_metadata",
                root_cause=str(me),
                recovery_action="Review title templates and Gemini API configuration.",
                file_path=str(output_path),
                status="FAILED",
            )

        youtube_url = "N/A (Local execution)"
        uploaded_to_youtube = False
        video_id = ""
        if not local_only:
            try:
                logger.info("Uploading video to YouTube")
                youtube_url = publisher.upload_video(output_path, metadata)
                if youtube_url and "youtu" in youtube_url:
                    cleaned = youtube_url.rstrip("/").split("/")[-1].split("?v=")[-1]
                    if cleaned and cleaned not in ("N/A (Local execution)", "mock_ldoe_video"):
                        video_id = cleaned
                        uploaded_to_youtube = True

                if not uploaded_to_youtube:
                    raise PublishingError(
                        operation="upload_video",
                        root_cause=f"YouTube upload failed to return a verified published video ID (URL: {youtube_url}).",
                        recovery_action="Verify YouTube credentials, channel verification status, and API quota.",
                        file_path=str(output_path),
                        status="FAILED",
                    )
            except Exception as ue:
                if isinstance(ue, PublishingError):
                    raise ue
                raise PublishingError(
                    operation="upload_video",
                    root_cause=str(ue),
                    recovery_action="Check YouTube API quota, channel status, or re-run scripts/setup_google_auth.py.",
                    file_path=str(output_path),
                    status="FAILED",
                )
        else:
            logger.info("Local execution: Output generated in project output/ folder without upload.")
            try:
                title_mgr.advance_episode(title=metadata.title, job_id="local_execution")
            except Exception as se:
                logger.warning(
                    f"Could not advance episode counter in local mode: {se}",
                    extra_data={
                        "operation": "advance_episode",
                        "component": "TitleManager",
                        "root_cause": str(se),
                        "recovery_action": "Check series_tracker.json permissions.",
                        "status": "DEGRADED",
                    },
                )

        # Step 6: History Logging & Notifications
        logger.info("Step 6/6: Recording job execution to history")
        if not video_id and youtube_url and "youtu" in youtube_url:
            cleaned = youtube_url.rstrip("/").split("/")[-1].split("?v=")[-1]
            if cleaned and cleaned != "N/A (Local execution)":
                video_id = cleaned

        try:
            tracker.record_job(
                job_id=f"job_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                input_filename=input_video_path.name,
                output_filename=output_path.name,
                status="SUCCESS",
                youtube_url=youtube_url,
                video_id=video_id,
                md5_checksum=file_md5,
                details={
                    "video_id": video_id,
                    "youtube_url": youtube_url,
                    "video_output": str(output_path),
                    "metadata_output": str(metadata_json_path),
                    "thumbnail_output": str(thumbnail_path) if thumbnail_path else None,
                    "title_candidates": metadata.title_candidates,
                    "duration_seconds": video_duration,
                    "soundtrack_tracks": [t["title"] for t in track_sequence],
                    "subtitles_burned": sub_path is not None,
                    "privacy_redacted": blur_filter is not None,
                },
            )
        except Exception as he:
            logger.warning(
                f"Failed to record job to history tracker: {he}",
                extra_data={
                    "operation": "record_job",
                    "component": "HistoryTracker",
                    "root_cause": str(he),
                    "recovery_action": "Inspect history file permissions.",
                    "status": "DEGRADED",
                },
            )

        try:
            notifier.send_video_published_notification(
                video_title=metadata.title,
                youtube_url=youtube_url,
                processing_date=datetime.now().strftime("%d/%m/%Y"),
                details={
                    "duration_seconds": video_duration,
                    "soundtrack_tracks": [t["title"] for t in track_sequence],
                },
            )
        except Exception as ne:
            logger.warning(
                f"Failed to send email notification: {ne}",
                extra_data={
                    "operation": "send_notification",
                    "component": "Notifier",
                    "root_cause": str(ne),
                    "recovery_action": "Check recipient list or Gmail credentials.",
                    "status": "DEGRADED",
                },
            )

        logger.info("Workflow execution completed successfully!")

        # Step 7: Delete input video if configured to prevent duplicate processing
        if delete_input:
            if input_video_path.exists():
                try:
                    input_video_path.unlink()
                    logger.info(f"Successfully deleted processed input video: {input_video_path}")
                except Exception as de:
                    logger.warning(
                        f"Could not delete input video {input_video_path}: {de}",
                        extra_data={
                            "operation": "delete_input_video",
                            "component": "PipelineOrchestrator",
                            "file": str(input_video_path),
                            "root_cause": str(de),
                            "recovery_action": "Check file system permissions.",
                            "status": "DEGRADED",
                        },
                    )

        result = RenderResult(output_path)
        result.youtube_url = youtube_url
        result.uploaded_to_youtube = uploaded_to_youtube
        result.video_id = video_id
        return result

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

        # Step A: Daily cleanup of Drive Processed folder
        try:
            drive_client.cleanup_processed_folder()
        except Exception as ce:
            logger.warning(f"Drive Processed folder cleanup skipped: {ce}")

        # Step B: 7-day retention cleanup of Drive Output videos
        try:
            drive_client.cleanup_old_output_videos(retention_days=settings.drive.output_retention_days)
        except Exception as oe:
            logger.warning(f"Drive Output video retention cleanup skipped: {oe}")

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
                # Run full video pipeline (delete_input=False because temp file cleanup is managed explicitly below)
                rendered_output = run_pipeline(local_download_path, local_only=not upload, force=force, delete_input=False)

                # STRICT CONFIRMATION: NEVER delete raw video from Google Drive Input until confirmed uploaded to YouTube
                is_uploaded = upload and getattr(rendered_output, "uploaded_to_youtube", False)
                if is_uploaded:
                    logger.info(
                        f"Video confirmed uploaded to YouTube ({getattr(rendered_output, 'youtube_url', '')}). "
                        f"Deleting raw video '{file_name}' ({file_id}) from Google Drive Input..."
                    )
                    try:
                        drive_client.delete_video(file_id)
                        logger.info(f"Confirmed: raw video '{file_name}' ({file_id}) deleted from Google Drive Input after verified YouTube upload.")
                    except Exception as de:
                        logger.error(f"Failed to delete video from Drive Input: {de}", extra_data={"file_id": file_id})
                else:
                    logger.warning(
                        f"SAFETY LOCK: Preserving raw video '{file_name}' ({file_id}) in Google Drive Input. "
                        f"Video will NOT be deleted from Drive Input until successfully uploaded to YouTube (upload={upload}, is_uploaded={is_uploaded})."
                    )

                # Upload processed video & metadata to Google Drive Output (Year -> Month -> video_ddmmyyyy)
                try:
                    meta_json = rendered_output.with_name(f"{rendered_output.stem}_metadata.json")
                    logger.info("Uploading processed video to Google Drive Output organized by Year/Month...")
                    drive_client.upload_processed_video(
                        local_video_path=rendered_output,
                        metadata_path=meta_json if meta_json.exists() else None,
                    )
                except Exception as ue:
                    logger.error(f"Google Drive Output upload failed: {ue}. (YouTube upload was already completed successfully).")

                # Clean up local raw download to save runner disk space
                if local_download_path.exists():
                    local_download_path.unlink()
                    logger.info(f"Cleaned temporary downloaded file: {local_download_path}")

            except Exception as pe:
                err_dict = pe.to_dict() if isinstance(pe, PipelineError) else {
                    "operation": "process_drive_video",
                    "component": "CronRunner",
                    "file_path": str(local_download_path),
                    "root_cause": str(pe),
                    "recovery_action": "Investigate runner logs. Raw video is safely preserved in Drive Input.",
                    "status": "FAILED",
                }
                logger.error(
                    f"Failed to process video '{file_name}' ({file_id}): {pe}. "
                    f"Raw video will NOT be deleted from Google Drive Input.",
                    extra_data=err_dict,
                )
                try:
                    notifier.send_failure_notification(video_title=file_name, error_details=err_dict)
                except Exception as n_err:
                    logger.warning(f"Could not dispatch failure notification: {n_err}")

                if local_download_path.exists():
                    local_download_path.unlink()
                return 1

        # Post-processing routine: ensure Processed folder is empty
        try:
            drive_client.cleanup_processed_folder()
        except Exception as ce:
            logger.warning(f"Post-processing Processed folder cleanup skipped: {ce}")

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
    process_parser.add_argument("--delete-input", dest="delete_input", action="store_true", default=None, help="Delete input video file after successful processing")
    process_parser.add_argument("--keep-input", dest="delete_input", action="store_false", help="Preserve input video file after processing")

    # Scheduled Google Drive CRON command
    cron_parser = subparsers.add_parser("drive-cron", help="Poll Google Drive for pending recordings and process")
    cron_parser.add_argument("--dry-run", action="store_true", help="Inspect Drive Input folder without processing")
    cron_parser.add_argument("--limit", type=int, default=1, help="Max videos to process in this run (default: 1)")
    cron_parser.add_argument("--no-upload", action="store_true", help="Do not upload to YouTube")
    cron_parser.add_argument("--force", action="store_true", help="Force processing even if duplicate is detected")

    args = parser.parse_args()

    if args.command == "process":
        local_flag = not args.upload
        run_pipeline(Path(args.input), local_only=local_flag, force=args.force, delete_input=args.delete_input)
    elif args.command == "drive-cron":
        upload_flag = not args.no_upload
        exit_code = run_drive_cron(dry_run=args.dry_run, limit=args.limit, upload=upload_flag, force=args.force)
        sys.exit(exit_code)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
