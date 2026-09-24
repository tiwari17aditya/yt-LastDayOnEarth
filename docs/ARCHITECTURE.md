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
[ Google Drive: MyDrive -> youtube-projects -> LastDayOnEarth -> Input ]
             │
             │ (GitHub Actions cron: '0 */4 * * *' - 6 times daily)
             ▼
[ Workflow Orchestrator: src/main.py drive-cron ]
             │
 ┌───────────┴─────────────────────────────────────────────────────────────────┐
 │ 1. Ingestion: Google Drive API v3 (Strict safety boundary lock)            │
 │ 2. Privacy Guard: Redacts only real phone/OS popups (preserves HUD/username) │
 │ 3. Gameplay AI: 1-sec sleek action cues ("Global Map", "Crafting", etc.)   │
 │ 4. Audio Engine: 20 Soothing non-copyrighted CC-BY 4.0 tracks with ducking   │
 │ 5. Video Processor: FFmpeg composite render (veryfast preset, 60fps)        │
 │ 6. Publisher: YouTube Data API v3 upload & rich SEO metadata (Public)       │
 │ 7. Playlist Manager: Dedicated playlist auto-discovery & video assignment   │
 │ 8. Input Video Cleanup: Immediately deletes raw video from Drive Input      │
 │ 9. Drive Output: Uploads video & metadata to Output/videos & Output/metadata │
 │ 10. Notifier: Google Gmail API v1 rich HTML notification dispatch           │
 │ 11. Storage Tracker: Appends execution record to data/history.json          │
 └───────────┬─────────────────────────────────────────────────────────────────┘
             │
             ├──► [ YouTube Channel (Published / Public in Dedicated Playlist) ]
             ├──► [ Google Drive: Output/videos & Output/metadata ]
             ├──► [ Google Drive: Input Video Deleted Immediately ]
             └──► [ Gmail Notification (Direct via Gmail API) ]
```

---

## 3. Module Boundaries & Interfaces

### 3.1 Ingestion (`src/ingestion/`)
- **Responsibility**: Detect, download, and delete/archive candidate gameplay files from Google Drive.
- **Interface**: `BaseIngestionClient`
  - `list_pending_videos() -> List[RemoteFile]`
  - `download_video(file_id: str, dest_path: Path) -> Path`
  - `delete_video(file_id: str) -> None`
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
- **Responsibility**: Formulate engaging, SEO-optimized rotating titles with date format `(DD Mon, YYYY)`, description with chapter markers, 50 trending hashtags, direct Public upload via YouTube Data API v3, and automated dedicated playlist management.
- **Interface**: `BasePublisher`
  - `generate_metadata(video_title: str, events: List[GameplayEvent]) -> VideoPublishMetadata`
  - `upload_video(video_path: Path, metadata: VideoPublishMetadata) -> str`
  - `get_or_create_playlist(youtube, title: str, description: str, privacy_status: str) -> Optional[str]`
  - `add_video_to_playlist(youtube, video_id: str, playlist_id: str) -> bool`

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
