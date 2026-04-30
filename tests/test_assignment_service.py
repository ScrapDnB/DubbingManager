from services.assignment_service import (
    ASSIGNMENT_SCOPE_EPISODE,
    ASSIGNMENT_SCOPE_GLOBAL,
    LOCAL_UNASSIGNED_ACTOR_ID,
    get_actor_for_character,
    get_actor_roles,
    get_assignment_scope,
    get_episode_assignments,
    rename_character_assignments,
)


def test_local_assignment_overrides_global() -> None:
    data = {
        "global_map": {"Man 1": "actor-global"},
        "episode_actor_map": {"2": {"Man 1": "actor-local"}},
    }

    assert get_actor_for_character(data, "Man 1", "1") == "actor-global"
    assert get_actor_for_character(data, "Man 1", "2") == "actor-local"


def test_local_unassigned_overrides_global() -> None:
    data = {
        "global_map": {"Man 1": "actor-global"},
        "episode_actor_map": {
            "2": {"Man 1": LOCAL_UNASSIGNED_ACTOR_ID}
        },
    }

    assert get_actor_for_character(data, "Man 1", "2") is None
    assert get_assignment_scope(data, "Man 1", "2") == ASSIGNMENT_SCOPE_EPISODE


def test_assignment_scope_defaults_to_global() -> None:
    data = {"global_map": {"Crowd": "actor-1"}, "episode_actor_map": {}}

    assert get_assignment_scope(data, "Crowd", "1") == ASSIGNMENT_SCOPE_GLOBAL

    get_episode_assignments(data, "1")["Crowd"] = "actor-2"

    assert get_assignment_scope(data, "Crowd", "1") == ASSIGNMENT_SCOPE_EPISODE


def test_actor_roles_include_episode_local_roles() -> None:
    data = {
        "global_map": {"Hero": "actor-1"},
        "episode_actor_map": {
            "1": {"Man 1": "actor-1"},
            "2": {"Crowd": "actor-2"},
        },
    }

    assert get_actor_roles(data, "actor-1") == ["Hero", "Man 1"]


def test_rename_character_assignments_renames_local_maps() -> None:
    data = {
        "global_map": {"Old": "actor-1"},
        "episode_actor_map": {"1": {"Old": "actor-2"}},
    }

    rename_character_assignments(data, "Old", "New")

    assert data["global_map"] == {"New": "actor-1"}
    assert data["episode_actor_map"]["1"] == {"New": "actor-2"}
