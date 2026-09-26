# Last Day on Earth: Survival — Pipeline Enhancements & Roadmap

This document outlines the architectural enhancements completed in the recent development sessions, the currently staged features ready for integration, and the prioritized roadmap for the next development session.

---

## 1. Staged & Validated Enhancements (In `session/today-complete-session`)

The following features were developed, tested with 48/48 passing tests, and safely preserved in the backup branch [`session/today-complete-session`](https://github.com/tiwari17aditya/yt-LastDayOnEarth/tree/session/today-complete-session) (Commit `8633b23`):

### 1.1 Dynamic Timeline & Event Analyzer (`src/subtitles/event_analyzer.py`)
* Replaced static mock timestamps with OpenCV computer vision analysis.
* Automatically detects video duration via `ffprobe` and samples frames across the entire video.
* Identifies real in-game activities (Base building, crafting, workbench, furnace smelting, chest storage, global map).
* Guarantees interactive YouTube chapters starting strictly at `00:00`.

### 1.2 16:9 Studio HD Thumbnail Engine (`src/processor/thumbnail_generator.py`)
* **Aspect Ratio:** Generates native 16:9 (`1280x720`) HD thumbnails, eliminating black bars and distorted stretching.
* **Mobile HUD Removal:** Applied symmetrical 28% focus-crop (`crop=iw*0.72:ih*0.72`) to eliminate on-screen touch joysticks, dynamic island notch, and mobile attack buttons.
* **Cinematic Vignette:** Added smooth radial corner shading to focus attention on the central hero character and base layout.
* **Studio Gamer Plate:** High-contrast dark glass plate (`rgba(12, 15, 20, 235)`) with gold accent border (`#FFB300`), flame-orange episode tag, and bold white hook text with drop shadow in the safe top-left corner.

### 1.3 Natural Title Manager (`src/publisher/title_manager.py`)
* Generates clean, human-crafted Title Case titles (e.g. `Workshop & Smelting + Blueprint Upgrades! | LDoE Survival #8`).
* Enforces the single conjunction rule to prevent repetitive `& &` ampersands.
* Excludes mundane transition keywords (`Global Map Navigation`, `Entering Base`, `Loading`).
* Synchronizes sequential episode numbers across `data/series_tracker.json`.

### 1.4 Description & Metadata Formatting (`src/publisher/youtube_client.py`)
* Strictly excludes soundtrack and Creative Commons licensing blocks from YouTube descriptions.
* Replaced the 23-hashtag block with 3 clean, featured tags (`#LastDayOnEarth #LDoE #ZombieSurvival`).
* Added visual divider bars (`────────────────────────────────────────`) for readability.

### 1.5 Dedicated YouTube Growth & Reach Monitor (`src/monitor/growth_tracker.py`)
* Real-time metrics engine dedicated strictly to the Last Day on Earth series.
* Tracks subscriber gains, view velocity, like ratios, and comments.
* Persists historical snapshots in `data/growth_history.json`.
* Registered custom skill and slash command: `/youtube-growth-monitor` (and `/yt-growth`).

---

## 2. Next Up: Priority Tasks for Next Session

When resuming, execute the following steps in sequence:

### Priority 1: Pull & Integrate Staged Session
* Checkout and merge the validated session into `main`:
  ```bash
  git checkout main
  git merge session/today-complete-session --ff-only
  git push origin main
  ```
* Run test suite to verify 48/48 green tests: `pytest`

### Priority 2: Episode #8 Automated Upload & Playlist Assignment
* Ingest the next raw gameplay recording from Google Drive input folder.
* Execute full pipeline:
  1. Audio normalization, ducking, and ambient music mixing.
  2. Dynamic computer vision timeline analysis and subtitle generation.
  3. 16:9 Studio HD thumbnail generation for Episode #8.
  4. YouTube upload with title: `Workshop & Smelting + Blueprint Upgrades! | LDoE Survival #8`.
  5. Auto-assignment to dedicated playlist: `Last Day on Earth: Survival — Official Gameplay Series`.
  6. Auto-increment series tracker to Episode #9.

### Priority 3: First-Hour Engagement Automation
* Implement an automated first-hour pinned comment loop:
  * When a video is uploaded, auto-post a pinned discussion question (e.g. *"Which workshop room should we upgrade next: Gunsmith Table or Medical Lab? Drop your tips below!"*).
  * Boosts initial viewer interaction signals within the first 60 minutes to trigger YouTube browse recommendations.

### Priority 4: Recurring Growth Monitor (Cron Hook)
* Set up a recurring background check via the `schedule` tool or cron:
  ```python
  schedule(
      CronExpression="0 9 * * *",
      Prompt="Run python -m src.monitor.growth_tracker, inspect delta subscriber/view gains for Last Day on Earth, and flag any new viewer comments.",
      IsDaemon=True
  )
  ```

### Priority 5: YouTube Shorts Vertical Clipping Pipeline
* Build an automated 30-45 second vertical highlight extractor (`src/processor/shorts_extractor.py`):
  * Crop center 9:16 vertical ratio for mobile feeds.
  * Extract peak action (e.g., zombie raid, weapon crafting).
  * Auto-upload as YouTube Short with pinned comment linking directly to the full series episode to drive subscriber conversions.
