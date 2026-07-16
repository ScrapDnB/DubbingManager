"""QML backend for configurable DOCX import."""

from copy import deepcopy
from pathlib import Path
import re
from typing import Any, Optional

from PySide6.QtCore import QObject, Property, QUrl, Signal, Slot, Qt

from core.commands import UndoStack, UpdateProjectFileStateCommand
from services.docx_import_service import COLUMN_TYPES, DocxImportService
from services.episode_service import EpisodeService
from ui.controllers.import_controller import ImportController
from ui.qml_backend.models import DictListModel
from ui.qml_backend.project_session import ProjectSession


class DocxImportBridge(QObject):
    changed = Signal()
    projectDataChanged = Signal(str)
    statusRequested = Signal(str)
    errorRequested = Signal(str)

    def __init__(
        self,
        session: ProjectSession,
        episode_service,
        script_text_service,
        global_settings_service,
        parent: Optional[QObject] = None,
    ) -> None:
        super().__init__(parent)
        self._session = session
        self._episode_service = episode_service
        self._script_text_service = script_text_service
        self._global_settings_service = global_settings_service
        self._service = DocxImportService()
        self._path = ""
        self._tables: list[list[list[str]]] = []
        self._table_index = 0
        self._mapping: dict[str, Any] = {}
        self._summary = "Выберите DOCX-файл"
        self._detection_summary = ""
        self._tables_model = DictListModel({
            "index": Qt.UserRole + 1,
            "label": Qt.UserRole + 2,
        }, self)
        self._columns_model = DictListModel({
            "index": Qt.UserRole + 1,
            "label": Qt.UserRole + 2,
        }, self)
        self._preview_model = DictListModel({
            "character": Qt.UserRole + 1,
            "timing": Qt.UserRole + 2,
            "text": Qt.UserRole + 3,
            "status": Qt.UserRole + 4,
        }, self)

    @Property(QObject, constant=True)
    def tablesModel(self) -> QObject:
        return self._tables_model

    @Property(QObject, constant=True)
    def columnsModel(self) -> QObject:
        return self._columns_model

    @Property(QObject, constant=True)
    def previewModel(self) -> QObject:
        return self._preview_model

    @Property(str, notify=changed)
    def fileName(self) -> str:
        return Path(self._path).name if self._path else "Файл не выбран"

    @Property(str, notify=changed)
    def suggestedEpisode(self) -> str:
        numbers = re.findall(r"\d+", Path(self._path).stem)
        return " ".join(numbers) or "1"

    @Property(int, notify=changed)
    def currentTableIndex(self) -> int:
        return self._table_index

    @Property(int, notify=changed)
    def tableCount(self) -> int:
        return len(self._tables)

    @Property("QVariantMap", notify=changed)
    def mapping(self) -> dict:
        return deepcopy(self._mapping)

    @Property(str, notify=changed)
    def summary(self) -> str:
        return self._summary

    @Property(str, notify=changed)
    def detectionSummary(self) -> str:
        return self._detection_summary

    @Property(str, notify=changed)
    def separators(self) -> str:
        return " ".join(self._service.time_separators)

    @Property(bool, notify=changed)
    def canImport(self) -> bool:
        return bool(self._tables and self._mapping.get("text") is not None)

    @Property("QVariantList", constant=True)
    def fields(self) -> list[dict[str, str]]:
        return [
            {"key": key, "label": label}
            for key, label in COLUMN_TYPES.items()
        ]

    @Slot(str, result=bool)
    def load(self, path_or_url: str) -> bool:
        path = self._local_path(path_or_url)
        if not path:
            return False
        config = deepcopy(self._global_settings_service.get_docx_import_config())
        project_config = self._session.data.get("docx_import_config", {})
        if isinstance(project_config, dict):
            config.update(deepcopy(project_config))
        self._service = DocxImportService(detection_config=config)
        try:
            tables = self._service.extract_tables_from_docx(path)
        except Exception as exc:
            self.errorRequested.emit(f"Не удалось открыть DOCX: {exc}")
            return False
        if not tables:
            self.errorRequested.emit("В DOCX не найдено таблиц или текста")
            return False
        self._path = path
        self._tables = tables
        self._tables_model.set_rows([
            {
                "index": index,
                "label": self._table_label(index, rows),
            }
            for index, rows in enumerate(tables)
        ])
        self._table_index = 0
        self._prepare_table(use_saved_mapping=True)
        self.changed.emit()
        return True

    @Slot(int)
    def setTable(self, index: int) -> None:
        if not 0 <= index < len(self._tables) or index == self._table_index:
            return
        self._table_index = index
        self._prepare_table(use_saved_mapping=False)
        self.changed.emit()

    @Slot()
    def autoDetect(self) -> None:
        if not self._tables:
            return
        self._mapping = self._service.detect_columns(
            self._tables[self._table_index]
        )
        self._update_detection_summary()
        self._refresh_preview()
        self.changed.emit()

    @Slot(str, int)
    def setMapping(self, field: str, column: int) -> None:
        if field not in COLUMN_TYPES:
            return
        self._mapping[field] = None if column < 0 else int(column)
        self._refresh_preview()
        self.changed.emit()

    @Slot(str)
    def setSeparators(self, text: str) -> None:
        values = [
            value for value in re.split(r"[\s,]+", str(text or "").strip())
            if value
        ]
        if not values:
            return
        self._service.set_time_separators(values)
        self._refresh_preview()
        self.changed.emit()

    @Slot(str, bool, result=bool)
    def importEpisode(self, episode: str, all_tables: bool) -> bool:
        episode = str(episode or "").strip()
        if not episode:
            self.errorRequested.emit("Введите название серии")
            return False
        if episode in self._session.data.get("episodes", {}):
            self.errorRequested.emit("Серия с таким названием уже существует")
            return False
        if not self.canImport:
            self.errorRequested.emit("Укажите колонку с текстом")
            return False

        selected_tables = (
            self._tables if all_tables else [self._tables[self._table_index]]
        )
        _stats, all_lines = self._service.parse_tables(
            selected_tables,
            self._mapping,
        )
        if not all_lines:
            self.errorRequested.emit("Не удалось извлечь реплики из DOCX")
            return False

        candidate = deepcopy(self._session.data)
        import_service = EpisodeService()
        controller = ImportController(
            candidate,
            import_service,
            self._script_text_service,
            UndoStack(),
            lambda: self._session.project_service.current_project_path,
        )
        controller.add_docx_episode(
            episode,
            self._path,
            {"lines": all_lines},
        )
        docx_config = deepcopy(candidate.get("docx_import_config", {}))
        docx_config.update({
            "mapping": deepcopy(self._mapping),
            "time_separators": list(self._service.time_separators),
        })
        candidate["docx_import_config"] = docx_config
        fields = (
            "project_kind", "episodes", "loaded_episodes",
            "episode_working_texts", "docx_import_config",
        )
        updates = {
            field: candidate.get(field)
            for field in fields
            if candidate.get(field) != self._session.data.get(field)
        }
        self._session.execute(UpdateProjectFileStateCommand(
            self._session.data,
            updates,
            f"Импортирован DOCX как серия {episode}",
        ), "working_text")
        self._session.current_episode = episode
        self._episode_service.invalidate_episode(episode)
        self.projectDataChanged.emit("working_text")
        self.statusRequested.emit(
            f"DOCX импортирован: серия {episode} · реплик: {len(all_lines)} · "
            f"таблиц: {len(selected_tables)}"
        )
        return True

    @Slot()
    def reset(self) -> None:
        self._path = ""
        self._tables = []
        self._mapping = {}
        self._table_index = 0
        self._tables_model.set_rows([])
        self._columns_model.set_rows([])
        self._preview_model.set_rows([])
        self._summary = "Выберите DOCX-файл"
        self._detection_summary = ""
        self.changed.emit()

    def _prepare_table(self, use_saved_mapping: bool) -> None:
        rows = self._tables[self._table_index]
        max_columns = max((len(row) for row in rows), default=0)
        header = rows[0] if rows else []
        self._columns_model.set_rows([
            {
                "index": index,
                "label": f"{index + 1}: "
                + (
                    self._one_line(header[index])[:50]
                    if index < len(header)
                    else "Колонка"
                ),
            }
            for index in range(max_columns)
        ])
        saved = self._session.data.get("docx_import_config", {}).get(
            "mapping", {}
        )
        if use_saved_mapping and self._mapping_usable(saved, max_columns):
            self._service.detect_columns(rows)
            self._mapping = deepcopy(saved)
            self._detection_summary = "Применён последний mapping проекта"
        else:
            self._mapping = self._service.detect_columns(rows)
            self._update_detection_summary()
        self._refresh_preview()

    def _refresh_preview(self) -> None:
        if not self._tables:
            return
        preview = self._service.get_preview_data(
            self._tables[self._table_index], self._mapping, limit=30
        )
        rows = []
        valid = 0
        for item in preview:
            mapped = item.get("mapped", {})
            text = str(mapped.get("text") or "")
            character = str(mapped.get("character") or "")
            timing = str(
                mapped.get("time_split")
                or " - ".join(filter(None, (
                    mapped.get("time_start"), mapped.get("time_end")
                )))
                or ""
            )
            if text:
                valid += 1
            rows.append({
                "character": self._one_line(character) or "-",
                "timing": self._one_line(timing) or "-",
                "text": self._one_line(text) or "-",
                "status": "Готово" if text else "Нет текста",
            })
        self._preview_model.set_rows(rows)
        self._summary = (
            f"Таблица {self._table_index + 1} из {len(self._tables)} · "
            f"строк в предпросмотре: {len(rows)} · готово: {valid}"
        )

    def _update_detection_summary(self) -> None:
        info = self._service.last_detection
        if info.get("header_found"):
            self._detection_summary = (
                f"Заголовок: строка {info['header_row'] + 1} · "
                f"совпадений: {info['matches']} · "
                f"уверенность: {round(info['confidence'] * 100)}%"
            )
        else:
            self._detection_summary = "Заголовок не найден, применён fallback mapping"

    @staticmethod
    def _mapping_usable(mapping: dict, column_count: int) -> bool:
        return DocxImportService.mapping_usable(mapping, column_count)

    @staticmethod
    def _table_label(index: int, rows: list[list[str]]) -> str:
        first = next((cell for row in rows[:1] for cell in row if cell), "")
        first = DocxImportBridge._one_line(first)
        return f"Таблица {index + 1}" + (f" · {first[:40]}" if first else "")

    @staticmethod
    def _one_line(value: Any) -> str:
        return " ".join(str(value or "").split())

    @staticmethod
    def _local_path(path_or_url: str) -> str:
        url = QUrl(str(path_or_url or ""))
        return url.toLocalFile() if url.isLocalFile() else str(path_or_url or "")
