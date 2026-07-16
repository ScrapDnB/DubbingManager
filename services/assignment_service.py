"""Helpers for global and per-episode actor assignments."""

from typing import Any, Dict, List, Optional, Set


ASSIGNMENT_SCOPE_GLOBAL = "global"
ASSIGNMENT_SCOPE_EPISODE = "episode"
LOCAL_UNASSIGNED_ACTOR_ID = "__local_unassigned__"


def ensure_episode_actor_map(project_data: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """Return the per-episode assignment map, creating it when needed."""
    mapping = project_data.setdefault("episode_actor_map", {})
    if not isinstance(mapping, dict):
        project_data["episode_actor_map"] = {}
        mapping = project_data["episode_actor_map"]
    return mapping


def get_episode_assignments(
    project_data: Dict[str, Any],
    ep_num: Optional[str]
) -> Dict[str, Any]:
    """Return local assignments for an episode."""
    if ep_num is None:
        return {}
    episode_maps = ensure_episode_actor_map(project_data)
    mapping = episode_maps.setdefault(str(ep_num), {})
    if not isinstance(mapping, dict):
        episode_maps[str(ep_num)] = {}
        mapping = episode_maps[str(ep_num)]
    return mapping


def get_assignment_map(
    project_data: Dict[str, Any],
    scope: str,
    ep_num: Optional[str] = None
) -> Dict[str, Any]:
    """Return the mutable assignment map for a selected scope."""
    if scope == ASSIGNMENT_SCOPE_EPISODE:
        return get_episode_assignments(project_data, ep_num)
    mapping = project_data.setdefault("global_map", {})
    if not isinstance(mapping, dict):
        project_data["global_map"] = {}
        mapping = project_data["global_map"]
    return mapping


def actor_ids_from_assignment(value: Any) -> List[str]:
    """Normalize legacy single and new multiple actor assignments."""
    if value == LOCAL_UNASSIGNED_ACTOR_ID or value is None:
        return []
    raw_ids = value if isinstance(value, (list, tuple, set)) else [value]
    result: List[str] = []
    for actor_id in raw_ids:
        actor_id = str(actor_id or "").strip()
        if actor_id and actor_id != LOCAL_UNASSIGNED_ACTOR_ID and actor_id not in result:
            result.append(actor_id)
    return result


def get_actor_ids_for_character(
    project_data: Dict[str, Any],
    char_name: str,
    ep_num: Optional[str] = None
) -> List[str]:
    """Resolve every actor assigned to a character, preferring local overrides."""
    local = (
        project_data.get("episode_actor_map", {}).get(str(ep_num), {})
        if ep_num is not None
        else {}
    )
    if not isinstance(local, dict):
        local = {}
    if char_name in local:
        return actor_ids_from_assignment(local.get(char_name))
    return actor_ids_from_assignment(
        project_data.get("global_map", {}).get(char_name)
    )


def get_actor_for_character(
    project_data: Dict[str, Any],
    char_name: str,
    ep_num: Optional[str] = None
) -> Optional[str]:
    """Return the primary actor for legacy single-actor consumers."""
    actor_ids = get_actor_ids_for_character(project_data, char_name, ep_num)
    return actor_ids[0] if actor_ids else None


def get_assignment_scope(
    project_data: Dict[str, Any],
    char_name: str,
    ep_num: Optional[str]
) -> str:
    """Return whether a character currently uses a local or global assignment."""
    local = (
        project_data.get("episode_actor_map", {}).get(str(ep_num), {})
        if ep_num is not None
        else {}
    )
    if isinstance(local, dict) and char_name in local:
        return ASSIGNMENT_SCOPE_EPISODE
    return ASSIGNMENT_SCOPE_GLOBAL


def clear_episode_assignment(
    project_data: Dict[str, Any],
    char_name: str,
    ep_num: Optional[str]
) -> None:
    """Remove a local override for a character in an episode."""
    if ep_num is None:
        return
    get_episode_assignments(project_data, ep_num).pop(char_name, None)


def get_actor_roles(project_data: Dict[str, Any], actor_id: str) -> List[str]:
    """Return unique role names assigned to an actor globally or locally."""
    roles: Set[str] = set()

    for char_name, assignment in project_data.get("global_map", {}).items():
        if actor_id in actor_ids_from_assignment(assignment):
            roles.add(char_name)

    for episode_map in ensure_episode_actor_map(project_data).values():
        if not isinstance(episode_map, dict):
            continue
        for char_name, assignment in episode_map.items():
            if actor_id in actor_ids_from_assignment(assignment):
                roles.add(char_name)

    return sorted(roles, key=str.lower)


def rename_character_assignments(
    project_data: Dict[str, Any],
    old_name: str,
    new_name: str
) -> None:
    """Rename a character in all assignment maps."""
    global_map = get_assignment_map(project_data, ASSIGNMENT_SCOPE_GLOBAL)
    if old_name in global_map:
        global_map[new_name] = global_map.pop(old_name)

    for episode_map in ensure_episode_actor_map(project_data).values():
        if isinstance(episode_map, dict) and old_name in episode_map:
            episode_map[new_name] = episode_map.pop(old_name)


def remove_actor_assignments(
    project_data: Dict[str, Any],
    actor_id: str
) -> None:
    """Remove all assignments for an actor across global and local maps."""
    global_map = get_assignment_map(project_data, ASSIGNMENT_SCOPE_GLOBAL)
    for char_name, assignment in list(global_map.items()):
        remaining = [
            assigned for assigned in actor_ids_from_assignment(assignment)
            if assigned != actor_id
        ]
        if len(remaining) == len(actor_ids_from_assignment(assignment)):
            continue
        if not remaining:
            del global_map[char_name]
        else:
            global_map[char_name] = remaining[0] if len(remaining) == 1 else remaining

    for episode_map in ensure_episode_actor_map(project_data).values():
        if not isinstance(episode_map, dict):
            continue
        for char_name, assignment in list(episode_map.items()):
            previous = actor_ids_from_assignment(assignment)
            remaining = [assigned for assigned in previous if assigned != actor_id]
            if len(remaining) == len(previous):
                continue
            if not remaining:
                del episode_map[char_name]
            else:
                episode_map[char_name] = (
                    remaining[0] if len(remaining) == 1 else remaining
                )


def move_episode_assignments(
    project_data: Dict[str, Any],
    old_ep: str,
    new_ep: str
) -> None:
    """Move local assignments when an episode is renamed."""
    episode_maps = ensure_episode_actor_map(project_data)
    if old_ep in episode_maps:
        episode_maps[str(new_ep)] = episode_maps.pop(str(old_ep))


def delete_episode_assignments(project_data: Dict[str, Any], ep_num: str) -> None:
    """Delete local assignments for a removed episode."""
    ensure_episode_actor_map(project_data).pop(str(ep_num), None)
