"""Tests for configuration loading and validation."""

from src.config import get_settings, PipelineSettings


def test_default_settings_instantiation():
    settings = get_settings()
    assert isinstance(settings, PipelineSettings)
    assert settings.drive.input_folder_name == "Input"
    assert settings.drive.processed_folder_name == "Processed"
    assert settings.youtube.category_id == "20"
    assert settings.processing.target_fps == 60
    assert settings.processing.resolution == "1920x1080"
