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
             │ (GitHub Actions crons aligned with IST rhythms:
             │  - Weekdays: 3:00 PM IST & 7:00 PM IST ['30 9,13 * * 1-5']
             │  - Weekends: 11:00 AM, 2:00 PM, 5:00 PM, 8:00 PM IST ['30 5,8,11,14 * * 6,0'])
             ▼
[ Workflow Orchestrator: src/main.py drive-cron ]
             │
 ┌───────────┴─────────────────────────────────────────────────────────────────┐
 │ 1. Ingestion: Google Drive API v3 (Strict safety boundary lock)            │
 │ 2. Privacy Guard: Redacts real phone/OS popups (preserves HUD/username)    │
 │ 3. Gameplay AI: 1-sec sleek action cues ("Global Map", "Crafting", etc.)   │
 │ 4. Audio Engine: CC-BY 4.0 tracks with dynamic sidechain ducking           │
 │ 5. Commentary Engine: Edge-TTS neural commentary walkthrough + downtime    │
 │ 6. Video Processor: FFmpeg composite render (veryfast preset, 60fps)        │
 │ 7. Queue Manager: Calculates next open slot (2/day weekdays, 3/day weekends)│
 │ 8. Publisher: YouTube Data API v3 upload as Private with native publishAt  │
 │ 9. Playlist Manager: Dedicated playlist auto-discovery & video assignment   │
 │ 10. Input Cleanup: Immediately deletes raw video from Drive Input          │
 │ 11. Drive Output: Uploads video & metadata to Output/videos & Output/meta  │
 │ 12. Notifier: Google Gmail API v1 rich HTML notification dispatch          │
 │ 13. Queue & History Tracker: Persists data/publishing_queue.json & history │
 └───────────┬─────────────────────────────────────────────────────────────────┘
             │
             ├──► [ YouTube Channel (Uploaded Private, Scheduled for Public Release) ]
             ├──► [ Publishing Queue Ledger (data/publishing_queue.json) ]
             ├──► [ Google Drive: Output/videos & Output/metadata ]
             ├──► [ Google Drive: Input Video Deleted Immediately ]
             └──► [ Gmail Notification (Direct via Gmail API) ]
```

---

## 3. Module Boundaries & Interfaces

### 3.1 Ingestion (`src/ingestion/`)
- **Responsibility**: Detect, download, and delete/archive candidate gameplay files from Google Drive.
- **Interface**: `BaseIngestionClient`
  - `list_pending_videos() -> List[RemoteFile]` *(Paginates Drive inventory, parses mobile recording timestamps `ScreenRecording_MM-DD-YYYY HH-MM-SS`, sorts chronologically with historical backfill priority, and cross-references `HistoryTracker` to auto-delete duplicates)*
  - `download_video(file_id: str, dest_path: Path) -> Path`
  - `delete_video(file_id: str) -> None` *(Strict Safety Guard: called after verified confirmation of YouTube publishing or upon identifying verified historical duplicates)*
  - `mark_as_processed(file_id: str) -> None`
  - `cleanup_processed_folder() -> int`
  - `cleanup_old_output_videos(retention_days: int = 7) -> int`

### 3.2 Privacy, PII Redaction & In-Game Advertisement Excision (src/privacy/ and src/processor/)
- **Responsibility**: Detect personal identifiers in video frames, and automatically identify and excise mobile in-game commercial advertisements (rewarded ads, countdown banners, install endcards) watched during gameplay.
- **Components**:
  - PrivacyDetector (src/privacy/detector.py): Scans video for sensitive notification popups while strictly preserving the player username, health bar, and in-game chat.
  - AdDetector (src/privacy/ad_detector.py): Scans gameplay keyframes to detect commercial breaks via Gemini 2.5 Flash Vision multimodal analysis, with zero-dependency native Windows OCR (Windows.Media.Ocr), EasyOCR, and OpenCV HUD absence/pillarbox signature heuristics.
  - AdRemover (src/processor/ad_remover.py): Computes keep intervals and performs FFmpeg sample-accurate stream trimming (	rim/trim) and concatenation (concat) to seamlessly excise advertisement segments with zero A/V desync, and shifts subsequent subtitle cues and chapter timestamps backwards to maintain perfect synchronization.
- **Interface**:
  - AdDetector.detect_ads(video_path: Path) -> List[AdSegment]
  - AdRemover.remove_ads(input_video: Path, ad_segments: List[AdSegment], output_video: Optional[Path]) -> Path
  - AdRemover.adjust_event_timestamps(events: List[GameplayEvent], ad_segments: List[AdSegment]) -> List[GameplayEvent]
- **Safeguard**: Ignores fixed game HUD elements (character health bar, minimap, quick inventory, sneak button).

### 3.3 Subtitles & Context Engine (`src/subtitles/`)
- **Responsibility**: Identify game locations (Motel, Bunker Alfa, Farm, Home Base) and actions (looting, sneak attack, zombie engagement) and format synchronized captions.
- **Components**:
  - `SubtitleGenerator`: Integrates Gemini 2.5 Flash Vision (`google-genai` multimodal keyframe analysis) with fallback OpenCV color/HUD signature heuristics and diversified non-repeating procedural event rotation.
- **Interface**: `BaseSubtitleGenerator`
  - `analyze_events(video_path: Path) -> List[GameplayEvent]`
  - `generate_subtitles(events: List[GameplayEvent], output_path: Path) -> Path`

### 3.4 Audio & AI Commentary Engine (`src/audio/`)
- **Responsibility**: Select appropriate music track from the 20 royalty-free catalog, loop seamlessly, duck audio under gameplay sound effects, synthesize continuous AI companion voice walkthroughs, generate synchronized dialogue subtitles, and produce multi-lingual companion dub packages.
- **Components**:
  - `AudioMixer`: Manages royalty-free music library selection, duration probing, and multi-track concatenation loops (`create_random_loop_sequence`).
  - `CommentaryEngine` (`src/audio/commentary_engine.py`):
    - Synthesizes dynamic, domain-grounded commentary dialogue across video durations using `edge-tts`.
    - Personas: Casual (`en-US-GuyNeural`), Soft Walkthrough Companion (`CommentaryPersona.SOFT`), Energetic (`en-US-ChristopherNeural`), and Tactical (`en-US-AndrewNeural`).
    - Soft Voice Acoustics: Warm vocal EQ curve (`highpass=75,lowpass=7800,equalizer=3200Hz -2dB`), -16 LUFS loudness target, gentle -22dB BGM bed, and 3.5 sidechain ducking ratio.
    - Synchronized Subtitles: Emits burned-in Full HD (`1920x1080`) ASS dialogue subtitles (`Style: Commentary`) and matching `.srt` closed caption files for spoken walkthrough narration.
    - Multi-Language Regional Dubs: Translates cues into German (`de`), Spanish (`es`), Russian (`ru`), and French (`fr`) using Gemini AI with gaming vocabulary fallback, synthesizing companion `.m4a` dubs and `.srt` caption files indexed via `multilingual_manifest.json`.
    - Fills timeline silence gaps during gameplay downtime/roaming with 36+ survival strategy and advancement topics (~25s interval).
    - Dynamic FFmpeg Sidechain Compression: Routes voice through `asplit=2` to trigger `sidechaincompress(threshold=0.02, ratio=3.5)` against ambient background music (`-22dB`), ducking it smoothly while keeping spoken voice at `-16 LUFS` broadcast level via `amix(normalize=0)`.
    - Fail-Safe Fallback: Degradation path catches synthesis errors and automatically falls back to standard background music loop without halting video rendering or publishing.
- **Interface**:
  - `BaseAudioMixer`: `select_track(mood: str, target_duration: float) -> MusicTrack`, `build_audio_filter(...) -> str`
  - `CommentaryEngine`: `generate_script(...) -> List[CommentaryCue]`, `synthesize_all_cues(...)`, `generate_subtitles(...)`, `translate_cues(...)`, `synthesize_regional_audio_track(...)`, `generate_multilingual_package(...)`, `mix_commentary_with_bgm(...)`, `generate_commentary_track(...)`

### 3.5 Video Processor & Outro Animation Engine (`src/processor/`)
- **Responsibility**: Assemble video streams, blur filters, burned-in styled subtitles, mixed audio, and animated brand outro tails using FFmpeg into a broadcast-standard YouTube-ready MP4.
- **Components**:
  - `VideoProcessor`: Single-pass composite FFmpeg rendering pipeline synthesizing resolution normalization, blur filters, subtitle burning, background music ducking, and outro tail concatenation in a single filter graph, with fallback to two-pass stitching (`append_outro_tail`).
  - `Silent Mode Defense (`mute_raw_audio`)`: Eliminates microphone ambient noise and rogue audio leakage by routing isolated royalty-free background music directly when gaming in silent mode (`MUTE_RAW_AUDIO=true`).
  - `OutroTailGenerator` (`src/processor/outro_generator.py`): Generates 5–8 second high-energy 1080p animated outro videos featuring interactive dynamic buttons (Like, Share, Subscribe, Bell) with visual cursor interaction, neon pulse effects, and energetic audio stings.
  - `EndScreenGenerator` (`src/processor/endscreen_generator.py`): Visual template slate generator matching YouTube interactive card layout dimensions.
- **Naming Rule**: `<Original_Title>_Processed_<DDMMYYYY>.mp4`

### 3.6 Publisher, Release Queue & Dynamic Metadata (`src/publisher/`)
- **Responsibility**: Formulate engaging, SEO-optimized front-loaded titles, descriptions with chapter markers & ~50 dynamic trending hashtags, dynamic video tags, automated custom HD thumbnail generation, staged private YouTube uploads with native scheduled public release (`publishAt`), queue management across weekdays/weekends, dedicated playlist management, and automated decentralized cross-posting across open-source networks.
- **Components**:
  - `BasePublisher`: Abstract base interface defining metadata generation and video uploading contracts.
  - `PublishingQueueManager` (`src/publisher/queue_manager.py`):
    - Persistent release ledger (`data/publishing_queue.json`) managing episode sequences and time-slot allocations.
    - Cadence Matrix: Weekdays (2 videos/day at 3:00 PM & 7:00 PM IST) and Weekends (3 videos/day at 11:00 AM, 4:00 PM & 8:00 PM IST).
    - Multi-video sequencing: When multiple videos are ingested in batch, calculates consecutive open slots across upcoming days without slot collisions or series skips.
    - Synchronization: Automatically transitions matured releases from `SCHEDULED` to `PUBLISHED` when the scheduled time passes.
  - `YouTubeClient`: Handles OAuth upload, thumbnail upload, playlist management, and video assignment on YouTube. Sets initial privacy to `private` and applies `status.publishAt` so YouTube automatically releases videos publicly at the designated timetable. Includes automatic API error recovery with fallback to private upload.
  - `PeerTubeClient`: Open-source decentralized video hosting client implementing `BasePublisher` via PeerTube REST API v1 (federated across the global ActivityPub Fediverse).
  - `FediverseBroadcaster`: Cross-posts rich release announcements with custom thumbnails, video links, and dynamic hashtags to Mastodon and Lemmy communities (automatically deferred for scheduled private videos until public).
  - `MultiPlatformPublisher`: Orchestrates primary publishing (YouTube) and non-blocking open-source mirrors and social broadcasts (PeerTube + Fediverse), preserving fail-safe pipeline semantics.
  - `TitleManager` (`src/publisher/title_manager.py`): Front-loaded high-CTR title variations, search-intent tutorial formula (`search_guide`, +37% viewer retention), Title History Anti-Repetition Guard (`is_title_repetitive` vs last 10 episodes in `data/series_tracker.json`), persistent series episode tracking, and live YouTube channel/playlist episode auto-synchronization (`sync_with_youtube`).
  - `MetadataLocalizer` (`src/publisher/localization.py`): Multi-language translation engine producing YouTube Data API v3 `localizations` payloads and synchronized `.srt` Closed Caption tracks for key player regions: German (`de`), Spanish (`es`), Russian (`ru`), French (`fr`), and Portuguese (`pt`).
  - `DynamicTagGenerator` (`src/publisher/metadata_generator.py`): Dynamically analyzes gameplay events and titles to synthesize ~50 trending hashtags via Gemini AI or multi-cluster contextual algorithmic selection with seeded rotation.
  - `scripts/resolve_copyright_claims.py`: Channel-wide copyright and territorial restriction auditing, batch-fixing, and YouTube Studio dispute resolution copy generator.
- **Interface**: `BasePublisher`
  - `generate_metadata(video_title: str, events: List[GameplayEvent], ...) -> VideoPublishMetadata`
  - `export_metadata_json(metadata: VideoPublishMetadata, output_json_path: Path) -> Path`
  - `upload_video(video_path: Path, metadata: VideoPublishMetadata) -> str`
  - `upload_captions(youtube: Any, video_id: str, events: Optional[List[Any]] = None, languages: Optional[List[str]] = None, caption_tracks: Optional[Dict[str, Tuple[Path, str]]] = None) -> Dict[str, str]`
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
