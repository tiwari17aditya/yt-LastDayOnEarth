"""YouTube Channel Growth & Performance Digest Generator.

Collects real-time statistics (views, watch time, subscribers, engagement velocity)
and generates executive Markdown/HTML reports to track channel health.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

from src.logging_config import get_logger
from src.google_auth import get_google_credentials
from src.notifications.gmail_client import GmailNotifier
from googleapiclient.discovery import build

logger = get_logger(component="ChannelDigest")


class ChannelGrowthMonitor:
    """Monitors channel statistics, subscriber gains, view velocity, and engagement rates."""

    def __init__(self, reports_dir: Path = Path("reports/analytics")) -> None:
        self.reports_dir = reports_dir
        self.reports_dir.mkdir(parents=True, exist_ok=True)

    def get_youtube_service(self):
        """Constructs authenticated YouTube Data API client."""
        creds = get_google_credentials(
            scopes=[
                "https://www.googleapis.com/auth/youtube.upload",
                "https://www.googleapis.com/auth/youtube.force-ssl",
            ]
        )
        if not creds:
            logger.warning("No Google credentials available for YouTube Analytics")
            return None
        return build("youtube", "v3", credentials=creds, cache_discovery=False)

    def fetch_channel_overview(self, youtube: Any) -> Dict[str, Any]:
        """Fetches high-level subscriber count, total views, and video counts."""
        res = youtube.channels().list(mine=True, part="snippet,statistics,contentDetails").execute()
        items = res.get("items", [])
        if not items:
            return {}

        ch = items[0]
        stats = ch.get("statistics", {})
        snippet = ch.get("snippet", {})
        uploads_id = ch.get("contentDetails", {}).get("relatedPlaylists", {}).get("uploads")

        return {
            "channel_id": ch.get("id"),
            "channel_title": snippet.get("title", "Last Day on Earth Survival"),
            "subscriber_count": int(stats.get("subscriberCount", 0)),
            "total_views": int(stats.get("viewCount", 0)),
            "total_videos": int(stats.get("videoCount", 0)),
            "uploads_playlist_id": uploads_id,
        }

    def fetch_recent_videos(self, youtube: Any, uploads_playlist_id: str, limit: int = 15) -> List[Dict[str, Any]]:
        """Fetches recent published videos with view, like, and comment engagement data."""
        if not uploads_playlist_id:
            return []

        pl_resp = youtube.playlistItems().list(
            playlistId=uploads_playlist_id,
            part="snippet,contentDetails",
            maxResults=limit,
        ).execute()

        video_ids = [item["contentDetails"]["videoId"] for item in pl_resp.get("items", [])]
        if not video_ids:
            return []

        vid_resp = youtube.videos().list(
            id=",".join(video_ids),
            part="snippet,statistics",
        ).execute()

        videos = []
        for item in vid_resp.get("items", []):
            vid_id = item["id"]
            snip = item.get("snippet", {})
            stat = item.get("statistics", {})

            views = int(stat.get("viewCount", 0))
            likes = int(stat.get("likeCount", 0))
            comments = int(stat.get("commentCount", 0))

            like_ratio = (likes / views * 100) if views > 0 else 0.0
            comment_ratio = (comments / views * 100) if views > 0 else 0.0
            total_engagement = ((likes + comments) / views * 100) if views > 0 else 0.0

            videos.append({
                "video_id": vid_id,
                "title": snip.get("title", ""),
                "published_at": snip.get("publishedAt", "")[:10],
                "views": views,
                "likes": likes,
                "comments": comments,
                "like_ratio": round(like_ratio, 2),
                "comment_ratio": round(comment_ratio, 2),
                "engagement_rate": round(total_engagement, 2),
                "url": f"https://youtu.be/{vid_id}",
            })

        return videos

    def compile_digest(self) -> Dict[str, Any]:
        """Gathers full channel overview and per-video metrics into a consolidated dictionary."""
        youtube = self.get_youtube_service()
        if not youtube:
            return {"error": "Unable to initialize YouTube client"}

        overview = self.fetch_channel_overview(youtube)
        uploads_id = overview.get("uploads_playlist_id", "")
        videos = self.fetch_recent_videos(youtube, uploads_id, limit=15)

        avg_like_ratio = sum(v["like_ratio"] for v in videos) / len(videos) if videos else 0.0
        avg_comment_ratio = sum(v["comment_ratio"] for v in videos) / len(videos) if videos else 0.0

        return {
            "timestamp": datetime.now().isoformat(),
            "channel": overview,
            "recent_videos": videos,
            "benchmarks": {
                "average_like_ratio": round(avg_like_ratio, 2),
                "average_comment_ratio": round(avg_comment_ratio, 2),
                "channel_health": "EXCELLENT" if avg_like_ratio >= 4.0 else ("GOOD" if avg_like_ratio >= 2.0 else "FAIR"),
            },
        }

    def generate_markdown_report(self, digest: Dict[str, Any], output_path: Optional[Path] = None) -> Path:
        """Renders formatted Markdown report and persists it to reports/analytics/."""
        ch = digest.get("channel", {})
        benchmarks = digest.get("benchmarks", {})
        videos = digest.get("recent_videos", [])
        date_str = datetime.now().strftime("%Y-%m-%d")

        if not output_path:
            output_path = self.reports_dir / f"channel_digest_{date_str}.md"

        lines = [
            f"# 📊 YouTube Channel Growth & Performance Digest — {date_str}",
            "",
            f"**Channel**: `{ch.get('channel_title', 'LDoE Series')}` | **Subscribers**: `{ch.get('subscriber_count', 0):,}` | **Total Views**: `{ch.get('total_views', 0):,}` | **Videos**: `{ch.get('total_videos', 0)}`",
            "",
            "## 🎯 Key Algorithmic Health Indicators",
            f"- **Channel Health**: `{benchmarks.get('channel_health', 'N/A')}`",
            f"- **Average Like Ratio**: `{benchmarks.get('average_like_ratio', 0.0)}%` (Target: >4.0%)",
            f"- **Average Comment Ratio**: `{benchmarks.get('average_comment_ratio', 0.0)}%` (Target: >0.5%)",
            "",
            "## 🎬 Recent Episode Performance & Engagement",
            "",
            "| Episode Title | Date | Views | Likes | Comments | Like % | Eng. % | Link |",
            "|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|",
        ]

        for v in videos:
            short_title = v["title"][:42] + ("..." if len(v["title"]) > 42 else "")
            lines.append(
                f"| {short_title} | {v['published_at']} | {v['views']:,} | {v['likes']} | {v['comments']} | {v['like_ratio']}% | {v['engagement_rate']}% | [Watch]({v['url']}) |"
            )

        lines.extend([
            "",
            "## 💡 Actionable Growth Recommendations",
            "1. **CTR Momentum**: Videos with custom 3D distressed stencil thumbnails should be monitored for CTR surges.",
            "2. **Viewer Engagement**: Maintain automated creator first comments on every video to boost comment ranking.",
            "3. **Cross-Traffic**: Funnel mobile viewers using vertical 9:16 YouTube Shorts clips linking to full episodes.",
            "",
            "---",
            f"*Generated by LDoE Autonomous Channel Growth Monitor on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*",
        ])

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text("\n".join(lines), encoding="utf-8")
        logger.info(f"Channel performance digest saved to {output_path}")
        return output_path

    def send_digest_email(self, digest: Dict[str, Any], recipients: Optional[List[str]] = None) -> bool:
        """Sends the performance digest as an HTML executive summary via GmailNotifier."""
        try:
            gmail = GmailNotifier(recipients=recipients)

            ch = digest.get("channel", {})
            date_str = datetime.now().strftime("%d %b %Y")
            subject = f"📈 LDoE Channel Growth Digest — {date_str} ({ch.get('subscriber_count', 0)} Subs)"

            html_body = f"""
            <div style="font-family: Arial, sans-serif; background-color: #0f172a; color: #f8fafc; padding: 24px; border-radius: 8px;">
                <h2 style="color: #ef4444; border-bottom: 2px solid #ef4444; padding-bottom: 8px;">
                    Last Day on Earth: Channel Performance Digest
                </h2>
                <p><strong>Subscribers:</strong> {ch.get('subscriber_count', 0):,} &nbsp;|&nbsp; 
                   <strong>Total Views:</strong> {ch.get('total_views', 0):,} &nbsp;|&nbsp; 
                   <strong>Videos:</strong> {ch.get('total_videos', 0)}
                </p>
                <div style="background-color: #1e293b; padding: 16px; border-radius: 6px; margin: 16px 0;">
                    <p style="margin: 0; color: #38bdf8;"><strong>Algorithmic Health:</strong> {digest.get('benchmarks', {}).get('channel_health', 'N/A')}</p>
                    <p style="margin: 4px 0 0 0;">Avg Like Ratio: <strong>{digest.get('benchmarks', {}).get('average_like_ratio', 0.0)}%</strong> &nbsp;|&nbsp; Avg Comment Ratio: <strong>{digest.get('benchmarks', {}).get('average_comment_ratio', 0.0)}%</strong></p>
                </div>
                <p style="color: #94a3b8; font-size: 13px;">Automated report generated by LDoE Pipeline.</p>
            </div>
            """

            return gmail.send_digest_email(
                subject=subject,
                html_body=html_body,
                recipients=recipients,
            )
        except Exception as e:
            logger.warning(f"Failed to email channel digest: {e}")
            return False
