"""Intelligent title generation and series management for YouTube publishing."""

import json
import re
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import List, Optional, Dict, Any
from src.logging_config import get_logger

logger = get_logger(component="TitleManager")


@dataclass
class TitlePackage:
    primary_title: str
    action_hook: str
    curiosity: str
    walkthrough: str
    episode_number: int = 1
    summary: str = ""
    search_guide: str = ""
    anti_repetition_applied: bool = False
    similarity_score: float = 0.0
    avoided_recent_title: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class TitleManager:
    """Manages episode numbering, dynamic event-based title synthesis, and candidate generation."""

    def __init__(
        self,
        tracker_file: Path = Path("data/series_tracker.json"),
        series_name: str = "Last Day on Earth: Survival",
        series_prefix: str = "LDoE",
        title_style: str = "action_hook",
        episode_numbering: bool = True,
        max_title_length: int = 100,
        sync_youtube: bool = False,
    ) -> None:
        self.tracker_file = tracker_file
        self.series_name = series_name
        self.series_prefix = series_prefix
        self.title_style = title_style
        self.episode_numbering = episode_numbering
        self.max_title_length = max_title_length
        self.sync_youtube = sync_youtube
        self._synced_with_youtube = False
        self._ensure_tracker_exists()

    def _ensure_tracker_exists(self) -> None:
        self.tracker_file.parent.mkdir(parents=True, exist_ok=True)
        if not self.tracker_file.exists():
            initial_data = {
                "series_name": self.series_name,
                "current_episode": 1,
                "completed_episodes": [],
            }
            try:
                self.tracker_file.write_text(json.dumps(initial_data, indent=2), encoding="utf-8")
                logger.info(f"Initialized new series tracker at {self.tracker_file}")
            except Exception as e:
                logger.warning(f"Could not initialize series tracker: {e}")

    def _read_tracker_episode(self) -> int:
        if not self.tracker_file.exists():
            return 1
        try:
            data = json.loads(self.tracker_file.read_text(encoding="utf-8"))
            return int(data.get("current_episode", 1))
        except Exception as e:
            logger.warning(f"Error reading current episode from tracker: {e}")
            return 1

    def _update_current_episode(self, episode_number: int) -> None:
        data = {
            "series_name": self.series_name,
            "current_episode": episode_number,
            "completed_episodes": [],
        }
        if self.tracker_file.exists():
            try:
                data = json.loads(self.tracker_file.read_text(encoding="utf-8"))
            except Exception:
                pass
        data["current_episode"] = episode_number
        try:
            self.tracker_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except Exception as e:
            logger.warning(f"Failed to update tracker with synced episode #{episode_number}: {e}")

    def sync_with_youtube(self, youtube_service: Optional[Any] = None) -> int:
        """Inspects YouTube channel/playlist to detect the highest published episode number.
        
        Ensures consecutive episode numbering across ephemeral runners (e.g. GitHub Actions)
        and updates local tracker file if YouTube reflects higher episode numbers.
        """
        self._synced_with_youtube = True
        try:
            if youtube_service is None:
                from src.google_auth import get_google_credentials
                from googleapiclient.discovery import build
                creds = get_google_credentials()
                if not creds:
                    return self._read_tracker_episode()
                youtube_service = build("youtube", "v3", credentials=creds, cache_discovery=False)

            highest_ep = 0

            # 1. Search in dedicated playlist
            try:
                p_req = youtube_service.playlists().list(part="snippet", mine=True, maxResults=50)
                p_res = p_req.execute()
                for p in p_res.get("items", []):
                    title = p.get("snippet", {}).get("title", "")
                    if "Last Day on Earth" in title or self.series_prefix.lower() in title.lower():
                        pid = p["id"]
                        pi_req = youtube_service.playlistItems().list(part="snippet", playlistId=pid, maxResults=50)
                        while pi_req:
                            pi_res = pi_req.execute()
                            for item in pi_res.get("items", []):
                                t = item.get("snippet", {}).get("title", "")
                                match = re.findall(r"#(\d+)", t)
                                if match:
                                    highest_ep = max(highest_ep, int(match[-1]))
                            pi_req = youtube_service.playlistItems().list_next(pi_req, pi_res)
            except Exception as pe:
                logger.debug(f"Playlist check during YouTube episode sync encountered: {pe}")

            # 2. Search in channel recent uploads
            try:
                ch_resp = youtube_service.channels().list(mine=True, part="contentDetails").execute()
                if ch_resp.get("items"):
                    uploads_id = ch_resp["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]
                    up_req = youtube_service.playlistItems().list(part="snippet", playlistId=uploads_id, maxResults=50)
                    up_res = up_req.execute()
                    for it in up_res.get("items", []):
                        t = it.get("snippet", {}).get("title", "")
                        if self.series_prefix.lower() in t.lower() or "last day on earth" in t.lower():
                            match = re.findall(r"#(\d+)", t)
                            if match:
                                highest_ep = max(highest_ep, int(match[-1]))
            except Exception as ue:
                logger.debug(f"Uploads check during YouTube episode sync encountered: {ue}")

            if highest_ep > 0:
                next_ep = highest_ep + 1
                tracker_ep = self._read_tracker_episode()
                if next_ep > tracker_ep:
                    logger.info(
                        f"Synchronized series episode with YouTube: highest published is #{highest_ep}. "
                        f"Updating tracker next episode from #{tracker_ep} to #{next_ep}"
                    )
                    self._update_current_episode(next_ep)
                    return next_ep
                return tracker_ep

            return self._read_tracker_episode()

        except Exception as e:
            logger.warning(f"Could not synchronize episode counter with YouTube: {e}")
            return self._read_tracker_episode()

    def get_current_episode(self, sync_youtube: Optional[bool] = None) -> int:
        should_sync = self.sync_youtube if sync_youtube is None else sync_youtube
        if should_sync and not self._synced_with_youtube:
            return self.sync_with_youtube()
        return self._read_tracker_episode()

    def advance_episode(
        self,
        title: str,
        video_id: Optional[str] = None,
        youtube_url: Optional[str] = None,
        job_id: Optional[str] = None,
    ) -> int:
        """Records the published episode with its video ID and increments the episode counter."""
        current_ep = 1
        data = {
            "series_name": self.series_name,
            "current_episode": 1,
            "completed_episodes": [],
        }
        if self.tracker_file.exists():
            try:
                data = json.loads(self.tracker_file.read_text(encoding="utf-8"))
                current_ep = int(data.get("current_episode", 1))
            except Exception as e:
                logger.warning(f"Failed to read tracker before increment: {e}")

        next_ep = current_ep + 1
        completed = data.get("completed_episodes", [])
        resolved_vid = video_id or job_id
        resolved_url = youtube_url or (f"https://youtu.be/{resolved_vid}" if resolved_vid and not resolved_vid.startswith("local") else "")

        completed.append({
            "episode": current_ep,
            "title": title,
            "video_id": resolved_vid,
            "youtube_url": resolved_url,
            "job_id": job_id or resolved_vid,
        })
        data["current_episode"] = next_ep
        data["completed_episodes"] = completed
        self._synced_with_youtube = True

        try:
            self.tracker_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
            logger.info(f"Advanced series episode from #{current_ep} to #{next_ep} (Video ID: {resolved_vid})")
        except Exception as e:
            logger.error(f"Failed to update series tracker: {e}")

        return next_ep

    def extract_key_activities(self, events: List[Any]) -> List[str]:
        """Filters out mundane loading/nav events and selects primary gameplay activities."""
        low_priority = ["global map", "entering base", "exiting", "loading", "navigation", "intro"]
        activities = []

        for ev in events:
            desc = getattr(ev, "description", "")
            if not desc:
                continue
            clean = desc.strip()
            # Skip mundane navigation or transition screens
            if any(k in clean.lower() for k in low_priority):
                continue
            if clean not in activities:
                activities.append(clean)

        if not activities and events:
            # Fallback if only navigation events were detected
            activities = [getattr(ev, "description", "").strip() for ev in events if getattr(ev, "description", "")]

        return activities

    def synthesize_hook_phrases(self, activities: List[str]) -> tuple[str, str]:
        """Transforms activity list into punchy, high-CTR action phrases in clean Title Case."""
        if not activities:
            return "Ultimate Base Survival & Workshop", "Crafting, Building & Resource Prep"

        # Map common activities into clean high-energy hook phrases
        enhancements = {
            "crafting planks": "Woodcraft & Planks",
            "weapon bench": "Weapon Workbench Setup",
            "workbench & blueprints": "Blueprint Upgrades",
            "workbench": "Workbench Crafting",
            "blueprints": "Blueprint Upgrades",
            "organizing chests": "Base Storage Optimization",
            "storage & chests": "Base Storage Optimization",
            "smelting iron": "Furnace Smelting",
            "bunker alfa": "Bunker Alfa Raid",
            "chopping trees": "Pine Log Harvest",
            "mining iron": "Iron Ore Scavenge",
            "base defense": "Zombie Horde Defense",
            "workshop & smelting": "Workshop & Smelting",
            "workshop": "Workshop Expansion",
        }

        upgraded = []
        for act in activities:
            matched = False
            for k, v in enhancements.items():
                if k in act.lower():
                    if v not in upgraded:
                        upgraded.append(v)
                    matched = True
                    break
            if not matched:
                clean_title = act.strip().title()
                if clean_title not in upgraded:
                    upgraded.append(clean_title)

        # Select top 2 activities and combine naturally
        if len(upgraded) >= 2:
            first, second = upgraded[0], upgraded[1]
            separator = " + " if ("&" in first or "&" in second) else " & "
            hook_lead = f"{first}{separator}{second}"
            sub_summary = f"{activities[0]} and {activities[1]}"
            if len(activities) > 2:
                sub_summary += f" plus {activities[2]}"
        else:
            hook_lead = upgraded[0] if upgraded else "Base Expansion"
            sub_summary = activities[0] if activities else "Base Operations"

        return hook_lead, sub_summary

    def generate_titles(
        self,
        events: List[Any],
        episode_number: Optional[int] = None,
    ) -> TitlePackage:
        """Generates 3 high-impact title candidates (Action Hook, Curiosity/Challenge, Clean Walkthrough)."""
        ep = episode_number if episode_number is not None else self.get_current_episode()
        activities = self.extract_key_activities(events)
        hook_lead, sub_summary = self.synthesize_hook_phrases(activities)

        ep_tag = f"#{ep}" if self.episode_numbering else ""

        # Formula 1: Action Hook (High CTR - Front-loads excitement)
        # e.g.: "MAX BASE STORAGE & SMELTING! | LDoE Survival #1"
        action_parts = [hook_lead]
        if ep_tag:
            action_hook_raw = f"{hook_lead}! | {self.series_prefix} Survival {ep_tag}".strip()
        else:
            action_hook_raw = f"{hook_lead}! | {self.series_name}".strip()
        action_hook = self._fit_title_length(action_hook_raw, ep_tag)

        # Formula 2: Curiosity / Challenge Hook
        # e.g.: "Can We Upgrade Our Entire Base? Workshop & Smelting | LDoE #1"
        curiosity_lead = f"Can We Survive & Upgrade? {sub_summary.title()}"
        if ep_tag:
            curiosity_raw = f"{curiosity_lead} | {self.series_prefix} {ep_tag}".strip()
        else:
            curiosity_raw = f"{curiosity_lead} | {self.series_prefix}".strip()
        curiosity = self._fit_title_length(curiosity_raw, ep_tag)

        # Formula 3: Clean Series Walkthrough / Guide
        # e.g.: "Surviving Day 1: Base Setup, Woodcraft & Smelting | LDoE"
        walkthrough_lead = f"Surviving Day {ep}: {sub_summary.title()}" if ep_tag else f"Surviving & Thriving: {sub_summary.title()}"
        walkthrough_raw = f"{walkthrough_lead} | {self.series_prefix}".strip()
        walkthrough = self._fit_title_length(walkthrough_raw, ep_tag)

        # Formula 4: Search-Optimized Tutorial / How-To Guide (+37% viewer retention)
        # e.g.: "Fastest Way to Clear Bunker Alfa (F2P Guide) | LDoE #5"
        # e.g.: "Best Base Storage & Workshop Layout Guide | LDoE #1"
        activities_lower = " ".join(activities).lower()
        if "bunker" in activities_lower:
            guide_lead = "Fastest Way to Clear Bunker Alfa (F2P Guide)"
        elif any(k in activities_lower for k in ["chopper", "bike", "motorcycle"]):
            guide_lead = "How to Get the Chopper Fast (F2P Guide)"
        elif any(k in activities_lower for k in ["smelt", "furnace", "iron"]):
            guide_lead = "Fastest Iron Smelting & Resource Farm Trick"
        elif any(k in activities_lower for k in ["storage", "chest", "organize"]):
            guide_lead = "Best Base Storage & Workshop Layout Guide"
        elif any(k in activities_lower for k in ["weapon", "gun", "gunsmith"]):
            guide_lead = "How to Save Weapon Durability & Craft Guns"
        elif any(k in activities_lower for k in ["farm", "crooked creek"]):
            guide_lead = "How to Clear Crooked Creek Farm Solo (F2P)"
        else:
            guide_lead = f"How to Farm & Master {hook_lead} Fast"

        if ep_tag:
            guide_raw = f"{guide_lead} | {self.series_prefix} {ep_tag}".strip()
        else:
            guide_raw = f"{guide_lead} | {self.series_name}".strip()
        search_guide = self._fit_title_length(guide_raw, ep_tag)

        # Select primary title according to configured title_style
        if self.title_style in ["search_guide", "tutorial_guide", "seo_guide"]:
            primary = search_guide
        elif self.title_style == "curiosity_story":
            primary = curiosity
        elif self.title_style == "clean_walkthrough":
            primary = walkthrough
        else:
            primary = action_hook

        # Anti-Repetition Guard: Cross-reference against recent episodes
        recent_titles = self.get_recent_published_titles(limit=10)
        anti_rep_applied = False
        similarity_score = 0.0
        avoided_title = ""

        is_rep, matched_recent, score = self.is_title_repetitive(primary, recent_titles, threshold=0.50)
        if is_rep:
            logger.info(
                f"Anti-Repetition Guard triggered for Episode #{ep}: primary title '{primary}' "
                f"is too similar to recent episode '{matched_recent}' (similarity: {score:.2f})"
            )
            anti_rep_applied = True
            similarity_score = score
            avoided_title = matched_recent

            # Check alternative formulas in order
            candidates = [search_guide, curiosity, walkthrough, action_hook]
            chosen_candidate = None

            for alt in candidates:
                if alt != primary:
                    alt_rep, _, _ = self.is_title_repetitive(alt, recent_titles, threshold=0.50)
                    if not alt_rep:
                        chosen_candidate = alt
                        logger.info(f"Anti-Repetition Guard selected non-repetitive alternative formula: '{alt}'")
                        break

            if chosen_candidate:
                primary = chosen_candidate
            else:
                thematic_rotations = [
                    "Bunker Alfa Infiltration & Red Crate Run",
                    "Crooked Creek Farm Clearing & Combat",
                    "High-Value Resource Scavenge & Smelting",
                    "Zombie Horde Survival & Base Fortification",
                    "Chopper Motorcycle Assembly & Fuel Run",
                    "Rare Blueprint & Workshop Blueprint Upgrades",
                ]
                used_texts = " ".join(recent_titles[:5]).lower()
                chosen_theme = None
                for theme in thematic_rotations:
                    if not any(k in used_texts for k in theme.lower().split()[:2]):
                        chosen_theme = theme
                        break
                chosen_theme = chosen_theme or thematic_rotations[ep % len(thematic_rotations)]

                if ep_tag:
                    primary = self._fit_title_length(f"{chosen_theme}! | {self.series_prefix} Survival {ep_tag}", ep_tag)
                else:
                    primary = self._fit_title_length(f"{chosen_theme}! | {self.series_name}", ep_tag)
                logger.info(f"Anti-Repetition Guard synthesized fresh thematic hook: '{primary}'")

        logger.info(
            f"Generated high-CTR title package for Episode #{ep}",
            extra_data={
                "primary": primary,
                "action_hook": action_hook,
                "curiosity": curiosity,
                "walkthrough": walkthrough,
                "search_guide": search_guide,
                "anti_repetition_applied": anti_rep_applied,
                "similarity_score": similarity_score,
                "avoided_recent_title": avoided_title,
            },
        )

        return TitlePackage(
            primary_title=primary,
            action_hook=action_hook,
            curiosity=curiosity,
            walkthrough=walkthrough,
            episode_number=ep,
            summary=sub_summary,
            search_guide=search_guide,
            anti_repetition_applied=anti_rep_applied,
            similarity_score=similarity_score,
            avoided_recent_title=avoided_title,
        )

    def get_recent_published_titles(self, limit: int = 10) -> List[str]:
        """Fetches the titles of the most recent N completed episodes from tracker file."""
        if not self.tracker_file.exists():
            return []
        try:
            data = json.loads(self.tracker_file.read_text(encoding="utf-8"))
            completed = data.get("completed_episodes", [])
            recent = [ep.get("title", "") for ep in completed if ep.get("title")]
            return list(reversed(recent[-limit:]))
        except Exception as e:
            logger.warning(f"Could not read recent titles for anti-repetition check: {e}")
            return []

    def clean_title_for_comparison(self, title: str) -> str:
        """Strips series prefixes, episode numbers, and formatting to isolate core hook keywords."""
        if not title:
            return ""
        cleaned = re.sub(r"\|\s*(LDoE|Last Day on Earth).*$", "", title, flags=re.IGNORECASE)
        cleaned = re.sub(r"#\d+", "", cleaned)
        cleaned = re.sub(r"[^\w\s]", " ", cleaned).lower()
        return " ".join(cleaned.split())

    def calculate_title_similarity(self, title_a: str, title_b: str) -> float:
        """Calculates token-overlap similarity between two titles (excluding boilerplate words)."""
        stop_words = {"and", "the", "with", "for", "plus", "part", "to", "how", "fast", "guide", "survival", "ldoe"}
        tokens_a = {w for w in self.clean_title_for_comparison(title_a).split() if len(w) > 2 and w not in stop_words}
        tokens_b = {w for w in self.clean_title_for_comparison(title_b).split() if len(w) > 2 and w not in stop_words}

        if not tokens_a or not tokens_b:
            return 0.0

        intersection = tokens_a & tokens_b
        union = tokens_a | tokens_b
        jaccard = len(intersection) / len(union)
        containment = len(intersection) / min(len(tokens_a), len(tokens_b))
        return max(jaccard, containment * 0.85)

    def is_title_repetitive(
        self,
        candidate_title: str,
        recent_titles: List[str],
        threshold: float = 0.50,
    ) -> tuple[bool, str, float]:
        """Determines whether a candidate title is too repetitive against recently published episodes."""
        for recent in recent_titles:
            score = self.calculate_title_similarity(candidate_title, recent)
            if score >= threshold:
                return True, recent, score
        return False, "", 0.0

    def _fit_title_length(self, title: str, ep_suffix: str) -> str:
        """Ensures title strictly fits under max_title_length while preserving suffix."""
        if len(title) <= self.max_title_length:
            return title

        # Truncate front while keeping suffix
        allowed_main = self.max_title_length - len(ep_suffix) - 5
        truncated = title[:allowed_main].rsplit(" ", 1)[0]
        return f"{truncated}... {ep_suffix}".strip()
