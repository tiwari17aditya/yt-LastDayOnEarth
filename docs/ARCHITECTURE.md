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
             │ (GitHub Actions cron: '0 */3 * * *' - 8 times daily)
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
  - `list_pending_videos() -> List[RemoteFile]` *(Cross-references `HistoryTracker` and Drive records to detect and auto-delete already-published duplicates, preventing head-of-line queue deadlock)*
  - `download_video(file_id: str, dest_path: Path) -> Path`
  - `delete_video(file_id: str) -> None` *(Strict Safety Guard: called after verified confirmation of YouTube publishing or upon identifying verified historical duplicates)*
  - `mark_as_processed(file_id: str) -> None`
  - `cleanup_processed_folder() -> int`
  - `cleanup_old_output_videos(retention_days: int = 7) -> int`
  - `upload_processed_video(local_video_path: Path, ...) -> Dict[str, Any]` *(Uploads processed video to Drive Output/videos/{year}/{month})*
  - `upload_processed_short(local_short_path: Path, ...) -> Dict[str, Any]` *(Uploads companion Short to Drive Output/shorts/{year}/{month})*

### 3.2 Privacy & PII Redaction (`src/privacy/`)
- **Responsibility**: Detect personal identifiers (email addresses, phone push notifications, personal chat bubbles) in video frames and produce dynamic bounding boxes.
- **Interface**: `BasePrivacyDetector`
  - `detect_sensitive_regions(video_path: Path) -> List[BoundingBox]`
  - `generate_ffmpeg_blur_filter(bboxes: List[BoundingBox]) -> str`
- **Safeguard**: Ignores fixed game HUD elements (character health bar, minimap, quick inventory, sneak button).

### 3.3 Subtitles & Context Engine (`src/subtitles/`)
- **Responsibility**: Identify game locations (Motel, Bunker Alfa, Farm, Home Base) and actions (looting, sneak attack, zombie engagement) and format synchronized captions.
- **Components**:
  - `SubtitleGenerator`: Integrates Gemini 2.5 Flash Vision (`google-genai` multimodal keyframe analysis) with fallback OpenCV color/HUD signature heuristics and diversified non-repeating procedural event rotation.
- **Interface**: `BaseSubtitleGenerator`
  - `analyze_events(video_path: Path) -> List[GameplayEvent]`
  - `generate_subtitles(events: List[GameplayEvent], output_path: Path) -> Path`

### 3.4 Audio Engine (`src/audio/`)
- **Responsibility**: Select appropriate music track from the 20 royalty-free catalog, loop seamlessly, and duck audio under gameplay sound effects.
- **Interface**: `BaseAudioMixer`
  - `select_track(mood: str, target_duration: float) -> MusicTrack`
  - `build_audio_filter(video_audio_stream: str, music_track: MusicTrack, ducking_db: str) -> str`

### 3.5 Video Processor & Outro Animation Engine (`src/processor/`)
- **Responsibility**: Assemble video streams, blur filters, burned-in styled subtitles, mixed audio, animated brand outro tails, and vertical companion YouTube Shorts using FFmpeg into broadcast-standard video artifacts.
- **Components**:
  - `VideoProcessor`: Single-pass composite FFmpeg rendering pipeline synthesizing resolution normalization, blur filters, subtitle burning, background music ducking, and outro tail concatenation in a single filter graph, with fallback to two-pass stitching (`append_outro_tail`).
  - `ShortsGenerator` (`src/processor/shorts_generator.py`): Automatically detects peak gameplay moments (fails, rare loot, combat, workshop tips) and generates vertical 9:16 (`1080x1920`, 60fps) companion YouTube Shorts clips featuring an ambient blurred background, framed 16:9 gameplay center box, hook headers, episode badges, and footer CTAs.
  - `OutroTailGenerator` (`src/processor/outro_generator.py`): Generates 5–8 second high-energy 1080p animated outro videos featuring interactive dynamic buttons (Like, Share, Subscribe, Bell) with visual cursor interaction, neon pulse effects, and energetic audio stings.
  - `EndScreenGenerator` (`src/processor/endscreen_generator.py`): Visual template slate generator matching YouTube interactive card layout dimensions.
- **Naming Rule**: `<Original_Title>_Processed_<DDMMYYYY>.mp4`

### 3.6 Publisher & Dynamic Metadata (`src/publisher/`)
- **Responsibility**: Formulate engaging, SEO-optimized front-loaded titles, descriptions with chapter markers & ~50 dynamic trending hashtags, dynamic video tags, automated custom HD thumbnail generation, direct Public upload via YouTube Data API v3, dedicated playlist management, companion Shorts publishing with separate playlist routing, and automated decentralized cross-posting across open-source networks.
- **Components**:
  - `BasePublisher`: Abstract base interface defining metadata generation, video uploading, and companion Short publishing contracts.
  - `YouTubeClient`: Handles OAuth upload, thumbnail upload, main series playlist management, companion Short upload with dedicated Shorts playlist management (`Last Day on Earth: Survival — Official Gameplay Shorts`), and automated backlink comments.
  - `PeerTubeClient`: Open-source decentralized video hosting client implementing `BasePublisher` via PeerTube REST API v1 (federated across the global ActivityPub Fediverse).
  - `FediverseBroadcaster`: Cross-posts rich release announcements with custom thumbnails, video links, and dynamic hashtags to Mastodon and Lemmy communities.
  - `MultiPlatformPublisher`: Orchestrates primary publishing (YouTube) and non-blocking open-source mirrors and social broadcasts (PeerTube + Fediverse), preserving fail-safe pipeline semantics.
  - `TitleManager` (`src/publisher/title_manager.py`): Front-loaded high-CTR title variations, search-intent tutorial formula (`search_guide`, +37% viewer retention), Title History Anti-Repetition Guard (`is_title_repetitive` vs last 10 episodes in `data/series_tracker.json`), persistent series episode tracking, and live YouTube channel/playlist episode auto-synchronization (`sync_with_youtube`).
  - `MetadataLocalizer` (`src/publisher/localization.py`): Multi-language translation engine producing YouTube Data API v3 `localizations` payloads and synchronized `.srt` Closed Caption tracks for key player regions: Russian (`ru`), Portuguese (`pt`), and Spanish (`es`).
  - `DynamicTagGenerator` (`src/publisher/metadata_generator.py`): Dynamically analyzes gameplay events and titles to synthesize ~50 trending hashtags via Gemini AI or multi-cluster contextual algorithmic selection with seeded rotation.
- **Interface**: `BasePublisher`
  - `generate_metadata(video_title: str, events: List[GameplayEvent], ...) -> VideoPublishMetadata`
  - `export_metadata_json(metadata: VideoPublishMetadata, output_json_path: Path) -> Path`
  - `upload_video(video_path: Path, metadata: VideoPublishMetadata) -> str`
  - `upload_captions(youtube: Any, video_id: str, events: List[Any], languages: List[str]) -> Dict[str, str]`
  - `publish_all(video_path: Path, metadata: VideoPublishMetadata) -> MultiPlatformPublishResult` (in `MultiPlatformPublisher`)

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
