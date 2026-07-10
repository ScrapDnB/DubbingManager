import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt
from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import QApplication, QMessageBox, QWidget

from services.book_import_service import BookChapter
from ui.dialogs.audiobook import AudiobookDialog, ChapterMarkupDialog


def _app():
    return QApplication.instance() or QApplication([])


class DummyMainWindow(QWidget):
    def __init__(self, project_folder):
        super().__init__()
        self.data = {
            "project_folder": str(project_folder),
            "episodes": {"Глава 1": "book.pdf"},
            "book_chapters": {
                "Глава 1": {
                    "html": (
                        "<!DOCTYPE HTML><html><body>"
                        "<h1>Глава 1</h1>"
                        "<p>Первый абзац.</p>"
                        "<p>Второй абзац.</p>"
                        "</body></html>"
                    ),
                    "source": {"path": "book.pdf"},
                }
            },
            "loaded_episodes": {"Глава 1": []},
            "episode_texts": {},
            "actors": {},
            "global_map": {},
            "episode_actor_map": {},
            "audiobook_source": {
                "path": "book.pdf",
                "html": (
                    "<!DOCTYPE HTML><html><body>"
                    "<h1>Глава 1</h1>"
                    "<p>Первый абзац.</p>"
                    "<p>Второй абзац.</p>"
                    "</body></html>"
                ),
            },
            "audiobook_settings": {},
            "episode_working_texts": {},
            "replica_merge_config": {},
        }
        self.current_project_path = None
        self.global_settings = {"audiobook_config": {"chapter_keywords": ["Глава"]}}
        self.dirty = False
        self.selected_episode = None

    def update_ep_list(self, current_episode=None):
        self.selected_episode = current_episode

    def refresh_actor_list(self):
        pass

    def set_dirty(self, value):
        self.dirty = value


def test_audiobook_pdf_import_sets_default_project_name(tmp_path, monkeypatch):
    _app()
    parent = DummyMainWindow(tmp_path)
    parent.data["project_name"] = "Новый проект"
    parent.data["episodes"] = {}
    parent.data["book_chapters"] = {}
    parent.data["loaded_episodes"] = {}
    parent.data["audiobook_source"] = {}
    pdf_path = tmp_path / "Book Title.pdf"
    pdf_path.write_text("pdf", encoding="utf-8")

    dialog = AudiobookDialog(parent)
    dialog._pending_import_path = str(pdf_path)
    monkeypatch.setattr(
        QMessageBox,
        "information",
        lambda *args, **kwargs: QMessageBox.Ok,
    )

    dialog._finish_pdf_import([
        BookChapter(title="Пролог", paragraphs=["Текст пролога."]),
        BookChapter(title="Глава 1", paragraphs=["Текст главы."]),
    ])

    assert parent.data["project_name"] == "Book Title"
    assert parent.data["project_kind"] == "audiobook"
    assert parent.data["audiobook_chapter_order"] == ["Пролог", "Глава 1"]


def test_audiobook_apply_chapter_markup_preserves_manual_titles(tmp_path):
    _app()
    parent = DummyMainWindow(tmp_path)
    parent.data["episodes"] = {
        "Глава 1": "book.pdf",
        "Пролог": "book.pdf",
        "Глава 1 2": "book.pdf",
    }
    parent.data["book_chapters"] = {
        title: {
            "html": (
                "<!DOCTYPE HTML><html><body>"
                f"<h1>{title}</h1><p>Старый текст.</p>"
                "</body></html>"
            )
        }
        for title in parent.data["episodes"]
    }
    parent.data["loaded_episodes"] = {
        title: [] for title in parent.data["episodes"]
    }
    parent.data["episode_working_texts"] = {
        title: {"lines": []} for title in parent.data["episodes"]
    }
    parent.data["audiobook_source"] = {
        "html": (
            "<!DOCTYPE HTML><html><body>"
            "<h1>Вступление</h1><p>Текст вступления.</p>"
            "<h1>Пролог</h1><p>Текст пролога.</p>"
            "<h1>Глава 1</h1><p>Текст первой главы.</p>"
            "</body></html>"
        ),
        "path": "book.pdf",
    }
    dialog = AudiobookDialog(parent)
    dialog.current_episode = "Глава 1"
    dialog._set_editor_html(
        "<!DOCTYPE HTML><html><body><h1>Глава 1</h1>"
        "<p>Старое вступление.</p></body></html>"
    )

    dialog._apply_chapter_markup(
        {
            "Вступление": (
                "<!DOCTYPE HTML><html><body><h1>Вступление</h1>"
                "<p>Текст вступления.</p></body></html>"
            ),
            "Пролог": (
                "<!DOCTYPE HTML><html><body><h1>Пролог</h1>"
                "<p>Текст пролога.</p></body></html>"
            ),
            "Глава 1": (
                "<!DOCTYPE HTML><html><body><h1>Глава 1</h1>"
                "<p>Текст первой главы.</p></body></html>"
            ),
        },
        parent.data["audiobook_source"]["html"],
    )

    titles = [
        dialog.chapter_list.item(row).text()
        for row in range(dialog.chapter_list.count())
    ]
    assert titles == ["Вступление", "Пролог", "Глава 1"]
    assert parent.data["project_kind"] == "audiobook"
    assert parent.data["audiobook_chapter_order"] == [
        "Вступление",
        "Пролог",
        "Глава 1",
    ]
    assert set(parent.data["episodes"]) == {"Вступление", "Пролог", "Глава 1"}
    assert "Глава 1 2" not in parent.data["book_chapters"]
    assert "Глава 1 2" not in parent.data["episode_working_texts"]
    assert "Текст первой главы." in parent.data["book_chapters"]["Глава 1"]["html"]


def test_chapter_markup_dialog_keeps_source_text_after_chapter_delete(monkeypatch):
    _app()
    source_html = (
        "<!DOCTYPE HTML><html><body>"
        "<p>Первый абзац.</p>"
        "<p>Второй абзац.</p>"
        "</body></html>"
    )
    dialog = ChapterMarkupDialog(
        source_html,
        {"Глава 1": "<!DOCTYPE HTML><html><body><h1>Глава 1</h1><p>Первый абзац.</p></body></html>"},
        set(),
    )
    monkeypatch.setattr(
        QMessageBox,
        "question",
        lambda *args, **kwargs: QMessageBox.Yes,
    )

    dialog._delete_current()

    assert dialog.chapter_html == {}
    assert "Первый абзац." in dialog.source_editor.toPlainText()
    assert "Второй абзац." in dialog.source_editor.toPlainText()


def test_chapter_markup_dialog_can_create_boundary_in_full_source():
    _app()
    source_html = (
        "<!DOCTYPE HTML><html><body>"
        "<p>Первый абзац.</p>"
        "<p>Второй абзац.</p>"
        "</body></html>"
    )
    dialog = ChapterMarkupDialog(source_html, {}, set())
    dialog.title_edit.setText("Глава 2")

    cursor = dialog.source_editor.textCursor()
    start = dialog.source_editor.toPlainText().index("Второй")
    cursor.setPosition(start)
    dialog.source_editor.setTextCursor(cursor)

    dialog._create_boundary_at_cursor()
    dialog.accept()

    assert "Глава 2" in dialog.chapter_html
    assert "Второй абзац." in dialog.chapter_html["Глава 2"]
    assert "········  Глава 2  ········" in dialog.source_editor.toPlainText()
    boundary_cursor = dialog.source_editor.document().find("········  Глава 2")
    assert boundary_cursor.blockFormat().background().style() == Qt.NoBrush


def test_chapter_markup_dialog_generates_title_for_new_boundary():
    _app()
    source_html = (
        "<!DOCTYPE HTML><html><body>"
        "<p>Первый абзац.</p>"
        "<p>Второй абзац.</p>"
        "</body></html>"
    )
    dialog = ChapterMarkupDialog(
        source_html,
        {
            "Глава 1": (
                "<!DOCTYPE HTML><html><body><h1>Глава 1</h1>"
                "<p>Первый абзац.</p></body></html>"
            ),
        },
        set(),
    )

    cursor = dialog.source_editor.document().find("Второй абзац.")
    dialog.source_editor.setTextCursor(cursor)

    dialog._create_boundary_at_cursor()
    dialog.accept()

    assert "Глава 2" in dialog.chapter_html
    assert "Второй абзац." in dialog.chapter_html["Глава 2"]
    assert dialog.title_edit.text() == "Глава 2"


def test_chapter_markup_dialog_orders_new_boundary_by_document_position():
    _app()
    source_html = (
        "<!DOCTYPE HTML><html><body>"
        "<p>Первый абзац.</p>"
        "<p>Средний абзац.</p>"
        "<p>Последний абзац.</p>"
        "</body></html>"
    )
    dialog = ChapterMarkupDialog(source_html, {}, set())

    first_cursor = dialog.source_editor.document().find("Первый абзац.")
    dialog.source_editor.setTextCursor(first_cursor)
    dialog.title_edit.setText("Глава 1")
    dialog._create_boundary_at_cursor()

    last_cursor = dialog.source_editor.document().find("Последний абзац.")
    dialog.source_editor.setTextCursor(last_cursor)
    dialog.title_edit.setText("Глава 3")
    dialog._create_boundary_at_cursor()

    middle_cursor = dialog.source_editor.document().find("Средний абзац.")
    dialog._show_insertion_preview(middle_cursor)
    dialog.title_edit.setText("Глава 2")
    dialog._create_boundary_at_cursor()

    titles = [
        dialog.chapter_list.item(row).text()
        for row in range(dialog.chapter_list.count())
    ]
    assert titles == ["Глава 1", "Глава 2", "Глава 3"]
    assert dialog.chapter_list.currentItem().text() == "Глава 2"


def test_chapter_markup_dialog_shows_insert_cursor_preview():
    _app()
    source_html = (
        "<!DOCTYPE HTML><html><body>"
        "<p>Первый абзац.</p>"
        "<p>Второй абзац.</p>"
        "</body></html>"
    )
    dialog = ChapterMarkupDialog(source_html, {}, set())

    cursor = dialog.source_editor.document().find("Второй абзац.")
    dialog._show_insertion_preview(cursor)

    marker = dialog.source_editor.insertion_cursor()
    assert marker is not None
    assert marker.block().text() == "Второй абзац."
    assert dialog.source_editor.extraSelections() == []


def test_chapter_markup_dialog_does_not_treat_dialogue_as_boundary():
    _app()
    source_html = (
        "<!DOCTYPE HTML><html><body>"
        "<p>— Мы определенно не в Калифорнии.</p>"
        "<p>········  Глава 1  ········</p>"
        "</body></html>"
    )
    dialog = ChapterMarkupDialog(source_html, {}, set())

    dialogue_cursor = dialog.source_editor.document().find(
        "Мы определенно не в Калифорнии"
    )
    boundary_cursor = dialog.source_editor.document().find("Глава 1")

    assert dialog._boundary_from_block(dialogue_cursor.block()) is None
    assert dialog._boundary_from_block(boundary_cursor.block()) == "Глава 1"


def test_chapter_source_editor_paints_insert_cursor():
    app = _app()
    dialog = ChapterMarkupDialog(
        "<!DOCTYPE HTML><html><body><p>Первый абзац.</p></body></html>",
        {},
        set(),
    )
    dialog.show()
    cursor = dialog.source_editor.document().find("Первый абзац.")
    dialog._show_insertion_preview(cursor)

    app.processEvents()
    dialog.source_editor.viewport().repaint()

    assert dialog.source_editor.insertion_cursor() is not None


def test_chapter_markup_dialog_uses_fixed_insert_cursor():
    _app()
    source_html = (
        "<!DOCTYPE HTML><html><body>"
        "<p>Первый абзац.</p>"
        "<p>Второй абзац.</p>"
        "</body></html>"
    )
    dialog = ChapterMarkupDialog(source_html, {}, set())
    dialog.title_edit.setText("Глава 1")

    marker_cursor = dialog.source_editor.document().find("Второй абзац.")
    dialog._show_insertion_preview(marker_cursor)
    first_cursor = dialog.source_editor.document().find("Первый абзац.")
    dialog.source_editor.setTextCursor(first_cursor)

    dialog._create_boundary_at_cursor()
    dialog.accept()

    assert "Второй абзац." in dialog.chapter_html["Глава 1"]
    assert "Первый абзац." not in dialog.chapter_html["Глава 1"]


def test_chapter_markup_dialog_selecting_chapter_moves_to_its_text():
    _app()
    source_html = (
        "<!DOCTYPE HTML><html><body>"
        "<h1>Глава 1</h1>"
        "<p>Первый абзац.</p>"
        "<h1>Глава 2</h1>"
        "<p>Второй абзац.</p>"
        "</body></html>"
    )
    dialog = ChapterMarkupDialog(
        source_html,
        {
            "Глава 1": (
                "<!DOCTYPE HTML><html><body><h1>Глава 1</h1>"
                "<p>Первый абзац.</p></body></html>"
            ),
            "Глава 2": (
                "<!DOCTYPE HTML><html><body><h1>Глава 2</h1>"
                "<p>Второй абзац.</p></body></html>"
            ),
        },
        set(),
    )

    dialog.chapter_list.setCurrentRow(1)

    cursor_position = dialog.source_editor.textCursor().position()
    second_chapter_position = dialog.source_editor.toPlainText().index("Глава 2")
    assert cursor_position <= second_chapter_position
    assert dialog._boundary_position("Глава 2") is not None


def test_chapter_markup_dialog_restores_boundary_before_short_heading():
    _app()
    source_html = (
        "<!DOCTYPE HTML><html><body>"
        "<h1>Глава 1</h1>"
        "<p>Первый абзац.</p>"
        "</body></html>"
    )
    dialog = ChapterMarkupDialog(
        source_html,
        {
            "Глава 1": (
                "<!DOCTYPE HTML><html><body><h1>Глава 1</h1>"
                "<p>Первый абзац.</p></body></html>"
            ),
        },
        set(),
    )

    plain_text = dialog.source_editor.toPlainText()
    boundary_position = plain_text.index("········  Глава 1  ········")
    heading_position = plain_text.index("Глава 1", boundary_position + 1)
    assert boundary_position < heading_position


def test_chapter_markup_dialog_moves_boundary_to_cursor():
    _app()
    source_html = (
        "<!DOCTYPE HTML><html><body>"
        "<p>Первый абзац.</p>"
        "<p>Второй абзац.</p>"
        "<p>Третий абзац.</p>"
        "</body></html>"
    )
    dialog = ChapterMarkupDialog(source_html, {}, set())
    dialog.title_edit.setText("Глава 1")

    cursor = dialog.source_editor.textCursor()
    cursor.setPosition(dialog.source_editor.toPlainText().index("Первый"))
    dialog.source_editor.setTextCursor(cursor)
    dialog._create_boundary_at_cursor()

    cursor.setPosition(dialog.source_editor.toPlainText().index("Третий"))
    dialog.source_editor.setTextCursor(cursor)
    dialog._move_current_boundary_to_cursor()
    dialog.accept()

    assert "Глава 1" in dialog.chapter_html
    assert "Третий абзац." in dialog.chapter_html["Глава 1"]
    assert "Первый абзац." not in dialog.chapter_html["Глава 1"]

    cursor = dialog.source_editor.document().find("Первый абзац.")
    assert cursor.charFormat().fontWeight() != 75
    lines = dialog.source_editor.toPlainText().splitlines()
    assert "" not in lines


def test_chapter_markup_dialog_drag_keeps_source_heading_formatting():
    _app()
    source_html = (
        "<!DOCTYPE HTML><html><body>"
        "<h1 style=\"font-size:22pt; font-weight:600;\">Первый заголовок</h1>"
        "<p>Первый абзац.</p>"
        "<h1 style=\"font-size:22pt; font-weight:600;\">Второй заголовок</h1>"
        "<p>Второй абзац.</p>"
        "</body></html>"
    )
    dialog = ChapterMarkupDialog(source_html, {}, set())
    dialog.title_edit.setText("Глава 1")

    cursor = dialog.source_editor.textCursor()
    cursor.setPosition(dialog.source_editor.toPlainText().index("Первый заголовок"))
    dialog.source_editor.setTextCursor(cursor)
    dialog._create_boundary_at_cursor()

    heading_cursor = dialog.source_editor.document().find("Первый заголовок")
    before_weight = heading_cursor.charFormat().fontWeight()
    before_size = heading_cursor.charFormat().fontPointSize()

    target_cursor = dialog.source_editor.document().find("Второй заголовок")
    dialog._move_boundary_to_cursor(
        "Глава 1",
        target_cursor,
        rebuild=False,
        scroll=False,
    )

    heading_cursor = dialog.source_editor.document().find("Первый заголовок")
    assert heading_cursor.charFormat().fontWeight() == before_weight
    assert heading_cursor.charFormat().fontPointSize() == before_size


def test_chapter_markup_dialog_drag_preview_does_not_move_boundary():
    _app()
    source_html = (
        "<!DOCTYPE HTML><html><body>"
        "<p>Первый абзац.</p>"
        "<p>Второй абзац.</p>"
        "</body></html>"
    )
    dialog = ChapterMarkupDialog(source_html, {}, set())
    dialog.title_edit.setText("Глава 1")

    cursor = dialog.source_editor.textCursor()
    cursor.setPosition(dialog.source_editor.toPlainText().index("Первый"))
    dialog.source_editor.setTextCursor(cursor)
    dialog._create_boundary_at_cursor()
    boundary_position = dialog._boundary_position("Глава 1")

    target_cursor = dialog.source_editor.document().find("Второй абзац.")
    dialog._show_boundary_drop_preview(target_cursor)

    assert dialog._boundary_position("Глава 1") == boundary_position
    marker = dialog.source_editor.insertion_cursor()
    assert marker is not None
    assert marker.block().text() == "Второй абзац."
    assert dialog.source_editor.extraSelections() == []
