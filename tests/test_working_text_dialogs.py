"""Tests for dialogs reading working text lines."""

import pytest
from PySide6.QtWidgets import QApplication, QWidget

from ui.dialogs.search import GlobalSearchDialog
from ui.dialogs.summary import SummaryDialog
import ui.dialogs.summary as summary_module


@pytest.fixture
def app():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


class MainAppStub(QWidget):
    def __init__(self, data, lines_by_ep):
        super().__init__()
        self.data = data
        self.lines_by_ep = lines_by_ep
        self.global_settings = {"project_summary_export_metric": "rings"}
        self.global_settings_service = GlobalSettingsServiceStub(
            self.global_settings
        )

    def get_episode_lines(self, ep_num):
        return self.lines_by_ep.get(str(ep_num), [])

    def switch_to_episode(self, ep_num):
        self.switched_to = ep_num


class GlobalSettingsServiceStub:
    def __init__(self, settings):
        self.settings = settings
        self.saved_settings = None

    def get_project_summary_export_metric(self):
        return self.settings.get("project_summary_export_metric", "rings")

    def set_project_summary_export_metric(self, metric):
        self.settings["project_summary_export_metric"] = metric

    def get_settings(self):
        return self.settings

    def save_settings(self, settings):
        self.saved_settings = dict(settings)
        self.settings = settings
        return True


def _project_data():
    return {
        "actors": {
            "actor-1": {"name": "Actor One", "color": "#ff0000"}
        },
        "global_map": {"Hero": "actor-1"},
        "episodes": {"1": "/tmp/source.docx"},
        "loaded_episodes": {},
        "replica_merge_config": {"merge": False},
    }


def _working_lines():
    return [{
        "id": 0,
        "s": 1.0,
        "e": 2.0,
        "char": "Hero",
        "text": "Hello from docx",
        "s_raw": "00:00:01,000",
        "_working_text": True,
    }]


def test_summary_uses_working_text_callback(app):
    data = _project_data()
    parent = MainAppStub(data, {"1": _working_lines()})

    dialog = SummaryDialog(data, "1", parent)

    assert dialog._table.rowCount() == 1
    assert dialog._table.item(0, 0).text() == "Actor One"
    assert dialog._table.item(0, 2).text() == "1"
    assert dialog._table.item(0, 3).text() == "3"


def test_project_summary_exports_formatted_google_sheets_xlsx(
    app,
    tmp_path,
    monkeypatch
):
    data = _project_data()
    data["project_name"] = "Project"
    parent = MainAppStub(data, {"1": _working_lines()})
    dialog = SummaryDialog(data, None, parent)
    save_path = tmp_path / "summary.xlsx"
    messages = []
    save_dialog_calls = []

    monkeypatch.setattr(
        summary_module.QInputDialog,
        "getItem",
        lambda *args, **kwargs: ("Слова", True)
    )
    monkeypatch.setattr(
        summary_module.QFileDialog,
        "getSaveFileName",
        lambda *args, **kwargs: (
            save_dialog_calls.append(args) or (str(save_path), "Excel (*.xlsx)")
        )
    )
    monkeypatch.setattr(
        summary_module.QMessageBox,
        "information",
        lambda *args, **kwargs: messages.append(args)
    )

    dialog._export_project_xlsx()

    assert save_path.exists()
    assert save_path.read_bytes().startswith(b"PK")
    from openpyxl import load_workbook

    workbook = load_workbook(save_path)
    assert workbook.active["C2"].value == 3
    assert workbook.active["D2"].value == 3
    assert save_dialog_calls[0][2] == "Project.xlsx"
    assert parent.global_settings_service.saved_settings[
        "project_summary_export_metric"
    ] == "words"
    assert messages


def test_global_search_uses_working_text_callback(app):
    data = _project_data()
    parent = MainAppStub(data, {"1": _working_lines()})
    dialog = GlobalSearchDialog(data, parent)

    dialog._search_input.setText("docx")
    dialog._perform_search()

    assert dialog._table.rowCount() == 1
    assert dialog._table.item(0, 0).text() == "1"
    assert dialog._table.item(0, 2).text() == "Hero"
    assert dialog._table.item(0, 3).text() == "Hello from docx"
