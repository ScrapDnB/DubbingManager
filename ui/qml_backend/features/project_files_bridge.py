"""QML backend for project file links and project health checks."""

from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4

from PySide6.QtCore import QObject, Property, QUrl, Signal, Slot, Qt

from config.constants import PROJECT_VERSION
from core.commands import UpdateProjectFileStateCommand
from services.docx_import_service import DocxImportService
from services.dynamic_script_storage import (
    SOURCE_LINE_MODE_ATOMIC,
    SOURCE_LINE_MODE_PREMERGED,
    new_script_storage,
)
from services.episode_service import EpisodeService
from services.export_service import ExportService
from services.project_fps_service import consider_ass_fps, consider_video_fps
from ui.qml_backend.models import DictListModel
from ui.qml_backend.project_session import ProjectSession


def _display_path(path_or_url: str) -> str:
    if not path_or_url:
        return ""
    url = QUrl(path_or_url)
    return url.toLocalFile() if url.isLocalFile() else path_or_url


def _episode_sort_key(value: str) -> tuple[int, str]:
    try:
        return (0, f"{int(value):08d}")
    except (TypeError, ValueError):
        return (1, str(value).lower())


class ProjectFilesBridge(QObject):
    """Own project-folder links, working texts, and health diagnostics."""

    filesChanged = Signal()
    healthChanged = Signal()
    ignoreEmptyLinesChanged = Signal()
    currentFileStateChanged = Signal()
    statusRequested = Signal(str)
    errorRequested = Signal(str)
    projectDataChanged = Signal(str)
    episodeDeletionRequested = Signal(list)

    def __init__(
        self,
        session: ProjectSession,
        project_folder_service,
        project_health_service,
        episode_service,
        script_text_service,
        global_settings_service,
        parent: Optional[QObject] = None,
    ) -> None:
        super().__init__(parent)
        self._session = session
        self._project_folder_service = project_folder_service
        self._project_health_service = project_health_service
        self._episode_service = episode_service
        self._script_text_service = script_text_service
        self._global_settings_service = global_settings_service
        self._files_summary = ""
        self._health_summary = ""
        self._ignore_empty_lines = False
        self._files_model = DictListModel({
            "episode": Qt.UserRole + 1,
            "kind": Qt.UserRole + 2,
            "kindLabel": Qt.UserRole + 3,
            "status": Qt.UserRole + 4,
            "statusKind": Qt.UserRole + 5,
            "path": Qt.UserRole + 6,
            "resolvedPath": Qt.UserRole + 7,
            "exists": Qt.UserRole + 8,
            "canRegenerate": Qt.UserRole + 9,
            "hasSourceAss": Qt.UserRole + 10,
            "canRelink": Qt.UserRole + 11,
        }, self)
        self._health_model = DictListModel({
            "severity": Qt.UserRole + 1,
            "severityLabel": Qt.UserRole + 2,
            "episode": Qt.UserRole + 3,
            "category": Qt.UserRole + 4,
            "message": Qt.UserRole + 5,
            "path": Qt.UserRole + 6,
        }, self)
        self._session.currentEpisodeChanged.connect(
            self.currentFileStateChanged
        )
        self.refresh()

    @Property(str, notify=filesChanged)
    def folder(self) -> str:
        return str(self._session.data.get("project_folder") or "")

    @Property(str, notify=filesChanged)
    def filesSummary(self) -> str:
        return self._files_summary

    @Property(str, notify=healthChanged)
    def healthSummary(self) -> str:
        return self._health_summary

    @Property(bool, notify=ignoreEmptyLinesChanged)
    def ignoreEmptyLines(self) -> bool:
        return self._ignore_empty_lines

    @Slot(bool)
    def setIgnoreEmptyLines(self, value: bool) -> None:
        value = bool(value)
        if self._ignore_empty_lines == value:
            return
        self._ignore_empty_lines = value
        self.ignoreEmptyLinesChanged.emit()
        self._refresh_health()

    @Property(bool, notify=currentFileStateChanged)
    def currentEpisodeSourceMissing(self) -> bool:
        if self._session.data.get("project_kind") == "audiobook":
            return False
        episode = self._session.current_episode
        source = self._session.data.get("episodes", {}).get(episode)
        return bool(
            episode
            and source
            and not self._project_folder_service.project_path_exists(
                self._session.data,
                source,
            )
        )

    @Property(str, notify=currentFileStateChanged)
    def currentEpisodeSourcePath(self) -> str:
        return str(
            self._session.data.get("episodes", {}).get(
                self._session.current_episode
            ) or ""
        )

    @Property(QObject, constant=True)
    def filesModel(self) -> QObject:
        return self._files_model

    @Property(QObject, constant=True)
    def healthModel(self) -> QObject:
        return self._health_model

    @Property(bool, notify=filesChanged)
    def legacyMergedProject(self) -> bool:
        """Return whether the open subtitle project uses saved merged lines."""
        runtime = self._session.data.get("_project_format")
        return bool(
            self._session.data.get("project_kind") == "subtitle"
            and isinstance(runtime, dict)
            and runtime.get("storage_model") == "legacy_merged"
        )

    @Property(bool, notify=filesChanged)
    def canConvertToNewFormat(self) -> bool:
        """Return whether every legacy episode has a resolved ASS source."""
        return bool(
            self.legacyMergedProject
            and self._conversion_episode_names(self._session.data)
            and not self._missing_conversion_ass(self._session.data)
        )

    @Property(str, notify=filesChanged)
    def conversionStatus(self) -> str:
        """Explain whether the legacy project can be converted."""
        if not self.legacyMergedProject:
            return ""
        episodes = self._conversion_episode_names(self._session.data)
        if not episodes:
            return "В проекте нет серий для конвертации"
        missing = self._missing_conversion_ass(self._session.data)
        if missing:
            return (
                "Для конвертации должны быть найдены ASS всех серий. "
                f"Не найдены: {', '.join(missing)}"
            )
        return "Все ASS найдены; проект можно конвертировать в формат 2.0"

    @Slot()
    def refresh(self) -> None:
        self._project_folder_service.invalidate_cache()
        self._refresh_files()
        self._refresh_health()

    @Slot()
    def refresh_health(self) -> None:
        """Refresh validation without rescanning project-folder file paths."""
        self._refresh_health()

    def materialize_missing_source_lines(self) -> int:
        """Embed original source lines for legacy working texts before saving."""
        return self._materialize_missing_source_lines(self._session.data)

    @Slot()
    def createMissingSourceLines(self) -> None:
        """Create original source-line snapshots for every eligible episode."""
        candidate = deepcopy(self._session.data)
        materialized = self._materialize_missing_source_lines(candidate)
        if not materialized:
            self.statusRequested.emit(
                "Нет рабочих текстов, которым нужны исходные строки"
            )
            return
        self._push_file_state(
            candidate,
            "Созданы исходные строки из файлов субтитров",
        )
        self.statusRequested.emit(
            f"Созданы исходные строки: {materialized}"
        )

    @Slot()
    def convertToNewFormat(self) -> None:
        """Convert a legacy merged project to dynamic ASS-backed storage."""
        if not self.legacyMergedProject:
            self.errorRequested.emit(
                "Конвертация доступна только для проектов старого формата"
            )
            return

        episodes = self._conversion_episode_names(self._session.data)
        missing = self._missing_conversion_ass(self._session.data)
        if not episodes:
            self.errorRequested.emit("В проекте нет серий для конвертации")
            return
        if missing:
            self.errorRequested.emit(
                "Для конвертации должны быть найдены ASS всех серий: "
                + ", ".join(missing)
            )
            return

        candidate = deepcopy(self._session.data)
        legacy_payloads = deepcopy(candidate.get("episode_working_texts", {}))
        parsed_by_episode: Dict[str, List[Dict[str, Any]]] = {}
        sources: Dict[str, str] = {}
        import_configs: Dict[str, Dict[str, Any]] = {}

        try:
            # Older projects may keep their editable working text in a file
            # instead of embedding it in the project.  Load those payloads
            # before clearing ``episode_texts`` so their edits are migrated
            # into dynamic edit blocks as well.
            for episode in episodes:
                if episode in legacy_payloads:
                    continue
                legacy_path = candidate.get("episode_texts", {}).get(episode)
                if not legacy_path:
                    continue
                resolved_path = self._project_folder_service.resolve_project_path(
                    candidate, legacy_path
                )
                if not resolved_path or not Path(resolved_path).is_file():
                    raise ValueError(
                        f"не найден рабочий текст серии {episode}"
                    )
                payload = self._script_text_service.load_episode_text(
                    resolved_path
                )
                if not isinstance(payload, dict):
                    raise ValueError(
                        f"некорректный рабочий текст серии {episode}"
                    )
                legacy_payloads[episode] = payload

            for episode in episodes:
                source = self._resolved_episode_source(episode, candidate)
                import_config = self._legacy_ass_import_config(
                    candidate, episode
                )
                _stats, lines = EpisodeService(
                    ass_import_config=import_config
                ).parse_ass_file(source)
                if not lines:
                    raise ValueError(
                        f"в ASS серии {episode} не найдено строк"
                    )
                sources[episode] = source
                parsed_by_episode[episode] = lines
                import_configs[episode] = import_config

            candidate["script_storage"] = new_script_storage()
            candidate["episode_working_texts"] = {}
            candidate["episode_texts"] = {}
            candidate.setdefault("loaded_episodes", {}).clear()

            for episode in episodes:
                source = sources[episode]
                lines = parsed_by_episode[episode]
                self._script_text_service.create_episode_text(
                    candidate,
                    episode,
                    source,
                    lines,
                    self._script_text_service.get_merge_config(candidate),
                    self._session.project_service.current_project_path or None,
                    import_config=import_configs[episode],
                    line_mode=SOURCE_LINE_MODE_ATOMIC,
                )
                dynamic_payload = candidate["script_storage"]["episodes"][
                    episode
                ]
                legacy_payload = legacy_payloads.get(episode)
                if isinstance(legacy_payload, dict):
                    self._restore_legacy_edits(
                        candidate,
                        episode,
                        legacy_payload,
                        dynamic_payload,
                        lines,
                    )
        except Exception as exc:
            self.errorRequested.emit(f"Не удалось конвертировать проект: {exc}")
            return

        candidate["_project_format"] = {
            "storage_model": "dynamic_source",
            "original_version": PROJECT_VERSION,
            "preserved_fields": {},
        }
        if not self._push_file_state(
            candidate,
            "Проект конвертирован в новый формат",
            include_format=True,
        ):
            return
        self._episode_service.clear_cache()
        self.statusRequested.emit(
            f"Проект конвертирован в формат {PROJECT_VERSION}: "
            f"серий {len(episodes)}"
        )

    def _materialize_missing_source_lines(
        self,
        project_data: Dict[str, Any],
    ) -> int:
        if project_data.get("project_kind") == "audiobook":
            return 0

        materialized = 0
        for episode in project_data.get("episode_working_texts", {}):
            if self._script_text_service.has_imported_source_lines(
                project_data,
                episode,
            ):
                continue
            source = self._resolved_episode_source(str(episode), project_data)
            if not source:
                continue
            try:
                lines = self._parse_episode_source(source, project_data)
            except Exception:
                continue
            if self._script_text_service.embed_source_lines_from_source(
                project_data,
                str(episode),
                source,
                lines,
            ):
                materialized += 1
        return materialized

    @Slot(str)
    def setFolder(self, path_or_url: str) -> None:
        folder = Path(_display_path(path_or_url)).expanduser()
        if not folder.is_dir():
            self.errorRequested.emit("Выбранная папка проекта не существует")
            return

        candidate = deepcopy(self._session.data)
        previous_episodes = dict(candidate.get("episodes", {}))
        previous_videos = dict(candidate.get("video_paths", {}))
        candidate["project_folder"] = str(folder.resolve())
        self._project_folder_service.invalidate_cache()
        counts = self._project_folder_service.scan_and_link_files(
            candidate,
            candidate["project_folder"],
        )
        self._consider_fps_for_link_changes(
            candidate,
            previous_episodes,
            previous_videos,
        )
        self._push_file_state(
            candidate,
            "Изменена папка проекта",
            include_folder=True,
        )
        self.statusRequested.emit(
            "Папка проекта выбрана · найдено: "
            f"источников {counts[0]}, видео {counts[1]}, текстов {counts[2]}"
        )

    @Slot()
    def clearFolder(self) -> None:
        if not self.folder:
            return
        candidate = deepcopy(self._session.data)
        candidate.pop("project_folder", None)
        self._project_folder_service.invalidate_cache()
        self._push_file_state(
            candidate,
            "Отвязана папка проекта",
            include_folder=True,
        )
        self.statusRequested.emit("Папка проекта отвязана")

    @Slot()
    def scanFolder(self) -> None:
        folder = self.folder
        if not folder or not Path(folder).is_dir():
            self.errorRequested.emit(
                "Сначала выберите существующую папку проекта"
            )
            return
        candidate = deepcopy(self._session.data)
        previous_episodes = dict(candidate.get("episodes", {}))
        previous_videos = dict(candidate.get("video_paths", {}))
        self._project_folder_service.invalidate_cache(folder)
        counts = self._project_folder_service.scan_and_link_files(
            candidate,
            folder,
        )
        if not any(counts):
            self.refresh()
            self.statusRequested.emit(
                "Новых совпадений в папке проекта не найдено"
            )
            return
        self._consider_fps_for_link_changes(
            candidate,
            previous_episodes,
            previous_videos,
        )
        self._push_file_state(
            candidate,
            "Перепривязаны файлы из папки проекта",
        )
        self.statusRequested.emit(
            f"Перепривязано: источников {counts[0]}, видео {counts[1]}, "
            f"текстов {counts[2]}"
        )

    @Slot()
    def batchImportFolder(self) -> None:
        folder = self.folder
        if not folder or not Path(folder).is_dir():
            self.errorRequested.emit(
                "Сначала выберите существующую папку проекта"
            )
            return

        candidate = deepcopy(self._session.data)
        existing_episodes = set(candidate.get("episodes", {}))
        existing_videos = set(candidate.get("video_paths", {}))
        self._project_folder_service.invalidate_cache(folder)
        source_count, video_count = (
            self._project_folder_service.batch_import_from_folder(
                candidate, folder
            )
        )
        added_episodes = [
            episode
            for episode in candidate.get("episodes", {})
            if episode not in existing_episodes
        ]
        for episode in sorted(added_episodes, key=_episode_sort_key):
            source = self._resolved_episode_source(episode, candidate)
            if source and Path(source).suffix.lower() == ".ass":
                consider_ass_fps(candidate, source)
                break
        for episode in sorted(
            (
                str(value)
                for value in candidate.get("video_paths", {})
                if value not in existing_videos
            ),
            key=_episode_sort_key,
        ):
            video = self._project_folder_service.resolve_project_path(
                candidate,
                candidate.get("video_paths", {}).get(episode),
            )
            if video and Path(video).is_file():
                consider_video_fps(candidate, str(video))
                break
        self._episode_service.set_merge_gap_from_config(
            self._script_text_service.get_merge_config(candidate)
        )
        created = 0
        failed = 0
        for episode in sorted(added_episodes, key=_episode_sort_key):
            source = self._resolved_episode_source(episode, candidate)
            if not source:
                failed += 1
                continue
            try:
                lines = self._parse_episode_source(source, candidate)
            except Exception:
                failed += 1
                continue
            if not lines:
                failed += 1
                continue
            merge_config = self._script_text_service.get_merge_config(candidate)
            if (
                Path(source).suffix.lower() == ".docx"
                and not self._script_text_service.uses_dynamic_storage(candidate)
            ):
                merge_config = {**merge_config, "merge": False}
            self._script_text_service.create_episode_text(
                candidate,
                episode,
                source,
                lines,
                merge_config,
                self._session.project_service.current_project_path or None,
                import_config=self._source_import_config(
                    source, candidate, episode
                ),
                line_mode=self._source_line_mode(source),
            )
            created += 1

        if not source_count and not video_count:
            self.refresh()
            self.statusRequested.emit("Новых серий и видео в папке не найдено")
            return
        if source_count:
            candidate["project_kind"] = "subtitle"
        candidate.setdefault("loaded_episodes", {}).clear()
        self._push_file_state(
            candidate,
            "Добавлены серии из папки проекта",
            include_project_kind=True,
        )
        self._episode_service.clear_cache()
        suffix = f" · без рабочего текста: {failed}" if failed else ""
        self.statusRequested.emit(
            f"Добавлено серий: {source_count} · видео: {video_count} · "
            f"рабочих текстов: {created}{suffix}"
        )

    @Slot(str, str, str)
    def relink(self, episode: str, kind: str, path_or_url: str) -> None:
        episode = str(episode or "")
        kind = str(kind or "").lower()
        path = Path(_display_path(path_or_url)).expanduser()
        if not episode or not path.is_file():
            self.errorRequested.emit("Выбранный файл не существует")
            return

        allowed = {
            "source": {".ass", ".srt", ".docx"},
            "video": self._project_folder_service.VIDEO_EXTENSIONS,
            "working": {".json"},
        }
        if kind not in allowed or path.suffix.lower() not in allowed[kind]:
            self.errorRequested.emit("Выбран неподдерживаемый тип файла")
            return

        field = {
            "source": "episodes",
            "video": "video_paths",
            "working": "episode_texts",
        }[kind]
        candidate = deepcopy(self._session.data)
        candidate.setdefault(field, {})[episode] = str(path.resolve())
        if kind == "source" and path.suffix.lower() == ".ass":
            consider_ass_fps(candidate, str(path.resolve()))
        elif kind == "video":
            consider_video_fps(candidate, str(path.resolve()))
        self._push_file_state(candidate, f"Перепривязан файл серии {episode}")
        if kind == "source":
            self._episode_service.invalidate_episode(episode)
        self.statusRequested.emit(f"Файл серии {episode} перепривязан")

    @Slot(str)
    def removeVideo(self, episode: str) -> None:
        episode = str(episode or "")
        if not episode or episode not in self._session.data.get("video_paths", {}):
            return
        candidate = deepcopy(self._session.data)
        candidate.setdefault("video_paths", {}).pop(episode, None)
        if self._push_file_state(
            candidate,
            f"Отвязано видео серии {episode}",
        ):
            self.statusRequested.emit(f"Видео серии {episode} отвязано")

    @Slot(str)
    def regenerateWorkingText(self, episode: str) -> None:
        episode = str(episode or "")
        source = self._resolved_episode_source(episode)
        if not source:
            self.errorRequested.emit("Исходный файл серии не найден")
            return
        try:
            lines = self._parse_episode_source(source, self._session.data)
        except Exception as exc:
            self.errorRequested.emit(
                f"Не удалось прочитать исходный файл: {exc}"
            )
            return
        if not lines:
            self.errorRequested.emit("В исходном файле нет строк")
            return

        candidate = deepcopy(self._session.data)
        merge_config = self._script_text_service.get_merge_config(candidate)
        if (
            Path(source).suffix.lower() == ".docx"
            and not self._script_text_service.uses_dynamic_storage(candidate)
        ):
            merge_config = {**merge_config, "merge": False}
        self._script_text_service.create_episode_text(
            candidate,
            episode,
            source,
            lines,
            merge_config,
            self._session.project_service.current_project_path or None,
            import_config=self._source_import_config(
                source, self._session.data, episode
            ),
            line_mode=self._source_line_mode(source),
        )
        candidate.setdefault("loaded_episodes", {}).pop(episode, None)
        self._push_file_state(
            candidate,
            f"Пересоздан рабочий текст серии {episode}",
        )
        self._episode_service.invalidate_episode(episode)
        self.statusRequested.emit(
            f"Рабочий текст серии {episode} пересоздан"
        )

    @Slot()
    def createMissingWorkingTexts(self) -> None:
        candidate = deepcopy(self._session.data)
        created = 0
        failed = 0
        for episode in sorted(
            candidate.get("episodes", {}),
            key=_episode_sort_key,
        ):
            if self._script_text_service.get_episode_payload(candidate, episode):
                continue
            source = self._resolved_episode_source(episode, candidate)
            if not source:
                continue
            try:
                lines = self._parse_episode_source(source, candidate)
            except Exception:
                failed += 1
                continue
            if not lines:
                failed += 1
                continue
            merge_config = self._script_text_service.get_merge_config(candidate)
            if (
                Path(source).suffix.lower() == ".docx"
                and not self._script_text_service.uses_dynamic_storage(candidate)
            ):
                merge_config = {**merge_config, "merge": False}
            self._script_text_service.create_episode_text(
                candidate,
                episode,
                source,
                lines,
                merge_config,
                self._session.project_service.current_project_path or None,
                import_config=self._source_import_config(
                    source, candidate, episode
                ),
                line_mode=self._source_line_mode(source),
            )
            created += 1

        if not created:
            if failed:
                self.errorRequested.emit(
                    f"Не удалось создать рабочих текстов: {failed}"
                )
            else:
                self.statusRequested.emit("Нет рабочих текстов для создания")
            return
        candidate.setdefault("loaded_episodes", {}).clear()
        self._push_file_state(
            candidate,
            "Созданы недостающие рабочие тексты",
        )
        self._episode_service.clear_cache()
        suffix = f"; не удалось: {failed}" if failed else ""
        self.statusRequested.emit(
            f"Создано рабочих текстов: {created}{suffix}"
        )

    @Slot(str, str)
    def saveOriginalAss(self, episode: str, path_or_url: str) -> None:
        episode = str(episode or "")
        path = _display_path(path_or_url)
        if not episode or not path:
            return
        target = Path(path).expanduser()
        if not target.suffix:
            target = target.with_suffix(".ass")
        if self._script_text_service.save_source_ass(
            self._session.data,
            episode,
            str(target),
        ):
            self.statusRequested.emit(f"Исходный ASS сохранён: {target.name}")
        else:
            self.errorRequested.emit(
                "В серии нет сохранённого исходного ASS"
            )

    @Slot(str)
    def deleteEpisode(self, episode: str) -> None:
        self.deleteEpisodes([episode])

    @Slot(list)
    def deleteEpisodes(self, episodes: list) -> None:
        episode_names = list(dict.fromkeys(
            str(episode) for episode in episodes if str(episode)
        ))
        if episode_names:
            self.episodeDeletionRequested.emit(episode_names)

    def _refresh_files(self) -> None:
        project_data = self._session.data
        episodes = project_data.get("episodes", {})
        working_texts = project_data.get("episode_working_texts", {})
        dynamic_texts = (
            project_data.get("script_storage", {}).get("episodes", {})
            if self._script_text_service.uses_dynamic_storage(project_data)
            else {}
        )
        legacy_texts = project_data.get("episode_texts", {})
        video_paths = project_data.get("video_paths", {})
        episode_names = sorted(
            {
                str(name)
                for mapping in (
                    episodes,
                    working_texts,
                    dynamic_texts,
                    legacy_texts,
                    video_paths,
                )
                for name in mapping
            },
            key=_episode_sort_key,
        )

        rows: List[Dict[str, Any]] = []
        source_found = 0
        working_found = 0
        video_found = 0
        for episode in episode_names:
            source_path = str(episodes.get(episode) or "")
            source_resolved = str(
                self._project_folder_service.resolve_project_path(
                    project_data,
                    source_path,
                ) or ""
            )
            source_exists = bool(
                source_path
                and self._project_folder_service.project_path_exists(
                    project_data,
                    source_path,
                )
            )
            source_found += int(source_exists)
            rows.append({
                "episode": episode,
                "kind": "source",
                "kindLabel": "Источник",
                "status": "Найден" if source_exists else (
                    "Не найден" if source_path else "Не указан"
                ),
                "statusKind": "success" if source_exists else (
                    "error" if source_path else "info"
                ),
                "path": source_path or "-",
                "resolvedPath": source_resolved,
                "exists": source_exists,
                "canRegenerate": bool(
                    source_exists
                    and Path(source_resolved).suffix.lower()
                    in {".ass", ".srt", ".docx"}
                ),
                "hasSourceAss": False,
                "canRelink": True,
            })

            payload = (
                dynamic_texts.get(episode)
                if dynamic_texts
                else working_texts.get(episode)
            )
            legacy_path = str(legacy_texts.get(episode) or "")
            has_embedded = isinstance(payload, dict)
            has_source_lines = self._script_text_service.has_imported_source_lines(
                project_data,
                episode,
            )
            legacy_exists = bool(
                legacy_path
                and self._project_folder_service.project_path_exists(
                    project_data,
                    legacy_path,
                )
            )
            working_exists = has_embedded or legacy_exists
            working_found += int(working_exists)
            rows.append({
                "episode": episode,
                "kind": "working",
                "kindLabel": "Рабочий текст",
                "status": "В проекте" if has_embedded and has_source_lines else (
                    "Нет исходных строк" if has_embedded else (
                    "Найден" if legacy_exists else (
                        "Не найден" if legacy_path else "Не создан"
                    ))
                ),
                "statusKind": "success" if has_embedded and has_source_lines else (
                    "warning" if has_embedded else (
                    "error" if legacy_path else "warning"
                )),
                "path": (
                    "Встроен в .dub"
                    if has_embedded
                    else (legacy_path or "-")
                ),
                "resolvedPath": "" if has_embedded else str(
                    self._project_folder_service.resolve_project_path(
                        project_data,
                        legacy_path,
                    ) or ""
                ),
                "exists": working_exists,
                "canRegenerate": bool(
                    source_exists
                    and Path(source_resolved).suffix.lower()
                    in {".ass", ".srt", ".docx"}
                ),
                "hasSourceAss": self._script_text_service.has_source_ass(
                    project_data,
                    episode,
                ),
                "canRelink": not has_embedded,
            })

            video_path = str(video_paths.get(episode) or "")
            video_exists = bool(
                video_path
                and self._project_folder_service.project_path_exists(
                    project_data,
                    video_path,
                )
            )
            video_found += int(video_exists)
            rows.append({
                "episode": episode,
                "kind": "video",
                "kindLabel": "Видео",
                "status": "Найден" if video_exists else (
                    "Не найден" if video_path else "Не привязано"
                ),
                "statusKind": "success" if video_exists else (
                    "error" if video_path else "info"
                ),
                "path": video_path or "-",
                "resolvedPath": str(
                    self._project_folder_service.resolve_project_path(
                        project_data,
                        video_path,
                    ) or ""
                ),
                "exists": video_exists,
                "canRegenerate": False,
                "hasSourceAss": False,
                "canRelink": True,
            })

        self._files_model.set_rows(rows)
        total = len(episode_names)
        self._files_summary = (
            f"Серий: {total} · источников: {source_found}/{total} · "
            f"рабочих текстов: {working_found}/{total} · видео: {video_found}"
        )
        self.filesChanged.emit()
        self.currentFileStateChanged.emit()

    def _refresh_health(self) -> None:
        issues = self._project_health_service.check_project(
            self._session.data,
            ignore_empty_lines=self._ignore_empty_lines,
        )
        labels = {
            "error": "Ошибка",
            "warning": "Предупреждение",
            "info": "Инфо",
        }
        self._health_model.set_rows([
            {
                "severity": issue.severity,
                "severityLabel": labels.get(
                    issue.severity,
                    issue.severity,
                ),
                "episode": str(issue.episode or ""),
                "category": issue.category,
                "message": issue.message,
                "path": str(issue.path or ""),
            }
            for issue in issues
        ])
        summary = self._project_health_service.get_summary(issues)
        if not issues:
            self._health_summary = "Проблем не найдено"
        else:
            self._health_summary = (
                f"Ошибки: {summary['errors']} · "
                f"предупреждения: {summary['warnings']} · "
                f"инфо: {summary['info']}"
            )
        self.healthChanged.emit()

    def _push_file_state(
        self,
        candidate: Dict[str, Any],
        description: str,
        include_folder: bool = False,
        include_project_kind: bool = False,
        include_format: bool = False,
    ) -> bool:
        fields = [
            "episodes",
            "video_paths",
            "episode_texts",
            "episode_working_texts",
            "script_storage",
            "project_settings",
            "loaded_episodes",
        ]
        if include_folder:
            fields.append("project_folder")
        if include_project_kind:
            fields.append("project_kind")
        if include_format:
            fields.append("_project_format")
        updates = {
            field: candidate.get(field)
            for field in fields
            if candidate.get(field) != self._session.data.get(field)
        }
        if not updates:
            self._refresh_files()
            self._refresh_health()
            return False
        self._session.execute(
            UpdateProjectFileStateCommand(
                self._session.data,
                updates,
                description,
            ),
            "project_files",
        )
        self.projectDataChanged.emit("project_files")
        return True

    @staticmethod
    def _conversion_episode_names(project_data: Dict[str, Any]) -> List[str]:
        """Return every legacy subtitle episode that must be converted."""
        names = {
            str(name)
            for mapping in (
                project_data.get("episodes", {}),
                project_data.get("episode_working_texts", {}),
                project_data.get("episode_texts", {}),
            )
            if isinstance(mapping, dict)
            for name in mapping
        }
        return sorted(names, key=_episode_sort_key)

    def _missing_conversion_ass(
        self,
        project_data: Dict[str, Any],
    ) -> List[str]:
        """Return episodes without a resolved ASS source file."""
        missing = []
        for episode in self._conversion_episode_names(project_data):
            source = self._resolved_episode_source(episode, project_data)
            if not source or Path(source).suffix.lower() != ".ass":
                missing.append(episode)
        return missing

    def _legacy_ass_import_config(
        self,
        project_data: Dict[str, Any],
        episode: str,
    ) -> Dict[str, Any]:
        """Return the ASS rules used by the legacy project when available."""
        payload = self._script_text_service.get_episode_payload(
            project_data, episode
        )
        source = payload.get("source") if isinstance(payload, dict) else None
        saved = source.get("import_config") if isinstance(source, dict) else None
        if isinstance(saved, dict) and saved:
            return deepcopy(saved)

        runtime = project_data.get("_project_format")
        preserved = (
            runtime.get("preserved_fields", {})
            if isinstance(runtime, dict)
            else {}
        )
        saved = preserved.get("ass_import_config")
        if isinstance(saved, dict) and saved:
            return deepcopy(saved)
        return deepcopy(self._episode_service.ass_import_config)

    def _restore_legacy_edits(
        self,
        project_data: Dict[str, Any],
        episode: str,
        legacy_payload: Dict[str, Any],
        dynamic_payload: Dict[str, Any],
        source_lines: List[Dict[str, Any]],
    ) -> None:
        """Carry legacy text/character edits into dynamic edit blocks."""
        legacy_lines = [
            line for line in legacy_payload.get("lines", [])
            if isinstance(line, dict)
        ]
        if not legacy_lines:
            return

        source_id_map = {
            str(line.get("origin", {}).get("imported_id")): str(line["id"])
            for line in dynamic_payload.get("source_lines", [])
            if isinstance(line, dict)
            and line.get("id")
            and isinstance(line.get("origin"), dict)
        }
        source_order = {
            str(line.get("id")): index
            for index, line in enumerate(dynamic_payload.get("source_lines", []))
            if isinstance(line, dict) and line.get("id")
        }

        merge_config = legacy_payload.get("merge_config")
        if not isinstance(merge_config, dict):
            runtime = project_data.get("_project_format")
            preserved = (
                runtime.get("preserved_fields", {})
                if isinstance(runtime, dict)
                else {}
            )
            merge_config = preserved.get("replica_merge_config")
        if not isinstance(merge_config, dict):
            merge_config = self._script_text_service.get_merge_config(
                project_data
            )

        normalized_source_lines = []
        for index, line in enumerate(source_lines):
            normalized = deepcopy(line)
            normalized.setdefault("id", index)
            normalized_source_lines.append(normalized)
        expected_rows = ExportService(project_data).process_merge_logic(
            normalized_source_lines,
            merge_config,
        )
        expected_by_sources = {
            self._legacy_source_key(row): row
            for row in expected_rows
            if self._legacy_source_key(row)
        }

        desired_characters: Dict[str, set[str]] = {}
        analyzed = []
        for line in legacy_lines:
            legacy_key = self._legacy_source_key(line)
            expected = expected_by_sources.get(legacy_key)
            base_character = str(
                (expected or {}).get("char")
                or line.get("character", "")
                or ""
            )
            desired_character = str(
                line.get("display_character")
                or line.get("character", "")
                or ""
            )
            if base_character:
                desired_characters.setdefault(base_character, set()).add(
                    desired_character
                )
            analyzed.append((line, legacy_key, expected, base_character,
                             desired_character))

        aliases = dynamic_payload.setdefault("character_aliases", {})
        for base_character, values in desired_characters.items():
            if len(values) != 1:
                continue
            desired_character = next(iter(values))
            if desired_character and desired_character != base_character:
                aliases[base_character] = desired_character

        edit_rows = []
        for line, legacy_key, expected, base_character, desired_character in analyzed:
            expected_text = (
                str(expected.get("text", ""))
                if isinstance(expected, dict)
                else None
            )
            text_changed = (
                str(line.get("text", "")) != expected_text
                if expected_text is not None
                else bool(line.get("dirty"))
            )
            character_changed = bool(
                desired_character != base_character
                and aliases.get(base_character) != desired_character
            )
            if not text_changed and not character_changed:
                continue

            dynamic_ids = [
                source_id_map.get(source_id) for source_id in legacy_key
            ]
            if not dynamic_ids or any(not value for value in dynamic_ids):
                raise ValueError(
                    f"не удалось сопоставить правки серии {episode} "
                    "с исходными строками ASS"
                )
            indices = sorted(source_order[str(value)] for value in dynamic_ids)
            if indices != list(range(indices[0], indices[-1] + 1)):
                raise ValueError(
                    f"правки серии {episode} охватывают несмежные строки ASS"
                )
            edit_rows.append({
                "source_ids": [str(value) for value in dynamic_ids],
                "fragment": {
                    "id": f"frag_{uuid4().hex}",
                    "text": str(line.get("text", "") or ""),
                    "character": desired_character,
                },
            })

        blocks = []
        for row in edit_rows:
            row_ids = set(row["source_ids"])
            if blocks and row_ids.intersection(blocks[-1]["_source_id_set"]):
                block = blocks[-1]
                block["_source_id_set"].update(row_ids)
                block["fragments"].append(row["fragment"])
                block["source_ids"] = sorted(
                    block["_source_id_set"],
                    key=source_order.__getitem__,
                )
                continue
            blocks.append({
                "id": f"edit_{uuid4().hex}",
                "source_ids": list(row["source_ids"]),
                "fragments": [row["fragment"]],
                "_source_id_set": set(row["source_ids"]),
            })

        for block in blocks:
            block.pop("_source_id_set", None)
        if blocks or aliases:
            dynamic_payload["edit_blocks"] = blocks
            dynamic_payload["modified_at"] = datetime.now().isoformat()

    @staticmethod
    def _legacy_source_key(line: Dict[str, Any]) -> tuple[str, ...]:
        source_ids = line.get("source_ids")
        if not isinstance(source_ids, list):
            source_id = line.get("id")
            source_ids = [] if source_id is None else [source_id]
        return tuple(str(value) for value in source_ids if value is not None)

    def _consider_fps_for_link_changes(
        self,
        candidate: Dict[str, Any],
        previous_episodes: Dict[str, Any],
        previous_videos: Dict[str, Any],
    ) -> None:
        """Detect FPS when folder scanning resolves the first source/video."""
        changed_sources = [
            str(episode)
            for episode, value in candidate.get("episodes", {}).items()
            if value != previous_episodes.get(episode)
        ]
        for episode in sorted(changed_sources, key=_episode_sort_key):
            source = self._resolved_episode_source(episode, candidate)
            if source and Path(source).suffix.lower() == ".ass":
                consider_ass_fps(candidate, source)
                break

        changed_videos = [
            str(episode)
            for episode, value in candidate.get("video_paths", {}).items()
            if value != previous_videos.get(episode)
        ]
        for episode in sorted(changed_videos, key=_episode_sort_key):
            video = self._project_folder_service.resolve_project_path(
                candidate,
                candidate.get("video_paths", {}).get(episode),
            )
            if video and Path(video).is_file():
                consider_video_fps(candidate, str(video))
                break

    def _resolved_episode_source(
        self,
        episode: str,
        project_data: Optional[Dict[str, Any]] = None,
    ) -> str:
        data = project_data or self._session.data
        raw_path = data.get("episodes", {}).get(str(episode))
        resolved = self._project_folder_service.resolve_project_path(
            data,
            raw_path,
        )
        return str(resolved) if resolved and Path(resolved).is_file() else ""

    def _parse_episode_source(
        self,
        path: str,
        project_data: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        suffix = Path(path).suffix.lower()
        if suffix == ".srt":
            _stats, lines = self._episode_service.parse_srt_file(path)
            return lines
        if suffix == ".ass":
            _stats, lines = self._episode_service.parse_ass_file(path)
            return lines
        if suffix == ".docx":
            config = self._global_settings_service.get_docx_import_config()
            service = DocxImportService(detection_config=config)
            mapping = config.get("mapping") if isinstance(config, dict) else None
            _stats, lines = service.parse_document(path, mapping)
            return lines
        return []

    @staticmethod
    def _source_line_mode(path: str) -> str:
        return (
            SOURCE_LINE_MODE_PREMERGED
            if Path(path).suffix.lower() == ".docx"
            else SOURCE_LINE_MODE_ATOMIC
        )

    def _source_import_config(
        self,
        path: str,
        project_data: Dict[str, Any],
        episode: str,
    ) -> Dict[str, Any]:
        payload = self._script_text_service.get_episode_payload(
            project_data, episode
        )
        source = payload.get("source") if isinstance(payload, dict) else None
        saved = source.get("import_config") if isinstance(source, dict) else None
        if isinstance(saved, dict) and saved:
            return deepcopy(saved)
        suffix = Path(path).suffix.lower()
        if suffix == ".ass":
            return deepcopy(self._episode_service.ass_import_config)
        if suffix == ".srt":
            return deepcopy(self._episode_service.srt_import_config)
        if suffix == ".docx":
            return deepcopy(
                self._global_settings_service.get_docx_import_config()
            )
        return {}
