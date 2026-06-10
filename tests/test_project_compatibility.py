"""Tests for project compatibility upgrades."""

from services.project_compatibility import ensure_project_compatibility


def test_ensure_project_compatibility_adds_current_fields_to_legacy_project():
    data = {
        "project_name": "Legacy",
        "actors": {},
        "episodes": {},
        "export_config": {
            "layout_type": "Сценарий 1",
            "merge": False,
            "merge_gap": 12,
            "p_short": 0.3,
            "p_long": 1.7,
        },
    }

    ensure_project_compatibility(data)

    assert data["video_paths"] == {}
    assert data["episode_texts"] == {}
    assert data["global_map"] == {}
    assert data["episode_actor_map"] == {}
    assert data["prompter_config"]
    assert data["docx_import_config"]
    assert data["project_folder"] is None
    assert data["export_config"]["layout_type"] == "Сценарий 1"
    assert data["export_config"]["col_tc"] is True
    assert data["replica_merge_config"] == {
        "merge": False,
        "merge_gap": 12,
        "p_short": 0.3,
        "p_long": 1.7,
    }
    assert data["metadata"]["format_version"] == "0.9"
    assert data["metadata"]["created_by"] == ""
    assert data["metadata"]["studio"] == ""


def test_ensure_project_compatibility_preserves_existing_metadata():
    data = {
        "metadata": {
            "format_version": "1.0",
            "app_version": "1.0+",
            "created_at": "2026-01-01T00:00:00",
            "modified_at": "2026-01-01T00:00:00",
            "created_by": "Studio",
        },
        "project_name": "Current",
        "actors": {},
        "episodes": {},
    }

    ensure_project_compatibility(data)

    assert data["metadata"]["format_version"] == "1.0"
    assert data["metadata"]["created_by"] == "Studio"
    assert data["metadata"]["studio"] == ""
