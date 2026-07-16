"""QML backend for project file links and project health checks."""

from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, List, Optional

from PySide6.QtCore import QObject, Property, QUrl, Signal, Slot, Qt

from core.commands import UpdateProjectFileStateCommand
from services.docx_import_service import DocxImportService
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
    currentFileStateChanged = Signal()
    statusRequested = Signal(str)
    errorRequested = Signal(str)
    projectDataChanged = Signal(str)
    episodeDeletionRequested = Signal(str)

    def __init__(
        self,
        session: ProjectSession,
        project_folder_service,
        project_health_service,
        episode_service,
        script_text_service,
        parent: Optional[QObject] = None,
    ) -> None:
        super().__init__(parent)
        self._session = session
        self._project_folder_service = project_folder_service
        self._project_health_service = project_health_service
        self._episode_service = episode_service
        self._script_text_service = script_text_service
        self._files_summary = ""
        self._health_summary = ""
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

    @Property(bool, notify=currentFileStateChanged)
    def currentEpisodeSourceMissing(self) -> bool:
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

    @Slot()
    def refresh(self) -> None:
        self._project_folder_service.invalidate_cache()
        self._refresh_files()
        self._refresh_health()

    @Slot(str)
    def setFolder(self, path_or_url: str) -> None:
        folder = Path(_display_path(path_or_url)).expanduser()
        if not folder.is_dir():
            self.errorRequested.emit("Выбранная папка проекта не существует")
            return

        candidate = deepcopy(self._session.data)
        candidate["project_folder"] = str(folder.resolve())
        self._project_folder_service.invalidate_cache()
        counts = self._project_folder_service.scan_and_link_files(
            candidate,
            candidate["project_folder"],
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
            merge_config = candidate.get("replica_merge_config", {})
            if Path(source).suffix.lower() == ".docx":
                merge_config = {**merge_config, "merge": False}
            self._script_text_service.create_episode_text(
                candidate,
                episode,
                source,
                lines,
                merge_config,
                self._session.project_service.current_project_path or None,
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
            self.errorRequested.emit("В исходном файле нет реплик")
            return

        candidate = deepcopy(self._session.data)
        merge_config = candidate.get("replica_merge_config", {})
        if Path(source).suffix.lower() == ".docx":
            merge_config = {**merge_config, "merge": False}
        self._script_text_service.create_episode_text(
            candidate,
            episode,
            source,
            lines,
            merge_config,
            self._session.project_service.current_project_path or None,
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
            if candidate.get("episode_working_texts", {}).get(episode):
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
            merge_config = candidate.get("replica_merge_config", {})
            if Path(source).suffix.lower() == ".docx":
                merge_config = {**merge_config, "merge": False}
            self._script_text_service.create_episode_text(
                candidate,
                episode,
                source,
                lines,
                merge_config,
                self._session.project_service.current_project_path or None,
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
        episode = str(episode or "")
        if episode:
            self.episodeDeletionRequested.emit(episode)

    def _refresh_files(self) -> None:
        project_data = self._session.data
        episodes = project_data.get("episodes", {})
        working_texts = project_data.get("episode_working_texts", {})
        legacy_texts = project_data.get("episode_texts", {})
        video_paths = project_data.get("video_paths", {})
        episode_names = sorted(
            {
                str(name)
                for mapping in (
                    episodes,
                    working_texts,
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

            payload = working_texts.get(episode)
            legacy_path = str(legacy_texts.get(episode) or "")
            has_embedded = isinstance(payload, dict)
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
                "status": "В проекте" if has_embedded else (
                    "Найден" if legacy_exists else (
                        "Не найден" if legacy_path else "Не создан"
                    )
                ),
                "statusKind": "success" if working_exists else (
                    "error" if legacy_path else "warning"
                ),
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
            self._session.data
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
    ) -> bool:
        fields = [
            "episodes",
            "video_paths",
            "episode_texts",
            "episode_working_texts",
            "loaded_episodes",
        ]
        if include_folder:
            fields.append("project_folder")
        if include_project_kind:
            fields.append("project_kind")
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
            config = project_data.get("docx_import_config", {})
            service = DocxImportService(detection_config=config)
            mapping = config.get("mapping") if isinstance(config, dict) else None
            _stats, lines = service.parse_document(path, mapping)
            return lines
        return []
