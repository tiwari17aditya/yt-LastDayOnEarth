"""Downloads 20 fresh, upbeat, positive, and royalty-free gaming tracks by Kevin MacLeod (CC-BY 4.0).

Excludes all dark, gloomy, anxiety-inducing, or negative sounds.
Updates config/music_library.json and cleans config/audio/.
"""

import json
import subprocess
import urllib.parse
import urllib.request
from pathlib import Path

AUDIO_DIR = Path("config/audio")
AUDIO_DIR.mkdir(parents=True, exist_ok=True)
CONFIG_FILE = Path("config/music_library.json")

# Curated 20 fresh, upbeat, cool gaming tracks (No negative, dark, or gloomy rhythms)
FRESH_GAMING_CATALOG = [
    {
        "id": "track_01",
        "title": "Decisions",
        "artist": "Kevin MacLeod",
        "genre": "Subtle Lo-Fi / Clean Electronic Ambient",
        "source": "Incompetech",
        "url": "https://incompetech.com/music/royalty-free/mp3-royaltyfree/Decisions.mp3",
        "license": "Creative Commons Attribution 4.0 (CC-BY 4.0)",
        "attribution_required": True,
        "attribution_text": "Music: 'Decisions' by Kevin MacLeod (incompetech.com) Licensed under Creative Commons: By Attribution 4.0 License",
        "mood": "home_base",
        "bpm": 78,
    },
    {
        "id": "track_02",
        "title": "Wallpaper",
        "artist": "Kevin MacLeod",
        "genre": "Smooth Synth-Pop Gameplay Anthem",
        "source": "Incompetech",
        "url": "https://incompetech.com/music/royalty-free/mp3-royaltyfree/Wallpaper.mp3",
        "license": "Creative Commons Attribution 4.0 (CC-BY 4.0)",
        "attribution_required": True,
        "attribution_text": "Music: 'Wallpaper' by Kevin MacLeod (incompetech.com) Licensed under Creative Commons: By Attribution 4.0 License",
        "mood": "synth_gameplay",
        "bpm": 118,
    },
    {
        "id": "track_03",
        "title": "Clean Soul",
        "artist": "Kevin MacLeod",
        "genre": "Chill Lo-Fi Gaming Groove",
        "source": "Incompetech",
        "url": "https://incompetech.com/music/royalty-free/mp3-royaltyfree/Clean%20Soul.mp3",
        "license": "Creative Commons Attribution 4.0 (CC-BY 4.0)",
        "attribution_required": True,
        "attribution_text": "Music: 'Clean Soul' by Kevin MacLeod (incompetech.com) Licensed under Creative Commons: By Attribution 4.0 License",
        "mood": "lofi_chill",
        "bpm": 88,
    },
    {
        "id": "track_04",
        "title": "Carefree",
        "artist": "Kevin MacLeod",
        "genre": "Acoustic / Cheerful & Upbeat Gaming",
        "source": "Incompetech",
        "url": "https://incompetech.com/music/royalty-free/mp3-royaltyfree/Carefree.mp3",
        "license": "Creative Commons Attribution 4.0 (CC-BY 4.0)",
        "attribution_required": True,
        "attribution_text": "Music: 'Carefree' by Kevin MacLeod (incompetech.com) Licensed under Creative Commons: By Attribution 4.0 License",
        "mood": "cheerful",
        "bpm": 100,
    },
    {
        "id": "track_05",
        "title": "Life of Riley",
        "artist": "Kevin MacLeod",
        "genre": "Uplifting Sunny Gaming Adventure",
        "source": "Incompetech",
        "url": "https://incompetech.com/music/royalty-free/mp3-royaltyfree/Life%20of%20Riley.mp3",
        "license": "Creative Commons Attribution 4.0 (CC-BY 4.0)",
        "attribution_required": True,
        "attribution_text": "Music: 'Life of Riley' by Kevin MacLeod (incompetech.com) Licensed under Creative Commons: By Attribution 4.0 License",
        "mood": "happy_adventure",
        "bpm": 110,
    },
    {
        "id": "track_06",
        "title": "Pamgaea",
        "artist": "Kevin MacLeod",
        "genre": "Island Marimba & Upbeat Rhythm",
        "source": "Incompetech",
        "url": "https://incompetech.com/music/royalty-free/mp3-royaltyfree/Pamgaea.mp3",
        "license": "Creative Commons Attribution 4.0 (CC-BY 4.0)",
        "attribution_required": True,
        "attribution_text": "Music: 'Pamgaea' by Kevin MacLeod (incompetech.com) Licensed under Creative Commons: By Attribution 4.0 License",
        "mood": "island_chill",
        "bpm": 105,
    },
    {
        "id": "track_07",
        "title": "Daily Beetle",
        "artist": "Kevin MacLeod",
        "genre": "Gentle Acoustic & Woodwinds Crafting",
        "source": "Incompetech",
        "url": "https://incompetech.com/music/royalty-free/mp3-royaltyfree/Daily%20Beetle.mp3",
        "license": "Creative Commons Attribution 4.0 (CC-BY 4.0)",
        "attribution_required": True,
        "attribution_text": "Music: 'Daily Beetle' by Kevin MacLeod (incompetech.com) Licensed under Creative Commons: By Attribution 4.0 License",
        "mood": "peaceful",
        "bpm": 85,
    },
    {
        "id": "track_08",
        "title": "Sneaky Snitch",
        "artist": "Kevin MacLeod",
        "genre": "Playful Stealth & Bouncy Gaming",
        "source": "Incompetech",
        "url": "https://incompetech.com/music/royalty-free/mp3-royaltyfree/Sneaky%20Snitch.mp3",
        "license": "Creative Commons Attribution 4.0 (CC-BY 4.0)",
        "attribution_required": True,
        "attribution_text": "Music: 'Sneaky Snitch' by Kevin MacLeod (incompetech.com) Licensed under Creative Commons: By Attribution 4.0 License",
        "mood": "playful_stealth",
        "bpm": 125,
    },
    {
        "id": "track_09",
        "title": "Fretless",
        "artist": "Kevin MacLeod",
        "genre": "Smooth Bass & Modern Ambient Beats",
        "source": "Incompetech",
        "url": "https://incompetech.com/music/royalty-free/mp3-royaltyfree/Fretless.mp3",
        "license": "Creative Commons Attribution 4.0 (CC-BY 4.0)",
        "attribution_required": True,
        "attribution_text": "Music: 'Fretless' by Kevin MacLeod (incompetech.com) Licensed under Creative Commons: By Attribution 4.0 License",
        "mood": "smooth_groove",
        "bpm": 95,
    },
    {
        "id": "track_10",
        "title": "Groove Grove",
        "artist": "Kevin MacLeod",
        "genre": "Upbeat Funky Gaming Rhythm",
        "source": "Incompetech",
        "url": "https://incompetech.com/music/royalty-free/mp3-royaltyfree/Groove%20Grove.mp3",
        "license": "Creative Commons Attribution 4.0 (CC-BY 4.0)",
        "attribution_required": True,
        "attribution_text": "Music: 'Groove Grove' by Kevin MacLeod (incompetech.com) Licensed under Creative Commons: By Attribution 4.0 License",
        "mood": "funk_groove",
        "bpm": 112,
    },
    {
        "id": "track_11",
        "title": "Electro Cabello",
        "artist": "Kevin MacLeod",
        "genre": "Fresh Upbeat Electronic Latin Dance",
        "source": "Incompetech",
        "url": "https://incompetech.com/music/royalty-free/mp3-royaltyfree/Electro%20Cabello.mp3",
        "license": "Creative Commons Attribution 4.0 (CC-BY 4.0)",
        "attribution_required": True,
        "attribution_text": "Music: 'Electro Cabello' by Kevin MacLeod (incompetech.com) Licensed under Creative Commons: By Attribution 4.0 License",
        "mood": "electro_energy",
        "bpm": 120,
    },
    {
        "id": "track_12",
        "title": "Monkeys Spinning Monkeys",
        "artist": "Kevin MacLeod",
        "genre": "Lively Playful High-Energy Gaming Fun",
        "source": "Incompetech",
        "url": "https://incompetech.com/music/royalty-free/mp3-royaltyfree/Monkeys%20Spinning%20Monkeys.mp3",
        "license": "Creative Commons Attribution 4.0 (CC-BY 4.0)",
        "attribution_required": True,
        "attribution_text": "Music: 'Monkeys Spinning Monkeys' by Kevin MacLeod (incompetech.com) Licensed under Creative Commons: By Attribution 4.0 License",
        "mood": "fun_playful",
        "bpm": 128,
    },
    {
        "id": "track_13",
        "title": "Local Forecast",
        "artist": "Kevin MacLeod",
        "genre": "Smooth Modern Chillout Lo-Fi",
        "source": "Incompetech",
        "url": "https://incompetech.com/music/royalty-free/mp3-royaltyfree/Local%20Forecast.mp3",
        "license": "Creative Commons Attribution 4.0 (CC-BY 4.0)",
        "attribution_required": True,
        "attribution_text": "Music: 'Local Forecast' by Kevin MacLeod (incompetech.com) Licensed under Creative Commons: By Attribution 4.0 License",
        "mood": "chill_modern",
        "bpm": 110,
    },
    {
        "id": "track_14",
        "title": "Somewhere Sunny",
        "artist": "Kevin MacLeod",
        "genre": "Warm Sunny Acoustic Survival Home",
        "source": "Incompetech",
        "url": "https://incompetech.com/music/royalty-free/mp3-royaltyfree/Somewhere%20Sunny.mp3",
        "license": "Creative Commons Attribution 4.0 (CC-BY 4.0)",
        "attribution_required": True,
        "attribution_text": "Music: 'Somewhere Sunny' by Kevin MacLeod (incompetech.com) Licensed under Creative Commons: By Attribution 4.0 License",
        "mood": "sunny_acoustic",
        "bpm": 84,
    },
    {
        "id": "track_15",
        "title": "Clear Waters",
        "artist": "Kevin MacLeod",
        "genre": "Fresh Tranquil Guitar & Flute",
        "source": "Incompetech",
        "url": "https://incompetech.com/music/royalty-free/mp3-royaltyfree/Clear%20Waters.mp3",
        "license": "Creative Commons Attribution 4.0 (CC-BY 4.0)",
        "attribution_required": True,
        "attribution_text": "Music: 'Clear Waters' by Kevin MacLeod (incompetech.com) Licensed under Creative Commons: By Attribution 4.0 License",
        "mood": "serene_calm",
        "bpm": 76,
    },
    {
        "id": "track_16",
        "title": "Bossa Antigua",
        "artist": "Kevin MacLeod",
        "genre": "Breezy Bossa Nova Acoustic Pause",
        "source": "Incompetech",
        "url": "https://incompetech.com/music/royalty-free/mp3-royaltyfree/Bossa%20Antigua.mp3",
        "license": "Creative Commons Attribution 4.0 (CC-BY 4.0)",
        "attribution_required": True,
        "attribution_text": "Music: 'Bossa Antigua' by Kevin MacLeod (incompetech.com) Licensed under Creative Commons: By Attribution 4.0 License",
        "mood": "bossa_chill",
        "bpm": 80,
    },
    {
        "id": "track_17",
        "title": "Constance",
        "artist": "Kevin MacLeod",
        "genre": "Hopeful Acoustic Strings & Exploration",
        "source": "Incompetech",
        "url": "https://incompetech.com/music/royalty-free/mp3-royaltyfree/Constance.mp3",
        "license": "Creative Commons Attribution 4.0 (CC-BY 4.0)",
        "attribution_required": True,
        "attribution_text": "Music: 'Constance' by Kevin MacLeod (incompetech.com) Licensed under Creative Commons: By Attribution 4.0 License",
        "mood": "hopeful_adventure",
        "bpm": 80,
    },
    {
        "id": "track_18",
        "title": "Shores of Avalon",
        "artist": "Kevin MacLeod",
        "genre": "Triumphant Epic Adventure Map",
        "source": "Incompetech",
        "url": "https://incompetech.com/music/royalty-free/mp3-royaltyfree/Shores%20of%20Avalon.mp3",
        "license": "Creative Commons Attribution 4.0 (CC-BY 4.0)",
        "attribution_required": True,
        "attribution_text": "Music: 'Shores of Avalon' by Kevin MacLeod (incompetech.com) Licensed under Creative Commons: By Attribution 4.0 License",
        "mood": "epic_adventure",
        "bpm": 92,
    },
    {
        "id": "track_19",
        "title": "Urban Gauntlet",
        "artist": "Kevin MacLeod",
        "genre": "Exciting Synthesizer Arcade Run",
        "source": "Incompetech",
        "url": "https://incompetech.com/music/royalty-free/mp3-royaltyfree/Urban%20Gauntlet.mp3",
        "license": "Creative Commons Attribution 4.0 (CC-BY 4.0)",
        "attribution_required": True,
        "attribution_text": "Music: 'Urban Gauntlet' by Kevin MacLeod (incompetech.com) Licensed under Creative Commons: By Attribution 4.0 License",
        "mood": "synth_run",
        "bpm": 130,
    },
    {
        "id": "track_20",
        "title": "Volatile Reaction",
        "artist": "Kevin MacLeod",
        "genre": "Punchy Tactical Action & Combat Beats",
        "source": "Incompetech",
        "url": "https://incompetech.com/music/royalty-free/mp3-royaltyfree/Volatile%20Reaction.mp3",
        "license": "Creative Commons Attribution 4.0 (CC-BY 4.0)",
        "attribution_required": True,
        "attribution_text": "Music: 'Volatile Reaction' by Kevin MacLeod (incompetech.com) Licensed under Creative Commons: By Attribution 4.0 License",
        "mood": "tactical_action",
        "bpm": 135,
    },
]


def probe_duration(file_path: Path) -> float:
    """Probes accurate duration using ffprobe."""
    try:
        cmd = [
            "ffprobe",
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(file_path),
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=20)
        return round(float(res.stdout.strip()), 2)
    except Exception:
        return 90.0


def download_and_refresh_catalog():
    print("=== Refreshing Audio Catalog: 100% Fresh & Gaming Mood Only ===")
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

    expected_filenames = set()
    updated_tracks = []

    for item in FRESH_GAMING_CATALOG:
        slug = item["title"].lower().replace(" ", "_")
        dest_file = AUDIO_DIR / f"{slug}.mp3"
        expected_filenames.add(dest_file.name)

        if not dest_file.exists() or dest_file.stat().st_size == 0:
            print(f"Fetching: {item['title']} -> {dest_file.name} ...", end=" ", flush=True)
            req = urllib.request.Request(item["url"], headers=headers)
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = resp.read()
                dest_file.write_bytes(data)
            size_kb = len(data) // 1024
            print(f"DONE ({size_kb} KB)")
        else:
            print(f"Already present: {dest_file.name} ({dest_file.stat().st_size // 1024} KB)")

        duration = probe_duration(dest_file)

        track_dict = dict(item)
        track_dict.pop("url", None)
        track_dict["file_path"] = str(dest_file.resolve().as_posix())
        track_dict["duration"] = duration
        updated_tracks.append(track_dict)

    # Remove any old negative or obsolete mp3 files
    removed_count = 0
    for existing in AUDIO_DIR.glob("*.mp3"):
        if existing.name not in expected_filenames:
            print(f"Removing obsolete/negative audio track: {existing.name}")
            existing.unlink()
            removed_count += 1

    # Save to config/music_library.json
    library_payload = {
        "version": "5.0.0",
        "catalog_type": "Fresh & Upbeat Royalty-Free Gaming Soundtrack (CC-BY 4.0)",
        "total_tracks": len(updated_tracks),
        "tracks": updated_tracks,
    }
    CONFIG_FILE.write_text(json.dumps(library_payload, indent=2), encoding="utf-8")
    print(f"\n[SUCCESS] Saved 20 fresh gaming tracks to {CONFIG_FILE} (Cleaned {removed_count} old tracks).")


if __name__ == "__main__":
    download_and_refresh_catalog()
