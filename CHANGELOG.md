# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.5.0] - 2026-09-23

### Added
- **Automated YouTube Playlist Management**: Automatically discovers or creates the dedicated channel playlist (`Last Day on Earth: Survival — Official Gameplay Series`, ID `PLJPzVNVZwaGY`) with rich description and hashtags, and automatically adds all newly published episodes.
- **Comprehensive Duplicate Prevention**:
  - **Drive Input Deduplication**: Compares native `md5Checksum` against `Processed` folder to skip previously processed recordings and auto-archive twin duplicate uploads.
  - **Drive Output Disambiguation**: Resolves same-day filename collisions by auto-incrementing suffixes (`video_{ddmmyyyy}_1.mp4`, `metadata_{ddmmyyyy}_1.json`).
  - **Local Deduplication**: Computes MD5 file checksums and verifies against `HistoryTracker` with `--force` CLI override.
  - **Strict Drive Removal**: Verifies `parents` after moving to ensure raw recordings are permanently removed from `Input`.
- **Streamlined OAuth & Secret Sync**: Integrated one-click credential saving and automatic GitHub repository secret synchronization in `scripts/setup_google_auth.py`.
- **Test Suite Expansion**: Added `tests/test_duplicates.py` and `tests/test_youtube_client.py` bringing test coverage to 27 unit tests.

### Changed
- **Default Privacy Status**: Switched default YouTube publishing privacy from `unlisted` to `public` across configurations, workflow runners, and publishing clients.

## [0.4.0] - 2026-09-23

### Added
- **Dynamic YouTube Titles**: Implemented randomized high-CTR title rotation combined with formatted date `(DD Mon, YYYY)` to ensure unique and compliant YouTube metadata.
- **Top 50 Trending Hashtags**: Embedded top 50 curated high-reach survival and gaming hashtags into YouTube video descriptions.
- **Drive Output Hierarchy**: Structured `Output` into segregated `videos/` and `metadata/` trees organized by `Year/Month/` (`video_ddmmyyyy.mp4` and `metadata_ddmmyyyy.json`).
- **Automated GitHub Secrets Sync**: Added `scripts/sync_github_secrets.py` to encrypt and synchronize Google Cloud OAuth secrets to GitHub Actions using the GitHub REST API and libsodium encryption.
- **Test Staging Script**: Added `scripts/stage_input_test.py` for staging test recordings directly in Google Drive.

### Changed
- **Description Hygiene**: Removed soundtrack listing and Creative Commons attribution blocks from YouTube video descriptions.
- **GitHub Runner Optimization**: Disabled pip caching in `.github/workflows/scheduled_pipeline.yml`, saving ~200 MB of repository storage.

## [0.3.0] - 2026-09-23

### Added
- **Strict Google Drive API v3 Ingestion**: Direct Drive integration strictly locked to `MyDrive -> youtube-projects -> LastDayOnEarth`. Checks for pending videos in `Input` and automatically moves processed videos to `Processed` without requiring local Drive sync.
- **Gmail API v1 Notifier**: Replaced SMTP with native Google Gmail API v1 (`https://www.googleapis.com/auth/gmail.send`) dispatching rich HTML notifications on publishing success or pipeline failure.
- **GitHub Actions Scheduled Pipeline**: Configured `.github/workflows/scheduled_pipeline.yml` running 6 times daily (`0 */4 * * *`) with automatic exit if no files are pending, conserving GitHub minutes.
- **One-Time Google OAuth Setup Script**: `scripts/setup_google_auth.py` generates unified OAuth credentials for Drive, YouTube, and Gmail and outputs GitHub Secrets format.
- **Drive-Cron Orchestrator Command**: Added `python -m src.main drive-cron [--dry-run] [--limit N] [--no-upload]`.
- **Test Suite Expansion**: Added unit tests for Google Drive safety boundaries, Gmail API encoding, and drive-cron flow (17/17 tests passing).

## [0.2.0] - 2026-09-23

### Changed
- **Privacy Policy**: Removed intrusive bounding boxes on native game HUD (username `adistar656` and lower-left clan chat area preserved 100% unblurred).
- **Subtitles**: Replaced continuous subtitle bars with snappy 1-second action cues ("Global Map", "Entering Base", "Weapon Bench", etc.) with fade in/out animations.
- **Music Library**: Downloaded 20 authentic 320 kbps soothing/chill studio tracks (CC-BY 4.0 by Kevin MacLeod) replacing sub-bass sweeps.

## [0.1.0] - 2026-09-23

### Added
- Project initialization and scaffolding according to global engineering standards.
- Git repository initialization and `.gitignore` covering media files, secrets, virtual environments, and logs.
- Project documentation: `README.md`, `docs/ARCHITECTURE.md`, `docs/DEVELOPMENT.md`.
- Structured machine-readable logging foundation (`src/logging_config.py`) with daily rotation (`logs/YYYY-MM-DD/application.log`).
- Unified error handling hierarchy (`src/exceptions.py`) capturing Operation, Component, File, Root Cause, Recovery Action, and Status.
- Configuration management module (`src/config.py`) with environment variable validation.
- Modular architecture scaffold for Ingestion, Privacy Redaction, Subtitles, Audio, Processing, Publishing, Notifications, and Storage.
- Royalty-free music catalog schema and dataset (`config/music_library.json`) with 20 curated tracks.
- Foundation unit test suite in `tests/`.
