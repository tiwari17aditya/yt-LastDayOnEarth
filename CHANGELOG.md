# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.5.0] - 2026-09-29

### Added
- **Automated Creator First Engagement Comment Hook**:
  - Implemented `post_engagement_comment()` in [`src/publisher/youtube_client.py`](file:///d:/youtube-projects/LastDayOnEarth/src/publisher/youtube_client.py), automatically posting a top community comment with an episode discussion question, series playlist link, and subscription callout immediately after publishing.
  - Added CLI tool [`scripts/post_engagement_comments.py`](file:///d:/youtube-projects/LastDayOnEarth/scripts/post_engagement_comments.py) to manage engagement comments across any episode or channel video.

- **Automated YouTube Shorts (9:16) Auto-Clipper**:
  - Implemented [`src/processor/shorts_generator.py`](file:///d:/youtube-projects/LastDayOnEarth/src/processor/shorts_generator.py) converting 16:9 gameplay footage to high-impact 1080x1920 vertical format using a fast bicubic downscale-upscale blurred backdrop and centered HD gameplay box.
  - Generates high-contrast distressed branding header, episode badge, and call-to-action overlays.
  - Added CLI tool [`scripts/generate_short.py`](file:///d:/youtube-projects/LastDayOnEarth/scripts/generate_short.py) for rendering YouTube Shorts clips with custom timestamps.

- **End-Screen & Cards Outro Slate Generator**:
  - Implemented [`src/processor/endscreen_generator.py`](file:///d:/youtube-projects/LastDayOnEarth/src/processor/endscreen_generator.py) rendering 1920x1080 cinematic outro video bumpers with visual guide card boxes for YouTube Studio's interactive elements (Next Episode, Series Playlist, Subscribe Pill).
  - Added CLI tool [`scripts/generate_endscreen.py`](file:///d:/youtube-projects/LastDayOnEarth/scripts/generate_endscreen.py).

- **Channel Growth Analytics & Retention Digest**:
  - Implemented [`src/analytics/channel_digest.py`](file:///d:/youtube-projects/LastDayOnEarth/src/analytics/channel_digest.py) querying YouTube Data API for subscriber counts, total views, per-video engagement metrics (like-to-view and comment-to-view ratios), and algorithmic channel health.
  - Generates Markdown reports under `reports/analytics/` and dispatches executive HTML digests via [`GmailNotifier`](file:///d:/youtube-projects/LastDayOnEarth/src/notifications/gmail_client.py).
  - Added CLI tool [`scripts/generate_channel_digest.py`](file:///d:/youtube-projects/LastDayOnEarth/scripts/generate_channel_digest.py).

- **Dynamic Milestone Chapters with Emoji Badges**:
  - Enhanced chapter generation in [`src/publisher/youtube_client.py`](file:///d:/youtube-projects/LastDayOnEarth/src/publisher/youtube_client.py) with contextual event badges (`🛠️`, `⚔️`, `🎒`, `☢️`, `🎬`, `🏡`, `🏆`) to optimize the video scrub bar and Google Search rich snippet indexation.

## [1.4.0] - 2026-09-29

### Added
- **Cinematic Grunge Thumbnail Engine**:
  - Implemented high-CTR cinematic survival branding in [src/processor/cinematic_branding.py](file:///d:/youtube-projects/LastDayOnEarth/src/processor/cinematic_branding.py), rendering the distressed stencil "LAST DAY ON EARTH" logo and organic paint-splatter episode badges (`#<N>`) with dynamic rotating survivor color palettes (Crimson, Amber, Emerald, Cobalt, Purple, Flame).
  - Upgraded [ThumbnailGenerator](file:///d:/youtube-projects/LastDayOnEarth/src/processor/thumbnail_generator.py) with automatic pre-generated episode thumbnail discovery and default grunge aesthetic for future video pipeline runs.
  - Added dedicated CLI tool [scripts/generate_thumbnail.py](file:///d:/youtube-projects/LastDayOnEarth/scripts/generate_thumbnail.py) supporting automated episode thumbnail generation, keyframe branding, AI prompt generation for custom scenarios (Bunker Alfa, Farm, Chopper, Workshop, Base Defense), and YouTube thumbnail upload.
  - Added [scripts/update_youtube_thumbnails.py](file:///d:/youtube-projects/LastDayOnEarth/scripts/update_youtube_thumbnails.py) for batch thumbnail updating across channel videos.
  - Curated and saved high-resolution 1280x720 cinematic thumbnails for Episodes 1 through 13 in `data/thumbnails/`.

- **Copyright Claim Prevention & Attribution System**:
  - Automatically injected Creative Commons Attribution 4.0 (CC BY 4.0) and Kefir Games Fair Use disclaimers in [YouTubeClient.generate_metadata](file:///d:/youtube-projects/LastDayOnEarth/src/publisher/youtube_client.py) across all published descriptions.
  - Adjusted default background music volume ducking from `-8dB` to `-15dB` across [src/config.py](file:///d:/youtube-projects/LastDayOnEarth/src/config.py), [src/audio/selector.py](file:///d:/youtube-projects/LastDayOnEarth/src/audio/selector.py), and [src/processor/video_processor.py](file:///d:/youtube-projects/LastDayOnEarth/src/processor/video_processor.py) to prevent aggressive Content ID audio fingerprint triggering.
  - Added [scripts/resolve_copyright_claims.py](file:///d:/youtube-projects/LastDayOnEarth/scripts/resolve_copyright_claims.py) utility to audit channel videos and resolve Content ID notices.
  - Purged claimed track `Morning` (`morning.mp3`) from audio library and replaced with 100% copyright-free original theme `Wasteland Horizon` (`wasteland_horizon.mp3`, CC0 Public Domain).
  - Added [scripts/generate_safe_ambient_theme.py](file:///d:/youtube-projects/LastDayOnEarth/scripts/generate_safe_ambient_theme.py) for algorithmic synthesis of Content-ID-immune ambient music.

### Changed
- **Updated All Existing YouTube Video Thumbnails**:
  - Synchronized and updated custom thumbnails across all 12 published LDoE videos on YouTube (Episodes #1 through #11) with the new cinematic grunge aesthetic.

## [1.3.5] - 2026-09-29

### Added
- **Gmail Automation & Mail Segregation Rules**:
  - Added [config/gmail_filters.xml](file:///d:/youtube-projects/LastDayOnEarth/config/gmail_filters.xml) import template to automatically route emails into a hierarchical folder tree under parent label `lastDayOnEarth-yt` (`Success`, `Weekly Reports`, `Monthly Reports`, `Alerts`).
  - Configured filters to automatically skip the Inbox (`shouldArchive=true`) and bypass spam (`shouldNeverSpam=true`).
  - Added [scripts/setup_gmail_rules.py](file:///d:/youtube-projects/LastDayOnEarth/scripts/setup_gmail_rules.py) for programmatic Gmail API filter and label configuration.

## [1.3.4] - 2026-09-29

### Fixed & Enhanced
- **Continuous YouTube Episode Numbering Maintenance**:
  - Implemented dynamic live episode synchronization in [TitleManager](file:///d:/youtube-projects/LastDayOnEarth/src/publisher/title_manager.py) (`sync_with_youtube`), automatically discovering the highest published series episode number (`#N`) on the YouTube playlist/channel uploads upon initialization or publishing.
  - Guarantees consecutive episode progression across ephemeral CI/CD runners (e.g. GitHub Actions) without ever resetting or producing duplicate episode numbers.
  - Added persistence step in [.github/workflows/scheduled_pipeline.yml](file:///d:/youtube-projects/LastDayOnEarth/.github/workflows/scheduled_pipeline.yml) to push updated tracker and history state back to GitHub on scheduled runs.
  - Synchronized episode numbers between thumbnail generation and video metadata generation in [src/main.py](file:///d:/youtube-projects/LastDayOnEarth/src/main.py).

### Fixed
- **Corrected Current Video Titles & Descriptions on YouTube**:
  - Identified and repaired duplicate `#8` title suffixes across published videos on YouTube.
  - Updated Video 7 (`JMa211Yc4YU`) from `#8` to `#7`.
  - Maintained Video 8 (`Wf50vxO0NHs`) as `#8`.
  - Updated Video 9 (`VP7g6-VqNY4`) from `#8` to `#9`.
  - Updated Video 10 (`eYny9FafrjI`) from `#8` to `#10`.
  - Updated matching description episode headers (`In Episode #N`) on YouTube.
  - Verified `data/series_tracker.json` reflects all 10 episodes and targets `#11` for the next video.

## [1.3.3] - 2026-09-28

### Fixed & Enhanced
- **Strict YouTube Upload Confirmation Before Drive Input Deletion**:
  - Implemented an immutable safety lock in [src/main.py](file:///d:/youtube-projects/LastDayOnEarth/src/main.py) guaranteeing that videos in Google Drive (`Input/`) are NEVER deleted unless YouTube upload has completed and returned a verified published video ID (`uploaded_to_youtube=True`).
  - Prohibited deletion when running in local or dry-run modes (`upload=False` or `--no-upload`), preserving raw recordings in Drive Input.
  - Eliminated mock/silent upload fallback when OAuth credentials are unset in [src/publisher/youtube_client.py](file:///d:/youtube-projects/LastDayOnEarth/src/publisher/youtube_client.py), raising `PublishingError` instead of returning mock video URLs to prevent accidental deletion of un-uploaded files.
  - Added unit test suite in `tests/test_cron_mode.py` verifying preservation of input video on upload disabled, pipeline crashes, and unconfirmed uploads.

## [1.3.2] - 2026-09-28

### Changed
- **Scheduled Pipeline Interval**: Increased GitHub Actions cron frequency from every 4 hours (`0 */4 * * *`) to every 3 hours (`0 */3 * * *`), running 8 times daily. Reduces waiting time for newly dropped Google Drive recordings before automated processing, upload, and success email delivery.

## [1.3.1] - 2026-09-28


### Fixed
- **YouTube `invalidTags` (HttpError 400) Video Upload Rejection**:
  - Identified root cause preventing YouTube video upload and subsequent success email notification: YouTube Data API wraps keywords containing spaces in double quotes when calculating the serialized length against the 500-character ceiling, which pushed tag strings to ~542 characters.
  - Updated `generate_video_tags` in [src/publisher/metadata_generator.py](file:///d:/youtube-projects/LastDayOnEarth/src/publisher/metadata_generator.py) to accurately account for YouTube quotation marks and comma separators, with a safe 400-character ceiling.
  - Sanitized keywords to strip forbidden characters (angle brackets `<`, `>`, commas `,`, double quotes `"`) and handle acronyms (`LDoE`) cleanly.
  - Implemented automatic retry with safe minimal core keywords in [src/publisher/youtube_client.py](file:///d:/youtube-projects/LastDayOnEarth/src/publisher/youtube_client.py) if YouTube API returns `invalidTags`, ensuring uploads never abort.
  - Added unit tests for serialized YouTube tag length validation and upload retry on `invalidTags` in `tests/test_dynamic_tags.py` and `tests/test_youtube_client.py`.

## [1.3.0] - 2026-09-27


### Added
- **7-Day Drive Output Video Retention & Auto-Purge**:
  - Implemented `cleanup_old_output_videos(retention_days=7)` in [src/ingestion/drive_client.py](file:///d:/youtube-projects/LastDayOnEarth/src/ingestion/drive_client.py).
  - Automatically identifies and permanently deletes videos in `Output/videos/` older than 7 days using file creation timestamps and name-based fallback parsing.
  - Added configurable `output_retention_days` to `GoogleDriveSettings` and `.env.example`.
- **Daily Drive Processed Folder Purge**:
  - Implemented `cleanup_processed_folder()` in [src/ingestion/drive_client.py](file:///d:/youtube-projects/LastDayOnEarth/src/ingestion/drive_client.py) to purge the `Processed` folder daily and immediately after pipeline runs.
  - Direct auto-deletion of duplicate recordings found in `Input` without sending them to `Processed`.
- **Unit Test Suite Expansion**: Added unit tests in `tests/test_drive_client.py` bringing total passed tests to 50.

## [1.2.0] - 2026-09-27

### Added
- **Dynamic ~50 Trending Hashtags & Tag Engine**:
  - Implemented `DynamicTagGenerator` in [src/publisher/metadata_generator.py](file:///d:/youtube-projects/LastDayOnEarth/src/publisher/metadata_generator.py).
  - Dynamically extracts gameplay events and episode titles to generate ~50 trending hashtags tailored to the specific gameplay actions.
  - Multi-cluster contextual engine with seeded rotation guarantees unique, non-repetitive combinations across episodes while preserving core LDoE identity.
  - Google Gemini AI integration with offline local algorithmic fallback.
  - Dynamically generates up to 500 characters of YouTube video keyword tags (`metadata.tags`).
- **Unit Test Suite**: Added `tests/test_dynamic_tags.py` with 6 dedicated test cases bringing test suite to 48 passing tests.

## [1.1.0] - 2026-09-26

### Added
- **Front-Loaded Dynamic Title Management (`TitleManager`)**:
  - Event-aware dynamic title synthesis that extracts actual gameplay achievements (crafting benches, smelting, storage, raids) into high-impact hook leads.
  - Front-loaded formulas keeping primary hooks within the first 45 characters, avoiding mobile app truncation.
  - Generates 3 title variations per video: Action Hook, Curiosity/Story Challenge, and Clean Walkthrough Guide.
  - Persistent series episode tracking in `data/series_tracker.json` with automatic episode numbering (`#1`, `#2`, `#3`...).
- **Automated High-Impact Custom Thumbnail Generator (`ThumbnailGenerator`)**:
  - Intelligent keyframe selection extracting gameplay frames during active player workshop & bench tasks (>=30s) rather than loading/intro screens.
  - Dynamic color grading via FFmpeg filter (`eq=contrast=1.12:brightness=0.02:saturation=1.25,unsharp=5:5:0.8:5:5:0.0`) optimizing visuals for YouTube's dark mode UI.
  - Crisp, modern dark-mode pill badge overlay (`#EPISODE 01` / series tag) in the top-left corner using Pillow.
  - Native YouTube API thumbnail upload integration via `youtube.thumbnails().set()`.
- **YouTube "First Look" Metadata Excellence**:
  - Enforced `00:00` start timestamp requirement enabling YouTube's interactive timeline scrubber chapters.
  - Formatted 2-line above-the-fold description hook specifically tailored for mobile and search snippet previews.
  - Clean soundtrack list, attribution, and top 25 curated hashtags.
- **Unit & Integration Test Suite**:
  - Added `tests/test_title_manager.py` and `tests/test_thumbnail_generator.py`, bringing total tests to 42 (all passing).

## [0.6.0] - 2026-09-24

### Added
- **Immediate Input Video Deletion**:
  - Raw gameplay recordings in Google Drive are now permanently deleted from `Input` immediately upon video processing and publication, preventing duplicate processing on scheduled cron cycles.
  - Added `delete_video` to `GoogleDriveClient` with automatic fallback to Google Drive Trash if hard deletion is restricted by permissions.
  - Added configurable local input deletion via `delete_input_after_processing` setting and CLI flags (`--delete-input`, `--keep-input`).
- **YouTube Pre-Upload Duplicate Guard**: `YouTubeClient.upload_video` now inspects recent channel uploads for identical titles prior to inserting, completely halting duplicate uploads at the API gateway.
- **Pytest Configuration**: Added `pytest.ini` configuring standard test discovery paths.

### Fixed
- **Drive-Cron Processing Reentrancy**: Decoupled Input video deletion from secondary Drive Output uploads so that network or quota failures during archiving do not leave raw videos lingering in `Input`.
- Cleaned up pending duplicate recording from Google Drive Input.

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
