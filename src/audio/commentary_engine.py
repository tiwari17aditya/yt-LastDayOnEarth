"""Automated AI Voice Commentary Engine for Last Day on Earth gameplay videos.

Provides high-engagement spoken commentary walkthrough personas (Casual, Energetic, Tactical)
synthesized via edge-tts neural voices, timeline audio positioning, broadcast-standard
audio normalization, and sidechain BGM ducking.
"""

import asyncio
import json
import math
import os
import shutil
import subprocess
import wave
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import edge_tts

from src.exceptions import CommentaryError, AudioProcessingError
from src.logging_config import get_logger

logger = get_logger(component="CommentaryEngine")


class CommentaryPersona(str, Enum):
    """Available commentary personas and presentation styles."""
    CASUAL = "casual"         # Warm, conversational, friendly gameplay walkthrough (Style 2 - Recommended)
    SOFT = "soft"             # Soft-spoken, calm, relaxing survival companion (Gentle & Soothing)
    ENERGETIC = "energetic"   # High-excitement, hype gamer, fast reactions (Style 1)
    TACTICAL = "tactical"     # Pro-survival strategist, game mechanics & raid tips (Style 3)


@dataclass
class PersonaConfig:
    """Voice configuration settings for a specific commentary persona."""
    persona: CommentaryPersona
    voice: str
    rate: str
    pitch: str
    volume: str
    description: str


# Recommended production voice mappings for edge-tts
PERSONA_PROFILES: Dict[CommentaryPersona, PersonaConfig] = {
    CommentaryPersona.CASUAL: PersonaConfig(
        persona=CommentaryPersona.CASUAL,
        voice="en-US-GuyNeural",
        rate="-3%",
        pitch="-2Hz",
        volume="-2%",
        description="Friendly, conversational gamer walkthrough companion. Soft, natural, relatable, and relaxed.",
    ),
    CommentaryPersona.SOFT: PersonaConfig(
        persona=CommentaryPersona.SOFT,
        voice="en-US-GuyNeural",
        rate="-4%",
        pitch="-2Hz",
        volume="-4%",
        description="Soft-spoken, calm, relaxing survival companion. Gentle walkthrough cadence with soothing delivery.",
    ),
    CommentaryPersona.ENERGETIC: PersonaConfig(
        persona=CommentaryPersona.ENERGETIC,
        voice="en-US-ChristopherNeural",
        rate="+4%",
        pitch="+0Hz",
        volume="+0%",
        description="High-energy, hype gamer persona. Punchy reactions, fast-paced and enthusiastic.",
    ),
    CommentaryPersona.TACTICAL: PersonaConfig(
        persona=CommentaryPersona.TACTICAL,
        voice="en-US-AndrewNeural",
        rate="-2%",
        pitch="-2Hz",
        volume="-1%",
        description="Strategic survival guide and pro walkthrough. Focused on tips, weapon durability, and mechanics.",
    ),
}


@dataclass
class CommentaryCue:
    """Represents a timed commentary dialogue entry."""
    start_time: float
    text: str
    style: CommentaryPersona = CommentaryPersona.CASUAL
    duration: float = 0.0
    audio_path: Optional[Path] = None
    topic: str = ""  # Short chapter heading for YouTube description


# Comprehensive pool of procedural commentary dialogue for Last Day on Earth
PROCEDURAL_CASUAL_TOPICS = [
    {
        "category": "inventory",
        "topic": "Storage & Inventory Sorting",
        "text": "I always like to spend a few minutes organizing storage before heading out. Having dedicated chests for raw wood, ores, and weapons saves so much time later.",
    },
    {
        "category": "progression",
        "topic": "Base Evolution & Memories",
        "text": "Looking around this base, remember when this was just a small three-by-three wooden box with a single campfire? We have come such a long way since those early grind sessions.",
    },
    {
        "category": "smelting",
        "topic": "Smelter Fuel Efficiency",
        "text": "Checking in on our smelters. A quick pro tip: turning raw wood into charcoal gives you much higher fuel efficiency than burning plain logs.",
    },
    {
        "category": "defense",
        "topic": "Honeycomb Wall Defense",
        "text": "Expanding our base perimeter today. Upgrading from basic wood to sturdy level two planks makes a huge difference when the daily zombie horde sweeps through.",
    },
    {
        "category": "horde",
        "topic": "Horde Pathing Mechanics",
        "text": "When the daily horde visits, they break two to three outer walls and pass right through. Do not waste stone on outer walls until your inner reinforced core is finished.",
    },
    {
        "category": "combat",
        "topic": "Sneak Attack Melee Strategy",
        "text": "Clearing out the perimeter with sneak attacks here. That triple damage bonus on the first strike saves a ton of weapon durability in the long run.",
    },
    {
        "category": "durability",
        "topic": "Weapon Durability Economy",
        "text": "Always keep an eye on weapon durability. For easy resource zones, craft cheap cleavers or wooden spears. Save your high-damage katanas and machetes for the bunker.",
    },
    {
        "category": "vehicle",
        "topic": "Chopper Motorcycle Assembly",
        "text": "Taking a quick look at the Chopper. Piecing together wheels, the gas tank, and engine parts is always one of the most rewarding milestones in LDoE.",
    },
    {
        "category": "watchtower",
        "topic": "Northern Watchtower & Oak",
        "text": "Once your Chopper is running, hauling the electric generator to the northern watchtower unlocks oak clearings and winter snow zones. It opens up the whole map.",
    },
    {
        "category": "recycler",
        "topic": "Recycler Scrap & Electronics",
        "text": "Our recycler is steadily running. Leveling up electronics and mechanics with spare batteries and broken flashlights is the best route to free copper and steel.",
    },
    {
        "category": "companion",
        "topic": "Canine Companion Breeding",
        "text": "Stopping by the dog crate to feed the pups. Rolling traits like Bloodhound or True Friend gives you an incredible passive boost out in the field.",
    },
    {
        "category": "true_friend",
        "topic": "True Friend Dog Ability",
        "text": "Getting a pup with True Friend takes patience, but having a dog that actually attacks zombies with you and opens secret bunker crawl spaces is unbeatable.",
    },
    {
        "category": "scouting",
        "topic": "Zone Scouting & Minimap Pacing",
        "text": "Pacing ourselves through this zone. You always want to keep one eye glued to the minimap to avoid getting cornered by spitters or roaming packs.",
    },
    {
        "category": "spitters",
        "topic": "Toxic Spitter Evasion",
        "text": "Watch out for toxic spitters! Sidestep the green spit. If you take three hits and get smelly, every zombie across the entire zone starts sprinting right at you.",
    },
    {
        "category": "bunker",
        "topic": "Bunker Alfa Ticket Farming",
        "text": "Stocking up combat tickets for Bunker Alfa. Cashing in green, yellow, and red tickets downstairs remains the most consistent source of military firearms.",
    },
    {
        "category": "wall_trick",
        "topic": "Wall Trick Doorway Technique",
        "text": "Practicing the wall trick on doorway frames is the single biggest ammo saver in LDoE. Time your melee swings right as the zombie strikes the wall.",
    },
    {
        "category": "farm",
        "topic": "Crooked Creek Farm Strategy",
        "text": "Whenever you hit Crooked Creek Farm, remember to sneak past the diseased giants if you want to conserve ammo, and let the saw cutter finish the blue crate quietly.",
    },
    {
        "category": "ravager",
        "topic": "Farm Ravager Boss Tactics",
        "text": "When fighting the Ravager at the farm, simply circle around him when he pauses to spit. He deals zero armor damage as long as you keep moving laterally.",
    },
    {
        "category": "gunsmith",
        "topic": "Gunsmith Weapon Modding",
        "text": "Fine-tuning our weapon mods at the gunsmith bench. Adding red dot optics and expanded magazines transforms even basic pistols into clearing machines.",
    },
    {
        "category": "police",
        "topic": "Blackport PD Wave Defense",
        "text": "Managing resources for the Blackport PD yard. Surviving consecutive waves without burning through all your armor is the secret to scoring purple inspector badges.",
    },
    {
        "category": "winter",
        "topic": "Winter Zone Thermal Prep",
        "text": "Getting our warm fur armor ready for the cold zones. Freezing ruins your attack speed and leaves you vulnerable, so thermal flasks and fur insulation are everything.",
    },
    {
        "category": "oak",
        "topic": "Oak Forest Woodcraft",
        "text": "Heading to the oak clearings. Always bring iron hatchets instead of basic stone ones, because regular tools cannot chop through thick oak trunks.",
    },
    {
        "category": "evolution",
        "topic": "LDoE Game Advancements",
        "text": "Looking back at how far Kefir has developed this game — from basic forest zones to drone combat, laboratory runs, and the settlement — it has been an awesome journey.",
    },
    {
        "category": "settlement",
        "topic": "Settlement Power & Barracks",
        "text": "The settlement system has completely transformed late-game progression. Routing power distribution and upgrading residential barracks gives permanent perks.",
    },
    {
        "category": "crater",
        "topic": "Multiplayer Crater Trading",
        "text": "If you haven't checked out the Crater sector recently, running multiplayer clan contracts and setting up your own shop is such a fun change of pace.",
    },
    {
        "category": "air_drop",
        "topic": "Air Drop Energy Timing",
        "text": "Air drop event tip: when an event triggers, always travel there immediately. If your survivor energy dips under 70, the map often spawns an extra trader or drop.",
    },
    {
        "category": "healer",
        "topic": "Healer Buff Strategy",
        "text": "Never ignore the healer standing near your pickup truck. Grabbing that five percent rare weapon drop buff or full energy refill before a raid gives you a massive edge.",
    },
    {
        "category": "sorting",
        "topic": "Fast-Drop Inventory Sorting",
        "text": "Keeping a designated dump chest near your base entrance saves so much time. Drop everything instantly after a run, and do deep sorting once your crates fill up.",
    },
    {
        "category": "fishing",
        "topic": "Fishing Buffs & Recipes",
        "text": "Hitting the fishing pond with professional rods and burley. Cooking catfish and trout dishes on the kitchen stove gives long-lasting buffs for boss fights.",
    },
    {
        "category": "gear_check",
        "topic": "Armor Conservation Discipline",
        "text": "Discipline with armor saves thousands of cloth and leather. Never chop wood or gather limestone in full tactical armor — keep durability fresh for real danger.",
    },
    {
        "category": "community",
        "topic": "Community Milestone Question",
        "text": "I'm curious to hear where you all are at in your survival journey right now! Are you grinding Bunker Alfa, finishing the Chopper, or building stone walls? Let me know in the comments!",
    },
    {
        "category": "crafting",
        "topic": "Workbench Resource Loops",
        "text": "Keeping our workbenches humming. Crafting thick leather, sewing bandages, and refining iron ensures you never start a mission unprepared.",
    },
    {
        "category": "resupply",
        "topic": "Health & Nutrition Routine",
        "text": "Checking our health bar and nourishment. Eating canned food and drinking water regularly prevents your survivor from slowing down during high-stress runs.",
    },
    {
        "category": "atv",
        "topic": "Late-Game ATV Transmission",
        "text": "Working toward the ATV is the ultimate long-term grind in LDoE. Stocking up car batteries, cogwheels, and transmission cases from the bravo bunker takes real dedication.",
    },
    {
        "category": "bunker_bravo",
        "topic": "Bunker Bravo Radiation Prep",
        "text": "Speaking of Bunker Bravo, radiation suits and anti-rad ampoules are mandatory. The radiation timer forces you to blitz rooms at lightning speed.",
    },
    {
        "category": "motel",
        "topic": "Motel Resource Clears",
        "text": "The motel remains one of the best low-risk loot spots for beginners. You can clear the whole building with just a spear and walk away with easy energy drinks.",
    },
]

PROCEDURAL_ENERGETIC_TOPICS = [
    {
        "category": "hype",
        "topic": "Adrenaline & Action Momentum",
        "text": "Alright survivors, let's keep the momentum going! Checking our gear, stacking the best melee weapons, and staying on high alert!",
    },
    {
        "category": "craft",
        "topic": "Furnace & Production Rush",
        "text": "Look at those furnaces burning! Production never stops on this base — turning raw ore into iron bars 24/7!",
    },
    {
        "category": "combat",
        "topic": "Rapid Zombie Elimination",
        "text": "Spotted spitters and fast biters closing in! Keep moving, don't let them surround you. That sneak attack bonus is so satisfying!",
    },
    {
        "category": "loot",
        "topic": "High-Tier Crate Looting",
        "text": "Opening up these high-tier crates... engine parts, weapon mods, and rare tickets! That is a massive score!",
    },
    {
        "category": "threat",
        "topic": "Noise Meter Threat Alert",
        "text": "Watch the noise meter! In higher zones, making too much racket brings the Big One, and that's an instant reset. Staying light and fast!",
    },
    {
        "category": "clutch",
        "topic": "Bandage Hotkey Clutch Recovery",
        "text": "Down to half health but we've got bandages hotkeyed! Quick heal, reset the fight, and back into action!",
    },
]

PROCEDURAL_TACTICAL_TOPICS = [
    {
        "category": "tactical_rule",
        "topic": "Durability & Weapon Economy",
        "text": "Key survival rule: always calculate weapon durability per enemy encounter. Avoid using firearms on standard roaming zombies — preserve guns for Frenzied Giants.",
    },
    {
        "category": "base_layout",
        "topic": "Honeycomb Perimeter Defense",
        "text": "When building your base layout, implement a honeycomb wall design. The daily horde destroys two to three outer walls, but cannot penetrate your reinforced core.",
    },
    {
        "category": "wall_trick",
        "topic": "Doorframe Wall-Trick Technique",
        "text": "Notice the engagement spacing here. Utilizing door mechanics and wall-tricking eliminates incoming damage entirely, saving both healing items and armor durability.",
    },
    {
        "category": "loot_priority",
        "topic": "High-Value Item Prioritization",
        "text": "Priority loot extracted. Always prioritize red combat tickets, aluminum wire, and factory parts over common limestone and raw pine.",
    },
    {
        "category": "resource_calc",
        "topic": "Energy Travel Calculation",
        "text": "Energy conservation principle: batch your resource runs to adjacent zones to minimize travel energy while maximizing inventory capacity.",
    },
]


class CommentaryEngine:
    """Orchestrates script synthesis, voice generation, timeline alignment, and audio ducking."""

    def __init__(self, temp_dir: Path = Path("temp/commentary")) -> None:
        self.temp_dir = temp_dir
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.last_cues: List[CommentaryCue] = []

    def get_persona_config(self, persona: CommentaryPersona) -> PersonaConfig:
        """Retrieve voice parameters for a specific persona."""
        return PERSONA_PROFILES.get(persona, PERSONA_PROFILES[CommentaryPersona.CASUAL])

    def generate_script(
        self,
        events: Optional[List[Any]] = None,
        duration: float = 900.0,
        episode_number: Optional[int] = None,
        persona: CommentaryPersona = CommentaryPersona.CASUAL,
        min_cue_interval: float = 25.0,
    ) -> List[CommentaryCue]:
        """Synthesizes high-engagement, domain-grounded LDoE commentary cues matching video duration.
        
        Dynamically distributes cues across the timeline with comfortable breathing room,
        grounding dialogue in detected gameplay events or procedural survival walkthrough topics.
        Ensures continuous, interactive commentary during roaming and free-play downtime.
        """
        ep_label = f"Episode {episode_number}" if episode_number else "our survival series"
        cues: List[CommentaryCue] = []

        # 1. Intro Hook (starts at 2.0s)
        if persona == CommentaryPersona.SOFT:
            intro_text = (
                f"Hey everyone, welcome back to Last Day on Earth. This is {ep_label}, and today we're taking a relaxed, "
                "steady pace through our base routine, organizing supplies, and heading out into the wasteland. Let's get comfortable and get to it."
            )
            intro_topic = "Soothing Intro & Base Routine"
        elif persona == CommentaryPersona.CASUAL:
            intro_text = (
                f"Hey everyone, welcome back to Last Day on Earth! In {ep_label}, we're diving into base optimization, "
                "stocking up on essential survival supplies, and heading out into the wasteland. Let's see what we can accomplish today."
            )
            intro_topic = "Introduction & Base Prep"
        elif persona == CommentaryPersona.ENERGETIC:
            intro_text = (
                f"What is up survivors! Welcome back to Last Day on Earth, {ep_label}! Today we are gearing up, "
                "raiding deep into zombie territory, and testing our base defenses. Let's get right into it!"
            )
            intro_topic = "High-Energy Intro & Objectives"
        else:  # TACTICAL
            intro_text = (
                f"Welcome survivors. This is {ep_label} of our Last Day on Earth strategic walkthrough. "
                "Today's focus is resource economy, defense optimization, and risk-managed clearing."
            )
            intro_topic = "Strategic Mission Briefing"

        cues.append(CommentaryCue(start_time=2.0, text=intro_text, style=persona, topic=intro_topic))

        # 2. Outro Hook (starts ~20-22s before end)
        outro_time = max(15.0, duration - 22.0)
        if persona == CommentaryPersona.SOFT:
            outro_text = (
                "Thank you so much for relaxing and spending some time with me on today's episode. If you enjoyed this calm walkthrough, "
                "please leave a gentle like, subscribe to keep following our survival progress, and let me know your thoughts down below. "
                "Take care, and see you next time."
            )
        elif persona == CommentaryPersona.CASUAL:
            outro_text = (
                "Thanks so much for hanging out and watching today's episode! If you enjoyed this walkthrough, "
                "please drop a thumbs up, subscribe to follow the journey, and drop a comment below with your favorite survival setup. "
                "Catch you all in the next one!"
            )
        elif persona == CommentaryPersona.ENERGETIC:
            outro_text = (
                "What a run! Drop a like if you enjoyed today's raid, hit that subscribe button for daily survival guides, "
                "and let me know in the comments: what's your go-to bunker weapon? See you in the next one!"
            )
        else:  # TACTICAL
            outro_text = (
                "That concludes today's tactical breakdown. Remember to subscribe for more in-depth LDoE raid guides, "
                "and leave your questions in the comments below. Stay sharp out there."
            )
        outro_cue = CommentaryCue(start_time=round(outro_time, 1), text=outro_text, style=persona, topic="Episode Recap & Outro")

        # 3. Middle Dialogue Cues (continuous pacing across video timeline)
        if duration >= 45.0:
            usable_start = 25.0
            usable_end = outro_time - 20.0

            # Step 1: Collect detected gameplay events if provided
            event_cues: List[CommentaryCue] = []
            if events:
                last_ev_time = 0.0
                for ev in events:
                    ev_time = getattr(ev, "start_time", None)
                    if ev_time is None or not (usable_start <= ev_time <= usable_end):
                        continue

                    if last_ev_time > 0 and (ev_time - last_ev_time < min_cue_interval):
                        continue

                    ev_type = getattr(ev, "action_type", getattr(ev, "event_type", "nav"))
                    ev_desc = getattr(ev, "description", "")

                    cue_text, cue_topic = self._format_event_cue(ev_type, ev_desc, persona)
                    event_cues.append(
                        CommentaryCue(
                            start_time=float(ev_time),
                            text=cue_text,
                            style=persona,
                            topic=cue_topic,
                        )
                    )
                    last_ev_time = float(ev_time)

            # Combine intro, event cues, and outro to identify silence gaps
            anchor_cues = [cues[0]] + event_cues + [outro_cue]
            anchor_cues.sort(key=lambda c: c.start_time)

            # Step 2: Fill gaps continuously so roaming/free time has active strategy/advancement talk
            procedural_topics = (
                PROCEDURAL_CASUAL_TOPICS
                if persona in (CommentaryPersona.CASUAL, CommentaryPersona.SOFT)
                else PROCEDURAL_ENERGETIC_TOPICS
                if persona == CommentaryPersona.ENERGETIC
                else PROCEDURAL_TACTICAL_TOPICS
            )

            final_cues: List[CommentaryCue] = [anchor_cues[0]]
            topic_idx = 0

            for i in range(len(anchor_cues) - 1):
                c_prev = anchor_cues[i]
                c_next = anchor_cues[i + 1]

                # Estimated speech duration of preceding cue (~8 seconds)
                prev_finish = c_prev.start_time + 8.0
                gap = c_next.start_time - prev_finish

                # If gap permits dialogue with natural breather, insert procedural commentary
                if gap >= (min_cue_interval + 4.0):
                    num_inserts = int(gap // (min_cue_interval + 3.0))
                    if num_inserts > 0:
                        interval = gap / (num_inserts + 1)
                        for k in range(1, num_inserts + 1):
                            insert_time = round(prev_finish + (interval * k), 1)
                            if insert_time <= usable_end:
                                item = procedural_topics[topic_idx % len(procedural_topics)]
                                topic_idx += 1
                                final_cues.append(
                                    CommentaryCue(
                                        start_time=insert_time,
                                        text=item["text"],
                                        style=persona,
                                        topic=item.get("topic", "Survival Strategy"),
                                    )
                                )

                final_cues.append(c_next)

            cues = final_cues
        else:
            cues.append(outro_cue)

        # Sort cues strictly chronologically
        cues.sort(key=lambda c: c.start_time)
        return cues

    def _format_event_cue(self, event_type: str, description: str, persona: CommentaryPersona) -> Tuple[str, str]:
        """Adapts a gameplay event into natural persona dialogue and returns (dialogue_text, topic_heading)."""
        desc_clean = description.strip() if description else "this objective"
        ev_type = (event_type or "").lower()
        if persona in (CommentaryPersona.CASUAL, CommentaryPersona.SOFT):
            if any(k in ev_type for k in ["combat", "fight", "attack", "kill"]):
                return (
                    f"Spotting enemy movement here: {desc_clean}. Taking our time, dodging attacks to preserve armor durability.",
                    "Combat & Defense Strategy",
                )
            elif any(k in ev_type for k in ["craft", "smelt", "furnace", "workshop", "build"]):
                return (
                    f"Checking our production here: {desc_clean}. Keeping materials organized and workbenches running smoothly.",
                    "Crafting & Smelting Queue",
                )
            elif any(k in ev_type for k in ["loot", "crate", "chest", "storage"]):
                return (
                    f"Opening up this stash: {desc_clean}. Exactly the kind of high-value components we need for future upgrades.",
                    "High-Value Loot Recovery",
                )
            elif any(k in ev_type for k in ["defense", "base", "wall", "spike"]):
                return (
                    f"Focusing on base security: {desc_clean}. Reinforcing this perimeter pays off every single time the horde arrives.",
                    "Base Defense & Fortifications",
                )
            else:
                return (
                    f"Moving to the next objective: {desc_clean}. Staying cautious and keeping our vitals topped off.",
                    "Wasteland Exploration",
                )
        elif persona == CommentaryPersona.ENERGETIC:
            if any(k in ev_type for k in ["combat", "fight", "attack", "kill"]):
                return (
                    f"Zombies spotted! {desc_clean}! Let's take them down quickly before they swarm us!",
                    "High-Intensity Combat",
                )
            elif any(k in ev_type for k in ["loot", "crate", "chest"]):
                return (
                    f"Yes! Checking this loot: {desc_clean}! That is pure value right there!",
                    "Loot Crate Opening",
                )
            else:
                return (
                    f"Pushing ahead into {desc_clean}! Let's get it done!",
                    "Fast-Paced Zone Push",
                )
        else:  # TACTICAL
            return (
                f"Engaging tactical sequence: {desc_clean}. Maintaining positioning and monitoring weapon wear.",
                "Tactical Objective Execution",
            )

    async def _synthesize_single_cue(
        self,
        cue: CommentaryCue,
        config: PersonaConfig,
        output_path: Path,
        max_retries: int = 2,
    ) -> float:
        """Synthesizes text to an MP3 file via edge-tts with automatic retry logic and error isolation."""
        for attempt in range(max_retries + 1):
            try:
                communicate = edge_tts.Communicate(
                    text=cue.text,
                    voice=config.voice,
                    rate=config.rate,
                    pitch=config.pitch,
                    volume=config.volume,
                )
                await communicate.save(str(output_path))

                dur = self._probe_audio_duration(output_path)
                cue.duration = dur
                cue.audio_path = output_path
                return dur
            except Exception as e:
                if attempt < max_retries:
                    logger.warning(
                        f"edge-tts attempt {attempt+1}/{max_retries+1} failed for cue: {e}. Retrying...",
                        extra_data={"text_preview": cue.text[:40]},
                    )
                    await asyncio.sleep(1.0)
                else:
                    logger.warning(
                        f"Failed to synthesize cue after {max_retries+1} attempts: {e}",
                        extra_data={
                            "operation": "synthesize_cue",
                            "component": "CommentaryEngine",
                            "root_cause": str(e),
                            "recovery_action": "Skipping failed dialogue cue; timeline will proceed seamlessly.",
                            "status": "DEGRADED",
                            "text_preview": cue.text[:50],
                        },
                    )
                    cue.audio_path = None
                    cue.duration = 0.0
                    return 0.0

    def _probe_audio_duration(self, audio_path: Path) -> float:
        """Extracts exact audio duration in seconds using ffprobe."""
        cmd = [
            "ffprobe",
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(audio_path),
        ]
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return float(res.stdout.strip())
        except Exception as e:
            logger.warning(f"Could not probe audio duration for {audio_path}: {e}")
            return 3.0

    async def synthesize_all_cues_async(
        self,
        cues: List[CommentaryCue],
        persona: CommentaryPersona = CommentaryPersona.CASUAL,
    ) -> List[CommentaryCue]:
        """Asynchronously synthesizes all commentary audio cues."""
        config = self.get_persona_config(persona)
        for idx, cue in enumerate(cues):
            cue_file = self.temp_dir / f"cue_{persona.value}_{idx:03d}.mp3"
            dur = await self._synthesize_single_cue(cue, config, cue_file)
            if dur > 0.0:
                logger.info(
                    f"Generated {persona.value} commentary cue #{idx+1} ({dur:.2f}s) at offset {cue.start_time:.1f}s"
                )
        return cues

    def synthesize_all_cues(
        self,
        cues: List[CommentaryCue],
        persona: CommentaryPersona = CommentaryPersona.CASUAL,
    ) -> List[CommentaryCue]:
        """Synchronous wrapper for synthesize_all_cues_async."""
        return asyncio.run(self.synthesize_all_cues_async(cues, persona))

    def build_timeline_commentary_track(
        self,
        cues: List[CommentaryCue],
        total_duration: float,
        output_path: Path,
        sample_rate: int = 44100,
    ) -> Path:
        """Assembles all timed commentary cues into a continuous master audio track with exact silence gaps."""
        output_path.parent.mkdir(parents=True, exist_ok=True)

        valid_cues = [c for c in cues if c.audio_path and c.audio_path.exists()]
        if not valid_cues:
            raise CommentaryError(
                operation="build_timeline_commentary_track",
                root_cause="No synthesized audio cues available to assemble master track.",
                recovery_action="Check edge-tts network connection or synthesis logs.",
                file_path=str(output_path),
            )

        # Convert each MP3 cue to 44100Hz mono WAV
        wav_cues: List[Tuple[float, Path, float]] = []
        for idx, cue in enumerate(valid_cues):
            wav_path = self.temp_dir / f"cue_{idx:03d}.wav"
            cmd = [
                "ffmpeg", "-y",
                "-i", str(cue.audio_path),
                "-ar", str(sample_rate),
                "-ac", "1",
                str(wav_path),
            ]
            try:
                subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
                dur = self._probe_audio_duration(wav_path)
                wav_cues.append((cue.start_time, wav_path, dur))
            except Exception as fe:
                logger.warning(f"Failed to transcode cue #{idx} to WAV: {fe}")
                continue

        if not wav_cues:
            raise CommentaryError(
                operation="build_timeline_commentary_track",
                root_cause="All cue WAV transcodes failed.",
                file_path=str(output_path),
            )

        # Build full master timeline using Python standard wave module
        total_samples = int(total_duration * sample_rate)
        master_pcm = bytearray(total_samples * 2)  # 16-bit mono = 2 bytes per sample

        for start_t, wav_p, dur in wav_cues:
            start_sample = int(start_t * sample_rate)
            if start_sample >= total_samples:
                continue

            try:
                with wave.open(str(wav_p), "rb") as wf:
                    cue_pcm = wf.readframes(wf.getnframes())

                end_sample = min(total_samples, start_sample + len(cue_pcm) // 2)
                bytes_to_copy = (end_sample - start_sample) * 2
                master_pcm[start_sample * 2 : start_sample * 2 + bytes_to_copy] = cue_pcm[:bytes_to_copy]
            except Exception as we:
                logger.warning(f"Error reading PCM from {wav_p}: {we}")
                continue

        master_wav = self.temp_dir / "master_commentary.wav"
        with wave.open(str(master_wav), "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(master_pcm)

        # Encode master to high-quality AAC/M4A
        encode_cmd = [
            "ffmpeg", "-y",
            "-i", str(master_wav),
            "-c:a", "aac",
            "-b:a", "192k",
            str(output_path),
        ]
        subprocess.run(encode_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        logger.info(f"Master commentary audio track assembled: {output_path} ({total_duration:.1f}s)")
        return output_path

    def mix_commentary_with_bgm(
        self,
        commentary_audio: Path,
        bgm_audio: Path,
        output_audio_path: Path,
        raw_game_audio: Optional[Path] = None,
        ducking_ratio: float = 3.5,
        voice_volume_boost_db: str = "+1dB",
        bgm_volume_db: str = "-22dB",
        duration: Optional[float] = None,
    ) -> Path:
        """Applies gentle acoustic EQ, loudness normalization, and dynamic sidechain compression for soft, warm voice."""
        output_audio_path.parent.mkdir(parents=True, exist_ok=True)

        soft_voice_filter = (
            f"highpass=f=75,lowpass=f=7800,equalizer=f=3200:t=q:w=1.2:g=-2.0,"
            f"volume={voice_volume_boost_db},loudnorm=I=-16:TP=-1.5:LRA=11"
        )

        if raw_game_audio and raw_game_audio.exists():
            filtergraph = (
                f"[1:a]{soft_voice_filter},asplit=2[voice_sc][voice_mix];"
                f"[0:a]volume={bgm_volume_db}[bg_soft];"
                f"[bg_soft][voice_sc]sidechaincompress=threshold=0.02:ratio={ducking_ratio}:attack=100:release=700[bg_ducked];"
                f"[2:a]volume=-22dB[game_low];"
                f"[bg_ducked][voice_mix][game_low]amix=inputs=3:normalize=0:duration=first:dropout_transition=2,aformat=sample_rates=44100:channel_layouts=stereo[aout]"
            )
            cmd = [
                "ffmpeg", "-y",
                "-i", str(bgm_audio),
                "-i", str(commentary_audio),
                "-i", str(raw_game_audio),
                "-filter_complex", filtergraph,
                "-map", "[aout]",
                "-c:a", "aac",
                "-b:a", "256k",
            ]
        else:
            filtergraph = (
                f"[1:a]{soft_voice_filter},asplit=2[voice_sc][voice_mix];"
                f"[0:a]volume={bgm_volume_db}[bg_soft];"
                f"[bg_soft][voice_sc]sidechaincompress=threshold=0.02:ratio={ducking_ratio}:attack=100:release=700[bg_ducked];"
                f"[bg_ducked][voice_mix]amix=inputs=2:normalize=0:duration=first:dropout_transition=2,aformat=sample_rates=44100:channel_layouts=stereo[aout]"
            )
            cmd = [
                "ffmpeg", "-y",
                "-i", str(bgm_audio),
                "-i", str(commentary_audio),
                "-filter_complex", filtergraph,
                "-map", "[aout]",
                "-c:a", "aac",
                "-b:a", "256k",
            ]

        if duration:
            cmd.extend(["-t", str(duration)])
        cmd.append(str(output_audio_path))

        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        logger.info(f"Commentary mixed with ducked BGM successfully: {output_audio_path}")
        return output_audio_path

    def normalize_pure_voice_track(
        self,
        raw_voice_audio: Path,
        output_audio_path: Path,
        volume_boost_db: str = "+1dB",
    ) -> Path:
        """Applies warm acoustic EQ and loudness normalization (-16 LUFS) to pure spoken audio."""
        output_audio_path.parent.mkdir(parents=True, exist_ok=True)
        soft_voice_filter = (
            f"highpass=f=75,lowpass=f=7800,equalizer=f=3200:t=q:w=1.2:g=-2.0,"
            f"volume={volume_boost_db},loudnorm=I=-16:TP=-1.5:LRA=11,"
            f"aformat=sample_rates=44100:channel_layouts=stereo"
        )
        cmd = [
            "ffmpeg", "-y",
            "-i", str(raw_voice_audio),
            "-filter:a", soft_voice_filter,
            "-c:a", "aac",
            "-b:a", "192k",
            str(output_audio_path),
        ]
        try:
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
            logger.info(f"Normalized pure voice commentary track: {output_audio_path}")
            return output_audio_path
        except Exception as e:
            logger.warning(f"Loudnorm failed ({e}); falling back to copying raw commentary track.")
            shutil.copy2(str(raw_voice_audio), str(output_audio_path))
            return output_audio_path

    def generate_subtitles(
        self,
        cues: List[CommentaryCue],
        output_path: Path,
        events: Optional[List[Any]] = None,
    ) -> Path:
        """Generates synchronized ASS subtitles and closed-caption SRT files for commentary dialogue.

        Renders stylish, highly readable subtitles for spoken gameplay walkthrough cues
        along with unobtrusive action badges for game events at 1920x1080 canvas resolution.
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)

        ass_header = (
            "[Script Info]\n"
            "Title: Last Day on Earth Spoken Commentary Subtitles\n"
            "ScriptType: v4.00+\n"
            "PlayResX: 1920\n"
            "PlayResY: 1080\n"
            "ScaledBorderAndShadow: yes\n\n"
            "[V4+ Styles]\n"
            "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, "
            "Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, "
            "Alignment, MarginL, MarginR, MarginV, Encoding\n"
            "Style: Commentary,Arial,42,&H00FFFFFF,&H000000FF,&H00000000,&H90000000,-1,0,0,0,100,100,0,0,1,3.0,1.5,2,80,80,48,1\n"
            "Style: ActionBadge,Arial,32,&H0000E5FF,&H000000FF,&H00000000,&H90000000,-1,0,0,0,100,100,0,0,1,2.0,1.0,8,40,40,32,1\n\n"
            "[Events]\n"
            "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
        )

        def format_ass_time(seconds: float) -> str:
            hrs = int(seconds // 3600)
            mins = int((seconds % 3600) // 60)
            secs = seconds % 60
            return f"{hrs:01d}:{mins:02d}:{secs:05.2f}"

        def format_srt_time(seconds: float) -> str:
            hrs = int(seconds // 3600)
            mins = int((seconds % 3600) // 60)
            secs = int(seconds % 60)
            millis = int(round((seconds - int(seconds)) * 1000))
            return f"{hrs:02d}:{mins:02d}:{secs:02d},{millis:03d}"

        ass_lines = [ass_header]
        srt_entries: List[str] = []
        srt_idx = 1

        # 1. Spoken commentary dialogue cues
        for cue in cues:
            dur = cue.duration if (cue.duration and cue.duration > 0) else max(3.0, len(cue.text.split()) * 0.38)
            start_t = max(0.0, cue.start_time)
            end_t = start_t + dur

            start_ass = format_ass_time(start_t)
            end_ass = format_ass_time(end_t)
            # Smooth 200ms fade in/out for dialogue
            ass_lines.append(f"Dialogue: 1,{start_ass},{end_ass},Commentary,,0,0,0,,{{\\fad(200,200)}}{cue.text}\n")

            start_srt = format_srt_time(start_t)
            end_srt = format_srt_time(end_t)
            srt_entries.append(f"{srt_idx}\n{start_srt} --> {end_srt}\n{cue.text}\n\n")
            srt_idx += 1

        # 2. Gameplay event badges (if present and distinct)
        if events:
            for ev in events:
                ev_start = getattr(ev, "start_time", 0.0)
                ev_end = getattr(ev, "end_time", ev_start + 1.2)
                ev_desc = getattr(ev, "description", "")
                if ev_desc:
                    start_ass = format_ass_time(ev_start)
                    end_ass = format_ass_time(ev_end)
                    ass_lines.append(f"Dialogue: 0,{start_ass},{end_ass},ActionBadge,,0,0,0,,{{\\fad(150,150)}}{ev_desc}\n")

        # Write ASS file
        with open(output_path, "w", encoding="utf-8") as f:
            f.writelines(ass_lines)

        # Write SRT file alongside
        srt_path = output_path.with_suffix(".srt")
        try:
            with open(srt_path, "w", encoding="utf-8") as f:
                f.writelines(srt_entries)
        except Exception as e:
            logger.warning(f"Could not write SRT closed captions: {e}")

        logger.info(f"Generated {len(cues)} commentary subtitle lines at: {output_path}")
        return output_path

    def generate_commentary_track(
        self,
        duration: float,
        output_path: Path,
        events: Optional[List[Any]] = None,
        episode_number: Optional[int] = None,
        persona: CommentaryPersona = CommentaryPersona.CASUAL,
        include_bgm: bool = True,
        bgm_audio: Optional[Path] = None,
        volume_boost_db: str = "+1dB",
        bgm_volume_db: str = "-22dB",
        ducking_ratio: float = 3.5,
        min_cue_interval: float = 25.0,
        raw_game_audio: Optional[Path] = None,
    ) -> Path:
        """One-stop workflow: Generates script, synthesizes neural voice, and produces final master audio track."""
        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # 1. Script generation
            cues = self.generate_script(
                events=events,
                duration=duration,
                episode_number=episode_number,
                persona=persona,
                min_cue_interval=min_cue_interval,
            )
            logger.info(f"Generated {len(cues)} commentary cues for duration {duration:.1f}s ({persona.value})")

            # 2. Synthesis
            self.synthesize_all_cues(cues, persona=persona)

            # 3. Synchronized subtitles generation (.ass and .srt)
            self.last_cues = cues
            try:
                sub_path = output_path.with_suffix(".ass")
                self.generate_subtitles(cues=cues, output_path=sub_path, events=events)
                logger.info(f"Generated synchronized commentary subtitles: {sub_path}")
            except Exception as se:
                logger.warning(f"Commentary subtitle generation degraded: {se}")

            # 4. Timeline assembly
            raw_voice_path = self.temp_dir / f"timeline_voice_{output_path.stem}.m4a"
            self.build_timeline_commentary_track(
                cues=cues,
                total_duration=duration,
                output_path=raw_voice_path,
            )

            # 5. Mix or Pure Voice
            if include_bgm and bgm_audio and bgm_audio.exists():
                logger.info(f"Mixing commentary with background music loop ({bgm_volume_db}) via sidechain ducking (ratio {ducking_ratio})...")
                return self.mix_commentary_with_bgm(
                    commentary_audio=raw_voice_path,
                    bgm_audio=bgm_audio,
                    output_audio_path=output_path,
                    raw_game_audio=raw_game_audio,
                    voice_volume_boost_db=volume_boost_db,
                    bgm_volume_db=bgm_volume_db,
                    ducking_ratio=ducking_ratio,
                    duration=duration,
                )
            else:
                logger.info("Normalizing pure voice commentary track (Zero added BGM)...")
                return self.normalize_pure_voice_track(
                    raw_voice_audio=raw_voice_path,
                    output_audio_path=output_path,
                    volume_boost_db=volume_boost_db,
                )

        except CommentaryError:
            raise
        except Exception as e:
            raise CommentaryError(
                operation="generate_commentary_track",
                root_cause=str(e),
                recovery_action="Fallback to standard background music loop.",
                file_path=str(output_path),
            )

    def render_commentary_video(
        self,
        video_input: Path,
        mixed_audio_input: Path,
        output_video_path: Path,
        duration: Optional[float] = None,
    ) -> Path:
        """Muxes the final mixed commentary audio with gameplay video."""
        output_video_path.parent.mkdir(parents=True, exist_ok=True)
        cmd = [
            "ffmpeg", "-y",
            "-i", str(video_input),
            "-i", str(mixed_audio_input),
            "-map", "0:v:0",
            "-map", "1:a:0",
            "-c:v", "copy",
            "-c:a", "aac",
            "-b:a", "192k",
            "-shortest",
        ]
        if duration:
            cmd.extend(["-t", str(duration)])
        cmd.append(str(output_video_path))

        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        logger.info(f"Rendered final commentary video: {output_video_path}")
        return output_video_path
