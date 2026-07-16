"""QML backend for project lifecycle, episodes, and undo history."""

from datetime import datetime
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QObject, Property, QTimer, QUrl, Signal, Slot, Qt

from config.constants import (
    PROJECT_BACKUP_FILE_EXTENSION,
    PROJECT_FILE_EXTENSION,
)
from core.commands import (
    DeleteEpisodeCommand,
    RenameEpisodeCommand,
    UpdateProjectNameCommand,
)
from ui.controllers.import_controller import ImportController
from ui.qml_backend.models import DictListModel
from ui.qml_backend.project_session import ProjectSession
from utils.helpers import ordered_episode_names


def _display_path(path_or_url: str) -> str:
    if not path_or_url:
        return ""
    url = QUrl(path_or_url)
    return url.toLocalFile() if url.isLocalFile() else path_or_url


class ProjectBridge(QObject):
    """Own the open-project lifecycle and episode navigation."""

    nameChanged = Signal()
    pathChanged = Signal()
    currentEpisodeChanged = Signal()
    dirtyChanged = Signal()
    undoStateChanged = Signal()
    recentProjectsChanged = Signal()
    backupsChanged = Signal()
    statusRequested = Signal(str)
    errorRequested = Signal(str)
    saveChangesRequested = Signal(str)
    savePathRequested = Signal()
    closeApproved = Signal()
    resetRequested = Signal()
    refreshRequested = Signal()

    def __init__(
        self,
        session: ProjectSession,
        episode_service,
        script_text_service,
        project_folder_service,
        global_settings_service,
        global_settings: dict,
        parent: Optional[QObject] = None,
    ) -> None:
        super().__init__(parent)
        self._session = session
        self._episode_service = episode_service
        self._script_text_service = script_text_service
        self._project_folder_service = project_folder_service
        self._global_settings_service = global_settings_service
        self._global_settings = global_settings
        self._pending_action: Optional[tuple[str, str]] = None
        self._episodes_model = DictListModel({
            "name": Qt.UserRole + 1,
            "subtitle": Qt.UserRole + 2,
            "lineCount": Qt.UserRole + 3,
            "hasVideo": Qt.UserRole + 4,
        }, self)
        self._recent_projects_model = DictListModel({
            "path": Qt.UserRole + 1,
            "name": Qt.UserRole + 2,
            "display": Qt.UserRole + 3,
        }, self)
        self._backups_model = DictListModel({
            "path": Qt.UserRole + 1,
            "name": Qt.UserRole + 2,
            "modified": Qt.UserRole + 3,
            "size": Qt.UserRole + 4,
        }, self)
        self._session.currentEpisodeChanged.connect(
            self.currentEpisodeChanged
        )
        self._session.dirtyChanged.connect(self.dirtyChanged)
        self._session.undoStateChanged.connect(self.undoStateChanged)
        self.refresh_models()
        self._refresh_recent_projects()
        self._autosave_timer = QTimer(self)
        self._autosave_timer.setInterval(self._backup_interval_ms())
        self._autosave_timer.timeout.connect(self.autoSave)
        if self._session.project_service.backups_enabled():
            self._autosave_timer.start()

    @Property(str, notify=nameChanged)
    def name(self) -> str:
        return str(self._session.data.get("project_name") or "Без имени")

    @name.setter
    def name(self, value: str) -> None:
        value = value.strip() or "Без имени"
        if value == self.name:
            return
        self._session.execute(
            UpdateProjectNameCommand(self._session.data, value),
            "project_name",
        )
        self.nameChanged.emit()

    @Property(str, notify=pathChanged)
    def path(self) -> str:
        return self._session.project_service.current_project_path or ""

    @Property(str, notify=currentEpisodeChanged)
    def currentEpisode(self) -> str:
        return self._session.current_episode

    @Property(bool, notify=dirtyChanged)
    def dirty(self) -> bool:
        return self._session.project_service.is_dirty

    @Property(bool, notify=undoStateChanged)
    def canUndo(self) -> bool:
        return self._session.undo_stack.can_undo()

    @Property(bool, notify=undoStateChanged)
    def canRedo(self) -> bool:
        return self._session.undo_stack.can_redo()

    @Property(QObject, constant=True)
    def episodesModel(self) -> QObject:
        return self._episodes_model

    @Property(QObject, constant=True)
    def recentProjectsModel(self) -> QObject:
        return self._recent_projects_model

    @Property(QObject, constant=True)
    def backupsModel(self) -> QObject:
        return self._backups_model

    @Property(int, notify=backupsChanged)
    def backupCount(self) -> int:
        return self._backups_model.rowCount()

    @Slot()
    def create(self) -> None:
        if self._defer_for_unsaved_changes("new", ""):
            return
        self._create_now()

    @Slot(str)
    def open(self, path_or_url: str) -> None:
        path = _display_path(path_or_url)
        if not path:
            return
        if self._defer_for_unsaved_changes("open", path):
            return
        self._open_now(path)

    @Slot()
    def save(self) -> None:
        if not self.path:
            self.savePathRequested.emit()
            return
        if self._save_now():
            self._continue_pending_action()

    @Slot(str)
    def saveAs(self, path_or_url: str) -> None:
        path = self._normalized_save_path(path_or_url)
        if not path:
            return
        if self._session.project_service.save_project_as(
            self._session.data,
            path,
        ):
            self.statusRequested.emit(f"Проект сохранён: {Path(path).name}")
            self.pathChanged.emit()
            self.dirtyChanged.emit()
            self._remember_recent_project(path)
            self._continue_pending_action()
        else:
            self.errorRequested.emit("Не удалось сохранить проект")

    @Slot()
    def requestClose(self) -> None:
        if self._defer_for_unsaved_changes("close", ""):
            return
        self.closeApproved.emit()

    @Slot(str)
    def resolvePendingChanges(self, decision: str) -> None:
        decision = str(decision or "").strip().lower()
        if not self._pending_action:
            return
        if decision == "cancel":
            self._pending_action = None
            return
        if decision == "discard":
            self._execute_pending_action()
            return
        if decision != "save":
            return
        if not self.path:
            self.savePathRequested.emit()
            return
        if self._save_now():
            self._continue_pending_action()

    @Slot()
    def cancelPendingChanges(self) -> None:
        self._pending_action = None

    @Slot()
    def autoSave(self) -> None:
        service = self._session.project_service
        if not service.is_dirty or not service.backups_enabled():
            return
        if service.auto_save(self._session.data):
            self.refreshBackups()
            self.statusRequested.emit("Создана автокопия проекта")
        else:
            self.errorRequested.emit("Не удалось создать автокопию проекта")

    @Slot("QVariantMap")
    def setBackupConfig(self, config: dict) -> None:
        self._session.project_service.set_backup_config(config)
        self._autosave_timer.setInterval(self._backup_interval_ms())
        if self._session.project_service.backups_enabled():
            self._autosave_timer.start()
        else:
            self._autosave_timer.stop()
        self.refreshBackups()

    @Slot(str)
    def openRecent(self, path: str) -> None:
        path = path or ""
        if path == "__clear__":
            self.clearRecent()
            return
        if not path:
            return
        if not Path(path).exists():
            self.errorRequested.emit(f"Файл больше не существует: {path}")
            self._refresh_recent_projects()
            return
        self.open(path)

    @Slot()
    def clearRecent(self) -> None:
        self._global_settings_service.clear_recent_projects()
        self._global_settings["recent_projects"] = []
        self._global_settings_service.save_settings(self._global_settings)
        self._refresh_recent_projects()
        self.statusRequested.emit("Список недавних проектов очищен")

    @Slot()
    def refreshBackups(self) -> None:
        rows = []
        for path in self._session.project_service.list_backups():
            try:
                stat = path.stat()
            except OSError:
                continue
            rows.append({
                "path": str(path),
                "name": path.name,
                "modified": datetime.fromtimestamp(stat.st_mtime).strftime(
                    "%d.%m.%Y %H:%M"
                ),
                "size": self._format_file_size(stat.st_size),
            })
        self._backups_model.set_rows(rows)
        self.backupsChanged.emit()

    @Slot(str)
    def restoreBackup(self, backup_path: str) -> None:
        backup_path = _display_path(backup_path)
        if not self.path:
            self.errorRequested.emit(
                "Восстановление доступно после первого сохранения проекта"
            )
            return
        allowed = {
            str(path.resolve())
            for path in self._session.project_service.list_backups()
        }
        try:
            resolved = str(Path(backup_path).resolve())
        except (OSError, RuntimeError):
            resolved = ""
        if not resolved or resolved not in allowed:
            self.errorRequested.emit("Резервная копия не найдена")
            self.refreshBackups()
            return
        if self._defer_for_unsaved_changes("restore", resolved):
            return
        self._restore_backup_now(resolved)

    @Slot(str)
    def importSubtitle(self, path_or_url: str) -> None:
        path = _display_path(path_or_url)
        if not path:
            return
        source_path = Path(path)
        if source_path.suffix.lower() not in {".ass", ".srt"}:
            self.errorRequested.emit("QML-импорт сейчас поддерживает ASS и SRT")
            return
        if not source_path.exists():
            self.errorRequested.emit(f"Файл не найден: {path}")
            return

        controller = self._import_controller()
        episode = self._unique_episode_name(
            controller.suggested_episode_name(path)
        )
        old_name = self.name
        self._episode_service.set_merge_gap_from_config(
            self._session.data.get("replica_merge_config", {})
        )
        self._episode_service.set_import_configs(
            self._session.data.get("ass_import_config", {}),
            self._session.data.get("srt_import_config", {}),
        )
        try:
            _stats, lines = controller.add_subtitle_episode(episode, path)
        except Exception as exc:
            self.errorRequested.emit(f"Не удалось импортировать субтитры: {exc}")
            return
        self._session.current_episode = episode
        self._session.mark_dirty()
        self.refresh_models()
        if self.name != old_name:
            self.nameChanged.emit()
        self.refreshRequested.emit()
        self.statusRequested.emit(
            f"Импортирована серия {episode}: {source_path.name}"
            + (f" ({len(lines)} реплик)" if lines else "")
        )

    @Slot(str)
    def selectEpisode(self, episode: str) -> None:
        episode = str(episode or "")
        if episode == self._session.current_episode:
            return
        self._session.current_episode = episode
        self.refreshRequested.emit()

    @Slot(str)
    def renameCurrentEpisode(self, new_name: str) -> None:
        old_name = self._session.current_episode
        new_name = (new_name or "").strip()
        if not old_name:
            self.errorRequested.emit("Нет выбранной серии")
            return
        if not new_name or new_name == old_name:
            return
        if new_name in self._session.data.get("episodes", {}):
            self.errorRequested.emit("Серия с таким именем уже есть")
            return
        self._session.execute(RenameEpisodeCommand(
            self._session.data.setdefault("episodes", {}),
            old_name,
            new_name,
            self._session.data.setdefault("episode_actor_map", {}),
            self._session.data.setdefault("video_paths", {}),
            self._session.data.setdefault("loaded_episodes", {}),
            self._session.data.setdefault("episode_texts", {}),
            self._session.data.setdefault("episode_working_texts", {}),
            self._session.data.setdefault("audiobook_chapter_order", []),
        ), "episodes")
        self._session.current_episode = new_name
        self.refresh_models()
        self.refreshRequested.emit()
        self.statusRequested.emit(
            f"Серия переименована: {old_name} -> {new_name}"
        )

    @Slot()
    def deleteCurrentEpisode(self) -> None:
        self.deleteEpisode(self._session.current_episode)

    @Slot(str)
    def deleteEpisode(self, episode: str) -> None:
        episode = str(episode or "")
        if not episode:
            self.errorRequested.emit("Нет выбранной серии")
            return
        if episode not in self._session.data.get("episodes", {}):
            self.errorRequested.emit("Серия не найдена")
            return
        self._session.execute(DeleteEpisodeCommand(
            self._session.data.setdefault("episodes", {}),
            self._session.data.setdefault("video_paths", {}),
            self._session.data.setdefault("loaded_episodes", {}),
            episode,
            self._session.data.setdefault("episode_actor_map", {}),
            self._session.data.setdefault("episode_texts", {}),
            self._session.data.setdefault("episode_working_texts", {}),
            self._session.data.setdefault("audiobook_chapter_order", []),
        ), "episodes")
        self._episode_service.invalidate_episode(episode)
        if self._session.current_episode == episode:
            self._session.current_episode = self._first_episode()
        self.refresh_models()
        self.refreshRequested.emit()
        self.statusRequested.emit(f"Серия удалена: {episode}")

    @Slot()
    def undo(self) -> None:
        if not self._session.undo_stack.undo():
            return
        self._session.mark_dirty()
        self._session.notify_changed("project")
        self.nameChanged.emit()
        self.refresh_models()
        self.refreshRequested.emit()
        self.statusRequested.emit("Отменено")

    @Slot()
    def redo(self) -> None:
        if not self._session.undo_stack.redo():
            return
        self._session.mark_dirty()
        self._session.notify_changed("project")
        self.nameChanged.emit()
        self.refresh_models()
        self.refreshRequested.emit()
        self.statusRequested.emit("Повторено")

    @Slot()
    def refresh(self) -> None:
        self.refresh_models()
        self.refreshRequested.emit()

    def refresh_models(self) -> None:
        episodes = self._session.data.get("episodes", {})
        rows = []
        for name in ordered_episode_names(self._session.data):
            lines = self._script_text_service.load_episode_lines(
                self._session.data,
                name,
            )
            source = episodes.get(name) or ""
            rows.append({
                "name": name,
                "subtitle": f"{len(lines)} реплик" + (
                    f" · {Path(source).name}" if source else ""
                ),
                "lineCount": len(lines),
                "hasVideo": bool(
                    self._session.data.get("video_paths", {}).get(name)
                ),
            })
        self._episodes_model.set_rows(rows)
        current = self._session.current_episode
        if current and current not in episodes:
            self._session.current_episode = str(rows[0]["name"]) if rows else ""
        elif not current and rows:
            self._session.current_episode = str(rows[0]["name"])

    def _create_now(self) -> None:
        service = self._session.project_service
        data = service.create_new_project("Новый проект")
        data.update({
            "export_config": self._global_settings_service.get_default_export_config(),
            "prompter_config": self._global_settings_service.get_default_prompter_config(),
            "replica_merge_config": self._global_settings_service.get_replica_merge_config(),
            "ass_import_config": self._global_settings_service.get_ass_import_config(),
            "srt_import_config": self._global_settings_service.get_srt_import_config(),
            "docx_import_config": self._global_settings_service.get_docx_import_config(),
        })
        service.current_project_path = None
        service.is_dirty = False
        self._session.undo_stack.clear()
        self._session.replace_project(data, "")
        self.resetRequested.emit()
        self._emit_project_changed()
        self.refresh_models()
        self.refreshRequested.emit()
        self.statusRequested.emit("Создан новый QML-проект")

    def _open_now(self, path: str) -> None:
        is_backup = Path(path).suffix.lower() == PROJECT_BACKUP_FILE_EXTENSION
        try:
            data = self._session.project_service.load_project(path)
        except Exception as exc:
            self.errorRequested.emit(f"Не удалось открыть проект: {exc}")
            return
        if data is None:
            self.errorRequested.emit("Проект не был загружен")
            return
        paths_rebased = self._project_folder_service.prepare_project_paths(
            data, path
        )
        imported_texts = self._script_text_service.link_existing_working_texts(
            data, path
        )
        self._session.undo_stack.clear()
        self._session.replace_project(data, self._first_episode(data))
        self.resetRequested.emit()
        self._emit_project_changed()
        self.refresh_models()
        self.refreshRequested.emit()
        if paths_rebased or imported_texts:
            self._session.mark_dirty()
        if is_backup:
            self._session.project_service.current_project_path = None
            self._session.project_service.is_dirty = True
            self.pathChanged.emit()
            self.dirtyChanged.emit()
            self.statusRequested.emit(
                "Открыта резервная копия. Сохраните её как обычный проект"
            )
            return
        self._remember_recent_project(path)
        if imported_texts:
            self.statusRequested.emit(
                f"Открыт проект: встроено рабочих текстов: {imported_texts}"
            )
        elif paths_rebased:
            self.statusRequested.emit(
                f"Открыт проект: обновлена папка проекта"
            )
        else:
            self.statusRequested.emit(f"Открыт проект: {Path(path).name}")

    def _restore_backup_now(self, backup_path: str) -> None:
        target = self.path
        backup_name = Path(backup_path).name
        if not target or not self._session.project_service.restore_from_backup(
            backup_path,
            target,
        ):
            self.errorRequested.emit("Не удалось восстановить резервную копию")
            return
        self._open_now(target)
        self.refreshBackups()
        self.statusRequested.emit(
            f"Восстановлена резервная копия: {backup_name}"
        )

    def _save_now(self) -> bool:
        if self._session.project_service.save_project(self._session.data):
            self.statusRequested.emit("Проект сохранён")
            self.dirtyChanged.emit()
            self._remember_recent_project(self.path)
            return True
        self.errorRequested.emit("Не удалось сохранить проект")
        return False

    def _import_controller(self) -> ImportController:
        return ImportController(
            data_ref=self._session.data,
            episode_service=self._episode_service,
            script_text_service=self._script_text_service,
            undo_stack=self._session.undo_stack,
            get_current_project_path=lambda: self.path or None,
        )

    def _refresh_recent_projects(self) -> None:
        existing = [
            path for path in self._global_settings_service.get_recent_projects()
            if Path(path).exists()
        ]
        rows = [{
            "path": "",
            "name": "Недавние проекты",
            "display": "Недавние проекты",
        }]
        if existing:
            rows.extend(self._recent_project_rows(existing))
            rows.append({
                "path": "__clear__",
                "name": "Очистить список",
                "display": "Очистить список",
            })
        else:
            rows.append({
                "path": "",
                "name": "Нет недавних проектов",
                "display": "Нет недавних проектов",
            })
        self._recent_projects_model.set_rows(rows)
        self.recentProjectsChanged.emit()

    def _remember_recent_project(self, path: str) -> None:
        if not path:
            return
        self._global_settings_service.add_recent_project(path)
        self._global_settings["recent_projects"] = (
            self._global_settings_service.get_recent_projects()
        )
        self._global_settings_service.save_settings(self._global_settings)
        self._refresh_recent_projects()

    @staticmethod
    def _recent_project_rows(paths: list[str]) -> list[dict[str, str]]:
        counts: dict[str, int] = {}
        for path in paths:
            name = Path(path).name or path
            counts[name] = counts.get(name, 0) + 1
        rows = []
        for path in paths:
            item = Path(path)
            name = item.name or path
            display = (
                f"{name} - {item.parent.name}"
                if counts.get(name, 0) > 1 and item.parent.name
                else name
            )
            rows.append({"path": path, "name": name, "display": display})
        return rows

    def _defer_for_unsaved_changes(self, action: str, payload: str) -> bool:
        if not self._session.project_service.is_dirty:
            return False
        self._pending_action = (action, payload)
        labels = {
            "new": "созданием нового проекта",
            "open": "открытием другого проекта",
            "close": "выходом из программы",
            "restore": "восстановлением резервной копии",
        }
        self.saveChangesRequested.emit(
            f"Сохранить изменения перед {labels.get(action, 'продолжением')}?"
        )
        return True

    def _continue_pending_action(self) -> None:
        if self._pending_action:
            self._execute_pending_action()

    def _execute_pending_action(self) -> None:
        pending = self._pending_action
        self._pending_action = None
        if not pending:
            return
        action, payload = pending
        if action == "new":
            self._create_now()
        elif action == "open":
            self._open_now(payload)
        elif action == "close":
            self.closeApproved.emit()
        elif action == "restore":
            self._restore_backup_now(payload)

    def _emit_project_changed(self) -> None:
        self.nameChanged.emit()
        self.pathChanged.emit()
        self.currentEpisodeChanged.emit()
        self.dirtyChanged.emit()
        self.undoStateChanged.emit()

    def _normalized_save_path(self, path_or_url: str) -> str:
        path = _display_path(path_or_url)
        if not path:
            return ""
        project_path = Path(path).expanduser()
        if not project_path.suffix:
            project_path = project_path.with_suffix(PROJECT_FILE_EXTENSION)
        return str(project_path)

    def _unique_episode_name(self, suggested: str) -> str:
        base = (suggested or "1").strip() or "1"
        episodes = self._session.data.setdefault("episodes", {})
        if base not in episodes:
            return base
        counter = 2
        while f"{base} {counter}" in episodes:
            counter += 1
        return f"{base} {counter}"

    def _first_episode(self, data: Optional[dict] = None) -> str:
        ordered = ordered_episode_names(data or self._session.data)
        return ordered[0] if ordered else ""

    @staticmethod
    def _episode_sort_key(value: str) -> tuple[int, str]:
        text = str(value)
        return (int(text), "") if text.isdigit() else (10**9, text.casefold())

    @staticmethod
    def _format_file_size(size: int) -> str:
        if size >= 1024 * 1024:
            return f"{size / (1024 * 1024):.1f} МБ"
        return f"{max(1, round(size / 1024))} КБ"

    def _backup_interval_ms(self) -> int:
        config = self._session.project_service.get_backup_config()
        return int(config.get("interval_minutes", 5)) * 60_000
