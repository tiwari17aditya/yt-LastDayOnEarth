"""Automated high-CTR thumbnail generation from video gameplay keyframes."""

import subprocess
from pathlib import Path
from typing import Optional, List, Any
from PIL import Image, ImageDraw, ImageFont, ImageEnhance
from src.logging_config import get_logger
from src.exceptions import VideoProcessingError

logger = get_logger(component="ThumbnailGenerator")


class ThumbnailGenerator:
    """Extracts high-impact gameplay frames, enhances colors, and adds clean branding badges."""

    def __init__(self, output_dir: Path = Path("output")) -> None:
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def select_best_timestamp(self, events: Optional[List[Any]] = None, duration: float = 180.0) -> float:
        """Picks optimal timestamp featuring prominent gameplay action rather than loading screens or menus."""
        if events:
            # Look for active crafting or interaction events occurring once player is in base (>= 30.0s)
            action_keywords = ["bench", "crafting", "smelting", "storage", "chests", "defense", "raid", "workshop"]
            for ev in events:
                desc = getattr(ev, "description", "").lower()
                st = getattr(ev, "start_time", 0.0)
                if any(kw in desc for kw in action_keywords) and st >= 30.0:
                    # Give enough offset so menu/inventory screens have closed
                    if st < 35.0:
                        return min(float(st + 13.6), 45.0)
                    return float(st + 5.0)

            # Fallback to any action event > 15.0s
            for ev in events:
                desc = getattr(ev, "description", "").lower()
                st = getattr(ev, "start_time", 0.0)
                if any(kw in desc for kw in action_keywords) and st > 15.0:
                    return float(st + 5.0)

            # Fallback to second event if first is global map
            if len(events) > 1:
                return float(getattr(events[1], "start_time", 15.0) + 5.0)

        # Default to 25% of video duration (avoiding intro screen)
        if duration > 40.0:
            return min(duration * 0.25, 45.0)
        return max(5.0, duration * 0.2)

    def extract_enhanced_frame(
        self,
        video_path: Path,
        output_frame_path: Path,
        timestamp: float,
    ) -> Path:
        """Extracts 16:9 frame, crops out mobile HUD buttons, and applies cinematic color grading."""
        output_frame_path.parent.mkdir(parents=True, exist_ok=True)

        # 1. Crop to 16:9 centered (cuts extra ultrawide phone edges)
        # 2. Crop 28% symmetrically (crop=iw*0.72:ih*0.72) to eliminate mobile joystick & touch buttons
        # 3. Scale to YouTube standard 1280x720
        # 4. Color grade: +15% contrast, +25% saturation, unsharp filter
        vf = (
            "crop=min(iw\\,ih*16/9):min(ih\\,iw*9/16),"
            "crop=iw*0.72:ih*0.72,"
            "scale=1280:720,"
            "eq=contrast=1.15:brightness=0.02:saturation=1.25,"
            "unsharp=5:5:0.8:5:5:0.0"
        )

        cmd = [
            "ffmpeg",
            "-y",
            "-ss", str(max(0.0, timestamp)),
            "-i", str(video_path),
            "-vf", vf,
            "-vframes", "1",
            "-q:v", "2",
            str(output_frame_path),
        ]

        logger.info(f"Extracting enhanced 16:9 thumbnail at {timestamp:.2f}s from {video_path.name}")
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, check=True)
            if not output_frame_path.exists():
                raise VideoProcessingError(
                    operation="extract_enhanced_frame",
                    root_cause=f"FFmpeg exited without writing thumbnail: {res.stderr}",
                    recovery_action="Check FFmpeg installation and video format.",
                    file_path=str(video_path),
                )
            return output_frame_path
        except subprocess.CalledProcessError as e:
            logger.error(f"FFmpeg thumbnail extraction failed: {e.stderr}")
            raise VideoProcessingError(
                operation="extract_enhanced_frame",
                root_cause=e.stderr or str(e),
                recovery_action="Ensure video has valid video stream and FFmpeg is in PATH.",
                file_path=str(video_path),
            )

    def _apply_cinematic_vignette(self, img: Image.Image) -> Image.Image:
        """Applies a smooth edge vignette to focus attention onto the gameplay action."""
        import numpy as np
        w, h = img.size
        mask = np.zeros((h, w), dtype=np.float32)
        cx, cy = w / 2.0, h / 2.0
        max_rx, max_ry = w / 1.6, h / 1.6

        y_indices, x_indices = np.indices((h, w))
        dist = np.sqrt(((x_indices - cx) / max_rx) ** 2 + ((y_indices - cy) / max_ry) ** 2)

        vignette_threshold = 0.55
        ramp = np.clip((dist - vignette_threshold) / (1.0 - vignette_threshold), 0.0, 1.0)
        mask = ramp * 175.0  # Max shadow alpha

        vig_arr = np.zeros((h, w, 4), dtype=np.uint8)
        vig_arr[..., 3] = mask.astype(np.uint8)
        vig_img = Image.fromarray(vig_arr, mode="RGBA")

        return Image.alpha_composite(img.convert("RGBA"), vig_img)

    def apply_badge_overlay(
        self,
        image_path: Path,
        badge_text: str,
        series_tag: str = "LAST DAY ON EARTH: SURVIVAL",
        hook_text: Optional[str] = None,
    ) -> Path:
        """Draws a premium studio gamer plate with series branding, episode pill, and hook."""
        try:
            with Image.open(image_path) as raw_img:
                img = self._apply_cinematic_vignette(raw_img)
                width, height = img.size

                overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
                draw = ImageDraw.Draw(overlay)

                # Load fonts with high-impact fallbacks
                def load_font(names: List[str], size: int) -> ImageFont.ImageFont:
                    font_dirs = [Path("C:/Windows/Fonts"), Path("/usr/share/fonts")]
                    for name in names:
                        for fdir in font_dirs:
                            fpath = fdir / name
                            if fpath.exists():
                                try:
                                    return ImageFont.truetype(str(fpath), size)
                                except Exception:
                                    pass
                    return ImageFont.load_default()

                font_brand = load_font(["segoeuib.ttf", "arialbd.ttf"], int(height * 0.030))
                font_ep = load_font(["impact.ttf", "arialbd.ttf"], int(height * 0.052))
                font_hook = load_font(["impact.ttf", "arialbd.ttf"], int(height * 0.072))

                px, py = int(width * 0.035), int(height * 0.06)
                brand_str = series_tag.upper()
                ep_str = badge_text.upper()
                hook_str = (hook_text or "").upper().strip()

                b_box = draw.textbbox((0, 0), brand_str, font=font_brand)
                e_box = draw.textbbox((0, 0), ep_str, font=font_ep)
                h_box = draw.textbbox((0, 0), hook_str, font=font_hook) if hook_str else (0, 0, 0, 0)

                brand_w = b_box[2] - b_box[0]
                ep_w = e_box[2] - e_box[0]
                hook_w = h_box[2] - h_box[0]

                plate_w = max(brand_w, ep_w + 30, hook_w) + 48
                plate_h = int(height * 0.23) if hook_str else int(height * 0.15)

                # Dark glassmorphic plate with gold border
                draw.rounded_rectangle(
                    [px, py, px + plate_w, py + plate_h],
                    radius=14,
                    fill=(12, 15, 20, 235),
                    outline=(255, 179, 0, 230),
                    width=3,
                )

                # Series brand tag (amber/gold)
                draw.text((px + 22, py + 14), brand_str, font=font_brand, fill=(255, 193, 7, 255))

                # Episode pill (Flame orange)
                ep_pill_w = ep_w + 22
                pill_y = py + int(height * 0.058)
                pill_h = int(height * 0.065)
                draw.rounded_rectangle(
                    [px + 20, pill_y, px + 20 + ep_pill_w, pill_y + pill_h],
                    radius=6,
                    fill=(230, 81, 0, 255),
                )
                draw.text((px + 30, pill_y + int(pill_h * 0.08)), ep_str, font=font_ep, fill=(255, 255, 255, 255))

                # Dynamic Action Hook (Crisp white with shadow)
                if hook_str:
                    hook_y = pill_y + pill_h + int(height * 0.015)
                    # Shadow
                    draw.text((px + 24, hook_y + 2), hook_str, font=font_hook, fill=(0, 0, 0, 200))
                    # Foreground
                    draw.text((px + 22, hook_y), hook_str, font=font_hook, fill=(255, 255, 255, 255))

                final_img = Image.alpha_composite(img, overlay).convert("RGB")
                final_img.save(image_path, "JPEG", quality=95)
                logger.info(f"Rendered studio thumbnail badge into {image_path.name}")
                return image_path

        except Exception as e:
            logger.warning(f"Could not apply badge overlay to thumbnail: {e}")
            return image_path

    def generate_thumbnail(
        self,
        video_path: Path,
        output_path: Path,
        events: Optional[List[Any]] = None,
        duration: float = 180.0,
        episode_number: Optional[int] = None,
        badge_text: Optional[str] = None,
        hook_text: Optional[str] = None,
        timestamp: Optional[float] = None,
    ) -> Path:
        """Full orchestration: keyframe extraction, 16:9 focus zoom, color enhancement, and studio branding."""
        ts = timestamp if timestamp is not None else self.select_best_timestamp(events=events, duration=duration)
        self.extract_enhanced_frame(video_path, output_path, ts)

        # Default badge text if episode given
        label = badge_text
        if not label and episode_number is not None:
            label = f"EPISODE #{episode_number:02d}"

        # If hook text is not provided, derive from key gameplay event
        if not hook_text and events:
            action_keywords = ["bench", "crafting", "smelting", "storage", "chests", "workshop"]
            for ev in events:
                desc = getattr(ev, "description", "")
                if any(kw in desc.lower() for kw in action_keywords):
                    hook_text = desc.upper()
                    break

        if label:
            self.apply_badge_overlay(output_path, badge_text=label, hook_text=hook_text)

        logger.info(f"Custom 16:9 YouTube thumbnail generated successfully at: {output_path}")
        return output_path

