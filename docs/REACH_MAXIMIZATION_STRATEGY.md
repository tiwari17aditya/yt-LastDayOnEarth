# Last Day on Earth: Audience Growth & Global Reach Strategy

**Branch:** `feature/audience-reach-maximizer`  
**Target:** Global Algorithmic Reach, High-CPM Demographics, and Cross-Platform Virality  

---

## 1. Demographic Alignment & Audience Geography

Based on global survival game analytics, mobile store data, and official player demographics for *Last Day on Earth: Survival* (140M+ installs):

| Region | Market Characteristics | Optimization Directives |
| :--- | :--- | :--- |
| **United States & North America** | ~31% of global survival gaming market; Highest CPM / ad-revenue tier; English-speaking. | Front-loaded high-CTR English titles; SEO keywords targeting high-intent guide searches (Bunker Alfa, Chopper, F2P). |
| **Russia & Eastern Europe** | Kefir! home territory; Consistently Top 3 globally in downloads & active player base. | Automated Russian (`ru`) title & description localization via YouTube API; Russian subtitle / CC tracks. |
| **Brazil & Latin America** | Top 3 download region on Google Play; Extreme passion for mobile survival/action games. | Automated Portuguese (`pt`) and Spanish (`es`) metadata localizations; Portuguese subtitle tracks. |

*(Note: China has high installs, but YouTube is blocked, so localization prioritizes EN, RU, and PT).*

---

## 2. Technical Architecture & Implementation Plan

```text
┌────────────────────────────────────────────────────────────────────────┐
│                   Audience Reach Maximizer Pipeline                    │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
       ┌────────────────────────────┼────────────────────────────┐
       ▼                            ▼                            ▼
┌──────────────────────┐  ┌──────────────────────┐  ┌──────────────────────┐
│  1. Localization     │  │  2. High-Intent SEO  │  │ 3. Community Loops   │
│     Engine           │  │     Title System     │  │    & Comment Hook    │
├──────────────────────┤  ├──────────────────────┤  ├──────────────────────┤
│ • YouTube API v3     │  │ • Tutorial & Hacks   │  │ • Pinned Question    │
│   localizations dict │  │   (+37% retention)   │  │   Bank (Chopper,     │
│   (en, ru, pt)       │  │ • High-volume search │  │   Bunker, ATV)       │
│ • Multilingual CC    │  │   queries (Alfa,     │  │ • "The Grind"        │
│   track generation   │  │   Chopper, Farming)  │  │   Empathy Prompts    │
└──────────────────────┘  └──────────────────────┘  └──────────────────────┘
                                    │
                                    ▼
                          ┌──────────────────────┐
                          │ 4. Virality & Shorts │
                          │    Distribution      │
                          ├──────────────────────┤
                          │ • High-Emotion / Fail│
                          │   Moments (30s-45s)  │
                          │ • Discord / Reddit   │
                          │   Deep-Linked        │
                          │   Timestamp Chapters │
                          └──────────────────────┘
```

---

## 3. Engineering Workflows for Feature Development

### Phase 1: Metadata Localization & Subtitle Generation (`src/publisher/localization.py`)
- Define `MetadataLocalizer` supporting automated translation/mapping of video titles and descriptions into Russian (`ru`) and Portuguese (`pt`).
- Update `YouTubeClient.upload_video` to supply the `localizations` property in the YouTube Data API v3 insert request with `snippet.defaultLanguage: "en"`.
- Support uploading multi-language captions/subtitles via YouTube Data API (`captions.insert`).

### Phase 2: Search-Friendly Tutorial & Guide Titles (`src/publisher/title_manager.py`)
- Incorporate high-ranking search formulas:
  - `"Fastest Way to Clear [Location] (F2P Guide)"`
  - `"How to Get the Chopper Fast in Last Day on Earth"`
  - `"Ultimate Weapon Durability & Resource Saving Guide"`
  - `"How to Prepare for [Location/Event] (Zero Loss)"`
- Add search-optimized tags targeting specific player pain points (Bunker Alfa floor 2/3, Farm blue chest, Chopper gas tank, Titanium mining).

### Phase 3: Community Retention & Engagement Mechanics (`src/publisher/youtube_client.py` & `scripts/post_engagement_comments.py`)
- Expand creator comment generator with high-converting community questions:
  - Chopper / vehicle level comparisons: *"What level is your Chopper right now?"*
  - Bunker / Farm weapon discussions: *"What is your go-to budget weapon for the Spooky Farm?"*
  - Empathy with the grind: *"How long did it take you to find your first engine part / ATV transmission? Let me know below!"*
- Auto-pin creator comments upon upload to stimulate the first-hour engagement velocity required by the recommendation algorithm.

### Phase 4: Shareable Timestamps & High-Emotion Shorts Highlights (`src/processor/shorts_generator.py`)
- Enhance chapter descriptions with shareable milestone markers (`00:00 - Base Prep`, `05:23 - Bunker Alfa Floor 2`, `14:10 - Opening the Chest`) optimized for linking in Reddit (`r/LastDayonEarthGame`) and Discord.
- Add preset detection in the Shorts generator to clip high-stakes moments (near-death escapes, loss of rare loot, opening rare chests) into vertical 9:16 Shorts with CTA linking to the full episode.

---

## 4. Expected Impact on Channel Metrics

1. **Click-Through Rate (CTR):** Expected +20–35% lift in Eastern Europe and Latin America through native language titles in search/browse.
2. **Audience Retention:** +25–37% retention boost by structuring content around tutorial/problem-solving beats.
3. **Engagement Velocity:** 2x–3x increase in comment volume within the critical 0–2 hour post-upload window via pinned community questions.
4. **Referral Traffic:** Increased organic shares on Reddit/Discord due to precise chapter markers.
