# Automated Last Day on Earth Video Pipeline

An automated, modular, cloud-friendly workflow for processing and publishing *Last Day on Earth: Survival* gameplay videos to YouTube.

## Overview

The pipeline automates the end-to-end publishing journey:
1. **Google Drive & Local Ingestion**: Monitors incoming gameplay video uploads (`Input/Input 1`), paginating Drive queries and sorting chronologically by mobile device recording timestamp (`ScreenRecording_MM-DD-YYYY HH-MM-SS`) with automatic historical backfill priority to preserve series storyline continuity and sequential episode numbering.
2. **Privacy Protection & Automated Ad Cutting**: Scans video frames to detect and cleanly excise in-game mobile commercial advertisements (rewarded ads, countdown timers) and redacts sensitive personal popups while strictly preserving the player username and game HUD.
3. **Gameplay Context & Subtitles**: Generates synchronized in-game commentary and authentic chapter markers using Gemini 2.5 Flash Vision multimodal keyframe analysis, backed by a Title History Anti-Repetition Guard preventing consecutive duplicate episode phrasings.
4. **Interactive AI Voice Commentary & Multi-Language Dubbing**: Generates continuous, soft-spoken survival walkthrough commentary dynamically ducked over royalty-free background music via FFmpeg sidechain compression, with automated companion multi-language dubs and closed captions for German, Spanish, Russian, and French.
5. **Royalty-Free Audio Engine**: Integrates a curated catalog of 20 royalty-free survival and gaming tracks, seamlessly looping and ducking background music.
6. **FFmpeg Video Composite**: Hardcodes stylized subtitles and renders high-definition, YouTube-optimized video with standardized naming convention (`<Title>_Processed_<DDMMYYYY>.mp4`).
7. **AI Metadata Generation**: Crafts tailored YouTube titles, structured descriptions with concise chapter timestamps, game tags, and music licensing attributions.
8. **YouTube Publishing**: Uploads directly to YouTube via YouTube Data API v3.
9. **Notifications & Periodic Reporting**: Delivers immediate email alerts upon completion/failure, plus automated weekly and monthly aggregation reports.

---

## Directory Structure

```
LastDayOnEarth/
├── .github/workflows/          # GitHub Actions CI/CD & Cron jobs
├── config/
│   ├── music_library.json     # 20 curated royalty-free tracks catalog
│   └── settings.example.yaml  # YAML configuration template
├── data/                      # Persistent history and tracking records
├── docs/
│   ├── ARCHITECTURE.md        # Comprehensive technical architecture
│   └── DEVELOPMENT.md         # Local setup, testing & developer workflows
├── logs/                      # Machine-readable structured logs (daily rotated)
├── scripts/                   # CLI utilities, OAuth helpers & Google Apps Script
├── src/
│   ├── ingestion/             # Google Drive API downloader & archiver
│   ├── privacy/               # Sensitive data OCR detector & frame blurrer
│   ├── subtitles/             # Event analysis & ASS/SRT caption generator
│   ├── audio/                 # Music library selector & audio mixer
│   ├── processor/             # FFmpeg wrapper & composite engine
│   ├── publisher/             # YouTube uploader & metadata generator
│   ├── notifications/         # SMTP email dispatcher & report aggregator
│   ├── storage/               # Execution history tracker
│   ├── config.py              # Central environment configuration
│   ├── exceptions.py          # Unified structured error handling
│   ├── logging_config.py      # Structured machine-readable logger
│   └── main.py                # Pipeline CLI & workflow orchestrator
├── tests/                     # Unit and integration test suite
├── .env.example               # Environment variables template
├── .gitignore                 # Git ignore rules
├── CHANGELOG.md               # Version history
└── requirements.txt           # Python dependencies
```

---

## Quickstart

### Prerequisites
- Python 3.11+
- FFmpeg 6.0+ (compiled with `libass` and `libx264`)
- Google Cloud Project with Drive API, YouTube Data API v3, and Gmail API enabled

### Google Cloud Setup (One-Time)
1. Enable **Google Drive API**, **YouTube Data API v3**, and **Gmail API** in Google Cloud Console.
2. Create an OAuth 2.0 Desktop Application Client ID.
3. Run the interactive setup helper:
   ```bash
   python scripts/setup_google_auth.py
   ```
4. This helper guides one-time browser approval, creates `config/token.json`, and prints the GitHub Secrets to configure:
   - `GCP_CLIENT_ID`
   - `GCP_CLIENT_SECRET`
   - `GCP_REFRESH_TOKEN`
   - `NOTIFICATION_RECIPIENTS`

### Google Drive Folder Architecture
The pipeline enforces a strict folder containment rule locked to `MyDrive -> youtube-projects -> LastDayOnEarth`:
- **Input Recordings**: Place new raw gameplay recordings in `Input/`.
- **Automatic Deletion on Processing**: Once a recording is rendered and published, it is permanently deleted from `Input/` immediately to prevent duplicate runs on subsequent scheduled cron cycles.
- **Output Storage**: Published videos and companion metadata JSON are uploaded to:
  - `Output/videos/YYYY/MM/video_ddmmyyyy.mp4`
  - `Output/metadata/YYYY/MM/metadata_ddmmyyyy.json`
- **Duplicate Prevention**: Multi-layered duplicate protection:
  - YouTube channel pre-flight duplicate check prevents re-uploading identical episode titles.
  - Native MD5 checksum scanning automatically filters duplicate uploads.
  - Automatic suffix disambiguation resolves same-day output collisions (`video_ddmmyyyy_1.mp4`).

### Dedicated YouTube Playlist
All uploaded episodes are published directly as **Public** and automatically organized into the channel's dedicated series playlist:
- **Playlist**: `Last Day on Earth: Survival — Official Gameplay Series` (ID: `PLJPzVNVZwaGY`)

### Running the Pipeline
```bash
# Continuous local watcher daemon (checks Google Drive Input every 60s)
python -m src.main watch --interval 60

# Inspect Drive Input without processing (dry run)
python -m src.main drive-cron --dry-run

# Run scheduled Drive ingestion and processing once
python -m src.main drive-cron --limit 1

# Process a specific local video directly (with optional --delete-input or --keep-input)
python -m src.main process --input "sample_gameplay.mp4" --local [--delete-input | --keep-input] [--force]

# Automatically sync Google Cloud credentials to GitHub Actions repository secrets
python scripts/sync_github_secrets.py
```

### Production CLI Tools & Operations

```bash
# Playlist Management (Audit, Chronological Sorting #1 -> #N, and Deduplication)
python scripts/manage_playlist.py --audit
python scripts/manage_playlist.py --sort
python scripts/manage_playlist.py --dedup

# Vertical YouTube Shorts (9:16) Auto-Clipper
python scripts/generate_short.py --video data/output/gameplay.mp4 --start 45.0 --duration 35.0 --episode 12

# Inspect Scheduled YouTube Release Queue
python -m src.main queue-status
python -m src.main queue-status --sync

# Cinematic Animated Outro Tail with Smooth Fade-Out/In Transition
python scripts/generate_animated_outro.py

# Sync Static Video & Audio Assets with Google Drive
python -m src.main sync-assets --download   # Pull missing assets from Drive
python -m src.main sync-assets --upload     # Mirror local assets to Drive

# Channel Video Duration Distribution Analysis
python scripts/analyze_video_durations.py

# Channel Growth & Retention Performance Digest
python scripts/generate_channel_digest.py
python scripts/generate_channel_digest.py --email

# Creator Engagement First Comments Manager
python scripts/post_engagement_comments.py --video-id <ID> --episode <NUM>
python scripts/post_engagement_comments.py --all-episodes

# Multi-Language Closed Captions (.srt) Uploader (EN, RU, PT, ES)
python scripts/upload_video_captions.py --video-id <ID>

# Publish Reach-Maximized Sample Demonstration Video
python scripts/publish_sample_reach_video.py --privacy unlisted

# High-CTR Cinematic Grunge Thumbnail Engine
python scripts/generate_thumbnail.py --episode 13 --upload --video-id <ID>
```

### GitHub Actions Automation
A scheduled workflow (`.github/workflows/scheduled_pipeline.yml`) runs aligned with creator release rhythms:
- **Weekdays (Mon–Fri)**: 2 times daily at **3:00 PM IST** (`09:30 UTC`) and **7:00 PM IST** (`13:30 UTC`) (`30 9,13 * * 1-5`).
- **Weekends (Sat–Sun)**: 4 times daily at **11:00 AM IST** (`05:30 UTC`), **2:00 PM IST** (`08:30 UTC`), **5:00 PM IST** (`11:30 UTC`), and **8:00 PM IST** (`14:30 UTC`) (`30 5,8,11,14 * * 6,0`).
- Connects to Google Drive API directly (no local file sync needed) and checks `MyDrive/youtube-projects/LastDayOnEarth/Input`.
- If no videos are pending, exits cleanly in ~15 seconds.
- When videos are pending: downloads, renders with AI commentary & soothing music, uploads to YouTube as **`private`**, applies native YouTube scheduled release (`publishAt`) into the next sequential slot (**2 videos/day on weekdays, 3 videos/day on weekends**), records the video in `data/publishing_queue.json`, cleans Drive Input, and dispatches a notification!

---

## Documentation Links

- [System Architecture](docs/ARCHITECTURE.md)
- [Developer Guide & Testing](docs/DEVELOPMENT.md)
- [Changelog](CHANGELOG.md)

---

## License

This project is licensed under the MIT Open Source License.
