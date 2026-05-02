import json

import pytest

from services.assignment_service import LOCAL_UNASSIGNED_ACTOR_ID
from services.assignment_transfer_service import (
    ASSIGNMENT_TRANSFER_FORMAT,
    AssignmentTransferService,
)


def test_assignment_transfer_roundtrip(tmp_path):
    service = AssignmentTransferService()
    source = {
        "project_name": "Season 1",
        "actors": {
            "actor1": {"name": "Actor One", "color": "#FF0000"},
        },
        "global_map": {
            "Hero": "actor1",
        },
        "episode_actor_map": {
            "1": {
                "Guest": "actor1",
                "Muted": LOCAL_UNASSIGNED_ACTOR_ID,
            }
        },
    }
    path = tmp_path / "assignments.json"

    service.save_export(source, str(path))

    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["format"] == ASSIGNMENT_TRANSFER_FORMAT
    assert payload["actors"] == source["actors"]
    assert payload["global_map"] == source["global_map"]


def test_import_assignment_transfer_matches_actor_names_and_skips_unknown_episodes():
    service = AssignmentTransferService()
    target = {
        "actors": {
            "existing": {"name": "Actor One", "color": "#00FF00"},
        },
        "global_map": {},
        "episode_actor_map": {},
        "episodes": {"1": "/tmp/episode.ass"},
    }
    payload = {
        "format": ASSIGNMENT_TRANSFER_FORMAT,
        "version": "1.0",
        "actors": {
            "actor1": {"name": "Actor One", "color": "#FF0000"},
            "actor2": {"name": "Actor Two", "color": "#0000FF"},
        },
        "global_map": {
            "Hero": "actor1",
            "Villain": "actor2",
        },
        "episode_actor_map": {
            "1": {"Guest": "actor2"},
            "2": {"Skipped": "actor2"},
        },
    }

    stats = service.import_payload(target, payload)

    assert stats["actors_added"] == 1
    assert stats["actors_matched"] == 1
    assert target["global_map"]["Hero"] == "existing"
    new_actor_id = target["global_map"]["Villain"]
    assert target["actors"][new_actor_id]["name"] == "Actor Two"
    assert target["episode_actor_map"]["1"]["Guest"] == new_actor_id
    assert "2" not in target["episode_actor_map"]
    assert stats["skipped_episode_assignments"] == 1


def test_import_assignment_transfer_rejects_wrong_format():
    service = AssignmentTransferService()

    with pytest.raises(ValueError):
        service.import_payload({}, {"actors": {}, "global_map": {}})
