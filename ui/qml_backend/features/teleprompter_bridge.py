"""QML backend for the teleprompter workflow."""

from copy import deepcopy
from typing import Any, Dict, List, Optional

from PySide6.QtCore import QObject, Property, Signal, Slot, Qt

from config.constants import DEFAULT_PROMPTER_CONFIG
from core.commands import ReplaceMappingValueCommand
from services import ExportService, get_actor_ids_for_character
from services.episode_service import EpisodeService
from services.global_settings_service import GlobalSettingsService
from services.osc_worker import OSC_AVAILABLE, OscWorker
from services.script_text_service import ScriptTextService
from services.teleprompter_navigation_service import TeleprompterNavigationService
from ui.qml_backend.models import DictListModel
from ui.qml_backend.project_session import ProjectSession


GLOBAL_OSC_KEYS = {
    "osc_enabled",
    "port_in",
    "port_out",
    "sync_in",
    "sync_out",
    "reaper_offset_enabled",
    "reaper_offset_seconds",
}


def _format_time(seconds: Any, include_milliseconds: bool = False) -> str:
    try:
        total = max(0.0, float(seconds))
    except (TypeError, ValueError):
        total = 0.0
    whole = int(total)
    hours = whole // 3600
    minutes = (whole % 3600) // 60
    secs = whole % 60
    result = f"{hours}:{minutes:02d}:{secs:02d}"
    if include_milliseconds:
        result += f".{int((total - whole) * 1000):03d}"
    return result


class TeleprompterBridge(QObject):
    """Expose teleprompter state and actions without depending on the root UI."""

    changed = Signal()
    configChanged = Signal()
    positionChanged = Signal()
    oscChanged = Signal()
    projectDataChanged = Signal(str)
    statusRequested = Signal(str)
    errorRequested = Signal(str)

    def __init__(
        self,
        session: ProjectSession,
        episode_service: EpisodeService,
        script_text_service: ScriptTextService,
        global_settings_service: GlobalSettingsService,
        episodes_model: QObject,
        parent: Optional[QObject] = None,
    ) -> None:
        super().__init__(parent)
        self._session = session
        self._episode_service = episode_service
        self._script_text_service = script_text_service
        self._global_settings_service = global_settings_service
        self._episodes_model = episodes_model
        self._navigation = TeleprompterNavigationService()
        self._episode = ""
        self._selected_actor_ids: Optional[List[str]] = None
        self._time = 0.0
        self._current_index = -1
        self._osc_status = "OSC выключен"
        self._osc_worker: Optional[OscWorker] = None
        self._osc_client = None
        self._model = DictListModel({
            "rowIndex": Qt.UserRole + 1,
            "start": Qt.UserRole + 2,
            "end": Qt.UserRole + 3,
            "time": Qt.UserRole + 4,
            "character": Qt.UserRole + 5,
            "actor": Qt.UserRole + 6,
            "replicaText": Qt.UserRole + 7,
            "actorColor": Qt.UserRole + 8,
            "active": Qt.UserRole + 9,
            "sourceIds": Qt.UserRole + 10,
            "colorActive": Qt.UserRole + 11,
        }, self)
        self._actor_model = DictListModel({
            "actorId": Qt.UserRole + 1,
            "name": Qt.UserRole + 2,
            "color": Qt.UserRole + 3,
            "selected": Qt.UserRole + 4,
            "roleCount": Qt.UserRole + 5,
        }, self)
        self._preset_model = DictListModel({
            "presetIndex": Qt.UserRole + 1,
            "filled": Qt.UserRole + 2,
            "presetBackground": Qt.UserRole + 3,
            "presetForeground": Qt.UserRole + 4,
        }, self)
        self._refresh_presets()

    @Property(str, notify=changed)
    def episode(self) -> str:
        return self._episode

    @Property("QVariantMap", notify=configChanged)
    def config(self) -> Dict[str, Any]:
        return self._normalized_config(
            self._session.data.get("prompter_config")
        )

    @Property(float, notify=positionChanged)
    def time(self) -> float:
        return self._time

    @Property(str, notify=positionChanged)
    def timecode(self) -> str:
        return _format_time(self._time, True)

    @Property(int, notify=positionChanged)
    def currentIndex(self) -> int:
        return self._current_index

    @Property(str, notify=oscChanged)
    def oscStatus(self) -> str:
        return self._osc_status

    @Property(bool, constant=True)
    def oscAvailable(self) -> bool:
        return OSC_AVAILABLE

    @Property(list, notify=changed)
    def characterNames(self) -> List[str]:
        project_data = self._session.data
        names = set(str(name) for name in project_data.get("global_map", {}))
        for episode_map in project_data.get("episode_actor_map", {}).values():
            if isinstance(episode_map, dict):
                names.update(str(name) for name in episode_map)
        for payload in project_data.get("episode_working_texts", {}).values():
            if not isinstance(payload, dict):
                continue
            names.update(str(name) for name in payload.get("characters", {}))
            for line in payload.get("lines", []):
                if not isinstance(line, dict):
                    continue
                name = line.get("display_character") or line.get("character")
                if name:
                    names.add(str(name))
        return sorted((name for name in names if name), key=str.casefold)

    @Property(QObject, constant=True)
    def model(self) -> QObject:
        return self._model

    @Property(QObject, constant=True)
    def actorModel(self) -> QObject:
        return self._actor_model

    @Property(QObject, constant=True)
    def presetModel(self) -> QObject:
        return self._preset_model

    @Property(QObject, constant=True)
    def episodesModel(self) -> QObject:
        return self._episodes_model

    @Slot(str, result=bool)
    def prepare(self, episode: str = "") -> bool:
        target = str(
            episode
            or self._session.current_episode
            or self._first_episode()
        )
        if not target or target not in self._session.data.get("episodes", {}):
            self.errorRequested.emit("Для телесуфлёра нужна серия")
            return False
        self._episode = target
        self._time = 0.0
        self._current_index = -1
        self.refresh()
        if self.config.get("osc_enabled"):
            self._start_osc()
        self.changed.emit()
        return True

    @Slot()
    def close(self) -> None:
        self._stop_osc()

    @Slot(str)
    def setEpisode(self, episode: str) -> None:
        episode = str(episode or "")
        if (
            not episode
            or episode == self._episode
            or episode not in self._session.data.get("episodes", {})
        ):
            return
        self._episode = episode
        self._time = 0.0
        self._current_index = -1
        self.refresh()
        self.changed.emit()

    @Slot()
    def refreshCast(self) -> None:
        if not self._episode:
            return
        self._episode_service.invalidate_episode(self._episode)
        self.refresh()
        self.statusRequested.emit("Каст телесуфлёра обновлён")

    @Slot(str, bool)
    def setActorSelected(self, actor_id: str, selected: bool) -> None:
        all_ids = set(self._session.data.get("actors", {}))
        selected_ids = (
            set(all_ids)
            if self._selected_actor_ids is None
            else set(self._selected_actor_ids)
        )
        if selected:
            selected_ids.add(str(actor_id))
        else:
            selected_ids.discard(str(actor_id))
        self._selected_actor_ids = (
            None if selected_ids == all_ids else sorted(selected_ids)
        )
        self.refresh()

    @Slot(bool)
    def selectAllActors(self, selected: bool) -> None:
        self._selected_actor_ids = None if selected else []
        self.refresh()

    @Slot(str, "QVariant")
    def setConfigValue(self, key: str, value: Any) -> None:
        if key in GLOBAL_OSC_KEYS:
            return
        config = self.config
        normalized = self._normalize_option(key, value)
        if normalized is None:
            return
        if key.startswith("colors."):
            color_key = key.split(".", 1)[1]
            if config["colors"].get(color_key) == normalized:
                return
            config["colors"][color_key] = normalized
        else:
            if config.get(key) == normalized:
                return
            config[key] = normalized
        self._session.execute(ReplaceMappingValueCommand(
            self._session.data,
            "prompter_config",
            config,
            "Изменены настройки телесуфлёра",
        ), "teleprompter_config")
        self.configChanged.emit()
    @Slot(float)
    def jumpTo(self, seconds: float) -> None:
        self._set_time(max(0.0, float(seconds)))
        config = self.config
        if not (
            config.get("osc_enabled")
            and config.get("sync_out")
            and self._osc_client
        ):
            return
        send_time = self._time
        if config.get("reaper_offset_enabled"):
            send_time += float(config.get("reaper_offset_seconds", -2.0))
        try:
            self._osc_client.send_message("/time", send_time)
            self._osc_client.send_message("/track/0/pos", send_time)
        except Exception as exc:
            self._osc_status = f"Ошибка отправки OSC: {exc}"
            self.oscChanged.emit()

    @Slot(int)
    def navigate(self, direction: int) -> None:
        rows = self._model.rows()
        active = [index for index, row in enumerate(rows) if row.get("active")]
        if not active:
            return
        nearest = min(
            active,
            key=lambda index: abs(float(rows[index]["start"]) - self._time),
        )
        position = active.index(nearest)
        target = active[(position + (1 if direction >= 0 else -1)) % len(active)]
        self.jumpTo(float(rows[target]["start"]))

    @Slot("QVariantList", str, str, result=bool)
    def editReplica(
        self,
        source_ids: List[Any],
        character: str,
        text: str,
    ) -> bool:
        payload = deepcopy(
            self._session.data.get("episode_working_texts", {}).get(self._episode)
        )
        ids = list(source_ids or [])
        character = str(character or "").strip()
        if not isinstance(payload, dict) or not ids or not character:
            self.errorRequested.emit("Реплика не связана с рабочим текстом")
            return False
        temp_data = {"episode_working_texts": {self._episode: payload}}
        changed = False
        for line_id in ids:
            changed = self._script_text_service.update_line_character(
                temp_data, self._episode, line_id, character
            ) or changed
        parts = self._navigation.split_merged_text(text.strip(), ids)
        if not parts and len(ids) > 1:
            parts = [part.strip() for part in text.splitlines() if part.strip()]
        if len(parts) != len(ids):
            parts = [text] if len(ids) == 1 else []
        for line_id, part in zip(ids, parts):
            changed = self._script_text_service.update_line_text(
                temp_data, self._episode, line_id, part
            ) or changed
        if not changed:
            return False
        if not self._session.ensure_edit_backup(f"episode_{self._episode}"):
            self.errorRequested.emit(
                "Не удалось создать резервную копию перед правкой"
            )
            return False
        self._replace_payload(payload, "Изменена реплика телесуфлёра")
        return True

    @Slot("QVariantList", str, str, str, result=bool)
    def splitReplica(
        self,
        source_ids: List[Any],
        remaining_text: str,
        split_text: str,
        split_character: str,
    ) -> bool:
        payload = deepcopy(
            self._session.data.get("episode_working_texts", {}).get(self._episode)
        )
        ids = list(source_ids or [])
        if not isinstance(payload, dict) or len(ids) != 1:
            self.errorRequested.emit("Разделить можно только одну исходную реплику")
            return False
        temp_data = {"episode_working_texts": {self._episode: payload}}
        if not self._script_text_service.split_line_to_character(
            temp_data,
            self._episode,
            ids[0],
            remaining_text,
            split_text,
            split_character,
        ):
            return False
        if not self._session.ensure_edit_backup(f"episode_{self._episode}"):
            self.errorRequested.emit(
                "Не удалось создать резервную копию перед правкой"
            )
            return False
        self._replace_payload(payload, "Разделена реплика телесуфлёра")
        return True

    @Slot(int)
    def applyOrSavePreset(self, index: int) -> None:
        presets = self._global_settings_service.get_prompter_color_presets()
        if not 0 <= index < len(presets):
            return
        if not presets[index]:
            self.savePreset(index)
            return
        config = self.config
        config["colors"] = deepcopy(presets[index])
        self._session.execute(ReplaceMappingValueCommand(
            self._session.data,
            "prompter_config",
            config,
            f"Применён цветовой пресет телесуфлёра {index + 1}",
        ), "teleprompter_config")
        self.configChanged.emit()

    @Slot(int)
    def savePreset(self, index: int) -> None:
        self._global_settings_service.set_prompter_color_preset(
            index, self.config.get("colors", {})
        )
        self._global_settings_service.save_settings(
            self._global_settings_service.settings
        )
        self._refresh_presets()

    @Slot(int)
    def clearPreset(self, index: int) -> None:
        self._global_settings_service.clear_prompter_color_preset(index)
        self._global_settings_service.save_settings(
            self._global_settings_service.settings
        )
        self._refresh_presets()

    def refresh_if_active(self) -> None:
        if self._episode:
            self.refresh()

    def notify_config_changed(self) -> None:
        """Refresh QML bindings after project-wide undo or redo."""
        self.configChanged.emit()

    @Slot()
    def notify_global_config_changed(self) -> None:
        """Apply globally owned OSC settings to an open teleprompter."""
        self.configChanged.emit()
        if not self._episode:
            return
        if self.config.get("osc_enabled"):
            self._start_osc()
        else:
            self._stop_osc()

    def refresh(self) -> None:
        project_data = self._session.data
        if self._episode not in project_data.get("episodes", {}):
            self._model.set_rows([])
            self._actor_model.set_rows([])
            self._current_index = -1
            self.changed.emit()
            self.positionChanged.emit()
            return
        lines = sorted(
            self._script_text_service.load_episode_lines(
                project_data, self._episode
            ),
            key=lambda line: float(line.get("s", 0.0)),
        )
        processed = ExportService(project_data).process_merge_logic(
            lines,
            project_data.get("replica_merge_config", {}),
        )
        actors = project_data.get("actors", {})
        all_actor_ids = set(actors)
        selected_actor_ids = (
            all_actor_ids
            if self._selected_actor_ids is None
            else set(self._selected_actor_ids)
        )
        rows = []
        actor_role_counts: Dict[str, int] = {actor_id: 0 for actor_id in actors}
        for index, replica in enumerate(processed):
            character = str(replica.get("char") or "")
            actor_ids = get_actor_ids_for_character(
                project_data, character, self._episode
            )
            selected_for_replica = [
                actor_id for actor_id in actor_ids
                if actor_id in selected_actor_ids
            ]
            color_actor_id = (
                selected_for_replica[0]
                if len(selected_for_replica) == 1 else ""
            )
            color_actor = actors.get(color_actor_id, {})
            for actor_id in actor_ids:
                if actor_id in actor_role_counts:
                    actor_role_counts[actor_id] += 1
            source_ids = (
                [replica.get("working_id", replica.get("id", index))]
                if replica.get("_working_text")
                else replica.get("source_ids", [replica.get("id", index)])
            )
            start = float(replica.get("s", 0.0) or 0.0)
            end = float(replica.get("e", start) or start)
            rows.append({
                "rowIndex": index,
                "start": start,
                "end": end,
                "time": _format_time(start),
                "character": character or "-",
                "actor": " / ".join(
                    str(actors.get(actor_id, {}).get("name") or actor_id)
                    for actor_id in actor_ids
                ) or "-",
                "replicaText": str(replica.get("text") or ""),
                "actorColor": str(color_actor.get("color") or "#FFFFFF"),
                "active": bool(selected_for_replica),
                "colorActive": bool(color_actor_id),
                "sourceIds": list(source_ids),
            })
        self._model.set_rows(rows)
        self._actor_model.set_rows([
            {
                "actorId": actor_id,
                "name": str(actor.get("name") or actor_id),
                "color": str(actor.get("color") or "#FFFFFF"),
                "selected": actor_id in selected_actor_ids,
                "roleCount": actor_role_counts.get(actor_id, 0),
            }
            for actor_id, actor in sorted(
                actors.items(),
                key=lambda item: str(item[1].get("name", item[0])).casefold(),
            )
        ])
        self._refresh_presets()
        self._update_index()
        self.changed.emit()
        self.positionChanged.emit()

    def reset(self) -> None:
        self.close()
        self._episode = ""
        self._selected_actor_ids = None
        self._time = 0.0
        self._current_index = -1
        self._model.set_rows([])
        self._actor_model.set_rows([])
        self.changed.emit()
        self.positionChanged.emit()

    def _normalized_config(self, value: Any) -> Dict[str, Any]:
        config = deepcopy(DEFAULT_PROMPTER_CONFIG)
        defaults = self._global_settings_service.get_default_prompter_config()
        for source in (defaults, value):
            if not isinstance(source, dict):
                continue
            config.update({
                key: deepcopy(item)
                for key, item in source.items()
                if key != "colors"
            })
            if isinstance(source.get("colors"), dict):
                config["colors"].update(source["colors"])
        for key in GLOBAL_OSC_KEYS:
            config[key] = deepcopy(defaults.get(key, DEFAULT_PROMPTER_CONFIG[key]))
        return config

    def _normalize_option(self, key: str, value: Any) -> Any:
        if key in {
            "is_mirrored", "show_header", "osc_enabled", "sync_in",
            "sync_out", "reaper_offset_enabled", "use_cocoa_float_window",
        }:
            return bool(value)
        limits = {
            "f_tc": (10, 150),
            "f_char": (10, 150),
            "f_actor": (10, 150),
            "f_text": (10, 300),
            "port_in": (1, 65535),
            "port_out": (1, 65535),
            "scroll_smoothness_slider": (0, 100),
        }
        if key in limits:
            try:
                low, high = limits[key]
                return max(low, min(high, int(value)))
            except (TypeError, ValueError):
                return None
        if key == "focus_ratio":
            try:
                return max(0.1, min(0.9, float(value)))
            except (TypeError, ValueError):
                return None
        if key == "reaper_offset_seconds":
            try:
                return max(-60.0, min(60.0, float(value)))
            except (TypeError, ValueError):
                return None
        if key.startswith("colors."):
            color_key = key.split(".", 1)[1]
            if color_key not in DEFAULT_PROMPTER_CONFIG["colors"]:
                return None
            color = str(value or "").strip()
            return color if color else None
        if key in {"key_prev", "key_next"}:
            return str(value or "")
        return None

    def _refresh_presets(self) -> None:
        self._preset_model.set_rows([
            {
                "presetIndex": index,
                "filled": bool(preset),
                "presetBackground": str((preset or {}).get("bg", "#000000")),
                "presetForeground": str(
                    (preset or {}).get("active_text", "#FFFFFF")
                ),
            }
            for index, preset in enumerate(
                self._global_settings_service.get_prompter_color_presets()
            )
        ])
        self.changed.emit()

    def _set_time(self, seconds: float) -> None:
        self._time = max(0.0, float(seconds))
        self._update_index()
        self.positionChanged.emit()

    def _update_index(self) -> None:
        rows = self._model.rows()
        if not rows:
            self._current_index = -1
            return
        current = 0
        for index, row in enumerate(rows):
            if self._time < float(row["start"]):
                break
            current = index
            if self._time <= float(row["end"]):
                break
        self._current_index = current

    def _replace_payload(
        self,
        payload: Dict[str, Any],
        description: str,
    ) -> None:
        self._session.execute(ReplaceMappingValueCommand(
            self._session.data.setdefault("episode_working_texts", {}),
            self._episode,
            payload,
            description,
        ), "working_text")
        self._episode_service.invalidate_episode(self._episode)
        self.refresh()
        self.projectDataChanged.emit("working_text")
        self.statusRequested.emit(description)

    def _first_episode(self) -> str:
        episodes = self._session.data.get("episodes", {})
        if not episodes:
            return ""
        def sort_key(value: str) -> tuple[int, str]:
            try:
                return (0, f"{int(value):08d}")
            except (TypeError, ValueError):
                return (1, str(value).lower())
        return str(sorted(episodes, key=sort_key)[0])

    def _start_osc(self) -> None:
        self._stop_osc()
        if not OSC_AVAILABLE:
            self._osc_status = "OSC недоступен: установите python-osc"
            self.oscChanged.emit()
            return
        config = self.config
        try:
            from pythonosc.udp_client import SimpleUDPClient

            worker = OscWorker(int(config["port_in"]), self)
            worker.time_changed.connect(self._on_osc_time)
            worker.navigation_requested.connect(self._on_osc_navigation)
            worker.start()
            self._osc_worker = worker
            self._osc_client = SimpleUDPClient(
                "127.0.0.1", int(config["port_out"])
            )
            self._osc_status = (
                f"OSC: {config['port_in']} -> {config['port_out']}"
            )
        except Exception as exc:
            self._osc_status = f"Ошибка OSC: {exc}"
            self._osc_worker = None
            self._osc_client = None
        self.oscChanged.emit()

    def _stop_osc(self) -> None:
        if self._osc_worker is not None:
            self._osc_worker.stop()
            self._osc_worker.deleteLater()
        self._osc_worker = None
        self._osc_client = None
        self._osc_status = "OSC выключен"
        self.oscChanged.emit()

    @Slot(float)
    def _on_osc_time(self, seconds: float) -> None:
        if self.config.get("sync_in"):
            self._set_time(seconds)

    @Slot(str)
    def _on_osc_navigation(self, direction: str) -> None:
        self.navigate(1 if direction == "next" else -1)
