"""Import and export actor assignment transfer files."""

import json
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from config.constants import APP_VERSION
from services.assignment_service import LOCAL_UNASSIGNED_ACTOR_ID


ASSIGNMENT_TRANSFER_FORMAT = "dubbing-manager.actor-assignments"
ASSIGNMENT_TRANSFER_VERSION = "1.0"


class AssignmentTransferService:
    """Service for portable actor-base and assignment files."""

    def build_export_payload(self, project_data: Dict[str, Any]) -> Dict[str, Any]:
        """Build a portable assignment payload."""
        return {
            "format": ASSIGNMENT_TRANSFER_FORMAT,
            "version": ASSIGNMENT_TRANSFER_VERSION,
            "app_version": APP_VERSION,
            "exported_at": datetime.now().isoformat(),
            "project_name": project_data.get("project_name", ""),
            "actors": deepcopy(project_data.get("actors", {})),
            "global_map": deepcopy(project_data.get("global_map", {})),
            "episode_actor_map": deepcopy(
                project_data.get("episode_actor_map", {})
            ),
        }

    def save_export(self, project_data: Dict[str, Any], path: str) -> None:
        """Save assignment payload to disk."""
        payload = self.build_export_payload(project_data)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)

    def load_export(self, path: str) -> Dict[str, Any]:
        """Load and validate an assignment payload."""
        with open(path, "r", encoding="utf-8") as f:
            payload = json.load(f)
        self._validate_payload(payload)
        return payload

    def import_from_file(
        self,
        project_data: Dict[str, Any],
        path: str
    ) -> Dict[str, int]:
        """Import assignment payload from disk into a project."""
        return self.import_payload(project_data, self.load_export(path))

    def import_payload(
        self,
        project_data: Dict[str, Any],
        payload: Dict[str, Any]
    ) -> Dict[str, int]:
        """Merge assignment payload into a project."""
        self._validate_payload(payload)

        actors = project_data.setdefault("actors", {})
        global_map = project_data.setdefault("global_map", {})
        episode_actor_map = project_data.setdefault("episode_actor_map", {})
        existing_episodes = {str(ep) for ep in project_data.get("episodes", {})}

        imported_actors = payload.get("actors", {})
        actor_id_map: Dict[str, Optional[str]] = {
            LOCAL_UNASSIGNED_ACTOR_ID: LOCAL_UNASSIGNED_ACTOR_ID
        }
        stats = {
            "actors_added": 0,
            "actors_matched": 0,
            "global_assignments": 0,
            "episode_assignments": 0,
            "skipped_episode_assignments": 0,
        }

        for imported_id, actor_data in imported_actors.items():
            if not isinstance(actor_data, dict):
                continue

            actor_name = str(actor_data.get("name", "")).strip()
            if not actor_name:
                continue

            existing_id = self._find_actor_by_name(actors, actor_name)
            if existing_id:
                actor_id_map[str(imported_id)] = existing_id
                stats["actors_matched"] += 1
                continue

            new_id = self._available_actor_id(actors, str(imported_id))
            actors[new_id] = {
                "name": actor_name,
                "color": actor_data.get("color", "#FFFFFF"),
            }
            actor_id_map[str(imported_id)] = new_id
            stats["actors_added"] += 1

        for char_name, imported_actor_id in payload.get("global_map", {}).items():
            mapped_id = actor_id_map.get(str(imported_actor_id))
            if not mapped_id or mapped_id == LOCAL_UNASSIGNED_ACTOR_ID:
                continue
            global_map[str(char_name)] = mapped_id
            stats["global_assignments"] += 1

        for ep_num, assignments in payload.get("episode_actor_map", {}).items():
            ep_key = str(ep_num)
            if existing_episodes and ep_key not in existing_episodes:
                stats["skipped_episode_assignments"] += len(assignments)
                continue
            if not isinstance(assignments, dict):
                continue

            target_map = episode_actor_map.setdefault(ep_key, {})
            for char_name, imported_actor_id in assignments.items():
                mapped_id = actor_id_map.get(str(imported_actor_id))
                if not mapped_id:
                    continue
                target_map[str(char_name)] = mapped_id
                stats["episode_assignments"] += 1

        return stats

    def _validate_payload(self, payload: Dict[str, Any]) -> None:
        """Validate assignment transfer payload shape."""
        if not isinstance(payload, dict):
            raise ValueError("Файл распределения должен быть JSON-объектом.")

        if payload.get("format") != ASSIGNMENT_TRANSFER_FORMAT:
            raise ValueError("Это не файл распределения актёров Dubbing Manager.")

        for key in ("actors", "global_map", "episode_actor_map"):
            if key not in payload or not isinstance(payload[key], dict):
                raise ValueError(f"В файле распределения нет секции {key}.")

    def _find_actor_by_name(
        self,
        actors: Dict[str, Any],
        actor_name: str
    ) -> Optional[str]:
        """Find an actor id by display name."""
        normalized = actor_name.casefold()
        for actor_id, actor_data in actors.items():
            if not isinstance(actor_data, dict):
                continue
            if str(actor_data.get("name", "")).strip().casefold() == normalized:
                return str(actor_id)
        return None

    def _available_actor_id(self, actors: Dict[str, Any], preferred_id: str) -> str:
        """Return a free actor id, preferring the imported id."""
        if preferred_id and preferred_id not in actors:
            return preferred_id

        stem = Path(preferred_id or "actor").stem or "actor"
        index = 1
        while True:
            candidate = f"{stem}_imported_{index}"
            if candidate not in actors:
                return candidate
            index += 1
