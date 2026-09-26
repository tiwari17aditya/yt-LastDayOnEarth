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
    episode_number: int
    summary: str

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
    ) -> None:
        self.tracker_file = tracker_file
        self.series_name = series_name
        self.series_prefix = series_prefix
        self.title_style = title_style
        self.episode_numbering = episode_numbering
        self.max_title_length = max_title_length
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

    def get_current_episode(self) -> int:
        if not self.tracker_file.exists():
            return 1
        try:
            data = json.loads(self.tracker_file.read_text(encoding="utf-8"))
            return int(data.get("current_episode", 1))
        except Exception as e:
            logger.warning(f"Error reading current episode from tracker: {e}")
            return 1

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

        # Select primary title according to configured title_style
        if self.title_style == "curiosity_story":
            primary = curiosity
        elif self.title_style == "clean_walkthrough":
            primary = walkthrough
        else:
            primary = action_hook

        logger.info(
            f"Generated high-CTR title package for Episode #{ep}",
            extra_data={
                "primary": primary,
                "action_hook": action_hook,
                "curiosity": curiosity,
                "walkthrough": walkthrough,
            },
        )

        return TitlePackage(
            primary_title=primary,
            action_hook=action_hook,
            curiosity=curiosity,
            walkthrough=walkthrough,
            episode_number=ep,
            summary=sub_summary,
        )

    def _fit_title_length(self, title: str, ep_suffix: str) -> str:
        """Ensures title strictly fits under max_title_length while preserving suffix."""
        if len(title) <= self.max_title_length:
            return title

        # Truncate front while keeping suffix
        allowed_main = self.max_title_length - len(ep_suffix) - 5
        truncated = title[:allowed_main].rsplit(" ", 1)[0]
        return f"{truncated}... {ep_suffix}".strip()
