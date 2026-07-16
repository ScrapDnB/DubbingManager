"""Undoable command objects."""

from abc import ABC, abstractmethod
from copy import deepcopy
from datetime import datetime
from typing import Any, Dict, List, Optional, Callable
import logging
import os

logger = logging.getLogger(__name__)


class Command(ABC):
    """Undoable command for ."""

    @abstractmethod
    def execute(self) -> None:
        """Execute."""
        pass

    @abstractmethod
    def undo(self) -> None:
        """Undo."""
        pass

    @abstractmethod
    def get_description(self) -> str:
        """Return description."""
        pass


class AddActorCommand(Command):
    """Undoable command for add actor."""

    def __init__(
        self,
        actors: Dict[str, dict],
        actor_id: str,
        name: str,
        color: str,
        gender: str = ""
    ):
        self.actors = actors
        self.actor_id = actor_id
        self.name = name
        self.color = color
        self.gender = gender
        self._old_data: Optional[dict] = None

    def execute(self) -> None:
        self._old_data = self.actors.get(self.actor_id)
        self.actors[self.actor_id] = {
            "name": self.name,
            "color": self.color,
            "gender": self.gender,
            "roles": []
        }
        logger.debug(f"AddActorCommand executed: {self.name}")

    def undo(self) -> None:
        if self._old_data is not None:
            self.actors[self.actor_id] = self._old_data
        else:
            self.actors.pop(self.actor_id, None)
        logger.debug(f"AddActorCommand undone: {self.name}")

    def get_description(self) -> str:
        return f"Добавлен актёр: {self.name}"


class DeleteActorCommand(Command):
    """Undoable command for delete actor."""

    def __init__(
        self,
        actors: Dict[str, dict],
        global_map: Dict[str, Any],
        actor_id: str,
        extra_maps: Optional[List[Dict[str, Any]]] = None
    ):
        self.actors = actors
        self.global_map = global_map
        self.extra_maps = extra_maps or []
        self.actor_id = actor_id
        self._deleted_data: Optional[dict] = None
        self._changed_mappings: List[tuple] = []
        self._changed_extra_mappings: List[tuple] = []

    def execute(self) -> None:
        self._deleted_data = self.actors.get(self.actor_id)

        self._changed_mappings = self._remove_actor_from_map(self.global_map)
        self._changed_extra_mappings = []
        for map_index, assignment_map in enumerate(self.extra_maps):
            for char, previous in self._remove_actor_from_map(assignment_map):
                self._changed_extra_mappings.append((map_index, char, previous))

        # Remove actor
        if self.actor_id in self.actors:
            del self.actors[self.actor_id]

        logger.debug(f"DeleteActorCommand executed: {self.actor_id}")

    def undo(self) -> None:
        if self._deleted_data:
            self.actors[self.actor_id] = self._deleted_data
        
        for char, value in self._changed_mappings:
            self.global_map[char] = value

        for map_index, char, value in self._changed_extra_mappings:
            if map_index < len(self.extra_maps):
                self.extra_maps[map_index][char] = value
        
        logger.debug(f"DeleteActorCommand undone: {self.actor_id}")

    def get_description(self) -> str:
        actor_name = self._deleted_data["name"] if self._deleted_data else "Неизвестный"
        return f"Удалён актёр: {actor_name}"

    def _remove_actor_from_map(self, assignment_map: Dict[str, Any]) -> List[tuple]:
        changed: List[tuple] = []
        for character, value in list(assignment_map.items()):
            ids = value if isinstance(value, list) else [value]
            remaining = [item for item in ids if item != self.actor_id]
            if len(remaining) == len(ids):
                continue
            changed.append((character, deepcopy(value)))
            if not remaining:
                del assignment_map[character]
            else:
                assignment_map[character] = (
                    remaining[0] if len(remaining) == 1 else remaining
                )
        return changed


class RenameActorCommand(Command):
    """Undoable command for rename actor."""

    def __init__(
        self,
        actors: Dict[str, dict],
        actor_id: str,
        new_name: str
    ):
        self.actors = actors
        self.actor_id = actor_id
        self.new_name = new_name
        self._old_name: Optional[str] = None

    def execute(self) -> None:
        if self.actor_id in self.actors:
            self._old_name = self.actors[self.actor_id]["name"]
            self.actors[self.actor_id]["name"] = self.new_name
        logger.debug(f"RenameActorCommand executed: {self.actor_id} -> {self.new_name}")

    def undo(self) -> None:
        if self.actor_id in self.actors and self._old_name:
            self.actors[self.actor_id]["name"] = self._old_name
        logger.debug(f"RenameActorCommand undone: {self.actor_id} -> {self._old_name}")

    def get_description(self) -> str:
        return f"Переименован актёр: {self._old_name} -> {self.new_name}"


class UpdateActorColorCommand(Command):
    """Undoable command for update actor color."""

    def __init__(
        self,
        actors: Dict[str, dict],
        actor_id: str,
        new_color: str
    ):
        self.actors = actors
        self.actor_id = actor_id
        self.new_color = new_color
        self._old_color: Optional[str] = None

    def execute(self) -> None:
        if self.actor_id in self.actors:
            self._old_color = self.actors[self.actor_id]["color"]
            self.actors[self.actor_id]["color"] = self.new_color
        logger.debug(f"UpdateActorColorCommand executed: {self.actor_id} -> {self.new_color}")

    def undo(self) -> None:
        if self.actor_id in self.actors and self._old_color:
            self.actors[self.actor_id]["color"] = self._old_color
        logger.debug(f"UpdateActorColorCommand undone: {self.actor_id} -> {self._old_color}")

    def get_description(self) -> str:
        return f"Изменён цвет актёра: {self._old_color} -> {self.new_color}"


class UpdateActorGenderCommand(Command):
    """Undoable command for update actor gender."""

    def __init__(
        self,
        actors: Dict[str, dict],
        actor_id: str,
        new_gender: str
    ):
        self.actors = actors
        self.actor_id = actor_id
        self.new_gender = new_gender
        self._old_gender: Optional[str] = None

    def execute(self) -> None:
        if self.actor_id in self.actors:
            self._old_gender = self.actors[self.actor_id].get("gender", "")
            self.actors[self.actor_id]["gender"] = self.new_gender
        logger.debug(f"UpdateActorGenderCommand executed: {self.actor_id} -> {self.new_gender}")

    def undo(self) -> None:
        if self.actor_id in self.actors and self._old_gender is not None:
            self.actors[self.actor_id]["gender"] = self._old_gender
        logger.debug(f"UpdateActorGenderCommand undone: {self.actor_id} -> {self._old_gender}")

    def get_description(self) -> str:
        return f"Изменён пол актёра: {self._old_gender} -> {self.new_gender}"


class UpdateExportConfigCommand(Command):
    """Undoable replacement of the project export configuration."""

    def __init__(self, data: Dict[str, Any], new_config: Dict[str, Any]):
        self.data = data
        self.new_config = deepcopy(new_config)
        self._old_config: Optional[Dict[str, Any]] = None

    def execute(self) -> None:
        if self._old_config is None:
            self._old_config = deepcopy(self.data.get("export_config", {}))
        self.data["export_config"] = deepcopy(self.new_config)

    def undo(self) -> None:
        self.data["export_config"] = deepcopy(self._old_config or {})

    def get_description(self) -> str:
        return "Изменены настройки монтажного листа"


class UpdateWorkingTextLineCommand(Command):
    """Undoable edit of one line in an embedded episode working text."""

    def __init__(
        self,
        working_texts: Dict[str, Any],
        episode: str,
        line_id: Any,
        new_text: str,
    ) -> None:
        self.working_texts = working_texts
        self.episode = str(episode)
        self.line_id = line_id
        self.new_text = new_text
        self._old_text: Optional[str] = None
        self._old_dirty: Any = None
        self._had_dirty = False
        self._old_modified_at: Any = None
        self._had_modified_at = False
        self._captured = False

    def _payload(self) -> Optional[Dict[str, Any]]:
        payload = self.working_texts.get(self.episode)
        return payload if isinstance(payload, dict) else None

    def _line(self) -> Optional[Dict[str, Any]]:
        payload = self._payload()
        if not payload:
            return None
        line_id = str(self.line_id)
        for index, line in enumerate(payload.get("lines", [])):
            if str(line.get("id")) == line_id or str(index) == line_id:
                return line
        return None

    def execute(self) -> None:
        payload = self._payload()
        line = self._line()
        if payload is None or line is None:
            return
        if not self._captured:
            self._old_text = str(line.get("text", ""))
            self._had_dirty = "dirty" in line
            self._old_dirty = line.get("dirty")
            self._had_modified_at = "modified_at" in payload
            self._old_modified_at = payload.get("modified_at")
            self._captured = True
        line["text"] = self.new_text
        line["dirty"] = True
        payload["modified_at"] = datetime.now().isoformat()

    def undo(self) -> None:
        payload = self._payload()
        line = self._line()
        if payload is None or line is None or not self._captured:
            return
        line["text"] = self._old_text or ""
        if self._had_dirty:
            line["dirty"] = self._old_dirty
        else:
            line.pop("dirty", None)
        if self._had_modified_at:
            payload["modified_at"] = self._old_modified_at
        else:
            payload.pop("modified_at", None)

    def get_description(self) -> str:
        return f"Изменён текст реплики в серии {self.episode}"


class AssignActorToCharacterCommand(Command):
    """Undoable command for assign actor to character."""

    def __init__(
        self,
        global_map: Dict[str, Any],
        character_name: str,
        actor_id: Any
    ):
        self.global_map = global_map
        self.character_name = character_name
        self.actor_id = actor_id
        self._old_actor_id: Any = None

    def execute(self) -> None:
        self._old_actor_id = deepcopy(self.global_map.get(self.character_name))
        if self.actor_id:
            self.global_map[self.character_name] = self.actor_id
        elif self.character_name in self.global_map:
            del self.global_map[self.character_name]
        logger.debug(f"AssignActorToCharacterCommand executed: {self.character_name} -> {self.actor_id}")

    def undo(self) -> None:
        if self._old_actor_id is not None:
            self.global_map[self.character_name] = deepcopy(self._old_actor_id)
        elif self.character_name in self.global_map:
            del self.global_map[self.character_name]
        logger.debug(f"AssignActorToCharacterCommand undone: {self.character_name}")

    def get_description(self) -> str:
        return f"Назначен актёр для: {self.character_name}"


class AddActorToCharacterCommand(Command):
    """Append an actor to a role while preserving its existing assignment."""

    def __init__(
        self,
        assignment_map: Dict[str, Any],
        character_name: str,
        actor_id: str,
        unassigned_marker: str = "__local_unassigned__",
    ) -> None:
        self.assignment_map = assignment_map
        self.character_name = character_name
        self.actor_id = actor_id
        self.unassigned_marker = unassigned_marker
        self._had_previous = False
        self._previous: Any = None

    def execute(self) -> None:
        self._had_previous = self.character_name in self.assignment_map
        self._previous = deepcopy(self.assignment_map.get(self.character_name))
        if self._previous in (None, self.unassigned_marker, ""):
            self.assignment_map[self.character_name] = self.actor_id
            return
        current = self._previous if isinstance(self._previous, list) else [self._previous]
        current = [str(value) for value in current if value]
        if self.actor_id not in current:
            current.append(self.actor_id)
        self.assignment_map[self.character_name] = (
            current[0] if len(current) == 1 else current
        )

    def undo(self) -> None:
        if self._had_previous:
            self.assignment_map[self.character_name] = deepcopy(self._previous)
        else:
            self.assignment_map.pop(self.character_name, None)

    def get_description(self) -> str:
        return f"Добавлен актёр для: {self.character_name}"


class AssignProjectRolesCommand(Command):
    """Assign roles globally and clear their episode-local overrides."""

    def __init__(
        self,
        data: Dict[str, Any],
        roles: List[str],
        actor_id: Optional[str],
    ) -> None:
        self.data = data
        self.roles = [str(role) for role in roles if str(role)]
        self.actor_id = actor_id
        self._old_global_map: Optional[Dict[str, Any]] = None
        self._old_episode_maps: Optional[Dict[str, Any]] = None

    def execute(self) -> None:
        if self._old_global_map is None:
            self._old_global_map = deepcopy(self.data.get("global_map", {}))
            self._old_episode_maps = deepcopy(
                self.data.get("episode_actor_map", {})
            )
        global_map = self.data.setdefault("global_map", {})
        for role in self.roles:
            if self.actor_id:
                global_map[role] = self.actor_id
            else:
                global_map.pop(role, None)
        for assignment_map in self.data.get("episode_actor_map", {}).values():
            if isinstance(assignment_map, dict):
                for role in self.roles:
                    assignment_map.pop(role, None)

    def undo(self) -> None:
        self.data["global_map"] = deepcopy(self._old_global_map or {})
        self.data["episode_actor_map"] = deepcopy(
            self._old_episode_maps or {}
        )

    def get_description(self) -> str:
        return f"Назначены роли: {len(self.roles)}"


class RenameCharacterCommand(Command):
    """Undoable command for rename character."""

    def __init__(
        self,
        global_map: Dict[str, str],
        loaded_episodes: Dict[str, List[Dict[str, Any]]],
        current_ep_stats: List[Dict[str, Any]],
        episode: str,
        old_name: str,
        new_name: str,
        rename_callback: Optional[Callable[[str, str], None]] = None
    ):
        self.global_map = global_map
        self.loaded_episodes = loaded_episodes
        self.current_ep_stats = current_ep_stats
        self.episode = episode
        self.old_name = old_name
        self.new_name = new_name
        self.rename_callback = rename_callback

    def execute(self) -> None:
        self._update_names(self.old_name, self.new_name)
        logger.debug(f"RenameCharacterCommand executed: {self.old_name} -> {self.new_name}")

    def undo(self) -> None:
        self._update_names(self.new_name, self.old_name)
        logger.debug(f"RenameCharacterCommand undone: {self.new_name} -> {self.old_name}")

    def _update_names(self, from_name: str, to_name: str) -> None:
        # Update global_map
        if from_name in self.global_map:
            actor_id = self.global_map[from_name]
            del self.global_map[from_name]
            self.global_map[to_name] = actor_id

        if self.episode in self.loaded_episodes:
            for line in self.loaded_episodes[self.episode]:
                if line.get('char') == from_name:
                    line['char'] = to_name

        for stat in self.current_ep_stats:
            if stat.get("name") == from_name:
                stat["name"] = to_name
                break

        if self.rename_callback:
            self.rename_callback(from_name, to_name)

    def get_description(self) -> str:
        return f"Переименован персонаж: {self.old_name} -> {self.new_name}"


class AddEpisodeCommand(Command):
    """Undoable command for add episode."""

    def __init__(
        self,
        episodes: Dict[str, str],
        episode_num: str,
        path: str
    ):
        self.episodes = episodes
        self.episode_num = episode_num
        self.path = path
        self._old_path: Optional[str] = None

    def execute(self) -> None:
        self._old_path = self.episodes.get(self.episode_num)
        self.episodes[self.episode_num] = self.path
        logger.debug(f"AddEpisodeCommand executed: {self.episode_num} -> {self.path}")

    def undo(self) -> None:
        if self._old_path is not None:
            self.episodes[self.episode_num] = self._old_path
        else:
            self.episodes.pop(self.episode_num, None)
        logger.debug(f"AddEpisodeCommand undone: {self.episode_num}")

    def get_description(self) -> str:
        return f"Добавлена серия: {self.episode_num}"


class RenameEpisodeCommand(Command):
    """Undoable command for rename episode."""

    def __init__(
        self,
        episodes: Dict[str, str],
        old_name: str,
        new_name: str,
        episode_actor_map: Optional[Dict[str, Dict[str, str]]] = None,
        video_paths: Optional[Dict[str, str]] = None,
        loaded_episodes: Optional[Dict[str, List[Dict[str, Any]]]] = None,
        episode_texts: Optional[Dict[str, str]] = None,
        episode_working_texts: Optional[Dict[str, Dict[str, Any]]] = None,
        episode_order: Optional[List[str]] = None
    ):
        self.episodes = episodes
        self.old_name = old_name
        self.new_name = new_name
        self.episode_actor_map = episode_actor_map
        self.video_paths = video_paths
        self.loaded_episodes = loaded_episodes
        self.episode_texts = episode_texts
        self.episode_working_texts = episode_working_texts
        self.episode_order = episode_order
        self._old_data: Optional[str] = None

    def execute(self) -> None:
        self._old_data = self.episodes.get(self.old_name)
        if self._old_data:
            del self.episodes[self.old_name]
            self.episodes[self.new_name] = self._old_data
        self._rename_related(self.old_name, self.new_name)
        logger.debug(f"RenameEpisodeCommand executed: {self.old_name} -> {self.new_name}")

    def undo(self) -> None:
        if self._old_data:
            del self.episodes[self.new_name]
            self.episodes[self.old_name] = self._old_data
        self._rename_related(self.new_name, self.old_name)
        logger.debug(f"RenameEpisodeCommand undone: {self.new_name} -> {self.old_name}")

    def _rename_related(self, from_name: str, to_name: str) -> None:
        related_maps = [
            self.episode_actor_map,
            self.video_paths,
            self.loaded_episodes,
            self.episode_texts,
            self.episode_working_texts,
        ]
        for mapping in related_maps:
            if mapping is not None and from_name in mapping:
                mapping[to_name] = mapping.pop(from_name)
        if self.episode_order is not None:
            self.episode_order[:] = [
                to_name if item == from_name else item
                for item in self.episode_order
            ]

    def get_description(self) -> str:
        return f"Переименована серия: {self.old_name} -> {self.new_name}"


class DeleteEpisodeCommand(Command):
    """Undoable command for delete episode."""

    def __init__(
        self,
        episodes: Dict[str, str],
        video_paths: Dict[str, str],
        loaded_episodes: Dict[str, List[Dict[str, Any]]],
        episode_num: str,
        episode_actor_map: Optional[Dict[str, Dict[str, str]]] = None,
        episode_texts: Optional[Dict[str, str]] = None,
        episode_working_texts: Optional[Dict[str, Dict[str, Any]]] = None,
        episode_order: Optional[List[str]] = None
    ):
        self.episodes = episodes
        self.video_paths = video_paths
        self.loaded_episodes = loaded_episodes
        self.episode_actor_map = episode_actor_map
        self.episode_texts = episode_texts
        self.episode_working_texts = episode_working_texts
        self.episode_order = episode_order
        self.episode_num = episode_num
        self._deleted_episode: Optional[str] = None
        self._deleted_video: Optional[str] = None
        self._deleted_loaded_data: Optional[List[Dict[str, Any]]] = None
        self._deleted_actor_map: Optional[Dict[str, str]] = None
        self._deleted_text: Optional[str] = None
        self._deleted_working_text: Optional[Dict[str, Any]] = None
        self._old_order: Optional[List[str]] = None

    def execute(self) -> None:
        self._deleted_episode = self.episodes.get(self.episode_num)
        self._deleted_video = self.video_paths.get(self.episode_num)
        self._deleted_loaded_data = self.loaded_episodes.get(self.episode_num)
        self._deleted_text = (
            self.episode_texts.get(self.episode_num)
            if self.episode_texts
            else None
        )
        self._deleted_working_text = (
            self.episode_working_texts.get(self.episode_num)
            if self.episode_working_texts
            else None
        )
        self._deleted_actor_map = (
            self.episode_actor_map.get(self.episode_num)
            if self.episode_actor_map
            else None
        )
        self._old_order = list(self.episode_order) if self.episode_order is not None else None

        self.episodes.pop(self.episode_num, None)
        self.video_paths.pop(self.episode_num, None)
        self.loaded_episodes.pop(self.episode_num, None)
        if self.episode_texts:
            self.episode_texts.pop(self.episode_num, None)
        if self.episode_working_texts:
            self.episode_working_texts.pop(self.episode_num, None)
        if self.episode_actor_map:
            self.episode_actor_map.pop(self.episode_num, None)
        if self.episode_order is not None:
            self.episode_order[:] = [
                item for item in self.episode_order
                if item != self.episode_num
            ]

        logger.debug(f"DeleteEpisodeCommand executed: {self.episode_num}")

    def undo(self) -> None:
        if self._deleted_episode:
            self.episodes[self.episode_num] = self._deleted_episode
        if self._deleted_video:
            self.video_paths[self.episode_num] = self._deleted_video
        if self._deleted_loaded_data:
            self.loaded_episodes[self.episode_num] = self._deleted_loaded_data
        if self._deleted_text and self.episode_texts is not None:
            self.episode_texts[self.episode_num] = self._deleted_text
        if self._deleted_working_text and self.episode_working_texts is not None:
            self.episode_working_texts[self.episode_num] = self._deleted_working_text
        if self._deleted_actor_map and self.episode_actor_map is not None:
            self.episode_actor_map[self.episode_num] = self._deleted_actor_map
        if self._old_order is not None and self.episode_order is not None:
            self.episode_order[:] = self._old_order

        logger.debug(f"DeleteEpisodeCommand undone: {self.episode_num}")

    def get_description(self) -> str:
        return f"Удалена серия: {self.episode_num}"


class UpdateProjectNameCommand(Command):
    """Undoable command for update project name."""

    def __init__(
        self,
        data: Dict[str, Any],
        new_name: str
    ):
        self.data = data
        self.new_name = new_name
        self._old_name: Optional[str] = None

    def execute(self) -> None:
        self._old_name = self.data.get("project_name")
        self.data["project_name"] = self.new_name
        logger.debug(f"UpdateProjectNameCommand executed: {self._old_name} -> {self.new_name}")

    def undo(self) -> None:
        if self._old_name:
            self.data["project_name"] = self._old_name
        logger.debug(f"UpdateProjectNameCommand undone: {self.new_name} -> {self._old_name}")

    def get_description(self) -> str:
        return f"Переименован проект: {self._old_name} -> {self.new_name}"


class SetProjectFolderCommand(Command):
    """Undoable command for set project folder."""

    def __init__(
        self,
        data: Dict[str, Any],
        folder_path: Optional[str]
    ):
        self.data = data
        self.folder_path = folder_path
        self._old_folder: Optional[str] = None

    def execute(self) -> None:
        self._old_folder = self.data.get("project_folder")
        if self.folder_path:
            self.data["project_folder"] = self.folder_path
        elif "project_folder" in self.data:
            del self.data["project_folder"]
        logger.debug(f"SetProjectFolderCommand executed: {self.folder_path}")

    def undo(self) -> None:
        if self._old_folder:
            self.data["project_folder"] = self._old_folder
        elif "project_folder" in self.data:
            del self.data["project_folder"]
        logger.debug(f"SetProjectFolderCommand undone")

    def get_description(self) -> str:
        if self.folder_path:
            folder_name = os.path.basename(self.folder_path)
            return f"Установлена папка: {folder_name}"
        return "Папка проекта очищена"


class UpdateProjectFileStateCommand(Command):
    """Atomically replace selected top-level project file fields."""

    def __init__(
        self,
        data: Dict[str, Any],
        updates: Dict[str, Any],
        description: str,
    ) -> None:
        self.data = data
        self.updates = deepcopy(updates)
        self.description = description
        self._old_values: Dict[str, Any] = {}
        self._old_presence: Dict[str, bool] = {}
        self._captured = False

    def execute(self) -> None:
        if not self._captured:
            for key in self.updates:
                self._old_presence[key] = key in self.data
                if key in self.data:
                    self._old_values[key] = deepcopy(self.data[key])
            self._captured = True

        for key, value in self.updates.items():
            if value is None:
                self.data.pop(key, None)
            else:
                self.data[key] = deepcopy(value)

        logger.debug("UpdateProjectFileStateCommand executed: %s", self.description)

    def undo(self) -> None:
        for key in self.updates:
            if self._old_presence.get(key):
                self.data[key] = deepcopy(self._old_values[key])
            else:
                self.data.pop(key, None)

        logger.debug("UpdateProjectFileStateCommand undone: %s", self.description)

    def get_description(self) -> str:
        return self.description


class ReplaceMappingValueCommand(Command):
    """Undoable replacement of one value in a mapping."""

    def __init__(
        self,
        mapping: Dict[str, Any],
        key: str,
        new_value: Any,
        description: str,
    ) -> None:
        self.mapping = mapping
        self.key = str(key)
        self.new_value = deepcopy(new_value)
        self.description = description
        self._old_value: Any = None
        self._had_value = False
        self._captured = False

    def execute(self) -> None:
        if not self._captured:
            self._had_value = self.key in self.mapping
            if self._had_value:
                self._old_value = deepcopy(self.mapping[self.key])
            self._captured = True
        self.mapping[self.key] = deepcopy(self.new_value)

    def undo(self) -> None:
        if self._had_value:
            self.mapping[self.key] = deepcopy(self._old_value)
        else:
            self.mapping.pop(self.key, None)

    def get_description(self) -> str:
        return self.description


class UndoStack:
    """Undo Stack class."""

    def __init__(self, max_size: int = 100):
        self._undo_stack: List[Command] = []
        self._redo_stack: List[Command] = []
        self._max_size = max_size
        self._on_change_callbacks: List[Callable] = []

    def push(self, command: Command) -> None:
        """Push."""
        command.execute()
        self._undo_stack.append(command)

        while len(self._undo_stack) > self._max_size:
            old_command = self._undo_stack.pop(0)
            # Old commands were already applied, so only release their heavy references.
            self._cleanup_command(old_command)

        # A new command invalidates the redo history.
        self._redo_stack.clear()

        self._notify_change()
        logger.debug(f"Command pushed: {command.get_description()}")

    def _cleanup_command(self, command: Command) -> None:
        """Cleanup command."""
        # Commands may keep snapshots of large project data; clear them when they leave the stack.
        for attr_name in ['_old_data', '_deleted_data', '_removed_mappings', 
                          '_old_name', '_old_color', '_old_folder', '_old_actor_id',
                          '_old_values']:
            if hasattr(command, attr_name):
                setattr(command, attr_name, None)

    def undo(self) -> bool:
        """Undo."""
        if not self._undo_stack:
            logger.debug("Undo failed: stack is empty")
            return False

        command = self._undo_stack.pop()
        command.undo()
        self._redo_stack.append(command)
        
        self._notify_change()
        logger.debug(f"Undo performed: {command.get_description()}")
        return True

    def redo(self) -> bool:
        """Redo."""
        if not self._redo_stack:
            logger.debug("Redo failed: stack is empty")
            return False

        command = self._redo_stack.pop()
        command.execute()
        self._undo_stack.append(command)
        
        self._notify_change()
        logger.debug(f"Redo performed: {command.get_description()}")
        return True

    def can_undo(self) -> bool:
        """Can undo."""
        return len(self._undo_stack) > 0

    def can_redo(self) -> bool:
        """Can redo."""
        return len(self._redo_stack) > 0

    def clear(self) -> None:
        """Clear."""
        for command in self._undo_stack:
            self._cleanup_command(command)
        for command in self._redo_stack:
            self._cleanup_command(command)
            
        self._undo_stack.clear()
        self._redo_stack.clear()
        self._notify_change()
        logger.debug("UndoStack cleared")

    def on_change(self, callback: Callable) -> None:
        """Handle change."""
        self._on_change_callbacks.append(callback)

    def _notify_change(self) -> None:
        """Notify change."""
        for callback in self._on_change_callbacks:
            try:
                callback()
            except Exception as e:
                logger.error(f"UndoStack callback error: {e}")
