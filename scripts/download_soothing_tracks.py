"""Downloads 20 soothing, chill, pleasant gameplay royalty-free tracks by Kevin MacLeod (CC-BY 4.0)

and updates config/music_library.json.
"""

import json
import urllib.request
import urllib.parse
from pathlib import Path

AUDIO_DIR = Path("config/audio")
AUDIO_DIR.mkdir(parents=True, exist_ok=True)
CONFIG_FILE = Path("config/music_library.json")

# 20 curated soothing, relaxing, pleasant gameplay tracks
SOOTHING_CATALOG = [
    {
        "id": "track_01",
        "title": "Carefree",
        "artist": "Kevin MacLeod",
        "genre": "Acoustic / Cheerful & Upbeat",
        "source": "Incompetech",
        "url": "https://incompetech.com/music/royalty-free/mp3-royaltyfree/Carefree.mp3",
        "license": "Creative Commons Attribution 4.0 (CC-BY 4.0)",
        "attribution_required": True,
        "attribution_text": "Music: 'Carefree' by Kevin MacLeod (incompetech.com) Licensed under Creative Commons: By Attribution 4.0 License",
        "mood": "cheerful",
        "bpm": 100,
    },
    {
        "id": "track_02",
        "title": "Daily Beetle",
        "artist": "Kevin MacLeod",
        "genre": "Gentle Acoustic & Woodwinds",
        "source": "Incompetech",
        "url": "https://incompetech.com/music/royalty-free/mp3-royaltyfree/Daily%20Beetle.mp3",
        "license": "Creative Commons Attribution 4.0 (CC-BY 4.0)",
        "attribution_required": True,
        "attribution_text": "Music: 'Daily Beetle' by Kevin MacLeod (incompetech.com) Licensed under Creative Commons: By Attribution 4.0 License",
        "mood": "peaceful",
        "bpm": 85,
    },
    {
        "id": "track_03",
        "title": "Life of Riley",
        "artist": "Kevin MacLeod",
        "genre": "Uplifting Sunny Folk",
        "source": "Incompetech",
        "url": "https://incompetech.com/music/royalty-free/mp3-royaltyfree/Life%20of%20Riley.mp3",
        "license": "Creative Commons Attribution 4.0 (CC-BY 4.0)",
        "attribution_required": True,
        "attribution_text": "Music: 'Life of Riley' by Kevin MacLeod (incompetech.com) Licensed under Creative Commons: By Attribution 4.0 License",
        "mood": "happy",
        "bpm": 110,
    },
    {
        "id": "track_04",
        "title": "Clean Soul",
        "artist": "Kevin MacLeod",
        "genre": "Chill Lo-Fi Groove",
        "source": "Incompetech",
        "url": "https://incompetech.com/music/royalty-free/mp3-royaltyfree/Clean%20Soul.mp3",
        "license": "Creative Commons Attribution 4.0 (CC-BY 4.0)",
        "attribution_required": True,
        "attribution_text": "Music: 'Clean Soul' by Kevin MacLeod (incompetech.com) Licensed under Creative Commons: By Attribution 4.0 License",
        "mood": "lofi_chill",
        "bpm": 88,
    },
    {
        "id": "track_05",
        "title": "Clear Waters",
        "artist": "Kevin MacLeod",
        "genre": "Tranquil Guitar & Flute",
        "source": "Incompetech",
        "url": "https://incompetech.com/music/royalty-free/mp3-royaltyfree/Clear%20Waters.mp3",
        "license": "Creative Commons Attribution 4.0 (CC-BY 4.0)",
        "attribution_required": True,
        "attribution_text": "Music: 'Clear Waters' by Kevin MacLeod (incompetech.com) Licensed under Creative Commons: By Attribution 4.0 License",
        "mood": "calm",
        "bpm": 76,
    },
    {
        "id": "track_06",
        "title": "Deliberate Thought",
        "artist": "Kevin MacLeod",
        "genre": "Melodic Electronic Ambient",
        "source": "Incompetech",
        "url": "https://incompetech.com/music/royalty-free/mp3-royaltyfree/Deliberate%20Thought.mp3",
        "license": "Creative Commons Attribution 4.0 (CC-BY 4.0)",
        "attribution_required": True,
        "attribution_text": "Music: 'Deliberate Thought' by Kevin MacLeod (incompetech.com) Licensed under Creative Commons: By Attribution 4.0 License",
        "mood": "reflective",
        "bpm": 80,
    },
    {
        "id": "track_07",
        "title": "Fresh Air",
        "artist": "Kevin MacLeod",
        "genre": "Serene Acoustic Strumming",
        "source": "Incompetech",
        "url": "https://incompetech.com/music/royalty-free/mp3-royaltyfree/Fresh%20Air.mp3",
        "license": "Creative Commons Attribution 4.0 (CC-BY 4.0)",
        "attribution_required": True,
        "attribution_text": "Music: 'Fresh Air' by Kevin MacLeod (incompetech.com) Licensed under Creative Commons: By Attribution 4.0 License",
        "mood": "relaxing",
        "bpm": 92,
    },
    {
        "id": "track_08",
        "title": "Fretless",
        "artist": "Kevin MacLeod",
        "genre": "Smooth Bass & Ambient Beats",
        "source": "Incompetech",
        "url": "https://incompetech.com/music/royalty-free/mp3-royaltyfree/Fretless.mp3",
        "license": "Creative Commons Attribution 4.0 (CC-BY 4.0)",
        "attribution_required": True,
        "attribution_text": "Music: 'Fretless' by Kevin MacLeod (incompetech.com) Licensed under Creative Commons: By Attribution 4.0 License",
        "mood": "groove",
        "bpm": 95,
    },
    {
        "id": "track_09",
        "title": "Morning",
        "artist": "Kevin MacLeod",
        "genre": "Gentle Acoustic Awakening",
        "source": "Incompetech",
        "url": "https://incompetech.com/music/royalty-free/mp3-royaltyfree/Morning.mp3",
        "license": "Creative Commons Attribution 4.0 (CC-BY 4.0)",
        "attribution_required": True,
        "attribution_text": "Music: 'Morning' by Kevin MacLeod (incompetech.com) Licensed under Creative Commons: By Attribution 4.0 License",
        "mood": "morning",
        "bpm": 72,
    },
    {
        "id": "track_10",
        "title": "Pamgaea",
        "artist": "Kevin MacLeod",
        "genre": "Island Marimba & Warm Rhythm",
        "source": "Incompetech",
        "url": "https://incompetech.com/music/royalty-free/mp3-royaltyfree/Pamgaea.mp3",
        "license": "Creative Commons Attribution 4.0 (CC-BY 4.0)",
        "attribution_required": True,
        "attribution_text": "Music: 'Pamgaea' by Kevin MacLeod (incompetech.com) Licensed under Creative Commons: By Attribution 4.0 License",
        "mood": "island_chill",
        "bpm": 105,
    },
    {
        "id": "track_11",
        "title": "Peaceful Desolation",
        "artist": "Kevin MacLeod",
        "genre": "Gentle Open World Ambient",
        "source": "Incompetech",
        "url": "https://incompetech.com/music/royalty-free/mp3-royaltyfree/Peaceful%20Desolation.mp3",
        "license": "Creative Commons Attribution 4.0 (CC-BY 4.0)",
        "attribution_required": True,
        "attribution_text": "Music: 'Peaceful Desolation' by Kevin MacLeod (incompetech.com) Licensed under Creative Commons: By Attribution 4.0 License",
        "mood": "ambient_calm",
        "bpm": 68,
    },
    {
        "id": "track_12",
        "title": "Plucky Daisy",
        "artist": "Kevin MacLeod",
        "genre": "Lighthearted Acoustic Picking",
        "source": "Incompetech",
        "url": "https://incompetech.com/music/royalty-free/mp3-royaltyfree/Plucky%20Daisy.mp3",
        "license": "Creative Commons Attribution 4.0 (CC-BY 4.0)",
        "attribution_required": True,
        "attribution_text": "Music: 'Plucky Daisy' by Kevin MacLeod (incompetech.com) Licensed under Creative Commons: By Attribution 4.0 License",
        "mood": "playful",
        "bpm": 90,
    },
    {
        "id": "track_13",
        "title": "Somewhere Sunny",
        "artist": "Kevin MacLeod",
        "genre": "Warm Sunny Acoustic Guitar",
        "source": "Incompetech",
        "url": "https://incompetech.com/music/royalty-free/mp3-royaltyfree/Somewhere%20Sunny.mp3",
        "license": "Creative Commons Attribution 4.0 (CC-BY 4.0)",
        "attribution_required": True,
        "attribution_text": "Music: 'Somewhere Sunny' by Kevin MacLeod (incompetech.com) Licensed under Creative Commons: By Attribution 4.0 License",
        "mood": "sunny",
        "bpm": 84,
    },
    {
        "id": "track_14",
        "title": "Sweeter Vermouth",
        "artist": "Kevin MacLeod",
        "genre": "Cozy Lounge Jazz Lo-Fi",
        "source": "Incompetech",
        "url": "https://incompetech.com/music/royalty-free/mp3-royaltyfree/Sweeter%20Vermouth.mp3",
        "license": "Creative Commons Attribution 4.0 (CC-BY 4.0)",
        "attribution_required": True,
        "attribution_text": "Music: 'Sweeter Vermouth' by Kevin MacLeod (incompetech.com) Licensed under Creative Commons: By Attribution 4.0 License",
        "mood": "cozy",
        "bpm": 70,
    },
    {
        "id": "track_15",
        "title": "Wallpaper",
        "artist": "Kevin MacLeod",
        "genre": "Smooth Synth-Pop Gameplay",
        "source": "Incompetech",
        "url": "https://incompetech.com/music/royalty-free/mp3-royaltyfree/Wallpaper.mp3",
        "license": "Creative Commons Attribution 4.0 (CC-BY 4.0)",
        "attribution_required": True,
        "attribution_text": "Music: 'Wallpaper' by Kevin MacLeod (incompetech.com) Licensed under Creative Commons: By Attribution 4.0 License",
        "mood": "synth_gameplay",
        "bpm": 118,
    },
    {
        "id": "track_16",
        "title": "Water Lily",
        "artist": "Kevin MacLeod",
        "genre": "Tranquil Piano & Strings",
        "source": "Incompetech",
        "url": "https://incompetech.com/music/royalty-free/mp3-royaltyfree/Water%20Lily.mp3",
        "license": "Creative Commons Attribution 4.0 (CC-BY 4.0)",
        "attribution_required": True,
        "attribution_text": "Music: 'Water Lily' by Kevin MacLeod (incompetech.com) Licensed under Creative Commons: By Attribution 4.0 License",
        "mood": "serene_piano",
        "bpm": 65,
    },
    {
        "id": "track_17",
        "title": "Bossa Antigua",
        "artist": "Kevin MacLeod",
        "genre": "Smooth Bossa Nova Acoustic",
        "source": "Incompetech",
        "url": "https://incompetech.com/music/royalty-free/mp3-royaltyfree/Bossa%20Antigua.mp3",
        "license": "Creative Commons Attribution 4.0 (CC-BY 4.0)",
        "attribution_required": True,
        "attribution_text": "Music: 'Bossa Antigua' by Kevin MacLeod (incompetech.com) Licensed under Creative Commons: By Attribution 4.0 License",
        "mood": "bossa_nova",
        "bpm": 80,
    },
    {
        "id": "track_18",
        "title": "Comfortable Mystery",
        "artist": "Kevin MacLeod",
        "genre": "Gentle Vibraphone & Curiosity",
        "source": "Incompetech",
        "url": "https://incompetech.com/music/royalty-free/mp3-royaltyfree/Comfortable%20Mystery.mp3",
        "license": "Creative Commons Attribution 4.0 (CC-BY 4.0)",
        "attribution_required": True,
        "attribution_text": "Music: 'Comfortable Mystery' by Kevin MacLeod (incompetech.com) Licensed under Creative Commons: By Attribution 4.0 License",
        "mood": "curiosity",
        "bpm": 82,
    },
    {
        "id": "track_19",
        "title": "Modern Jazz Samba",
        "artist": "Kevin MacLeod",
        "genre": "Relaxing Latin Jazz Rhythm",
        "source": "Incompetech",
        "url": "https://incompetech.com/music/royalty-free/mp3-royaltyfree/Modern%20Jazz%20Samba.mp3",
        "license": "Creative Commons Attribution 4.0 (CC-BY 4.0)",
        "attribution_required": True,
        "attribution_text": "Music: 'Modern Jazz Samba' by Kevin MacLeod (incompetech.com) Licensed under Creative Commons: By Attribution 4.0 License",
        "mood": "jazz_samba",
        "bpm": 96,
    },
    {
        "id": "track_20",
        "title": "Sneaky Adventure",
        "artist": "Kevin MacLeod",
        "genre": "Playful Lighthearted Stealth",
        "source": "Incompetech",
        "url": "https://incompetech.com/music/royalty-free/mp3-royaltyfree/Sneaky%20Adventure.mp3",
        "license": "Creative Commons Attribution 4.0 (CC-BY 4.0)",
        "attribution_required": True,
        "attribution_text": "Music: 'Sneaky Adventure' by Kevin MacLeod (incompetech.com) Licensed under Creative Commons: By Attribution 4.0 License",
        "mood": "playful_stealth",
        "bpm": 88,
    },
]


def download_soothing_tracks():
    print(f"Downloading 20 soothing, chill gameplay MP3s to {AUDIO_DIR}...")
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

    # Delete old dark audio files in AUDIO_DIR
    for old_f in AUDIO_DIR.glob("*.mp3"):
        old_f.unlink()
    print("Cleaned out previous dark audio tracks.")

    updated_tracks = []
    for item in SOOTHING_CATALOG:
        slug = item["title"].lower().replace(" ", "_")
        dest_file = AUDIO_DIR / f"{slug}.mp3"
        print(f"Downloading: {item['title']} -> {dest_file.name} ...", end=" ", flush=True)

        req = urllib.request.Request(item["url"], headers=headers)
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = resp.read()
            dest_file.write_bytes(data)

        size_kb = len(data) // 1024
        print(f"DONE ({size_kb} KB)")

        track_dict = dict(item)
        track_dict.pop("url", None)
        track_dict["file_path"] = str(dest_file.resolve().as_posix())
        updated_tracks.append(track_dict)

    # Save to config/music_library.json
    library_payload = {
        "version": "3.0.0",
        "catalog_type": "Soothing & Chill Gameplay",
        "total_tracks": len(updated_tracks),
        "tracks": updated_tracks,
    }
    CONFIG_FILE.write_text(json.dumps(library_payload, indent=2), encoding="utf-8")
    print(f"\nSuccessfully downloaded all {len(updated_tracks)} soothing tracks and updated {CONFIG_FILE}!")


if __name__ == "__main__":
    download_soothing_tracks()
