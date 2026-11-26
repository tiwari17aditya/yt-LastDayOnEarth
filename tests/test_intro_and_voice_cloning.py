"""Unit tests for Intro Screen Generation, Profile Branding, and Resilient Voice Cloning Client."""

from pathlib import Path
from unittest.mock import MagicMock, patch

from src.config import get_settings
from src.processor.intro_generator import IntroGenerator, escape_drawtext, resolve_system_font
from src.audio.clone_client import VoiceCloningClient
from src.publisher.youtube_client import YouTubeClient


def test_escape_drawtext():
    assert escape_drawtext("Bunker: Alfa") == "Bunker\\: Alfa"
    assert escape_drawtext("100% loot") == "100\\% loot"
    assert escape_drawtext("It's awesome") == "It\\'s awesome"
    assert escape_drawtext("") == ""


def test_resolve_system_font():
    font = resolve_system_font("bold")
    assert font != ""
    assert isinstance(font, str)


def test_intro_generator_bumper_filters():
    gen = IntroGenerator(
        player_name="adistar656",
        player_id="#9045",
        clan_name="Stark029",
        intro_style="bumper",
    )
    filters = gen.build_bumper_filters(episode_num=132, episode_title="Bunker Alfa Raid")
    vf_text = ",".join(filters)

    assert "adistar656" in vf_text
    assert "\\#9045" in vf_text or "#9045" in vf_text
    assert "Stark029" in vf_text
    assert "EPISODE #132" in vf_text
    assert "BUNKER ALFA RAID" in vf_text
    assert "LAST DAY ON EARTH \\: SURVIVAL" in vf_text
    assert "scale=1920:1080" in vf_text


def test_intro_generator_overlay_filters():
    gen = IntroGenerator(
        player_name="adistar656",
        player_id="#9045",
        clan_name="Stark029",
        intro_style="overlay",
    )
    filters = gen.build_overlay_filters(episode_num=132, duration=4.0)
    vf_text = ",".join(filters)

    assert "adistar656" in vf_text
    assert "Stark029" in vf_text
    assert "fade=t=out" in vf_text
    assert "drawbox" in vf_text


def test_intro_generator_prebaked_intro_selection():
    gen = IntroGenerator(intros_dir=Path("assets/audio/intros"))
    audio_hi = gen.get_prebaked_intro_audio(language="hi")
    assert audio_hi is not None
    assert audio_hi.exists()
    assert audio_hi.suffix == ".mp3"
    assert "hinglish" in audio_hi.name

    audio_en = gen.get_prebaked_intro_audio(language="en")
    assert audio_en is not None
    assert audio_en.exists()
    assert audio_en.suffix == ".mp3"
    assert "english" in audio_en.name


def test_voice_cloning_client_unconfigured():
    client = VoiceCloningClient(endpoint_url=None)
    assert not client.is_configured
    success = client.synthesize(text="Hello", output_path=Path("temp/dummy.mp3"))
    assert not success


def test_voice_cloning_client_success(tmp_path):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.content = b"x" * 2000  # Valid audio bytes

    client = VoiceCloningClient(endpoint_url="https://mock-hf-space.hf.space/clone-voice")
    assert client.is_configured

    dest = tmp_path / "cloned.mp3"
    with patch("requests.post", return_value=mock_resp):
        success = client.synthesize(text="Hello", output_path=dest)
        assert success
        assert dest.exists()
        assert dest.stat().st_size == 2000


def test_voice_cloning_client_resilient_fallback(tmp_path):
    import requests

    client = VoiceCloningClient(endpoint_url="https://mock-hf-space.hf.space/clone-voice", timeout_seconds=2.0)
    dest = tmp_path / "cloned.mp3"

    # Test timeout resilience
    with patch("requests.post", side_effect=requests.Timeout("Connection timed out")):
        success = client.synthesize(text="Test", output_path=dest)
        assert not success
        assert not dest.exists()

    # Test 500 error resilience
    mock_500 = MagicMock()
    mock_500.status_code = 500
    mock_500.content = b"Server Error"
    with patch("requests.post", return_value=mock_500):
        success = client.synthesize(text="Test", output_path=dest)
        assert not success
        assert not dest.exists()


def test_youtube_metadata_includes_player_profile():
    client = YouTubeClient()
    meta = client.generate_metadata(
        video_title="Bunker Alfa Infiltration",
        events=[],
        episode_number=132,
    )
    desc = meta.description
    assert "SURVIVOR PROFILE & CLAN RECRUITMENT:" in desc
    assert "adistar656" in desc
    assert "#9045" in desc
    assert "Stark029" in desc


def test_video_processor_apply_intro_none(tmp_path):
    from src.processor.video_processor import VideoProcessor

    proc = VideoProcessor(output_dir=tmp_path)
    main_v = tmp_path / "main.mp4"
    main_v.write_bytes(b"dummy video")
    out_v = tmp_path / "out.mp4"

    res = proc.apply_intro(main_video=main_v, output_video=out_v, intro_style="none")
    assert res == main_v


def test_config_player_profile_and_intro_defaults():
    settings = get_settings()
    assert settings.processing.ldoe_player_name == "adistar656"
    assert settings.processing.ldoe_player_id == "#9045"
    assert settings.processing.ldoe_clan_name == "Stark029"
    assert settings.processing.intro_style in ["bumper", "overlay", "none"]
    assert settings.processing.intro_audio_enabled is False
    assert settings.processing.intro_audio_language == "en"
    assert "hi" in settings.commentary.multilingual_languages


def test_video_processor_apply_intro_bumper_no_audio_by_default(tmp_path):
    from src.processor.video_processor import VideoProcessor

    proc = VideoProcessor(output_dir=tmp_path)
    main_v = tmp_path / "main.mp4"
    main_v.write_bytes(b"dummy video")
    bg_img = tmp_path / "cover.jpg"
    bg_img.write_bytes(b"dummy image")
    out_v = tmp_path / "out.mp4"

    captured_cmds = []

    def mock_run(cmd, *args, **kwargs):
        captured_cmds.append(cmd)
        mock_res = MagicMock()
        mock_res.returncode = 0
        return mock_res

    with patch("subprocess.run", side_effect=mock_run):
        proc.apply_intro(
            main_video=main_v,
            output_video=out_v,
            intro_style="bumper",
            intro_bg_image=bg_img,
            intro_audio_enabled=False,
        )

    assert len(captured_cmds) == 1
    cmd = captured_cmds[0]
    # Verify no audio input file is added as input 2
    cmd_str = " ".join(cmd)
    assert "[2:a]" not in cmd_str
    assert "avoice" not in cmd_str
    # Verify single audio track delay is used
    assert "adelay=3000|3000" in cmd_str


def test_video_processor_apply_intro_bumper_with_audio_when_enabled(tmp_path):
    from src.processor.video_processor import VideoProcessor

    proc = VideoProcessor(output_dir=tmp_path)
    main_v = tmp_path / "main.mp4"
    main_v.write_bytes(b"dummy video")
    bg_img = tmp_path / "cover.jpg"
    bg_img.write_bytes(b"dummy image")
    out_v = tmp_path / "out.mp4"

    captured_cmds = []

    def mock_run(cmd, *args, **kwargs):
        captured_cmds.append(cmd)
        mock_res = MagicMock()
        mock_res.returncode = 0
        return mock_res

    with patch("subprocess.run", side_effect=mock_run):
        proc.apply_intro(
            main_video=main_v,
            output_video=out_v,
            intro_style="bumper",
            intro_bg_image=bg_img,
            intro_audio_enabled=True,
            intro_audio_language="en",
        )

    assert len(captured_cmds) == 1
    cmd = captured_cmds[0]
    cmd_str = " ".join(cmd)
    # Audio input should be present and should be an English asset
    assert "[2:a]" in cmd_str
    assert "intro_english" in cmd_str
