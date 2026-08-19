from unittest.mock import patch

from services.project_fps_service import (
    consider_ass_fps,
    consider_video_fps,
    detect_ass_fps,
    effective_merge_config,
    ensure_project_settings,
    set_project_fps,
)


def test_detect_ass_fps_supports_decimal_and_fraction(tmp_path):
    decimal = tmp_path / "decimal.ass"
    decimal.write_text(
        "[Script Info]\nVideo FPS: 23.976\n[Events]\n",
        encoding="utf-8",
    )
    fraction = tmp_path / "fraction.ass"
    fraction.write_text(
        "[Script Info]\nFrameRate: 24000/1001\n[Events]\n",
        encoding="utf-8",
    )

    assert detect_ass_fps(str(decimal)) == 23.976
    assert abs(detect_ass_fps(str(fraction)) - 23.976) < 0.001


def test_only_first_ass_is_considered_for_project_fps(tmp_path):
    first = tmp_path / "first.ass"
    first.write_text("[Script Info]\nTitle: No FPS\n", encoding="utf-8")
    second = tmp_path / "second.ass"
    second.write_text("[Script Info]\nFPS: 30\n", encoding="utf-8")
    data = {}

    assert consider_ass_fps(data, str(first))
    assert not consider_ass_fps(data, str(second))
    assert data["project_settings"]["fps"] == 25.0
    assert data["project_settings"]["fps_source"] == "default"


def test_first_ass_fps_overrides_earlier_video_detection(tmp_path):
    ass = tmp_path / "first.ass"
    ass.write_text("[Script Info]\nVideo Frame Rate: 24\n", encoding="utf-8")
    data = {}

    with patch(
        "services.project_fps_service.probe_video_fps",
        return_value=29.97,
    ):
        assert consider_video_fps(data, "/video/first.mp4")
    assert data["project_settings"]["fps_source"] == "video"

    assert consider_ass_fps(data, str(ass))
    assert data["project_settings"]["fps"] == 24.0
    assert data["project_settings"]["fps_source"] == "ass"


def test_manual_project_fps_has_priority_over_detection(tmp_path):
    ass = tmp_path / "first.ass"
    ass.write_text("[Script Info]\nFPS: 30\n", encoding="utf-8")
    data = {}

    assert set_project_fps(data, 25.5)
    assert not consider_ass_fps(data, str(ass))
    assert not consider_video_fps(data, "/video/first.mp4")
    assert data["project_settings"]["fps"] == 25.5
    assert data["project_settings"]["fps_source"] == "manual"


def test_old_project_merge_config_migrates_only_fps():
    data = {
        "script_storage": {
            "model": "dynamic_source",
            "schema_revision": 1,
            "merge_config": {
                "merge": False,
                "merge_gap": 60,
                "fps": 30,
            },
            "episodes": {},
        }
    }

    settings = ensure_project_settings(data)

    assert settings["fps"] == 30.0
    assert settings["fps_source"] == "legacy"
    assert "merge_config" not in data["script_storage"]


def test_effective_merge_config_uses_global_seconds_and_project_fps():
    data = {"project_settings": {"fps": 23.976, "fps_source": "manual"}}

    config = effective_merge_config(data, {
        "merge": True,
        "merge_gap_seconds": 2.5,
    })

    assert config["fps"] == 23.976
    assert config["merge_gap_seconds"] == 2.5
    assert abs(config["merge_gap"] - 59.94) < 0.0001
