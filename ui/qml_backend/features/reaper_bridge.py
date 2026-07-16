"""QML backend for Reaper project and marker export."""

import re
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, Dict, Optional

from PySide6.QtCore import QObject, Property, QUrl, Signal, Slot
from PySide6.QtGui import QDesktopServices

from services.project_folder_service import ProjectFolderService
from services.script_text_service import ScriptTextService
from services.reaper_export_service import ReaperExportService
from ui.qml_backend.project_session import ProjectSession


def _display_path(path_or_url: str) -> str:
    if not path_or_url:
        return ""
    url = QUrl(path_or_url)
    return url.toLocalFile() if url.isLocalFile() else path_or_url


def _episode_sort_key(value: Any) -> tuple[int, str]:
    try:
        return (0, f"{int(value):08d}")
    except (TypeError, ValueError):
        return (1, str(value).casefold())


def _safe_filename(value: str) -> str:
    safe = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", str(value or ""))
    return safe.strip(" .") or "Reaper export"


class ReaperBridge(QObject):
    """Own Reaper preview and export state for the QML dialog."""

    changed = Signal()
    statusRequested = Signal(str)
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
        self._preview: Dict[str, Any] = {}
        self._episode = ""
        self._video_path = ""
        self._source_markers_available = False
        self._last_export_path = ""
        self._last_export_count = 0

    @Property("QVariantMap", notify=changed)
    def preview(self) -> Dict[str, Any]:
        return deepcopy(self._preview)

    @Property(str, notify=changed)
    def episode(self) -> str:
        return self._episode

    @Property(bool, notify=changed)
    def videoAvailable(self) -> bool:
        return bool(self._video_path and Path(self._video_path).is_file())

    @Property(str, notify=changed)
    def videoName(self) -> str:
        return Path(self._video_path).name if self.videoAvailable else ""

    @Property(bool, notify=changed)
    def sourceMarkersAvailable(self) -> bool:
        return self._source_markers_available

    @Property(str, notify=changed)
    def lastExportPath(self) -> str:
        return self._last_export_path

    @Property(int, notify=changed)
    def lastExportCount(self) -> int:
        return self._last_export_count

    @Property(int, notify=changed)
    def exportableEpisodeCount(self) -> int:
        return len(self._exportable_episodes())

    @Property(bool, notify=changed)
    def allSourceMarkersAvailable(self) -> bool:
        episodes = self._exportable_episodes()
        controller = self._controller()
        return bool(episodes) and all(
            controller.has_source_markers(episode) for episode in episodes
        )

    @Property(bool, notify=changed)
    def anyVideoAvailable(self) -> bool:
        controller = self._controller()
        return any(
            self._resolved_video_path(controller, episode)
            for episode in self._exportable_episodes()
        )

    @Slot(result=bool)
    def prepare(self) -> bool:
        episode = self._session.current_episode
        if not episode:
            self.errorRequested.emit("Выберите серию для экспорта в Reaper")
            return False
        lines = self._get_lines(episode)
        if not lines:
            self.errorRequested.emit("В выбранной серии нет рабочего текста")
            return False

        controller = self._controller()
        self._episode = episode
        self._last_export_path = ""
        self._last_export_count = 0
        self._video_path = str(controller.resolve_video_path(episode) or "")
        self._source_markers_available = controller.has_source_markers(episode)
        self._update_preview(
            use_video=self.videoAvailable,
            use_regions=True,
            transliterate_actor_names=False,
            marker_mode="merged",
        )
        return True

    @Slot(bool, bool, bool, str, result="QVariantMap")
    def updatePreview(
        self,
        use_video: bool,
        use_regions: bool,
        transliterate_actor_names: bool,
        marker_mode: str,
    ) -> Dict[str, Any]:
        if not self._episode:
            return {}
        return self._update_preview(
            use_video,
            use_regions,
            transliterate_actor_names,
            marker_mode,
        )

    @Slot(str, str, bool, bool, bool, str, result=bool)
    def export(
        self,
        output_format: str,
        path_or_url: str,
        use_video: bool,
        use_regions: bool,
        transliterate_actor_names: bool,
        marker_mode: str,
    ) -> bool:
        episode = self._episode or self._session.current_episode
        path = _display_path(path_or_url)
        if not episode or not path:
            return False
        lines = self._get_lines(episode)
        if not lines:
            self.errorRequested.emit("В выбранной серии нет рабочего текста")
            return False

        output_format = str(output_format or "").lower()
        if output_format not in {"rpp", "csv"}:
            self.errorRequested.emit("Неизвестный формат экспорта Reaper")
            return False
        marker_mode = self._normalized_marker_mode(marker_mode)
        output_path = Path(path).expanduser()
        suffix = f".{output_format}"
        if output_path.suffix.lower() != suffix:
            output_path = output_path.with_suffix(suffix)

        controller = self._controller()
        try:
            if output_format == "csv":
                controller.save_marker_csv(
                    episode,
                    lines,
                    str(output_path),
                    marker_mode,
                )
                message = f"Маркеры Reaper сохранены: {output_path.name}"
            else:
                controller.save(
                    episode,
                    lines,
                    str(output_path),
                    self._video_path,
                    bool(use_video and self.videoAvailable),
                    use_regions,
                    transliterate_actor_names,
                    marker_mode,
                )
                message = f"Проект Reaper сохранён: {output_path.name}"
        except Exception as exc:
            self.errorRequested.emit(
                f"Не удалось сохранить экспорт Reaper: {exc}"
            )
            return False

        self._last_export_path = str(output_path)
        self._last_export_count = 1
        self.statusRequested.emit(message)
        self.changed.emit()
        return True

    @Slot(str, str, bool, bool, bool, str, result=bool)
    def exportAll(
        self,
        output_format: str,
        path_or_url: str,
        use_video: bool,
        use_regions: bool,
        transliterate_actor_names: bool,
        marker_mode: str,
    ) -> bool:
        output_format = str(output_format or "").lower()
        output_folder = Path(_display_path(path_or_url)).expanduser()
        episodes = self._exportable_episodes()
        if output_format not in {"rpp", "csv"}:
            self.errorRequested.emit("Неизвестный формат экспорта Reaper")
            return False
        if not episodes or not str(output_folder):
            self.errorRequested.emit("В проекте нет серий с рабочим текстом")
            return False
        marker_mode = str(marker_mode or "").strip().lower()
        if marker_mode == "source" and not self.allSourceMarkersAvailable:
            self.errorRequested.emit(
                "Точные исходные маркеры доступны не во всех сериях"
            )
            return False
        marker_mode = "source" if marker_mode == "source" else "merged"

        controller = self._controller()
        filenames = self._batch_filenames(controller, episodes, output_format)
        try:
            output_folder.mkdir(parents=True, exist_ok=True)
            with TemporaryDirectory(
                prefix=".dubbing-manager-reaper-",
                dir=output_folder,
            ) as temporary_directory:
                temporary_folder = Path(temporary_directory)
                for episode, filename in zip(episodes, filenames):
                    lines = self._get_lines(episode)
                    temporary_path = temporary_folder / filename
                    if output_format == "csv":
                        controller.save_marker_csv(
                            episode,
                            lines,
                            str(temporary_path),
                            marker_mode,
                        )
                        continue
                    video_path = str(
                        controller.resolve_video_path(episode) or ""
                    )
                    controller.save(
                        episode,
                        lines,
                        str(temporary_path),
                        video_path,
                        bool(
                            use_video
                            and video_path
                            and Path(video_path).is_file()
                        ),
                        use_regions,
                        transliterate_actor_names,
                        marker_mode,
                    )
                for filename in filenames:
                    (temporary_folder / filename).replace(
                        output_folder / filename
                    )
        except Exception as exc:
            self.errorRequested.emit(
                f"Не удалось экспортировать все серии в Reaper: {exc}"
            )
            return False

        self._last_export_path = str(output_folder)
        self._last_export_count = len(filenames)
        self.statusRequested.emit(
            f"Экспорт Reaper завершён: {len(filenames)} файлов"
        )
        self.changed.emit()
        return True

    @Slot()
    def openLastExport(self) -> None:
        if self._last_export_path:
            QDesktopServices.openUrl(
                QUrl.fromLocalFile(self._last_export_path)
            )

    def reset(self) -> None:
        self._preview = {}
        self._episode = ""
        self._video_path = ""
        self._source_markers_available = False
        self._last_export_path = ""
        self._last_export_count = 0
        self.changed.emit()

    def _update_preview(
        self,
        use_video: bool,
        use_regions: bool,
        transliterate_actor_names: bool,
        marker_mode: str,
    ) -> Dict[str, Any]:
        marker_mode = self._normalized_marker_mode(marker_mode)
        self._preview = self._controller().preview(
            self._episode,
            self._get_lines(self._episode),
            self._video_path,
            bool(use_video and self.videoAvailable),
            use_regions,
            transliterate_actor_names,
            marker_mode,
        )
        self.changed.emit()
        return deepcopy(self._preview)

    def _controller(self) -> ReaperExportService:
        return ReaperExportService(
            self._session.data,
            self._project_folder_service,
        )

    def _get_lines(self, episode: str):
        return self._script_text_service.load_episode_lines(
            self._session.data,
            str(episode),
        )

    def _exportable_episodes(self) -> list[str]:
        return [
            str(episode)
            for episode in sorted(
                self._session.data.get("episodes", {}),
                key=_episode_sort_key,
            )
            if self._get_lines(str(episode))
        ]

    @staticmethod
    def _resolved_video_path(
        controller: ReaperExportService,
        episode: str,
    ) -> str:
        path = str(controller.resolve_video_path(episode) or "")
        return path if path and Path(path).is_file() else ""

    @staticmethod
    def _batch_filenames(
        controller: ReaperExportService,
        episodes: list[str],
        output_format: str,
    ) -> list[str]:
        filenames = []
        used = set()
        for episode in episodes:
            raw = (
                controller.default_csv_filename(episode)
                if output_format == "csv"
                else controller.default_filename(episode)
            )
            candidate = _safe_filename(raw)
            stem = Path(candidate).stem
            suffix = Path(candidate).suffix
            duplicate = 2
            while candidate.casefold() in used:
                candidate = f"{stem} ({duplicate}){suffix}"
                duplicate += 1
            used.add(candidate.casefold())
            filenames.append(candidate)
        return filenames

    def _normalized_marker_mode(self, value: str) -> str:
        mode = str(value or "").strip().lower()
        if mode == "source" and self._source_markers_available:
            return mode
        return "merged"
