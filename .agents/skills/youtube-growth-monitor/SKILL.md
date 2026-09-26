---
name: youtube-growth-monitor
description: Dedicated YouTube platform reach and audience growth monitor. Purely monitors subscriber gains, view velocity, like-to-view ratios, comment threads, and algorithmic reach to maximize conversions and engagement.
---

# YouTube Growth & Platform Reach Monitor

Use this skill whenever the user asks to monitor YouTube platform reach, track subscriber growth, inspect video likes/comments, evaluate audience retention, or optimize future uploads for algorithmic amplification.

## Slash Command & Trigger
* **Slash Command:** `/youtube-growth-monitor` (or `/yt-growth`)
* **Triggers:**
  * "monitor youtube platform reach"
  * "track our subscriber gains, comments, likes"
  * "how are our videos performing on YouTube?"
  * "check comment sentiment and audience engagement"

---

## 1. Quick Execution: Generating Growth Intelligence

To perform a real-time audit and record a delta snapshot:

```bash
python -m src.monitor.growth_tracker
```

This autonomously:
1. Connects to the YouTube Data API v3 (`channels.list`, `videos.list`, `commentThreads.list`).
2. Pulls live channel subscriber count, total channel views, and video counts.
3. Retrieves real-time views, likes, and comments for every series episode in `data/series_tracker.json`.
4. Computes engagement rates: `(likes + comments) / views * 100%`.
5. Compares against the previous snapshot in `data/growth_history.json` to calculate delta gains (`+subs`, `+views`, `+likes`, `+comments`).
6. Flags unreplied comments to boost community signals.
7. Produces an executive markdown report at `output/growth_audit_report.md`.

---

## 2. Setting Up Recurring Automated Monitoring

To monitor reach on an automated recurring schedule, use the `schedule` tool:

```python
# Schedule daily reach check every 24 hours at 9:00 AM UTC
schedule(
    CronExpression="0 9 * * *",
    Prompt="Run python -m src.monitor.growth_tracker, inspect delta subscriber/view gains, and alert the user if any video reaches a breakout milestone or receives urgent comments.",
    IsDaemon=True
)
```

---

## 3. Growth Optimization Directives

When auditing channel growth, analyze:
1. **Top Hook Identification:** Compare titles with high views vs. zero views. Highlight keywords that generate organic searches (e.g., `Workshop Smelting`, `Base Storage`).
2. **First-Hour Engagement Loop:** Suggest pinning an engaging question in the comment section within 60 minutes of upload.
3. **End Screen Call-To-Action:** Verify that videos link directly to the official series playlist to boost session watch time.
4. **Shorts Funnel:** Recommend 30-45 second gameplay highlights as YouTube Shorts linking directly to the main long-form episode.
