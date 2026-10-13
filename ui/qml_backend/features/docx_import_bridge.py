"""QML backend for configurable DOCX import."""

from copy import deepcopy
from pathlib import Path
import re
from typing import Any, Optional

from PySide6.QtCore import QObject, Property, QUrl, Signal, Slot, Qt

from core.commands import UndoStack, UpdateProjectFileStateCommand
from services.docx_import_service import COLUMN_TYPES, DocxImportService
from services.episode_service import EpisodeService
from application import ImportController
from application.import_controller import SUBTITLE_IMPORT_UNAVAILABLE
from utils.helpers import format_seconds_to_full_tc
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
        self._first_rows = {}
        self._ignore_headers = {}
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

    @Property(int, notify=changed)
    def columnCount(self) -> int:
        return self._columns_model.rowCount()

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

    @Property(int, notify=changed)
    def rowCount(self) -> int:
        return len(self._tables[self._table_index]) if self._tables else 0

    @Property(int, notify=changed)
    def firstRow(self) -> int:
        if not self._tables:
            return 1
        return self._first_rows.get(self._table_index, self._service._data_start_index(self._tables[self._table_index]) + 1)

    @Property(bool, notify=changed)
    def ignoreHeader(self) -> bool:
        if not self._tables:
            return False
        return self._ignore_headers.get(self._table_index, bool(self._service.last_detection.get("header_found")))

    @Property(int, notify=changed)
    def tableStartRow(self) -> int:
        return max(1, self.firstRow - int(self.ignoreHeader))

    @Property("QVariantList", notify=changed)
    def rawRows(self) -> list:
        if not self._tables:
            return []
        return [{"row": i + 1, "cells": row} for i, row in enumerate(self._tables[self._table_index][:30])]

    @Property(str, notify=changed)
    def sourceSummary(self) -> str:
        return f"DOCX · таблиц: {len(self._tables)}"

    @Property(str, notify=changed)
    def validationMessage(self) -> str:
        return "" if self.canImport else "Выберите колонку с текстом реплик"

    @Property(bool, notify=changed)
    def canImport(self) -> bool:
        return bool(self._tables and self._service.mapping_usable(
            self._mapping, max((len(row) for row in self._tables[self._table_index]), default=0)))

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
        self._first_rows = {}
        self._ignore_headers = {}
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
        self._first_rows.pop(self._table_index, None)
        self._ignore_headers.pop(self._table_index, None)
        self._update_detection_summary()
        self._refresh_preview()
        self.changed.emit()

    @Slot(str, int)
    def setMapping(self, field: str, column: int) -> None:
        if field not in COLUMN_TYPES:
            return
        self._mapping[field] = None if column < 0 else int(column)
        if column >= 0:
            if field == "time_split":
                self._mapping["time_start"] = self._mapping["time_end"] = None
            elif field in ("time_start", "time_end"):
                self._mapping["time_split"] = None
        self._refresh_preview()
        self.changed.emit()

    @Slot(int)
    def setFirstRow(self, row: int) -> None:
        if 1 <= row <= self.rowCount:
            self._first_rows[self._table_index] = row
            if row == 1:
                self._ignore_headers[self._table_index] = False
            self._refresh_preview()
            self.changed.emit()

    @Slot(int)
    def setTableStartRow(self, row: int) -> None:
        if 1 <= row <= self.rowCount:
            self._first_rows[self._table_index] = row + int(self.ignoreHeader)
            self._refresh_preview()
            self.changed.emit()

    @Slot(bool)
    def setIgnoreHeader(self, ignored: bool) -> None:
        if self._tables:
            start = self.tableStartRow
            self._ignore_headers[self._table_index] = ignored
            self._first_rows[self._table_index] = start + int(ignored)
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
        if self._session.data.get("project_kind") == "audiobook":
            self.errorRequested.emit(SUBTITLE_IMPORT_UNAVAILABLE)
            return False
        if not self._session.flush_pending_edits():
            return False
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
        self._service.detection_config["rows_to_skip"] = self._global_settings_service.get_docx_import_config().get("rows_to_skip", 0)
        _stats, all_lines = self._service.parse_tables(
            selected_tables,
            self._mapping,
            first_rows=[self._first_rows.get(i) for i in (
                range(len(self._tables)) if all_tables else [self._table_index])],
        )
        if not all_lines:
            self.errorRequested.emit("Не удалось извлечь реплики из DOCX")
            return False

        docx_config = self._global_settings_service.get_docx_import_config()
        docx_config.update({
            "mapping": deepcopy(self._mapping),
            "time_separators": list(self._service.time_separators),
        })
        source_import_config = deepcopy(docx_config)
        source_import_config["first_rows"] = {str(i): row for i, row in self._first_rows.items()}
        source_import_config["ignore_headers"] = {str(i): value for i, value in self._ignore_headers.items()}
        source_import_config["table_selection"] = {
            "mode": "all" if all_tables else "single",
            "index": None if all_tables else self._table_index,
            "table_count": len(selected_tables),
        }

        candidate = deepcopy(self._session.data)
        import_service = EpisodeService()
        controller = ImportController(
            candidate,
            import_service,
            self._script_text_service,
            UndoStack(),
            lambda: self._session.project_service.current_project_path,
            merge_config=(
                self._global_settings_service.get_replica_merge_config()
            ),
        )
        controller.add_docx_episode(
            episode,
            self._path,
            {
                "lines": all_lines,
                "import_config": source_import_config,
            },
        )
        self._global_settings_service.update_docx_import_config(docx_config)
        self._global_settings_service.save_settings(
            self._global_settings_service.get_settings()
        )
        fields = (
            "project_kind", "episodes", "loaded_episodes",
            "episode_working_texts", "script_storage",
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
        self._first_rows = {}
        self._ignore_headers = {}
        self._tables_model.set_rows([])
        self._columns_model.set_rows([])
        self._preview_model.set_rows([])
        self._summary = "Выберите DOCX-файл"
        self._detection_summary = ""
        self.changed.emit()

    def _prepare_table(self, use_saved_mapping: bool) -> None:
        rows = self._tables[self._table_index]
        max_columns = max((len(row) for row in rows), default=0)
        self._service.detect_columns(rows)
        header_index = self._service.last_detection.get("header_row") or 0
        header = rows[header_index] if rows else []
        self._columns_model.set_rows([
            {
                "index": index,
                "label": f"{index + 1} · "
                + (
                    self._one_line(header[index])[:50]
                    if index < len(header)
                    else "Колонка"
                ),
            }
            for index in range(max_columns)
        ])
        saved = self._global_settings_service.get_docx_import_config().get("mapping", {})
        if use_saved_mapping and self._mapping_usable(saved, max_columns):
            self._service.detect_columns(rows)
            self._mapping = deepcopy(saved)
            self._detection_summary = "Использованы последние настройки колонок"
        else:
            self._mapping = self._service.detect_columns(rows)
            self._update_detection_summary()
        self._refresh_preview()

    def _refresh_preview(self) -> None:
        if not self._tables:
            return
        self._service.detect_columns(self._tables[self._table_index])
        if self._table_index in self._first_rows:
            self._service._has_header = False
            self._service.detection_config["rows_to_skip"] = self._first_rows[self._table_index] - 1
        else:
            self._service.detection_config["rows_to_skip"] = self._global_settings_service.get_docx_import_config().get("rows_to_skip", 0)
        preview = self._service.get_preview_data(
            self._tables[self._table_index], self._mapping, limit=30
        )
        rows = []
        valid = 0
        for item in preview:
            mapped = item.get("mapped", {})
            text = str(mapped.get("text") or "")
            character = str(mapped.get("character") or "")
            start = item.get("time_split_start_parsed")
            end = item.get("time_split_end_parsed")
            if start is None:
                start = item.get("time_start_parsed")
            if end is None:
                end = item.get("time_end_parsed")
            start = start if start is not None else 0.0
            end = end if end is not None else start + float(self._service.detection_config.get("default_duration", 1.0))
            timing = f"{format_seconds_to_full_tc(start)} – {format_seconds_to_full_tc(end)}"
            if text:
                valid += 1
            rows.append({
                "character": self._one_line(character) or "-",
                "timing": self._one_line(timing) or "-",
                "text": text or "-",
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
            self._detection_summary = "Заголовок не распознан. Проверьте колонки и первую строку данных."

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
