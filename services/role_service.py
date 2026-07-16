"""Project role collection helpers shared by desktop frontends."""

from typing import Any, Callable, Dict, List, Optional, Set

from services.assignment_service import get_actor_ids_for_character
from services.export_service import ExportService
from utils.helpers import natural_sort_key

ROLE_NO_ACTOR = "__no_actor__"
ROLE_MIXED_ACTOR = "__mixed_actor__"


def collect_project_roles(
    project_data: Dict[str, Any],
    get_episode_lines: Optional[Callable[[str], List[Dict[str, Any]]]] = None,
) -> List[Dict[str, Any]]:
    roles: Set[str] = set()
    episodes_by_role: Dict[str, Set[str]] = {}
    global_map = project_data.get("global_map", {})
    if isinstance(global_map, dict):
        roles.update(str(role) for role in global_map)
    episode_maps = project_data.get("episode_actor_map", {})
    if isinstance(episode_maps, dict):
        for episode, assignment_map in episode_maps.items():
            if not isinstance(assignment_map, dict):
                continue
            for role in assignment_map:
                role = str(role)
                roles.add(role)
                episodes_by_role.setdefault(role, set()).add(str(episode))
    for episode in project_data.get("episodes", {}):
        lines = get_episode_lines(str(episode)) if get_episode_lines else []
        for line in lines:
            role = str(line.get("char", "")).strip()
            if role:
                roles.add(role)
                episodes_by_role.setdefault(role, set()).add(str(episode))

    actors = project_data.get("actors", {})
    result = []
    for role in sorted(roles, key=str.casefold):
        actor_ids = {
            actor_id
            for episode in episodes_by_role.get(role, set())
            for actor_id in get_actor_ids_for_character(
                project_data, role, episode
            )
        }
        if not actor_ids:
            actor_ids.update(get_actor_ids_for_character(project_data, role))
        actor_id = next(iter(actor_ids)) if len(actor_ids) == 1 else ROLE_MIXED_ACTOR
        if actor_id == ROLE_MIXED_ACTOR:
            actor_name = " / ".join(
                str(actors.get(item, {}).get("name") or item)
                for item in sorted(actor_ids)
            ) or "Разные"
        elif not actor_id:
            actor_name = "Без актёра"
        else:
            actor_name = actors.get(actor_id, {}).get("name", actor_id)
        result.append({
            "name": role,
            "actor_id": actor_id,
            "actor_name": actor_name,
            "episodes": sorted(
                episodes_by_role.get(role, set()),
                key=natural_sort_key,
            ),
        })
    return result


def actor_role_stats(
    project_data: Dict[str, Any],
    actor_id: str,
    get_episode_lines: Callable[[str], List[Dict[str, Any]]],
) -> List[Dict[str, Any]]:
    """Return merged-replica ring and word totals for one actor's roles."""
    stats: Dict[str, Dict[str, Any]] = {}
    export_service = ExportService(project_data)
    for episode in project_data.get("episodes", {}):
        lines = get_episode_lines(str(episode))
        for line in export_service.process_merge_logic(
            lines,
            project_data.get("replica_merge_config", {}),
        ):
            role = str(line.get("char", ""))
            if actor_id not in get_actor_ids_for_character(
                project_data,
                role,
                str(episode),
            ):
                continue
            row = stats.setdefault(
                role,
                {"name": role, "rings": 0, "words": 0},
            )
            row["rings"] += 1
            row["words"] += len(str(line.get("text", "")).split())
    return sorted(stats.values(), key=lambda row: row["name"].casefold())
