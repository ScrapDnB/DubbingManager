"""Per-sheet spreadsheet import configuration and one atomic project mutation."""

from copy import deepcopy
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QObject, Property, QUrl, Signal, Slot, Qt

from application import ImportController
from application.import_controller import SUBTITLE_IMPORT_UNAVAILABLE
from core.commands import UndoStack, UpdateProjectFileStateCommand
from services.docx_import_service import COLUMN_TYPES, DocxImportService
from services.episode_service import EpisodeService
from services.project_fps_service import project_fps
from services.spreadsheet_import_service import SpreadsheetImportService
from ui.qml_backend.models import DictListModel


class SpreadsheetImportBridge(QObject):
    changed = Signal()
    projectDataChanged = Signal(str)
    statusRequested = Signal(str)
    errorRequested = Signal(str)

    def __init__(self, session, episode_service, script_text_service, global_settings_service,
                 parent: Optional[QObject] = None):
        super().__init__(parent)
        self._session = session
        self._episode_service = episode_service
        self._script_text_service = script_text_service
        self._settings = global_settings_service
        self._service = SpreadsheetImportService()
        self._columns_model = DictListModel({"index": Qt.UserRole + 1, "label": Qt.UserRole + 2}, self)
        self._preview_model = DictListModel({key: Qt.UserRole + i + 1 for i, key in enumerate(
            ("row", "character", "timing", "text", "status"))}, self)
        self.reset()

    @Property(int, notify=changed)
    def columnCount(self) -> int:
        return self._columns_model.rowCount()

    @Property(QObject, constant=True)
    def columnsModel(self):
        return self._columns_model

    @Property(QObject, constant=True)
    def previewModel(self):
        return self._preview_model

    @Property("QVariantList", constant=True)
    def fields(self):
        return [{"key": key, "label": label} for key, label in COLUMN_TYPES.items()]

    @Property(str, notify=changed)
    def fileName(self):
        return Path(self._path).name

    @Property(bool, notify=changed)
    def isCsv(self):
        return Path(self._path).suffix.lower() == ".csv"

    @Property("QVariantList", notify=changed)
    def sheets(self):
        return [{"index": i, "name": sheet.name, "selected": state["selected"],
                 "episode": state["episode"], "hidden": sheet.hidden,
                 "rowCount": len(sheet.rows), "lineCount": state.get("line_count", 0)}
                for i, (sheet, state) in enumerate(zip(self._sheets, self._states))]

    @Property(int, notify=changed)
    def currentSheetIndex(self):
        return self._index

    @Property(str, notify=changed)
    def episodeName(self):
        return self._state.get("episode", "")

    @Property("QVariantMap", notify=changed)
    def mapping(self):
        return deepcopy(self._state.get("config", {}).get("mapping", {}))

    @Property(int, notify=changed)
    def firstRow(self):
        return self._state.get("config", {}).get("first_row", 1)

    @Property(bool, notify=changed)
    def ignoreHeader(self):
        return bool(self._state.get("config", {}).get("ignore_header", False))

    @Property(int, notify=changed)
    def tableStartRow(self):
        return max(1, self.firstRow - int(self.ignoreHeader))

    @Property(bool, notify=changed)
    def canApplyMappingToAll(self):
        return (sum(bool(sheet.rows) for sheet in self._sheets) > 1
                and DocxImportService.mapping_usable(self.mapping, self.columnCount))

    @Property(int, notify=changed)
    def rowCount(self):
        return len(self._sheets[self._index].rows) if self._sheets else 0

    @Property(str, notify=changed)
    def timeUnit(self):
        return self._state.get("config", {}).get("time_unit", "seconds")

    @Property(float, notify=changed)
    def fps(self):
        return self._state.get("config", {}).get("fps", 25.0)

    @Property(str, notify=changed)
    def encoding(self):
        return self._encoding

    @Property(str, notify=changed)
    def delimiter(self):
        return self._delimiter

    @Property(str, notify=changed)
    def sourceSummary(self):
        if self.isCsv:
            separator = "табуляция" if self._service.delimiter == "\t" else self._service.delimiter
            return f"CSV · {self._service.encoding} · разделитель: {separator}"
        return f"{Path(self._path).suffix[1:].upper()} · листов: {len(self._sheets)}"

    @Property(str, notify=changed)
    def summary(self):
        selected = [state for state in self._states if state["selected"]]
        return f"Выбрано листов: {len(selected)} · серий: {len(selected)} · реплик: {sum(s.get('line_count', 0) for s in selected)}"

    @Property(str, notify=changed)
    def validationMessage(self):
        return self._problem

    @Property(bool, notify=changed)
    def canImport(self):
        return bool(self._sheets and not self._problem)

    @Property("QVariantList", notify=changed)
    def rawRows(self):
        if not self._sheets:
            return []
        return [{"row": i + 1, "cells": [self._service.cell_text(value) for value in row]}
                for i, row in enumerate(self._sheets[self._index].rows[:30])]

    @property
    def _state(self):
        return self._states[self._index] if self._states else {}

    @Slot(str, result=bool)
    def load(self, path_or_url):
        if self._session.data.get("project_kind") == "audiobook":
            self.errorRequested.emit(SUBTITLE_IMPORT_UNAVAILABLE)
            return False
        url = QUrl(path_or_url)
        path = url.toLocalFile() if url.isLocalFile() else path_or_url
        return self._load(path, "auto", "auto")

    def _load(self, path, encoding, delimiter):
        service = SpreadsheetImportService()
        try:
            sheets = service.load(path, encoding, delimiter)
            if not any(sheet.rows for sheet in sheets):
                raise ValueError("В файле нет данных")
            used = set(self._session.data.get("episodes", {}))
            states = []
            fps = project_fps(deepcopy(self._session.data))
            for sheet in sheets:
                base = ImportController.suggested_episode_name(path) if len(sheets) == 1 else sheet.name
                episode = base
                suffix = 2
                while episode in used:
                    episode = f"{base} ({suffix})"
                    suffix += 1
                used.add(episode)
                config = service.detect(sheet)
                config["fps"] = fps
                states.append({"selected": bool(sheet.rows) and not sheet.hidden,
                               "episode": episode, "config": config})
        except Exception as exc:
            self.errorRequested.emit(f"Не удалось открыть таблицу: {exc}")
            return False
        self._service, self._path, self._sheets, self._states = service, path, sheets, states
        self._encoding, self._delimiter = encoding, delimiter
        self._index = next((i for i, state in enumerate(states) if state["selected"]), 0)
        self._refresh()
        return True

    @Slot(str, str, result=bool)
    def setCsvOptions(self, encoding, delimiter):
        if not self.isCsv:
            return False
        old_state = deepcopy(self._state)
        if not self._load(self._path, encoding, delimiter):
            return False
        self._state["episode"] = old_state["episode"]
        self._state["selected"] = old_state["selected"]
        self._refresh()
        return True

    @Slot(int)
    def setSheet(self, index):
        if 0 <= index < len(self._sheets):
            self._index = index
            self._refresh()

    @Slot(int, bool)
    def setSelected(self, index, selected):
        if 0 <= index < len(self._states):
            self._states[index]["selected"] = selected
            self._refresh()

    @Slot(str)
    def setEpisodeName(self, name):
        if self._states:
            self._state["episode"] = str(name).strip()
            self._refresh()

    @Slot(str, int)
    def setMapping(self, field, column):
        if self._states and field in COLUMN_TYPES:
            mapping = self._state["config"]["mapping"]
            if column >= self._sheets[self._index].column_count:
                return
            mapping[field] = column if column >= 0 else None
            if column >= 0:
                if field == "time_split":
                    mapping["time_start"] = mapping["time_end"] = None
                elif field in ("time_start", "time_end"):
                    mapping["time_split"] = None
            self._refresh()

    @Slot(int)
    def setFirstRow(self, row):
        if self._states:
            self._state["config"]["first_row"] = row
            if row == 1:
                self._state["config"]["ignore_header"] = False
            self._refresh()

    @Slot(int)
    def setTableStartRow(self, row):
        if self._states and 1 <= row <= self.rowCount:
            self.setFirstRow(row + int(self.ignoreHeader))

    @Slot(bool)
    def setIgnoreHeader(self, ignored):
        if self._states:
            start = self.tableStartRow
            self._state["config"]["ignore_header"] = ignored
            self._state["config"]["first_row"] = start + int(ignored)
            self._refresh()

    @Slot()
    def applyMappingToAll(self):
        if not self.canApplyMappingToAll:
            return
        mapping = self.mapping
        ignore_header = self.ignoreHeader
        for sheet, state in zip(self._sheets, self._states):
            if sheet.rows:
                config = state["config"]
                start = max(1, config.get("first_row", 1) - int(bool(config.get("ignore_header", False))))
                config["mapping"] = deepcopy(mapping)
                config["ignore_header"] = ignore_header
                config["first_row"] = start + int(ignore_header)
        self._refresh()
        self.statusRequested.emit("Настройки колонок и пропуска заголовка применены ко всем непустым листам")

    @Slot(str)
    def setTimeUnit(self, unit):
        if self._states and unit in ("seconds", "excel"):
            self._state["config"]["time_unit"] = unit
            self._refresh()

    @Slot(float)
    def setFps(self, fps):
        if self._states and 0 < fps <= 240:
            self._state["config"]["fps"] = fps
            self._refresh()

    @Slot()
    def autoDetect(self):
        if self._states:
            fps = self.fps
            self._state["config"] = self._service.detect(self._sheets[self._index])
            self._state["config"]["fps"] = fps
            self._refresh()

    def _refresh(self):
        names, problems = set(), []
        if not any(state["selected"] for state in self._states):
            problems.append("Выберите хотя бы один лист")
        current_preview = []
        for i, (sheet, state) in enumerate(zip(self._sheets, self._states)):
            # Navigating/renaming/selecting a sheet does not reparse its rows.
            if state.get("parsed_config") != state["config"]:
                error = ""
                try:
                    lines, preview = self._service.parse_sheet(sheet, state["config"])
                    bad = next((row for row in preview if row["status"] == "Ошибка тайминга"), None)
                    if bad:
                        error = f"Лист «{sheet.name}», строка {bad['row']}: проверьте тайминг"
                    elif not lines:
                        error = f"Лист «{sheet.name}»: нет реплик с текстом"
                except ValueError as exc:
                    lines, preview, error = [], [], str(exc)
                state.update({"parsed_config": deepcopy(state["config"]), "preview": preview[:30],
                              "line_count": len(lines), "error": error})
            error = state["error"]
            if i == self._index:
                current_preview = state["preview"]
            if not state["selected"]:
                continue
            name = state["episode"]
            if not name:
                problems.append(f"Лист «{sheet.name}»: введите название серии")
            elif name in names or name in self._session.data.get("episodes", {}):
                problems.append(f"Серия «{name}» уже существует или повторяется")
            names.add(name)
            if error:
                problems.append(error)
        self._problem = problems[0] if problems else ""
        if self._sheets:
            sheet = self._sheets[self._index]
            header_index = max(0, self.firstRow - 2)
            header = sheet.rows[header_index] if header_index < len(sheet.rows) else []
            self._columns_model.set_rows([{"index": i, "label": f"{i + 1} · " + (
                self._service.cell_text(header[i])[:50] if i < len(header) else "Колонка")}
                for i in range(sheet.column_count)])
        self._preview_model.set_rows(current_preview)
        self.changed.emit()

    @Slot(result=bool)
    def importSelected(self):
        if self._session.data.get("project_kind") == "audiobook":
            self.errorRequested.emit(SUBTITLE_IMPORT_UNAVAILABLE)
            return False
        if not self._session.flush_pending_edits():
            return False
        self._refresh()
        if not self.canImport:
            self.errorRequested.emit(self._problem)
            return False
        candidate = deepcopy(self._session.data)
        controller = ImportController(candidate, EpisodeService(), self._script_text_service, UndoStack(),
                                      lambda: self._session.project_service.current_project_path,
                                      merge_config=self._settings.get_replica_merge_config())
        imported = []
        try:
            for sheet, state in zip(self._sheets, self._states):
                if not state["selected"]:
                    continue
                lines, _preview = self._service.parse_sheet(sheet, state["config"])
                config = {**deepcopy(state["config"]), "sheet_name": sheet.name,
                          "encoding": self._service.encoding or "auto", "delimiter": self._service.delimiter or "auto"}
                controller.add_table_episode(state["episode"], self._path,
                                             {"lines": lines, "import_config": config})
                imported.append(state["episode"])
        except Exception as exc:
            self.errorRequested.emit(f"Не удалось импортировать таблицу: {exc}")
            return False
        fields = ("project_kind", "episodes", "loaded_episodes", "episode_working_texts", "script_storage")
        updates = {field: candidate.get(field) for field in fields
                   if candidate.get(field) != self._session.data.get(field)}
        self._session.execute(UpdateProjectFileStateCommand(
            self._session.data, updates, f"Импорт таблицы: {len(imported)} серий"), "working_text")
        self._session.current_episode = imported[0]
        for episode in imported:
            self._episode_service.invalidate_episode(episode)
        self.projectDataChanged.emit("working_text")
        self.statusRequested.emit(f"Таблица импортирована · {self.summary}")
        return True

    @Slot()
    def reset(self):
        self._path = ""
        self._sheets, self._states = [], []
        self._index = 0
        self._encoding = self._delimiter = "auto"
        self._problem = "Выберите файл XLS, XLSX или CSV"
        self._columns_model.set_rows([])
        self._preview_model.set_rows([])
        self.changed.emit()
