"""Tests for project compatibility upgrades."""

from uuid import UUID

from config.constants import PROJECT_VERSION
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
    assert data["audiobook_document"] == {}
    assert data["episode_texts"] == {}
    assert data["episode_working_texts"] == {}
    assert data["global_map"] == {}
    assert data["character_aliases"] == {}
    assert data["episode_actor_map"] == {}
    assert data["prompter_config"]
    assert data["project_folder"] is None
    assert data["export_config"]["layout_type"] == "Сценарий 1"
    assert data["export_config"]["col_tc"] is True
    assert not {
        "replica_merge_config", "ass_import_config", "srt_import_config",
        "docx_import_config",
    } & data.keys()
    assert data["metadata"]["format_version"] == PROJECT_VERSION
    assert data["metadata"]["created_by"] == ""
    assert data["metadata"]["studio"] == ""


def test_ensure_project_compatibility_preserves_current_audiobook():
    data = {
        "project_name": "Book",
        "actors": {},
        "episodes": {
            "Пролог": "book.pdf",
            "Глава 1": "book.pdf",
        },
        "project_kind": "audiobook",
        "audiobook_document": {"chapters": [
            {"title": "Пролог", "blocks": []},
            {"title": "Глава 1", "blocks": []},
        ]},
    }

    ensure_project_compatibility(data)

    assert data["project_kind"] == "audiobook"
    assert [
        chapter["title"]
        for chapter in data["audiobook_document"]["chapters"]
    ] == ["Пролог", "Глава 1"]


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

    assert data["metadata"]["format_version"] == PROJECT_VERSION
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


def test_compatibility_rebuilds_every_legacy_actor_reference_with_uuids():
    first = "1788437715.85358"
    second = "global_1788437730.771291"
    data = {
        "project_name": "Legacy casting",
        "actors": {
            first: {"name": "One", "color": "#123456"},
            second: {"name": "Two", "color": "#654321"},
        },
        "episodes": {"1": "episode.ass"},
        "global_map": {"Crowd": [first, second]},
        "episode_actor_map": {"1": {"Guest": second}},
        "audiobook_settings": {
            "slots": [{"character": "Crowd", "actor_id": first}],
        },
        "audiobook_document": {
            "chapters": [{
                "blocks": [{"runs": [{"actor_id": second}]}],
            }],
        },
        "export_config": {
            "highlight_ids_export": [first, second],
            "highlight_negative_ids_export": [second],
        },
    }

    ensure_project_compatibility(data)

    migrated_ids = list(data["actors"])
    assert all(str(UUID(actor_id)) == actor_id for actor_id in migrated_ids)
    first_uuid, second_uuid = migrated_ids
    assert data["global_map"]["Crowd"] == [first_uuid, second_uuid]
    assert data["episode_actor_map"]["1"]["Guest"] == second_uuid
    assert data["audiobook_settings"]["slots"][0]["actor_id"] == first_uuid
    run = data["audiobook_document"]["chapters"][0]["blocks"][0]["runs"][0]
    assert run["actor_id"] == second_uuid
    assert data["export_config"]["highlight_ids_export"] == [
        first_uuid, second_uuid,
    ]
    assert data["export_config"]["highlight_negative_ids_export"] == [
        second_uuid,
    ]
