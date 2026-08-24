"""QML backend for actors, characters, filters, and assignments."""

from datetime import datetime
import random
from typing import Any, Dict, Optional

from PySide6.QtCore import QObject, Property, Signal, Slot, Qt

from config.constants import MY_PALETTE
from core.commands import (
    AddActorCommand,
    AddActorToCharacterCommand,
    AssignActorToCharacterCommand,
    DeleteActorCommand,
    DeleteActorsCommand,
    RenameActorCommand,
    RenameCharacterCommand,
    UpdateCharacterProfileCommand,
    UpdateActorColorCommand,
    UpdateActorGenderCommand,
)
from services import (
    ASSIGNMENT_SCOPE_EPISODE,
    ASSIGNMENT_SCOPE_GLOBAL,
    CharacterStatsService,
    LOCAL_UNASSIGNED_ACTOR_ID,
    build_actor_roles_index,
    get_assignment_map,
    get_actor_for_character,
    get_actor_ids_for_character,
    get_actor_roles,
    rename_character_assignments,
)
from services.role_service import collect_project_roles
from utils.helpers import natural_sort_key
from ui.qml_backend.models import DictListModel
from ui.qml_backend.project_session import ProjectSession


def _format_time(seconds: Any) -> str:
    try:
        total = max(0, float(seconds))
    except (TypeError, ValueError):
        total = 0.0
    minutes = int(total // 60)
    return f"{minutes:02d}:{total - minutes * 60:05.2f}"


class CastingBridge(QObject):
    """Own the casting workspace consumed by the main QML window."""

    changed = Signal()
    actorFilterChanged = Signal()
    showUnassignedOnlyChanged = Signal()
    searchTextChanged = Signal()
    selectedCharacterChanged = Signal()
    selectedCharacterStatsChanged = Signal()
    statusRequested = Signal(str)
    errorRequested = Signal(str)
    actorCreated = Signal(str, str)
    projectDataChanged = Signal(str)

    def __init__(
        self,
        session: ProjectSession,
        episode_service,
        script_text_service,
        ui_state=None,
        parent: Optional[QObject] = None,
    ) -> None:
        super().__init__(parent)
        self._session = session
        self._episode_service = episode_service
        self._script_text_service = script_text_service
        self._ui_state = ui_state
        self._actor_filter = ""
        self._show_unassigned_only = False
        self._search_text = ""
        self._selected_character = ""
        self._selected_character_stats = "Выберите персонажа в таблице"
        self._episode_lines_cache: Dict[str, list[Dict[str, Any]]] = {}
        self._timeline_lines_cache: Dict[str, list[Dict[str, Any]]] = {}
        self._project_stats_cache: Dict[str, Dict[str, Any]] = {}
        self._timeline_sort_mode = "appearance"
        self._actor_sort_key, self._actor_sort_ascending = self._restore_sort(
            "tableSort/projectActors", {"name", "gender", "roleCount"}, "name"
        )
        self._character_sort_key, self._character_sort_ascending = (
            self._restore_sort(
                "tableSort/characters",
                {"character", "lines", "rings", "words", "scope", "actor"},
                "character",
            )
        )
        self._actors_model = DictListModel({
            "id": Qt.UserRole + 1, "name": Qt.UserRole + 2,
            "color": Qt.UserRole + 3, "roleCount": Qt.UserRole + 4,
            "gender": Qt.UserRole + 5,
        }, self)
        self._actor_filter_model = DictListModel({
            "id": Qt.UserRole + 1, "name": Qt.UserRole + 2,
        }, self)
        self._lines_model = DictListModel({
            "time": Qt.UserRole + 1, "character": Qt.UserRole + 2,
            "actor": Qt.UserRole + 3, "text": Qt.UserRole + 4,
            "color": Qt.UserRole + 5, "start": Qt.UserRole + 6,
            "end": Qt.UserRole + 7, "actorIds": Qt.UserRole + 8,
        }, self)
        self._timeline_model = DictListModel({
            "start": Qt.UserRole + 1, "end": Qt.UserRole + 2,
            "character": Qt.UserRole + 3, "actor": Qt.UserRole + 4,
            "actorId": Qt.UserRole + 5, "actorColor": Qt.UserRole + 6,
            "lane": Qt.UserRole + 7, "selected": Qt.UserRole + 8,
        }, self)
        self._timeline_actors_model = DictListModel({
            "id": Qt.UserRole + 1, "name": Qt.UserRole + 2,
            "actorColor": Qt.UserRole + 3, "lane": Qt.UserRole + 4,
        }, self)
        self._timeline_duration = 0.0
        self._characters_model = DictListModel({
            "character": Qt.UserRole + 1, "lines": Qt.UserRole + 2,
            "rings": Qt.UserRole + 3, "words": Qt.UserRole + 4,
            "scope": Qt.UserRole + 5, "actor": Qt.UserRole + 6,
            "color": Qt.UserRole + 7, "actorId": Qt.UserRole + 8,
            "scopeId": Qt.UserRole + 9, "actorIds": Qt.UserRole + 10,
            "actorEntries": Qt.UserRole + 11,
            "aliasesText": Qt.UserRole + 12,
        }, self)
        self._character_episode_stats_model = DictListModel({
            "episode": Qt.UserRole + 1, "lines": Qt.UserRole + 2,
            "rings": Qt.UserRole + 3, "words": Qt.UserRole + 4,
            "actor": Qt.UserRole + 5, "scope": Qt.UserRole + 6,
        }, self)
        self._session.currentEpisodeChanged.connect(self._episode_changed)
        self.refresh()

    @Property(str, notify=actorFilterChanged)
    def actorFilter(self) -> str:
        return self._actor_filter

    @Property(bool, notify=showUnassignedOnlyChanged)
    def showUnassignedOnly(self) -> bool:
        return self._show_unassigned_only

    @Property(str, notify=searchTextChanged)
    def searchText(self) -> str:
        return self._search_text

    @Property(str, notify=selectedCharacterChanged)
    def selectedCharacter(self) -> str:
        return self._selected_character

    @Property(str, notify=selectedCharacterStatsChanged)
    def selectedCharacterStats(self) -> str:
        return self._selected_character_stats

    @Property(list, constant=True)
    def actorPalette(self) -> list[str]:
        return list(MY_PALETTE)

    @Property(QObject, constant=True)
    def actorsModel(self) -> QObject:
        return self._actors_model

    @Property(QObject, constant=True)
    def actorFilterModel(self) -> QObject:
        return self._actor_filter_model

    @Property(QObject, constant=True)
    def linesModel(self) -> QObject:
        return self._lines_model

    @Property(QObject, constant=True)
    def timelineModel(self) -> QObject:
        return self._timeline_model

    @Property(QObject, constant=True)
    def timelineActorsModel(self) -> QObject:
        return self._timeline_actors_model

    @Property(float, notify=changed)
    def timelineDuration(self) -> float:
        return self._timeline_duration

    @Property(str, notify=changed)
    def timelineSortMode(self) -> str:
        return self._timeline_sort_mode

    @Property(QObject, constant=True)
    def charactersModel(self) -> QObject:
        return self._characters_model

    @Property(QObject, constant=True)
    def characterEpisodeStatsModel(self) -> QObject:
        return self._character_episode_stats_model

    @Property(str, notify=changed)
    def actorSortKey(self) -> str:
        return self._actor_sort_key

    @Property(bool, notify=changed)
    def actorSortAscending(self) -> bool:
        return self._actor_sort_ascending

    @Slot(str)
    def setActorSort(self, key: str) -> None:
        if key not in {"name", "gender", "roleCount"}:
            return
        if key == self._actor_sort_key:
            self._actor_sort_ascending = not self._actor_sort_ascending
        else:
            self._actor_sort_key = key
            self._actor_sort_ascending = True
        self._save_sort(
            "tableSort/projectActors",
            self._actor_sort_key,
            self._actor_sort_ascending,
        )
        self._refresh_actors()
        self.changed.emit()

    @Property(str, notify=changed)
    def characterSortKey(self) -> str:
        return self._character_sort_key

    @Property(bool, notify=changed)
    def characterSortAscending(self) -> bool:
        return self._character_sort_ascending

    @Slot(str)
    def setCharacterSort(self, key: str) -> None:
        if key not in {"character", "lines", "rings", "words", "scope", "actor"}:
            return
        if key == self._character_sort_key:
            self._character_sort_ascending = not self._character_sort_ascending
        else:
            self._character_sort_key = key
            self._character_sort_ascending = True
        self._save_sort(
            "tableSort/characters",
            self._character_sort_key,
            self._character_sort_ascending,
        )
        self._refresh_characters()
        self.changed.emit()

    @Slot(str)
    def setTimelineSortMode(self, mode: str) -> None:
        if mode not in {"appearance", "words", "lines", "name"}:
            mode = "appearance"
        if mode == self._timeline_sort_mode:
            return
        self._timeline_sort_mode = mode
        self._refresh_lines()
        self.changed.emit()

    def _restore_sort(
        self, state_key: str, allowed_keys: set[str], default_key: str
    ) -> tuple[str, bool]:
        if self._ui_state is None:
            return default_key, True
        stored = str(self._ui_state.stringValue(state_key, "") or "")
        key, separator, direction = stored.partition("|")
        if key not in allowed_keys or not separator:
            return default_key, True
        return key, direction != "desc"

    def _save_sort(self, state_key: str, key: str, ascending: bool) -> None:
        if self._ui_state is not None:
            self._ui_state.setStringValue(
                state_key, f"{key}|{'asc' if ascending else 'desc'}"
            )

    @Slot(str)
    def setActorFilter(self, actor_id: str) -> None:
        actor_id = actor_id or ""
        show_unassigned_only = actor_id == "__unassigned__"
        actor_id = "" if show_unassigned_only else actor_id
        if (
            actor_id == self._actor_filter
            and show_unassigned_only == self._show_unassigned_only
        ):
            return
        self._actor_filter = actor_id
        self._show_unassigned_only = show_unassigned_only
        self.actorFilterChanged.emit()
        self.showUnassignedOnlyChanged.emit()
        self._refresh_characters()

    @Slot(bool)
    def setShowUnassignedOnly(self, enabled: bool) -> None:
        if enabled == self._show_unassigned_only:
            return
        self._show_unassigned_only = enabled
        self.showUnassignedOnlyChanged.emit()
        self._refresh_characters()

    @Slot(str)
    def setSearchText(self, text: str) -> None:
        text = (text or "").strip()
        if text == self._search_text:
            return
        self._search_text = text
        self.searchTextChanged.emit()
        self._refresh_characters()

    @Slot(str)
    def selectCharacter(self, character: str) -> None:
        self._set_selected_character(character or "")

    @Slot(str)
    def addActor(self, name: str) -> None:
        self.addActorWithDetails(name, "", "")

    @Slot(str, str, str)
    def addActorWithDetails(self, name: str, color: str, gender: str) -> None:
        name = (name or "").strip()
        if not name:
            self.errorRequested.emit("Введите имя актёра")
            return
        if self._find_actor_by_name(name):
            self.errorRequested.emit("Актёр с таким именем уже есть в проекте")
            return
        actor_id = str(datetime.now().timestamp())
        actor_color = self._normalized_color(color) or self._next_actor_color()
        self._execute(AddActorCommand(
            self._session.data.setdefault("actors", {}), actor_id, name,
            actor_color, self._normalized_gender(gender),
        ), "actors")
        self.actorCreated.emit(name, self._normalized_gender(gender))
        self.statusRequested.emit(f"Добавлен актёр: {name}")

    @Slot(str)
    def deleteActor(self, actor_id: str) -> None:
        actors = self._session.data.get("actors", {})
        if actor_id not in actors:
            self.errorRequested.emit("Выберите актёра")
            return
        name = actors[actor_id].get("name", actor_id)
        extra_maps = [
            value for value in self._session.data.get(
                "episode_actor_map", {}
            ).values() if isinstance(value, dict)
        ]
        self._execute(DeleteActorCommand(
            actors, self._session.data.setdefault("global_map", {}),
            actor_id, extra_maps,
        ), "actors")
        if self._actor_filter == actor_id:
            self.setActorFilter("")
        self.statusRequested.emit(f"Удалён актёр: {name}")

    @Slot("QVariantList")
    def deleteActors(self, actor_ids: list) -> None:
        actors = self._session.data.get("actors", {})
        ids = list(dict.fromkeys(
            str(actor_id) for actor_id in actor_ids
            if str(actor_id) in actors
        ))
        if not ids:
            self.errorRequested.emit("Выберите хотя бы одного актёра")
            return
        extra_maps = [
            value for value in self._session.data.get(
                "episode_actor_map", {}
            ).values() if isinstance(value, dict)
        ]
        self._execute(DeleteActorsCommand(
            actors, self._session.data.setdefault("global_map", {}),
            ids, extra_maps,
        ), "actors")
        if self._actor_filter in ids:
            self.setActorFilter("")
        self.statusRequested.emit(f"Удалено актёров: {len(ids)}")

    @Slot("QVariantList", result="QVariantList")
    def actorRoleAssignments(self, actor_ids: list) -> list:
        """Return project role summaries for the delete confirmation."""
        actors = self._session.data.get("actors", {})
        rows = []
        for actor_id in dict.fromkeys(str(value) for value in actor_ids):
            actor = actors.get(actor_id)
            if not actor:
                continue
            roles = get_actor_roles(self._session.data, actor_id)
            if roles:
                rows.append({
                    "actorName": str(actor.get("name") or actor_id),
                    "rolesText": ", ".join(roles),
                })
        return rows

    @Slot(str, str)
    def renameActor(self, actor_id: str, name: str) -> None:
        actors = self._session.data.get("actors", {})
        name = (name or "").strip()
        if actor_id not in actors:
            self.errorRequested.emit("Выберите актёра")
            return
        if not name:
            self.errorRequested.emit("Введите имя актёра")
            return
        duplicate = self._find_actor_by_name(name)
        if duplicate and duplicate != actor_id:
            self.errorRequested.emit("Актёр с таким именем уже есть в проекте")
            return
        if name == actors[actor_id].get("name", ""):
            return
        self._execute(RenameActorCommand(actors, actor_id, name), "actors")
        self.statusRequested.emit(f"Актёр переименован: {name}")

    @Slot(str, str)
    def updateActorColor(self, actor_id: str, color: str) -> None:
        actors = self._session.data.get("actors", {})
        color = self._normalized_color(color)
        if actor_id not in actors:
            self.errorRequested.emit("Выберите актёра")
            return
        if not color:
            self.errorRequested.emit("Некорректный цвет актёра")
            return
        if actors[actor_id].get("color") == color:
            return
        self._execute(UpdateActorColorCommand(actors, actor_id, color), "actors")
        self.statusRequested.emit(
            f"Цвет актёра изменён: {actors[actor_id].get('name', actor_id)}"
        )

    @Slot(str, str)
    def updateActorGender(self, actor_id: str, gender: str) -> None:
        actors = self._session.data.get("actors", {})
        if actor_id not in actors:
            self.errorRequested.emit("Выберите актёра")
            return
        gender = self._normalized_gender(gender)
        if actors[actor_id].get("gender", "") == gender:
            return
        self._execute(UpdateActorGenderCommand(
            actors, actor_id, gender
        ), "actors")
        self.statusRequested.emit(
            f"Пол актёра изменён: {actors[actor_id].get('name', actor_id)}"
        )

    @Slot(str, str)
    def assignActor(self, character: str, actor_id: str) -> None:
        character = (character or "").strip()
        actor_id = actor_id or None
        if not character:
            return
        if actor_id and actor_id not in self._session.data.get("actors", {}):
            self.errorRequested.emit("Выберите актёра")
            return
        scope = self._scope(character)
        target = get_assignment_map(
            self._session.data, scope, self._session.current_episode
        )
        stored = (
            LOCAL_UNASSIGNED_ACTOR_ID
            if scope == ASSIGNMENT_SCOPE_EPISODE and actor_id is None
            else actor_id
        )
        if target.get(character) == stored:
            return
        self._execute(AssignActorToCharacterCommand(
            target, character, stored
        ), "assignments")
        actor_name = self._session.data.get("actors", {}).get(
            actor_id, {}
        ).get("name", "-") if actor_id else "-"
        self.statusRequested.emit(f"{character}: {actor_name}")

    @Slot(str, str)
    def addActorToCharacter(self, character: str, actor_id: str) -> None:
        """Add a second or subsequent actor without replacing the role cast."""
        character = (character or "").strip()
        actor_id = (actor_id or "").strip()
        actors = self._session.data.get("actors", {})
        if not character or actor_id not in actors:
            self.errorRequested.emit("Выберите актёра")
            return
        assigned = get_actor_ids_for_character(
            self._session.data, character, self._session.current_episode
        )
        if actor_id in assigned:
            self.errorRequested.emit("Этот актёр уже назначен на персонажа")
            return
        scope = self._scope(character)
        target = get_assignment_map(
            self._session.data, scope, self._session.current_episode
        )
        self._execute(AddActorToCharacterCommand(
            target, character, actor_id, LOCAL_UNASSIGNED_ACTOR_ID
        ), "assignments")
        self.statusRequested.emit(
            f"{character}: добавлен {actors[actor_id].get('name', actor_id)}"
        )

    @Slot(str, str)
    def removeActorFromCharacter(self, character: str, actor_id: str) -> None:
        """Remove one actor from a role while retaining the rest of its cast."""
        character = (character or "").strip()
        actor_id = (actor_id or "").strip()
        if not character or not actor_id:
            return

        assigned = get_actor_ids_for_character(
            self._session.data, character, self._session.current_episode
        )
        if actor_id not in assigned:
            return

        scope = self._scope(character)
        target = get_assignment_map(
            self._session.data, scope, self._session.current_episode
        )
        remaining = [assigned_id for assigned_id in assigned if assigned_id != actor_id]
        stored: Any
        if remaining:
            stored = remaining[0] if len(remaining) == 1 else remaining
        elif scope == ASSIGNMENT_SCOPE_EPISODE:
            stored = LOCAL_UNASSIGNED_ACTOR_ID
        else:
            stored = None

        self._execute(AssignActorToCharacterCommand(
            target, character, stored
        ), "assignments")
        actor_name = self._session.data.get("actors", {}).get(
            actor_id, {}
        ).get("name", actor_id)
        self.statusRequested.emit(f"{character}: убран {actor_name}")

    @Slot(str, str)
    def setAssignmentScope(self, character: str, scope: str) -> None:
        character = (character or "").strip()
        if scope not in {ASSIGNMENT_SCOPE_GLOBAL, ASSIGNMENT_SCOPE_EPISODE}:
            return
        if not character or not self._session.current_episode:
            return
        if scope == self._scope(character):
            return
        local_map = get_assignment_map(
            self._session.data, ASSIGNMENT_SCOPE_EPISODE,
            self._session.current_episode,
        )
        actor_ids = get_actor_ids_for_character(
            self._session.data, character, self._session.current_episode
        )
        stored = (
            (
                actor_ids[0] if len(actor_ids) == 1 else actor_ids
            ) if actor_ids else LOCAL_UNASSIGNED_ACTOR_ID
        ) if scope == ASSIGNMENT_SCOPE_EPISODE else None
        self._execute(AssignActorToCharacterCommand(
            local_map, character, stored
        ), "assignments")
        self.statusRequested.emit(
            f"{character}: {'Серия' if scope == ASSIGNMENT_SCOPE_EPISODE else 'Проект'}"
        )

    @Slot(str, str)
    def renameCharacter(self, old_name: str, new_name: str) -> None:
        self.updateCharacterProfile(
            old_name,
            new_name,
            self.characterAliases(old_name),
        )

    @Slot(str, result="QVariantList")
    def characterAliases(self, character: str) -> list[str]:
        values = self._session.data.get("character_aliases", {}).get(
            str(character or ""), []
        )
        return list(values) if isinstance(values, list) else []

    @Slot(str, str, "QVariantList")
    def updateCharacterProfile(
        self, old_name: str, new_name: str, aliases: list
    ) -> None:
        old_name, new_name = (old_name or "").strip(), (new_name or "").strip()
        episode = self._session.current_episode
        if not episode:
            self.errorRequested.emit("Нет выбранной серии")
            return
        if not old_name:
            self.errorRequested.emit("Выберите персонажа")
            return
        if not new_name:
            return
        current_names = {
            str(row["name"])
            for row in collect_project_roles(
                self._session.data,
                lambda ep: self._script_text_service.load_episode_lines(
                    self._session.data, ep
                ),
            )
        }
        if new_name != old_name and new_name in current_names:
            self.errorRequested.emit("Персонаж с таким именем уже есть в проекте")
            return
        normalized_aliases = []
        seen = set()
        for value in aliases:
            alias = " ".join(str(value or "").split())
            folded = alias.casefold()
            if not alias or folded in seen or folded == new_name.casefold():
                continue
            seen.add(folded)
            normalized_aliases.append(alias)
        alias_mapping = self._session.data.setdefault("character_aliases", {})
        occupied = {name.casefold() for name in current_names if name != old_name}
        for character, values in alias_mapping.items():
            if character == old_name or not isinstance(values, list):
                continue
            occupied.update(str(value).casefold() for value in values)
        conflict = next(
            (alias for alias in normalized_aliases if alias.casefold() in occupied),
            "",
        )
        if conflict:
            self.errorRequested.emit(
                f"Имя или алиас «{conflict}» уже используется другим персонажем"
            )
            return
        old_aliases = self.characterAliases(old_name)
        if new_name == old_name and normalized_aliases == old_aliases:
            return
        rename_command = None
        if new_name != old_name:
            rename_command = RenameCharacterCommand(
                self._session.data.setdefault("global_map", {}),
                self._session.data.setdefault("loaded_episodes", {}),
                self._characters_model.rows(), episode, old_name, new_name,
                lambda source, target: (
                    rename_character_assignments(
                        self._session.data, source, target
                    ),
                    self._script_text_service.rename_character(
                        self._session.data, source, target, episode
                    ),
                ),
            )
        command = UpdateCharacterProfileCommand(
            alias_mapping,
            old_name,
            new_name,
            normalized_aliases,
            rename_command,
        )
        self._execute(command, "working_text")
        if new_name != old_name:
            self._episode_service.invalidate_episode(episode)
        self._set_selected_character(new_name)
        self.statusRequested.emit(f"Карточка персонажа обновлена: {new_name}")

    def refresh(self, domain: str = "") -> None:
        self.invalidate_cache(domain)
        self._refresh_actors()
        self._refresh_lines()
        self._refresh_characters()
        self.changed.emit()

    def reset(self) -> None:
        self.invalidate_cache("project")
        self.resetFilters()
        self._set_selected_character("")
        self.refresh()

    @Slot()
    def resetFilters(self) -> None:
        self._actor_filter = ""
        self._show_unassigned_only = False
        self._search_text = ""
        self.actorFilterChanged.emit()
        self.showUnassignedOnlyChanged.emit()
        self.searchTextChanged.emit()
        self._refresh_characters()

    def _execute(self, command, domain: str) -> None:
        self._session.execute(command, domain)
        # AppBridge refreshes all models affected by this project mutation.
        # Refreshing here as well rebuilt the large casting and timeline models twice.
        self.projectDataChanged.emit(domain)

    def _refresh_actors(self) -> None:
        rows, filters = [], [
            {"id": "", "name": "Все актёры"},
            {"id": "__unassigned__", "name": "Без актёра"},
        ]
        actors = self._session.data.get("actors", {})
        roles_by_actor = build_actor_roles_index(self._session.data)
        for actor_id, actor in actors.items():
            name = actor.get("name", actor_id)
            rows.append({
                "id": actor_id, "name": name,
                "color": actor.get("color", "#8FAADC"),
                "roleCount": len(roles_by_actor.get(actor_id, ())),
                "gender": actor.get("gender", ""),
            })
            filters.append({"id": actor_id, "name": name})
        rows.sort(
            key=self._actor_sort_value,
            reverse=not self._actor_sort_ascending,
        )
        filters[2:] = sorted(
            filters[2:], key=lambda row: str(row["name"]).casefold()
        )
        self._actors_model.set_rows(rows)
        self._actor_filter_model.set_rows(filters)
        if self._actor_filter and self._actor_filter not in self._session.data.get("actors", {}):
            self._actor_filter = ""
            self.actorFilterChanged.emit()

    def _actor_sort_value(self, row: Dict[str, Any]):
        value = row.get(self._actor_sort_key)
        if self._actor_sort_key == "roleCount":
            return int(value or 0), str(row.get("name", "")).casefold()
        return str(value or "").casefold(), str(row.get("name", "")).casefold()

    def _refresh_lines(self) -> None:
        episode = self._session.current_episode
        if not episode:
            self._lines_model.set_rows([])
            self._timeline_model.set_rows([])
            self._timeline_actors_model.set_rows([])
            self._timeline_duration = 0.0
            return
        actors = self._session.data.get("actors", {})
        rows = []
        timeline_rows = []
        timeline_actor_stats: Dict[str, Dict[str, Any]] = {}
        duration = 0.0
        for line in self._get_lines():
            character = str(line.get("char") or "")
            actor_ids = get_actor_ids_for_character(
                self._session.data, character, episode
            )
            actor = actors.get(actor_ids[0], {}) if actor_ids else {}
            start = max(0.0, float(line.get("s") or 0.0))
            end = max(start, float(line.get("e") or start))
            rows.append({
                "time": f"{_format_time(line.get('s'))} - {_format_time(line.get('e'))}",
                "character": character or "-",
                "actor": self._actor_names(actor_ids),
                "text": line.get("text", ""),
                "color": actor.get("color", "#4F81BD") if len(actor_ids) == 1 else "transparent",
                "start": start, "end": end, "actorIds": actor_ids,
            })

        for line in self._get_timeline_lines():
            character = str(line.get("char") or "")
            actor_ids = get_actor_ids_for_character(
                self._session.data, character, episode
            )
            start = max(0.0, float(line.get("s") or 0.0))
            end = max(start, float(line.get("e") or start))
            duration = max(duration, end)
            # A multiple cast produces one segment on each assigned actor's
            # lane; unassigned lines stay visible on a neutral lane.
            segment_actor_ids = actor_ids or [""]
            for actor_id in segment_actor_ids:
                timeline_actor = actors.get(actor_id, {})
                lane_key = actor_id or "__unassigned__"
                if lane_key not in timeline_actor_stats:
                    timeline_actor_stats[lane_key] = {
                        "id": actor_id,
                        "name": str(timeline_actor.get("name") or "Без актёра"),
                        "actorColor": str(timeline_actor.get("color") or "#9A9A9A"),
                        "firstAppearance": len(timeline_actor_stats),
                        "words": 0,
                        "lines": 0,
                    }
                timeline_actor_stats[lane_key]["lines"] += 1
                timeline_actor_stats[lane_key]["words"] += len(
                    str(line.get("text") or "").split()
                )
                timeline_rows.append({
                    "start": start, "end": end,
                    "character": character or "-",
                    "actor": str(timeline_actor.get("name") or "Без актёра"),
                    "actorId": actor_id,
                    "actorColor": str(timeline_actor.get("color") or "#9A9A9A"),
                    "_laneKey": lane_key,
                    "selected": character == self._selected_character,
                })
        timeline_actors = list(timeline_actor_stats.values())
        if self._timeline_sort_mode == "words":
            timeline_actors.sort(
                key=lambda item: (
                    -int(item["words"]), natural_sort_key(str(item["name"]))
                )
            )
        elif self._timeline_sort_mode == "lines":
            timeline_actors.sort(
                key=lambda item: (
                    -int(item["lines"]), natural_sort_key(str(item["name"]))
                )
            )
        elif self._timeline_sort_mode == "name":
            timeline_actors.sort(key=lambda item: natural_sort_key(str(item["name"])))
        else:
            timeline_actors.sort(key=lambda item: int(item["firstAppearance"]))
        lane_by_actor = {
            str(item["id"] or "__unassigned__"): lane
            for lane, item in enumerate(timeline_actors)
        }
        for lane, item in enumerate(timeline_actors):
            item["lane"] = lane
            item.pop("firstAppearance", None)
            item.pop("words", None)
            item.pop("lines", None)
        for item in timeline_rows:
            item["lane"] = lane_by_actor[str(item.pop("_laneKey"))]
        self._lines_model.set_rows(rows)
        self._timeline_model.set_rows(timeline_rows)
        self._timeline_actors_model.set_rows(timeline_actors)
        self._timeline_duration = duration

    def _refresh_characters(self) -> None:
        episode = self._session.current_episode
        if not episode:
            self._characters_model.set_rows([])
            self._set_selected_character("")
            return
        stats: Dict[str, Dict[str, Any]] = {}
        for line in self._get_lines():
            character = str(line.get("char") or "-")
            item = stats.setdefault(character, {
                "character": character, "lines": 0, "rings": 0, "words": 0,
            })
            item["lines"] += 1
            item["words"] += len(str(line.get("text") or "").split())
        for line in self._get_timeline_lines():
            character = str(line.get("char") or "-")
            item = stats.setdefault(character, {
                "character": character, "lines": 0, "rings": 0, "words": 0,
            })
            item["rings"] += 1
        actors = self._session.data.get("actors", {})
        character_aliases = self._session.data.get("character_aliases", {})
        local = self._session.data.get("episode_actor_map", {}).get(episode, {})
        rows = []
        for character, item in stats.items():
            actor_ids = get_actor_ids_for_character(
                self._session.data, character, episode
            )
            actor = actors.get(actor_ids[0], {}) if actor_ids else {}
            actor_name = self._actor_names(actor_ids)
            if not self._matches(character, actor_ids, actor_name, item):
                continue
            rows.append({
                **item, "scope": "Серия" if character in local else "Проект",
                "scopeId": ASSIGNMENT_SCOPE_EPISODE if character in local else ASSIGNMENT_SCOPE_GLOBAL,
                "actor": actor_name,
                "color": actor.get("color", "transparent") if len(actor_ids) == 1 else "transparent",
                "actorId": actor_ids[0] if actor_ids else "",
                "actorIds": actor_ids,
                "actorEntries": [
                    {
                        "id": actor_id,
                        "name": str(actors.get(actor_id, {}).get("name") or actor_id),
                        "color": str(actors.get(actor_id, {}).get("color") or "#8FAADC"),
                    }
                    for actor_id in actor_ids
                ],
                "aliasesText": ", ".join(
                    character_aliases.get(character, [])
                    if isinstance(character_aliases.get(character, []), list)
                    else []
                ),
            })
        rows.sort(
            key=self._character_sort_value,
            reverse=not self._character_sort_ascending,
        )
        self._characters_model.set_rows(rows)
        visible = {row["character"] for row in rows}
        if self._selected_character and self._selected_character not in visible:
            self._set_selected_character("")
        elif self._selected_character:
            self._update_stats()

    def _matches(self, character, actor_ids, actor_name, item) -> bool:
        if self._actor_filter and self._actor_filter not in actor_ids:
            return False
        if self._show_unassigned_only and actor_ids:
            return False
        if self._search_text:
            aliases = self._session.data.get("character_aliases", {}).get(
                character, []
            )
            alias_text = " ".join(aliases) if isinstance(aliases, list) else ""
            haystack = " ".join((
                character, alias_text, actor_name,
                str(item["words"]), str(item["lines"]),
            )).casefold()
            return self._search_text.casefold() in haystack
        return True

    def _scope(self, character: str) -> str:
        local = self._session.data.get("episode_actor_map", {}).get(
            self._session.current_episode, {}
        )
        return ASSIGNMENT_SCOPE_EPISODE if character in local else ASSIGNMENT_SCOPE_GLOBAL

    def _set_selected_character(self, character: str) -> None:
        changed = character != self._selected_character
        if character != self._selected_character:
            self._selected_character = character
            self.selectedCharacterChanged.emit()
        self._update_stats()
        # The timeline mirrors the current selection with a stronger segment
        # outline. It is intentionally refreshed only when selection changes.
        if changed:
            self._timeline_model.update_rows({
                index: {"selected": row.get("character") == character}
                for index, row in enumerate(self._timeline_model.rows())
            })
            self.changed.emit()

    def _update_stats(self) -> None:
        text = "Выберите персонажа в таблице"
        episode_rows = []
        if self._selected_character:
            actors = self._session.data.get("actors", {})
            stats = self._project_stats(self._selected_character)
            for episode_stats in stats["episodes"]:
                episode = str(episode_stats["episode"])
                actor_ids = get_actor_ids_for_character(
                    self._session.data, self._selected_character, episode
                )
                local = self._session.data.get("episode_actor_map", {}).get(
                    episode, {}
                )
                episode_rows.append({
                    "episode": episode,
                    "lines": int(episode_stats.get("lines", 0)),
                    "rings": int(episode_stats.get("rings", 0)),
                    "words": int(episode_stats.get("words", 0)),
                    "actor": self._actor_names(actor_ids),
                    "scope": "Серия" if self._selected_character in local
                        else "Проект",
                })
            actor_ids = get_actor_ids_for_character(
                self._session.data, self._selected_character,
                self._session.current_episode,
            )
            actor_name = self._actor_names(actor_ids)
            text = (
                f"{self._selected_character}\nАктёр: {actor_name}\n"
                f"Строк: {stats['lines']}\nРеплик: {stats['rings']}\n"
                f"Слов: {stats['words']}"
                if episode_rows else
                f"{self._selected_character}\nНет реплик в проекте"
            )
        self._character_episode_stats_model.set_rows(episode_rows)
        if text != self._selected_character_stats:
            self._selected_character_stats = text
            self.selectedCharacterStatsChanged.emit()

    def _character_sort_value(self, row: Dict[str, Any]):
        value = row.get(self._character_sort_key)
        if self._character_sort_key in {"lines", "rings", "words"}:
            return int(value or 0), str(row.get("character", "")).casefold()
        return str(value or "").casefold(), str(row.get("character", "")).casefold()

    def _get_lines(self):
        return self._get_episode_lines(self._session.current_episode)

    def _get_episode_lines(self, episode: str) -> list[Dict[str, Any]]:
        episode = str(episode or "")
        if episode not in self._episode_lines_cache:
            self._episode_lines_cache[episode] = (
                self._script_text_service.load_atomic_episode_lines(
                    self._session.data, episode
                )
            )
        return self._episode_lines_cache[episode]

    def _get_timeline_lines(self) -> list[Dict[str, Any]]:
        episode = str(self._session.current_episode or "")
        if episode not in self._timeline_lines_cache:
            self._timeline_lines_cache[episode] = (
                self._script_text_service.load_episode_lines(
                    self._session.data, episode
                )
            )
        return self._timeline_lines_cache[episode]

    def _project_stats(self, character: str) -> Dict[str, Any]:
        if character not in self._project_stats_cache:
            self._project_stats_cache[character] = CharacterStatsService(
                self._session.data,
                self._script_text_service.get_merge_config(
                    self._session.data
                ),
            ).project_stats(character, self._get_episode_lines)
        return self._project_stats_cache[character]

    def invalidate_cache(self, domain: str = "") -> None:
        if domain in {"", "project", "working_text", "project_files", "settings"}:
            self._episode_lines_cache.clear()
            self._timeline_lines_cache.clear()
            self._project_stats_cache.clear()

    def _find_actor_by_name(self, name: str) -> Optional[str]:
        name = name.strip().casefold()
        for actor_id, actor in self._session.data.get("actors", {}).items():
            if actor.get("name", "").strip().casefold() == name:
                return actor_id
        return None

    def _actor_names(self, actor_ids) -> str:
        actors = self._session.data.get("actors", {})
        names = [
            str(actors.get(actor_id, {}).get("name") or actor_id)
            for actor_id in actor_ids
        ]
        return "\n".join(names) if names else "-"

    def _next_actor_color(self) -> str:
        used = {actor.get("color", "").upper() for actor in self._session.data.get("actors", {}).values()}
        available = [color for color in MY_PALETTE if color.upper() not in used]
        return random.choice(available or MY_PALETTE)

    @staticmethod
    def _normalized_color(color: str) -> str:
        value = (color or "").strip()
        if value.startswith("#") and len(value) == 7:
            try:
                int(value[1:], 16)
                return value.upper()
            except ValueError:
                pass
        return ""

    @staticmethod
    def _normalized_gender(gender: str) -> str:
        value = (gender or "").strip().upper()
        if value in {"M", "М"}:
            return "М"
        if value in {"F", "Ж"}:
            return "Ж"
        return ""

    @Slot()
    def _episode_changed(self) -> None:
        self._set_selected_character("")
        self._refresh_lines()
        self._refresh_characters()
        self.changed.emit()
