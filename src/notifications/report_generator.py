"""Weekly and periodic pipeline & channel performance report generator."""

import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional

from src.logging_config import get_logger
from src.config import get_settings
from src.storage.history_tracker import HistoryTracker
from src.analytics.channel_digest import ChannelGrowthMonitor
from src.notifications.gmail_client import GmailNotifier
from src.notifications.email_client import EmailNotifier

logger = get_logger(component="ReportGenerator")


class WeeklyReportGenerator:
    """Aggregates pipeline execution history and channel growth analytics into weekly reports."""

    def __init__(
        self,
        history_file: Path = Path("data/history.json"),
        reports_dir: Path = Path("reports/weekly"),
    ) -> None:
        self.history_file = history_file
        self.reports_dir = reports_dir
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        self.tracker = HistoryTracker(history_file=self.history_file)

    def compile_weekly_summary(self, days: int = 7) -> Dict[str, Any]:
        """Gathers processing history and YouTube metrics for the past `days`."""
        now = datetime.now(timezone.utc)
        cutoff_date = now - timedelta(days=days)
        cutoff_iso = cutoff_date.isoformat()

        all_records = self.tracker.load_records()
        weekly_records = [
            r for r in all_records
            if r.get("timestamp", "") >= cutoff_iso
        ]

        total_processed = len(weekly_records)
        successful = [r for r in weekly_records if r.get("status") == "SUCCESS"]
        failed = [r for r in weekly_records if r.get("status") != "SUCCESS"]

        # If no records in exact window, fall back to recent records for meaningful report
        if not weekly_records and all_records:
            weekly_records = all_records[-7:]
            total_processed = len(weekly_records)
            successful = [r for r in weekly_records if r.get("status") == "SUCCESS"]
            failed = [r for r in weekly_records if r.get("status") != "SUCCESS"]

        success_count = len(successful)
        failed_count = len(failed)
        success_rate = round((success_count / total_processed * 100), 1) if total_processed > 0 else 100.0

        episodes = []
        total_duration_sec = 0.0
        subtitles_count = 0
        privacy_count = 0

        for r in weekly_records:
            details = r.get("details", {})
            dur = details.get("duration_seconds", 0)
            total_duration_sec += dur

            if details.get("subtitles_burned"):
                subtitles_count += 1
            if details.get("privacy_redacted"):
                privacy_count += 1

            title_cands = details.get("title_candidates", {})
            title = (
                title_cands.get("action_hook")
                or title_cands.get("primary")
                or r.get("output_filename")
                or r.get("input_filename", "LDoE Episode")
            )

            episodes.append({
                "job_id": r.get("job_id", ""),
                "title": title,
                "input_filename": r.get("input_filename", ""),
                "status": r.get("status", "UNKNOWN"),
                "youtube_url": r.get("youtube_url", "N/A"),
                "video_id": r.get("video_id") or details.get("video_id", ""),
                "date": r.get("timestamp", "")[:10],
                "duration_minutes": round(dur / 60, 1),
            })

        errors = []
        for r in failed:
            details = r.get("details", {})
            errors.append({
                "job_id": r.get("job_id", ""),
                "filename": r.get("input_filename", ""),
                "error": details.get("root_cause") or details.get("error") or "Unknown error",
                "component": details.get("component", "Pipeline"),
                "date": r.get("timestamp", "")[:10],
            })

        # Fetch live YouTube Channel overview & analytics
        yt_metrics = {}
        try:
            monitor = ChannelGrowthMonitor()
            digest = monitor.compile_digest()
            if "error" not in digest:
                yt_metrics = digest
            else:
                logger.warning(f"Could not load YouTube channel metrics: {digest.get('error')}")
        except Exception as ye:
            logger.warning(f"YouTube Analytics fetch skipped during weekly summary: {ye}")

        start_str = cutoff_date.strftime("%Y-%m-%d")
        end_str = now.strftime("%Y-%m-%d")

        return {
            "generated_at": now.isoformat(),
            "start_date": start_str,
            "end_date": end_str,
            "days_analyzed": days,
            "pipeline_metrics": {
                "total_processed": total_processed,
                "successful_published": success_count,
                "failed_jobs": failed_count,
                "success_rate_percent": success_rate,
                "total_duration_minutes": round(total_duration_sec / 60, 1),
                "subtitles_burned_count": subtitles_count,
                "privacy_redacted_count": privacy_count,
            },
            "episodes": episodes,
            "errors": errors,
            "youtube_metrics": yt_metrics,
        }

    def generate_markdown_report(self, summary: Dict[str, Any], output_path: Optional[Path] = None) -> Path:
        """Renders formatted Markdown summary and saves to reports/weekly/."""
        start_date = summary.get("start_date", "")
        end_date = summary.get("end_date", "")
        pipe = summary.get("pipeline_metrics", {})
        episodes = summary.get("episodes", [])
        errors = summary.get("errors", [])
        yt = summary.get("youtube_metrics", {})
        ch = yt.get("channel", {})
        bm = yt.get("benchmarks", {})

        if not output_path:
            output_path = self.reports_dir / f"weekly_report_{end_date}.md"

        lines = [
            f"# 📊 Weekly Pipeline & Channel Performance Report",
            f"**Period**: `{start_date}` to `{end_date}` | **Generated**: `{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}`",
            "",
            "## ⚙️ Automated Pipeline Execution Statistics",
            f"- **Videos Processed**: `{pipe.get('total_processed', 0)}`",
            f"- **Successfully Published**: `{pipe.get('successful_published', 0)}`",
            f"- **Failed Jobs**: `{pipe.get('failed_jobs', 0)}`",
            f"- **Pipeline Success Rate**: `{pipe.get('success_rate_percent', 100.0)}%`",
            f"- **Total Footage Rendered**: `{pipe.get('total_duration_minutes', 0.0)} mins`",
            f"- **Subtitles Burned**: `{pipe.get('subtitles_burned_count', 0)}`",
            f"- **Privacy Scans Completed**: `{pipe.get('privacy_redacted_count', 0)}`",
            "",
        ]

        if ch:
            lines.extend([
                "## 📈 YouTube Channel Health & Growth",
                f"- **Channel Title**: `{ch.get('channel_title', 'LDoE Series')}`",
                f"- **Subscribers**: `{ch.get('subscriber_count', 0):,}`",
                f"- **Total Views**: `{ch.get('total_views', 0):,}`",
                f"- **Total Published Videos**: `{ch.get('total_videos', 0)}`",
                f"- **Algorithmic Health Rating**: `{bm.get('channel_health', 'N/A')}`",
                f"- **Average Like Ratio**: `{bm.get('average_like_ratio', 0.0)}%`",
                f"- **Average Comment Ratio**: `{bm.get('average_comment_ratio', 0.0)}%`",
                "",
            ])

        lines.extend([
            "## 🎬 Processed Episodes This Week",
            "",
            "| Date | Episode Title | Duration | Status | YouTube URL |",
            "|:---|:---|:---:|:---:|:---|",
        ])

        if episodes:
            for ep in episodes:
                url_display = f"[Watch]({ep['youtube_url']})" if "http" in ep["youtube_url"] else ep["youtube_url"]
                lines.append(
                    f"| {ep['date']} | {ep['title'][:45]} | {ep['duration_minutes']}m | `{ep['status']}` | {url_display} |"
                )
        else:
            lines.append("| — | No videos processed in this period | — | — | — |")

        if errors:
            lines.extend([
                "",
                "## ⚠️ Processing & Publishing Errors",
                "",
                "| Date | File | Component | Error Details |",
                "|:---|:---|:---|:---|",
            ])
            for err in errors:
                lines.append(f"| {err['date']} | `{err['filename']}` | `{err['component']}` | {err['error']} |")

        recent_yt = yt.get("recent_videos", [])
        if recent_yt:
            lines.extend([
                "",
                "## 🎯 Recent Episode Audience Engagement",
                "",
                "| Video Title | Date | Views | Likes | Comments | Like % | Link |",
                "|:---|:---:|:---:|:---:|:---:|:---:|:---:|",
            ])
            for v in recent_yt[:7]:
                title_short = v["title"][:40] + ("..." if len(v["title"]) > 40 else "")
                lines.append(
                    f"| {title_short} | {v['published_at']} | {v['views']:,} | {v['likes']} | {v['comments']} | {v['like_ratio']}% | [Link]({v['url']}) |"
                )

        lines.extend([
            "",
            "---",
            f"*Generated automatically by Last Day on Earth Autonomous Reporting System*",
        ])

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text("\n".join(lines), encoding="utf-8")
        logger.info(f"Weekly report markdown saved to {output_path}")
        return output_path

    def generate_html_report(self, summary: Dict[str, Any]) -> str:
        """Renders rich responsive HTML executive summary for email dispatch."""
        start_date = summary.get("start_date", "")
        end_date = summary.get("end_date", "")
        pipe = summary.get("pipeline_metrics", {})
        episodes = summary.get("episodes", [])
        errors = summary.get("errors", [])
        yt = summary.get("youtube_metrics", {})
        ch = yt.get("channel", {})
        bm = yt.get("benchmarks", {})

        episodes_html = ""
        for ep in episodes:
            status_color = "#10b981" if ep["status"] == "SUCCESS" else "#ef4444"
            url_link = f'<a href="{ep["youtube_url"]}" style="color: #38bdf8; text-decoration: none;">Watch</a>' if "http" in ep["youtube_url"] else "Local"
            episodes_html += f"""
            <tr style="border-bottom: 1px solid #334155;">
                <td style="padding: 10px 12px; color: #94a3b8; font-size: 13px;">{ep['date']}</td>
                <td style="padding: 10px 12px; color: #f8fafc; font-weight: 500;">{ep['title'][:48]}</td>
                <td style="padding: 10px 12px; color: #cbd5e1; font-size: 13px;">{ep['duration_minutes']}m</td>
                <td style="padding: 10px 12px;"><span style="background: {status_color}22; color: {status_color}; padding: 3px 8px; border-radius: 4px; font-size: 12px; font-weight: bold;">{ep['status']}</span></td>
                <td style="padding: 10px 12px;">{url_link}</td>
            </tr>
            """

        errors_html = ""
        if errors:
            errors_html += """
            <h3 style="color: #ef4444; margin-top: 24px;">⚠️ Failures & Warnings</h3>
            <table style="width: 100%; border-collapse: collapse; margin-top: 8px; background: #1e1b4b; border-radius: 6px;">
            """
            for err in errors:
                errors_html += f"""
                <tr style="border-bottom: 1px solid #312e81;">
                    <td style="padding: 8px 12px; color: #fca5a5; font-size: 13px;">{err['date']}</td>
                    <td style="padding: 8px 12px; color: #f8fafc; font-weight: bold;">{err['filename']}</td>
                    <td style="padding: 8px 12px; color: #fecaca; font-size: 13px;">{err['error']}</td>
                </tr>
                """
            errors_html += "</table>"

        return f"""
        <!DOCTYPE html>
        <html>
        <head>
          <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #0b0f19; margin: 0; padding: 24px; color: #f8fafc; }}
            .container {{ max-width: 680px; margin: 0 auto; background: #111827; border-radius: 12px; border: 1px solid #1f2937; overflow: hidden; }}
            .header {{ background: linear-gradient(135deg, #1e293b, #0f172a); padding: 28px 24px; border-bottom: 2px solid #ef4444; }}
            .title {{ margin: 0; font-size: 22px; color: #ffffff; }}
            .subtitle {{ margin: 6px 0 0 0; color: #94a3b8; font-size: 14px; }}
            .content {{ padding: 24px; }}
            .metrics-grid {{ display: flex; flex-wrap: wrap; gap: 12px; margin: 16px 0 24px 0; }}
            .metric-card {{ flex: 1 1 30%; background: #1f2937; padding: 14px 16px; border-radius: 8px; border-left: 4px solid #ef4444; }}
            .metric-label {{ font-size: 12px; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.5px; }}
            .metric-value {{ font-size: 20px; font-weight: bold; color: #ffffff; margin-top: 4px; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 12px; }}
            th {{ text-align: left; padding: 10px 12px; background: #1e293b; color: #94a3b8; font-size: 12px; text-transform: uppercase; }}
            .footer {{ text-align: center; padding: 20px; font-size: 12px; color: #64748b; border-top: 1px solid #1f2937; }}
          </style>
        </head>
        <body>
          <div class="container">
            <div class="header">
              <h1 class="title">📊 [WEEKLY REPORT] Last Day on Earth Pipeline</h1>
              <p class="subtitle">Summary for {start_date} &mdash; {end_date}</p>
            </div>
            <div class="content">
              
              <table style="width: 100%; border: none; margin-bottom: 20px;">
                <tr>
                  <td style="background: #1e293b; padding: 12px 16px; border-radius: 8px; border-left: 4px solid #38bdf8;">
                    <span style="font-size: 11px; color: #94a3b8; text-transform: uppercase;">Videos Processed</span><br>
                    <strong style="font-size: 22px; color: #f8fafc;">{pipe.get('total_processed', 0)}</strong>
                  </td>
                  <td style="width: 12px;"></td>
                  <td style="background: #1e293b; padding: 12px 16px; border-radius: 8px; border-left: 4px solid #10b981;">
                    <span style="font-size: 11px; color: #94a3b8; text-transform: uppercase;">Published Success</span><br>
                    <strong style="font-size: 22px; color: #10b981;">{pipe.get('successful_published', 0)}</strong>
                  </td>
                  <td style="width: 12px;"></td>
                  <td style="background: #1e293b; padding: 12px 16px; border-radius: 8px; border-left: 4px solid #f59e0b;">
                    <span style="font-size: 11px; color: #94a3b8; text-transform: uppercase;">Success Rate</span><br>
                    <strong style="font-size: 22px; color: #f8fafc;">{pipe.get('success_rate_percent', 100.0)}%</strong>
                  </td>
                </tr>
              </table>

              {f'''
              <div style="background: #1e293b; padding: 14px 18px; border-radius: 8px; margin-bottom: 24px; border: 1px solid #334155;">
                <p style="margin: 0; color: #38bdf8; font-weight: bold;">📺 YouTube Channel: {ch.get('channel_title', 'Pulse Vector')}</p>
                <p style="margin: 6px 0 0 0; color: #cbd5e1; font-size: 14px;">
                  👥 <strong>{ch.get('subscriber_count', 0):,}</strong> Subs &nbsp;|&nbsp; 
                  👁️ <strong>{ch.get('total_views', 0):,}</strong> Views &nbsp;|&nbsp; 
                  ⭐ Health: <strong>{bm.get('channel_health', 'N/A')}</strong> &nbsp;|&nbsp;
                  👍 Like Ratio: <strong>{bm.get('average_like_ratio', 0.0)}%</strong>
                </p>
              </div>
              ''' if ch else ''}

              <h3 style="color: #f8fafc; margin: 18px 0 8px 0; font-size: 16px;">🎬 Processed Episodes</h3>
              <table style="width: 100%; border-collapse: collapse; background: #162032; border-radius: 8px; overflow: hidden;">
                <thead>
                  <tr>
                    <th>Date</th>
                    <th>Episode</th>
                    <th>Duration</th>
                    <th>Status</th>
                    <th>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {episodes_html or '<tr><td colspan="5" style="padding: 16px; text-align: center; color: #94a3b8;">No recordings processed this week.</td></tr>'}
                </tbody>
              </table>

              {errors_html}

            </div>
            <div class="footer">
              Automated Periodic Report &bull; Last Day on Earth Video Pipeline &bull; Filter Label: <code>Weekly Reports</code>
            </div>
          </div>
        </body>
        </html>
        """

    def send_weekly_report(
        self,
        summary: Dict[str, Any],
        recipients: Optional[List[str]] = None,
    ) -> bool:
        """Dispatches the weekly report via GmailNotifier or fallback to EmailNotifier."""
        start_date = summary.get("start_date", "")
        end_date = summary.get("end_date", "")
        pipe = summary.get("pipeline_metrics", {})
        published = pipe.get("successful_published", 0)

        # Explicit subject containing "[WEEKLY REPORT]" to match Gmail filter:
        # "Weekly Report" OR "[WEEKLY REPORT]" -> label: lastDayOnEarth-yt/Weekly Reports
        subject = f"📊 [WEEKLY REPORT] Last Day on Earth Pipeline Summary — {start_date} to {end_date} ({published} Published)"
        html_body = self.generate_html_report(summary)

        settings = get_settings()
        target_recipients = recipients or settings.gmail.recipients or settings.smtp.recipients

        if not target_recipients:
            logger.warning("No notification recipients configured; skipping weekly report email dispatch.")
            return False

        # 1. Try GmailNotifier
        try:
            gmail = GmailNotifier(recipients=target_recipients, sender=settings.gmail.sender)
            if gmail.send_digest_email(subject=subject, html_body=html_body, recipients=target_recipients):
                logger.info("Weekly report dispatched successfully via Gmail API")
                return True
        except Exception as ge:
            logger.warning(f"Gmail API weekly report dispatch failed: {ge}. Attempting SMTP fallback...")

        # 2. Fallback to EmailNotifier (SMTP)
        try:
            smtp_client = EmailNotifier(
                host=settings.smtp.host,
                port=settings.smtp.port,
                user=settings.smtp.user,
                password=settings.smtp.password,
                recipients=target_recipients,
            )
            sent = smtp_client.send_digest_email(subject=subject, html_body=html_body, recipients=target_recipients)
            if sent:
                logger.info("Weekly report dispatched successfully via SMTP fallback")
                return True
        except Exception as se:
            logger.error(f"SMTP fallback weekly report dispatch also failed: {se}")

        return False
