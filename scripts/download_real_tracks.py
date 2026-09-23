"""Downloads 20 genuine, full-fidelity royalty-free tracks by Kevin MacLeod (CC-BY 4.0)

and updates config/music_library.json.
"""

import json
import urllib.request
import urllib.parse
from pathlib import Path

AUDIO_DIR = Path("config/audio")
AUDIO_DIR.mkdir(parents=True, exist_ok=True)
CONFIG_FILE = Path("config/music_library.json")

# Curated 20 diverse tracks tailored for Last Day on Earth: Survival
TRACK_CATALOG = [
    {
        "id": "track_01",
        "title": "Decisions",
        "artist": "Kevin MacLeod",
        "genre": "Subtle Lo-Fi / Electronic Ambient",
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
        "title": "Aftermath",
        "artist": "Kevin MacLeod",
        "genre": "Apocalyptic Strings & Ambient Drone",
        "source": "Incompetech",
        "url": "https://incompetech.com/music/royalty-free/mp3-royaltyfree/Aftermath.mp3",
        "license": "Creative Commons Attribution 4.0 (CC-BY 4.0)",
        "attribution_required": True,
        "attribution_text": "Music: 'Aftermath' by Kevin MacLeod (incompetech.com) Licensed under Creative Commons: By Attribution 4.0 License",
        "mood": "scavenging",
        "bpm": 65,
    },
    {
        "id": "track_03",
        "title": "Volatile Reaction",
        "artist": "Kevin MacLeod",
        "genre": "Fast Tactical Action & Percussion",
        "source": "Incompetech",
        "url": "https://incompetech.com/music/royalty-free/mp3-royaltyfree/Volatile%20Reaction.mp3",
        "license": "Creative Commons Attribution 4.0 (CC-BY 4.0)",
        "attribution_required": True,
        "attribution_text": "Music: 'Volatile Reaction' by Kevin MacLeod (incompetech.com) Licensed under Creative Commons: By Attribution 4.0 License",
        "mood": "combat",
        "bpm": 135,
    },
    {
        "id": "track_04",
        "title": "Darkling",
        "artist": "Kevin MacLeod",
        "genre": "Ominous Drone & Suspense",
        "source": "Incompetech",
        "url": "https://incompetech.com/music/royalty-free/mp3-royaltyfree/Darkling.mp3",
        "license": "Creative Commons Attribution 4.0 (CC-BY 4.0)",
        "attribution_required": True,
        "attribution_text": "Music: 'Darkling' by Kevin MacLeod (incompetech.com) Licensed under Creative Commons: By Attribution 4.0 License",
        "mood": "tense",
        "bpm": 70,
    },
    {
        "id": "track_05",
        "title": "Mechanolith",
        "artist": "Kevin MacLeod",
        "genre": "Industrial Mechanical Tension",
        "source": "Incompetech",
        "url": "https://incompetech.com/music/royalty-free/mp3-royaltyfree/Mechanolith.mp3",
        "license": "Creative Commons Attribution 4.0 (CC-BY 4.0)",
        "attribution_required": True,
        "attribution_text": "Music: 'Mechanolith' by Kevin MacLeod (incompetech.com) Licensed under Creative Commons: By Attribution 4.0 License",
        "mood": "workshop",
        "bpm": 110,
    },
    {
        "id": "track_06",
        "title": "Industrial Cinematic",
        "artist": "Kevin MacLeod",
        "genre": "Heavy Cinematic Synth Drone",
        "source": "Incompetech",
        "url": "https://incompetech.com/music/royalty-free/mp3-royaltyfree/Industrial%20Cinematic.mp3",
        "license": "Creative Commons Attribution 4.0 (CC-BY 4.0)",
        "attribution_required": True,
        "attribution_text": "Music: 'Industrial Cinematic' by Kevin MacLeod (incompetech.com) Licensed under Creative Commons: By Attribution 4.0 License",
        "mood": "dungeon",
        "bpm": 95,
    },
    {
        "id": "track_07",
        "title": "Constance",
        "artist": "Kevin MacLeod",
        "genre": "Calm Acoustic Strings & Hope",
        "source": "Incompetech",
        "url": "https://incompetech.com/music/royalty-free/mp3-royaltyfree/Constance.mp3",
        "license": "Creative Commons Attribution 4.0 (CC-BY 4.0)",
        "attribution_required": True,
        "attribution_text": "Music: 'Constance' by Kevin MacLeod (incompetech.com) Licensed under Creative Commons: By Attribution 4.0 License",
        "mood": "settlement",
        "bpm": 80,
    },
    {
        "id": "track_08",
        "title": "Echoes of Time",
        "artist": "Kevin MacLeod",
        "genre": "Mysterious Atmospheric Piano",
        "source": "Incompetech",
        "url": "https://incompetech.com/music/royalty-free/mp3-royaltyfree/Echoes%20of%20Time.mp3",
        "license": "Creative Commons Attribution 4.0 (CC-BY 4.0)",
        "attribution_required": True,
        "attribution_text": "Music: 'Echoes of Time' by Kevin MacLeod (incompetech.com) Licensed under Creative Commons: By Attribution 4.0 License",
        "mood": "exploration",
        "bpm": 85,
    },
    {
        "id": "track_09",
        "title": "Shores of Avalon",
        "artist": "Kevin MacLeod",
        "genre": "Epic World Map Adventure",
        "source": "Incompetech",
        "url": "https://incompetech.com/music/royalty-free/mp3-royaltyfree/Shores%20of%20Avalon.mp3",
        "license": "Creative Commons Attribution 4.0 (CC-BY 4.0)",
        "attribution_required": True,
        "attribution_text": "Music: 'Shores of Avalon' by Kevin MacLeod (incompetech.com) Licensed under Creative Commons: By Attribution 4.0 License",
        "mood": "world_map",
        "bpm": 92,
    },
    {
        "id": "track_10",
        "title": "Hitman",
        "artist": "Kevin MacLeod",
        "genre": "Dark Stealth Action",
        "source": "Incompetech",
        "url": "https://incompetech.com/music/royalty-free/mp3-royaltyfree/Hitman.mp3",
        "license": "Creative Commons Attribution 4.0 (CC-BY 4.0)",
        "attribution_required": True,
        "attribution_text": "Music: 'Hitman' by Kevin MacLeod (incompetech.com) Licensed under Creative Commons: By Attribution 4.0 License",
        "mood": "stealth",
        "bpm": 120,
    },
    {
        "id": "track_11",
        "title": "The Complex",
        "artist": "Kevin MacLeod",
        "genre": "Bunker Alfa Electronic Drive",
        "source": "Incompetech",
        "url": "https://incompetech.com/music/royalty-free/mp3-royaltyfree/The%20Complex.mp3",
        "license": "Creative Commons Attribution 4.0 (CC-BY 4.0)",
        "attribution_required": True,
        "attribution_text": "Music: 'The Complex' by Kevin MacLeod (incompetech.com) Licensed under Creative Commons: By Attribution 4.0 License",
        "mood": "bunker",
        "bpm": 130,
    },
    {
        "id": "track_12",
        "title": "Unseen Horrors",
        "artist": "Kevin MacLeod",
        "genre": "Creeping Zombie Suspense",
        "source": "Incompetech",
        "url": "https://incompetech.com/music/royalty-free/mp3-royaltyfree/Unseen%20Horrors.mp3",
        "license": "Creative Commons Attribution 4.0 (CC-BY 4.0)",
        "attribution_required": True,
        "attribution_text": "Music: 'Unseen Horrors' by Kevin MacLeod (incompetech.com) Licensed under Creative Commons: By Attribution 4.0 License",
        "mood": "horror",
        "bpm": 60,
    },
    {
        "id": "track_13",
        "title": "Oppressive Gloom",
        "artist": "Kevin MacLeod",
        "genre": "Foggy Cemetery Dark Drone",
        "source": "Incompetech",
        "url": "https://incompetech.com/music/royalty-free/mp3-royaltyfree/Oppressive%20Gloom.mp3",
        "license": "Creative Commons Attribution 4.0 (CC-BY 4.0)",
        "attribution_required": True,
        "attribution_text": "Music: 'Oppressive Gloom' by Kevin MacLeod (incompetech.com) Licensed under Creative Commons: By Attribution 4.0 License",
        "mood": "grim",
        "bpm": 64,
    },
    {
        "id": "track_14",
        "title": "Anxiety",
        "artist": "Kevin MacLeod",
        "genre": "Heartbeat Threat Pulse",
        "source": "Incompetech",
        "url": "https://incompetech.com/music/royalty-free/mp3-royaltyfree/Anxiety.mp3",
        "license": "Creative Commons Attribution 4.0 (CC-BY 4.0)",
        "attribution_required": True,
        "attribution_text": "Music: 'Anxiety' by Kevin MacLeod (incompetech.com) Licensed under Creative Commons: By Attribution 4.0 License",
        "mood": "threat",
        "bpm": 105,
    },
    {
        "id": "track_15",
        "title": "Gathering Darkness",
        "artist": "Kevin MacLeod",
        "genre": "Nightfall Wilderness Atmosphere",
        "source": "Incompetech",
        "url": "https://incompetech.com/music/royalty-free/mp3-royaltyfree/Gathering%20Darkness.mp3",
        "license": "Creative Commons Attribution 4.0 (CC-BY 4.0)",
        "attribution_required": True,
        "attribution_text": "Music: 'Gathering Darkness' by Kevin MacLeod (incompetech.com) Licensed under Creative Commons: By Attribution 4.0 License",
        "mood": "nightfall",
        "bpm": 72,
    },
    {
        "id": "track_16",
        "title": "Dangerous",
        "artist": "Kevin MacLeod",
        "genre": "Rapid Red Zone Danger",
        "source": "Incompetech",
        "url": "https://incompetech.com/music/royalty-free/mp3-royaltyfree/Dangerous.mp3",
        "license": "Creative Commons Attribution 4.0 (CC-BY 4.0)",
        "attribution_required": True,
        "attribution_text": "Music: 'Dangerous' by Kevin MacLeod (incompetech.com) Licensed under Creative Commons: By Attribution 4.0 License",
        "mood": "danger",
        "bpm": 115,
    },
    {
        "id": "track_17",
        "title": "The Descent",
        "artist": "Kevin MacLeod",
        "genre": "Subterranean Mine Descent",
        "source": "Incompetech",
        "url": "https://incompetech.com/music/royalty-free/mp3-royaltyfree/The%20Descent.mp3",
        "license": "Creative Commons Attribution 4.0 (CC-BY 4.0)",
        "attribution_required": True,
        "attribution_text": "Music: 'The Descent' by Kevin MacLeod (incompetech.com) Licensed under Creative Commons: By Attribution 4.0 License",
        "mood": "underground",
        "bpm": 75,
    },
    {
        "id": "track_18",
        "title": "Halls of the Undead",
        "artist": "Kevin MacLeod",
        "genre": "Heavy Zombie Horde Drums",
        "source": "Incompetech",
        "url": "https://incompetech.com/music/royalty-free/mp3-royaltyfree/Halls%20of%20the%20Undead.mp3",
        "license": "Creative Commons Attribution 4.0 (CC-BY 4.0)",
        "attribution_required": True,
        "attribution_text": "Music: 'Halls of the Undead' by Kevin MacLeod (incompetech.com) Licensed under Creative Commons: By Attribution 4.0 License",
        "mood": "horde",
        "bpm": 125,
    },
    {
        "id": "track_19",
        "title": "Urban Gauntlet",
        "artist": "Kevin MacLeod",
        "genre": "Synthesizer Escape Run",
        "source": "Incompetech",
        "url": "https://incompetech.com/music/royalty-free/mp3-royaltyfree/Urban%20Gauntlet.mp3",
        "license": "Creative Commons Attribution 4.0 (CC-BY 4.0)",
        "attribution_required": True,
        "attribution_text": "Music: 'Urban Gauntlet' by Kevin MacLeod (incompetech.com) Licensed under Creative Commons: By Attribution 4.0 License",
        "mood": "escape",
        "bpm": 130,
    },
    {
        "id": "track_20",
        "title": "Private Reflection",
        "artist": "Kevin MacLeod",
        "genre": "Melodic Acoustic Survival Pause",
        "source": "Incompetech",
        "url": "https://incompetech.com/music/royalty-free/mp3-royaltyfree/Private%20Reflection.mp3",
        "license": "Creative Commons Attribution 4.0 (CC-BY 4.0)",
        "attribution_required": True,
        "attribution_text": "Music: 'Private Reflection' by Kevin MacLeod (incompetech.com) Licensed under Creative Commons: By Attribution 4.0 License",
        "mood": "home_base",
        "bpm": 75,
    },
]


def download_and_update():
    print(f"Downloading 20 authentic royalty-free MP3s to {AUDIO_DIR}...")
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

    # Clean old placeholder files if needed
    updated_tracks = []
    for item in TRACK_CATALOG:
        slug = item["title"].lower().replace(" ", "_")
        dest_file = AUDIO_DIR / f"{slug}.mp3"
        print(f"Fetching: {item['title']} -> {dest_file.name} ...", end=" ", flush=True)

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
        "version": "2.0.0",
        "total_tracks": len(updated_tracks),
        "tracks": updated_tracks,
    }
    CONFIG_FILE.write_text(json.dumps(library_payload, indent=2), encoding="utf-8")
    print(f"\nSuccessfully downloaded all {len(updated_tracks)} tracks and updated {CONFIG_FILE}!")


if __name__ == "__main__":
    download_and_update()
