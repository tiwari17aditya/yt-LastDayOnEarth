"""Email notification dispatch via Google Gmail API v1."""

import base64
from email.message import EmailMessage
from typing import List, Dict, Any, Optional

from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

from src.logging_config import get_logger
from src.exceptions import NotificationError
from src.google_auth import get_google_credentials

logger = get_logger(component="GmailNotifier")


class GmailNotifier:
    """Dispatches HTML & plain text notifications using the Google Gmail API v1."""

    def __init__(
        self,
        credentials: Optional[Credentials] = None,
        recipients: Optional[List[str]] = None,
        sender: str = "me",
    ) -> None:
        self.credentials = credentials
        self.recipients = recipients or []
        self.sender = sender
        self.service = None

    def connect(self) -> None:
        """Initializes connection to Gmail API v1."""
        if self.service:
            return

        try:
            if not self.credentials:
                self.credentials = get_google_credentials(
                    scopes=["https://www.googleapis.com/auth/gmail.send"]
                )

            if not self.credentials:
                logger.warning("No Google credentials available for Gmail API; notifications will be skipped.")
                return

            self.service = build("gmail", "v1", credentials=self.credentials, cache_discovery=False)
            logger.info("Successfully connected to Google Gmail API v1")
        except Exception as e:
            logger.error(f"Failed to connect to Gmail API: {e}")
            raise NotificationError(
                operation="gmail_connect",
                root_cause=str(e),
                recovery_action="Ensure Gmail API is enabled and 'gmail.send' scope is authorized.",
            )

    def send_video_published_notification(
        self,
        video_title: str,
        youtube_url: str,
        processing_date: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Send rich HTML email alert when video upload succeeds."""
        if not self.recipients:
            logger.warning("No notification recipients configured; skipping email dispatch.")
            return

        self.connect()
        if not self.service:
            logger.warning("Gmail API service unavailable; skipping email dispatch.")
            return

        details = details or {}
        duration_s = details.get("duration_seconds", 0)
        mins = int(duration_s // 60)
        secs = int(duration_s % 60)
        tracks = details.get("soundtrack_tracks", [])
        tracks_html = "".join([f"<li>🎵 {t}</li>" for t in tracks]) or "<li>Royalty-free soothing background track</li>"

        subject = f"🚀 [SUCCESS] Published to YouTube: {video_title}"
        body_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
          <style>
            body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f4f7f9; margin: 0; padding: 20px; }}
            .card {{ max-width: 600px; margin: 0 auto; background: #ffffff; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.08); overflow: hidden; }}
            .header {{ background: linear-gradient(135deg, #1e88e5, #1565c0); color: white; padding: 24px; text-align: center; }}
            .content {{ padding: 24px; color: #333333; }}
            .button {{ display: inline-block; padding: 12px 24px; background: #d32f2f; color: #ffffff !important; text-decoration: none; border-radius: 6px; font-weight: bold; margin: 16px 0; }}
            .stats {{ background: #f8fafc; border-left: 4px solid #1e88e5; padding: 12px 16px; margin: 16px 0; border-radius: 4px; }}
            .footer {{ text-align: center; padding: 16px; font-size: 12px; color: #888888; border-top: 1px solid #eeeeee; }}
          </style>
        </head>
        <body>
          <div class="card">
            <div class="header">
              <h1 style="margin:0; font-size: 24px;">🎉 Video Published Successfully!</h1>
              <p style="margin: 8px 0 0 0; opacity: 0.9;">Last Day on Earth Automated Pipeline</p>
            </div>
            <div class="content">
              <h3>{video_title}</h3>
              <p>Your latest gameplay recording has been processed, subtitled with sleek action cues, mixed with soothing music, and published to YouTube.</p>
              
              <div style="text-align: center;">
                <a href="{youtube_url}" class="button" target="_blank">▶ Watch on YouTube</a>
              </div>

              <div class="stats">
                <p><strong>Published Link:</strong> <a href="{youtube_url}">{youtube_url}</a></p>
                <p><strong>Video Duration:</strong> {mins}m {secs}s</p>
                <p><strong>Processing Date:</strong> {processing_date}</p>
                <p><strong>Audio Tracks Mixed:</strong></p>
                <ul>{tracks_html}</ul>
              </div>

              <p style="font-size: 13px; color: #666;">The original video in Google Drive has been safely moved from <code>Input</code> to <code>Processed</code>.</p>
            </div>
            <div class="footer">
              Automated message from LastDayOnEarth Cloud Video Pipeline • Triggered by GitHub Actions
            </div>
          </div>
        </body>
        </html>
        """

        self._dispatch(subject, body_html)

    def send_failure_notification(
        self,
        video_title: str,
        error_details: Dict[str, Any],
    ) -> None:
        """Send rich HTML email alert when pipeline encounters a critical error."""
        if not self.recipients:
            return

        self.connect()
        if not self.service:
            return

        subject = f"⚠️ [ALERT] Pipeline Failed: {video_title}"
        body_html = f"""
        <!DOCTYPE html>
        <html>
        <body style="font-family: Arial, sans-serif; background: #fff5f5; padding: 20px;">
          <div style="max-width: 600px; margin: 0 auto; background: white; padding: 24px; border-radius: 8px; border: 1px solid #feb2b2;">
            <h2 style="color: #c53030; margin-top: 0;">⚠️ Last Day on Earth Pipeline Failed</h2>
            <p><strong>Video:</strong> {video_title}</p>
            <p><strong>Component:</strong> {error_details.get('component', 'N/A')}</p>
            <p><strong>Operation:</strong> {error_details.get('operation', 'N/A')}</p>
            <p><strong>Root Cause:</strong> <code style="background: #edf2f7; padding: 2px 6px;">{error_details.get('root_cause', 'N/A')}</code></p>
            <p><strong>Suggested Action:</strong> {error_details.get('recovery_action', 'N/A')}</p>
            <hr style="border: 0; border-top: 1px solid #eee; margin: 20px 0;">
            <p style="font-size: 12px; color: #718096;">Automated alert from LastDayOnEarth Pipeline.</p>
          </div>
        </body>
        </html>
        """
        self._dispatch(subject, body_html)

    def _dispatch(self, subject: str, html_body: str) -> None:
        """Encodes and sends message via Gmail API."""
        try:
            for recipient in self.recipients:
                msg = EmailMessage()
                msg["Subject"] = subject
                msg["From"] = self.sender
                msg["To"] = recipient
                msg.set_content("Please enable HTML viewing to see this notification.")
                msg.add_alternative(html_body, subtype="html")

                raw_bytes = msg.as_bytes()
                encoded_message = base64.urlsafe_b64encode(raw_bytes).decode("utf-8")

                self.service.users().messages().send(
                    userId="me",
                    body={"raw": encoded_message},
                ).execute()

                logger.info(f"Notification email dispatched via Gmail API to {recipient}")

        except Exception as e:
            logger.error(f"Failed to send email via Gmail API: {e}")
            raise NotificationError(
                operation="gmail_send",
                root_cause=str(e),
                recovery_action="Check Gmail API quota, 'gmail.send' scope, or recipient address.",
            )
