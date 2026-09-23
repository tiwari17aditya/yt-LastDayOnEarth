"""Script to generate 20 distinct royalty-free style ambient & rhythmic tracks for Last Day on Earth."""

import subprocess
from pathlib import Path

AUDIO_DIR = Path("config/audio")
AUDIO_DIR.mkdir(parents=True, exist_ok=True)

# 20 distinct acoustic/synth harmonic formulas (varying root notes, chords, and rhythmic pulses)
TRACK_SPECS = [
    ("track_01", "survival_instinct.mp3", "sin(55*2*PI*t)*0.18+sin(82.4*2*PI*t)*0.14+sin(110*2*PI*t)*0.1"),
    ("track_02", "zombies_approaching.mp3", "sin(65.4*2*PI*t)*0.2+sin(130.8*2*PI*t)*0.15+sin(196*2*PI*t)*0.1"),
    ("track_03", "wasteland_scavenger.mp3", "sin(73.4*2*PI*t)*0.16+sin(110*2*PI*t)*0.12+sin(146.8*2*PI*t)*0.09"),
    ("track_04", "decisions.mp3", "sin(130.8*2*PI*t)*0.15+sin(164.8*2*PI*t)*0.12+sin(196*2*PI*t)*0.09"),
    ("track_05", "aftermath.mp3", "sin(65.4*2*PI*t)*0.18+sin(98*2*PI*t)*0.14+sin(130.8*2*PI*t)*0.1"),
    ("track_06", "the_bunker.mp3", "sin(58.2*2*PI*t)*0.2+sin(87.3*2*PI*t)*0.14+sin(116.5*2*PI*t)*0.1"),
    ("track_07", "biter_rush.mp3", "sin(87.3*2*PI*t)*0.22+sin(130.8*2*PI*t)*0.15+sin(174.6*2*PI*t)*0.11"),
    ("track_08", "daybreak_patrol.mp3", "sin(146.8*2*PI*t)*0.15+sin(185*2*PI*t)*0.12+sin(220*2*PI*t)*0.09"),
    ("track_09", "darkling.mp3", "sin(49*2*PI*t)*0.2+sin(73.4*2*PI*t)*0.15+sin(98*2*PI*t)*0.1"),
    ("track_10", "sneak_attack.mp3", "sin(65.4*2*PI*t)*0.18+sin(110*2*PI*t)*0.13+sin(130.8*2*PI*t)*0.09"),
    ("track_11", "looting_time.mp3", "sin(164.8*2*PI*t)*0.15+sin(220*2*PI*t)*0.12+sin(261.6*2*PI*t)*0.09"),
    ("track_12", "the_safehouse.mp3", "sin(110*2*PI*t)*0.16+sin(146.8*2*PI*t)*0.12+sin(164.8*2*PI*t)*0.09"),
    ("track_13", "corrupted_world.mp3", "sin(77.7*2*PI*t)*0.18+sin(116.5*2*PI*t)*0.14+sin(155.5*2*PI*t)*0.1"),
    ("track_14", "red_zone_trek.mp3", "sin(98*2*PI*t)*0.2+sin(147*2*PI*t)*0.15+sin(196*2*PI*t)*0.1"),
    ("track_15", "midnight_gathering.mp3", "sin(110*2*PI*t)*0.15+sin(138.5*2*PI*t)*0.12+sin(164.8*2*PI*t)*0.09"),
    ("track_16", "foggy_forest.mp3", "sin(82.4*2*PI*t)*0.15+sin(123.4*2*PI*t)*0.11+sin(164.8*2*PI*t)*0.08"),
    ("track_17", "survival_beat_01.mp3", "sin(110*2*PI*t)*0.18+sin(165*2*PI*t)*0.13+sin(220*2*PI*t)*0.1"),
    ("track_18", "ghost_town_exploration.mp3", "sin(98*2*PI*t)*0.16+sin(147*2*PI*t)*0.12+sin(196*2*PI*t)*0.09"),
    ("track_19", "armored_convoy.mp3", "sin(87.3*2*PI*t)*0.2+sin(130.8*2*PI*t)*0.15+sin(174.6*2*PI*t)*0.11"),
    ("track_20", "nightfall_survival.mp3", "sin(65.4*2*PI*t)*0.18+sin(98*2*PI*t)*0.13+sin(130.8*2*PI*t)*0.1"),
]


def generate_all():
    print(f"Generating 20 distinct background music tracks in {AUDIO_DIR}...")
    for track_id, filename, formula in TRACK_SPECS:
        out_file = AUDIO_DIR / filename
        cmd = [
            "ffmpeg", "-y",
            "-f", "lavfi",
            "-i", f"anoisesrc=c=pink:r=44100:a=0.008,lowpass=f=350[n]; aevalsrc={formula}:s=44100[s]; [s][n]amix=inputs=2:dropout_transition=2,afade=t=in:ss=0:d=2,afade=t=out:st=28:d=2",
            "-t", "30",
            "-c:a", "mp3",
            "-b:a", "192k",
            str(out_file),
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode != 0:
            print(f"Error on {filename}: {res.stderr[-200:]}")
            return
        print(f"Generated {filename}")
    print("All 20 tracks generated successfully!")


if __name__ == "__main__":
    generate_all()
