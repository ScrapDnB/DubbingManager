"""Feature backend for the QML audiobook workspace."""

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
from typing import Any, Optional

from lxml import etree
from lxml import html as lxml_html
from PySide6.QtCore import (
    QDir, QObject, Property, QTemporaryFile, QThread, QUrl, Signal,
    Slot, Qt,
)
from PySide6.QtGui import QColor, QFontDatabase

from core.commands import UpdateProjectFileStateCommand
from services.audiobook_document_service import (
    AudiobookDocumentService,
)
from services.audiobook_pdf_export_service import AudiobookPdfExportService
from services.audiobook_review_service import (
    AudiobookReviewService,
    REVIEW_ALL,
    REVIEW_IGNORED,
    REVIEW_ISSUES,
    REVIEW_UNASSIGNED,
    REVIEW_UNMARKED_DIALOGUE,
)
from services.book_import_service import BookChapter, BookImportService
from services.project_metadata_service import maybe_set_project_name_from_first_import
from services.script_text_service import ScriptTextService
from ui.qml_backend.features.audiobook_html import (
    canonical_html,
    chapter_markup_document,
    editor_document,
)
from ui.qml_backend.models import DictListModel
from ui.qml_backend.project_session import ProjectSession
from utils.helpers import set_project_kind


class _PdfImportWorker(QObject):
    progress = Signal(int, int)
    completed = Signal(object)
    failed = Signal(str)
    finished = Signal()

    def __init__(self, path: str, keywords: list[str]) -> None:
        super().__init__()
        self._path = path
        self._keywords = keywords

    @Slot()
    def run(self) -> None:
        try:
            chapters = BookImportService(self._keywords).import_pdf(
                self._path, self.progress.emit
            )
            self.completed.emit(chapters)
        except Exception as exc:
            self.failed.emit(str(exc))
        finally:
            self.finished.emit()


class AudiobookBridge(QObject):
    changed = Signal()
    editorChanged = Signal()
    markupChanged = Signal()
    importChanged = Signal()
    projectDataChanged = Signal(str)
    projectNameChanged = Signal()
    reviewChanged = Signal()
    reviewNavigationRequested = Signal(str)
    statusRequested = Signal(str)
    errorRequested = Signal(str)

    def __init__(
        self,
        session: ProjectSession,
        script_text_service: ScriptTextService,
        global_settings_service,
        parent: Optional[QObject] = None,
    ) -> None:
        super().__init__(parent)
        self._session = session
        self._script_text_service = script_text_service
        self._document_service = AudiobookDocumentService()
        self._pdf_export_service = AudiobookPdfExportService()
        self._review_service = AudiobookReviewService()
        self._global_settings_service = global_settings_service
        self._chapters: dict[str, str] = {}
        self._order: list[str] = []
        self._source_path = ""
        self._source_html = ""
        self._current = ""
        self._current_segments: list[dict[str, str]] = []
        self._font_family = "Georgia"
        self._zoom = 0
        self._slots: list[dict[str, Any]] = []
        self._global_map: dict[str, str] = {}
        self._markup_chapters: list[dict[str, str]] = []
        self._markup_source = ""
        self._selected_boundary = ""
        self._importing = False
        self._import_current = 0
        self._import_total = 0
        self._pending_path = ""
        self._thread: Optional[QThread] = None
        self._worker: Optional[_PdfImportWorker] = None
        self._review_filter = REVIEW_ISSUES
        self._review_search = ""
        self._review_ignored: set[str] = set()
        self._review_rows_by_id: dict[str, dict[str, Any]] = {}
        self._editor_temp: Optional[QTemporaryFile] = None
        self._markup_temp: Optional[QTemporaryFile] = None
        self._editor_url = QUrl()
        self._markup_url = QUrl()
        self._chapter_model = DictListModel({
            "title": Qt.UserRole + 1,
            "selected": Qt.UserRole + 2,
        }, self)
        self._slot_model = DictListModel({
            "slotIndex": Qt.UserRole + 1,
            "character": Qt.UserRole + 2,
            "actorId": Qt.UserRole + 3,
            "actorIndex": Qt.UserRole + 4,
            "color": Qt.UserRole + 5,
        }, self)
        self._actor_model = DictListModel({
            "actorId": Qt.UserRole + 1,
            "name": Qt.UserRole + 2,
            "color": Qt.UserRole + 3,
        }, self)
        self._marked_model = DictListModel({
            "character": Qt.UserRole + 1,
            "fragments": Qt.UserRole + 2,
            "words": Qt.UserRole + 3,
            "summary": Qt.UserRole + 4,
        }, self)
        self._markup_model = DictListModel({
            "title": Qt.UserRole + 1,
            "selected": Qt.UserRole + 2,
        }, self)
        self._review_model = DictListModel({
            "itemId": Qt.UserRole + 1,
            "chapter": Qt.UserRole + 2,
            "character": Qt.UserRole + 3,
            "aliases": Qt.UserRole + 4,
            "snippet": Qt.UserRole + 5,
            "kind": Qt.UserRole + 6,
            "kindLabel": Qt.UserRole + 7,
            "issue": Qt.UserRole + 8,
            "ignored": Qt.UserRole + 9,
            "runId": Qt.UserRole + 10,
        }, self)

    @Property(QObject, constant=True)
    def chaptersModel(self) -> QObject:
        return self._chapter_model

    @Property(QObject, constant=True)
    def slotsModel(self) -> QObject:
        return self._slot_model

    @Property(QObject, constant=True)
    def actorsModel(self) -> QObject:
        return self._actor_model

    @Property(QObject, constant=True)
    def markedModel(self) -> QObject:
        return self._marked_model

    @Property(QObject, constant=True)
    def markupChaptersModel(self) -> QObject:
        return self._markup_model

    @Property(QObject, constant=True)
    def reviewModel(self) -> QObject:
        return self._review_model

    @Property(str, notify=reviewChanged)
    def reviewFilter(self) -> str:
        return self._review_filter

    @Property(str, notify=reviewChanged)
    def reviewSearch(self) -> str:
        return self._review_search

    @Property(int, notify=reviewChanged)
    def reviewCount(self) -> int:
        return sum(
            1 for row in self._review_rows_by_id.values()
            if row.get("issue") and not row.get("ignored")
        )

    @Property(str, notify=reviewChanged)
    def reviewSummary(self) -> str:
        total = len(self._review_rows_by_id)
        return f"{self.reviewCount} проблем · {total} фрагментов"

    @Property(str, notify=changed)
    def currentChapter(self) -> str:
        return self._current

    @Property("QVariantList", notify=changed)
    def chapterTitles(self) -> list[str]:
        return list(self._order)

    @Property(str, notify=changed)
    def sourceName(self) -> str:
        return Path(self._source_path).name if self._source_path else "PDF не импортирован"

    @Property(str, notify=editorChanged)
    def editorHtml(self) -> str:
        return editor_document(
            self._chapters.get(self._current, ""), self._font_family, self._zoom
        )

    @Property(QUrl, notify=editorChanged)
    def editorUrl(self) -> QUrl:
        return self._editor_url

    @Property(str, notify=markupChanged)
    def chapterMarkupHtml(self) -> str:
        return chapter_markup_document(self._markup_source, self._markup_chapters)

    @Property(QUrl, notify=markupChanged)
    def chapterMarkupUrl(self) -> QUrl:
        return self._markup_url

    @Property(str, notify=markupChanged)
    def selectedBoundary(self) -> str:
        return self._selected_boundary

    @Property(str, notify=changed)
    def fontFamily(self) -> str:
        return self._font_family

    @Property(int, notify=changed)
    def zoom(self) -> int:
        return self._zoom

    @Property("QVariantList", constant=True)
    def fontFamilies(self) -> list[str]:
        preferred = ["Georgia", "Charter", "Palatino", "Times New Roman", "Arial"]
        available = QFontDatabase.families()
        return list(dict.fromkeys([name for name in preferred if name in available] + available))

    @Property("QVariantList", notify=changed)
    def characterNames(self) -> list[str]:
        names = {"Автор"}
        names.update(self._global_map)
        names.update(
            str(segment.get("character", ""))
            for segment in self._current_segments
            if segment.get("character")
        )
        names.update(slot.get("character", "") for slot in self._slots)
        return [""] + sorted((name for name in names if name), key=str.casefold)

    @Property("QVariantList", notify=changed)
    def slots(self) -> list[dict[str, Any]]:
        return deepcopy(self._slot_rows())

    @Property(str, notify=changed)
    def statsSummary(self) -> str:
        fragments = len(self._current_segments)
        words = sum(len(item.get("text", "").split()) for item in self._current_segments)
        return f"{fragments} фрагментов · {words} слов"

    @Property(bool, notify=changed)
    def canEditMarkup(self) -> bool:
        return bool(self._source_html)

    @Property(bool, notify=importChanged)
    def importing(self) -> bool:
        return self._importing

    @Property(int, notify=importChanged)
    def importCurrent(self) -> int:
        return self._import_current

    @Property(int, notify=importChanged)
    def importTotal(self) -> int:
        return self._import_total

    @Slot()
    def prepare(self) -> None:
        data = self._session.data
        document = data.get("audiobook_document", {})
        source = document.get("source", {}) if isinstance(document, dict) else {}
        self._source_path = str(source.get("path", ""))
        structured_chapters = (
            document.get("chapters", []) if isinstance(document, dict) else []
        )
        self._order = self._document_service.chapter_titles(document)
        actor_colors = {
            str(actor_id): self._highlight_color(str(actor.get("color", "")))
            for actor_id, actor in data.get("actors", {}).items()
        }
        self._chapters = {
            str(chapter.get("title")): self._document_service.chapter_to_html(
                chapter, actor_colors
            )
            for chapter in structured_chapters
            if str(chapter.get("title", ""))
        }
        self._source_html = self._document_service.combined_html(document)
        settings = data.get("audiobook_settings", {})
        self._font_family = str(settings.get("font_family", "Georgia"))
        self._zoom = max(-5, min(10, int(settings.get("zoom_steps", 0))))
        self._slots = [
            {
                "character": str(item.get("character", "")),
                "actor_id": item.get("actor_id"),
            }
            for item in settings.get("slots", [])[:9]
        ]
        self._slots.extend({"character": "", "actor_id": None} for _ in range(9 - len(self._slots)))
        ignored = settings.get("review_ignored", [])
        self._review_ignored = {
            str(value) for value in ignored
        } if isinstance(ignored, list) else set()
        self._global_map = deepcopy(data.get("global_map", {}))
        self._refresh_actors()
        self._current = self._order[0] if self._order else ""
        self._current_segments = self._segments_from_html(self._chapters.get(self._current, ""))
        self._refresh_models()
        self._refresh_editor_document()
        self.changed.emit()
        self.editorChanged.emit()

    @Slot(str)
    def selectChapter(self, title: str) -> None:
        title = str(title or "")
        if title == self._current or title not in self._chapters:
            return
        self._current = title
        self._current_segments = self._segments_from_html(self._chapters[title])
        self._refresh_models()
        self._refresh_editor_document()
        self.changed.emit()
        self.editorChanged.emit()

    @Slot(str, str)
    def updateEditorState(self, html_text: str, segments_json: str) -> None:
        if not self._current:
            return
        self._chapters[self._current] = str(html_text)
        try:
            payload = json.loads(segments_json)
            self._current_segments = [item for item in payload if isinstance(item, dict)]
        except (TypeError, ValueError):
            self._current_segments = self._segments_from_html(html_text)
        self._refresh_marked()
        self._refresh_review()
        self.changed.emit()

    @Slot(int, str, str)
    def setSlot(self, index: int, character: str, actor_id: str) -> None:
        if not 0 <= index < 9:
            return
        character = str(character or "").strip()
        actor_id = str(actor_id or "") or None
        self._slots[index] = {"character": character, "actor_id": actor_id}
        if character:
            if actor_id:
                self._global_map[character] = actor_id
            else:
                self._global_map.pop(character, None)
        self._refresh_slots()
        self._refresh_review()
        self.changed.emit()

    @Slot(str)
    def setReviewFilter(self, value: str) -> None:
        allowed = {
            REVIEW_ALL,
            REVIEW_ISSUES,
            REVIEW_UNMARKED_DIALOGUE,
            REVIEW_UNASSIGNED,
            REVIEW_IGNORED,
        }
        value = str(value or REVIEW_ISSUES)
        if value not in allowed or value == self._review_filter:
            return
        self._review_filter = value
        self._apply_review_filter()

    @Slot(str)
    def setReviewSearch(self, value: str) -> None:
        value = " ".join(str(value or "").split())
        if value == self._review_search:
            return
        self._review_search = value
        self._apply_review_filter()

    @Slot(str)
    def openReviewItem(self, item_id: str) -> None:
        row = self._review_rows_by_id.get(str(item_id or ""))
        if not row:
            return
        chapter = str(row.get("chapter", ""))
        if chapter and chapter != self._current:
            self.selectChapter(chapter)
        self.reviewNavigationRequested.emit(str(row.get("text", "")))

    @Slot(str)
    def ignoreReviewItem(self, item_id: str) -> None:
        item_id = str(item_id or "")
        row = self._review_rows_by_id.get(item_id)
        if not row or not row.get("issue"):
            return
        self._review_ignored.add(item_id)
        self._store_review_ignored("Фрагмент исключён из проверки")

    @Slot()
    def resetIgnoredReviewItems(self) -> None:
        if not self._review_ignored:
            return
        self._review_ignored.clear()
        self._store_review_ignored("Возвращены пропущенные проверки")

    @Slot("QVariantList", str, bool, bool, result=bool)
    def exportPdf(
        self,
        chapter_titles: list,
        path_or_url: str,
        separate_files: bool,
        studio_layout: bool,
    ) -> bool:
        titles = [str(value) for value in chapter_titles if str(value)]
        path = self._local_path(path_or_url)
        if not titles or not path:
            self.errorRequested.emit("Выберите главы и место экспорта")
            return False
        try:
            document = self._live_document()
            if separate_files:
                paths = self._pdf_export_service.export_separate(
                    document,
                    self._session.data,
                    titles,
                    path,
                    studio_layout,
                )
                self.statusRequested.emit(
                    f"Экспортировано PDF: {len(paths)}"
                )
            else:
                saved = self._pdf_export_service.export_combined(
                    document,
                    self._session.data,
                    titles,
                    path,
                    studio_layout,
                )
                self.statusRequested.emit(f"PDF сохранён: {saved}")
            return True
        except Exception as exc:
            self.errorRequested.emit(f"Не удалось экспортировать PDF: {exc}")
            return False

    @Slot(str)
    def setFontFamily(self, family: str) -> None:
        family = str(family or "").strip()
        if family and family != self._font_family:
            self._font_family = family
            self._refresh_editor_document()
            self.changed.emit()
            self.editorChanged.emit()

    @Slot(int)
    def setZoom(self, value: int) -> None:
        value = max(-5, min(10, int(value)))
        if value != self._zoom:
            self._zoom = value
            self._refresh_editor_document()
            self.changed.emit()
            self.editorChanged.emit()

    @Slot(int, result="QVariantMap")
    def slotPayload(self, index: int) -> dict[str, Any]:
        rows = self._slot_rows()
        return rows[index] if 0 <= index < len(rows) else {}

    @Slot(str, result=str)
    def actorColor(self, actor_id: str) -> str:
        color = self._session.data.get("actors", {}).get(str(actor_id or ""), {}).get("color")
        return self._highlight_color(str(color or "#f1d77a"))

    @Slot(result=bool)
    def saveCurrent(self) -> bool:
        if not self._current:
            return False
        candidate = deepcopy(self._session.data)
        self._index_chapter(candidate, self._current)
        self._write_common(candidate)
        self._commit(candidate, f"Сохранена глава {self._current}")
        self.statusRequested.emit(f"Глава «{self._current}» сохранена")
        return True

    @Slot(result=bool)
    def saveAll(self) -> bool:
        if not self._chapters:
            return False
        candidate = deepcopy(self._session.data)
        for title in self._order:
            self._index_chapter(candidate, title)
        self._write_common(candidate)
        self._commit(candidate, "Сохранена разметка аудиокниги")
        self.statusRequested.emit(f"Сохранено глав: {len(self._order)}")
        return True

    @Slot(str, result=bool)
    def importPdf(self, path_or_url: str) -> bool:
        if self._importing:
            return False
        path = self._local_path(path_or_url)
        if not path:
            return False
        keywords = self._global_settings_service.get_audiobook_config().get("chapter_keywords", [])
        self._pending_path = path
        self._importing = True
        self._import_current = self._import_total = 0
        self.importChanged.emit()
        thread = QThread(self)
        worker = _PdfImportWorker(path, list(keywords))
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.progress.connect(self._on_import_progress)
        worker.completed.connect(self._finish_import)
        worker.failed.connect(self.errorRequested)
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(self._import_finished)
        self._thread, self._worker = thread, worker
        thread.start()
        return True

    @Slot()
    def prepareChapterMarkup(self) -> None:
        self._markup_source = self._source_html
        self._markup_chapters = [
            {"title": title, "html": self._chapters[title]} for title in self._order
        ]
        self._selected_boundary = self._order[0] if self._order else ""
        self._refresh_markup_model()
        self._refresh_markup_document()
        self.markupChanged.emit()

    @Slot(str)
    def updateBoundaries(self, payload_json: str) -> None:
        try:
            payload = json.loads(payload_json)
            chapters = payload.get("chapters", [])
            if not isinstance(chapters, list):
                return
            self._markup_source = str(payload.get("sourceHtml", ""))
            self._markup_chapters = [
                {"title": str(item.get("title", "")).strip(), "html": str(item.get("html", ""))}
                for item in chapters if str(item.get("title", "")).strip()
            ]
            titles = [item["title"] for item in self._markup_chapters]
            if self._selected_boundary not in titles:
                self._selected_boundary = titles[0] if titles else ""
            self._refresh_markup_model()
            self.markupChanged.emit()
        except (TypeError, ValueError):
            return

    @Slot(str)
    def selectBoundary(self, title: str) -> None:
        self._selected_boundary = str(title or "")
        self._refresh_markup_model()
        self.markupChanged.emit()

    @Slot(str, str)
    def boundaryRenamed(self, old_title: str, new_title: str) -> None:
        self._selected_boundary = str(new_title or "")

    @Slot(str)
    def boundaryDeleted(self, _title: str) -> None:
        pass

    @Slot(result=str)
    def suggestedChapterTitle(self) -> str:
        existing = {item["title"] for item in self._markup_chapters}
        number = 1
        while f"Глава {number}" in existing:
            number += 1
        return f"Глава {number}"

    @Slot(result=bool)
    def applyChapterMarkup(self) -> bool:
        titles = [item["title"] for item in self._markup_chapters]
        if len(titles) != len(set(titles)):
            self.errorRequested.emit("Названия глав не должны повторяться")
            return False
        candidate = deepcopy(self._session.data)
        old_titles = set(self._order)
        new_titles = set(titles)
        for title in old_titles - new_titles:
            self._remove_episode(candidate, title)
        for item in self._markup_chapters:
            self._index_chapter(candidate, item["title"])
        self._order = titles
        self._chapters = {item["title"]: item["html"] for item in self._markup_chapters}
        self._source_html = self._markup_source
        self._write_common(candidate)
        self._commit(candidate, "Изменена структура глав аудиокниги")
        self._current = self._selected_boundary if self._selected_boundary in self._chapters else (titles[0] if titles else "")
        self._current_segments = self._segments_from_html(self._chapters.get(self._current, ""))
        self._refresh_models()
        self._refresh_editor_document()
        self.changed.emit()
        self.editorChanged.emit()
        self.statusRequested.emit("Структура глав обновлена")
        return True

    @Slot(int, int)
    def _on_import_progress(self, current: int, total: int) -> None:
        self._import_current, self._import_total = current, total
        self.importChanged.emit()

    @Slot(object)
    def _finish_import(self, chapters: list[BookChapter]) -> None:
        service = BookImportService()
        existing = set(self._session.data.get("episodes", {})) - set(self._order)
        self._order = []
        self._chapters = {}
        for index, chapter in enumerate(chapters, 1):
            title = self._unique_title(chapter.title or f"Глава {index}", existing)
            existing.add(title)
            self._order.append(title)
            chapter.title = title
            self._chapters[title] = service.chapter_to_html(chapter)
        self._source_path = self._pending_path
        self._source_html = service.chapters_to_html(chapters)
        self._current = self._order[0] if self._order else ""
        self._current_segments = self._segments_from_html(self._chapters.get(self._current, ""))
        candidate = deepcopy(self._session.data)
        maybe_set_project_name_from_first_import(
            candidate, self._source_path, {".pdf"}
        )
        for title in list(candidate.get("episodes", {})):
            if title not in self._order:
                self._remove_episode(candidate, title)
        for title in self._order:
            self._index_chapter(candidate, title)
        self._write_common(candidate)
        self._commit(candidate, f"Импортирована аудиокнига {Path(self._source_path).name}")
        self.projectNameChanged.emit()
        self._refresh_models()
        self._refresh_editor_document()
        self.changed.emit()
        self.editorChanged.emit()
        self.statusRequested.emit(f"Импортировано глав: {len(self._order)}")

    @Slot()
    def _import_finished(self) -> None:
        self._thread = None
        self._worker = None
        self._pending_path = ""
        self._importing = False
        self.importChanged.emit()

    def _index_chapter(self, candidate: dict[str, Any], title: str) -> None:
        candidate.setdefault("episodes", {})[title] = "audiobook"

    def _write_common(self, candidate: dict[str, Any]) -> None:
        set_project_kind(candidate, "audiobook")
        document = self._document_service.create_document(
            self._source_path,
            ((title, self._chapters[title]) for title in self._order),
        )
        previous = candidate.get("audiobook_document", {})
        if (
            isinstance(previous, dict)
            and previous.get("source", {}).get("path") == self._source_path
        ):
            document["source"] = deepcopy(previous.get("source", {}))
        candidate["audiobook_document"] = document
        settings = deepcopy(candidate.get("audiobook_settings", {}))
        settings.update({
            "font_family": self._font_family,
            "zoom_steps": self._zoom,
            "slots": deepcopy(self._slots),
            "review_ignored": sorted(self._review_ignored),
        })
        candidate["audiobook_settings"] = settings
        candidate["global_map"] = deepcopy(self._global_map)
        if candidate.get("project_kind") == "audiobook":
            candidate["episode_working_texts"] = {}
            candidate["episode_texts"] = {}
            candidate.pop("loaded_episodes", None)

    def _commit(self, candidate: dict[str, Any], description: str) -> None:
        fields = (
            "project_name", "project_kind", "episodes", "audiobook_document",
            "loaded_episodes", "episode_texts", "episode_working_texts",
            "episode_actor_map", "audiobook_settings", "global_map",
        )
        updates = {
            field: candidate.get(field)
            for field in fields
            if candidate.get(field) != self._session.data.get(field)
            or (field in self._session.data) != (field in candidate)
        }
        if updates:
            self._session.execute(UpdateProjectFileStateCommand(self._session.data, updates, description), "working_text")
            self.projectDataChanged.emit("working_text")

    def _refresh_models(self) -> None:
        self._chapter_model.set_rows([
            {"title": title, "selected": title == self._current} for title in self._order
        ])
        self._refresh_slots()
        self._refresh_marked()
        self._refresh_review()

    def _refresh_editor_document(self) -> None:
        document = editor_document(
            self._chapters.get(self._current, ""), self._font_family, self._zoom
        )
        self._editor_temp, self._editor_url = self._temporary_document(
            document, "dm-audiobook-editor-XXXXXX.html"
        )

    def _refresh_markup_document(self) -> None:
        document = chapter_markup_document(
            self._markup_source, self._markup_chapters
        )
        self._markup_temp, self._markup_url = self._temporary_document(
            document, "dm-audiobook-chapters-XXXXXX.html"
        )

    @staticmethod
    def _temporary_document(
        content: str, template: str,
    ) -> tuple[QTemporaryFile, QUrl]:
        temporary = QTemporaryFile(str(Path(QDir.tempPath()) / template))
        temporary.setAutoRemove(True)
        if not temporary.open():
            return temporary, QUrl()
        temporary.write(content.encode("utf-8"))
        temporary.flush()
        return temporary, QUrl.fromLocalFile(temporary.fileName())

    def _refresh_slots(self) -> None:
        self._slot_model.set_rows(self._slot_rows())

    def _slot_rows(self) -> list[dict[str, Any]]:
        actors = [row["actorId"] for row in self._actor_model.rows()]
        rows = []
        for index, slot in enumerate(self._slots):
            actor_id = slot.get("actor_id") or ""
            rows.append({
                "slotIndex": index, "character": slot.get("character", ""), "actorId": actor_id,
                "actorIndex": actors.index(actor_id) if actor_id in actors else 0,
                "color": self.actorColor(actor_id),
            })
        return rows

    def _refresh_actors(self) -> None:
        rows = [{"actorId": "", "name": "Без актёра", "color": "#f1d77a"}]
        rows.extend({"actorId": str(actor_id), "name": str(info.get("name", actor_id)), "color": str(info.get("color", "#f1d77a"))} for actor_id, info in self._session.data.get("actors", {}).items())
        self._actor_model.set_rows(rows)

    def _refresh_marked(self) -> None:
        stats: dict[str, list[int]] = {}
        for segment in self._current_segments:
            character = str(segment.get("character") or "Автор")
            entry = stats.setdefault(character, [0, 0])
            entry[0] += 1
            entry[1] += len(str(segment.get("text", "")).split())
        self._marked_model.set_rows([
            {"character": name, "fragments": values[0], "words": values[1], "summary": f"{values[0]} фр. · {values[1]} слов"}
            for name, values in sorted(stats.items(), key=lambda item: item[0].casefold())
        ])

    def _refresh_review(self) -> None:
        rows = self._review_service.rows(
            self._live_document(), self._session.data, self._review_ignored
        )
        self._review_rows_by_id = {
            str(row["itemId"]): row for row in rows
        }
        self._apply_review_filter()

    def _apply_review_filter(self) -> None:
        rows = self._review_service.filtered_rows(
            self._review_rows_by_id.values(),
            self._review_filter,
            self._review_search,
        )
        self._review_model.set_rows([
            {**row, "snippet": str(row.get("text", ""))}
            for row in rows
        ])
        self.reviewChanged.emit()

    def _live_document(self) -> dict[str, Any]:
        source = self._session.data.get("audiobook_document", {}).get(
            "source", {}
        )
        return {
            "format_version": "1.0",
            "source": deepcopy(source),
            "chapters": [
                self._document_service.chapter_from_html(
                    title, self._chapters[title]
                )
                for title in self._order
                if title in self._chapters
            ],
        }

    def _store_review_ignored(self, description: str) -> None:
        settings = deepcopy(
            self._session.data.get("audiobook_settings", {})
        )
        settings["review_ignored"] = sorted(self._review_ignored)
        self._session.execute(
            UpdateProjectFileStateCommand(
                self._session.data,
                {"audiobook_settings": settings},
                description,
            ),
            "settings",
        )
        self.projectDataChanged.emit("settings")
        self._refresh_review()
        self.statusRequested.emit(description)

    def _refresh_markup_model(self) -> None:
        self._markup_model.set_rows([
            {"title": item["title"], "selected": item["title"] == self._selected_boundary}
            for item in self._markup_chapters
        ])

    def _segments_from_html(self, html_text: str) -> list[dict[str, str]]:
        try:
            root = lxml_html.document_fromstring(html_text or canonical_html(""))
            body = root.find("body")
            if body is None:
                body = root
        except (etree.ParserError, ValueError):
            return []
        result: list[dict[str, str]] = []
        current = "Автор"
        parts: list[str] = []

        def flush() -> None:
            nonlocal parts
            text = " ".join("".join(parts).split())
            if text:
                result.append({"character": current, "text": text})
            parts = []

        def walk(node, inherited: str) -> None:
            nonlocal current
            character = str(node.attrib.get("data-dm-character", inherited))
            if character != current:
                flush()
                current = character
            if node.text:
                parts.append(node.text)
            for child in node:
                walk(child, character)
                if child.tail:
                    if character != current:
                        flush()
                        current = character
                    parts.append(child.tail)
                if child.tag.lower() in {"p", "div", "h1", "h2", "h3", "li", "br"}:
                    parts.append(" ")
        walk(body, "Автор")
        flush()
        return result

    @staticmethod
    def _highlight_color(color: str) -> str:
        value = QColor(color)
        if not value.isValid():
            value = QColor("#f1d77a")
        return value.lighter(155).name()

    @staticmethod
    def _unique_title(title: str, existing: set[str]) -> str:
        base = " ".join(str(title).split()) or "Глава"
        candidate, number = base, 2
        while candidate in existing:
            candidate = f"{base} {number}"
            number += 1
        return candidate

    @staticmethod
    def _remove_episode(data: dict[str, Any], title: str) -> None:
        for key in ("episodes", "loaded_episodes", "episode_texts", "episode_working_texts", "episode_actor_map", "video_paths"):
            data.get(key, {}).pop(title, None)

    @staticmethod
    def _local_path(path_or_url: str) -> str:
        url = QUrl(str(path_or_url or ""))
        return url.toLocalFile() if url.isLocalFile() else str(path_or_url or "")
