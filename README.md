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
- Python 3.12+
- FFmpeg 6.0+ (compiled with `libass` and `libx264`)
- Google Cloud Project with Drive API & YouTube Data API v3 enabled
- Gemini API Key

### Installation

1. **Clone & Setup Virtual Environment**:
   ```bash
   python -m venv .venv
   # Windows PowerShell
   .venv\Scripts\Activate.ps1
   # Linux/macOS
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Configure Environment**:
   ```bash
   copy .env.example .env
   # Edit .env with your API keys and SMTP credentials
   ```

3. **Verify Installation**:
   ```bash
   python -m pytest tests/
   ```

4. **Run Local Pipeline**:
   ```bash
   python -m src.main process --input sample_gameplay.mp4 --local
   ```

---

## Documentation Links

- [System Architecture](docs/ARCHITECTURE.md)
- [Developer Guide & Testing](docs/DEVELOPMENT.md)
- [Changelog](CHANGELOG.md)

---

## License

This project is licensed under the MIT Open Source License.
