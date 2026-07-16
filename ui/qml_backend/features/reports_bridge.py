"""QML backend for project search and casting reports."""

from pathlib import Path
from typing import Any, Dict, List, Optional

from PySide6.QtCore import QObject, Property, QUrl, Signal, Slot, Qt
from PySide6.QtGui import QGuiApplication

from services import CharacterStatsService
from ui.qml_backend.models import DictListModel
from ui.qml_backend.project_session import ProjectSession
from utils.helpers import natural_sort_key


def _display_path(path_or_url: str) -> str:
    if not path_or_url:
        return ""
    url = QUrl(path_or_url)
    return url.toLocalFile() if url.isLocalFile() else path_or_url


def _format_time(seconds: Any) -> str:
    try:
        total = max(0, float(seconds))
    except (TypeError, ValueError):
        total = 0.0
    minutes = int(total // 60)
    return f"{minutes:02d}:{total - minutes * 60:05.2f}"


class ReportsBridge(QObject):
    """Own global search results and actor summary exports."""

    searchChanged = Signal()
    summaryChanged = Signal()
    metricChanged = Signal()
    statusRequested = Signal(str)
    errorRequested = Signal(str)
    navigationRequested = Signal(str, str)

    def __init__(
        self,
        session: ProjectSession,
        script_text_service,
        global_settings_service,
        parent: Optional[QObject] = None,
    ) -> None:
        super().__init__(parent)
        self._session = session
        self._script_text_service = script_text_service
        self._global_settings_service = global_settings_service
        self._search_result_count = 0
        self._search_query = ""
        self._search_sort_key = "episode"
        self._search_sort_ascending = True
        self._summary_target = ""
        self._summary_prepared = False
        self._summary_sort_key = "actor"
        self._summary_sort_ascending = True
        self._search_model = DictListModel({
            "episode": Qt.UserRole + 1,
            "time": Qt.UserRole + 2,
            "character": Qt.UserRole + 3,
            "text": Qt.UserRole + 4,
        }, self)
        self._summary_model = DictListModel({
            "actorId": Qt.UserRole + 1,
            "actor": Qt.UserRole + 2,
            "color": Qt.UserRole + 3,
            "rings": Qt.UserRole + 4,
            "words": Qt.UserRole + 5,
            "roles": Qt.UserRole + 6,
            "unassigned": Qt.UserRole + 7,
        }, self)

    @Property(int, notify=searchChanged)
    def searchResultCount(self) -> int:
        return self._search_result_count

    @Property(str, notify=summaryChanged)
    def summaryTarget(self) -> str:
        return self._summary_target

    @Property(str, notify=metricChanged)
    def projectSummaryMetric(self) -> str:
        return self._global_settings_service.get_project_summary_export_metric()

    @Property(QObject, constant=True)
    def searchModel(self) -> QObject:
        return self._search_model

    @Property(QObject, constant=True)
    def summaryModel(self) -> QObject:
        return self._summary_model

    @Property(str, notify=searchChanged)
    def searchSortKey(self) -> str:
        return self._search_sort_key

    @Property(bool, notify=searchChanged)
    def searchSortAscending(self) -> bool:
        return self._search_sort_ascending

    @Property(str, notify=summaryChanged)
    def summarySortKey(self) -> str:
        return self._summary_sort_key

    @Property(bool, notify=summaryChanged)
    def summarySortAscending(self) -> bool:
        return self._summary_sort_ascending

    @Slot(str, result=int)
    def search(self, query: str) -> int:
        needle = (query or "").strip().casefold()
        self._search_query = query or ""
        rows: List[Dict[str, Any]] = []
        if needle:
            for episode in sorted(
                self._session.data.get("episodes", {}),
                key=natural_sort_key,
            ):
                for line in self._get_episode_lines(str(episode)):
                    character = str(line.get("char") or "")
                    text = str(line.get("text") or "")
                    if (
                        needle not in character.casefold()
                        and needle not in text.casefold()
                    ):
                        continue
                    rows.append({
                        "episode": str(episode),
                        "time": str(
                            line.get("s_raw")
                            or _format_time(line.get("s"))
                        ),
                        "character": character,
                        "text": text,
                    })
        rows.sort(
            key=self._search_sort_value,
            reverse=not self._search_sort_ascending,
        )
        self._search_model.set_rows(rows)
        self._search_result_count = len(rows)
        self.searchChanged.emit()
        self.statusRequested.emit(
            f"Найдено: {len(rows)}" if needle else "Введите запрос для поиска"
        )
        return len(rows)

    @Slot(str)
    def setSearchSort(self, key: str) -> None:
        if key not in {"episode", "time", "character", "text"}:
            return
        if key == self._search_sort_key:
            self._search_sort_ascending = not self._search_sort_ascending
        else:
            self._search_sort_key = key
            self._search_sort_ascending = True
        self.search(self._search_query)

    @Slot(str, str)
    def openResult(self, episode: str, character: str) -> None:
        episode = str(episode or "")
        if episode not in self._session.data.get("episodes", {}):
            self.errorRequested.emit(
                "Серия из результата поиска больше не существует"
            )
            return
        self.navigationRequested.emit(episode, character or "")
        self.statusRequested.emit(f"Открыта серия {episode}: {character}")

    @Slot(str)
    def prepareSummary(self, target_episode: str) -> None:
        target_episode = str(target_episode or "")
        if (
            target_episode
            and target_episode not in self._session.data.get("episodes", {})
        ):
            self.errorRequested.emit("Выбранная серия больше не существует")
            return
        rows = CharacterStatsService(
            self._session.data
        ).actor_summary_rows(
            self._get_episode_lines,
            target_episode,
        )
        summary_rows = [
            {**row, "roles": ", ".join(row.get("roles", []))}
            for row in rows
        ]
        assigned_rows = [
            row for row in summary_rows if not row.get("unassigned")
        ]
        unassigned_rows = [
            row for row in summary_rows if row.get("unassigned")
        ]
        assigned_rows.sort(
            key=self._summary_sort_value,
            reverse=not self._summary_sort_ascending,
        )
        self._summary_model.set_rows(assigned_rows + unassigned_rows)
        self._summary_target = target_episode
        self._summary_prepared = True
        self.summaryChanged.emit()

    @Slot(str)
    def setSummarySort(self, key: str) -> None:
        if key not in {"actor", "rings", "words", "roles"}:
            return
        if key == self._summary_sort_key:
            self._summary_sort_ascending = not self._summary_sort_ascending
        else:
            self._summary_sort_key = key
            self._summary_sort_ascending = True
        if self._summary_prepared:
            self.prepareSummary(self._summary_target)

    @Slot(int)
    def copySearchResult(self, index: int) -> None:
        row = self._search_model.get(index)
        if not row:
            return
        QGuiApplication.clipboard().setText("\t".join((
            str(row.get("episode", "")), str(row.get("time", "")),
            str(row.get("character", "")), str(row.get("text", "")),
        )))
        self.statusRequested.emit("Результат поиска скопирован")

    @Slot(int)
    def copySummaryRow(self, index: int) -> None:
        row = self._summary_model.get(index)
        if not row:
            return
        QGuiApplication.clipboard().setText("\t".join((
            str(row.get("actor", "")), str(row.get("rings", "")),
            str(row.get("words", "")), str(row.get("roles", "")),
        )))
        self.statusRequested.emit("Строка отчёта скопирована")

    @Slot(str)
    def setProjectSummaryMetric(self, metric: str) -> None:
        metric = metric if metric in {"rings", "lines", "words"} else "rings"
        if metric == self.projectSummaryMetric:
            return
        self._global_settings_service.set_project_summary_export_metric(metric)
        settings = self._global_settings_service.get_settings()
        self._global_settings_service.save_settings(settings)
        self.metricChanged.emit()

    @Slot(str, str)
    def exportProjectSummaryXlsx(
        self,
        path_or_url: str,
        metric: str,
    ) -> None:
        path = _display_path(path_or_url)
        if not path:
            return
        output_path = Path(path).expanduser()
        if output_path.suffix.lower() != ".xlsx":
            output_path = output_path.with_suffix(".xlsx")
        metric = metric if metric in {"rings", "lines", "words"} else "rings"
        try:
            workbook = CharacterStatsService(
                self._session.data
            ).create_project_casting_xlsx(
                self._get_episode_lines,
                metric=metric,
            )
            workbook.save(output_path)
        except (ImportError, OSError) as exc:
            self.errorRequested.emit(f"Не удалось сохранить XLSX: {exc}")
            return
        self.setProjectSummaryMetric(metric)
        self.statusRequested.emit(f"Сводка сохранена: {output_path.name}")

    @Slot()
    def reset(self) -> None:
        self._search_model.set_rows([])
        self._summary_model.set_rows([])
        self._search_result_count = 0
        self._search_query = ""
        self._summary_target = ""
        self._summary_prepared = False
        self.searchChanged.emit()
        self.summaryChanged.emit()

    def refresh(self) -> None:
        if self._search_query.strip():
            self.search(self._search_query)
        if self._summary_prepared:
            self.prepareSummary(self._summary_target)

    def _search_sort_value(self, row: Dict[str, Any]):
        value = row.get(self._search_sort_key, "")
        if self._search_sort_key == "episode":
            return natural_sort_key(str(value))
        return str(value).casefold(), natural_sort_key(str(row.get("episode", "")))

    def _summary_sort_value(self, row: Dict[str, Any]):
        value = row.get(self._summary_sort_key, "")
        if self._summary_sort_key in {"rings", "words"}:
            sort_value: Any = int(value or 0)
        else:
            sort_value = str(value or "").casefold()
        return sort_value, str(row.get("actor", "")).casefold()

    def _get_episode_lines(self, episode: str) -> List[Dict[str, Any]]:
        return self._script_text_service.load_episode_lines(
            self._session.data,
            str(episode),
        )
