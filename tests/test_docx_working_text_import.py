"""Tests for DOCX import creating working text."""

from pathlib import Path
from unittest.mock import MagicMock

from PySide6.QtWidgets import QDialog

from core.commands import UndoStack
from services import EpisodeService, ProjectService, ScriptTextService
from ui.main_window import MainWindow


def _make_window_stub(tmp_path):
    window = MainWindow.__new__(MainWindow)
    window.data = ProjectService().create_new_project("Test")
    window.current_project_path = str(tmp_path / "project.json")
    window.current_ep_stats = []
    window.episode_service = EpisodeService()
    window.script_text_service = ScriptTextService()
    window.undo_stack = UndoStack()
    window.update_ep_list = MagicMock()
    window.set_dirty = MagicMock()
    return window


def test_docx_import_creates_working_text(tmp_path, monkeypatch):
    window = _make_window_stub(tmp_path)
    docx_path = str(tmp_path / "Episode_01.docx")

    class FakeDocxImportDialog:
        def __init__(self, parent=None, file_path=None):
            self.file_path = file_path

        def exec(self):
            return QDialog.Accepted

        def get_result(self):
            return {
                "stats": [{"name": "Hero", "lines": 1, "rings": 1, "words": 2}],
                "lines": [{
                    "s": 1.0,
                    "e": 2.0,
                    "char": "Hero",
                    "text": "Hello docx",
                    "s_raw": "00:00:01,000",
                    "e_raw": "00:00:02,000",
                }],
                "source_path": docx_path,
                "tables_count": 1,
            }

    monkeypatch.setattr("ui.dialogs.DocxImportDialog", FakeDocxImportDialog)
    monkeypatch.setattr(
        "ui.main_window.QInputDialog.getText",
        lambda *args, **kwargs: ("1", True)
    )
    monkeypatch.setattr("ui.main_window.QMessageBox.information", lambda *args: None)

    window.import_docx_with_dialog(docx_path)

    text_path = Path(window.data["episode_texts"]["1"])
    assert text_path.exists()
    assert text_path.parent.name == "project_texts_dm"
    assert window.data["episodes"]["1"] == docx_path
    assert window.data["loaded_episodes"]["1"][0]["_working_text"] is True
    assert window.get_episode_lines("1")[0]["text"] == "Hello docx"
