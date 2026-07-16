"""QML backend for the shared global actor library."""

from copy import deepcopy
from datetime import datetime
from typing import Optional

from PySide6.QtCore import QObject, Property, QUrl, Signal, Slot, Qt

from config.constants import MY_PALETTE
from core.commands import AddActorCommand, UpdateProjectFileStateCommand
from services.assignment_transfer_service import AssignmentTransferService
from ui.controllers.global_actor_controller import GlobalActorController
from ui.qml_backend.models import DictListModel
from ui.qml_backend.project_session import ProjectSession


class ActorLibraryBridge(QObject):
    changed = Signal()
    statusRequested = Signal(str)
    errorRequested = Signal(str)
    projectDataChanged = Signal(str)

    def __init__(
        self,
        session: ProjectSession,
        global_settings_service,
        global_settings: dict,
        parent: Optional[QObject] = None,
    ) -> None:
        super().__init__(parent)
        self._session = session
        self._settings = global_settings_service
        self._global_settings = global_settings
        self._assignment_transfer = AssignmentTransferService()
        self._actor_sort_key = "name"
        self._actor_sort_ascending = True
        self._global_model = DictListModel({
            "id": Qt.UserRole + 1, "name": Qt.UserRole + 2,
            "color": Qt.UserRole + 3, "roleCount": Qt.UserRole + 4,
            "gender": Qt.UserRole + 5, "inProject": Qt.UserRole + 6,
            "status": Qt.UserRole + 7,
        }, self)
        self._transfer_model = DictListModel({
            "actorId": Qt.UserRole + 1, "name": Qt.UserRole + 2,
            "exists": Qt.UserRole + 3, "label": Qt.UserRole + 4,
        }, self)
        self._global_choice_model = DictListModel({
            "id": Qt.UserRole + 1, "name": Qt.UserRole + 2,
        }, self)
        self._merge_target_model = DictListModel({
            "targetId": Qt.UserRole + 1, "targetKind": Qt.UserRole + 2,
            "label": Qt.UserRole + 3,
        }, self)
        self.refresh()

    @Property(QObject, constant=True)
    def globalActorsModel(self) -> QObject:
        return self._global_model

    @Property(QObject, constant=True)
    def projectActorTransferModel(self) -> QObject:
        return self._transfer_model

    @Property(QObject, constant=True)
    def globalActorChoicesModel(self) -> QObject:
        return self._global_choice_model

    @Property(QObject, constant=True)
    def mergeTargetModel(self) -> QObject:
        return self._merge_target_model

    @Property(str, notify=changed)
    def actorSortKey(self) -> str:
        return self._actor_sort_key

    @Property(bool, notify=changed)
    def actorSortAscending(self) -> bool:
        return self._actor_sort_ascending

    @Slot(str)
    def setActorSort(self, key: str) -> None:
        if key not in {"name", "gender", "status"}:
            return
        if key == self._actor_sort_key:
            self._actor_sort_ascending = not self._actor_sort_ascending
        else:
            self._actor_sort_key = key
            self._actor_sort_ascending = True
        self.refresh()

    @Slot(str, str)
    def addGlobalActor(self, name: str, gender: str) -> None:
        name = (name or "").strip()
        if not name:
            self.errorRequested.emit("Введите имя актёра")
            return
        if self._settings.find_global_actor_by_name(name):
            self.errorRequested.emit("Актёр с таким именем уже есть в глобальной базе")
            return
        self._settings.add_global_actor(name, gender=self._gender(gender))
        self._save()
        self.refresh()
        self.statusRequested.emit(f"Добавлен глобальный актёр: {name}")

    @Slot(str)
    def deleteGlobalActor(self, actor_id: str) -> None:
        actor = self._settings.get_global_actor_base().get(actor_id)
        if not actor:
            self.errorRequested.emit("Выберите актёра")
            return
        self._settings.remove_global_actor(actor_id)
        self._save()
        self.refresh()
        self.statusRequested.emit(
            f"Удалён глобальный актёр: {actor.get('name', actor_id)}"
        )

    @Slot(str, str, str)
    def updateGlobalActor(self, actor_id: str, name: str, gender: str) -> None:
        actors = self._settings.get_global_actor_base()
        if actor_id not in actors:
            self.errorRequested.emit("Выберите актёра")
            return
        name = (name or "").strip()
        if not name:
            self.errorRequested.emit("Введите имя актёра")
            return
        duplicate = self._settings.find_global_actor_by_name(name)
        if duplicate and duplicate != actor_id:
            self.errorRequested.emit("Актёр с таким именем уже есть в глобальной базе")
            return
        actors[actor_id] = {"name": name, "gender": self._gender(gender)}
        self._settings.set_global_actor_base(actors)
        self._save()
        self.refresh()
        self.statusRequested.emit(f"Глобальный актёр обновлён: {name}")

    @Slot(str)
    def addGlobalActorToProject(self, actor_id: str) -> None:
        actor = self._settings.get_global_actor_base().get(actor_id)
        if not actor:
            self.errorRequested.emit("Выберите актёра")
            return
        name = str(actor.get("name") or actor_id)
        if self._project_actor_by_name(name):
            self.errorRequested.emit(f"{name} уже добавлен в проект")
            return
        actors = self._session.data.setdefault("actors", {})
        target_id = actor_id if actor_id not in actors else str(datetime.now().timestamp())
        self._session.execute(AddActorCommand(
            actors, target_id, name, self._next_color(),
            self._gender(actor.get("gender", "")),
        ), "actors")
        self.projectDataChanged.emit("actors")
        self.refresh()
        self.statusRequested.emit(f"Добавлен в проект: {name}")

    @Slot(str)
    def addProjectActorToGlobal(self, actor_id: str) -> None:
        actor = self._session.data.get("actors", {}).get(actor_id)
        if not actor:
            self.errorRequested.emit("Выберите актёра")
            return
        name = str(actor.get("name") or actor_id)
        if self._settings.find_global_actor_by_name(name):
            self.errorRequested.emit(f"{name} уже есть в глобальной базе")
            return
        self._settings.add_global_actor(
            name, actor_id=actor_id, gender=self._gender(actor.get("gender", "")),
        )
        self._save()
        self.refresh()
        self.statusRequested.emit(f"Добавлен в глобальную базу: {name}")

    @Slot()
    def refreshProjectActorTransfer(self) -> None:
        rows, _ = GlobalActorController(
            self._session.data, self._settings,
        ).project_actor_transfer_rows()
        self._transfer_model.set_rows([{
            "actorId": row["actor_id"], "name": row["name"],
            "exists": row["exists"], "label": row["label"],
        } for row in rows])

    @Slot("QVariantList")
    def addProjectActorsToGlobal(self, actor_ids: list) -> None:
        ids = [str(value) for value in actor_ids if str(value)]
        if not ids:
            self.errorRequested.emit("Выберите хотя бы одного актёра")
            return
        stats = self._settings.add_project_actors_to_global(
            self._session.data.get("actors", {}), ids,
        )
        self._save()
        self.refresh()
        self.refreshProjectActorTransfer()
        self.statusRequested.emit(
            f"В глобальную базу добавлено: {stats['added']} · "
            f"уже было: {stats['skipped_existing']}"
        )

    @Slot(str, str)
    def rememberProjectActor(self, name: str, gender: str) -> None:
        if self._settings.find_global_actor_by_name(name):
            return
        self._settings.add_global_actor(name, gender=self._gender(gender))
        self._save()
        self.refresh()

    @Slot(result=int)
    def syncProjectActorsWithGlobalBase(self) -> int:
        candidate = deepcopy(self._session.data)
        changed = GlobalActorController(candidate, self._settings).sync_project_actors_with_global_base()
        if not changed:
            self.refresh()
            return 0
        fields = ("actors", "global_map", "episode_actor_map", "export_config")
        updates = {field: candidate.get(field) for field in fields
                   if candidate.get(field) != self._session.data.get(field)}
        self._session.execute(UpdateProjectFileStateCommand(
            self._session.data, updates, "Синхронизирована глобальная база актёров",
        ), "actors")
        self.projectDataChanged.emit("actors")
        self.refresh()
        self.statusRequested.emit(f"Синхронизировано актёров: {changed}")
        return changed

    @Slot(str)
    def prepareMergeTargets(self, source_actor_id: str) -> None:
        source_actor_id = str(source_actor_id or "")
        rows = []
        for actor_id, actor in sorted(
            self._session.data.get("actors", {}).items(),
            key=lambda item: str(item[1].get("name", item[0])).casefold(),
        ):
            if actor_id != source_actor_id:
                rows.append({
                    "targetId": actor_id,
                    "targetKind": "project",
                    "label": f"Проект: {actor.get('name', actor_id)}",
                })
        project_ids = set(self._session.data.get("actors", {}))
        for actor_id, actor in sorted(
            self._settings.get_global_actor_base().items(),
            key=lambda item: str(item[1].get("name", item[0])).casefold(),
        ):
            if actor_id == source_actor_id:
                continue
            if actor_id in project_ids:
                continue
            rows.append({
                "targetId": actor_id,
                "targetKind": "global",
                "label": f"Глобальная: {actor.get('name', actor_id)}",
            })
        self._merge_target_model.set_rows(rows)
        self.changed.emit()

    @Slot(str, str, str, result=bool)
    def mergeProjectActor(
        self, source_actor_id: str, target_kind: str, target_actor_id: str,
    ) -> bool:
        source_actor_id = str(source_actor_id or "")
        target_actor_id = str(target_actor_id or "")
        if source_actor_id not in self._session.data.get("actors", {}):
            self.errorRequested.emit("Выберите актёра для объединения")
            return False
        if not target_actor_id or target_kind not in {"project", "global"}:
            self.errorRequested.emit("Выберите актёра, который останется")
            return False
        candidate = deepcopy(self._session.data)
        controller = GlobalActorController(candidate, self._settings)
        source_name = candidate["actors"][source_actor_id].get(
            "name", source_actor_id
        )
        if target_kind == "global":
            global_actor = self._settings.get_global_actor_base().get(
                target_actor_id
            )
            if not global_actor:
                self.errorRequested.emit("Глобальный актёр не найден")
                return False
            changed = controller.merge_project_actor_with_global(
                source_actor_id, target_actor_id, global_actor
            )
        else:
            actors = candidate.get("actors", {})
            if target_actor_id == source_actor_id or target_actor_id not in actors:
                self.errorRequested.emit("Выберите другого актёра проекта")
                return False
            source = actors[source_actor_id]
            target = deepcopy(actors[target_actor_id])
            if not target.get("gender") and source.get("gender"):
                target["gender"] = source["gender"]
            target["roles"] = list(dict.fromkeys(
                list(target.get("roles", [])) + list(source.get("roles", []))
            ))
            actors[target_actor_id] = target
            del actors[source_actor_id]
            controller.replace_project_actor_references(
                source_actor_id, target_actor_id
            )
            changed = True
        if not changed:
            return False
        fields = ("actors", "global_map", "episode_actor_map", "export_config")
        updates = {
            field: candidate.get(field)
            for field in fields
            if candidate.get(field) != self._session.data.get(field)
        }
        self._session.execute(UpdateProjectFileStateCommand(
            self._session.data, updates,
            f"Объединён актёр {source_name}",
        ), "actors")
        self.projectDataChanged.emit("actors")
        self.refresh()
        target = self._session.data.get("actors", {}).get(target_actor_id, {})
        self.statusRequested.emit(
            f"Актёры объединены: {source_name} → "
            f"{target.get('name', target_actor_id)}"
        )
        return True

    @Slot(str, result=bool)
    def exportGlobalActorBase(self, path_or_url: str) -> bool:
        path = self._local_path(path_or_url)
        if not path:
            return False
        try:
            self._settings.export_global_actor_base(path)
        except Exception as exc:
            self.errorRequested.emit(
                f"Не удалось экспортировать глобальную базу актёров: {exc}"
            )
            return False
        self.statusRequested.emit(f"Глобальная база актёров сохранена: {path}")
        return True

    @Slot(str, result=bool)
    def importGlobalActorBase(self, path_or_url: str) -> bool:
        path = self._local_path(path_or_url)
        if not path:
            return False
        try:
            stats = self._settings.import_global_actor_base(path)
            self._save()
        except Exception as exc:
            self.errorRequested.emit(
                f"Не удалось импортировать глобальную базу актёров: {exc}"
            )
            return False
        self.refresh()
        self.statusRequested.emit(
            f"Глобальная база импортирована · добавлено: {stats['added']} · "
            f"уже было: {stats['matched']}"
        )
        return True

    @Slot(str, result=bool)
    def exportProjectAssignments(self, path_or_url: str) -> bool:
        path = self._local_path(path_or_url)
        if not path:
            return False
        try:
            self._assignment_transfer.save_export(self._session.data, path)
        except Exception as exc:
            self.errorRequested.emit(
                f"Не удалось экспортировать распределение актёров: {exc}"
            )
            return False
        self.statusRequested.emit(f"Распределение актёров сохранено: {path}")
        return True

    @Slot(str, result=bool)
    def importProjectAssignments(self, path_or_url: str) -> bool:
        path = self._local_path(path_or_url)
        if not path:
            return False
        candidate = deepcopy(self._session.data)
        try:
            stats = self._assignment_transfer.import_from_file(candidate, path)
        except Exception as exc:
            self.errorRequested.emit(
                f"Не удалось импортировать распределение актёров: {exc}"
            )
            return False

        fields = ("actors", "global_map", "episode_actor_map")
        updates = {
            field: candidate.get(field, {})
            for field in fields
            if candidate.get(field, {}) != self._session.data.get(field, {})
        }
        if updates:
            self._session.execute(UpdateProjectFileStateCommand(
                self._session.data,
                updates,
                "Импортировано распределение актёров",
            ), "assignments")
            self.projectDataChanged.emit("assignments")

        imported_ids = list(self._session.data.get("actors", {}))
        self._settings.add_project_actors_to_global(
            self._session.data.get("actors", {}), imported_ids,
        )
        self._save()
        self.refresh()
        self.statusRequested.emit(
            f"Распределение импортировано · актёров добавлено: "
            f"{stats['actors_added']} · сопоставлено: {stats['actors_matched']} · "
            f"глобальных назначений: {stats['global_assignments']} · "
            f"серийных: {stats['episode_assignments']} · "
            f"пропущено: {stats['skipped_episode_assignments']}"
        )
        return True

    @Slot()
    def refresh(self) -> None:
        project_names = {
            str(actor.get("name") or "").strip().casefold()
            for actor in self._session.data.get("actors", {}).values()
            if isinstance(actor, dict)
        }
        global_rows = [{
            "id": actor_id, "name": actor.get("name", actor_id),
            "color": "transparent", "roleCount": "В проекте" if str(actor.get("name") or "").strip().casefold() in project_names else "",
            "gender": actor.get("gender", ""),
            "inProject": str(actor.get("name") or "").strip().casefold() in project_names,
            "status": "В проекте" if str(actor.get("name") or "").strip().casefold() in project_names else "",
        } for actor_id, actor in self._settings.get_global_actor_base().items()]
        global_rows.sort(
            key=self._actor_sort_value,
            reverse=not self._actor_sort_ascending,
        )
        self._global_model.set_rows(global_rows)
        self._global_choice_model.set_rows([
            {"id": "", "name": "Создать нового актёра"},
            *[
                {"id": actor_id, "name": actor.get("name", actor_id)}
                for actor_id, actor in sorted(
                    self._settings.get_global_actor_base().items(),
                    key=lambda item: str(
                        item[1].get("name", item[0])
                    ).casefold(),
                )
                if not self._project_actor_by_name(
                    str(actor.get("name", actor_id))
                )
            ],
        ])
        self.changed.emit()

    def _actor_sort_value(self, row: dict):
        value = row.get(self._actor_sort_key)
        return str(value or "").casefold(), str(row.get("name", "")).casefold()

    def _save(self) -> None:
        self._global_settings["global_actor_base"] = (
            self._settings.get_global_actor_base()
        )
        self._settings.save_settings(self._global_settings)

    def _project_actor_by_name(self, name: str) -> bool:
        key = name.strip().casefold()
        return any(str(actor.get("name") or "").strip().casefold() == key
                   for actor in self._session.data.get("actors", {}).values())

    def _next_color(self) -> str:
        used = {str(actor.get("color", "")).upper()
                for actor in self._session.data.get("actors", {}).values()}
        return next((color for color in MY_PALETTE if color.upper() not in used), MY_PALETTE[0])

    @staticmethod
    def _gender(value: str) -> str:
        value = str(value or "").strip().upper()
        return "М" if value in {"M", "М"} else "Ж" if value in {"F", "Ж"} else ""

    @staticmethod
    def _local_path(path_or_url: str) -> str:
        url = QUrl(str(path_or_url or ""))
        return url.toLocalFile() if url.isLocalFile() else str(path_or_url or "")
