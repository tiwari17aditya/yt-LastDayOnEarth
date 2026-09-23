# Implementation Plan: Automated Last Day on Earth Video Processing & Publishing Pipeline

Build a cloud-oriented, open-source, automated pipeline that ingests recorded *Last Day on Earth: Survival* gameplay videos from Google Drive, performs automated privacy protection (PII blurring), generates timed gameplay context subtitles, mixes royalty-free background music, uploads to YouTube with AI-generated metadata, sends Gmail/SMTP notifications, and maintains logs for weekly/monthly reporting.

---

## User Review Required

> [!IMPORTANT]
> **Cloud Architecture Recommendation**: 
> To satisfy the requirement of **no permanently running local computer**, **no dedicated paid server**, and **100% free-tier tooling**, we recommend:
> 1. **Compute Engine**: **GitHub Actions** (Ubuntu runner with 2-core CPU, 7GB RAM, pre-installed FFmpeg & Python, 6-hour execution window, 2,000 free minutes/month for private repos or unlimited for public).
> 2. **Trigger**:
>    - **Option A (Instant)**: A lightweight **Google Apps Script** running inside Google Drive on a 5-minute timer (or Drive trigger) that pings GitHub's `workflow_dispatch` API whenever a new video appears in `Input/Input 1`.
>    - **Option B (Scheduled)**: A GitHub Actions scheduled cron workflow (e.g. runs every hour) that checks the Google Drive folder for new files.
>    - **Local Hybrid**: A standalone Python CLI (`python -m ldoe_pipeline run-local ...`) so you can also run jobs locally on your Windows machine whenever you want.
> 3. **AI Provider for Subtitles & Metadata**: Google Gemini Flash API (`gemini-2.5-flash` or `gemini-1.5-flash`) via the Google AI free tier (generous free rate limit per day, natively accepts video and image keyframes).
> 4. **Storage & Database**: Google Drive for video files + Google Sheets (or a lightweight GitHub-stored SQLite/JSON log) for reporting records.

> [!WARNING]
> **YouTube API Quotas & OAuth2**:
> - YouTube Data API v3 allocates a default free quota of **10,000 units per day**.
> - Uploading 1 video costs **1,600 units**, meaning you can upload up to **6 videos per day** on the free tier.
> - Video upload requires an OAuth2 Client ID & Secret and a one-time generated Refresh Token (Service Accounts cannot upload videos to regular YouTube channels). We will provide a simple one-click authentication script to generate this token.

---

## Proposed System Architecture

```text
[ Google Drive: Input/Input 1 ]
             │
             │ (Google Apps Script trigger or Scheduled cron)
             ▼
[ GitHub Actions Runner (Cloud) OR Local Windows CLI ]
             │
      ┌──────┴──────────────────────────────────────┐
      │  1. Ingestion: Download from Drive API      │
      │  2. Privacy Guard: OCR + Bounding Box Blur  │
      │  3. Gameplay AI: Keyframe Context & Subs   │
      │  4. Audio Engine: Royalty-Free Music Mix    │
      │  5. FFmpeg Render: Transcode & Sub Burn-in  │
      │  6. Metadata AI: Title, Description, Tags   │
      │  7. YouTube Publisher: YouTube v3 API       │
      │  8. Notification: Gmail SMTP Alert          │
      │  9. Logger: Record stats for Reports        │
      └─────────────────────────────────────────────┘
             │
             ├──► [ YouTube Channel (Published Video) ]
             ├──► [ Email Notification (Success / Failure) ]
             └──► [ Weekly & Monthly Report Cron ]
```

---

## Proposed Pipeline Components & Modules

### 1. Ingestion Module (`src/ingestion/`)
- Connects to Google Drive using Google Drive API v3.
- Monitors target folder path: `Input/Input 1`.
- Downloads candidate video files (`.mp4`, `.mkv`, `.mov`).
- Marks processed files (moves to an `Input/Processed/` or `Archive/` folder in Google Drive to prevent duplicate processing).

### 2. Privacy & Personal Data Redaction (`src/privacy/`)
- Samples video frames at regular intervals or analyzes motion triggers.
- Runs OCR (`EasyOCR` / `pytesseract`) + Regex and pattern matching for:
  - Email addresses (`[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+`)
  - Phone notification banners (Android/iOS push notifications, SMS alerts)
  - Account usernames / IDs (excluding safe in-game UI text)
- Preserves in-game HUD (health bar, minimap, inventory slots, sneak button, action buttons).
- Generates dynamic blur coordinates and outputs an FFmpeg filter (`boxblur` / `delogo`) to obscure sensitive screen portions while keeping gameplay crystal clear.

### 3. Gameplay Context & Subtitle Generator (`src/subtitles/`)
- Extracts keyframe snapshots or short video segment intervals.
- Uses Gemini Vision API with a custom system prompt grounded in *Last Day on Earth: Survival* lore, locations, and mechanics:
  - Locations: Home Base, Pine Bushes/Grove/Woods, Limestone Ridge/Cliffs, Motel, Bunker Alfa/Bravo, Farm, Blackport PD, Factory, Port, Laboratory.
  - Enemies: Roaming Zombie, Fast Biter, Floater Bloater, Toxic Abomination, Frenzied Giant, The Blind One.
  - Actions: Looting chests, Sneak attack, Chopping pine trees, Mining iron ore, Healing with bandages.
- Generates formatted ASS (Advanced SubStation Alpha) or SRT subtitles:
  - Modern typography (e.g. Outfit / Roboto / Montserrat).
  - Safe positioning (top-center or mid-screen lower-third, above action buttons so as not to obstruct Last Day on Earth's HUD).
  - Semitransparent dark pill background for readability against any background.

### 4. Background Music Library & Audio Mixer (`src/audio/`)
- Curate **20 verified royalty-free / Creative Commons / YouTube Audio Library safe tracks**:
  - Survival, ambient post-apocalyptic, suspense, and rhythmic electronic/lo-fi gaming themes.
  - Catalog maintained in `config/music_library.json` with Track Name, Artist, Source, License Type, and Description Attribution Text.
- Intelligent track selection: Picks suitable tracks or loops based on video duration.
- Audio mixing via FFmpeg:
  - Seamless loop using `aloop` / concat.
  - Audio ducking: Background music volume lowered (e.g. -18dB to -22dB) so zombie footsteps, gunshots, chest-opening sounds, and any commentary remain crisp and punchy.

### 5. Video Processing & Output Naming (`src/processor/`)
- FFmpeg wrapper combining video stream + privacy blur filters + audio mix + hardcoded/soft subtitles.
- Standardized naming convention: `<Original_Title>_Processed_<DDMMYYYY>.mp4`.
- Export optimized for YouTube (H.264 / AAC, 1080p/60fps or source resolution, faststart flag enabled).

### 6. YouTube Publishing Engine (`src/publisher/`)
- YouTube Data API v3 upload integration with resumable upload chunks.
- Generates:
  - SEO-rich Title (e.g., `Last Day on Earth: Survival - Motel Clear & Secret Room Looting! [Ep. 12]`)
  - Timestamps / Chapter markers from detected gameplay events.
  - Description including gameplay summary, hashtags, and music attribution.
  - Keywords / Tags (e.g., `Last Day on Earth`, `LDoE Survival`, `Bunker Alfa`, `Zombie Survival Mobile`).
  - Category ID: `20` (Gaming).
  - Configurable privacy status: `public`, `unlisted`, or `private` (default `unlisted` for safety until verified).

### 7. Notification & Reporting System (`src/notifications/`)
- **Email Notifications**:
  - Sent via standard SMTP (Gmail App Password or generic SMTP).
  - HTML & plain text template with video title, processing duration, YouTube link, thumbnail preview, and log summary.
  - Dedicated Failure Alert if any stage crashes.
- **Reporting Engine**:
  - Stores job records in `data/history.json` (or synced Google Sheet).
  - Weekly Report: Triggered every Sunday via cron.
  - Monthly Report: Triggered on the 1st of each month.
  - Computes processing counts, success rate, failed jobs, and links.

### 8. Automation & Cloud Orchestration (`.github/workflows/`)
- `.github/workflows/process_video.yml`: Main workflow to process newly uploaded video, triggered by `workflow_dispatch` (from Google Apps Script) or scheduled poll.
- `.github/workflows/weekly_report.yml`: Cron job for weekly summary.
- `.github/workflows/monthly_report.yml`: Cron job for monthly summary.
- `scripts/google_apps_script/DriveWatcher.gs`: Ready-to-paste Google Apps Script code to deploy on Google Drive.

---

## 20 Royalty-Free Music Tracks Catalog (Included in `config/music_library.json`)

| # | Track Name | Style / Vibe | License / Source | Attribution Required? |
|---|------------|--------------|------------------|------------------------|
| 1 | *Survival Instinct* | Dark Ambient / Tension | Incompetech (Kevin MacLeod) - CC-BY 4.0 | Yes (Auto-added to description) |
| 2 | *Zombies Approaching* | Suspense / Cinematic Drums | YouTube Audio Library (Royalty Free) | No |
| 3 | *Wasteland Scavenger* | Low-tempo post-apoc synth | Free Music Archive (CC0 Public Domain) | No |
| 4 | *Decisions* | Subtle Electronic / Lo-Fi | Incompetech - CC-BY 4.0 | Yes |
| 5 | *Aftermath* | Apocalyptic strings & drone | Incompetech - CC-BY 4.0 | Yes |
| 6 | *The Bunker* | Industrial / Dark Synth | YouTube Audio Library (Royalty Free) | No |
| 7 | *Biter Rush* | High Tension Action Beat | YouTube Audio Library (Royalty Free) | No |
| 8 | *Daybreak Patrol* | Acoustic / Hopeful Survival | Free Music Archive (CC-BY 3.0) | Yes |
| 9 | *Darkling* | Ominous drone / Investigation | Incompetech - CC-BY 4.0 | Yes |
| 10 | *Sneak Attack* | Muffled rhythm / stealth | YouTube Audio Library (Royalty Free) | No |
| 11 | *Looting Time* | Chill Beat / Gaming Lo-Fi | Free Music Archive (CC0 Public Domain) | No |
| 12 | *The Safehouse* | Warm ambient synth | YouTube Audio Library (Royalty Free) | No |
| 13 | *Corrupted World* | Cyberpunk / post-apocalyptic | Free Music Archive (CC-BY 4.0) | Yes |
| 14 | *Red Zone Trek* | Percussive tribal tension | Incompetech - CC-BY 4.0 | Yes |
| 15 | *Midnight Gathering* | Synthwave dark chill | YouTube Audio Library (Royalty Free) | No |
| 16 | *Foggy Forest* | Atmospheric nature ambient | YouTube Audio Library (Royalty Free) | No |
| 17 | *Survival Beat 01* | Electronic gaming groove | Free Music Archive (CC0 Public Domain) | No |
| 18 | *Ghost Town Exploration* | Minimalist guitar & pad | Incompetech - CC-BY 4.0 | Yes |
| 19 | *Armored Convoy* | Driving cinematic rhythm | YouTube Audio Library (Royalty Free) | No |
| 20 | *Nightfall Survival* | Dark electronic pulse | YouTube Audio Library (Royalty Free) | No |

---

## File Structure to Implement

```
LastDayOnEarth/
├── .github/
│   └── workflows/
│       ├── process_video.yml          # Cloud video processing runner
│       ├── weekly_report.yml          # Scheduled weekly email report
│       └── monthly_report.yml         # Scheduled monthly email report
├── config/
│   ├── settings.example.yaml          # Pipeline settings template
│   └── music_library.json             # 20 curated tracks with metadata & licenses
├── data/
│   └── history.json                   # Local/cloud persistent record of processed videos
├── docs/
│   ├── SETUP_GOOGLE_DRIVE.md          # Step-by-step Drive API & Apps Script setup
│   ├── SETUP_YOUTUBE_API.md           # Step-by-step YouTube OAuth2 token setup
│   └── SETUP_EMAIL_NOTIFICATION.md    # Gmail App Password configuration guide
├── scripts/
│   ├── authenticate_youtube.py        # CLI helper to obtain YouTube OAuth refresh token
│   └── google_apps_script/
│       └── DriveWatcher.gs            # Google Apps Script to trigger pipeline on upload
├── src/
│   ├── __init__.py
│   ├── main.py                        # Central pipeline orchestrator
│   ├── config.py                      # Configuration loader & validator
│   ├── ingestion/
│   │   ├── __init__.py
│   │   └── drive_client.py            # Google Drive API downloader & archiver
│   ├── privacy/
│   │   ├── __init__.py
│   │   ├── detector.py                # OCR + regex detector for sensitive info
│   │   └── blurrer.py                 # Generates blur bounding boxes / coordinates
│   ├── subtitles/
│   │   ├── __init__.py
│   │   ├── event_analyzer.py          # Gemini AI gameplay event recognition
│   │   └── subtitle_generator.py      # Formats and styles ASS/SRT subtitles
│   ├── audio/
│   │   ├── __init__.py
│   │   ├── selector.py                # Selects appropriate music track from library
│   │   └── mixer.py                   # FFmpeg audio ducking and seamless looping
│   ├── processor/
│   │   ├── __init__.py
│   │   └── video_processor.py         # FFmpeg composite render & renaming
│   ├── publisher/
│   │   ├── __init__.py
│   │   ├── metadata_generator.py      # AI generation of titles, tags, descriptions
│   │   └── youtube_client.py          # YouTube Data API v3 uploader
│   ├── notifications/
│   │   ├── __init__.py
│   │   ├── email_client.py            # Gmail/SMTP notification sender
│   │   └── report_generator.py        # Weekly & monthly statistics compiler
│   └── storage/
│       ├── __init__.py
│       └── history_tracker.py         # Job history logger (JSON/Sheets)
├── tests/
│   ├── test_privacy.py
│   ├── test_subtitles.py
│   ├── test_audio.py
│   └── test_processor.py
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```

---

## Verification Plan

### Automated Tests
1. **Privacy Detection Tests**: Unit test `test_privacy.py` with synthetic frames containing sample emails, phone numbers, and notification banners to ensure accurate bounding box detection without false positives on game HUD.
2. **Subtitle & Event Detection Tests**: Unit test `test_subtitles.py` testing ASS subtitle generation, styling syntax, and time-stamping accuracy.
3. **Audio Mixer & Looper Tests**: Unit test `test_audio.py` checking FFmpeg audio filter command generation (`amix`, `volume`, `aloop`).
4. **End-to-End Mock Run**: Dry-run the pipeline with a 15-second sample clip to verify the complete chain (Drive download mock -> privacy blur -> subtitle burn -> audio mix -> mock YouTube upload -> email notification).

### Manual Verification
1. User provides or generates Google Cloud API credentials (`client_secrets.json`) and Gmail App Password.
2. Run `python scripts/authenticate_youtube.py` to confirm channel access and receive OAuth tokens.
3. Drop a test gameplay clip in Google Drive `Input/Input 1` and verify:
   - Pipeline triggers and downloads video.
   - Blur accurately masks any sample notification.
   - Gameplay events are captioned cleanly in stylized subtitles without blocking UI.
   - Audio is looped cleanly with in-game sound preserved.
   - Video appears in YouTube Studio with correct title, tags, description, and music attribution.
   - Confirmation email arrives with direct YouTube link.
