#!/usr/bin/env python3
"""CLI utility to generate and inspect Last Day on Earth Weekly Pipeline & Channel Reports.

Usage:
  python scripts/generate_weekly_report.py
  python scripts/generate_weekly_report.py --email
  python scripts/generate_weekly_report.py --days 14 --email
"""

import argparse
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.logging_config import get_logger
from src.notifications.report_generator import WeeklyReportGenerator

logger = get_logger(component="WeeklyReportCLI")

# Ensure UTF-8 output encoding on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Generate Last Day on Earth Weekly Pipeline & Growth Report.")
    parser.add_argument("--days", type=lambda x: int(float(x)), default=7, help="Number of past days to aggregate (default: 7)")
    parser.add_argument("--output", type=str, help="Destination markdown path for report")
    parser.add_argument("--email", action="store_true", help="Send formatted HTML report via Gmail/SMTP")

    args = parser.parse_args()

    generator = WeeklyReportGenerator()
    logger.info(f"Aggregating pipeline history and YouTube analytics for the past {args.days} days...")
    summary = generator.compile_weekly_summary(days=args.days)

    out_file = generator.generate_markdown_report(
        summary=summary,
        output_path=Path(args.output) if args.output else None,
    )

    pipe = summary.get("pipeline_metrics", {})
    yt = summary.get("youtube_metrics", {})
    ch = yt.get("channel", {})
    bm = yt.get("benchmarks", {})

    print("\n" + "=" * 65)
    print(f"📊 LAST DAY ON EARTH WEEKLY REPORT ({summary.get('start_date')} to {summary.get('end_date')})")
    print("=" * 65)
    print(f"🎬 Total Videos Processed:    {pipe.get('total_processed', 0)}")
    print(f"🚀 Successfully Published:    {pipe.get('successful_published', 0)}")
    print(f"⚠️ Failed Pipeline Jobs:      {pipe.get('failed_jobs', 0)}")
    print(f"📈 Pipeline Success Rate:     {pipe.get('success_rate_percent', 100.0)}%")
    print(f"⏱️ Footage Rendered:          {pipe.get('total_duration_minutes', 0.0)} minutes")

    if ch:
        print("-" * 65)
        print(f"📺 Channel:                   {ch.get('channel_title', 'Pulse Vector')}")
        print(f"👥 Total Subscribers:         {ch.get('subscriber_count', 0):,}")
        print(f"👁️ Total Channel Views:       {ch.get('total_views', 0):,}")
        print(f"⭐ Algorithmic Health:        {bm.get('channel_health', 'N/A')}")
        print(f"👍 Average Like Ratio:        {bm.get('average_like_ratio', 0.0)}%")

    print("-" * 65)
    print(f"📁 Full Markdown Report:      {out_file}")
    print("=" * 65 + "\n")

    if args.email:
        logger.info("Dispatching weekly report email...")
        sent = generator.send_weekly_report(summary)
        if sent:
            print("✉️ Weekly report dispatched via email successfully.")
        else:
            print("⚠️ Email dispatch skipped or failed (check credentials/recipients).")


if __name__ == "__main__":
    main()
