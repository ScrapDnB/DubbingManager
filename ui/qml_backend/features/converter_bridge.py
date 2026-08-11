"""QML backend for standalone ASS/SRT montage conversion."""

from copy import deepcopy
from pathlib import Path
from typing import Any, Optional

from PySide6.QtCore import QObject, Property, QTimer, QUrl, Signal, Slot, Qt
from PySide6.QtGui import QDesktopServices, QGuiApplication

from services.episode_service import EpisodeService
from core.export_config_profiles import set_layout_profile_option
from services.global_settings_service import GlobalSettingsService
from services.quick_subtitle_service import QuickSubtitleService
from ui.qml_backend.export_config import normalize_export_option
from ui.qml_backend.models import DictListModel
from ui.qml_backend.project_session import ProjectSession


class ConverterBridge(QObject):
    changed = Signal()
    previewChanged = Signal()
    previewRequested = Signal()
    finished = Signal()
    statusRequested = Signal(str)
    errorRequested = Signal(str)

    def __init__(
        self,
        session: ProjectSession,
        global_settings_service: GlobalSettingsService,
        global_settings: dict[str, Any],
        parent: Optional[QObject] = None,
    ) -> None:
        super().__init__(parent)
        self._session = session
        self._global_settings_service = global_settings_service
        self._global_settings = global_settings
        self._rows: list[dict[str, Any]] = []
        self._queue: list[int] = []
        self._queue_position = 0
        self._cancel_requested = False
        self._busy = False
        self._awaiting_preview = False
        self._settings_preview = False
        self._preview_html = ""
        self._preview_title = ""
        self._preview_path = ""
        self._conversion_config: dict[str, Any] = {}
        self._quick_converter_config = (
            global_settings_service.get_quick_converter_config()
        )
        config = self._quick_converter_config
        self._line_by_line = bool(config.get("line_by_line", False))
        self._formats = {
            "html": bool(config.get("format_html", True)),
            "docx": bool(config.get("format_docx", False)),
            "pdf": bool(config.get("format_pdf", False)),
        }
        self._model = DictListModel({
            "fileName": Qt.UserRole + 1,
            "status": Qt.UserRole + 2,
            "detail": Qt.UserRole + 3,
            "outputPath": Qt.UserRole + 4,
            "statusKind": Qt.UserRole + 5,
        }, self)

    @Property(QObject, constant=True)
    def model(self) -> QObject:
        return self._model

    @Property(bool, notify=changed)
    def busy(self) -> bool:
        return self._busy

    @Property(bool, notify=changed)
    def hasResults(self) -> bool:
        return bool(self._rows)

    @Property(int, notify=changed)
    def total(self) -> int:
        return len(self._queue)

    @Property(int, notify=changed)
    def completed(self) -> int:
        return min(self._queue_position, len(self._queue))

    @Property(float, notify=changed)
    def progress(self) -> float:
        return self.completed / self.total if self.total else 0.0

    @Property(str, notify=changed)
    def summary(self) -> str:
        if self._busy:
            return f"Конвертация: {self.completed} из {self.total}"
        successful = sum(row["statusKind"] == "success" for row in self._rows)
        failed = sum(row["statusKind"] == "error" for row in self._rows)
        if successful or failed:
            return f"Готово: {successful} · ошибок: {failed}"
        return "Перетащите ASS или SRT"

    @Property(bool, notify=changed)
    def exportHtml(self) -> bool:
        return self._formats["html"]

    @Property(bool, notify=changed)
    def exportDocx(self) -> bool:
        return self._formats["docx"]

    @Property(bool, notify=changed)
    def exportPdf(self) -> bool:
        return self._formats["pdf"]

    @Property(bool, notify=changed)
    def lineByLine(self) -> bool:
        return self._line_by_line

    @Property(str, notify=previewChanged)
    def previewHtml(self) -> str:
        return self._preview_html

    @Property(str, notify=previewChanged)
    def previewTitle(self) -> str:
        return self._preview_title

    @Property("QVariantMap", notify=previewChanged)
    def previewConfig(self) -> dict[str, Any]:
        return deepcopy(self._conversion_config)

    @Property(bool, notify=previewChanged)
    def previewSettingsMode(self) -> bool:
        return self._settings_preview

    @Slot(str, bool)
    def setFormat(self, name: str, enabled: bool) -> None:
        if name not in self._formats or self._formats[name] == bool(enabled):
            return
        self._formats[name] = bool(enabled)
        self._quick_converter_config[f"format_{name}"] = bool(enabled)
        self.changed.emit()

    @Slot(bool)
    def setLineByLine(self, enabled: bool) -> None:
        enabled = bool(enabled)
        if self._line_by_line == enabled:
            return
        self._line_by_line = enabled
        self._quick_converter_config["line_by_line"] = enabled
        if self._awaiting_preview:
            self._conversion_config["line_by_line"] = enabled
            try:
                service = self._service()
                self._preview_html = (
                    service.demo_preview_html(self._conversion_config)
                    if self._settings_preview
                    else service.preview_html(
                        self._preview_path, self._conversion_config
                    )
                )
            except Exception as exc:
                self.errorRequested.emit(
                    f"Не удалось обновить предпросмотр: {exc}"
                )
            else:
                self.previewChanged.emit()
        self.changed.emit()

    @Slot("QVariantList", bool, result=bool)
    def convert(self, values: list[Any], preview_first: bool = False) -> bool:
        if self._busy or self._awaiting_preview:
            self.errorRequested.emit("Дождитесь завершения текущей конвертации")
            return False
        if not any(self._formats.values()):
            self.errorRequested.emit("Выберите хотя бы один формат")
            return False

        paths = []
        for value in values or []:
            path = self._local_path(value)
            if path and path not in paths:
                paths.append(path)
        service = self._service()
        supported = set(service.supported_files(paths))
        self._rows = []
        self._queue = []
        for path in paths:
            is_supported = path in supported
            row_index = len(self._rows)
            self._rows.append({
                "fileName": Path(path).name or path,
                "path": path,
                "status": "В очереди" if is_supported else "Пропущен",
                "detail": "" if is_supported else "Поддерживаются только ASS и SRT",
                "outputPath": "",
                "statusKind": "queued" if is_supported else "skipped",
            })
            if is_supported:
                self._queue.append(row_index)
        self._model.set_rows(self._rows)
        self._queue_position = 0
        self._cancel_requested = False
        self.changed.emit()
        if not self._queue:
            self.errorRequested.emit("Не найдено файлов ASS или SRT")
            return False

        if preview_first:
            first_path = self._rows[self._queue[0]]["path"]
            try:
                self._conversion_config = self._current_export_config(service)
                self._preview_path = first_path
                self._preview_html = service.preview_html(
                    first_path, self._conversion_config
                )
                self._preview_title = Path(first_path).name
            except Exception as exc:
                self.errorRequested.emit(f"Не удалось открыть предпросмотр: {exc}")
                return False
            self._awaiting_preview = True
            self._settings_preview = False
            self.previewChanged.emit()
            self.previewRequested.emit()
            return True

        self._conversion_config = self._current_export_config(service)
        self._start_queue()
        return True

    @Slot(result=bool)
    def openSettingsPreview(self) -> bool:
        """Open a demo preview for the isolated quick-converter profile."""
        if self._busy or self._awaiting_preview:
            self.errorRequested.emit("Дождитесь завершения текущей конвертации")
            return False
        service = self._service()
        try:
            self._conversion_config = self._current_export_config(service)
            self._preview_path = ""
            self._preview_title = "Настройки быстрого конвертера"
            self._preview_html = service.demo_preview_html(
                self._conversion_config
            )
        except Exception as exc:
            self.errorRequested.emit(
                f"Не удалось открыть демонстрационный предпросмотр: {exc}"
            )
            return False
        self._awaiting_preview = True
        self._settings_preview = True
        self.previewChanged.emit()
        self.previewRequested.emit()
        return True

    @Slot("QVariantList", result=bool)
    def convertDropped(self, values: list[Any]) -> bool:
        preview_first = bool(
            QGuiApplication.keyboardModifiers() & Qt.AltModifier
        )
        return self.convert(values, preview_first)

    @Slot()
    def continueAfterPreview(self) -> None:
        if not self._awaiting_preview or self._settings_preview:
            return
        self._awaiting_preview = False
        self._start_queue()

    @Slot()
    def cancelPreview(self) -> None:
        if not self._awaiting_preview:
            return
        if self._settings_preview:
            self._awaiting_preview = False
            self._settings_preview = False
            self._preview_path = ""
            self._preview_html = ""
            self._preview_title = ""
            self.previewChanged.emit()
            return
        self._awaiting_preview = False
        for row_index in self._queue:
            self._rows[row_index].update(
                status="Отменено", detail="Экспорт отменён",
                statusKind="skipped",
            )
        self._model.set_rows(self._rows)
        self._queue = []
        self._queue_position = 0
        self._preview_path = ""
        self._settings_preview = False
        self.changed.emit()
        self.previewChanged.emit()

    @Slot(result=bool)
    def savePreviewSettings(self) -> bool:
        """Persist the demo profile without touching the open project."""
        if not self._awaiting_preview or not self._settings_preview:
            return False
        updated = deepcopy(self._global_settings)
        config = deepcopy(self._conversion_config)
        config.update({
            "format_html": self._formats["html"],
            "format_docx": self._formats["docx"],
            "format_pdf": self._formats["pdf"],
            "line_by_line": self._line_by_line,
        })
        updated["quick_converter_config"] = config
        if not self._global_settings_service.save_settings(updated):
            self.errorRequested.emit(
                "Не удалось сохранить настройки быстрого конвертера"
            )
            return False
        self._global_settings.clear()
        self._global_settings.update(
            self._global_settings_service.get_settings()
        )
        self._quick_converter_config = (
            self._global_settings_service.get_quick_converter_config()
        )
        self._line_by_line = bool(
            self._quick_converter_config.get("line_by_line", False)
        )
        self._awaiting_preview = False
        self._settings_preview = False
        self._preview_path = ""
        self._preview_html = ""
        self._preview_title = ""
        self.previewChanged.emit()
        self.statusRequested.emit("Настройки быстрого конвертера сохранены")
        return True

    @Slot(str, "QVariant")
    def setPreviewOption(self, key: str, value: Any) -> None:
        if not self._awaiting_preview:
            return
        normalized = normalize_export_option(key, value)
        if normalized is None or self._conversion_config.get(key) == normalized:
            return
        self._conversion_config = set_layout_profile_option(
            self._conversion_config, key, normalized
        )
        try:
            service = self._service()
            self._preview_html = (
                service.demo_preview_html(self._conversion_config)
                if self._settings_preview
                else service.preview_html(
                    self._preview_path, self._conversion_config
                )
            )
        except Exception as exc:
            self.errorRequested.emit(f"Не удалось обновить предпросмотр: {exc}")
            return
        self.previewChanged.emit()

    @Slot()
    def cancel(self) -> None:
        if self._busy:
            self._cancel_requested = True
            self.changed.emit()

    @Slot()
    def clear(self) -> None:
        if self._busy:
            return
        self._rows = []
        self._queue = []
        self._queue_position = 0
        self._model.set_rows([])
        self.changed.emit()

    @Slot(int)
    def openResult(self, index: int) -> None:
        if not 0 <= index < len(self._rows):
            return
        path = self._rows[index].get("outputPath", "")
        if path and Path(path).exists():
            QDesktopServices.openUrl(QUrl.fromLocalFile(path))

    def _start_queue(self) -> None:
        self._busy = True
        self._cancel_requested = False
        self.changed.emit()
        QTimer.singleShot(0, self._process_next)

    def _process_next(self) -> None:
        if self._cancel_requested:
            for row_index in self._queue[self._queue_position:]:
                self._rows[row_index].update(
                    status="Отменено", detail="", statusKind="skipped"
                )
            self._finish()
            return
        if self._queue_position >= len(self._queue):
            self._finish()
            return

        row_index = self._queue[self._queue_position]
        row = self._rows[row_index]
        row.update(status="Конвертация...", detail="", statusKind="active")
        self._model.set_rows(self._rows)
        self.changed.emit()
        try:
            outputs = self._service().export_montage(
                row["path"],
                self._formats["html"],
                self._formats["docx"],
                self._formats["pdf"],
                self._conversion_config,
            )
            row.update(
                status="Готово",
                detail="\n".join(outputs),
                outputPath=outputs[0] if outputs else "",
                statusKind="success",
            )
        except Exception as exc:
            row.update(
                status="Ошибка",
                detail=str(exc),
                outputPath="",
                statusKind="error",
            )
        self._queue_position += 1
        self._model.set_rows(self._rows)
        self.changed.emit()
        QTimer.singleShot(0, self._process_next)

    def _finish(self) -> None:
        self._busy = False
        self._queue_position = len(self._queue)
        self._model.set_rows(self._rows)
        self.changed.emit()
        self.statusRequested.emit(self.summary)
        self.finished.emit()

    def _service(self) -> QuickSubtitleService:
        episode_service = EpisodeService()
        merge_config = (
            self._global_settings_service.get_replica_merge_config()
        )
        episode_service.set_merge_gap_from_config(merge_config)
        episode_service.set_import_configs(
            self._global_settings_service.get_ass_import_config(),
            self._global_settings_service.get_srt_import_config(),
        )
        converter_data = deepcopy(self._session.data)
        # The standalone converter must not inherit stale per-project merge
        # thresholds. Use the same current global rules as subtitle parsing.
        converter_data["replica_merge_config"] = merge_config
        return QuickSubtitleService(episode_service, converter_data)

    def _current_export_config(
        self, service: QuickSubtitleService
    ) -> dict[str, Any]:
        config = deepcopy(self._quick_converter_config)
        config.update({
            "format_html": self._formats["html"],
            "format_docx": self._formats["docx"],
            "format_pdf": self._formats["pdf"],
            "line_by_line": self._line_by_line,
        })
        return service.export_config(config)

    @staticmethod
    def _local_path(value: Any) -> str:
        if isinstance(value, QUrl):
            return value.toLocalFile() if value.isLocalFile() else value.toString()
        text = str(value or "")
        url = QUrl(text)
        return url.toLocalFile() if url.isLocalFile() else text
