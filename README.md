# Automated Last Day on Earth Video Pipeline

An automated, modular, cloud-friendly workflow for processing and publishing *Last Day on Earth: Survival* gameplay videos to YouTube.

## Overview

The pipeline automates the end-to-end publishing journey:
1. **Google Drive Ingestion**: Monitors incoming gameplay video uploads (`Input/Input 1`).
2. **Privacy Protection & PII Obfuscation**: Scans video frames with OCR to detect and redact sensitive personal information (emails, notifications, phone IDs) while preserving game HUD.
3. **Gameplay Context & Subtitles**: Generates synchronized in-game commentary and event captions using Gemini AI vision models grounded in *Last Day on Earth* lore and locations.
4. **Royalty-Free Audio Engine**: Integrates a curated catalog of 20 royalty-free survival and gaming tracks, seamlessly looping and ducking background music.
5. **FFmpeg Video Composite**: Hardcodes stylized subtitles and renders high-definition, YouTube-optimized video with standardized naming convention (`<Title>_Processed_<DDMMYYYY>.mp4`).
6. **AI Metadata Generation**: Crafts tailored YouTube titles, structured descriptions with chapter timestamps, game tags, and music licensing attributions.
7. **YouTube Publishing**: Uploads directly to YouTube via YouTube Data API v3.
8. **Notifications & Periodic Reporting**: Delivers immediate email alerts upon completion/failure, plus automated weekly and monthly aggregation reports.

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
- **Processed Archive**: Processed recordings are automatically moved to `Processed/` and verified.
- **Output Storage**: Published videos and companion metadata JSON are uploaded to:
  - `Output/videos/YYYY/MM/video_ddmmyyyy.mp4`
  - `Output/metadata/YYYY/MM/metadata_ddmmyyyy.json`
- **Duplicate Prevention**: Native MD5 checksum scanning automatically filters duplicate uploads and disambiguates output file name collisions.

### Dedicated YouTube Playlist
All uploaded episodes are published directly as **Public** and automatically organized into the channel's dedicated series playlist:
- **Playlist**: `Last Day on Earth: Survival — Official Gameplay Series` (ID: `PLJPzVNVZwaGY`)

### Running the Pipeline
```bash
# Inspect Drive Input without processing (dry run)
python -m src.main drive-cron --dry-run

# Run scheduled Drive ingestion and processing
python -m src.main drive-cron --limit 1

# Process a specific local video directly (with optional --force duplicate override)
python -m src.main process --input "sample_gameplay.mp4" --local [--force]

# Automatically sync Google Cloud credentials to GitHub Actions repository secrets
python scripts/sync_github_secrets.py
```

### GitHub Actions Automation
A scheduled workflow (`.github/workflows/scheduled_pipeline.yml`) runs **6 times daily at 4-hour intervals** (`0 */4 * * *`):
- Connects to Google Drive API directly (no local file sync needed).
- Checks `MyDrive/youtube-projects/LastDayOnEarth/Input`.
- If no videos are pending, exits in ~30 seconds.
- If a video is pending, downloads, renders with soothing music & action cues, uploads to YouTube, moves the video to `Processed` in Drive, and sends a Gmail alert!

---

## Documentation Links

- [System Architecture](docs/ARCHITECTURE.md)
- [Developer Guide & Testing](docs/DEVELOPMENT.md)
- [Changelog](CHANGELOG.md)

---

## License

This project is licensed under the MIT Open Source License.
