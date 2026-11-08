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
        rate="+0%",
        pitch="+0Hz",
        volume="+0%",
        description="Friendly, conversational gamer walkthrough companion. Natural, relatable, and relaxed.",
    ),
    CommentaryPersona.ENERGETIC: PersonaConfig(
        persona=CommentaryPersona.ENERGETIC,
        voice="en-US-ChristopherNeural",
        rate="+5%",
        pitch="+0Hz",
        volume="+0%",
        description="High-energy, hype gamer persona. Punchy reactions, fast-paced and enthusiastic.",
    ),
    CommentaryPersona.TACTICAL: PersonaConfig(
        persona=CommentaryPersona.TACTICAL,
        voice="en-US-AndrewNeural",
        rate="-2%",
        pitch="-2Hz",
        volume="+0%",
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


# Comprehensive pool of procedural commentary dialogue for Last Day on Earth
PROCEDURAL_CASUAL_TOPICS = [
    {
        "category": "inventory",
        "text": "I always like to spend a few minutes organizing storage before heading out. Having dedicated chests for raw wood, ores, and weapons saves so much time later.",
    },
    {
        "category": "smelting",
        "text": "Checking in on our smelters. A quick pro tip: turning raw wood into charcoal gives you much higher fuel efficiency than burning plain logs.",
    },
    {
        "category": "defense",
        "text": "Expanding our base perimeter today. Upgrading from basic wood to sturdy level two planks makes a huge difference when the daily zombie horde sweeps through.",
    },
    {
        "category": "combat",
        "text": "Clearing out the perimeter with sneak attacks here. That triple damage bonus on the first strike saves a ton of weapon durability in the long run.",
    },
    {
        "category": "vehicle",
        "text": "Taking a quick look at the Chopper. Piecing together wheels, the gas tank, and engine parts is always one of the most rewarding milestones in LDoE.",
    },
    {
        "category": "recycler",
        "text": "Our recycler is steadily running. Leveling up electronics and mechanics with spare batteries and broken flashlights is the best route to free copper and steel.",
    },
    {
        "category": "companion",
        "text": "Stopping by the dog crate to feed the pups. Rolling traits like Bloodhound or True Friend gives you an incredible passive boost out in the field.",
    },
    {
        "category": "scouting",
        "text": "Pacing ourselves through this zone. You always want to keep one eye glued to the minimap to avoid getting cornered by spitters or roaming packs.",
    },
    {
        "category": "bunker",
        "text": "Stocking up combat tickets for Bunker Alfa. Cashing in green, yellow, and red tickets downstairs remains the most consistent source of military firearms.",
    },
    {
        "category": "farm",
        "text": "Whenever you hit Crooked Creek Farm, remember to sneak past the diseased giants if you want to conserve ammo, and let the saw cutter finish the blue crate quietly.",
    },
    {
        "category": "gunsmith",
        "text": "Fine-tuning our weapon mods at the gunsmith bench. Adding red dot optics and expanded magazines transforms even basic pistols into clearing machines.",
    },
    {
        "category": "winter",
        "text": "Getting our warm fur armor ready for the cold zones. Freezing ruins your attack speed and leaves you vulnerable, so insulation is everything.",
    },
    {
        "category": "police",
        "text": "Managing resources for the Blackport PD yard. Surviving consecutive waves without burning through all your armor is the secret to scoring purple inspector badges.",
    },
    {
        "category": "crafting",
        "text": "Keeping our workbenches humming. Crafting thick leather, sewing bandages, and refining iron ensures you never start a mission unprepared.",
    },
    {
        "category": "resupply",
        "text": "Checking our health bar and nourishment. Eating canned food and drinking water regularly prevents your survivor from slowing down during high-stress runs.",
    },
]

PROCEDURAL_ENERGETIC_TOPICS = [
    {
        "category": "hype",
        "text": "Alright survivors, let's keep the momentum going! Checking our gear, stacking the best melee weapons, and staying on high alert!",
    },
    {
        "category": "craft",
        "text": "Look at those furnaces burning! Production never stops on this base â€” turning raw ore into iron bars 24/7!",
    },
    {
        "category": "combat",
        "text": "Spotted spitters and fast biters closing in! Keep moving, don't let them surround you. That sneak attack bonus is so satisfying!",
    },
    {
        "category": "loot",
        "text": "Opening up these high-tier crates... engine parts, weapon mods, and rare tickets! That is a massive score!",
    },
    {
        "category": "threat",
        "text": "Watch the noise meter! In higher zones, making too much racket brings the Big One, and that's an instant reset. Staying light and fast!",
    },
    {
        "category": "clutch",
        "text": "Down to half health but we've got bandages hotkeyed! Quick heal, reset the fight, and back into action!",
    },
]

PROCEDURAL_TACTICAL_TOPICS = [
    {
        "category": "tactical_rule",
        "text": "Key survival rule: always calculate weapon durability per enemy encounter. Avoid using firearms on standard roaming zombies â€” preserve guns for Frenzied Giants.",
    },
    {
        "category": "base_layout",
        "text": "When building your base layout, implement a honeycomb wall design. The daily horde destroys two to three outer walls, but cannot penetrate your reinforced core.",
    },
    {
        "category": "wall_trick",
        "text": "Notice the engagement spacing here. Utilizing door mechanics and wall-tricking eliminates incoming damage entirely, saving both healing items and armor durability.",
    },
    {
        "category": "loot_priority",
        "text": "Priority loot extracted. Always prioritize red combat tickets, aluminum wire, and factory parts over common limestone and raw pine.",
    },
    {
        "category": "resource_calc",
        "text": "Energy conservation principle: batch your resource runs to adjacent zones to minimize travel energy while maximizing inventory capacity.",
    },
]


class CommentaryEngine:
    """Orchestrates script synthesis, voice generation, timeline alignment, and audio ducking."""

    def __init__(self, temp_dir: Path = Path("temp/commentary")) -> None:
        self.temp_dir = temp_dir
        self.temp_dir.mkdir(parents=True, exist_ok=True)

    def get_persona_config(self, persona: CommentaryPersona) -> PersonaConfig:
        """Retrieve voice parameters for a specific persona."""
        return PERSONA_PROFILES.get(persona, PERSONA_PROFILES[CommentaryPersona.CASUAL])

    def generate_script(
        self,
        events: Optional[List[Any]] = None,
        duration: float = 900.0,
        episode_number: Optional[int] = None,
        persona: CommentaryPersona = CommentaryPersona.CASUAL,
        min_cue_interval: float = 60.0,
    ) -> List[CommentaryCue]:
        """Synthesizes high-engagement, domain-grounded LDoE commentary cues matching video duration.
        
        Dynamically distributes cues across the timeline with comfortable breathing room,
        grounding dialogue in detected gameplay events or procedural survival walkthrough topics.
        """
        ep_label = f"Episode {episode_number}" if episode_number else "our survival series"
        cues: List[CommentaryCue] = []

        # 1. Intro Hook (starts at 2.0s)
        if persona == CommentaryPersona.CASUAL:
            intro_text = (
                f"Hey everyone, welcome back to Last Day on Earth! In {ep_label}, we're diving into base optimization, "
                "stocking up on essential survival supplies, and heading out into the wasteland. Let's see what we can accomplish today."
            )
        elif persona == CommentaryPersona.ENERGETIC:
            intro_text = (
                f"What is up survivors! Welcome back to Last Day on Earth, {ep_label}! Today we are gearing up, "
                "raiding deep into zombie territory, and testing our base defenses. Let's get right into it!"
            )
        else:  # TACTICAL
            intro_text = (
                f"Welcome survivors. This is {ep_label} of our Last Day on Earth strategic walkthrough. "
                "Today's focus is resource economy, defense optimization, and risk-managed clearing."
            )

        cues.append(CommentaryCue(start_time=2.0, text=intro_text, style=persona))

        # 2. Outro Hook (starts ~20-25s before end)
        outro_time = max(15.0, duration - 22.0)

        # 3. Middle Dialogue Cues (spaced across video timeline)
        if duration >= 50.0:
            usable_start = 30.0
            usable_end = outro_time - 30.0

            # Check if valid events exist
            event_cues_added = False
            last_cue_time = 0.0

            if events:
                for ev in events:
                    ev_time = getattr(ev, "start_time", None)
                    if ev_time is None or not (usable_start <= ev_time <= usable_end):
                        continue

                    if last_cue_time > 0 and (ev_time - last_cue_time < min_cue_interval):
                        continue

                    ev_type = getattr(ev, "action_type", getattr(ev, "event_type", "nav"))
                    ev_desc = getattr(ev, "description", "")

                    # Map event to conversational cue
                    cue_text = self._format_event_cue(ev_type, ev_desc, persona)
                    cues.append(CommentaryCue(start_time=float(ev_time), text=cue_text, style=persona))
                    last_cue_time = float(ev_time)
                    event_cues_added = True

            # If no events or sparse gaps, fill procedurally
            if not event_cues_added or (outro_time - max(last_cue_time, 2.0) > 180.0):
                procedural_topics = (
                    PROCEDURAL_CASUAL_TOPICS
                    if persona == CommentaryPersona.CASUAL
                    else PROCEDURAL_ENERGETIC_TOPICS
                    if persona == CommentaryPersona.ENERGETIC
                    else PROCEDURAL_TACTICAL_TOPICS
                )

                # Compute target spacing (between 70s and 120s)
                total_span = usable_end - usable_start
                if total_span > 0:
                    num_steps = max(1, min(len(procedural_topics), int(total_span // 85.0)))
                    step_size = total_span / (num_steps + 1)

                    topic_idx = 0
                    current_t = usable_start + (step_size * 0.4)

                    while current_t <= usable_end and topic_idx < len(procedural_topics):
                        # Ensure distance from any already added event cues
                        conflict = any(abs(c.start_time - current_t) < 35.0 for c in cues)
                        if not conflict and (last_cue_time == 0.0 or current_t - last_cue_time >= 45.0):
                            item = procedural_topics[topic_idx]
                            cues.append(CommentaryCue(start_time=round(current_t, 1), text=item["text"], style=persona))
                            last_cue_time = current_t
                            topic_idx += 1
                        current_t += step_size

        # Append Outro Hook
        if persona == CommentaryPersona.CASUAL:
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

        cues.append(CommentaryCue(start_time=round(outro_time, 1), text=outro_text, style=persona))

        # Sort cues strictly chronologically
        cues.sort(key=lambda c: c.start_time)
        return cues

    def _format_event_cue(self, event_type: str, description: str, persona: CommentaryPersona) -> str:
        """Adapts a gameplay event into natural persona dialogue."""
        desc_clean = description.strip() if description else "this objective"
        ev_type = (event_type or "").lower()
        if persona == CommentaryPersona.CASUAL:
            if any(k in ev_type for k in ["combat", "fight", "attack", "kill"]):
                return f"Spotting enemy movement here: {desc_clean}. Taking our time, dodging attacks to preserve armor durability."
            elif any(k in ev_type for k in ["craft", "smelt", "furnace", "workshop", "build"]):
                return f"Checking our production here: {desc_clean}. Keeping materials organized and workbenches running smoothly."
            elif any(k in ev_type for k in ["loot", "crate", "chest", "storage"]):
                return f"Opening up this stash: {desc_clean}. Exactly the kind of high-value components we need for future upgrades."
            elif any(k in ev_type for k in ["defense", "base", "wall", "spike"]):
                return f"Focusing on base security: {desc_clean}. Reinforcing this perimeter pays off every single time the horde arrives."
            else:
                return f"Moving to the next objective: {desc_clean}. Staying cautious and keeping our vitals topped off."
        elif persona == CommentaryPersona.ENERGETIC:
            if any(k in ev_type for k in ["combat", "fight", "attack", "kill"]):
                return f"Zombies spotted! {desc_clean}! Let's take them down quickly before they swarm us!"
            elif any(k in ev_type for k in ["loot", "crate", "chest"]):
                return f"Yes! Checking this loot: {desc_clean}! That is pure value right there!"
            else:
                return f"Pushing ahead into {desc_clean}! Let's get it done!"
        else:  # TACTICAL
            return f"Engaging tactical sequence: {desc_clean}. Maintaining positioning and monitoring weapon wear."

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
        ducking_ratio: float = 6.0,
        voice_volume_boost_db: str = "+3dB",
    ) -> Path:
        """Applies professional dynamic sidechain compression: BGM ducks automatically when commentary speaks."""
        output_audio_path.parent.mkdir(parents=True, exist_ok=True)

        if raw_game_audio and raw_game_audio.exists():
            filtergraph = (
                f"[1:a]volume={voice_volume_boost_db}[voice];"
                f"[0:a][voice]sidechaincompress=threshold=0.04:ratio={ducking_ratio}:attack=150:release=700[bg_ducked];"
                f"[2:a]volume=-18dB[game_low];"
                f"[bg_ducked][voice][game_low]amix=inputs=3:duration=first:dropout_transition=2,aformat=sample_rates=44100:channel_layouts=stereo[aout]"
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
                str(output_audio_path),
            ]
        else:
            filtergraph = (
                f"[1:a]volume={voice_volume_boost_db}[voice];"
                f"[0:a][voice]sidechaincompress=threshold=0.04:ratio={ducking_ratio}:attack=150:release=700[bg_ducked];"
                f"[bg_ducked][voice]amix=inputs=2:duration=first:dropout_transition=2,aformat=sample_rates=44100:channel_layouts=stereo[aout]"
            )
            cmd = [
                "ffmpeg", "-y",
                "-i", str(bgm_audio),
                "-i", str(commentary_audio),
                "-filter_complex", filtergraph,
                "-map", "[aout]",
                "-c:a", "aac",
                "-b:a", "256k",
                str(output_audio_path),
            ]

        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        logger.info(f"Commentary mixed with ducked BGM successfully: {output_audio_path}")
        return output_audio_path

    def normalize_pure_voice_track(
        self,
        raw_voice_audio: Path,
        output_audio_path: Path,
        volume_boost_db: str = "+3dB",
    ) -> Path:
        """Applies loudness normalization (-16 LUFS) and peak limiting to pure spoken audio."""
        output_audio_path.parent.mkdir(parents=True, exist_ok=True)
        cmd = [
            "ffmpeg", "-y",
            "-i", str(raw_voice_audio),
            "-filter:a", f"volume={volume_boost_db},loudnorm=I=-16:TP=-1.5:LRA=11,aformat=sample_rates=44100:channel_layouts=stereo",
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

    def generate_commentary_track(
        self,
        duration: float,
        output_path: Path,
        events: Optional[List[Any]] = None,
        episode_number: Optional[int] = None,
        persona: CommentaryPersona = CommentaryPersona.CASUAL,
        include_bgm: bool = False,
        bgm_audio: Optional[Path] = None,
        volume_boost_db: str = "+3dB",
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
            )
            logger.info(f"Generated {len(cues)} commentary cues for duration {duration:.1f}s ({persona.value})")

            # 2. Synthesis
            self.synthesize_all_cues(cues, persona=persona)

            # 3. Timeline assembly
            raw_voice_path = self.temp_dir / f"timeline_voice_{output_path.stem}.m4a"
            self.build_timeline_commentary_track(
                cues=cues,
                total_duration=duration,
                output_path=raw_voice_path,
            )

            # 4. Mix or Pure Voice
            if include_bgm and bgm_audio and bgm_audio.exists():
                logger.info("Mixing commentary with background music loop via sidechain ducking...")
                return self.mix_commentary_with_bgm(
                    commentary_audio=raw_voice_path,
                    bgm_audio=bgm_audio,
                    output_audio_path=output_path,
                    raw_game_audio=raw_game_audio,
                    voice_volume_boost_db=volume_boost_db,
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
