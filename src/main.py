"""Main entry point and orchestrator for the Last Day on Earth video pipeline."""

import argparse
import sys
from pathlib import Path
from datetime import datetime

from src.config import get_settings
from src.logging_config import get_logger
from src.exceptions import PipelineError
from src.privacy.detector import PrivacyDetector
from src.subtitles.event_analyzer import SubtitleGenerator
from src.audio.selector import AudioMixer
from src.processor.video_processor import VideoProcessor
from src.publisher.youtube_client import YouTubeClient
from src.notifications.email_client import EmailNotifier
from src.storage.history_tracker import HistoryTracker

logger = get_logger(component="PipelineOrchestrator")


def run_pipeline(input_video_path: Path, local_only: bool = False) -> None:
    """Executes the full pipeline for a single video file."""
    settings = get_settings()
    logger.info("Initiating video processing workflow", extra_data={"input": str(input_video_path)})

    if not input_video_path.exists():
        logger.error(f"Input file not found: {input_video_path}")
        sys.exit(1)

    # Initialize components
    privacy_guard = PrivacyDetector()
    subtitle_engine = SubtitleGenerator(gemini_api_key=settings.gemini.api_key or "")
    audio_mixer = AudioMixer(library_path=settings.processing.music_library_file)
    processor = VideoProcessor(output_dir=settings.processing.output_dir)
    publisher = YouTubeClient(
        client_secrets_file=settings.youtube.client_secrets_file,
        token_file=settings.youtube.token_file,
        privacy_status=settings.youtube.privacy_status,
    )
    notifier = EmailNotifier(
        host=settings.smtp.host,
        port=settings.smtp.port,
        user=settings.smtp.user,
        password=settings.smtp.password,
        recipients=settings.smtp.recipients,
    )
    tracker = HistoryTracker(history_file=settings.processing.history_file)

    try:
        # Step 1: Privacy Scan
        logger.info("Step 1/6: Scanning for sensitive information")
        bboxes = privacy_guard.scan_video(input_video_path)
        blur_filter = privacy_guard.generate_ffmpeg_blur_filter(bboxes)

        # Step 2: Gameplay Events & Subtitles
        logger.info("Step 2/6: Analyzing gameplay events and rendering subtitles")
        events = subtitle_engine.analyze_events(input_video_path)
        sub_path = settings.processing.temp_dir / f"{input_video_path.stem}.ass"
        subtitle_engine.generate_subtitles(events, sub_path)

        # Step 3: Audio Selection
        logger.info("Step 3/6: Selecting royalty-free background track")
        track = audio_mixer.select_track()

        # Step 4: Render Video
        logger.info("Step 4/6: Rendering composite video with FFmpeg")
        output_path = processor.get_output_path(input_video_path.name)
        logger.info(f"Target output file: {output_path.name}")

        # Step 5: Publishing (if not local-only)
        youtube_url = "N/A (Local execution)"
        if not local_only:
            logger.info("Step 5/6: Generating YouTube metadata & uploading")
            metadata = publisher.generate_metadata(input_video_path.stem, events, track)
            youtube_url = publisher.upload_video(output_path, metadata)
        else:
            logger.info("Step 5/6: Skipping YouTube upload (--local specified)")

        # Step 6: Notifications & History
        logger.info("Step 6/6: Logging execution history and sending notification")
        tracker.record_job(
            job_id=f"job_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            input_filename=input_video_path.name,
            output_filename=output_path.name,
            status="SUCCESS",
            youtube_url=youtube_url,
        )

        notifier.send_video_published_notification(
            video_title=input_video_path.stem,
            youtube_url=youtube_url,
            processing_date=datetime.now().strftime("%d/%m/%Y"),
        )
        logger.info("Workflow execution completed successfully.")

    except PipelineError as pe:
        logger.error(f"Pipeline error occurred: {pe}", extra_data=pe.to_dict())
        notifier.send_failure_notification(input_video_path.stem, pe.to_dict())
        sys.exit(1)
    except Exception as e:
        logger.critical(f"Unhandled exception during pipeline execution: {e}", exc_info=True)
        sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(description="Last Day on Earth Automated Video Pipeline")
    subparsers = parser.add_subparsers(dest="command")

    process_parser = subparsers.add_parser("process", help="Process a gameplay video")
    process_parser.add_argument("--input", "-i", type=str, required=True, help="Path to input video file")
    process_parser.add_argument("--local", action="store_true", help="Run locally without uploading to YouTube")

    args = parser.parse_args()

    if args.command == "process":
        run_pipeline(Path(args.input), local_only=args.local)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
