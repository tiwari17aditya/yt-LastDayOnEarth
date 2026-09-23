"""Tests for structured exception hierarchy."""

from src.exceptions import PipelineError, IngestionError, PrivacyRedactionError


def test_pipeline_error_fields():
    err = PipelineError(
        operation="test_op",
        component="TestComponent",
        root_cause="Sample failure cause",
        recovery_action="Check test parameters",
        file_path="test_file.mp4",
        status="FAILED",
    )
    data = err.to_dict()
    assert data["operation"] == "test_op"
    assert data["component"] == "TestComponent"
    assert data["root_cause"] == "Sample failure cause"
    assert data["recovery_action"] == "Check test parameters"
    assert data["file_path"] == "test_file.mp4"
    assert data["status"] == "FAILED"


def test_ingestion_error_inheritance():
    err = IngestionError(
        operation="download",
        root_cause="Network timeout",
        recovery_action="Retry connection",
        file_path="video.mp4",
    )
    assert isinstance(err, PipelineError)
    assert err.component == "IngestionModule"
