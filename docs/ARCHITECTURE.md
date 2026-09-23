# System Architecture

## 1. Architectural Philosophy

The **Automated Last Day on Earth Video Pipeline** follows strict software engineering principles:
- **Modular & Component-Driven**: Every stage of the pipeline implements an independent module interface with loose coupling.
- **Resilient & Fail-Safe**: Failures in non-critical stages (e.g., subtitle stylization, background music) degrade gracefully rather than aborting the pipeline when avoidable. Critical failures trigger structured email alerts with full root-cause telemetry.
- **Zero-Cost & Serverless First**: Optimized to run inside free GitHub Actions runners (up to 6 hours continuous runtime) or on a local developer workstation, eliminating the need for paid VPS/dedicated servers.
- **Strict Separation of Concerns**: Storage, AI analysis, audio/video transformation, and publication are completely isolated.

---

## 2. High-Level System Architecture

```text
[ Google Drive: Input/Input 1 ]
             │
             │ (Google Apps Script webhook or GitHub Actions cron)
             ▼
[ Workflow Orchestrator: src/main.py ]
             │
 ┌───────────┴───────────────────────────────────────────────┐
 │ 1. Ingestion: Download raw recording via Drive API v3    │
 │ 2. Privacy Guard: OCR + Bounding Box dynamic blur        │
 │ 3. Gameplay AI: Gemini Vision context & ASS captions      │
 │ 4. Audio Engine: Royalty-Free Music Ducking & Looping     │
 │ 5. Video Processor: FFmpeg composite render               │
 │ 6. Publisher: AI SEO metadata & YouTube Data API upload   │
 │ 7. Notifier: SMTP dispatch (success/failure)              │
 │ 8. Storage Tracker: Appends execution record to history   │
 └───────────┬───────────────────────────────────────────────┘
             │
             ├──► [ YouTube Channel (Published / Unlisted) ]
             ├──► [ Email Notification (Operator Alert) ]
             └──► [ Weekly & Monthly Summary Cron ]
```

---

## 3. Module Boundaries & Interfaces

### 3.1 Ingestion (`src/ingestion/`)
- **Responsibility**: Detect, download, and archive candidate gameplay files from Google Drive.
- **Interface**: `BaseIngestionClient`
  - `list_pending_videos() -> List[RemoteFile]`
  - `download_video(file_id: str, dest_path: Path) -> Path`
  - `mark_as_processed(file_id: str) -> None`

### 3.2 Privacy & PII Redaction (`src/privacy/`)
- **Responsibility**: Detect personal identifiers (email addresses, phone push notifications, personal chat bubbles) in video frames and produce dynamic bounding boxes.
- **Interface**: `BasePrivacyDetector`
  - `detect_sensitive_regions(video_path: Path) -> List[BoundingBox]`
  - `generate_ffmpeg_blur_filter(bboxes: List[BoundingBox]) -> str`
- **Safeguard**: Ignores fixed game HUD elements (character health bar, minimap, quick inventory, sneak button).

### 3.3 Subtitles & Context Engine (`src/subtitles/`)
- **Responsibility**: Identify game locations (Motel, Bunker Alfa, Farm, Home Base) and actions (looting, sneak attack, zombie engagement) and format synchronized captions.
- **Interface**: `BaseSubtitleGenerator`
  - `analyze_events(video_path: Path) -> List[GameplayEvent]`
  - `render_subtitles(events: List[GameplayEvent], output_format: str = "ass") -> Path`

### 3.4 Audio Engine (`src/audio/`)
- **Responsibility**: Select appropriate music track from the 20 royalty-free catalog, loop seamlessly, and duck audio under gameplay sound effects.
- **Interface**: `BaseAudioMixer`
  - `select_track(mood: str, target_duration: float) -> MusicTrack`
  - `build_audio_filter(video_audio_stream: str, music_track: MusicTrack, ducking_db: str) -> str`

### 3.5 Video Processor (`src/processor/`)
- **Responsibility**: Assemble video streams, blur filters, burned-in styled subtitles, and mixed audio using FFmpeg into a YouTube-ready MP4.
- **Naming Rule**: `<Original_Title>_Processed_<DDMMYYYY>.mp4`

### 3.6 Publisher (`src/publisher/`)
- **Responsibility**: Formulate engaging, SEO-optimized title, description with chapter markers, and tags, followed by upload via YouTube Data API v3.
- **Interface**: `BasePublisher`
  - `generate_metadata(events: List[GameplayEvent]) -> VideoMetadata`
  - `upload_video(video_path: Path, metadata: VideoMetadata) -> UploadResult`

### 3.7 Notifications & Reporting (`src/notifications/`)
- **Responsibility**: Format and send HTML status emails for each job, and aggregate statistics for weekly and monthly reports.

---

## 4. Error Handling Standard

All exceptions inherit from `PipelineError` in `src/exceptions.py`. Every error report strictly identifies:
- **Operation**: Name of the active process.
- **Component**: Source module (e.g. `PrivacyDetector`, `YouTubePublisher`).
- **File**: Affected input/output file.
- **Root Cause**: Underlying technical cause / traceback.
- **Recovery / Action**: Recommended mitigation or fallback path.
- **Execution Status**: Whether the workflow recovered or aborted.

---

## 5. Structured Logging Architecture

Logs follow machine-readable JSON/structured format stored under:
```
logs/YYYY-MM-DD/application.log
```
Every log entry contains:
- `timestamp`: ISO-8601 UTC timestamp.
- `level`: DEBUG | INFO | WARNING | ERROR | CRITICAL.
- `component`: Originating module name.
- `operation`: Current execution phase.
- `message`: Contextual description.
- `payload`: Structured dictionary of metadata and execution metrics.
