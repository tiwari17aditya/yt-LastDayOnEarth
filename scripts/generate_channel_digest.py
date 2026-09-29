#!/usr/bin/env python3
"""CLI utility to generate and inspect YouTube channel performance and engagement digest.

Usage:
  python scripts/generate_channel_digest.py
  python scripts/generate_channel_digest.py --email
"""

import argparse
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.logging_config import get_logger
from src.analytics.channel_digest import ChannelGrowthMonitor

logger = get_logger(component="DigestCLI")

# Ensure UTF-8 output encoding on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Generate YouTube Channel Performance & Growth Digest.")
    parser.add_argument("--output", type=str, help="Destination markdown path for report")
    parser.add_argument("--email", action="store_true", help="Send HTML summary via Gmail notifier")

    args = parser.parse_args()

    monitor = ChannelGrowthMonitor()
    logger.info("Gathering YouTube channel performance metrics...")
    digest = monitor.compile_digest()

    if "error" in digest:
        logger.error(f"Failed to gather channel metrics: {digest['error']}")
        sys.exit(1)

    out_file = monitor.generate_markdown_report(
        digest=digest,
        output_path=Path(args.output) if args.output else None,
    )

    ch = digest.get("channel", {})
    bm = digest.get("benchmarks", {})

    print("\n" + "=" * 60)
    print(f"📊 YOUTUBE CHANNEL GROWTH DIGEST: {ch.get('channel_title', '')}")
    print("=" * 60)
    print(f"👥 Subscribers: {ch.get('subscriber_count', 0):,}")
    print(f"👁️ Total Views: {ch.get('total_views', 0):,}")
    print(f"🎬 Total Videos: {ch.get('total_videos', 0)}")
    print(f"⭐ Algorithmic Health: {bm.get('channel_health', 'N/A')}")
    print(f"👍 Avg Like Ratio: {bm.get('average_like_ratio', 0.0)}%")
    print(f"💬 Avg Comment Ratio: {bm.get('average_comment_ratio', 0.0)}%")
    print(f"📁 Full Report: {out_file}")
    print("=" * 60 + "\n")

    if args.email:
        logger.info("Dispatching email notification...")
        sent = monitor.send_digest_email(digest)
        if sent:
            print("✉️ Growth digest dispatched via email successfully.")
        else:
            print("⚠️ Email dispatch skipped (check Gmail credentials).")


if __name__ == "__main__":
    main()
