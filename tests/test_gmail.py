"""Unit tests for Gmail API notification client."""

import pytest
from unittest.mock import MagicMock
from src.notifications.gmail_client import GmailNotifier


def test_gmail_notifier_skips_when_no_recipients():
    """Ensure notifier exits cleanly when no recipients are configured."""
    notifier = GmailNotifier(recipients=[])
    # Should not raise exception
    notifier.send_video_published_notification(
        video_title="Test Video",
        youtube_url="https://youtu.be/test",
        processing_date="23/09/2026",
    )
    assert notifier.service is None


def test_gmail_notifier_sends_formatted_email():
    """Ensure email message is constructed and sent via Gmail API."""
    mock_service = MagicMock()
    notifier = GmailNotifier(recipients=["creator@example.com"], sender="me")
    notifier.service = mock_service

    notifier.send_video_published_notification(
        video_title="Survival Run 1",
        youtube_url="https://youtu.be/xyz123",
        processing_date="23/09/2026",
        details={
            "duration_seconds": 188.5,
            "soundtrack_tracks": ["Pamgaea", "Sweeter Vermouth"],
        },
    )

    mock_service.users().messages().send.assert_called_once()
    call_args = mock_service.users().messages().send.call_args[1]
    assert call_args["userId"] == "me"
    assert "raw" in call_args["body"]
