"""Audiobook chapter import and manual markup window."""

from __future__ import annotations

import html as html_lib
import re
from typing import Any, Dict, List, Optional
from urllib.parse import quote, unquote

from PySide6.QtCore import QEvent, QObject, QThread, Qt, Signal, Slot
from PySide6.QtGui import (
    QColor,
    QFont,
    QPainter,
    QPen,
    QTextBlockFormat,
    QTextCharFormat,
    QTextCursor,
    QTextFormat,
)
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFileDialog,
    QFontComboBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSplitter,
    QTextEdit,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from services.book_import_service import BookChapter, BookImportService
from services.assignment_service import get_actor_for_character
from services.project_metadata_service import maybe_set_project_name_from_first_import
from services.script_text_service import ScriptTextService
from utils.helpers import set_audiobook_chapter_order, set_project_kind


CHARACTER_PROP = QTextCharFormat.UserProperty + 41
CHAPTER_PROP = QTextCharFormat.UserProperty + 42


def body_inner_html(html_text: str) -> str:
    match = re.search(
        r"<body[^>]*>(.*)</body>",
        html_text,
        flags=re.IGNORECASE | re.DOTALL,
    )
    return match.group(1) if match else html_text


def chapter_title_html(title: str) -> str:
    return (
        "<h1 style=\"font-size:22pt; font-weight:600; "
        "margin-top:0; margin-bottom:18px;\">"
        f"{html_lib.escape(title)}</h1>"
    )


def body_without_first_heading(html_text: str) -> str:
    body = body_inner_html(html_text)
    return re.sub(
        r"^\s*<h1\b[^>]*>.*?</h1>\s*",
        "",
        body,
        count=1,
        flags=re.IGNORECASE | re.DOTALL,
    )


def html_with_title(title: str, body_html: str) -> str:
    body = body_without_first_heading(body_html)
    return (
        "<!DOCTYPE HTML><html><head><meta charset=\"utf-8\"></head><body>"
        f"{chapter_title_html(title)}{body}</body></html>"
    )


def rename_html_heading(html_text: str, title: str) -> str:
    body = body_inner_html(html_text)
    if re.search(r"<h1\b", body, flags=re.IGNORECASE):
        body = re.sub(
            r"<h1\b[^>]*>.*?</h1>",
            chapter_title_html(title),
            body,
            count=1,
            flags=re.IGNORECASE | re.DOTALL,
        )
    else:
        body = f"{chapter_title_html(title)}{body}"
    return (
        "<!DOCTYPE HTML><html><head><meta charset=\"utf-8\"></head><body>"
        f"{body}</body></html>"
    )


class ChapterSourceEditor(QTextEdit):
    """Read-only book editor with a persistent visual chapter cut cursor."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._insertion_cursor: Optional[QTextCursor] = None
        self._insertion_color = QColor("#3A66B3")

    def set_insertion_cursor(
        self,
        cursor: QTextCursor,
        color: QColor | None = None,
    ) -> None:
        self._insertion_cursor = QTextCursor(cursor)
        if color is not None:
            self._insertion_color = QColor(color)
        self.viewport().update()

    def insertion_cursor(self) -> Optional[QTextCursor]:
        if self._insertion_cursor is None:
            return None
        return QTextCursor(self._insertion_cursor)

    def clear_insertion_cursor(self) -> None:
        self._insertion_cursor = None
        self.viewport().update()

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        if self._insertion_cursor is None:
            return
        block = self._insertion_cursor.block()
        if not block.isValid():
            return

        cursor = QTextCursor(block)
        rect = self.cursorRect(cursor)
        y = round(rect.top())
        if y < 0 or y > self.viewport().height():
            return

        painter = QPainter(self.viewport())
        painter.setRenderHint(QPainter.Antialiasing, True)
        pen = QPen(self._insertion_color)
        pen.setWidth(2)
        pen.setStyle(Qt.DashLine)
        painter.setPen(pen)
        left = 22
        right = max(left, self.viewport().width() - 22)
        painter.drawLine(left, y, right, y)
        painter.setBrush(self._insertion_color)
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(left - 5, y - 5, 10, 10, 3, 3)


class ChapterMarkupDialog(QDialog):
    """Visual full-book chapter boundary editor."""

    def __init__(
        self,
        source_html: str,
        chapter_html: Dict[str, str],
        existing_names: set[str],
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Разметка глав PDF")
        self.resize(1300, 850)
        self.setMinimumSize(1000, 650)
        self.chapter_html = dict(chapter_html)
        self.existing_names = set(existing_names)
        self._restoring_chapter_marks = False
        self._dragging_boundary_title: Optional[str] = None

        layout = QHBoxLayout(self)
        splitter = QSplitter(Qt.Horizontal)
        layout.addWidget(splitter)

        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(8, 8, 12, 8)
        left_layout.addWidget(QLabel("Главы / серии"))

        self.chapter_list = QListWidget()
        for title in self.chapter_html:
            self.chapter_list.addItem(QListWidgetItem(title))
        self.chapter_list.currentItemChanged.connect(
            self._on_chapter_selected
        )
        left_layout.addWidget(self.chapter_list, stretch=1)

        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("Название главы")
        left_layout.addWidget(self.title_edit)

        self.btn_create = QPushButton("Новая граница здесь")
        self.btn_create.clicked.connect(self._create_boundary_at_cursor)
        left_layout.addWidget(self.btn_create)

        self.btn_replace = QPushButton("Перенести границу сюда")
        self.btn_replace.clicked.connect(self._move_current_boundary_to_cursor)
        left_layout.addWidget(self.btn_replace)

        self.btn_rename = QPushButton("Переименовать")
        self.btn_rename.clicked.connect(self._rename_current)
        left_layout.addWidget(self.btn_rename)

        self.btn_delete = QPushButton("Удалить главу")
        self.btn_delete.clicked.connect(self._delete_current)
        left_layout.addWidget(self.btn_delete)

        left_layout.addStretch()
        self.btn_apply = QPushButton("Применить разметку")
        self.btn_apply.clicked.connect(self.accept)
        left_layout.addWidget(self.btn_apply)
        self.btn_cancel = QPushButton("Отмена")
        self.btn_cancel.clicked.connect(self.reject)
        left_layout.addWidget(self.btn_cancel)
        splitter.addWidget(left)

        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 8, 8, 8)
        self.current_chapter_label = QLabel("")
        self.current_chapter_label.setStyleSheet(
            "font-weight: 600; color: #444; padding: 0 0 4px 2px;"
        )
        right_layout.addWidget(self.current_chapter_label)

        self.source_editor = ChapterSourceEditor()
        self.source_editor.setAcceptRichText(True)
        self.source_editor.setReadOnly(True)
        self.source_editor.installEventFilter(self)
        self.source_editor.viewport().installEventFilter(self)
        self.source_editor.viewport().setMouseTracking(True)
        self.source_editor.setHtml(source_html)
        self.source_editor.setStyleSheet(
            "QTextEdit { background: #fbfaf7; color: #1f1f1f; "
            "padding: 28px; }"
        )
        right_layout.addWidget(self.source_editor, stretch=1)
        splitter.addWidget(right)
        splitter.setSizes([330, 970])
        self._ensure_chapter_marks()
        self._rebuild_chapters_from_boundaries()

        if self.chapter_list.count():
            self.chapter_list.setCurrentRow(0)

    def source_html(self) -> str:
        return self.source_editor.toHtml()

    def accept(self) -> None:
        self._rebuild_chapters_from_boundaries()
        super().accept()

    def _on_chapter_selected(
        self,
        current: Optional[QListWidgetItem],
        _previous: Optional[QListWidgetItem],
    ) -> None:
        title = current.text() if current else ""
        self.title_edit.setText(title)
        self.current_chapter_label.setText(
            f"Граница: {title}" if title else ""
        )
        if title:
            self._scroll_to_chapter(title)

    def _current_title(self) -> Optional[str]:
        item = self.chapter_list.currentItem()
        return item.text() if item else None

    def _clean_title(self, title: str) -> str:
        return " ".join(title.split())

    def _validate_title(self, title: str, old_title: Optional[str] = None) -> bool:
        if not title:
            QMessageBox.warning(
                self,
                "Разметка глав",
                "Название главы не может быть пустым.",
            )
            return False
        used = set(self.chapter_html)
        used.update(self.existing_names)
        if old_title:
            used.discard(old_title)
        if title in used:
            QMessageBox.warning(
                self,
                "Разметка глав",
                "Глава или серия с таким названием уже существует.",
            )
            return False
        return True

    def _title_exists(self, title: str, old_title: Optional[str] = None) -> bool:
        used = set(self.chapter_html)
        used.update(self.existing_names)
        if old_title:
            used.discard(old_title)
        return title in used

    def _next_chapter_title(self) -> str:
        index = self.chapter_list.count() + 1
        while True:
            title = f"Глава {index}"
            if not self._title_exists(title):
                return title
            index += 1

    def _create_boundary_at_cursor(self) -> None:
        self._use_preview_cursor()
        title = self._clean_title(self.title_edit.text())
        current_title = self._current_title()
        if not title or title == current_title:
            title = self._next_chapter_title()
            self.title_edit.setText(title)
        if not self._validate_title(title):
            return

        self._insert_boundary_at_cursor(title)
        self._rebuild_chapters_from_boundaries()
        self._sync_chapter_list(title)

    def _move_current_boundary_to_cursor(self) -> None:
        title = self._current_title()
        if not title:
            return

        self._use_preview_cursor()
        self._remove_boundary(title)
        self._insert_boundary_at_cursor(title)
        self._rebuild_chapters_from_boundaries()
        self._sync_chapter_list(title)
        self._scroll_to_chapter(title)

    def _rename_current(self) -> None:
        old_title = self._current_title()
        if not old_title:
            return
        new_title = self._clean_title(self.title_edit.text())
        if new_title == old_title:
            return
        if not self._validate_title(new_title, old_title):
            return

        self.chapter_html[new_title] = rename_html_heading(
            self.chapter_html.pop(old_title),
            new_title,
        )
        self._rename_chapter_marks(old_title, new_title)
        item = self.chapter_list.currentItem()
        if item:
            item.setText(new_title)

    def _delete_current(self) -> None:
        title = self._current_title()
        if not title:
            return
        answer = QMessageBox.question(
            self,
            "Удалить главу",
            f"Удалить главу «{title}» из списка серий? Текст останется в PDF.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            return

        row = self.chapter_list.currentRow()
        self._clear_chapter_marks(title)
        self.chapter_html.pop(title, None)
        self._rebuild_chapters_from_boundaries()
        next_title = None
        titles = list(self.chapter_html)
        if titles:
            next_title = titles[min(row, len(titles) - 1)]
        self._sync_chapter_list(next_title)

    def _boundary_text(self, title: str) -> str:
        return f"········  {title}  ········"

    def _boundary_format(self, title: str) -> QTextCharFormat:
        fmt = QTextCharFormat()
        fmt.setProperty(CHAPTER_PROP, title)
        fmt.setAnchor(True)
        fmt.setAnchorHref(f"dm-chapter:{quote(title)}")
        fmt.clearProperty(QTextFormat.BackgroundBrush)
        fmt.setForeground(QColor("#3A66B3"))
        fmt.setFontUnderline(False)
        fmt.setFontWeight(QFont.Bold)
        return fmt

    def _boundary_block_format(self) -> QTextBlockFormat:
        fmt = QTextBlockFormat()
        fmt.setTopMargin(18)
        fmt.setBottomMargin(14)
        fmt.setAlignment(Qt.AlignCenter)
        fmt.clearProperty(QTextFormat.BackgroundBrush)
        return fmt

    def _insert_boundary_at_cursor(self, title: str) -> None:
        cursor = self.source_editor.textCursor()
        if self._boundary_from_block(cursor.block()):
            return
        if self._previous_block_is_boundary(cursor.block()):
            cursor.setPosition(cursor.block().position())
            if cursor.movePosition(QTextCursor.PreviousBlock):
                return
        cursor.setPosition(cursor.block().position())
        target_block_format = cursor.blockFormat()
        target_char_format = cursor.charFormat()
        self.source_editor.setReadOnly(False)
        cursor.beginEditBlock()
        cursor.setBlockFormat(self._boundary_block_format())
        cursor.setCharFormat(self._boundary_format(title))
        cursor.insertText(self._boundary_text(title), self._boundary_format(title))
        cursor.insertBlock(target_block_format, target_char_format)
        cursor.endEditBlock()
        self.source_editor.setReadOnly(True)

    def _ensure_chapter_marks(self) -> None:
        self._restoring_chapter_marks = True
        try:
            for title in self.chapter_html:
                if self._boundary_position(title) is not None:
                    self._rewrite_boundary(title)
                    continue
                self._insert_boundary_for_existing_chapter(title)
        finally:
            self._restoring_chapter_marks = False

    def _insert_boundary_for_existing_chapter(self, title: str) -> None:
        chapter_text = self._plain_text_from_html(
            self.chapter_html.get(title, "")
        )
        search_text = self._best_chapter_search_text(chapter_text)
        if not search_text:
            return

        document = self.source_editor.document()
        cursor = document.find(search_text)
        if cursor.isNull():
            body_text = self._plain_text_from_html(
                body_without_first_heading(self.chapter_html.get(title, ""))
            )
            search_text = self._best_chapter_search_text(body_text)
            cursor = document.find(search_text) if search_text else QTextCursor()
        if cursor.isNull():
            return

        previous = self.source_editor.textCursor()
        cursor.setPosition(cursor.selectionStart())
        self.source_editor.setTextCursor(cursor)
        self._insert_boundary_at_cursor(title)
        self.source_editor.setTextCursor(previous)

    def _plain_text_from_html(self, html_text: str) -> str:
        text_edit = QTextEdit()
        text_edit.setHtml(html_text)
        return text_edit.toPlainText().strip()

    def _best_chapter_search_text(self, text: str) -> str:
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        if lines:
            return lines[0][:120]
        for line in lines:
            if len(line) >= 12:
                return line[:120]
        return ""

    def _clear_chapter_marks(self, title: str) -> None:
        self._remove_boundary(title)

    def _rename_chapter_marks(self, old_title: str, new_title: str) -> None:
        self._rewrite_boundary(old_title, new_title)

    def _rewrite_boundary(
        self,
        old_title: str,
        new_title: Optional[str] = None,
    ) -> None:
        target_title = new_title or old_title
        position = self._boundary_position(old_title)
        if position is None:
            return
        document = self.source_editor.document()
        cursor = QTextCursor(document)
        cursor.setPosition(position)
        cursor.select(QTextCursor.BlockUnderCursor)
        self.source_editor.setReadOnly(False)
        cursor.setBlockFormat(self._boundary_block_format())
        cursor.setCharFormat(self._boundary_format(target_title))
        cursor.removeSelectedText()
        cursor.insertText(
            self._boundary_text(target_title),
            self._boundary_format(target_title),
        )
        cursor.clearSelection()
        self.source_editor.setReadOnly(True)

    def _scroll_to_chapter(self, title: str) -> None:
        position = self._boundary_position(title)
        if position is None:
            return
        cursor = self.source_editor.textCursor()
        cursor.setPosition(position)
        self.source_editor.setTextCursor(cursor)
        self.source_editor.ensureCursorVisible()

    def _boundary_position(self, title: str) -> Optional[int]:
        for block in self._boundary_blocks():
            if self._boundary_from_block(block) == title:
                return block.position()
        return None

    def _boundary_blocks(self):
        block = self.source_editor.document().begin()
        while block.isValid():
            if self._boundary_from_block(block):
                yield block
            block = block.next()

    def _boundary_from_block(self, block) -> Optional[str]:
        iterator = block.begin()
        while not iterator.atEnd():
            fragment = iterator.fragment()
            if fragment.isValid():
                fmt = fragment.charFormat()
                title = fmt.property(CHAPTER_PROP) or self._chapter_from_format(fmt)
                if title:
                    return title
            iterator += 1
        text = block.text().strip()
        match = re.fullmatch(
            r"(?:[·.\-–—━]\s*){4,}(.+?)(?:\s*[·.\-–—━]){4,}",
            text,
        )
        return match.group(1).strip() if match else None

    def _previous_block_is_boundary(self, block) -> bool:
        previous = block.previous()
        return previous.isValid() and bool(self._boundary_from_block(previous))

    def eventFilter(self, watched, event) -> bool:
        if watched in (self.source_editor, self.source_editor.viewport()):
            if event.type() == QEvent.MouseMove:
                cursor = self._cursor_for_mouse_event(event)
                title = self._boundary_from_block(cursor.block())
                if title or self._dragging_boundary_title:
                    self.source_editor.viewport().setCursor(Qt.ClosedHandCursor)
                else:
                    self.source_editor.viewport().setCursor(Qt.IBeamCursor)
                if self._dragging_boundary_title:
                    self._show_boundary_drop_preview(cursor)
                return bool(self._dragging_boundary_title)
            if event.type() == QEvent.MouseButtonPress:
                cursor = self._cursor_for_mouse_event(event)
                title = self._boundary_from_block(cursor.block())
                if title:
                    self._dragging_boundary_title = title
                    self.source_editor.viewport().setCursor(Qt.ClosedHandCursor)
                    self.current_chapter_label.setText(
                        f"Перетащите границу: {title}"
                    )
                    return True
                self.source_editor.setTextCursor(cursor)
                self._show_insertion_preview(cursor)
            if (
                event.type() == QEvent.MouseButtonRelease
                and self._dragging_boundary_title
            ):
                title = self._dragging_boundary_title
                self._dragging_boundary_title = None
                cursor = self._cursor_for_mouse_event(event)
                self._move_boundary_to_cursor(title, cursor)
                self._select_chapter(title)
                self._refresh_insertion_preview()
                self.source_editor.viewport().unsetCursor()
                return True
        return super().eventFilter(watched, event)

    def _show_boundary_drop_preview(self, cursor: QTextCursor) -> None:
        self._show_insertion_preview(cursor, QColor("#1D77D3"))

    def _show_insertion_preview(
        self,
        cursor: QTextCursor,
        color: QColor = QColor("#3A66B3"),
    ) -> None:
        if self._boundary_from_block(cursor.block()):
            self.source_editor.clear_insertion_cursor()
            return
        self.source_editor.set_insertion_cursor(cursor, color)

    def _refresh_insertion_preview(self) -> None:
        if self._dragging_boundary_title:
            return
        self._show_insertion_preview(self.source_editor.textCursor())

    def _use_preview_cursor(self) -> None:
        cursor = self.source_editor.insertion_cursor()
        if cursor is None:
            return
        if cursor.block().isValid():
            self.source_editor.setTextCursor(cursor)

    def _cursor_for_mouse_event(self, event) -> QTextCursor:
        point = (
            event.position().toPoint()
            if hasattr(event, "position")
            else event.pos()
        )
        return self.source_editor.cursorForPosition(point)

    def _move_boundary_to_cursor(
        self,
        title: str,
        cursor: QTextCursor,
        rebuild: bool = True,
        scroll: bool = True,
    ) -> None:
        target_block = cursor.block()
        if self._boundary_from_block(target_block) == title:
            if scroll:
                self._scroll_to_chapter(title)
            return
        self._remove_boundary(title)
        if target_block.isValid():
            cursor = QTextCursor(target_block)
        else:
            cursor = QTextCursor(self.source_editor.document())
            cursor.movePosition(QTextCursor.End)
        self.source_editor.setTextCursor(cursor)
        self._insert_boundary_at_cursor(title)
        if rebuild:
            self._rebuild_chapters_from_boundaries()
        if scroll:
            self._scroll_to_chapter(title)

    def _select_chapter(self, title: str) -> None:
        for row in range(self.chapter_list.count()):
            if self.chapter_list.item(row).text() == title:
                self.chapter_list.setCurrentRow(row)
                return

    def _sync_chapter_list(self, selected_title: Optional[str] = None) -> None:
        current_title = selected_title or self._current_title()
        self.chapter_list.blockSignals(True)
        self.chapter_list.clear()
        for title in self.chapter_html:
            self.chapter_list.addItem(QListWidgetItem(title))
        self.chapter_list.blockSignals(False)

        if current_title:
            for row in range(self.chapter_list.count()):
                if self.chapter_list.item(row).text() == current_title:
                    self.chapter_list.setCurrentRow(row)
                    return

        if self.chapter_list.count():
            self.chapter_list.setCurrentRow(0)
        else:
            self.title_edit.clear()
            self.current_chapter_label.clear()

    def _remove_boundary(self, title: str) -> None:
        position = self._boundary_position(title)
        if position is None:
            return
        document = self.source_editor.document()
        cursor = QTextCursor(document)
        cursor.setPosition(position)
        self.source_editor.setReadOnly(False)
        cursor.beginEditBlock()
        block = cursor.block()
        next_block = block.next()
        if next_block.isValid():
            cursor.setPosition(block.position())
            cursor.setPosition(
                next_block.position(),
                QTextCursor.MoveMode.KeepAnchor,
            )
        else:
            cursor.select(QTextCursor.BlockUnderCursor)
        cursor.removeSelectedText()
        cursor.endEditBlock()
        self.source_editor.setReadOnly(True)

    def _rebuild_chapters_from_boundaries(self) -> None:
        boundaries = [
            (block.position(), self._boundary_from_block(block), block)
            for block in self._boundary_blocks()
        ]
        boundaries = [(pos, title, block) for pos, title, block in boundaries if title]
        rebuilt: Dict[str, str] = {}
        document = self.source_editor.document()
        for index, (_pos, title, block) in enumerate(boundaries):
            start_block = block.next()
            if not start_block.isValid():
                continue
            start = start_block.position()
            if index + 1 < len(boundaries):
                end = boundaries[index + 1][0]
            else:
                end = document.characterCount() - 1
            if end <= start:
                continue
            cursor = QTextCursor(document)
            cursor.setPosition(start)
            cursor.setPosition(end, QTextCursor.MoveMode.KeepAnchor)
            if cursor.selectedText().strip():
                rebuilt[str(title)] = html_with_title(str(title), cursor.selection().toHtml())
        self.chapter_html = rebuilt

    def _chapter_from_format(self, fmt: QTextCharFormat) -> Optional[str]:
        href = fmt.anchorHref()
        if href.startswith("dm-chapter:"):
            return unquote(href[len("dm-chapter:"):])
        return None


class PdfImportWorker(QObject):
    """Extract a PDF away from the GUI thread."""

    progress = Signal(int, int)
    completed = Signal(object)
    failed = Signal(str)
    finished = Signal()

    def __init__(self, path: str, chapter_keywords: List[str]) -> None:
        super().__init__()
        self.path = path
        self.chapter_keywords = chapter_keywords

    @Slot()
    def run(self) -> None:
        try:
            chapters = BookImportService(self.chapter_keywords).import_pdf(
                self.path,
                lambda current, total: self.progress.emit(current, total),
            )
            self.completed.emit(chapters)
        except Exception as exc:
            self.failed.emit(str(exc))
        finally:
            self.finished.emit()


class AudiobookDialog(QDialog):
    """Dialog for importing PDF books and marking chapter text manually."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Аудиосериал")
        self.resize(1400, 1020)
        self.setMinimumSize(1050, 820)

        self.main_window = parent
        self.data: Dict[str, Any] = getattr(parent, "data", {})
        self.current_project_path = (
            getattr(parent, "current_project_path", None)
            if parent is not None
            else None
        )
        global_settings = getattr(parent, "global_settings", {})
        self.book_service = BookImportService(
            global_settings.get("audiobook_config", {}).get(
                "chapter_keywords"
            )
        )
        self.script_text_service = ScriptTextService()
        self.source_path: str = ""
        self.chapters: List[BookChapter] = []
        self.chapter_html: Dict[str, str] = {}
        self.current_episode: Optional[str] = None
        self._loading_document = False
        self._import_thread: Optional[QThread] = None
        self._import_worker: Optional[PdfImportWorker] = None
        self._pending_import_path = ""
        self.slot_controls: List[tuple[QComboBox, QComboBox]] = []
        self._initializing_ui = True
        self._zoom_steps = 0
        self._applied_zoom_steps = 0

        self._init_ui()
        self._load_existing_chapters()
        self._refresh_actor_combos()
        self._refresh_character_combos()
        self._load_ui_settings()
        self._initializing_ui = False
        self._save_ui_settings()

    def _init_ui(self) -> None:
        layout = QHBoxLayout(self)
        splitter = QSplitter(Qt.Horizontal)
        layout.addWidget(splitter)

        left_scroll = QScrollArea()
        left_scroll.setWidgetResizable(True)
        left_scroll.setFrameShape(QScrollArea.NoFrame)
        left_scroll.setMinimumWidth(340)
        left_scroll.setMaximumWidth(410)
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(8, 8, 12, 8)

        self.btn_import_pdf = QPushButton("Импорт PDF")
        self.btn_import_pdf.clicked.connect(self._import_pdf)
        left_layout.addWidget(self.btn_import_pdf)

        self.btn_chapter_markup = QPushButton("Разметка глав PDF")
        self.btn_chapter_markup.clicked.connect(self._open_chapter_markup)
        left_layout.addWidget(self.btn_chapter_markup)

        self.source_label = QLabel("PDF не импортирован")
        self.source_label.setWordWrap(True)
        self.source_label.setStyleSheet("color: #777;")
        left_layout.addWidget(self.source_label)
        self.import_progress = QProgressBar()
        self.import_progress.setVisible(False)
        left_layout.addWidget(self.import_progress)

        left_layout.addWidget(QLabel("Главы / серии"))
        self.chapter_list = QListWidget()
        self.chapter_list.setMinimumHeight(120)
        self.chapter_list.setMaximumHeight(150)
        self.chapter_list.currentItemChanged.connect(self._on_chapter_selected)
        left_layout.addWidget(self.chapter_list)

        left_layout.addWidget(QLabel("Отображение текста"))
        font_row = QHBoxLayout()
        self.font_combo = QFontComboBox()
        self.font_combo.setCurrentFont(QFont("Georgia"))
        self.font_combo.currentFontChanged.connect(self._apply_reader_font)
        font_row.addWidget(self.font_combo, stretch=1)
        self.btn_zoom_out = QToolButton()
        self.btn_zoom_out.setText("−")
        self.btn_zoom_out.setToolTip("Уменьшить текст")
        self.btn_zoom_out.clicked.connect(lambda: self._change_zoom(-1))
        font_row.addWidget(self.btn_zoom_out)
        self.zoom_label = QLabel("100%")
        self.zoom_label.setMinimumWidth(42)
        self.zoom_label.setAlignment(Qt.AlignCenter)
        font_row.addWidget(self.zoom_label)
        self.btn_zoom_in = QToolButton()
        self.btn_zoom_in.setText("+")
        self.btn_zoom_in.setToolTip("Увеличить текст")
        self.btn_zoom_in.clicked.connect(lambda: self._change_zoom(1))
        font_row.addWidget(self.btn_zoom_in)
        left_layout.addLayout(font_row)

        left_layout.addWidget(QLabel("Быстрые слоты 1–9"))
        slots_grid = QGridLayout()
        slots_grid.setColumnStretch(1, 1)
        slots_grid.setColumnStretch(2, 1)
        slots_grid.addWidget(QLabel(""), 0, 0)
        slots_grid.addWidget(QLabel("Персонаж"), 0, 1)
        slots_grid.addWidget(QLabel("Актёр"), 0, 2)
        for index in range(9):
            number = QLabel(str(index + 1))
            number.setAlignment(Qt.AlignCenter)
            number.setFixedWidth(24)
            character_combo = QComboBox()
            character_combo.setEditable(True)
            character_combo.setPlaceholderText("Персонаж")
            actor_combo = QComboBox()
            character_combo.currentTextChanged.connect(
                lambda text, slot=index: self._on_slot_character_changed(
                    slot, text
                )
            )
            actor_combo.currentIndexChanged.connect(
                lambda _value, slot=index: self._on_slot_actor_changed(slot)
            )
            slots_grid.addWidget(number, index + 1, 0)
            slots_grid.addWidget(character_combo, index + 1, 1)
            slots_grid.addWidget(actor_combo, index + 1, 2)
            self.slot_controls.append((character_combo, actor_combo))
        left_layout.addLayout(slots_grid)

        actions = QHBoxLayout()
        self.btn_apply = QPushButton("Назначить слот 1")
        self.btn_apply.clicked.connect(lambda: self._apply_slot(0))
        actions.addWidget(self.btn_apply)
        self.btn_clear = QPushButton("Снять разметку")
        self.btn_clear.clicked.connect(self._clear_selected_markup)
        actions.addWidget(self.btn_clear)
        left_layout.addLayout(actions)

        left_layout.addWidget(QLabel("Персонажи главы"))
        self.marked_list = QListWidget()
        self.marked_list.setMinimumHeight(100)
        self.marked_list.setMaximumHeight(110)
        left_layout.addWidget(self.marked_list)
        self.stats_label = QLabel("")
        self.stats_label.setWordWrap(True)
        self.stats_label.setStyleSheet("color: #777;")
        left_layout.addWidget(self.stats_label)

        self.btn_save = QPushButton("Сохранить главу")
        self.btn_save.clicked.connect(self._save_current_chapter)
        left_layout.addWidget(self.btn_save)
        self.btn_save_all = QPushButton("Сохранить все главы")
        self.btn_save_all.clicked.connect(lambda: self._save_all_chapters())
        left_layout.addWidget(self.btn_save_all)
        self.btn_close = QPushButton("Закрыть")
        self.btn_close.clicked.connect(self.accept)
        left_layout.addWidget(self.btn_close)
        left_layout.addStretch()

        left_scroll.setWidget(left)
        splitter.addWidget(left_scroll)

        center = QWidget()
        center_layout = QVBoxLayout(center)
        center_layout.setContentsMargins(0, 8, 8, 8)

        self.editor = QTextEdit()
        self.editor.setAcceptRichText(True)
        self.editor.installEventFilter(self)
        self.editor.setStyleSheet(
            "QTextEdit { background: #fbfaf7; color: #1f1f1f; "
            "padding: 28px; }"
        )
        center_layout.addWidget(self.editor, stretch=1)
        splitter.addWidget(center)
        splitter.setSizes([370, 810])
        self._apply_reader_font()

    def _load_existing_chapters(self) -> None:
        source = self.data.get("audiobook_source", {})
        if source.get("path"):
            self.source_path = source.get("path", "")
        for episode, payload in self.data.get("book_chapters", {}).items():
            html_text = self._normalize_book_html(payload.get("html", ""))
            if not html_text:
                continue
            self.chapter_html[str(episode)] = html_text
            self.chapter_list.addItem(QListWidgetItem(str(episode)))
            self.source_path = payload.get("source", {}).get("path", self.source_path)

        if self.source_path:
            self.source_label.setText(self.source_path)
        if self.chapter_list.count():
            self.chapter_list.setCurrentRow(0)

    def _audiobook_source_html(self) -> str:
        return self._normalize_book_html(
            self.data.get("audiobook_source", {}).get("html", "")
        )

    def _save_audiobook_source(self, html_text: str) -> None:
        self.data["audiobook_source"] = {
            "format_version": "1.0",
            "source": "pdf",
            "path": self.source_path,
            "html": self._normalize_book_html(html_text),
        }

    def _open_chapter_markup(self) -> None:
        if self.current_episode:
            self.chapter_html[self.current_episode] = (
                self._editor_html_at_base_zoom()
            )
        if not self._audiobook_source_html():
            QMessageBox.warning(
                self,
                "Разметка глав PDF",
                "Сначала импортируйте PDF.",
            )
            return

        existing_names = set(self.data.get("episodes", {})) - set(self.chapter_html)
        dialog = ChapterMarkupDialog(
            self._audiobook_source_html(),
            self.chapter_html,
            existing_names,
            self,
        )
        if dialog.exec() != QDialog.Accepted:
            return

        self._apply_chapter_markup(
            dialog.chapter_html,
            dialog.source_html(),
        )

    def _apply_chapter_markup(
        self,
        chapter_html: Dict[str, str],
        source_html: str,
    ) -> None:
        old_episodes = set(self.chapter_html)
        new_episodes = set(chapter_html)
        for episode in old_episodes - new_episodes:
            self._remove_episode_payload(episode)

        self.chapter_html = {
            title: self._normalize_book_html(html_text)
            for title, html_text in chapter_html.items()
        }
        set_project_kind(self.data, "audiobook")
        set_audiobook_chapter_order(self.data, list(self.chapter_html))
        self._save_audiobook_source(source_html)

        self.chapter_list.blockSignals(True)
        self.chapter_list.clear()
        for episode in self.chapter_html:
            self.chapter_list.addItem(QListWidgetItem(episode))
        self.chapter_list.blockSignals(False)
        self.current_episode = None

        if self.chapter_list.count():
            self.chapter_list.setCurrentRow(0)
            self._save_all_chapters(show_message=False)
        else:
            self.current_episode = None
            self.editor.clear()
            self._refresh_marked_list()

        self._notify_project_changed()

    def _refresh_actor_combos(self) -> None:
        for _, actor_combo in self.slot_controls:
            current = actor_combo.currentData()
            actor_combo.blockSignals(True)
            actor_combo.clear()
            actor_combo.addItem("Без актёра", None)
            for actor_id, info in self.data.get("actors", {}).items():
                actor_combo.addItem(info.get("name", actor_id), actor_id)
            if current:
                idx = actor_combo.findData(current)
                if idx >= 0:
                    actor_combo.setCurrentIndex(idx)
            actor_combo.blockSignals(False)

    def _refresh_character_combos(
        self,
        extra_characters: Optional[List[str]] = None,
    ) -> None:
        characters = self._project_characters()
        characters.update(extra_characters or [])
        ordered = sorted(
            (name for name in characters if name),
            key=str.casefold,
        )
        for character_combo, _ in self.slot_controls:
            current = character_combo.currentText()
            character_combo.blockSignals(True)
            character_combo.clear()
            character_combo.addItems(ordered)
            character_combo.setEditText(current)
            character_combo.blockSignals(False)

    def _project_characters(self) -> set[str]:
        characters = {
            str(name).strip()
            for name in self.data.get("global_map", {}).keys()
            if str(name).strip()
        }
        for episode_map in self.data.get("episode_actor_map", {}).values():
            characters.update(
                str(name).strip()
                for name in episode_map.keys()
                if str(name).strip()
            )
        for lines in self.data.get("loaded_episodes", {}).values():
            characters.update(
                str(line.get("char", "")).strip()
                for line in lines
                if str(line.get("char", "")).strip()
            )
        for html_text in self.chapter_html.values():
            characters.update(
                unquote(match)
                for match in re.findall(
                    r"dm-character:([^\"'<>\s]+)",
                    html_text,
                    flags=re.IGNORECASE,
                )
            )
        for slot in self.data.get("audiobook_settings", {}).get("slots", []):
            character = str(slot.get("character", "")).strip()
            if character:
                characters.add(character)
        return characters

    def _apply_reader_font(self, *_args) -> None:
        font = self.font_combo.currentFont()
        self.editor.document().setDefaultFont(font)
        family = font.family().replace('"', '\\"')
        self.editor.document().setDefaultStyleSheet(
            f'body, p {{ font-family: "{family}"; }}'
        )
        cursor = QTextCursor(self.editor.document())
        cursor.select(QTextCursor.Document)
        char_format = QTextCharFormat()
        char_format.setFontFamily(font.family())
        cursor.mergeCharFormat(char_format)
        self.editor.viewport().update()
        self._save_ui_settings()

    def _change_zoom(self, delta: int) -> None:
        target = max(-5, min(10, self._zoom_steps + delta))
        if target == self._zoom_steps:
            return
        self._scale_document_fonts(
            self._zoom_factor(target) / self._zoom_factor(self._zoom_steps)
        )
        self._zoom_steps = target
        self._applied_zoom_steps = target
        self._update_zoom_label()
        self._save_ui_settings()

    def _apply_reader_zoom(self) -> None:
        if self._zoom_steps != self._applied_zoom_steps:
            self._scale_document_fonts(
                self._zoom_factor(self._zoom_steps)
                / self._zoom_factor(self._applied_zoom_steps)
            )
        self._applied_zoom_steps = self._zoom_steps
        self._update_zoom_label()

    def _zoom_factor(self, steps: int) -> float:
        return 1.0 + steps * 0.1

    def _scale_document_fonts(self, ratio: float) -> None:
        if abs(ratio - 1.0) < 0.001:
            return
        document = self.editor.document()
        default_size = document.defaultFont().pointSizeF()
        block = document.begin()
        while block.isValid():
            iterator = block.begin()
            while not iterator.atEnd():
                fragment = iterator.fragment()
                if fragment.isValid() and fragment.length():
                    char_format = fragment.charFormat()
                    point_size = char_format.fontPointSize() or default_size
                    char_format.setFontPointSize(point_size * ratio)
                    cursor = QTextCursor(document)
                    cursor.setPosition(fragment.position())
                    cursor.setPosition(
                        fragment.position() + fragment.length(),
                        QTextCursor.MoveMode.KeepAnchor,
                    )
                    cursor.mergeCharFormat(char_format)
                iterator += 1
            block = block.next()

    def _update_zoom_label(self) -> None:
        self.zoom_label.setText(f"{100 + self._zoom_steps * 10}%")

    def _editor_html_at_base_zoom(self) -> str:
        applied = self._applied_zoom_steps
        if applied:
            self._scale_document_fonts(1.0 / self._zoom_factor(applied))
        html_text = self.editor.toHtml()
        if applied:
            self._scale_document_fonts(self._zoom_factor(applied))
        return html_text

    def _set_editor_html(self, html_text: str) -> None:
        self._apply_reader_font()
        self.editor.setHtml(self._normalize_book_html(html_text))
        self._applied_zoom_steps = 0
        self._apply_reader_font()
        self._apply_reader_zoom()
        self._sync_document_actor_colors()

    def _load_ui_settings(self) -> None:
        settings = self.data.get("audiobook_settings", {})
        family = settings.get("font_family")
        if family:
            self.font_combo.setCurrentFont(QFont(family))
        self._zoom_steps = int(settings.get("zoom_steps", 0))
        self._zoom_steps = max(-5, min(10, self._zoom_steps))

        slots = settings.get("slots", [])
        for index, payload in enumerate(slots[:len(self.slot_controls)]):
            character_combo, actor_combo = self.slot_controls[index]
            character_combo.setEditText(str(payload.get("character", "")))
            actor_id = payload.get("actor_id")
            actor_index = actor_combo.findData(actor_id)
            actor_combo.setCurrentIndex(actor_index if actor_index >= 0 else 0)
        self._apply_reader_font()
        self._apply_reader_zoom()

    def _save_ui_settings(self, *_args) -> None:
        if (
            self._initializing_ui
            or not hasattr(self, "slot_controls")
            or not hasattr(self, "font_combo")
        ):
            return
        self.data["audiobook_settings"] = {
            "font_family": self.font_combo.currentFont().family(),
            "zoom_steps": self._zoom_steps,
            "slots": [
                {
                    "character": character_combo.currentText().strip(),
                    "actor_id": actor_combo.currentData(),
                }
                for character_combo, actor_combo in self.slot_controls
            ],
        }

    def _on_slot_actor_changed(self, index: int) -> None:
        self._save_ui_settings()
        if self._initializing_ui or not 0 <= index < len(self.slot_controls):
            return

        character_combo, actor_combo = self.slot_controls[index]
        character = character_combo.currentText().strip()
        if not character:
            return

        actor_id = actor_combo.currentData()
        global_map = self.data.setdefault("global_map", {})
        if actor_id:
            global_map[character] = actor_id
        else:
            global_map.pop(character, None)

        self._recolor_character(character, self._actor_color(actor_id))
        if self.current_episode:
            self.chapter_html[self.current_episode] = (
                self._editor_html_at_base_zoom()
            )
        if self.main_window is not None and hasattr(self.main_window, "set_dirty"):
            self.main_window.set_dirty(True)

    def _on_slot_character_changed(self, index: int, text: str) -> None:
        self._save_ui_settings()
        if self._initializing_ui or not 0 <= index < len(self.slot_controls):
            return

        character = text.strip()
        _, actor_combo = self.slot_controls[index]
        actor_id = (
            get_actor_for_character(
                self.data,
                character,
                self.current_episode,
            )
            if character
            else None
        )
        actor_index = actor_combo.findData(actor_id)
        actor_combo.blockSignals(True)
        actor_combo.setCurrentIndex(actor_index if actor_index >= 0 else 0)
        actor_combo.blockSignals(False)
        self._save_ui_settings()

    def _import_pdf(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Выберите PDF книги",
            "",
            "PDF Files (*.pdf);;All Files (*)",
        )
        if not path:
            return

        self._pending_import_path = path
        self._set_importing(True)
        self.import_progress.setRange(0, 0)
        self.source_label.setText(f"Чтение PDF: {path}")

        thread = QThread(self)
        worker = PdfImportWorker(path, self.book_service.chapter_keywords)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.progress.connect(self._on_import_progress)
        worker.completed.connect(self._finish_pdf_import)
        worker.failed.connect(self._fail_pdf_import)
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(self._import_thread_finished)
        self._import_thread = thread
        self._import_worker = worker
        thread.start()

    @Slot(int, int)
    def _on_import_progress(self, current: int, total: int) -> None:
        self.import_progress.setRange(0, total)
        self.import_progress.setValue(current)
        self.import_progress.setFormat(f"Страница {current} из {total}")

    @Slot(object)
    def _finish_pdf_import(self, chapters: List[BookChapter]) -> None:
        path = self._pending_import_path
        self.source_path = path
        self.source_label.setText(path)
        self.chapters = chapters
        self.chapter_html.clear()
        self.chapter_list.clear()
        set_project_kind(self.data, "audiobook")
        maybe_set_project_name_from_first_import(self.data, path, {".pdf"})
        self._save_audiobook_source(self.book_service.chapters_to_html(chapters))

        existing = set(self.data.get("episodes", {}).keys())
        imported_order: List[str] = []
        for idx, chapter in enumerate(chapters, 1):
            episode = self._unique_episode_name(chapter.title or f"Глава {idx}", existing)
            existing.add(episode)
            imported_order.append(episode)
            html_text = self.book_service.chapter_to_html(chapter)
            self.chapter_html[episode] = html_text
            self.chapter_list.addItem(QListWidgetItem(episode))
            lines = self.book_service.build_lines_from_segments([
                {"character": "Автор", "text": chapter.text},
            ])
            self.data.setdefault("episodes", {})[episode] = path
            self.book_service.save_chapter_text(
                self.data, episode, path, html_text, lines
            )
            self.script_text_service.create_episode_text(
                self.data,
                episode,
                path,
                lines,
                {**self.data.get("replica_merge_config", {}), "merge": False},
                self.current_project_path,
            )

        set_audiobook_chapter_order(self.data, imported_order)
        if self.chapter_list.count():
            self.chapter_list.setCurrentRow(0)
        self._notify_project_changed()

        QMessageBox.information(
            self,
            "Импорт PDF",
            f"Импортировано глав: {len(chapters)}",
        )

    @Slot(str)
    def _fail_pdf_import(self, message: str) -> None:
        self.source_label.setText("Не удалось импортировать PDF")
        QMessageBox.warning(self, "Импорт PDF", message)

    @Slot()
    def _import_thread_finished(self) -> None:
        self._import_thread = None
        self._import_worker = None
        self._pending_import_path = ""
        self._set_importing(False)

    def _set_importing(self, importing: bool) -> None:
        self.btn_import_pdf.setEnabled(not importing)
        self.btn_chapter_markup.setEnabled(not importing)
        self.btn_close.setEnabled(not importing)
        self.import_progress.setVisible(importing)

    def reject(self) -> None:
        if self._import_thread is not None:
            return
        super().reject()

    def _unique_episode_name(self, title: str, existing: set[str]) -> str:
        base = " ".join(title.split()) or "Глава"
        candidate = base
        counter = 2
        while candidate in existing:
            candidate = f"{base} {counter}"
            counter += 1
        return candidate

    def _current_chapter_row(self) -> int:
        row = self.chapter_list.currentRow()
        return row if row >= 0 else 0

    def _existing_episode_names(self, exclude: Optional[str] = None) -> set[str]:
        names = set(self.data.get("episodes", {}).keys())
        names.update(self.chapter_html.keys())
        for row in range(self.chapter_list.count()):
            names.add(self.chapter_list.item(row).text())
        if exclude:
            names.discard(exclude)
        return names

    def _remove_episode_payload(self, episode: str) -> None:
        for key in (
            "episodes",
            "book_chapters",
            "loaded_episodes",
            "episode_texts",
            "episode_working_texts",
            "episode_actor_map",
            "video_paths",
        ):
            self.data.get(key, {}).pop(episode, None)

    def _on_chapter_selected(
        self,
        current: Optional[QListWidgetItem],
        previous: Optional[QListWidgetItem],
    ) -> None:
        if previous and self.current_episode:
            self.chapter_html[self.current_episode] = (
                self._editor_html_at_base_zoom()
            )

        if not current:
            self.current_episode = None
            self.editor.clear()
            return

        self.current_episode = current.text()
        self._loading_document = True
        self._set_editor_html(
            self.chapter_html.get(self.current_episode, "")
        )
        self._loading_document = False
        self._refresh_marked_list()

    def _normalize_book_html(self, html_text: str) -> str:
        """Drop the fixed body size emitted by the first importer version."""
        return re.sub(
            r"font-size:\s*13pt;\s*",
            "",
            html_text,
            flags=re.IGNORECASE,
        )

    def _apply_slot(self, index: int) -> None:
        if not 0 <= index < len(self.slot_controls):
            return
        character_combo, actor_combo = self.slot_controls[index]
        self._apply_selected_character(
            character_combo.currentText().strip(),
            actor_combo.currentData(),
        )

    def _apply_selected_character(
        self,
        character: str,
        actor_id: Optional[str],
    ) -> None:
        cursor = self.editor.textCursor()
        if not cursor.hasSelection():
            return

        if not character:
            QMessageBox.warning(
                self,
                "Разметка",
                "В выбранном слоте не указан персонаж.",
            )
            return

        color = self._actor_color(actor_id)
        fmt = QTextCharFormat()
        fmt.setProperty(CHARACTER_PROP, character)
        fmt.setAnchor(True)
        fmt.setAnchorHref(f"dm-character:{quote(character)}")
        fmt.setBackground(QColor(color).lighter(170))
        fmt.setForeground(QColor("#111111"))
        fmt.setFontUnderline(False)
        cursor.mergeCharFormat(fmt)
        self.editor.setTextCursor(cursor)

        global_map = self.data.setdefault("global_map", {})
        if actor_id:
            global_map[character] = actor_id
        else:
            global_map.pop(character, None)

        self._add_character_to_slots(character)

        self._refresh_marked_list()

    def _add_character_to_slots(self, character: str) -> None:
        self._refresh_character_combos([character])

    def eventFilter(self, watched, event) -> bool:
        key_to_slot = {
            Qt.Key_1: 0,
            Qt.Key_2: 1,
            Qt.Key_3: 2,
            Qt.Key_4: 3,
            Qt.Key_5: 4,
            Qt.Key_6: 5,
            Qt.Key_7: 6,
            Qt.Key_8: 7,
            Qt.Key_9: 8,
        }
        if (
            watched is self.editor
            and event.type() == QEvent.KeyPress
            and event.key() in key_to_slot
            and self.editor.textCursor().hasSelection()
            and event.modifiers() in (Qt.NoModifier, Qt.KeypadModifier)
        ):
            self._apply_slot(key_to_slot[event.key()])
            return True
        return super().eventFilter(watched, event)

    def _clear_selected_markup(self) -> None:
        cursor = self.editor.textCursor()
        if not cursor.hasSelection():
            return
        fmt = QTextCharFormat()
        fmt.clearProperty(CHARACTER_PROP)
        fmt.setAnchor(False)
        fmt.setAnchorHref("")
        fmt.setBackground(QColor(Qt.transparent))
        cursor.mergeCharFormat(fmt)
        self._refresh_marked_list()

    def _actor_color(self, actor_id: Optional[str]) -> str:
        if actor_id and actor_id in self.data.get("actors", {}):
            return self.data["actors"][actor_id].get("color", "#FFF2A8")
        return "#FFF2A8"

    def _sync_document_actor_colors(self) -> None:
        characters = {
            segment.get("character")
            for segment in self._segments_from_document()
            if segment.get("character") not in (None, "Автор")
        }
        global_map = self.data.get("global_map", {})
        for character in characters:
            self._recolor_character(
                character,
                self._actor_color(global_map.get(character)),
            )

    def _recolor_character(self, character: str, color: str) -> None:
        document = self.editor.document()
        ranges: List[tuple[int, int]] = []
        block = document.begin()
        while block.isValid():
            iterator = block.begin()
            while not iterator.atEnd():
                fragment = iterator.fragment()
                if fragment.isValid() and fragment.length():
                    char_format = fragment.charFormat()
                    marked_character = (
                        char_format.property(CHARACTER_PROP)
                        or self._character_from_format(char_format)
                    )
                    if marked_character == character:
                        ranges.append((fragment.position(), fragment.length()))
                iterator += 1
            block = block.next()

        background = QColor(color).lighter(170)
        for position, length in ranges:
            cursor = QTextCursor(document)
            cursor.setPosition(position)
            cursor.setPosition(
                position + length,
                QTextCursor.MoveMode.KeepAnchor,
            )
            char_format = QTextCharFormat()
            char_format.setBackground(background)
            cursor.mergeCharFormat(char_format)

    def _segments_from_document(self) -> List[Dict[str, Any]]:
        doc = self.editor.document()
        cursor = QTextCursor(doc)
        cursor.movePosition(QTextCursor.Start)

        segments: List[Dict[str, Any]] = []
        current_character: Optional[str] = None
        current_text: List[str] = []

        for pos in range(doc.characterCount()):
            cursor.setPosition(pos)
            ch = doc.characterAt(pos)
            if ch == "\u2029":
                ch = "\n\n"
            fmt = cursor.charFormat()
            character = fmt.property(CHARACTER_PROP) or self._character_from_format(fmt)

            if character != current_character:
                self._append_segment(segments, current_character, current_text)
                current_character = character
                current_text = []
            current_text.append(ch)

        self._append_segment(segments, current_character, current_text)
        return segments

    def _character_from_format(self, fmt: QTextCharFormat) -> str:
        href = fmt.anchorHref()
        if href.startswith("dm-character:"):
            return unquote(href[len("dm-character:"):]) or "Автор"
        return "Автор"

    def _append_segment(
        self,
        segments: List[Dict[str, Any]],
        character: Optional[str],
        text_parts: List[str]
    ) -> None:
        text = "".join(text_parts).strip()
        if not text:
            return
        segments.append({"character": character or "Автор", "text": text})

    def _save_current_chapter(self) -> None:
        if not self.current_episode:
            return
        self._save_episode_from_editor(self.current_episode)
        self._notify_project_changed()
        QMessageBox.information(self, "Аудиосериал", "Глава сохранена в проект.")

    def _save_all_chapters(self, show_message: bool = True) -> None:
        if self.current_episode:
            self.chapter_html[self.current_episode] = (
                self._editor_html_at_base_zoom()
            )

        current = self.current_episode
        for episode, html_text in list(self.chapter_html.items()):
            if episode == current:
                self._save_episode_from_editor(episode)
                continue
            self._set_editor_html(html_text)
            self.current_episode = episode
            self._save_episode_from_editor(episode)

        if current:
            self.current_episode = current
            self._set_editor_html(self.chapter_html.get(current, ""))
        self._notify_project_changed()
        if show_message:
            QMessageBox.information(
                self,
                "Аудиосериал",
                "Все главы сохранены в проект."
            )

    def _save_episode_from_editor(self, episode: str) -> None:
        self.chapter_html[episode] = self._editor_html_at_base_zoom()
        segments = self._segments_from_document()
        lines = self.book_service.build_lines_from_segments(segments)

        self.data.setdefault("episodes", {})[episode] = self.source_path or "audiobook"
        self.book_service.save_chapter_text(
            self.data,
            episode,
            self.source_path,
            self.chapter_html[episode],
            lines,
        )
        self.script_text_service.create_episode_text(
            self.data,
            episode,
            self.source_path or "audiobook",
            lines,
            {**self.data.get("replica_merge_config", {}), "merge": False},
            self.current_project_path,
        )

        for line in lines:
            character = line.get("char")
            if character:
                self._add_character_to_slots(character)

        self._refresh_marked_list()

    def _refresh_marked_list(self) -> None:
        self.marked_list.clear()
        counts: Dict[str, int] = {}
        words: Dict[str, int] = {}
        for segment in self._segments_from_document():
            character = segment.get("character") or "Автор"
            counts[character] = counts.get(character, 0) + 1
            words[character] = words.get(character, 0) + len(segment.get("text", "").split())

        for character in sorted(counts, key=str.lower):
            self.marked_list.addItem(
                QListWidgetItem(f"{character}: {counts[character]} фр., {words[character]} слов")
            )

        total_words = sum(words.values())
        self.stats_label.setText(
            f"Всего: {sum(counts.values())} фрагментов, {total_words} слов"
            )

    def _notify_project_changed(self) -> None:
        if self.main_window is None:
            return
        if hasattr(self.main_window, "update_ep_list"):
            self.main_window.update_ep_list(self.current_episode)
        if hasattr(self.main_window, "refresh_actor_list"):
            self.main_window.refresh_actor_list()
        if hasattr(self.main_window, "set_dirty"):
            self.main_window.set_dirty(True)
