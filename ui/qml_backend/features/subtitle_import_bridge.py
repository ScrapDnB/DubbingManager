"""QML backend for preparing and atomically importing subtitle files."""

from copy import deepcopy
from pathlib import Path
from typing import Any, Optional

from PySide6.QtCore import QObject, Property, QUrl, Signal, Slot, Qt

from core.commands import UndoStack, UpdateProjectFileStateCommand
from services.episode_service import EpisodeService
from ui.controllers.import_controller import ImportController
from ui.qml_backend.models import DictListModel
from ui.qml_backend.project_session import ProjectSession


class SubtitleImportBridge(QObject):
    changed = Signal()
    projectDataChanged = Signal(str)
    projectNameChanged = Signal()
    statusRequested = Signal(str)
    errorRequested = Signal(str)

    def __init__(
        self,
        session: ProjectSession,
        episode_service,
        script_text_service,
        parent: Optional[QObject] = None,
    ) -> None:
        super().__init__(parent)
        self._session = session
        self._episode_service = episode_service
        self._script_text_service = script_text_service
        self._rows: list[dict[str, Any]] = []
        self._model = DictListModel({
            "fileName": Qt.UserRole + 1,
            "path": Qt.UserRole + 2,
            "episode": Qt.UserRole + 3,
            "status": Qt.UserRole + 4,
            "statusKind": Qt.UserRole + 5,
        }, self)

    @Property(QObject, constant=True)
    def model(self) -> QObject:
        return self._model

    @Property(int, notify=changed)
    def count(self) -> int:
        return len(self._rows)

    @Property(str, notify=changed)
    def summary(self) -> str:
        if not self._rows:
            return "Файлы не выбраны"
        ready = sum(row["statusKind"] == "ready" for row in self._rows)
        return f"Файлов: {len(self._rows)} · готово к импорту: {ready}"

    @Property(bool, notify=changed)
    def canImport(self) -> bool:
        return bool(self._rows) and all(
            row["statusKind"] == "ready" for row in self._rows
        )

    @Slot("QVariantList", result=bool)
    def prepare(self, values: list[Any]) -> bool:
        paths: list[str] = []
        for value in values or []:
            path = self._local_path(value)
            source = Path(path)
            if (
                path
                and source.suffix.lower() in {".ass", ".srt"}
                and source.is_file()
                and path not in paths
            ):
                paths.append(path)
        if not paths:
            self.errorRequested.emit("Выберите существующие файлы ASS или SRT")
            return False

        existing = set(self._session.data.get("episodes", {}))
        reserved = set(existing)
        rows = []
        for path in paths:
            base = ImportController.suggested_episode_name(path)
            episode = self._unique_name(base, reserved)
            reserved.add(episode)
            rows.append({
                "fileName": Path(path).name,
                "path": path,
                "episode": episode,
                "status": "",
                "statusKind": "",
            })
        self._rows = rows
        self._validate(reset_model=True)
        return True

    @Slot(int, str)
    def setEpisode(self, index: int, value: str) -> None:
        if not 0 <= index < len(self._rows):
            return
        self._rows[index]["episode"] = str(value or "").strip()
        self._validate()

    @Slot(result=bool)
    def importAll(self) -> bool:
        self._validate()
        if not self.canImport:
            self.errorRequested.emit("Исправьте названия серий перед импортом")
            return False

        old_project_name = self._session.data.get("project_name")
        candidate = deepcopy(self._session.data)
        import_service = EpisodeService()
        import_service.set_merge_gap_from_config(
            candidate.get("replica_merge_config", {})
        )
        import_service.set_import_configs(
            candidate.get("ass_import_config", {}),
            candidate.get("srt_import_config", {}),
        )
        controller = ImportController(
            candidate,
            import_service,
            self._script_text_service,
            UndoStack(),
            lambda: self._session.project_service.current_project_path,
        )

        imported_lines = 0
        try:
            for row in self._rows:
                _stats, lines = controller.add_subtitle_episode(
                    row["episode"], row["path"]
                )
                imported_lines += len(lines)
        except Exception as exc:
            self.errorRequested.emit(f"Не удалось импортировать субтитры: {exc}")
            return False

        fields = (
            "project_name", "project_kind", "episodes", "loaded_episodes",
            "episode_texts", "episode_working_texts",
        )
        updates = {
            field: candidate.get(field)
            for field in fields
            if candidate.get(field) != self._session.data.get(field)
        }
        episodes = [row["episode"] for row in self._rows]
        self._session.execute(UpdateProjectFileStateCommand(
            self._session.data,
            updates,
            f"Импортировано серий: {len(episodes)}",
        ), "working_text")
        self._session.current_episode = episodes[-1]
        for episode in episodes:
            self._episode_service.invalidate_episode(episode)
        self.projectDataChanged.emit("working_text")
        if candidate.get("project_name") != old_project_name:
            self.projectNameChanged.emit()
        self.statusRequested.emit(
            f"Импортировано серий: {len(episodes)} · реплик: {imported_lines}"
        )
        self.reset()
        return True

    @Slot()
    def reset(self) -> None:
        self._rows = []
        self._model.set_rows([])
        self.changed.emit()

    def _validate(self, reset_model: bool = False) -> None:
        existing = set(self._session.data.get("episodes", {}))
        counts: dict[str, int] = {}
        for row in self._rows:
            name = row["episode"]
            counts[name] = counts.get(name, 0) + 1

        for row in self._rows:
            name = row["episode"]
            if not name:
                row.update(status="Введите название", statusKind="error")
            elif name in existing:
                row.update(status="Уже существует", statusKind="error")
            elif counts[name] > 1:
                row.update(status="Название повторяется", statusKind="error")
            else:
                row.update(status="Готово", statusKind="ready")
        if reset_model:
            self._model.set_rows(self._rows)
        elif self._rows:
            self._model.dataChanged.emit(
                self._model.index(0, 0),
                self._model.index(len(self._rows) - 1, 0),
                [Qt.UserRole + 4, Qt.UserRole + 5],
            )
        self.changed.emit()

    @staticmethod
    def _local_path(value: Any) -> str:
        if isinstance(value, QUrl):
            return value.toLocalFile() if value.isLocalFile() else value.toString()
        text = str(value or "")
        url = QUrl(text)
        return url.toLocalFile() if url.isLocalFile() else text

    @staticmethod
    def _unique_name(base: str, reserved: set[str]) -> str:
        base = str(base or "1").strip() or "1"
        if base not in reserved:
            return base
        counter = 2
        while f"{base} {counter}" in reserved:
            counter += 1
        return f"{base} {counter}"
