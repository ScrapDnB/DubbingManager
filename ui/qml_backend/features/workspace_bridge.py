"""Main-window workflow, working script, and inspector state."""

from copy import deepcopy
import math
from pathlib import Path
import re

from PySide6.QtCore import QObject, Property, QUrl, Signal, Slot, Qt

from core.commands import UpdateProjectFileStateCommand
from services import get_actor_ids_for_character
from services.project_fps_service import project_fps
from ui.qml_backend.models import DictListModel


def format_timecode(seconds: float, fps: float) -> str:
    """Non-drop SMPTE timecode using the project's actual frame rate."""
    nominal = max(1, round(fps))
    frames = max(0, round(seconds * fps))
    seconds, frame = divmod(frames, nominal)
    minutes, second = divmod(seconds, 60)
    hour, minute = divmod(minutes, 60)
    return f"{hour:02}:{minute:02}:{second:02}:{frame:02}"


def parse_timecode(value: str, fps: float) -> float:
    match = re.fullmatch(r"(\d{2,}):(\d{2}):(\d{2}):(\d{2,3})", value.strip())
    if not match:
        raise ValueError("Введите таймкод ЧЧ:ММ:СС:КК")
    hour, minute, second, frame = map(int, match.groups())
    nominal = max(1, round(fps))
    if minute >= 60 or second >= 60 or frame >= nominal:
        raise ValueError(f"Проверьте минуты, секунды и кадры ({fps:g} fps)")
    return ((hour * 3600 + minute * 60 + second) * nominal + frame) / fps


class WorkspaceBridge(QObject):
    """Keep stable script selection and stage edits until explicit apply/navigation."""

    changed = Signal()
    draftChanged = Signal()
    workflowChanged = Signal()
    startupWorkflowChanged = Signal()
    seekRequested = Signal(int)
    statusRequested = Signal(str)
    errorRequested = Signal(str)
    projectDataChanged = Signal(str)

    def __init__(self, session, scripts, folders, casting, ui_state, parent=None):
        super().__init__(parent)
        self._session, self._scripts, self._folders = session, scripts, folders
        self._casting, self._ui_state = casting, ui_state
        self._workflow = self.startupWorkflow
        self._search = self._actor = self._character = self._selected_id = ""
        self._selected = {}
        self._draft = {}
        self._lines = []
        self._all_rows = []
        self._video = ""
        self._committing = False
        self._model = DictListModel({
            name: Qt.UserRole + index + 1 for index, name in enumerate((
                "lineId", "number", "start", "end", "inTime", "outTime",
                "character", "actor", "actorIds", "actorColor", "text",
            ))
        }, self)
        self._characters = DictListModel({
            "value": Qt.UserRole + 1, "label": Qt.UserRole + 2,
        }, self)
        session.currentEpisodeChanged.connect(self._episode_changed)
        session.projectReplaced.connect(self.reset)
        casting.selectedCharacterChanged.connect(self.changed)
        self.refresh()

    @Property(int, notify=workflowChanged)
    def workflow(self):
        return self._workflow

    @Property(int, notify=startupWorkflowChanged)
    def startupWorkflow(self):
        value = self._ui_state.intValue("main.startupWorkflow", 0)
        return value if value in (0, 1) else 0

    @Slot(int)
    def setStartupWorkflow(self, value):
        if value not in (0, 1) or value == self.startupWorkflow:
            return
        self._ui_state.setIntValue("main.startupWorkflow", value)
        self.startupWorkflowChanged.emit()

    @Slot(int)
    def setWorkflow(self, value):
        if value not in (0, 1) or value == self._workflow:
            return
        if not self.flush():
            return
        self._workflow = value
        self.workflowChanged.emit()

    @Property(QObject, constant=True)
    def model(self):
        return self._model

    @Property(QObject, constant=True)
    def characterModel(self):
        return self._characters

    @Property(str, notify=changed)
    def searchText(self):
        return self._search

    @Property(str, notify=changed)
    def actorFilter(self):
        return self._actor

    @Property(str, notify=changed)
    def characterFilter(self):
        return self._character

    @Property(int, notify=changed)
    def count(self):
        return self._model.rowCount()

    @Property(int, notify=changed)
    def totalCount(self):
        return len(self._all_rows)

    @Property(int, notify=changed)
    def characterCount(self):
        return len({row["character"] for row in self._all_rows})

    @Property(int, notify=changed)
    def unassignedCount(self):
        return len({row["character"] for row in self._all_rows if not row["actorIds"]})

    @Property(float, notify=changed)
    def fps(self):
        return project_fps(self._session.data)

    @Property(bool, notify=changed)
    def isAudiobook(self):
        return self._session.data.get("project_kind") == "audiobook"

    @Property(QUrl, notify=changed)
    def videoUrl(self):
        return QUrl.fromLocalFile(self._video) if self._video else QUrl()

    @Property(bool, notify=changed)
    def hasVideo(self):
        return bool(self._video)

    @Property("QVariantMap", notify=changed)
    def selected(self):
        return dict(self._selected)

    @Property("QVariantMap", notify=draftChanged)
    def draft(self):
        return dict(self._draft)

    @Property(bool, notify=draftChanged)
    def draftDirty(self):
        return bool(self._selected and any(
            self._draft.get(key) != self._selected.get(key)
            for key in ("text", "character", "inTime", "outTime")
        ))

    @Property(str, notify=draftChanged)
    def validationError(self):
        if not self._selected:
            return ""
        if not str(self._draft.get("character", "")).strip():
            return "Укажите персонажа"
        try:
            start = parse_timecode(self._draft.get("inTime", ""), self.fps)
            end = parse_timecode(self._draft.get("outTime", ""), self.fps)
            if not math.isfinite(start + end) or end <= start:
                return "Выход должен быть позже входа"
        except ValueError as error:
            return str(error)
        return ""

    @Property("QVariantMap", notify=changed)
    def characterInfo(self):
        name = self._casting.selectedCharacter
        rows = [row for row in self._all_rows if row["character"] == name]
        if not rows:
            return {}
        actor_ids = get_actor_ids_for_character(self._session.data, name, self._session.current_episode)
        actors = self._session.data.get("actors", {})
        local = self._session.data.get("episode_actor_map", {}).get(self._session.current_episode, {})
        return {
            "name": name, "lines": len(rows),
            "words": sum(len(row["text"].split()) for row in rows),
            "scope": "episode" if name in local else "global",
            "actors": [{"id": key, "name": actors.get(key, {}).get("name", key),
                        "color": actors.get(key, {}).get("color", "#888888")} for key in actor_ids],
            "firstText": rows[0]["text"], "firstTime": rows[0]["inTime"],
        }

    @Slot(str)
    def setSearchText(self, value):
        self._search = value
        self._filter_rows()

    @Slot(str)
    def setActorFilter(self, value):
        self._actor = value
        self._filter_rows()

    @Slot(str)
    def setCharacterFilter(self, value):
        self._character = value
        self._filter_rows()

    @Slot(str, str)
    def setDraftField(self, key, value):
        if key not in ("text", "character", "inTime", "outTime") or not self._selected:
            return
        self._draft[key] = value
        self.draftChanged.emit()

    @Slot()
    def discardDraft(self):
        self._draft = dict(self._selected)
        self.draftChanged.emit()

    @Slot(str, result=bool)
    def selectLine(self, line_id, *, position=None):
        if line_id == self._selected_id:
            self.seekRequested.emit(round((self._selected.get("start", 0) if position is None else position) * 1000))
            return True
        if not self.flush():
            return False
        row = next((row for row in self._all_rows if row["lineId"] == line_id), None)
        if row is None:
            return False
        self._selected_id = line_id
        self._selected = dict(row)
        self._draft = dict(row)
        self.changed.emit()
        self.draftChanged.emit()
        self.seekRequested.emit(round((row["start"] if position is None else position) * 1000))
        return True

    @Slot(str)
    def openCharacter(self, name):
        if not self.flush():
            return
        self.setWorkflow(1)
        self._character, self._actor, self._search = name, "", ""
        self._filter_rows()
        if self._model.rowCount():
            self.selectLine(self._model.get(0)["lineId"])

    @Slot(float, str)
    def openAtTime(self, seconds, character):
        if not math.isfinite(seconds) or seconds < 0 or not self.flush():
            return
        self.setWorkflow(1)
        self._character = self._actor = self._search = ""
        self._filter_rows()
        rows = [row for row in self._all_rows if not character or row["character"] == character]
        if rows:
            # Prefer a line covering the click; a nearby later start may still
            # belong to a different replica. In gaps choose the nearest interval.
            row = min(rows, key=lambda row: (
                0 if row["start"] <= seconds < row["end"] else
                min(abs(row["start"] - seconds), abs(row["end"] - seconds)),
                abs(row["start"] - seconds), row["number"],
            ))
            self.selectLine(row["lineId"], position=seconds)

    @Slot(result=bool)
    def flush(self):
        if self._committing or not self.draftDirty:
            return True
        if self.validationError:
            self.errorRequested.emit(self.validationError + ". Исправьте правку или нажмите «Отменить».")
            return False
        if self.isAudiobook:
            self.errorRequested.emit("Редактируйте книгу в модуле аудиокниг")
            return False
        episode = self._session.current_episode
        data = self._session.data
        key = "script_storage" if self._scripts.uses_dynamic_storage(data) else "episode_working_texts"
        candidate = {key: deepcopy(data.get(key, {}))}
        if key == "episode_working_texts" and episode not in candidate[key]:
            path = self._folders.resolve_project_path(data, data.get("episode_texts", {}).get(episode))
            try:
                if not path:
                    raise ValueError("Рабочий текст недоступен")
                candidate[key][episode] = self._scripts.load_episode_text(str(path))
                candidate["episode_texts"] = deepcopy(data.get("episode_texts", {}))
                candidate["episode_texts"].pop(episode, None)
            except (OSError, ValueError) as error:
                self.errorRequested.emit(f"Не удалось загрузить рабочий текст: {error}")
                return False
        line_id = self._selected_id
        editable = self._scripts.load_atomic_episode_lines(candidate, episode)
        if not any(str(line.get("working_id") if line.get("working_id") is not None else line.get("id")) == line_id for line in editable):
            self.errorRequested.emit("Реплика больше не существует. Отмените правку и выберите другую строку.")
            return False
        changed = False
        if self._draft["text"] != self._selected["text"]:
            changed |= self._scripts.update_line_text(candidate, episode, line_id, self._draft["text"])
        # Display aliases must stay linked to their original character when
        # only text/timing changes.
        if self._draft["character"].strip() != self._selected["character"]:
            changed |= self._scripts.update_line_character(candidate, episode, line_id, self._draft["character"].strip())
        # Preserve sub-frame timing when only text/character changed.
        if any(self._draft[key] != self._selected[key] for key in ("inTime", "outTime")):
            start = parse_timecode(self._draft["inTime"], self.fps)
            end = parse_timecode(self._draft["outTime"], self.fps)
            changed |= self._scripts.update_line_timing(candidate, episode, line_id, start, end)
        if not changed:
            self.discardDraft()
            return True
        if not self._session.ensure_edit_backup(f"episode_{episode}"):
            self.errorRequested.emit("Не удалось создать резервную копию перед правкой")
            return False
        self._committing = True
        try:
            self._session.execute(UpdateProjectFileStateCommand(
                data, candidate, f"Изменена реплика в серии {episode}"
            ), "working_text")
            self._draft = {}
            self.projectDataChanged.emit("working_text")
            self.refresh()
        finally:
            self._committing = False
        self.statusRequested.emit("Правка реплики сохранена в проекте")
        return True

    def refresh(self):
        episode = self._session.current_episode
        old_id = self._selected_id
        keep_draft = self.draftDirty and not self._committing
        self._lines = self._scripts.load_atomic_episode_lines(self._session.data, episode) if episode else []
        actors = self._session.data.get("actors", {})
        rows = []
        for index, line in enumerate(self._lines):
            name = str(line.get("char") or "-")
            actor_ids = get_actor_ids_for_character(self._session.data, name, episode)
            actor = actors.get(actor_ids[0], {}) if actor_ids else {}
            start, end = float(line.get("s", 0)), float(line.get("e", 0))
            stable_id = line.get("working_id")
            if stable_id is None:
                stable_id = line.get("id", index)
            rows.append({
                "lineId": str(stable_id), "number": index + 1,
                "start": start, "end": end,
                "inTime": format_timecode(start, self.fps),
                "outTime": format_timecode(end, self.fps),
                "character": name,
                "actor": ", ".join(actors.get(key, {}).get("name", key) for key in actor_ids) or "Не назначен",
                "actorIds": actor_ids,
                "actorColor": actor.get("color", "#888888") if len(actor_ids) == 1 else "#888888",
                "text": str(line.get("text") or ""),
            })
        self._all_rows = rows
        self._characters.set_rows([{"value": "", "label": "Все персонажи"}] + [
            {"value": name, "label": name} for name in sorted({row["character"] for row in rows})
        ])
        selected = next((row for row in rows if row["lineId"] == old_id), {})
        self._selected = dict(selected)
        if not selected:
            self._selected_id = ""
        if not keep_draft or not selected:
            self._draft = dict(selected)
            self.draftChanged.emit()
        raw = self._session.data.get("video_paths", {}).get(episode)
        path = self._folders.resolve_project_path(self._session.data, raw)
        self._video = str(path) if path and Path(path).is_file() else ""
        self._filter_rows()

    def _filter_rows(self):
        query = self._search.strip().casefold().replace("ё", "е")
        self._model.set_rows([
            row for row in self._all_rows
            if (not self._character or row["character"] == self._character)
            and (not self._actor or
                 (self._actor == "__unassigned__" and not row["actorIds"])
                 or self._actor in row["actorIds"])
            and (not query or query in " ".join((row["text"], row["character"], row["actor"])).casefold().replace("ё", "е"))
        ])
        self.changed.emit()

    def _episode_changed(self):
        self._selected_id = self._character = ""
        self._selected, self._draft = {}, {}
        self.refresh()

    def reset(self):
        self._search = self._actor = self._character = self._selected_id = ""
        self._selected, self._draft = {}, {}
        self.refresh()
