"""Tests for live preview helper functions."""

from ui.preview_helpers import (
    apply_preview_settings,
    build_preview_project_data,
    get_export_highlight_ids,
    get_export_negative_ids,
)


def test_build_preview_project_data_returns_live_project_for_regular_preview():
    project_data = {"export_config": {"use_color": True}}

    result = build_preview_project_data(project_data, use_override_lines=False)

    assert result is project_data


def test_build_preview_project_data_sanitizes_quick_preview_copy():
    project_data = {
        "actors": {"actor-1": {"name": "Actor"}},
        "global_map": {"Hero": "actor-1"},
        "episode_actor_map": {"1": {"Hero": "actor-1"}},
        "export_config": {
            "use_color": True,
            "highlight_ids_export": ["actor-1"],
            "highlight_negative_ids_export": ["actor-1"],
        },
    }

    result = build_preview_project_data(project_data, use_override_lines=True)

    assert result is not project_data
    assert result["actors"] == {}
    assert result["global_map"] == {}
    assert result["episode_actor_map"] == {}
    assert result["export_config"]["use_color"] is False
    assert result["export_config"]["highlight_ids_export"] == []
    assert result["export_config"]["highlight_negative_ids_export"] == []
    assert project_data["actors"] == {"actor-1": {"name": "Actor"}}


def test_export_actor_filter_helpers_normalize_missing_negative_ids():
    project_data = {"export_config": {"highlight_ids_export": ["actor-1"]}}

    assert get_export_highlight_ids(project_data) == ["actor-1"]
    assert get_export_negative_ids(project_data) == []


def test_apply_preview_settings_updates_export_config():
    cfg = {}

    apply_preview_settings(cfg, {
        "layout_type": "Сценарий 1",
        "col_tc": False,
        "col_char": True,
        "col_actor": False,
        "col_text": True,
        "round_time": True,
        "time_display": "start",
        "f_time": 13,
        "f_char": 14,
        "f_actor": 15,
        "f_text": 16,
        "table_width_time": 6.5,
        "table_width_char": 11.5,
        "table_width_actor": 9.5,
        "soften_colors": False,
    })

    assert cfg == {
        "layout_type": "Сценарий 1",
        "col_tc": False,
        "col_char": True,
        "col_actor": False,
        "col_text": True,
        "round_time": True,
        "time_display": "start",
        "f_time": 13,
        "f_char": 14,
        "f_actor": 15,
        "f_text": 16,
        "table_width_time": 6.5,
        "table_width_char": 11.5,
        "table_width_actor": 9.5,
        "soften_colors": False,
    }
