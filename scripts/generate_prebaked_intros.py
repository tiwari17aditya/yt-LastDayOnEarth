"""Pre-generate studio-mastered intro voice audio files for zero-latency, zero-risk cloud execution."""
import asyncio
import subprocess
from pathlib import Path
import edge_tts

INTRO_DIR = Path("assets/audio/intros")
INTRO_DIR.mkdir(parents=True, exist_ok=True)

VOICE = "en-IN-PrabhatNeural"
RATE = "+12%"
PITCH = "+22Hz"

INTRO_SCRIPTS = [
    {
        "filename": "intro_hinglish_variant_1.mp3",
        "voice": VOICE,
        "text": (
            "Yo survivors! Welcome back to Last Day on Earth. "
            "Aaj hum Bunker Alfa raid karenge aur Stark029 clan ke saath epic loot secure karenge. Let's get right into the action!"
        )
    },
    {
        "filename": "intro_hinglish_variant_2.mp3",
        "voice": VOICE,
        "text": (
            "Hey what is up survivors! Welcome to Last Day on Earth. "
            "Aaj ke survival mission me hum high-tier zones explore karenge aur Stark029 clan ke saath survival dominance banayenge. Let's roll!"
        )
    },
    {
        "filename": "intro_hinglish_variant_3.mp3",
        "voice": VOICE,
        "text": (
            "Welcome back survivors to Last Day on Earth! "
            "Aaj ka episode full intense hone wala hai. Ready ho jao aur Stark029 clan ke saath full loot nikalte hain. Let's do this!"
        )
    },
    {
        "filename": "intro_english_variant_1.mp3",
        "voice": "en-US-ChristopherNeural",
        "text": (
            "Yo survivors! Welcome back to Last Day on Earth. "
            "Today we are raiding Bunker Alfa and securing top-tier loot with Clan Stark029. Let's get right into the action!"
        )
    },
    {
        "filename": "intro_english_variant_2.mp3",
        "voice": "en-US-AndrewMultilingualNeural",
        "text": (
            "Hey what's up survivors! Welcome back to another episode of Last Day on Earth with Clan Stark029. "
            "Let's gear up and survive together!"
        )
    }
]

async def generate_and_master(item):
    temp_file = INTRO_DIR / f"temp_{item['filename']}"
    target_file = INTRO_DIR / item["filename"]
    
    # Synthesize
    comm = edge_tts.Communicate(item["text"], voice=item["voice"], rate=RATE, pitch=PITCH)
    await comm.save(str(temp_file))
    
    # Master to broadcast standard -17.0 LUFS with crisp gaming EQ
    af = (
        "highpass=f=80,"
        "equalizer=f=3200:width_type=o:w=1.0:g=2.2,"
        "loudnorm=I=-17.0:TP=-1.0:LRA=5.0"
    )
    cmd = [
        "ffmpeg", "-y", "-i", str(temp_file),
        "-af", af,
        "-c:a", "libmp3lame", "-b:a", "192k",
        str(target_file)
    ]
    subprocess.run(cmd, capture_output=True, check=True)
    temp_file.unlink(missing_ok=True)
    print(f"Mastered intro: {target_file.name} ({target_file.stat().st_size} bytes)")

async def main():
    print(f"Generating {len(INTRO_SCRIPTS)} pre-baked intro audio files in {INTRO_DIR}...")
    tasks = [generate_and_master(item) for item in INTRO_SCRIPTS]
    await asyncio.gather(*tasks)
    print("All pre-baked intros successfully generated and mastered to -17 LUFS!")

if __name__ == "__main__":
    asyncio.run(main())

