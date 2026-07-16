"""QML backend for synchronized video and replica preview."""

from pathlib import Path
from typing import Any, Dict, Optional

from PySide6.QtCore import QObject, Property, QUrl, Signal, Slot, Qt

from services import get_actor_ids_for_character
from services.project_folder_service import ProjectFolderService
from services.script_text_service import ScriptTextService
from ui.qml_backend.models import DictListModel
from ui.qml_backend.project_session import ProjectSession


def _format_time(seconds: Any) -> str:
    try:
        total = max(0, float(seconds))
    except (TypeError, ValueError):
        total = 0.0
    minutes = int(total // 60)
    secs = total - minutes * 60
    return f"{minutes:02d}:{secs:05.2f}"


class VideoBridge(QObject):
    """Own video-preview state and models used by the QML dialog."""

    changed = Signal()
    errorRequested = Signal(str)

    def __init__(
        self,
        session: ProjectSession,
        project_folder_service: ProjectFolderService,
        script_text_service: ScriptTextService,
        parent: Optional[QObject] = None,
    ) -> None:
        super().__init__(parent)
        self._session = session
        self._project_folder_service = project_folder_service
        self._script_text_service = script_text_service
        self._episode = ""
        self._character = ""
        self._video_path = ""
        self._model = DictListModel({
            "lineId": Qt.UserRole + 1,
            "startMs": Qt.UserRole + 2,
            "endMs": Qt.UserRole + 3,
            "time": Qt.UserRole + 4,
            "character": Qt.UserRole + 5,
            "actor": Qt.UserRole + 6,
            "text": Qt.UserRole + 7,
            "actorColor": Qt.UserRole + 8,
        }, self)
        self._character_model = DictListModel({
            "value": Qt.UserRole + 1,
            "label": Qt.UserRole + 2,
            "count": Qt.UserRole + 3,
        }, self)

    @Property(str, notify=changed)
    def episode(self) -> str:
        return self._episode

    @Property(str, notify=changed)
    def character(self) -> str:
        return self._character

    @Property(bool, notify=changed)
    def hasVideo(self) -> bool:
        return bool(self._video_path and Path(self._video_path).is_file())

    @Property(QUrl, notify=changed)
    def videoUrl(self) -> QUrl:
        if not self.hasVideo:
            return QUrl()
        return QUrl.fromLocalFile(self._video_path)

    @Property(str, notify=changed)
    def videoName(self) -> str:
        return Path(self._video_path).name if self.hasVideo else ""

    @Property(int, notify=changed)
    def count(self) -> int:
        return self._model.rowCount()

    @Property(QObject, constant=True)
    def model(self) -> QObject:
        return self._model

    @Property(QObject, constant=True)
    def characterModel(self) -> QObject:
        return self._character_model

    @Slot(str, result=bool)
    def prepare(self, character: str) -> bool:
        episode = self._session.current_episode
        if not episode:
            self.errorRequested.emit("Выберите серию для просмотра реплик")
            return False
        lines = self._get_lines(episode)
        if not lines:
            self.errorRequested.emit("В выбранной серии нет рабочего текста")
            return False

        characters: Dict[str, int] = {}
        for line in lines:
            name = str(line.get("char") or "-")
            characters[name] = characters.get(name, 0) + 1
        requested_character = str(character or "")
        if requested_character not in characters:
            requested_character = ""

        raw_path = self._session.data.get("video_paths", {}).get(episode)
        resolved_path = self._project_folder_service.resolve_project_path(
            self._session.data,
            raw_path,
        )
        self._episode = episode
        self._character = requested_character
        self._video_path = (
            str(resolved_path)
            if resolved_path and Path(resolved_path).is_file()
            else ""
        )
        self._character_model.set_rows([
            {"value": "", "label": "Все персонажи", "count": len(lines)},
            *[
                {"value": name, "label": name, "count": count}
                for name, count in sorted(
                    characters.items(),
                    key=lambda item: item[0].casefold(),
                )
            ],
        ])
        self.refresh_rows()
        return True

    @Slot(str)
    def setCharacter(self, character: str) -> None:
        character = str(character or "")
        available = {row["value"] for row in self._character_model.rows()}
        if character not in available or character == self._character:
            return
        self._character = character
        self.refresh_rows()

    def refresh_if_active(self) -> None:
        if self._episode:
            self.refresh_rows()

    def refresh_rows(self) -> None:
        if not self._episode:
            self._model.set_rows([])
            self.changed.emit()
            return

        actors = self._session.data.get("actors", {})
        rows = []
        for index, line in enumerate(self._get_lines(self._episode)):
            character = str(line.get("char") or "-")
            if self._character and character != self._character:
                continue
            try:
                start = max(0.0, float(line.get("s", 0.0)))
            except (TypeError, ValueError):
                start = 0.0
            try:
                end = max(start, float(line.get("e", start)))
            except (TypeError, ValueError):
                end = start
            actor_ids = get_actor_ids_for_character(
                self._session.data,
                character,
                self._episode,
            )
            actor = actors.get(actor_ids[0], {}) if actor_ids else {}
            actor_name = (
                "Несколько актёров"
                if len(actor_ids) > 1
                else str(actor.get("name") or "-")
            )
            start_ms = round(start * 1000)
            rows.append({
                "lineId": str(line.get("id", index)),
                "startMs": start_ms,
                "endMs": max(round(end * 1000), start_ms + 1),
                "time": _format_time(start),
                "character": character,
                "actor": actor_name,
                "text": str(line.get("text") or ""),
                "actorColor": (
                    str(actor.get("color") or "#4F81BD")
                    if len(actor_ids) == 1
                    else "transparent"
                ),
            })
        self._model.set_rows(rows)
        self.changed.emit()

    def reset(self) -> None:
        self._episode = ""
        self._character = ""
        self._video_path = ""
        self._model.set_rows([])
        self._character_model.set_rows([])
        self.changed.emit()

    def _get_lines(self, episode: str):
        return self._script_text_service.load_episode_lines(
            self._session.data,
            str(episode),
        )
