"""QML backend for project role management and actor role statistics."""

from typing import Optional

from PySide6.QtCore import QObject, Property, Signal, Slot, Qt

from core.commands import AssignProjectRolesCommand
from services.role_service import ROLE_MIXED_ACTOR, ROLE_NO_ACTOR, actor_role_stats, collect_project_roles
from ui.qml_backend.models import DictListModel
from ui.qml_backend.project_session import ProjectSession


class RolesBridge(QObject):
    changed = Signal()
    actorStatsChanged = Signal()
    statusRequested = Signal(str)
    errorRequested = Signal(str)
    projectDataChanged = Signal(str)

    def __init__(self, session: ProjectSession, script_text_service,
                 parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._session = session
        self._scripts = script_text_service
        self._actor_title = ""
        self._roles_model = DictListModel({"name": Qt.UserRole + 1, "actorId": Qt.UserRole + 2, "actorName": Qt.UserRole + 3, "episodes": Qt.UserRole + 4}, self)
        self._actors_model = DictListModel({"id": Qt.UserRole + 1, "name": Qt.UserRole + 2}, self)
        self._stats_model = DictListModel({"name": Qt.UserRole + 1, "rings": Qt.UserRole + 2, "words": Qt.UserRole + 3}, self)
        self.refresh()

    @Property(QObject, constant=True)
    def model(self) -> QObject: return self._roles_model

    @Property(QObject, constant=True)
    def actorModel(self) -> QObject: return self._actors_model

    @Property(QObject, constant=True)
    def actorStatsModel(self) -> QObject: return self._stats_model

    @Property(str, notify=actorStatsChanged)
    def actorStatsTitle(self) -> str: return self._actor_title

    @Slot()
    def refresh(self) -> None:
        rows = collect_project_roles(self._session.data, self._lines)
        self._roles_model.set_rows([{"name": row["name"], "actorId": row["actor_id"] or ROLE_NO_ACTOR, "actorName": row["actor_name"], "episodes": ", ".join(row["episodes"]) or "-"} for row in rows])
        actors = [{"id": ROLE_NO_ACTOR, "name": "Без актёра"}]
        actors.extend({"id": actor_id, "name": actor.get("name", actor_id)} for actor_id, actor in sorted(self._session.data.get("actors", {}).items(), key=lambda item: str(item[1].get("name", item[0])).casefold()))
        self._actors_model.set_rows(actors)
        self.changed.emit()

    @Slot("QVariantList", str)
    def assign(self, roles: list, actor_id: str) -> None:
        names = [str(role) for role in roles if str(role)]
        if not names:
            self.errorRequested.emit("Выберите хотя бы одну роль")
            return
        actor_id = "" if actor_id in {ROLE_NO_ACTOR, ROLE_MIXED_ACTOR} else str(actor_id or "")
        if actor_id and actor_id not in self._session.data.get("actors", {}):
            self.errorRequested.emit("Выберите актёра")
            return
        self._session.execute(AssignProjectRolesCommand(self._session.data, names, actor_id or None), "assignments")
        self.refresh()
        self.projectDataChanged.emit("assignments")
        self.statusRequested.emit(f"Обновлено ролей: {len(names)}")

    @Slot(str)
    def prepareActorStats(self, actor_id: str) -> None:
        actor = self._session.data.get("actors", {}).get(actor_id)
        if not actor:
            self.errorRequested.emit("Выберите актёра")
            return
        self._stats_model.set_rows(actor_role_stats(self._session.data, actor_id, self._lines))
        self._actor_title = str(actor.get("name") or actor_id)
        self.actorStatsChanged.emit()

    def _lines(self, episode: str):
        return self._scripts.load_episode_lines(self._session.data, episode)
