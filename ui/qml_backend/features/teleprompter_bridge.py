"""QML backend for the teleprompter workflow."""

from copy import deepcopy
from time import monotonic
from typing import Any, Dict, List, Optional

from PySide6.QtCore import QObject, Property, QTimer, Signal, Slot, Qt

from config.constants import (
    DEFAULT_PROMPTER_CONFIG,
    PROMPTER_FONT_BOLD_KEYS,
    PROMPTER_FONT_KEYS,
    PROMPTER_LAYOUT_TYPES,
)
from core.commands import ReplaceMappingValueCommand, UpdateProjectFileStateCommand
from services import ExportService, get_actor_ids_for_character
from services.episode_service import EpisodeService
from services.global_settings_service import GlobalSettingsService
from services.osc_worker import OSC_AVAILABLE, OscWorker
from services.script_text_service import ScriptTextService
from services.teleprompter_navigation_service import TeleprompterNavigationService
from services.layout_template_service import layout_template_rows
from ui.qml_backend.models import DictListModel
from ui.qml_backend.project_session import ProjectSession


REAPER_ACTIVITY_TIMEOUT_SECONDS = 3.0
LOCAL_REAPER_SETTLE_SECONDS = 0.5
REAPER_TIME_ACK_TOLERANCE_SECONDS = 0.25


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
        self._position_origin = "internal"
        self._osc_status = "OSC выключен"
        self._osc_worker: Optional[OscWorker] = None
        self._osc_client = None
        self._last_osc_activity: Optional[float] = None
        self._last_reaper_time: Optional[float] = None
        self._reaper_playing = False
        self._debug_simulation_active = False
        self._pending_reaper_time: Optional[tuple[float, float]] = None
        self._osc_runtime_config: Optional[tuple[int, int]] = None
        self._reaper_connection_state = "disabled"
        self._osc_activity_timer = QTimer(self)
        self._osc_activity_timer.setInterval(500)
        self._osc_activity_timer.timeout.connect(
            self._refresh_reaper_connection_state
        )
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
            "timingGuides": Qt.UserRole + 12,
            "endTime": Qt.UserRole + 13,
            "editText": Qt.UserRole + 14,
            "parallelExpandable": Qt.UserRole + 15,
            "subReplicas": Qt.UserRole + 16,
            "replicaKey": Qt.UserRole + 17,
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
        return self._normalized_config(None)

    @Property(float, notify=positionChanged)
    def time(self) -> float:
        return self._time

    @Property(str, notify=positionChanged)
    def timecode(self) -> str:
        return _format_time(self._time, True)

    @Property(int, notify=positionChanged)
    def currentIndex(self) -> int:
        return self._current_index

    @Property(str, notify=positionChanged)
    def positionOrigin(self) -> str:
        return self._position_origin

    @Property(bool, notify=oscChanged)
    def debugSimulationActive(self) -> bool:
        return self._debug_simulation_active

    @Property(str, notify=oscChanged)
    def oscStatus(self) -> str:
        return self._osc_status

    @Property(str, notify=oscChanged)
    def reaperConnectionState(self) -> str:
        return self._reaper_connection_state

    @Property(str, notify=oscChanged)
    def reaperConnectionText(self) -> str:
        labels = {
            "active": "REAPER: синхронизация активна",
            "waiting": "REAPER: ожидание сигнала",
            "lost": "REAPER: сигнал потерян",
            "error": "REAPER: ошибка OSC",
            "unavailable": "REAPER: OSC недоступен",
            "disabled": "REAPER: синхронизация выключена",
        }
        return labels[self._reaper_connection_state]

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
        if (
            project_data.get("project_kind") == "audiobook"
            or self._script_text_service.uses_dynamic_storage(project_data)
        ):
            for episode in project_data.get("episodes", {}):
                for line in self._script_text_service.load_atomic_episode_lines(
                    project_data, str(episode)
                ):
                    name = line.get("char")
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
        self._position_origin = "internal"
        self.refresh()
        if self.config.get("osc_enabled"):
            self._start_osc()
        self.changed.emit()
        return True

    @Slot()
    def close(self) -> None:
        self._debug_simulation_active = False
        self._stop_osc()

    @Slot(bool)
    def debugSetSimulationActive(self, active: bool) -> None:
        """Enable a deterministic REAPER input simulator for QML diagnostics."""
        active = bool(active) and bool(self.config.get("page_debug_overlay"))
        if self._debug_simulation_active == active:
            return
        self._debug_simulation_active = active
        if not active:
            self._reaper_playing = False
        self.oscChanged.emit()

    @Slot(float)
    def debugSetReaperTime(self, seconds: float) -> None:
        """Inject one simulated REAPER position through the normal UI path."""
        if not (
            self._debug_simulation_active
            and self.config.get("page_debug_overlay")
        ):
            return
        seconds = max(0.0, float(seconds))
        self._last_reaper_time = seconds
        self._reaper_playing = True
        self._set_time(seconds, "reaper")

    @Slot()
    def restartOsc(self) -> None:
        """Reconnect the OSC transport without resetting the reader state."""
        if self._episode and self.config.get("osc_enabled"):
            self._start_osc()

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
        self._position_origin = "internal"
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
        if key.startswith("colors."):
            self._set_global_color_value(key, value)
            return
        self._set_global_layout_value(key, value)

    def _set_global_color_value(self, key: str, value: Any) -> None:
        normalized = self._normalize_option(key, value)
        if normalized is None:
            return
        color_key = key.split(".", 1)[1]
        config = self._global_settings_service.get_default_prompter_config()
        colors = deepcopy(config.get("colors", {}))
        if colors.get(color_key) == normalized:
            return
        colors[color_key] = normalized
        config["colors"] = colors
        self._save_global_prompter_config(
            config,
            "Не удалось сохранить цвета телесуфлёра",
        )

    def _save_global_prompter_config(
        self,
        config: Dict[str, Any],
        error_message: str,
        *,
        sync_layout_template: bool = False,
    ) -> bool:
        previous = deepcopy(self._global_settings_service.settings)
        self._global_settings_service.set_default_prompter_config(config)
        if sync_layout_template:
            suffix = {
                "Сценарий 1": "scenario1",
                "Сценарий 2": "scenario2",
                "Сценарий 3": "scenario3",
            }.get(str(config.get("layout_type")))
            if suffix:
                self._global_settings_service.set_active_layout_template_id(
                    "teleprompter", f"builtin.teleprompter.{suffix}"
                )
        if not self._global_settings_service.save_settings(
            self._global_settings_service.settings
        ):
            self._global_settings_service.settings = previous
            self.errorRequested.emit(error_message)
            return False
        self.configChanged.emit()
        if self._episode:
            self.refresh()
        return True

    def _set_global_layout_value(self, key: str, value: Any) -> None:
        config = self._global_settings_service.get_default_prompter_config()
        profiles = deepcopy(config.get("layout_font_sizes", {}))
        bold_profiles = deepcopy(config.get("layout_font_bold", {}))
        layout_type = str(config.get("layout_type", "Сценарий 1"))

        if key == "layout_type":
            normalized = str(value or "")
            if normalized not in PROMPTER_LAYOUT_TYPES:
                return
            if layout_type == normalized:
                return
            config["layout_type"] = normalized
        elif key in PROMPTER_FONT_KEYS:
            normalized = self._normalize_option(key, value)
            if normalized is None:
                return
            profile = deepcopy(profiles.get(layout_type, {}))
            if profile.get(key) == normalized:
                return
            profile[key] = normalized
            profiles[layout_type] = profile
            config["layout_font_sizes"] = profiles
            config[key] = normalized
        elif key in PROMPTER_FONT_BOLD_KEYS:
            normalized = self._normalize_option(key, value)
            if normalized is None:
                return
            profile = deepcopy(bold_profiles.get(layout_type, {}))
            if profile.get(key) == normalized:
                return
            profile[key] = normalized
            bold_profiles[layout_type] = profile
            config["layout_font_bold"] = bold_profiles
            config[key] = normalized
        else:
            normalized = self._normalize_option(key, value)
            if normalized is None or config.get(key) == normalized:
                return
            config[key] = normalized

        self._save_global_prompter_config(
            config,
            "Не удалось сохранить настройки разметки телесуфлёра",
            sync_layout_template=key == "layout_type",
        )

    @Slot(float)
    def jumpTo(self, seconds: float) -> None:
        self._jump_to(seconds, "local", send_sync=True)

    @Slot(int)
    def jumpToIndex(self, index: int) -> None:
        """Jump to an exact row even when replica time ranges overlap."""
        self._jump_to_index(index, "local", send_sync=True)

    @Slot(int)
    def navigate(self, direction: int) -> None:
        self._navigate(direction, "local", send_sync=True)

    @Slot(result=int)
    def currentIndexNow(self) -> int:
        """Return the current index without QML property-binding latency."""
        return self._current_index

    def _jump_to(
        self,
        seconds: float,
        origin: str,
        send_sync: bool,
    ) -> None:
        self._set_time(max(0.0, float(seconds)), origin)
        self._send_time_to_reaper(send_sync)

    def _jump_to_index(
        self,
        index: int,
        origin: str,
        send_sync: bool,
    ) -> None:
        rows = self._model.rows()
        index = int(index)
        if index < 0 or index >= len(rows) or not rows[index].get("active"):
            return
        self._time = max(0.0, float(rows[index]["start"]))
        self._position_origin = origin
        self._current_index = index
        self.positionChanged.emit()
        self._send_time_to_reaper(send_sync)

    def _send_time_to_reaper(self, send_sync: bool) -> None:
        config = self.config
        if not (
            send_sync
            and config.get("osc_enabled")
            and config.get("sync_out")
            and self._osc_client
        ):
            return
        send_time = self._reaper_time(self._time, config)
        try:
            self._osc_client.send_message("/time", send_time)
            self._osc_client.send_message("/track/0/pos", send_time)
            self._pending_reaper_time = (
                send_time,
                monotonic() + LOCAL_REAPER_SETTLE_SECONDS,
            )
        except Exception as exc:
            self._osc_status = f"Ошибка отправки OSC: {exc}"
            self.oscChanged.emit()

    @staticmethod
    def _uses_reaper_output_offset(config: Dict[str, Any]) -> bool:
        return bool(
            config.get("reaper_offset_enabled") and config.get("sync_out")
        )

    def _reaper_time(self, seconds: float, config: Dict[str, Any]) -> float:
        if not self._uses_reaper_output_offset(config):
            return seconds
        return seconds + float(config.get("reaper_offset_seconds", -2.0))

    def _navigate(
        self,
        direction: int,
        origin: str,
        send_sync: bool,
    ) -> None:
        rows = self._model.rows()
        active = [index for index, row in enumerate(rows) if row.get("active")]
        if not active:
            return
        if direction >= 0:
            target = next(
                (index for index in active if index > self._current_index),
                active[0],
            )
        else:
            target = next(
                (index for index in reversed(active) if index < self._current_index),
                active[-1],
            )
        self._jump_to_index(target, origin, send_sync)

    def _should_apply_reaper_time(self, seconds: float) -> bool:
        pending = self._pending_reaper_time
        if pending is None:
            return True
        expected_time, expires_at = pending
        if monotonic() >= expires_at:
            self._pending_reaper_time = None
            return True
        if abs(float(seconds) - expected_time) <= REAPER_TIME_ACK_TOLERANCE_SECONDS:
            self._pending_reaper_time = None
        return False

    def _osc_config_signature(self) -> Optional[tuple[int, int]]:
        config = self.config
        if not config.get("osc_enabled"):
            return None
        return int(config["port_in"]), int(config["port_out"])

    @Slot("QVariantList", str, str, result=bool)
    def editReplica(
        self,
        source_ids: List[Any],
        character: str,
        text: str,
    ) -> bool:
        is_audiobook = self._session.data.get("project_kind") == "audiobook"
        is_dynamic = self._script_text_service.uses_dynamic_storage(
            self._session.data
        )
        temp_data = deepcopy(self._session.data) if (is_audiobook or is_dynamic) else {
            "episode_working_texts": deepcopy(
                self._session.data.get("episode_working_texts", {})
            )
        }
        payload = self._script_text_service.get_episode_payload(
            temp_data, self._episode
        )
        ids = list(source_ids or [])
        character = str(character or "").strip()
        if not isinstance(payload, dict) or not ids or not character:
            self.errorRequested.emit("Реплика не связана с рабочим текстом")
            return False
        parts = [text]
        if len(ids) > 1:
            parts = self._navigation.split_merged_text(text.strip(), ids)
            if not parts:
                line_parts = [
                    part.strip() for part in text.splitlines() if part.strip()
                ]
                if len(line_parts) == len(ids):
                    parts = line_parts
            if not parts:
                self.errorRequested.emit(
                    "Текст объединённой реплики должен содержать по одной "
                    "части на исходную строку, разделённой переносом, « / » "
                    "или « // »"
                )
                return False
        if not is_audiobook and not is_dynamic:
            temp_data = {"episode_working_texts": {self._episode: payload}}
        changed = False
        for line_id in ids:
            changed = self._script_text_service.update_line_character(
                temp_data, self._episode, line_id, character
            ) or changed
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
        self._replace_payload(
            payload,
            "Изменена реплика телесуфлёра",
            temp_data.get("audiobook_document") if is_audiobook else None,
        )
        return True

    @Slot("QVariantList", str, str, str, result=bool)
    def splitReplica(
        self,
        source_ids: List[Any],
        remaining_text: str,
        split_text: str,
        split_character: str,
    ) -> bool:
        is_audiobook = self._session.data.get("project_kind") == "audiobook"
        is_dynamic = self._script_text_service.uses_dynamic_storage(
            self._session.data
        )
        temp_data = deepcopy(self._session.data) if (is_audiobook or is_dynamic) else {
            "episode_working_texts": deepcopy(
                self._session.data.get("episode_working_texts", {})
            )
        }
        payload = self._script_text_service.get_episode_payload(
            temp_data, self._episode
        )
        ids = list(source_ids or [])
        if not isinstance(payload, dict) or len(ids) != 1:
            self.errorRequested.emit("Разделить можно только одну исходную реплику")
            return False
        if not is_audiobook and not is_dynamic:
            temp_data = {"episode_working_texts": {self._episode: payload}}
        if not self._script_text_service.split_line_to_character(
            temp_data,
            self._episode,
            ids[0],
            remaining_text,
            split_text,
            split_character,
        ):
            self.errorRequested.emit("Не удалось разделить реплику")
            return False
        if not self._session.ensure_edit_backup(f"episode_{self._episode}"):
            self.errorRequested.emit(
                "Не удалось создать резервную копию перед правкой"
            )
            return False
        self._replace_payload(
            payload,
            "Разделена реплика телесуфлёра",
            temp_data.get("audiobook_document") if is_audiobook else None,
        )
        return True

    @Slot(int)
    def applyOrSavePreset(self, index: int) -> None:
        presets = self._global_settings_service.get_prompter_color_presets()
        if not 0 <= index < len(presets):
            return
        if not presets[index]:
            self.savePreset(index)
            return
        config = self._global_settings_service.get_default_prompter_config()
        config["colors"] = deepcopy(presets[index])
        self._save_global_prompter_config(
            config,
            f"Не удалось применить цветовой пресет {index + 1}",
        )

    @Slot(int)
    def savePreset(self, index: int) -> None:
        previous = self._global_settings_service.get_prompter_color_presets()
        self._global_settings_service.set_prompter_color_preset(
            index, self.config.get("colors", {})
        )
        if not self._global_settings_service.save_settings(
            self._global_settings_service.settings
        ):
            self._global_settings_service.settings[
                "prompter_color_presets"
            ] = previous
            self.errorRequested.emit("Не удалось сохранить цветовой пресет")
        self._refresh_presets()

    @Slot(int)
    def clearPreset(self, index: int) -> None:
        previous = self._global_settings_service.get_prompter_color_presets()
        self._global_settings_service.clear_prompter_color_preset(index)
        if not self._global_settings_service.save_settings(
            self._global_settings_service.settings
        ):
            self._global_settings_service.settings[
                "prompter_color_presets"
            ] = previous
            self.errorRequested.emit("Не удалось удалить цветовой пресет")
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
        self.refresh()
        signature = self._osc_config_signature()
        if signature is None:
            if self._osc_worker is not None or self._osc_client is not None:
                self._stop_osc()
        elif signature != self._osc_runtime_config:
            self._start_osc()
        self._refresh_reaper_connection_state()

    def refresh(self) -> None:
        project_data = self._session.data
        self._position_origin = "internal"
        if self._episode not in project_data.get("episodes", {}):
            self._model.set_rows([])
            self._actor_model.set_rows([])
            self._current_index = -1
            self.changed.emit()
            self.positionChanged.emit()
            return
        lines = sorted(
            self._script_text_service.load_episode_lines(
                project_data,
                self._episode,
                {
                    "hide_leading_timecode_zeros": bool(
                        self.config.get(
                            "hide_leading_timecode_zeros", False
                        )
                    )
                },
            ),
            key=lambda line: float(line.get("s", 0.0)),
        )
        processed = ExportService(project_data).process_merge_logic(
            lines,
            self._global_settings_service.get_replica_merge_config(),
        )
        source_timing_by_id: Dict[str, Dict[str, Any]] = {}
        if self._script_text_service.has_imported_source_lines(
            project_data, self._episode
        ):
            source_timing_by_id = {
                str(line.get("id")): line
                for line in self._script_text_service.get_source_lines(
                    project_data, self._episode
                )
                if line.get("id") is not None
            }
        actors = project_data.get("actors", {})
        all_actor_ids = set(actors)
        selected_actor_ids = (
            all_actor_ids
            if self._selected_actor_ids is None
            else set(self._selected_actor_ids)
        )
        # An empty cast or an empty selection means that the operator wants to
        # see the complete script, without assigning a highlight colour.
        show_all_as_active = not all_actor_ids or not selected_actor_ids
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
                list(replica.get("edit_ids", []))
                if replica.get("_dynamic_text")
                else [replica.get("working_id", replica.get("id", index))]
                if replica.get("_working_text")
                else replica.get("source_ids", [replica.get("id", index)])
            )
            start = float(replica.get("s", 0.0) or 0.0)
            end = float(replica.get("e", start) or start)
            sub_replicas = self._parallel_sub_replicas(replica)
            replica_key = "\x1f".join((
                str(self._episode),
                character,
                f"{start:.6f}",
                "\x1e".join(str(value) for value in source_ids),
            ))
            rows.append({
                "rowIndex": index,
                "start": start,
                "end": end,
                "time": _format_time(start),
                "endTime": _format_time(end),
                "character": character or "-",
                "actor": " / ".join(
                    str(actors.get(actor_id, {}).get("name") or actor_id)
                    for actor_id in actor_ids
                ) or "-",
                "replicaText": str(replica.get("text") or ""),
                "editText": (
                    "\n".join(
                        str(value)
                        for value in replica.get("source_texts", [])
                    )
                    if replica.get("_dynamic_text")
                    and len(replica.get("edit_ids", [])) > 1
                    else str(replica.get("text") or "")
                ),
                "actorColor": str(color_actor.get("color") or "#FFFFFF"),
                "active": show_all_as_active or bool(selected_for_replica),
                "colorActive": bool(color_actor_id),
                "sourceIds": list(source_ids),
                "timingGuides": self._replica_timing_guides(
                    replica, source_timing_by_id
                ),
                "parallelExpandable": bool(sub_replicas),
                "subReplicas": sub_replicas,
                "replicaKey": replica_key,
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

    @staticmethod
    def _parallel_sub_replicas(
        replica: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Return display-only source parts for a parallel merged replica."""
        if not replica.get("parallel_merged"):
            return []
        parts = replica.get("parts")
        if not isinstance(parts, list) or len(parts) < 2:
            return []
        result = []
        for index, part in enumerate(parts):
            if not isinstance(part, dict):
                return []
            try:
                start = float(part.get("start", 0.0) or 0.0)
                end = float(part.get("end", start) or start)
            except (TypeError, ValueError):
                return []
            end = max(start, end)
            result.append({
                "partIndex": index,
                "sourceId": part.get("id"),
                "start": start,
                "end": end,
                "time": _format_time(start),
                "endTime": _format_time(end),
                "text": str(part.get("text", "") or ""),
            })
        return result

    @staticmethod
    def _replica_timing_guides(
        replica: Dict[str, Any],
        source_timing_by_id: Dict[str, Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Map imported source-line ends to exact offsets in rendered text.

        Edited working text is intentionally not matched approximately: an
        incorrect character offset is worse than falling back to proportional
        scrolling for that replica.
        """
        if not source_timing_by_id:
            return []
        text = str(replica.get("text") or "")
        source_ids = list(
            replica.get("source_line_ids")
            or replica.get("source_ids")
            or []
        )
        source_texts = list(replica.get("source_texts") or [])
        if not text or not source_ids:
            return []

        replica_start = float(replica.get("s", 0.0) or 0.0)
        replica_end = float(replica.get("e", replica_start) or replica_start)
        cursor = 0
        last_end = replica_start
        guides: List[Dict[str, Any]] = []
        for position, source_id in enumerate(source_ids):
            source = source_timing_by_id.get(str(source_id))
            if source is None:
                return []
            source_text = str(
                source_texts[position]
                if position < len(source_texts)
                else source.get("text") or ""
            )
            if not source_text:
                return []
            text_start = text.find(source_text, cursor)
            if text_start < 0:
                return []
            text_end = text_start + len(source_text)
            start = float(source.get("s", replica_start) or replica_start)
            end = float(source.get("e", start) or start)
            if end < last_end or start > end:
                return []
            start = max(replica_start, min(replica_end, start))
            end = max(start, min(replica_end, end))
            # QML text positions use UTF-16 code units rather than Python
            # Unicode code points.
            utf16_start = len(text[:text_start].encode("utf-16-le")) // 2
            utf16_end = len(text[:text_end].encode("utf-16-le")) // 2
            guides.append({
                "sourceId": source_id,
                "start": start,
                "end": end,
                "textStart": utf16_start,
                "textEnd": utf16_end,
            })
            cursor = text_end
            last_end = end
        return guides

    def reset(self) -> None:
        self.close()
        self._episode = ""
        self._selected_actor_ids = None
        self._time = 0.0
        self._current_index = -1
        self._position_origin = "internal"
        self._model.set_rows([])
        self._actor_model.set_rows([])
        self.changed.emit()
        self.positionChanged.emit()

    def _normalized_config(self, value: Any) -> Dict[str, Any]:
        config = deepcopy(DEFAULT_PROMPTER_CONFIG)
        defaults = self._global_settings_service.get_default_prompter_config()
        for source in (defaults,):
            if not isinstance(source, dict):
                continue
            config.update({
                key: deepcopy(item)
                for key, item in source.items()
                if key != "colors"
            })
            if isinstance(source.get("colors"), dict):
                config["colors"].update(source["colors"])
        layout_type = config["layout_type"]
        profiles = config.get("layout_font_sizes", {})
        config.update(profiles.get(
            layout_type,
            DEFAULT_PROMPTER_CONFIG["layout_font_sizes"][layout_type],
        ))
        bold_profiles = config.get("layout_font_bold", {})
        config.update(bold_profiles.get(
            layout_type,
            DEFAULT_PROMPTER_CONFIG["layout_font_bold"][layout_type],
        ))
        active_template = self._global_settings_service.get_active_layout_template(
            "teleprompter"
        )
        if active_template and not active_template.get("built_in"):
            config["layout_template"] = active_template
            config["layout_template_rows"] = layout_template_rows(
                active_template["root"]
            )
        return config

    def _normalize_option(self, key: str, value: Any) -> Any:
        if key in {
            "is_mirrored", "show_header", "show_timecode",
            "show_end_timecode",
            "show_character", "show_actor", "show_replica",
            "show_block_borders", "hide_leading_timecode_zeros", "osc_enabled",
            "sync_in", "sync_out", "sync_play_only", "reaper_offset_enabled", "page_scroll_mode",
            "page_debug_overlay", "page_target_highlight_enabled",
            "page_timecode_highlight_enabled",
            *PROMPTER_FONT_BOLD_KEYS,
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
            "page_target_highlight_fade_in_ms": (0, 10000),
            "page_target_highlight_fade_ms": (0, 10000),
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
        if key in {
            "page_gap_prefetch_seconds",
            "page_gap_prefetch_delay_seconds",
        }:
            try:
                return max(0.0, min(60.0, float(value)))
            except (TypeError, ValueError):
                return None
        if key == "page_target_highlight_opacity":
            try:
                return max(0.0, min(0.44, float(value)))
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

    def _set_time(self, seconds: float, origin: str = "internal") -> None:
        self._time = max(0.0, float(seconds))
        self._position_origin = origin
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
            # Multiple ASS events may overlap. Incoming REAPER time has no
            # row identity, so prefer the latest row that has already begun;
            # local list navigation carries an exact index separately.
        self._current_index = current

    def _replace_payload(
        self,
        payload: Dict[str, Any],
        description: str,
        audiobook_document: Optional[Dict[str, Any]] = None,
    ) -> None:
        if audiobook_document is not None:
            self._session.execute(UpdateProjectFileStateCommand(
                self._session.data,
                {"audiobook_document": audiobook_document},
                description,
            ), "working_text")
        else:
            target_mapping = (
                self._session.data.get("script_storage", {}).setdefault(
                    "episodes", {}
                )
                if self._script_text_service.uses_dynamic_storage(
                    self._session.data
                )
                else self._session.data.setdefault("episode_working_texts", {})
            )
            self._session.execute(ReplaceMappingValueCommand(
                target_mapping,
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
        self._last_osc_activity = None
        self._last_reaper_time = None
        self._reaper_playing = False
        self._pending_reaper_time = None
        if not OSC_AVAILABLE:
            self._osc_status = "OSC недоступен: установите python-osc"
            self._refresh_reaper_connection_state()
            self.oscChanged.emit()
            return
        config = self.config
        try:
            from pythonosc.udp_client import SimpleUDPClient

            worker = OscWorker(int(config["port_in"]), self)
            worker.time_changed.connect(self._on_osc_time)
            worker.transport_playing_changed.connect(self._on_osc_transport)
            worker.error_occurred.connect(self._on_osc_error)
            worker.start()
            self._osc_worker = worker
            self._osc_client = SimpleUDPClient(
                "127.0.0.1", int(config["port_out"])
            )
            self._osc_status = (
                f"OSC: {config['port_in']} -> {config['port_out']}"
            )
            self._osc_runtime_config = self._osc_config_signature()
            self._osc_activity_timer.start()
        except Exception as exc:
            self._osc_status = f"Ошибка OSC: {exc}"
            self._osc_worker = None
            self._osc_client = None
            self._osc_runtime_config = None
        self._refresh_reaper_connection_state()
        self.oscChanged.emit()

    def _stop_osc(self) -> None:
        self._osc_activity_timer.stop()
        if self._osc_worker is not None:
            self._osc_worker.stop()
            self._osc_worker.deleteLater()
        self._osc_worker = None
        self._osc_client = None
        self._last_osc_activity = None
        self._last_reaper_time = None
        self._reaper_playing = False
        self._pending_reaper_time = None
        self._osc_runtime_config = None
        self._osc_status = "OSC выключен"
        self._refresh_reaper_connection_state()
        self.oscChanged.emit()

    def _refresh_reaper_connection_state(self) -> None:
        if not self.config.get("osc_enabled"):
            state = "disabled"
        elif self._osc_status.startswith("Ошибка OSC:"):
            state = "error"
        elif self._osc_worker is None:
            if self._osc_status.startswith("OSC недоступен"):
                state = "unavailable"
            else:
                state = "error" if self._osc_status.startswith("Ошибка") else "waiting"
        elif self._last_osc_activity is None:
            state = "waiting"
        elif monotonic() - self._last_osc_activity <= REAPER_ACTIVITY_TIMEOUT_SECONDS:
            state = "active"
        else:
            state = "lost"
        if state != self._reaper_connection_state:
            self._reaper_connection_state = state
            self.oscChanged.emit()

    def _mark_osc_activity(self) -> None:
        self._last_osc_activity = monotonic()
        self._refresh_reaper_connection_state()

    @Slot(object, str)
    def _on_osc_error(self, worker: object, message: str) -> None:
        if worker is not self._osc_worker:
            return
        self._osc_activity_timer.stop()
        self._osc_client = None
        self._last_osc_activity = None
        self._last_reaper_time = None
        self._reaper_playing = False
        self._pending_reaper_time = None
        self._osc_runtime_config = None
        self._osc_status = f"Ошибка OSC: {message}"
        self._refresh_reaper_connection_state()
        self.oscChanged.emit()

    @Slot(float)
    def _on_osc_time(self, seconds: float) -> None:
        self._last_reaper_time = float(seconds)
        self._mark_osc_activity()
        if self._debug_simulation_active:
            return
        config = self.config
        if self._should_follow_reaper_time(config) and self._apply_reaper_time(seconds):
            return

    def _should_follow_reaper_time(self, config: Dict[str, Any]) -> bool:
        return bool(
            config.get("sync_in")
            and (
                not config.get("sync_play_only")
                or self._reaper_playing
            )
        )

    def _apply_reaper_time(self, seconds: float) -> bool:
        if self._should_apply_reaper_time(seconds):
            self._set_time(seconds, "reaper")
            return True
        return False

    @Slot(bool)
    def _on_osc_transport(self, playing: bool) -> None:
        if self._debug_simulation_active:
            return
        playing = bool(playing)
        if self._reaper_playing != playing:
            self._reaper_playing = playing
            self.oscChanged.emit()
        self._mark_osc_activity()
        if (
            self._reaper_playing
            and self.config.get("sync_play_only")
            and self._last_reaper_time is not None
        ):
            self._apply_reaper_time(self._last_reaper_time)
