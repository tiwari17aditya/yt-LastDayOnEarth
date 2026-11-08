#!/usr/bin/env python3
"""Generate sample videos with PURE AI voice commentary (NO BGM) for Last Day on Earth.

Styles evaluated:
  1. Energetic Gamer (en-US-ChristopherNeural)
  2. Casual Walkthrough (en-US-GuyNeural)
  3. Tactical Survival Guide (en-US-AndrewNeural)

Features:
  - ZERO BGM: Pure, isolated spoken commentary for 100% vocal clarity
  - Spoken style announcements at the start of each sample
  - Audio normalization and volume boosting for clear listening on mobile/desktop
  - Robust FFmpeg filter_complex stream concatenation
"""

import argparse
import asyncio
import os
import subprocess
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import edge_tts
from src.audio.commentary_engine import (
    CommentaryEngine,
    CommentaryPersona,
    CommentaryCue,
    PERSONA_PROFILES,
)
from src.logging_config import get_logger

logger = get_logger(component="PureCommentarySamples")

# Ensure UTF-8 output encoding on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def probe_duration(path: Path) -> float:
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(path),
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return float(res.stdout.strip())


def render_title_slate_with_audio(
    title: str,
    subtitle: str,
    spoken_intro: str,
    voice: str,
    output_path: Path,
) -> Path:
    """Generates a visual title slate accompanied by the spoken style introduction."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temp_dir = output_path.parent / "temp_slate"
    temp_dir.mkdir(parents=True, exist_ok=True)

    # 1. Synthesize spoken intro
    intro_mp3 = temp_dir / f"{output_path.stem}_spoken.mp3"
    asyncio.run(edge_tts.Communicate(spoken_intro, voice).save(str(intro_mp3)))
    intro_dur = probe_duration(intro_mp3)
    slate_dur = max(3.5, intro_dur + 0.5)

    # 2. Render visual card with PIL
    img = Image.new("RGB", (1920, 1080), color=(15, 20, 35))
    draw = ImageDraw.Draw(img)

    try:
        font_main = ImageFont.truetype("arialbd.ttf", 68)
        font_sub = ImageFont.truetype("arial.ttf", 40)
    except Exception:
        font_main = ImageFont.load_default()
        font_sub = ImageFont.load_default()

    bbox1 = draw.textbbox((0, 0), title, font=font_main)
    w1 = bbox1[2] - bbox1[0]
    draw.text(((1920 - w1) // 2, 450), title, fill=(255, 204, 0), font=font_main)

    bbox2 = draw.textbbox((0, 0), subtitle, font=font_sub)
    w2 = bbox2[2] - bbox2[0]
    draw.text(((1920 - w2) // 2, 560), subtitle, fill=(230, 230, 245), font=font_sub)

    temp_png = temp_dir / f"{output_path.stem}.png"
    img.save(temp_png)

    # 3. Create MP4 slate with spoken intro
    cmd = [
        "ffmpeg", "-y",
        "-loop", "1", "-i", str(temp_png),
        "-i", str(intro_mp3),
        "-c:v", "libx264",
        "-t", str(slate_dur),
        "-pix_fmt", "yuv420p",
        "-r", "60",
        "-c:a", "aac",
        "-b:a", "192k",
        "-shortest",
        str(output_path),
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    return output_path


async def build_pure_voice_track(
    persona: CommentaryPersona,
    output_audio_path: Path,
    target_duration: float = 40.0,
    episode_number: int = 99,
) -> Path:
    """Synthesizes crystal clear, continuous commentary with NO background music."""
    profile = PERSONA_PROFILES[persona]
    temp_dir = output_audio_path.parent / f"cues_{persona.value}"
    temp_dir.mkdir(parents=True, exist_ok=True)

    scripts = {
        CommentaryPersona.ENERGETIC: [
            (0.5, f"What is up survivors! Welcome back to Last Day on Earth, Episode {episode_number}! Today we're gearing up, raiding deep into zombie territory, and testing our base defenses. Let's get right into it!"),
            (14.0, "Checking our inventory and sorting our weapon chests. Keeping the smelting furnaces running non-stop and taking out roaming spitters with that sneak attack critical damage!"),
            (27.0, "Awesome run today! Make sure to smash that like button, subscribe for daily survival guide episodes, and tell me in the comments what's your favorite raid weapon!"),
        ],
        CommentaryPersona.CASUAL: [
            (0.5, f"Hey everyone, welcome back to Last Day on Earth. In Episode {episode_number}, we're taking a look at our base progress, upgrading our layout, and stocking up on essential materials."),
            (13.5, "I always like to spend a few minutes organizing our storage chests before heading out. Having dedicated crates for raw wood, ores, and weapons saves so much time during intense raids."),
            (27.0, "Thanks so much for hanging out and watching today's gameplay! If you enjoyed it, please give it a thumbs up and subscribe to follow the series. See you all in the next one!"),
        ],
        CommentaryPersona.TACTICAL: [
            (0.5, f"Welcome survivors. This is Episode {episode_number} of our Last Day on Earth strategic walkthrough. Today's focus is resource economy, defense optimization, and risk-managed clearing."),
            (14.0, "Key tactical rule: always calculate weapon durability per enemy encounter. Utilize door mechanics and wall tricking to eliminate incoming damage and conserve armor durability."),
            (27.0, "That concludes today's tactical breakdown. Remember to subscribe for more in-depth LDoE raid guides, and leave your questions in the comments below. Stay sharp out there."),
        ],
    }

    cue_entries = scripts[persona]
    wav_cues: list[tuple[float, Path, float]] = []

    for idx, (start_t, text) in enumerate(cue_entries):
        cue_mp3 = temp_dir / f"cue_{idx:02d}.mp3"
        comm = edge_tts.Communicate(
            text=text,
            voice=profile.voice,
            rate=profile.rate,
            pitch=profile.pitch,
        )
        await comm.save(str(cue_mp3))

        # Convert to 44100Hz mono WAV
        cue_wav = temp_dir / f"cue_{idx:02d}.wav"
        cmd = [
            "ffmpeg", "-y",
            "-i", str(cue_mp3),
            "-ar", "44100",
            "-ac", "1",
            str(cue_wav),
        ]
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        dur = probe_duration(cue_wav)
        wav_cues.append((start_t, cue_wav, dur))
        logger.info(f"[{persona.value.upper()}] Synthesized cue #{idx+1} ({dur:.1f}s) at offset {start_t:.1f}s: \"{text[:45]}...\"")

    # Assemble timeline with Python wave module
    sample_rate = 44100
    total_samples = int(target_duration * sample_rate)
    master_pcm = bytearray(total_samples * 2)

    import wave
    for start_t, wav_p, dur in wav_cues:
        start_sample = int(start_t * sample_rate)
        if start_sample >= total_samples:
            continue
        with wave.open(str(wav_p), "rb") as wf:
            frames = wf.readframes(wf.getnframes())
        end_sample = min(total_samples, start_sample + len(frames) // 2)
        bytes_to_copy = (end_sample - start_sample) * 2
        master_pcm[start_sample * 2 : start_sample * 2 + bytes_to_copy] = frames[:bytes_to_copy]

    raw_wav = temp_dir / "master_raw.wav"
    with wave.open(str(raw_wav), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(master_pcm)

    # Encode with volume boost (+3dB) and 256k AAC for loud, crystal-clear speech
    norm_cmd = [
        "ffmpeg", "-y",
        "-i", str(raw_wav),
        "-af", "volume=+3dB,aformat=channel_layouts=stereo",
        "-c:a", "aac",
        "-b:a", "256k",
        str(output_audio_path),
    ]
    subprocess.run(norm_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    logger.info(f"Pure voice track created: {output_audio_path} ({target_duration:.1f}s)")
    return output_audio_path


def render_single_voice_sample(
    video_source: Path,
    voice_audio: Path,
    output_video: Path,
    duration: float = 40.0,
) -> Path:
    """Muxes pure voice commentary over gameplay video (game audio muted/removed)."""
    output_video.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg", "-y",
        "-ss", "0",
        "-t", str(duration),
        "-i", str(video_source),
        "-i", str(voice_audio),
        "-map", "0:v:0",
        "-map", "1:a:0",
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-r", "60",
        "-c:a", "aac",
        "-b:a", "256k",
        "-shortest",
        str(output_video),
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    logger.info(f"Rendered voice-only sample: {output_video}")
    return output_video


def build_unified_comparison_video(
    sections: list[tuple[Path, Path]],
    output_video: Path,
) -> Path:
    """Concatenates all (slate, sample) pairs using FFmpeg filter_complex concat for flawless A/V sync."""
    inputs = []
    filter_parts = []
    idx = 0
    for slate_path, sample_path in sections:
        inputs.extend(["-i", str(slate_path)])
        filter_parts.append(f"[{idx}:v][{idx}:a]")
        idx += 1

        inputs.extend(["-i", str(sample_path)])
        filter_parts.append(f"[{idx}:v][{idx}:a]")
        idx += 1

    total_segments = len(filter_parts)
    concat_filter = f"{''.join(filter_parts)}concat=n={total_segments}:v=1:a=1[v][a]"

    cmd = [
        "ffmpeg", "-y",
        *inputs,
        "-filter_complex", concat_filter,
        "-map", "[v]",
        "-map", "[a]",
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-c:a", "aac",
        "-b:a", "256k",
        str(output_video),
    ]
    logger.info("Assembling unified voice comparison video...")
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    logger.info(f"Unified voice comparison video successfully built: {output_video}")
    return output_video


def main():
    parser = argparse.ArgumentParser(description="Generate pure voice commentary samples (NO BGM).")
    parser.add_argument("--video", type=str, required=True, help="Input gameplay video file")
    parser.add_argument("--duration", type=float, default=40.0, help="Duration per sample in seconds")
    parser.add_argument("--output-dir", type=str, default="output/commentary_samples_pure_voice")

    args = parser.parse_args()
    video_path = Path(args.video)
    if not video_path.exists():
        logger.error(f"Input video not found: {video_path}")
        sys.exit(1)

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    personas_data = [
        (
            CommentaryPersona.ENERGETIC,
            "STYLE 1: ENERGETIC GAMER",
            "Voice: Christopher | High Energy, Hype & Punchy",
            "Style 1: Energetic Gamer, voiced by Christopher.",
            "en-US-ChristopherNeural",
        ),
        (
            CommentaryPersona.CASUAL,
            "STYLE 2: CASUAL WALKTHROUGH",
            "Voice: Guy | Warm, Natural & Conversational",
            "Style 2: Casual Walkthrough, voiced by Guy.",
            "en-US-GuyNeural",
        ),
        (
            CommentaryPersona.TACTICAL,
            "STYLE 3: TACTICAL SURVIVAL GUIDE",
            "Voice: Andrew | Strategic, Focused Tips & Mechanics",
            "Style 3: Tactical Survival Guide, voiced by Andrew.",
            "en-US-AndrewNeural",
        ),
    ]

    sections: list[tuple[Path, Path]] = []

    for persona, title, subtitle, spoken_intro, voice in personas_data:
        logger.info(f"\n--- Processing {persona.value.upper()} ({voice}) ---")

        # 1. Spoken title slate
        slate_file = out_dir / f"slate_{persona.value}.mp4"
        render_title_slate_with_audio(
            title=title,
            subtitle=subtitle,
            spoken_intro=spoken_intro,
            voice=voice,
            output_path=slate_file,
        )

        # 2. Pure Voice Audio Track (NO BGM)
        voice_audio = out_dir / f"pure_voice_{persona.value}.m4a"
        asyncio.run(
            build_pure_voice_track(
                persona=persona,
                output_audio_path=voice_audio,
                target_duration=args.duration,
                episode_number=99,
            )
        )

        # 3. Mux over gameplay video
        sample_video = out_dir / f"sample_{persona.value}_pure_voice.mp4"
        render_single_voice_sample(
            video_source=video_path,
            voice_audio=voice_audio,
            output_video=sample_video,
            duration=args.duration,
        )

        sections.append((slate_file, sample_video))

    # Assemble Unified Comparison Video
    unified_video = out_dir / "unified_pure_voice_showcase.mp4"
    build_unified_comparison_video(sections, unified_video)

    print("\n" + "=" * 65)
    print("PURE VOICE COMMENTARY SAMPLES GENERATED SUCCESSFULLY (NO BGM)!")
    print("=" * 65)
    for p, _, _, _, v in personas_data:
        f = out_dir / f"sample_{p.value}_pure_voice.mp4"
        print(f"- {p.value.upper()} ({v}): {f}")
    print(f"\nUnified Showcase Video: {unified_video}")
    print("=" * 65 + "\n")


if __name__ == "__main__":
    main()

