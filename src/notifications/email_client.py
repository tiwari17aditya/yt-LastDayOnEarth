"""Email notification and reporting dispatch via SMTP."""

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import List, Dict, Any, Optional
from src.logging_config import get_logger
from src.exceptions import NotificationError

logger = get_logger(component="NotificationSystem")


class EmailNotifier:
    """Dispatches HTML & plain text notifications and reports via SMTP."""

    def __init__(
        self,
        host: str,
        port: int,
        user: Optional[str],
        password: Optional[str],
        recipients: List[str],
    ) -> None:
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.recipients = recipients

    def send_video_published_notification(
        self,
        video_title: str,
        youtube_url: str,
        processing_date: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Send email alert when video publishing succeeds."""
        if not self.recipients or not self.user or not self.password:
            logger.warning("SMTP credentials or recipients not configured; skipping email dispatch.")
            return

        subject = f"[SUCCESS] Published: {video_title}"
        body_html = f"""
        <html>
          <body>
            <h2>🎉 Last Day on Earth Video Published!</h2>
            <p><strong>Video Title:</strong> {video_title}</p>
            <p><strong>Processing Date:</strong> {processing_date}</p>
            <p><strong>Watch on YouTube:</strong> <a href="{youtube_url}">{youtube_url}</a></p>
            <hr>
            <p><small>Automated notification from LastDayOnEarth Video Pipeline.</small></p>
          </body>
        </html>
        """
        self._send_email(subject, body_html)

    def send_failure_notification(
        self,
        video_title: str,
        error_details: Dict[str, Any],
    ) -> None:
        """Send email alert when any critical pipeline stage crashes."""
        if not self.recipients or not self.user or not self.password:
            logger.warning("SMTP credentials or recipients not configured; skipping email dispatch.")
            return

        subject = f"[FAILED] Pipeline Error: {video_title}"
        body_html = f"""
        <html>
          <body>
            <h2>⚠️ Last Day on Earth Pipeline Failed</h2>
            <p><strong>Video:</strong> {video_title}</p>
            <p><strong>Component:</strong> {error_details.get('component', 'N/A')}</p>
            <p><strong>Operation:</strong> {error_details.get('operation', 'N/A')}</p>
            <p><strong>Cause:</strong> {error_details.get('root_cause', 'N/A')}</p>
            <p><strong>Recovery Action:</strong> {error_details.get('recovery_action', 'N/A')}</p>
            <hr>
            <p><small>Automated error alert from LastDayOnEarth Video Pipeline.</small></p>
          </body>
        </html>
        """
        self._send_email(subject, body_html)

    def _send_email(self, subject: str, html_content: str) -> None:
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = self.user
            msg["To"] = ", ".join(self.recipients)
            msg.attach(MIMEText(html_content, "html"))

            with smtplib.SMTP(self.host, self.port) as server:
                server.starttls()
                server.login(self.user, self.password)
                server.sendmail(self.user, self.recipients, msg.as_string())

            logger.info("Notification email dispatched successfully", extra_data={"subject": subject})
        except Exception as e:
            raise NotificationError(
                operation="send_email",
                root_cause=str(e),
                recovery_action="Check SMTP host, port, Gmail App Password, and recipient addresses.",
            )
