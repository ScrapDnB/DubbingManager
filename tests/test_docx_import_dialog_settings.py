"""Tests for DOCX import dialog saved column mapping."""

import pytest
from PySide6.QtWidgets import QApplication, QWidget

from services import GlobalSettingsService
from ui.dialogs.docx_import import DocxImportDialog


@pytest.fixture
def app():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


class ParentStub(QWidget):
    def __init__(self, settings_file):
        super().__init__()
        self.global_settings_service = GlobalSettingsService()
        self.global_settings_service._settings_file = settings_file
        self.global_settings = self.global_settings_service.load_settings()


def test_dialog_applies_saved_mapping(app, tmp_path):
    parent = ParentStub(tmp_path / "settings.json")
    parent.global_settings["docx_import_config"] = {
        "mapping": {
            "character": 0,
            "time_start": None,
            "time_end": None,
            "time_split": 1,
            "text": 2,
        },
        "time_separators": ["|"],
    }

    dialog = DocxImportDialog(parent)
    dialog.current_rows = [
        ["Speaker", "Timing", "Line"],
        ["Hero", "00:00:01,000|00:00:02,000", "Hello"],
    ]
    dialog.available_columns = [0, 1, 2]
    dialog._update_mapping_combos()
    dialog._apply_saved_mapping_or_auto_detect()

    assert dialog.current_mapping["character"] == 0
    assert dialog.current_mapping["time_split"] == 1
    assert dialog.current_mapping["text"] == 2
    assert dialog.separator_edit.text() == "|"


def test_dialog_saves_mapping_on_import(app, tmp_path):
    parent = ParentStub(tmp_path / "settings.json")
    dialog = DocxImportDialog(parent)
    dialog.current_mapping = {
        "character": 0,
        "time_start": None,
        "time_end": None,
        "time_split": 1,
        "text": 2,
    }
    dialog.time_separators = ["-", "|"]

    dialog._save_current_import_settings()

    saved = parent.global_settings["docx_import_config"]
    assert saved["mapping"]["text"] == 2
    assert saved["time_separators"] == ["-", "|"]
