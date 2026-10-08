"""Feature backend for the QML audiobook workspace."""

from __future__ import annotations

from copy import deepcopy
import csv
import hashlib
import json
from pathlib import Path
from typing import Any, Optional

from lxml import etree
from lxml import html as lxml_html
from PySide6.QtCore import (
    QDir, QObject, Property, QTemporaryFile, QThread, QUrl, Signal,
    Slot, Qt, QTimer,
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


class _BookImportWorker(QObject):
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
        def progress(current: int, total: int) -> None:
            if QThread.currentThread().isInterruptionRequested():
                raise RuntimeError("Импорт отменён")
            self.progress.emit(current, total)

        try:
            chapters = BookImportService(self._keywords).import_file(
                self._path, progress
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
    editorFocusRequested = Signal(str, str)
    autoSaveRequested = Signal()
    selectionChanged = Signal()
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
        self._worker: Optional[_BookImportWorker] = None
        self._import_project: Optional[dict] = None
        self._shutting_down = False
        self._review_filter = REVIEW_ISSUES
        self._review_search = ""
        self._review_ignored: set[str] = set()
        self._review_rows_by_id: dict[str, dict[str, Any]] = {}
        self._editor_temp: Optional[QTemporaryFile] = None
        self._markup_temp: Optional[QTemporaryFile] = None
        self._editor_url = QUrl()
        self._editor_generation = 0
        self._editor_token = ""
        self._markup_url = QUrl()
        self._active = False
        self._committing = False
        self._pending = False
        self._selection: dict[str, Any] = {}
        self._selected_review = ""
        self._book_search = ""
        self._reading_speed = 150
        self._auto_save = True
        self._pronunciations: list[dict[str, str]] = []
        self._reviewed: dict[str, str] = {}
        self._retakes: list[dict[str, Any]] = []
        self._recording_positions: dict[str, list[str]] = {}
        self._recorded: dict[str, str] = {}
        self._palette_roles: list[str] = []
        self._chapter_cache: dict[str, tuple[str, dict[str, Any]]] = {}
        self._word_cache: dict[str, tuple[str, int]] = {}
        self._signature_cache: dict[str, tuple[str, str, str]] = {}
        self._save_timer = QTimer(self)
        self._save_timer.setSingleShot(True)
        self._save_timer.setInterval(900)
        self._save_timer.timeout.connect(self.flush)
        self._disk_timer = QTimer(self)
        self._disk_timer.setSingleShot(True)
        self._disk_timer.setInterval(5000)
        self._disk_timer.timeout.connect(self._auto_save_file)
        session.pendingEditsRequested.connect(self.flush)
        session.projectReplaced.connect(self._project_replaced)
        session.domainChanged.connect(self._session_changed)
        self._chapter_model = DictListModel({
            "title": Qt.UserRole + 1,
            "selected": Qt.UserRole + 2,
            "issues": Qt.UserRole + 3,
            "words": Qt.UserRole + 4,
            "ready": Qt.UserRole + 5,
            "id": Qt.UserRole + 6,
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
        self._roles_model = DictListModel({
            "slotIndex": Qt.UserRole + 1, "character": Qt.UserRole + 2,
            "actorId": Qt.UserRole + 3, "actorIndex": Qt.UserRole + 4,
            "color": Qt.UserRole + 5, "actorName": Qt.UserRole + 6,
        }, self)
        self._search_model = DictListModel({
            "itemId": Qt.UserRole + 1, "chapter": Qt.UserRole + 2,
            "snippet": Qt.UserRole + 3, "character": Qt.UserRole + 4,
        }, self)

    @Property(QObject, constant=True)
    def rolesModel(self) -> QObject:
        return self._roles_model

    @Property(QObject, constant=True)
    def searchModel(self) -> QObject:
        return self._search_model

    @Property("QVariantMap", notify=selectionChanged)
    def selection(self) -> dict[str, Any]:
        return deepcopy(self._selection)

    @Property(str, notify=reviewChanged)
    def selectedReviewId(self) -> str:
        return self._selected_review

    @Property("QVariantMap", notify=reviewChanged)
    def selectedReview(self) -> dict[str, Any]:
        return deepcopy(self._review_rows_by_id.get(self._selected_review, {}))

    @Property("QVariantList", notify=changed)
    def pronunciations(self) -> list[dict[str, str]]:
        return deepcopy(self._pronunciations)

    @Property("QVariantList", notify=changed)
    def retakes(self) -> list[dict[str, Any]]:
        return deepcopy(self._retakes)

    @Property("QVariantList", notify=changed)
    def recordedChapters(self) -> list[str]:
        return [title for title in self._order if self.chapterRecorded(title)]

    @Slot(str, result=bool)
    def hasChapter(self, title: str) -> bool:
        return any(c.get("title") == title for c in self._session.data.get("audiobook_document", {}).get("chapters", []))

    @Slot(str, "QVariantList", str, str)
    def addRetake(self, chapter: str, run_ids: list, text: str, note: str) -> None:
        ids = [str(i) for i in run_ids if i]
        if not ids or not self.hasChapter(chapter):
            return
        if not self._active:
            self.prepare()
        existing = next((r for r in self._retakes if r["chapter"] == chapter and r["runIds"] == ids), None)
        if existing:
            existing["note"] = note.strip() or "На перезапись"
        else:
            self._retakes.append({"chapter": chapter, "runIds": ids, "text": text, "note": note.strip() or "На перезапись"})
        self._schedule_save()
        self.statusRequested.emit("Фрагмент отмечен на перезапись")

    @Slot(str, "QVariantList")
    def removeRetake(self, chapter: str, run_ids: list) -> None:
        ids = [str(i) for i in run_ids]
        self._retakes = [r for r in self._retakes if r["chapter"] != chapter or r["runIds"] != ids]
        self._schedule_save()

    @Slot(str, "QVariantList")
    def saveRecordingPosition(self, chapter: str, run_ids: list) -> None:
        if self.hasChapter(chapter) and run_ids:
            self._recording_positions[chapter] = [str(i) for i in run_ids]
            self._schedule_save()

    @Slot(str, result="QVariantList")
    def recordingPosition(self, chapter: str) -> list[str]:
        return self._recording_positions.get(chapter, [])[:]

    @Slot(str, result=bool)
    def chapterRecorded(self, title: str) -> bool:
        return self._recorded.get(title) == self._chapter_signature(title)

    @Slot(str)
    def markChapterRecorded(self, title: str) -> None:
        if title in self._chapters:
            self._recorded[title] = self._chapter_signature(title)
            self._schedule_save()

    @Slot(str, result=bool)
    def exportRetakes(self, path_or_url: str) -> bool:
        try:
            path = self._local_path(path_or_url)
            with open(path, "w", newline="", encoding="utf-8-sig") as stream:
                writer = csv.writer(stream)
                writer.writerow(["Глава", "ID фрагментов", "Текст", "Примечание"])
                for row in self._retakes:
                    writer.writerow([row["chapter"], " ".join(row["runIds"]), row["text"], row["note"]])
            self.statusRequested.emit("Список перезаписей сохранён")
            return True
        except OSError as exc:
            self.errorRequested.emit(f"Не удалось сохранить список: {exc}")
            return False

    @Property(int, notify=changed)
    def nextSlot(self) -> int:
        return next((i for i, slot in enumerate(self._slots) if not slot.get("character")), -1)

    @Property(bool, notify=changed)
    def pending(self) -> bool:
        return self._pending

    @Property(bool, notify=changed)
    def autoSave(self) -> bool:
        return self._auto_save

    @Slot(bool)
    def setAutoSave(self, enabled: bool) -> None:
        self._auto_save = bool(enabled)
        if not enabled:
            self._disk_timer.stop()
        self._schedule_save()

    def _auto_save_file(self) -> None:
        self.flush()
        if self._auto_save and self._session.project_service.current_project_path and self._session.project_service.is_dirty:
            self.autoSaveRequested.emit()

    @Property(int, notify=changed)
    def readingSpeed(self) -> int:
        return self._reading_speed

    @Property(int, notify=changed)
    def chapterWords(self) -> int:
        return self._word_count(self._current)

    @Property(int, notify=changed)
    def bookWords(self) -> int:
        return sum(self._word_count(title) for title in self._order)

    @Property(str, notify=changed)
    def chapterDuration(self) -> str:
        return self._duration(self.chapterWords)

    @Property(str, notify=changed)
    def bookDuration(self) -> str:
        return self._duration(self.bookWords)

    @Property(int, notify=changed)
    def chapterIndex(self) -> int:
        return self._order.index(self._current) + 1 if self._current in self._order else 0

    @Property(int, notify=reviewChanged)
    def currentChapterIssues(self) -> int:
        return sum(1 for row in self._review_rows_by_id.values()
                   if row["chapter"] == self._current and row["issue"] and not row["ignored"])

    @Property(int, notify=reviewChanged)
    def readyChapters(self) -> int:
        return sum(1 for title in self._order if self._is_reviewed(title))

    @Property(bool, notify=reviewChanged)
    def currentChapterReady(self) -> bool:
        return self._is_reviewed(self._current)

    @Slot(str)
    def updateSelection(self, payload: str) -> None:
        try:
            self._selection = json.loads(payload)
        except (ValueError, TypeError):
            self._selection = {}
        self.selectionChanged.emit()

    @Slot()
    def flush(self) -> None:
        self._save_timer.stop()
        if self._pending and self._chapters:
            self.saveAll()

    def _project_replaced(self) -> None:
        self._save_timer.stop()
        self._disk_timer.stop()
        self._pending = False
        self._current = ""
        self._selected_review = ""
        if self._active:
            self.prepare()

    def _session_changed(self, domain: str) -> None:
        if not self._active or self._committing:
            return
        if domain in {"project", "working_text", "project_files", "actors", "assignments", "settings"}:
            if self._pending and domain in {"actors", "assignments", "settings"}:
                self._global_map = deepcopy(self._session.data.get("global_map", {}))
                self.flush()
            self.prepare()

    def _schedule_save(self) -> None:
        self._pending = True
        self._session.mark_dirty()
        self._save_timer.start()
        if self._auto_save:
            self._disk_timer.start()
        self.changed.emit()

    def _word_count(self, title: str) -> int:
        source = self._chapters.get(title, "")
        cached = self._word_cache.get(title)
        if cached and cached[0] == source:
            return cached[1]
        chapter = self._parsed_chapter(title)
        count = sum(len("".join(str(run.get("text", "")) for run in block["runs"]).split())
                    for block in chapter["blocks"] if block["type"] not in {"h1", "h2", "h3"})
        self._word_cache[title] = (source, count)
        return count

    def _parsed_chapter(self, title: str) -> dict[str, Any]:
        source = self._chapters.get(title, "")
        cached = self._chapter_cache.get(title)
        if cached and cached[0] == source:
            return cached[1]
        chapter = self._document_service.chapter_from_html(title, source)
        self._chapter_cache[title] = (source, chapter)
        return chapter

    def _duration(self, words: int) -> str:
        minutes = (words + self._reading_speed - 1) // self._reading_speed
        return f"≈ {minutes // 60} ч {minutes % 60:02d} мин" if minutes >= 60 else f"≈ {minutes} мин"

    def _chapter_signature(self, title: str) -> str:
        # IDs and rendering styles do not affect readiness; content and casting do.
        source = self._chapters.get(title, "")
        casting = json.dumps(self._global_map, sort_keys=True, ensure_ascii=False)
        cached = self._signature_cache.get(title)
        if cached and cached[:2] == (source, casting):
            return cached[2]
        chapter = self._parsed_chapter(title)
        content = [(b["type"], [(r.get("text"), r.get("character"), r.get("actor_id"))
                    for r in b["runs"]]) for b in chapter["blocks"]]
        signature = hashlib.sha256(json.dumps([content, self._global_map], ensure_ascii=False, sort_keys=True).encode()).hexdigest()
        self._signature_cache[title] = (source, casting, signature)
        return signature

    def _is_reviewed(self, title: str) -> bool:
        return bool(title and self._reviewed.get(title) == self._chapter_signature(title))

    @Slot(int)
    def setReadingSpeed(self, value: int) -> None:
        self._reading_speed = max(60, min(300, int(value)))
        self._schedule_save()

    @Slot(str, str, str)
    def savePronunciation(self, word: str, pronunciation: str, note: str) -> None:
        word, pronunciation = word.strip(), pronunciation.strip()
        if not word or not pronunciation:
            return
        self._pronunciations = [p for p in self._pronunciations if p["word"].casefold() != word.casefold()]
        self._pronunciations.append({"word": word, "pronunciation": pronunciation, "note": note.strip()})
        self._pronunciations.sort(key=lambda p: p["word"].casefold())
        self._schedule_save()

    @Slot(str)
    def removePronunciation(self, word: str) -> None:
        self._pronunciations = [p for p in self._pronunciations if p["word"] != word]
        self._schedule_save()

    @Slot(result=bool)
    def markChapterReviewed(self) -> bool:
        if not self._current or self.currentChapterIssues:
            self.statusRequested.emit("Сначала исправьте или пропустите замечания главы")
            return False
        self._reviewed[self._current] = self._chapter_signature(self._current)
        self._schedule_save()
        self._refresh_review()
        return True

    @Slot(str)
    def searchBook(self, query: str) -> None:
        self._book_search = query.strip()
        rows = self._review_service.filtered_rows(self._review_rows_by_id.values(), REVIEW_ALL, self._book_search) if self._book_search else []
        self._search_model.set_rows([{**r, "snippet": r["text"]} for r in rows])

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
        return Path(self._source_path).name if self._source_path else "Книга не импортирована"

    @Property(str, notify=editorChanged)
    def editorHtml(self) -> str:
        return editor_document(
            self._chapters.get(self._current, ""), self._font_family, self._zoom, self._editor_token
        )

    @Property(str, notify=editorChanged)
    def editorToken(self) -> str:
        return self._editor_token

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
        names.update(self._palette_roles)
        names.update(self._global_map)
        names.update(row["character"] for row in self._roles_model.rows())
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

    @Property("QVariantList", notify=changed)
    def roles(self) -> list[dict[str, Any]]:
        return deepcopy(self._roles_model.rows())

    @Property(str, notify=changed)
    def statsSummary(self) -> str:
        fragments = len(self._current_segments)
        words = sum(len(item.get("text", "").split()) for item in self._current_segments)
        return f"{fragments} фрагментов · {words} слов"

    @Property(bool, notify=changed)
    def canEditMarkup(self) -> bool:
        return bool(self._order)

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
        self._active = True
        self._save_timer.stop()
        self._pending = False
        previous_chapter = self._current
        self._chapter_cache.clear()
        self._word_cache.clear()
        self._signature_cache.clear()
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
        self._auto_save = bool(settings.get("auto_save", True))
        self._reading_speed = max(60, min(300, int(settings.get("reading_speed", 150))))
        self._pronunciations = deepcopy(settings.get("pronunciations", []))
        self._reviewed = deepcopy(settings.get("reviewed_chapters", {}))
        self._retakes = deepcopy(settings.get("retakes", []))
        self._recording_positions = deepcopy(settings.get("recording_positions", {}))
        self._recorded = deepcopy(settings.get("recorded_chapters", {}))
        self._palette_roles = list(settings.get("role_palette", []))
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
        if not any(slot.get("character") for slot in self._slots):
            names = ["Автор"] + sorted({str(run.get("character"))
                for chapter in structured_chapters for block in chapter.get("blocks", [])
                for run in block.get("runs", []) if run.get("character") and run["character"] != "Автор"})
            for index, name in enumerate(names[:9]):
                actor = self._global_map.get(name)
                self._slots[index] = {"character": name, "actor_id": actor if isinstance(actor, str) else None}
        self._refresh_actors()
        target = previous_chapter or str(settings.get("last_chapter", ""))
        self._current = target if target in self._order else (self._order[0] if self._order else "")
        self._selection = {}
        self.selectionChanged.emit()
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
        self._selection = {}
        self.selectionChanged.emit()
        self._current_segments = self._segments_from_html(self._chapters[title])
        self._refresh_models()
        self._refresh_editor_document()
        self.changed.emit()
        self.editorChanged.emit()

    @Slot(str, str)
    def updateEditorState(self, html_text: str, segments_json: str) -> None:
        if not self._current:
            return
        chapter = self._document_service.chapter_from_html(self._current, str(html_text))
        normalized = self._document_service.chapter_to_html(chapter)
        if self._chapters.get(self._current) == normalized:
            return
        self._chapters[self._current] = normalized
        try:
            payload = json.loads(segments_json)
            self._current_segments = [item for item in payload if isinstance(item, dict)]
        except (TypeError, ValueError):
            self._current_segments = self._segments_from_html(html_text)
        self._refresh_marked()
        self._refresh_review()
        self._schedule_save()

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
        self._schedule_save()

    @Slot(int, str, str, result=bool)
    def configureRole(self, index: int, character: str, actor_id: str) -> bool:
        character = character.strip()
        if not character or not -1 <= index < 9:
            return False
        if index >= 0 and any(i != index and s.get("character") == character for i, s in enumerate(self._slots)):
            self.errorRequested.emit("Эта роль уже есть в палитре")
            return False
        # Changing a cast assignment applies throughout the book, while changing
        # a shortcut's role does not rename previously marked manuscript text.
        current_changed = False
        for title in self._order:
            chapter = self._document_service.chapter_from_html(title, self._chapters[title])
            changed = False
            for block in chapter["blocks"]:
                for run in block["runs"]:
                    if run.get("character", "Автор") == character and (run.get("actor_id") or "") != actor_id:
                        changed = True
                        if actor_id:
                            run["actor_id"] = actor_id
                        else:
                            run.pop("actor_id", None)
            if changed:
                self._chapters[title] = self._document_service.chapter_to_html(chapter)
                current_changed = current_changed or title == self._current
        if character not in self._palette_roles:
            self._palette_roles.append(character)
        if index >= 0:
            self.setSlot(index, character, actor_id)
        else:
            if actor_id:
                self._global_map[character] = actor_id
            else:
                self._global_map.pop(character, None)
            self._schedule_save()
        if current_changed:
            self._reload_current()
        else:
            self._refresh_models()
            self.changed.emit()
        return True

    @Slot(int)
    def removeRoleShortcut(self, index: int) -> None:
        if 0 <= index < len(self._slots):
            self._slots[index] = {"character": "", "actor_id": None}
            self._refresh_slots()
            self._schedule_save()

    def _reload_current(self) -> None:
        self._current_segments = self._segments_from_html(self._chapters.get(self._current, ""))
        self._refresh_models()
        self._refresh_editor_document()
        self.changed.emit()
        self.editorChanged.emit()

    @Slot(str, str, str, result=bool)
    def resolveReviewItem(self, item_id: str, character: str, actor_id: str) -> bool:
        row = self._review_rows_by_id.get(item_id)
        character = character.strip()
        if not row or not character:
            return False
        title = row["chapter"]
        chapter = self._document_service.chapter_from_html(title, self._chapters[title])
        run = self._document_service._find_run({"chapters": [chapter]}, title, row["runId"])
        if run is None:
            return False
        run["character"] = character
        if actor_id:
            run["actor_id"] = actor_id
        else:
            run.pop("actor_id", None)
        self._chapters[title] = self._document_service.chapter_to_html(chapter)
        self._selected_review = ""
        self._schedule_save()
        self._reload_current()
        self.openNextReviewItem()
        return True

    @Slot()
    def openNextReviewItem(self) -> None:
        rows = self._review_model.rows()
        if rows:
            self.openReviewItem(rows[0]["itemId"])
        else:
            self._selected_review = ""
            self.reviewChanged.emit()

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
        self._selected_review = item_id
        chapter = str(row.get("chapter", ""))
        if chapter and chapter != self._current:
            self.selectChapter(chapter)
        self.reviewNavigationRequested.emit(str(row.get("text", "")))
        self.editorFocusRequested.emit(str(row.get("runId", "")), str(row.get("text", "")))
        self.reviewChanged.emit()

    @Slot(str)
    def ignoreReviewItem(self, item_id: str) -> None:
        item_id = str(item_id or "")
        row = self._review_rows_by_id.get(item_id)
        if not row or not row.get("issue"):
            return
        self.flush()
        self._review_ignored.add(item_id)
        self._store_review_ignored("Фрагмент исключён из проверки")

    @Slot()
    def resetIgnoredReviewItems(self) -> None:
        if not self._review_ignored:
            return
        self.flush()
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
            self._schedule_save()

    @Slot(int)
    def setZoom(self, value: int) -> None:
        value = max(-5, min(10, int(value)))
        if value != self._zoom:
            self._zoom = value
            self._schedule_save()

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
        self._pending = False
        self._save_timer.stop()
        self.changed.emit()
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
        self._save_timer.stop()
        self._pending = False
        self.changed.emit()
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
        self._import_project = self._session.data
        self._importing = True
        self._import_current = self._import_total = 0
        self.importChanged.emit()
        thread = QThread(self)
        worker = _BookImportWorker(path, list(keywords))
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.progress.connect(self._on_import_progress)
        worker.completed.connect(self._finish_import)
        worker.failed.connect(self._import_failed)
        worker.finished.connect(thread.quit, Qt.DirectConnection)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(self._import_finished)
        self._thread, self._worker = thread, worker
        thread.start()
        return True

    @Slot(str)
    def _import_failed(self, message: str) -> None:
        if not self._shutting_down and self._import_project is self._session.data:
            self.errorRequested.emit(message)

    @Slot()
    def shutdown(self) -> None:
        self._shutting_down = True
        self._disk_timer.stop()
        self.flush()
        if self._thread and self._thread.isRunning():
            self._thread.requestInterruption()
            self._thread.quit()
            self._thread.wait()

    @Slot(str, result=bool)
    def importBook(self, path_or_url: str) -> bool:
        self.flush()
        return self.importPdf(path_or_url)

    @Slot()
    def prepareChapterMarkup(self) -> None:
        self._markup_source = self._document_service.combined_html(self._live_document())
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
        self._selected_boundary = ""
        self._refresh_markup_model()
        self.markupChanged.emit()

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
        if not titles:
            self.errorRequested.emit("В книге должна остаться хотя бы одна глава")
            return False
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
        owners = {str(run["id"]): title for title in titles
                  for block in self._document_service.chapter_from_html(title, self._chapters[title])["blocks"]
                  for run in block["runs"]}
        self._recording_positions = {
            owners[ids[0]]: ids for ids in self._recording_positions.values() if ids and ids[0] in owners
        }
        for retake in self._retakes:
            if retake["runIds"] and retake["runIds"][0] in owners:
                retake["chapter"] = owners[retake["runIds"][0]]
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
        if self._shutting_down or self._import_project is not None and self._import_project is not self._session.data:
            return
        if not chapters:
            self.errorRequested.emit("В книге не найден текст")
            return
        service = BookImportService()
        existing = set(self._session.data.get("episodes", {})) - set(self._order)
        self._order = []
        self._chapters = {}
        for index, chapter in enumerate(chapters, 1):
            title = self._unique_title(chapter.title or f"Глава {index}", existing)
            existing.add(title)
            self._order.append(title)
            chapter.title = title
            canonical = self._document_service.chapter_from_html(title, service.chapter_to_html(chapter))
            self._chapters[title] = self._document_service.chapter_to_html(canonical)
        self._source_path = self._pending_path
        self._source_html = service.chapters_to_html(chapters)
        self._current = self._order[0] if self._order else ""
        if not any(slot.get("character") for slot in self._slots):
            self._slots = [{"character": "Автор", "actor_id": None}] + [{"character": "", "actor_id": None} for _ in range(8)]
        self._current_segments = self._segments_from_html(self._chapters.get(self._current, ""))
        candidate = deepcopy(self._session.data)
        maybe_set_project_name_from_first_import(
            candidate, self._source_path, {".pdf", ".docx", ".epub", ".txt"}
        )
        self._reviewed = {}
        self._review_ignored = set()
        self._retakes = []
        self._recording_positions = {}
        self._recorded = {}
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
        if self._auto_save:
            self._disk_timer.start()

    @Slot()
    def _import_finished(self) -> None:
        self._thread = None
        self._worker = None
        self._pending_path = ""
        self._import_project = None
        self._importing = False
        self.importChanged.emit()

    def _index_chapter(self, candidate: dict[str, Any], title: str) -> None:
        candidate.setdefault("episodes", {})[title] = "audiobook"

    def _write_common(self, candidate: dict[str, Any]) -> None:
        set_project_kind(candidate, "audiobook")
        document = self._document_service.create_document(
            self._source_path,
            [],
        )
        document["chapters"] = deepcopy([self._parsed_chapter(title) for title in self._order])
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
            "reading_speed": self._reading_speed,
            "pronunciations": deepcopy(self._pronunciations),
            "reviewed_chapters": deepcopy(self._reviewed),
            "last_chapter": self._current,
            "auto_save": self._auto_save,
            "retakes": deepcopy(self._retakes),
            "recording_positions": deepcopy(self._recording_positions),
            "recorded_chapters": deepcopy(self._recorded),
            "role_palette": self._palette_roles[:],
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
            domain = "working_text" if any(k not in {"audiobook_settings", "global_map"} for k in updates) else "assignments" if "global_map" in updates else "audiobook_settings"
            self._committing = True
            try:
                self._session.execute(UpdateProjectFileStateCommand(self._session.data, updates, description), domain)
                self.projectDataChanged.emit(domain)
            finally:
                self._committing = False

    def _refresh_models(self) -> None:
        self._refresh_slots()
        self._refresh_marked()
        self._refresh_review()

    def _refresh_editor_document(self) -> None:
        self._selection = {}
        self.selectionChanged.emit()
        self._editor_generation += 1
        self._editor_token = str(self._editor_generation)
        document = editor_document(
            self._chapters.get(self._current, ""), self._font_family, self._zoom, self._editor_token
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
        rows = [r for r in self._slot_rows() if r["character"]]
        shortcuts = {r["character"] for r in rows}
        names = set(self._palette_roles)
        names.update(run.get("character", "Автор") for title in self._order
                     for block in self._parsed_chapter(title)["blocks"] for run in block["runs"])
        actors = [row["actorId"] for row in self._actor_model.rows()]
        for name in sorted(names - shortcuts, key=str.casefold):
            actor_id = self.actorForCharacter(name)
            info = self._session.data.get("actors", {}).get(actor_id, {})
            rows.append({"slotIndex": -1, "character": name, "actorId": actor_id,
                         "actorIndex": actors.index(actor_id) if actor_id in actors else 0,
                         "actorName": str(info.get("name", "Не назначен")),
                         "color": str(info.get("color", "#8b8699"))})
        self._roles_model.set_rows(rows)

    @Slot(str, result=str)
    def actorForCharacter(self, character: str) -> str:
        actor = self._global_map.get(character, "")
        return actor if isinstance(actor, str) else ""

    def _slot_rows(self) -> list[dict[str, Any]]:
        actors = [row["actorId"] for row in self._actor_model.rows()]
        rows = []
        for index, slot in enumerate(self._slots):
            actor_id = slot.get("actor_id") or ""
            rows.append({
                "slotIndex": index, "character": slot.get("character", ""), "actorId": actor_id,
                "actorIndex": actors.index(actor_id) if actor_id in actors else 0,
                "color": str(self._session.data.get("actors", {}).get(actor_id, {}).get("color") or ["#367dc4", "#c88d25", "#8b62b9", "#4b9575"][index % 4]),
                "actorName": str(self._session.data.get("actors", {}).get(actor_id, {}).get("name", "Не назначен")),
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
        self._chapter_model.set_rows([
            {"id": title, "title": title, "selected": title == self._current,
             "issues": sum(1 for r in rows if r["chapter"] == title and r["issue"] and not r["ignored"]),
             "words": self._word_count(title), "ready": self._is_reviewed(title)}
            for title in self._order
        ])
        self.searchBook(self._book_search)

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
                self._parsed_chapter(title)
                for title in self._order
                if title in self._chapters
            ],
        }

    def _store_review_ignored(self, description: str) -> None:
        settings = deepcopy(
            self._session.data.get("audiobook_settings", {})
        )
        settings["review_ignored"] = sorted(self._review_ignored)
        self._committing = True
        try:
            self._session.execute(
                UpdateProjectFileStateCommand(self._session.data, {"audiobook_settings": settings}, description),
                "settings",
            )
        finally:
            self._committing = False
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
