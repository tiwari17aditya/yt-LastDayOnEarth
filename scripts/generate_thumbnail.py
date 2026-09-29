"""CLI utility to generate, brand, and upload high-CTR Last Day on Earth thumbnails."""

import argparse
import io
import shutil
import sys
from pathlib import Path

# Force UTF-8 output
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.logging_config import get_logger
from src.processor.cinematic_branding import (
    apply_cinematic_grunge_branding,
    BADGE_PALETTE,
)

logger = get_logger(component="ThumbnailCLI")

# Signature Last Day on Earth scenario prompts for future episodes
SCENARIO_PROMPTS = {
    "bunker": "Survivor in heavy SWAT tactical armor holding an M16 assault rifle entering the dark subterranean elevator entrance of Bunker Alfa, rotating red warning lights, blast doors.",
    "farm": "Survivor with machete and Glock walking through overgrown cornfield and barn at Crooked Creek Farm, diseased mutant bull in background.",
    "police": "Survivor defending barricades inside a ruined Police Station firing shotgun into incoming waves of infected officers and riot zombies.",
    "port": "Survivor at Blackport sea docks standing next to a military submarine, cargo containers, misty ocean sunset.",
    "chopper": "Survivor riding a custom apocalypse chopper motorcycle speeding down a broken asphalt highway escaping a pursuing zombie horde.",
    "base": "Expansive wooden and stone fortified survivor home base with watchtowers, spikes, farm crops, campfires, sunset.",
    "workshop": "Survivor working inside fortified workshop, smelting furnace molten glow and sparks, weapons wall and blueprints.",
    "storage": "Survivor organizing a massive fortified underground warehouse vault filled with green military crates, guns, medkits.",
    "airdrop": "Survivor discovering an open military cargo airdrop crate with a smoke flare billowing orange smoke in a pine forest.",
    "boss": "Survivor confronting the towering monstrous Blind One or Witch boss in a cavernous lair, glowing eyes and toxic fumes.",
}


def build_cinematic_prompt(episode: int, topic: str = "survival") -> str:
    """Builds the ideal 16:9 prompt for generating future thumbnails matching the sample aesthetic."""
    scenario_desc = SCENARIO_PROMPTS.get(topic.lower(), f"Intense survival action scene featuring {topic}")
    return (
        f"High quality cinematic 3D survival game YouTube thumbnail for Last Day on Earth: Survival. "
        f"16:9 aspect ratio. {scenario_desc}. "
        f"Prominently display bold distressed grunge stencil typography LAST DAY ON EARTH on the left "
        f"(LAST DAY in white, ON in small white, EARTH in distressed blood red with paint splatter). "
        f"In the top right corner, a paint splatter distressed grunge badge with bold white number #{episode}. "
        f"Cinematic lighting, high contrast, dramatic atmosphere, sharp focus, hyper-detailed."
    )


def list_existing_thumbnails():
    """Lists all stored episode thumbnails."""
    thumb_dir = Path("data/thumbnails")
    if not thumb_dir.exists():
        print("No thumbnails directory found at data/thumbnails.")
        return

    files = sorted(thumb_dir.glob("episode_*.jpg"))
    print(f"\n{'='*55}")
    print(f"STORED EPISODE THUMBNAILS ({len(files)} available):")
    print(f"{'='*55}")
    for f in files:
        size_kb = f.stat().st_size / 1024
        print(f"  • {f.name:<18} [{size_kb:6.1f} KB] -> {f}")
    print(f"{'='*55}\n")


def upload_thumbnail_to_youtube(video_id: str, thumbnail_path: Path) -> bool:
    """Uploads thumbnail to YouTube video."""
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
    from src.google_auth import get_google_credentials

    creds = get_google_credentials(
        scopes=[
            "https://www.googleapis.com/auth/youtube.upload",
            "https://www.googleapis.com/auth/youtube.force-ssl",
        ]
    )
    if not creds:
        print("[ERROR] Could not obtain YouTube credentials.")
        return False

    youtube = build("youtube", "v3", credentials=creds)
    try:
        media = MediaFileUpload(str(thumbnail_path), mimetype="image/jpeg", resumable=False)
        youtube.thumbnails().set(videoId=video_id, media_body=media).execute()
        print(f"[SUCCESS] Updated YouTube thumbnail for video {video_id} using {thumbnail_path.name}")
        return True
    except Exception as e:
        print(f"[ERROR] Failed to set thumbnail: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Last Day on Earth Thumbnail Generator & Manager")
    parser.add_argument("--episode", type=int, help="Episode number (e.g. 12, 13, 14)")
    parser.add_argument("--topic", type=str, default="survival", help="Episode topic or scenario keyword")
    parser.add_argument("--from-image", type=Path, help="Background image to apply grunge branding onto")
    parser.add_argument("--from-video", type=Path, help="Video path to extract enhanced keyframe and apply branding")
    parser.add_argument("--output", type=Path, help="Target output file path (default: data/thumbnails/episode_<NN>.jpg)")
    parser.add_argument("--prompt", action="store_true", help="Print the exact AI generation prompt for this episode")
    parser.add_argument("--upload", type=str, help="YouTube video ID to upload the generated thumbnail to")
    parser.add_argument("--list", action="store_true", help="List all generated thumbnails in data/thumbnails")

    args = parser.parse_args()

    if args.list:
        list_existing_thumbnails()
        return

    if args.prompt and args.episode:
        p = build_cinematic_prompt(episode=args.episode, topic=args.topic)
        print(f"\nAI Generation Prompt for Episode #{args.episode} ({args.topic}):\n")
        print(p)
        print("\n")
        return

    if not args.episode and not args.from_image and not args.from_video:
        parser.print_help()
        return

    ep = args.episode or 1
    dest = args.output or Path(f"data/thumbnails/episode_{ep:02d}.jpg")
    dest.parent.mkdir(parents=True, exist_ok=True)

    if args.from_video:
        from src.processor.thumbnail_generator import ThumbnailGenerator
        gen = ThumbnailGenerator()
        gen.generate_thumbnail(
            video_path=args.from_video,
            output_path=dest,
            episode_number=ep,
            branding_style="grunge",
        )
        print(f"[SUCCESS] Generated thumbnail from video: {dest}")

    elif args.from_image:
        apply_cinematic_grunge_branding(
            image_path=args.from_image,
            episode_number=ep,
            output_path=dest,
        )
        print(f"[SUCCESS] Applied grunge branding to image: {dest}")

    else:
        # Check if pre-existing
        existing = Path(f"data/thumbnails/episode_{ep:02d}.jpg")
        if existing.exists():
            print(f"[INFO] Thumbnail already exists for Episode #{ep}: {existing}")
            dest = existing
        else:
            prompt_str = build_cinematic_prompt(episode=ep, topic=args.topic)
            print(f"[INFO] No background image provided. Generating template branding for Episode #{ep}...")
            # Create a rich dark atmospheric backdrop with vignette and branding
            from PIL import Image
            base = Image.new("RGB", (1280, 720), (20, 24, 28))
            temp_base = Path(f"temp/base_ep{ep}.jpg")
            base.save(temp_base, "JPEG")
            apply_cinematic_grunge_branding(
                image_path=temp_base,
                episode_number=ep,
                output_path=dest,
            )
            print(f"[SUCCESS] Rendered branding template to {dest}")
            print(f"[TIP] Use --prompt to see the full AI generation prompt for realistic 3D artwork.")

    if args.upload:
        upload_thumbnail_to_youtube(video_id=args.upload, thumbnail_path=dest)


if __name__ == "__main__":
    main()
