import json
from pathlib import Path

lib = json.loads(Path("config/music_library.json").read_text(encoding="utf-8"))
valid_stems = {t["title"].lower().replace(" ", "_") for t in lib["tracks"]}

audio_dir = Path("config/audio")
deleted = 0
for f in audio_dir.glob("*.mp3"):
    if f.stem not in valid_stems:
        print(f"Removing old placeholder: {f.name}")
        f.unlink()
        deleted += 1

remaining = list(audio_dir.glob("*.mp3"))
print(f"Cleaned up {deleted} old placeholders. Remaining files in config/audio: {len(remaining)}")
for i, f in enumerate(sorted(remaining), 1):
    print(f"  {i:02d}. {f.name} ({f.stat().st_size // 1024} KB)")
