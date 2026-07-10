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
    assert data["project_kind"] == "subtitle"
    assert data["audiobook_chapter_order"] == []
    assert data["episode_texts"] == {}
    assert data["episode_working_texts"] == {}
    assert data["book_chapters"] == {}
    assert data["audiobook_source"] == {}
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
    assert data["metadata"]["format_version"] == "1.4"
    assert data["metadata"]["created_by"] == ""
    assert data["metadata"]["studio"] == ""


def test_ensure_project_compatibility_detects_existing_audiobook():
    data = {
        "project_name": "Book",
        "actors": {},
        "episodes": {
            "Пролог": "book.pdf",
            "Глава 1": "book.pdf",
        },
        "book_chapters": {
            "Пролог": {"html": "<p>Пролог</p>"},
            "Глава 1": {"html": "<p>Глава</p>"},
        },
    }

    ensure_project_compatibility(data)

    assert data["project_kind"] == "audiobook"
    assert data["audiobook_chapter_order"] == ["Пролог", "Глава 1"]


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

    assert data["metadata"]["format_version"] == "1.4"
    assert data["metadata"]["created_by"] == "Studio"
    assert data["metadata"]["studio"] == ""


def test_ensure_project_compatibility_adds_source_lines_to_working_texts():
    data = {
        "metadata": {
            "format_version": "1.3",
            "app_version": "1.0+",
            "created_at": "2026-01-01T00:00:00",
            "modified_at": "2026-01-01T00:00:00",
        },
        "project_name": "Legacy",
        "actors": {},
        "episodes": {},
        "episode_working_texts": {
            "1": {
                "lines": [{
                    "id": "1_0001",
                    "source_ids": [0, 1],
                    "source_texts": ["One", "Two"],
                    "start": 1.0,
                    "end": 3.0,
                    "s_raw": "0:00:01.00",
                    "character": "Hero",
                    "text": "One  Two",
                }]
            }
        },
    }

    ensure_project_compatibility(data)

    payload = data["episode_working_texts"]["1"]
    assert payload["source_ass"] is None
    assert payload["source_lines_origin"] == "reconstructed"
    assert payload["source_lines"] == [
        {
            "id": 0,
            "start": 1.0,
            "end": 3.0,
            "s_raw": "0:00:01.00",
            "character": "Hero",
            "text": "One",
        },
        {
            "id": 1,
            "start": 1.0,
            "end": 3.0,
            "s_raw": "0:00:01.00",
            "character": "Hero",
            "text": "Two",
        },
    ]
