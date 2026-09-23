Here’s a cleaner, more structured version of your requirements:

---

# Automated Video Processing & YouTube Publishing Workflow

I want to build an automated, cloud-based workflow for processing and publishing my recorded **Last Day on Earth: Survival** gameplay videos.

## 1. Fetch Videos from Google Drive

* Monitor a specific **Google Drive folder** (`Input 1` inside the `Input` folder) where I will upload my recorded gameplay videos.
* When a new video is detected, automatically fetch it for processing.
* The workflow should avoid depending on permanent local storage or a dedicated server wherever possible.

## 2. Video Processing

For every uploaded gameplay video, the system should:

### Privacy / Personal Data Protection

* Detect and remove or obscure any personally identifiable or sensitive information visible in the recording.
* Examples could include:

  * Email addresses
  * Usernames or account information
  * Notifications
  * Personal messages
  * Other accidentally captured personal information
* **Do not modify, remove, or alter legitimate in-game information or gameplay content.**

### Subtitles / Gameplay Context

Generate properly timed subtitles/captions that explain what is happening in the gameplay.

For example:

* `Leaving Home Base`
* `Entering Motel`
* `Searching Motel Room 2`
* `Collected: Bottles of Water`
* `Encountered: Fast Biter`
* `Returning to Home Base`

The subtitles should:

* Be synchronized with the relevant gameplay events.
* Use appropriate typography, formatting, positioning, and transparency.
* Remain clearly visible to viewers.
* Avoid covering important in-game UI elements.
* Maintain a consistent visual style throughout the video.

Where possible, gameplay events and item information should be derived from reliable **Last Day on Earth: Survival** manuals, documentation, or other publicly available reference material.

## 3. Background Music / Rhythms

For each video:

* Research and provide **20 suitable open-source, royalty-free, or appropriately licensed background music/rhythm/theme options** that can be used for gameplay videos.
* The music should be suitable for gaming content and should not interfere with important gameplay audio.
* Select an appropriate track/theme for the processed video.
* Where technically possible, loop the selected background track seamlessly throughout the video.
* Preserve important original gameplay sounds where appropriate.
* Maintain suitable audio levels between gameplay audio, commentary, and background music.

The licensing status of each recommended track should be clearly identified so that the music can be safely used for YouTube publishing.

## 4. Processed Video Naming

After processing, rename the resulting video using a consistent naming convention that includes:

* Original/relevant video title
* `Processed`
* Processing date in **DDMMYYYY** format

For example:

`Last_Day_on_Earth_Motel_Run_Processed_23092026.mp4`

## 5. YouTube Publishing Content

For every processed video, automatically generate the publishing metadata required for YouTube, including:

* Video title
* Description
* Relevant hashtags
* Tags/keywords
* Category
* Suggested thumbnail text/concept
* Other appropriate YouTube metadata

The generated content should be based on what actually happens in the video rather than using generic descriptions.

The workflow should initially support **YouTube**, while being designed so that additional platforms can be added later.

## 6. Automatic YouTube Publishing

After processing:

1. Upload the processed video to YouTube.
2. Apply the generated title, description, tags, and other metadata.
3. Publish the video according to the configured publishing settings.
4. Capture the resulting YouTube video URL and publishing details.

## 7. Email Notification

After successful YouTube publication, automatically send me an email through **Gmail or SMTP** containing:

* Confirmation that the video was successfully published.
* Video title.
* Processing date.
* Publication date/time.
* YouTube URL.
* Any relevant processing information or warnings.

If processing or publishing fails, send a failure notification with enough information to identify the failed stage.

## 8. Weekly & Monthly Reporting

Implement an automated reporting mechanism that sends me periodic reports by email.

### Weekly Report

The weekly report should include:

* Number of videos processed.
* Number successfully published.
* Number of failed videos.
* Video titles.
* YouTube URLs.
* Processing/publication dates.
* Processing or publishing errors.
* Any other useful workflow statistics.

### Monthly Report

The monthly report should provide the same information aggregated for the month, along with useful overall statistics such as:

* Total videos received.
* Total videos processed.
* Total videos published.
* Failed processing/publishing jobs.
* Processing success rate.
* Publication success rate.

If YouTube API data is available, the report can later be extended with metrics such as views, likes, comments, watch time, and other publishing analytics.

## 9. Technology Requirements

The entire solution should prioritize:

* **Open-source technologies**
* **Free-tier services wherever practical**
* No unnecessary paid software
* No proprietary/local-only processing dependencies where avoidable
* No requirement for a permanently running local computer
* No dependency on maintaining a dedicated private server
* Cloud-based/serverless architecture where practical
* APIs and services that can be automated programmatically
* Modular architecture so components can be replaced or upgraded later

## 10. Future Extensibility

The system should be designed as a modular pipeline so that additional capabilities can be added later.

Potential future integrations include:

* TikTok
* Instagram
* Facebook
* X
* Other video platforms
* Additional cloud-storage providers
* Automated thumbnail generation
* Advanced gameplay/event detection
* YouTube analytics
* Cross-platform publishing
* AI-assisted video highlights
* Automated short-form video generation

### Overall Workflow

```text
Google Drive
    ↓
Detect New Video
    ↓
Download/Access Video
    ↓
Privacy & Personal Data Detection
    ↓
Gameplay/Event Analysis
    ↓
Generate Time-Based Subtitles
    ↓
Generate/Select Background Music
    ↓
Video + Audio + Subtitles Processing
    ↓
Generate YouTube Metadata
    ↓
Rename Processed Video
    ↓
Upload to YouTube
    ↓
Verify Publication
    ↓
Send Success/Failure Email
    ↓
Store Publishing/Processing Metadata
    ↓
Weekly Report ──────┐
                    ├──→ Email
Monthly Report ─────┘
```

**Core objective:** Build a largely automated, open-source/free, cloud-oriented pipeline that takes a raw gameplay recording from Google Drive and turns it into a privacy-checked, captioned, enhanced, properly titled and documented YouTube video, publishes it, notifies me of the result, and maintains enough metadata to generate weekly and monthly reports.
