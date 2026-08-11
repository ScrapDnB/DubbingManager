"""QML backend for montage-sheet preview, editing, and export."""

from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, Optional

from PySide6.QtCore import QObject, Property, QTimer, QUrl, Signal, Slot, Qt
from PySide6.QtGui import QDesktopServices

from config.constants import DEFAULT_EXPORT_CONFIG
from core.export_config_profiles import (
    hydrate_layout_profile,
    set_layout_profile_option,
)
from core.commands import (
    UpdateProjectFileStateCommand,
    UpdateWorkingTextLineCommand,
)
from services import ExportService
from services.global_settings_service import GlobalSettingsService
from services.script_text_service import ScriptTextService
from ui.qml_backend.models import DictListModel
from ui.qml_backend.export_config import normalize_export_option
from ui.qml_backend.project_session import ProjectSession


def _display_path(path_or_url: str) -> str:
    if not path_or_url:
        return ""
    url = QUrl(path_or_url)
    return url.toLocalFile() if url.isLocalFile() else path_or_url


class MontageBridge(QObject):
    """Own the complete montage-sheet workflow exposed to QML."""

    changed = Signal()
    configChanged = Signal()
    episodeChanged = Signal()
    batchChanged = Signal()
    statusRequested = Signal(str)
    errorRequested = Signal(str)
    episodeSelectionRequested = Signal(str)
    projectDataChanged = Signal(str)

    def __init__(
        self,
        session: ProjectSession,
        episode_service,
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
        self._episode = ""
        self._html = ""
        self._batch_queue: list[tuple[str, str, str]] = []
        self._batch_results: list[dict[str, Any]] = []
        self._batch_position = 0
        self._batch_busy = False
        self._batch_cancel_requested = False
        self._batch_folder = ""
        self._highlight_ids: Optional[list[str]] = None
        self._negative_highlight_ids: list[str] = []
        self._model = DictListModel({
            "number": Qt.UserRole + 1,
            "time": Qt.UserRole + 2,
            "character": Qt.UserRole + 3,
            "actor": Qt.UserRole + 4,
            "text": Qt.UserRole + 5,
            "background": Qt.UserRole + 6,
            "textColor": Qt.UserRole + 7,
            "characterBackground": Qt.UserRole + 8,
            "characterTextColor": Qt.UserRole + 9,
        }, self)
        self._highlight_model = DictListModel({
            "actorId": Qt.UserRole + 1,
            "name": Qt.UserRole + 2,
            "actorColor": Qt.UserRole + 3,
            "selected": Qt.UserRole + 4,
            "negative": Qt.UserRole + 5,
        }, self)
        self._batch_result_model = DictListModel({
            "fileName": Qt.UserRole + 1,
            "status": Qt.UserRole + 2,
            "detail": Qt.UserRole + 3,
            "statusKind": Qt.UserRole + 4,
            "path": Qt.UserRole + 5,
        }, self)

    @Property("QVariantMap", notify=configChanged)
    def config(self) -> Dict[str, Any]:
        config = deepcopy(DEFAULT_EXPORT_CONFIG)
        config.update(self._global_settings_service.get_default_export_config())
        config = hydrate_layout_profile(config)
        active_template = self._global_settings_service.get_active_layout_template(
            "montage"
        )
        if active_template and not active_template.get("built_in"):
            config["layout_template"] = active_template
        config["highlight_ids_export"] = deepcopy(self._highlight_ids)
        config["highlight_negative_ids_export"] = deepcopy(
            self._negative_highlight_ids
        )
        if config.get("layout_type") == "Сценарий":
            config["layout_type"] = "Сценарий 1"
        return config

    @Property(str, notify=episodeChanged)
    def episode(self) -> str:
        return self._episode

    @Property(str, notify=changed)
    def html(self) -> str:
        return self._html

    @Property(int, notify=changed)
    def count(self) -> int:
        return self._model.rowCount()

    @Property(str, notify=configChanged)
    def highlightSummary(self) -> str:
        actor_ids = list(self._session.data.get("actors", {}))
        if not actor_ids:
            return "Нет актёров"
        configured = self.config.get("highlight_ids_export")
        if configured is None:
            return "Все актёры"
        selected = set(configured) & set(actor_ids)
        if not selected:
            return "Подсветка отключена"
        if len(selected) == len(actor_ids):
            return "Все актёры"
        return f"{len(selected)} из {len(actor_ids)}"

    @Property(QObject, constant=True)
    def model(self) -> QObject:
        return self._model

    @Property(QObject, constant=True)
    def highlightModel(self) -> QObject:
        return self._highlight_model

    @Property(QObject, constant=True)
    def episodesModel(self) -> QObject:
        return self._episodes_model

    @Property(QObject, constant=True)
    def batchResultModel(self) -> QObject:
        return self._batch_result_model

    @Property(bool, notify=batchChanged)
    def batchBusy(self) -> bool:
        return self._batch_busy

    @Property(int, notify=batchChanged)
    def batchTotal(self) -> int:
        return len(self._batch_queue)

    @Property(int, notify=batchChanged)
    def batchCompleted(self) -> int:
        return min(self._batch_position, len(self._batch_queue))

    @Property(float, notify=batchChanged)
    def batchProgress(self) -> float:
        return self.batchCompleted / self.batchTotal if self.batchTotal else 0.0

    @Property(str, notify=batchChanged)
    def batchSummary(self) -> str:
        successful = sum(
            row["statusKind"] == "success" for row in self._batch_results
        )
        failed = sum(
            row["statusKind"] == "error" for row in self._batch_results
        )
        if self._batch_busy:
            return (
                f"Экспорт: {self.batchCompleted} из {self.batchTotal} · "
                f"ошибок: {failed}"
            )
        if self._batch_results:
            return f"Экспортировано: {successful} · ошибок: {failed}"
        return ""

    @Slot(str)
    def prepare(self, episode: str) -> None:
        episode = str(episode or self._session.current_episode)
        if episode not in self._session.data.get("episodes", {}):
            self.errorRequested.emit("Выберите серию для предпросмотра")
            return
        self.episodeSelectionRequested.emit(episode)
        if self._episode != episode:
            self._episode = episode
            self.episodeChanged.emit()
        self.refresh_preview()

    @Slot(str, str)
    def updateText(self, line_id: str, new_text: str) -> None:
        if not self._episode:
            return
        is_audiobook = self._session.data.get("project_kind") == "audiobook"
        payload = self._script_text_service.get_episode_payload(
            self._session.data, self._episode
        )
        if not isinstance(payload, dict):
            self.errorRequested.emit(
                "Для редактирования нужен рабочий текст серии"
            )
            return
        target = next((
            line
            for index, line in enumerate(payload.get("lines", []))
            if str(line.get("id")) == str(line_id)
            or str(index) == str(line_id)
        ), None)
        if target is None or str(target.get("text", "")) == new_text:
            return
        if not self._session.ensure_edit_backup(f"episode_{self._episode}"):
            self.errorRequested.emit(
                "Не удалось создать резервную копию перед правкой"
            )
            return
        if is_audiobook:
            candidate = deepcopy(self._session.data.get("audiobook_document", {}))
            temp_data = {
                "project_kind": "audiobook",
                "audiobook_document": candidate,
            }
            if not self._script_text_service.update_line_text(
                temp_data, self._episode, line_id, new_text
            ):
                return
            self._session.execute(UpdateProjectFileStateCommand(
                self._session.data,
                {"audiobook_document": candidate},
                "Изменена реплика монтажного листа",
            ), "working_text")
        else:
            self._session.execute(UpdateWorkingTextLineCommand(
                self._session.data.setdefault("episode_working_texts", {}),
                self._episode,
                line_id,
                new_text,
            ), "working_text")
        self.refresh_preview()
        self.projectDataChanged.emit("working_text")
        self.statusRequested.emit(
            f"Текст реплики изменён: серия {self._episode}"
        )

    @Slot(str, "QVariant")
    def setOption(self, key: str, value: Any) -> None:
        normalized = self._normalize_option(key, value)
        if normalized is None:
            return
        config = self.config
        if config.get(key) == normalized:
            return
        config = set_layout_profile_option(config, key, normalized)
        if not self._save_global_config(
            config, sync_layout_template=key == "layout_type"
        ):
            return
        self.configChanged.emit()
        self.refresh_preview()
        self.statusRequested.emit("Настройки монтажного листа изменены")

    @Slot(str, bool)
    def setActorHighlighted(self, actor_id: str, enabled: bool) -> None:
        actors = self._session.data.get("actors", {})
        if actor_id not in actors:
            return
        all_ids = list(actors)
        configured = self.config.get("highlight_ids_export")
        selected = set(all_ids if configured is None else configured)
        if enabled:
            selected.add(actor_id)
        else:
            selected.discard(actor_id)
        self._set_actor_filters(selected, None)

    @Slot(str, bool)
    def setActorNegative(self, actor_id: str, enabled: bool) -> None:
        if actor_id not in self._session.data.get("actors", {}):
            return
        negative = set(
            self.config.get("highlight_negative_ids_export") or []
        )
        if enabled:
            negative.add(actor_id)
        else:
            negative.discard(actor_id)
        self._set_actor_filters(None, negative)

    @Slot(bool)
    def setAllActorsHighlighted(self, enabled: bool) -> None:
        selected = (
            set(self._session.data.get("actors", {})) if enabled else set()
        )
        self._set_actor_filters(selected, None)

    @Slot(str, str)
    def exportFile(self, export_format: str, path_or_url: str) -> None:
        episode = self._episode or self._session.current_episode
        if not episode:
            self.errorRequested.emit("Выберите серию для экспорта")
            return
        export_format = self._normalize_format(export_format)
        if not export_format:
            self.errorRequested.emit("Неизвестный формат экспорта")
            return
        path = _display_path(path_or_url)
        if not path:
            return
        output_path = Path(path).expanduser()
        if output_path.suffix.lower() != f".{export_format}":
            output_path = output_path.with_suffix(f".{export_format}")
        success, message = self._export_to_path(
            episode,
            export_format,
            str(output_path),
        )
        if not success:
            self.errorRequested.emit(message)
            return
        self.statusRequested.emit(message)
        self._open_if_enabled(output_path)

    @Slot(str, bool, bool, bool, bool, bool)
    def exportBatch(
        self,
        folder_or_url: str,
        export_html: bool,
        export_xlsx: bool,
        export_docx: bool,
        export_pdf: bool,
        all_episodes: bool,
    ) -> None:
        if self._batch_busy:
            self.errorRequested.emit("Пакетный экспорт уже выполняется")
            return
        folder_path = _display_path(folder_or_url)
        if not folder_path:
            return
        formats = [
            name for name, enabled in (
                ("html", export_html),
                ("xlsx", export_xlsx),
                ("docx", export_docx),
                ("pdf", export_pdf),
            ) if enabled
        ]
        if not formats:
            self.errorRequested.emit("Выберите хотя бы один формат")
            return
        folder = Path(folder_path).expanduser()
        try:
            folder.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            self.errorRequested.emit(
                f"Не удалось создать папку экспорта: {exc}"
            )
            return

        episodes = (
            list(self._session.data.get("episodes", {}))
            if all_episodes else [self._episode or self._session.current_episode]
        )
        episodes = [str(episode) for episode in episodes if str(episode)]
        if not episodes:
            self.errorRequested.emit("Выберите серию для экспорта")
            return
        project_name = str(
            self._session.data.get("project_name") or "Project"
        )
        self._batch_queue = [
            (
                episode,
                export_format,
                str(folder / f"{project_name} - Ep{episode}.{export_format}"),
            )
            for episode in episodes
            for export_format in formats
            if not (all_episodes and export_format == "xlsx")
        ]
        if all_episodes and "xlsx" in formats:
            self._batch_queue.append((
                "",
                "xlsx_all",
                str(folder / f"{project_name} - Все серии.xlsx"),
            ))
        self._batch_results = []
        self._batch_position = 0
        self._batch_busy = True
        self._batch_cancel_requested = False
        self._batch_folder = str(folder)
        self._batch_result_model.set_rows([])
        self.batchChanged.emit()
        QTimer.singleShot(0, self._process_batch_next)

    @Slot()
    def cancelBatch(self) -> None:
        if self._batch_busy:
            self._batch_cancel_requested = True
            self.batchChanged.emit()

    @Slot()
    def clearBatchResults(self) -> None:
        if self._batch_busy:
            return
        self._batch_queue = []
        self._batch_results = []
        self._batch_position = 0
        self._batch_result_model.set_rows([])
        self.batchChanged.emit()

    @Slot(int)
    def openBatchResult(self, index: int) -> None:
        if not 0 <= index < len(self._batch_results):
            return
        path = self._batch_results[index].get("path", "")
        if path and Path(path).exists():
            QDesktopServices.openUrl(QUrl.fromLocalFile(path))

    def _process_batch_next(self) -> None:
        if not self._batch_busy:
            return
        if self._batch_cancel_requested or self._batch_position >= len(
            self._batch_queue
        ):
            self._finish_batch()
            return
        episode, export_format, path = self._batch_queue[self._batch_position]
        if export_format == "xlsx_all":
            success, message = self._export_all_episodes_xlsx(path)
        else:
            success, message = self._export_to_path(
                episode, export_format, path
            )
        self._batch_results.append({
            "fileName": Path(path).name,
            "status": "Готово" if success else "Ошибка",
            "detail": message,
            "statusKind": "success" if success else "error",
            "path": path if success else "",
        })
        self._batch_position += 1
        self._batch_result_model.set_rows(self._batch_results)
        self.batchChanged.emit()
        QTimer.singleShot(0, self._process_batch_next)

    def _finish_batch(self) -> None:
        cancelled = self._batch_cancel_requested
        self._batch_busy = False
        self._batch_cancel_requested = False
        self.batchChanged.emit()
        successful = sum(
            row["statusKind"] == "success" for row in self._batch_results
        )
        failed = sum(
            row["statusKind"] == "error" for row in self._batch_results
        )
        message = self.batchSummary
        if cancelled:
            message += " · отменено"
        if successful and self.config.get("open_auto", True) and self._batch_folder:
            QDesktopServices.openUrl(QUrl.fromLocalFile(self._batch_folder))
        if failed:
            self.errorRequested.emit(message)
        else:
            self.statusRequested.emit(message)

    def refresh(self) -> None:
        self.refresh_highlights()
        if self._episode:
            self.refresh_preview()

    def refresh_preview(self) -> None:
        if (
            not self._episode
            or self._episode not in self._session.data.get("episodes", {})
        ):
            self._model.set_rows([])
            self._html = self._empty_html("Выберите серию")
            self.changed.emit()
            return
        lines = self._get_lines(self._episode)
        config = self.config
        service = ExportService(self._export_project_data(config))
        processed = service.process_merge_logic(
            lines,
            self._global_settings_service.get_replica_merge_config(),
        ) if lines else []
        self._html = (
            service.generate_html(
                self._episode,
                processed,
                config,
                config.get("highlight_ids_export"),
                layout_type=config.get("layout_type", "Таблица"),
                is_editable=bool(config.get("allow_edit", True)),
            )
            if processed
            else self._empty_html("Для серии нет рабочего текста")
        )
        actors = self._session.data.get("actors", {})
        effective_filter = service._get_effective_highlight_filter(config)
        rows = []
        for index, line in enumerate(processed, 1):
            character = str(line.get("char") or "")
            actor_id, actor, highlighted = service._actor_display_context(
                character, self._episode, effective_filter
            )
            background, _ = service._get_colors(
                bool(config.get("use_color", True)),
                highlighted,
                actor,
                bool(config.get("soften_colors", True)),
                config.get("color_softening_level", 1),
            )
            if not config.get("use_color", True) or not highlighted:
                background = "transparent"
            character_only = bool(config.get("highlight_character_only", False))
            negative_text = service._negative_text_color(
                actor_id,
                config,
                highlighted,
            ) or ""
            rows.append({
                "number": index,
                "time": service._format_export_timing(line, config),
                "character": character or "-",
                "actor": actor.get("name", "-"),
                "text": str(line.get("text") or ""),
                "background": "transparent" if character_only else background,
                "textColor": "" if character_only else negative_text,
                "characterBackground": background if character_only else "transparent",
                "characterTextColor": negative_text if character_only else "",
            })
        self._model.set_rows(rows)
        self.changed.emit()

    def refresh_highlights(self) -> None:
        actors = self._session.data.get("actors", {})
        all_ids = set(actors)
        configured = self.config.get("highlight_ids_export")
        selected = all_ids if configured is None else set(configured) & all_ids
        negative = set(
            self.config.get("highlight_negative_ids_export") or []
        ) & all_ids
        self._highlight_model.set_rows([
            {
                "actorId": actor_id,
                "name": actor.get("name", actor_id),
                "actorColor": actor.get("color", "#8FAADC"),
                "selected": actor_id in selected,
                "negative": actor_id in negative,
            }
            for actor_id, actor in sorted(
                actors.items(),
                key=lambda item: str(
                    item[1].get("name", item[0])
                ).casefold(),
            )
        ])

    def notify_project_changed(self) -> None:
        self.configChanged.emit()
        self.refresh()

    @Slot()
    def notify_global_config_changed(self) -> None:
        self.configChanged.emit()
        self.refresh()

    def reset(self) -> None:
        self._episode = ""
        self._html = ""
        self._highlight_ids = None
        self._negative_highlight_ids = []
        self._model.set_rows([])
        self._highlight_model.set_rows([])
        self._batch_queue = []
        self._batch_results = []
        self._batch_position = 0
        self._batch_busy = False
        self._batch_cancel_requested = False
        self._batch_result_model.set_rows([])
        self.episodeChanged.emit()
        self.configChanged.emit()
        self.changed.emit()
        self.batchChanged.emit()

    def _set_actor_filters(
        self,
        selected: Optional[set[str]],
        negative: Optional[set[str]],
    ) -> None:
        actors = self._session.data.get("actors", {})
        all_ids = list(actors)
        if selected is not None:
            selected_ids = [item for item in all_ids if item in selected]
            self._highlight_ids = (
                None if len(selected_ids) == len(all_ids) else selected_ids
            )
        if negative is not None:
            self._negative_highlight_ids = [
                item for item in all_ids if item in negative
            ]
        self.configChanged.emit()
        self.refresh_highlights()
        self.refresh_preview()
        self.statusRequested.emit("Подсветка актёров изменена")

    def _export_to_path(
        self,
        episode: str,
        export_format: str,
        path: str,
    ) -> tuple[bool, str]:
        lines = self._get_lines(episode)
        if not lines:
            return False, (
                f"Для серии {episode} не найден рабочий текст. "
                "Создайте его в окне «Файлы проекта»."
            )
        config = self.config
        service = ExportService(self._export_project_data(config))
        merge_config = self._global_settings_service.get_replica_merge_config()
        try:
            if export_format == "html":
                processed = service.process_merge_logic(lines, merge_config)
                html = service.generate_html(
                    episode,
                    processed,
                    config,
                    config.get("highlight_ids_export"),
                    layout_type=config.get("layout_type", "Таблица"),
                    is_editable=bool(config.get("allow_edit", True)),
                )
                Path(path).write_text(html, encoding="utf-8")
                return True, f"Экспортировано в {path}"
            if export_format == "xlsx":
                return service.export_to_excel(
                    episode, lines, config, path, merge_cfg=merge_config
                )
            if export_format == "docx":
                return service.export_to_docx(
                    episode, lines, config, path, merge_cfg=merge_config
                )
            if export_format == "pdf":
                return service.export_to_pdf(
                    episode, lines, config, path, merge_cfg=merge_config
                )
        except Exception as exc:
            return False, f"Ошибка экспорта: {exc}"
        return False, "Неизвестный формат экспорта"

    def _export_all_episodes_xlsx(self, path: str) -> tuple[bool, str]:
        """Export one workbook with a summary and one sheet per episode."""
        episodes_data = {
            str(episode): lines
            for episode in self._session.data.get("episodes", {})
            if (lines := self._get_lines(str(episode)))
        }
        if not episodes_data:
            return False, "Не найден рабочий текст ни для одной серии"

        config = self.config
        service = ExportService(self._export_project_data(config))
        merge_config = self._global_settings_service.get_replica_merge_config()
        first_episode = next(iter(episodes_data))
        return service.export_to_excel(
            first_episode,
            episodes_data[first_episode],
            config,
            path,
            all_episodes=episodes_data,
            merge_cfg=merge_config,
        )

    def _save_global_config(
        self,
        config: Dict[str, Any],
        *,
        sync_layout_template: bool = False,
    ) -> bool:
        config = deepcopy(config)
        config.pop("highlight_ids_export", None)
        config.pop("highlight_negative_ids_export", None)
        previous = deepcopy(self._global_settings_service.settings)
        self._global_settings_service.set_default_export_config(config)
        if sync_layout_template:
            template_id = {
                "Таблица": "builtin.montage.table",
                "Сценарий 1": "builtin.montage.scenario1",
                "Сценарий 2": "builtin.montage.scenario2",
                "Сценарий 3": "builtin.montage.scenario3",
            }.get(str(config.get("layout_type")))
            if template_id:
                self._global_settings_service.set_active_layout_template_id(
                    "montage", template_id
                )
        if self._global_settings_service.save_settings(
            self._global_settings_service.settings
        ):
            return True
        self._global_settings_service.settings = previous
        self.errorRequested.emit("Не удалось сохранить настройки монтажного листа")
        return False

    def _export_project_data(self, config: Dict[str, Any]) -> Dict[str, Any]:
        data = dict(self._session.data)
        data["export_config"] = config
        return data

    def _open_if_enabled(self, path: Path) -> None:
        if self.config.get("open_auto", True):
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))

    def _get_lines(self, episode: str):
        return self._script_text_service.load_episode_lines(
            self._session.data,
            str(episode),
        )

    @staticmethod
    def _normalize_format(value: str) -> str:
        value = str(value or "").strip().lower()
        return value if value in {"html", "xlsx", "docx", "pdf"} else ""

    @staticmethod
    def _normalize_option(key: str, value: Any) -> Any:
        return normalize_export_option(key, value)

    @staticmethod
    def _empty_html(message: str) -> str:
        return (
            "<html><head><meta charset='utf-8'><style>"
            "body{font-family:'Segoe UI',sans-serif;padding:36px;"
            "background:#f6f7f8;color:#5f6368}"
            "</style></head><body><h3>"
            f"{message}</h3></body></html>"
        )
