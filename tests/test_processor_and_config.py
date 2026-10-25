from src.config import _safe_int, _safe_float, get_settings
from src.processor.video_processor import VideoProcessor


def test_safe_int_and_float_parsers():
    assert _safe_int("", 587) == 587
    assert _safe_int("   ", 587) == 587
    assert _safe_int(None, 587) == 587
    assert _safe_int("invalid", 587) == 587
    assert _safe_int("465", 587) == 465

    assert _safe_float("", 9.5) == 9.5
    assert _safe_float("   ", 9.5) == 9.5
    assert _safe_float(None, 9.5) == 9.5
    assert _safe_float("invalid", 9.5) == 9.5
    assert _safe_float("8.0", 9.5) == 8.0


def test_config_with_empty_env_variables(monkeypatch):
    monkeypatch.setenv("SMTP_PORT", "")
    monkeypatch.setenv("GDRIVE_OUTPUT_RETENTION_DAYS", "")
    monkeypatch.setenv("VIDEO_TARGET_FPS", "")
    monkeypatch.setenv("PEERTUBE_PRIVACY_STATUS", "")
    monkeypatch.setenv("OUTRO_TAIL_DURATION", "")

    settings = get_settings()
    assert settings.smtp.port == 587
    assert settings.drive.output_retention_days == 7
    assert settings.processing.target_fps == 60
    assert settings.peertube.privacy_status == 1
    assert settings.processing.outro_tail_duration == 9.5


def test_video_processor_build_ffmpeg_command_single_pass_with_outro(tmp_path):
    vp = VideoProcessor(output_dir=tmp_path)
    input_v = tmp_path / "input.mp4"
    output_v = tmp_path / "output.mp4"
    music = tmp_path / "music.mp3"
    outro = tmp_path / "outro.mp4"

    input_v.touch()
    music.touch()
    outro.touch()

    cmd = vp.build_ffmpeg_command(
        input_video=input_v,
        output_video=output_v,
        music_file=music,
        outro_video=outro,
        ducking_db="-10dB",
        preset="ultrafast",
    )

    cmd_str = " ".join(cmd)
    assert "-filter_complex" in cmd_str
    assert "concat=n=2:v=1:a=1" in cmd_str
    assert "-map [vout]" in cmd_str
    assert "-map [aout]" in cmd_str
    assert str(outro) in cmd_str
    assert str(music) in cmd_str


def test_video_processor_build_ffmpeg_command_without_outro(tmp_path):
    vp = VideoProcessor(output_dir=tmp_path)
    input_v = tmp_path / "input.mp4"
    output_v = tmp_path / "output.mp4"
    music = tmp_path / "music.mp3"

    input_v.touch()
    music.touch()

    cmd = vp.build_ffmpeg_command(
        input_video=input_v,
        output_video=output_v,
        music_file=music,
        outro_video=None,
    )

    cmd_str = " ".join(cmd)
    assert "-filter_complex" in cmd_str
    assert "concat=n=2" not in cmd_str
    assert str(music) in cmd_str
