"""Tests for dialogs reading working text lines."""

import pytest
from PySide6.QtWidgets import QApplication, QWidget

from ui.dialogs.search import GlobalSearchDialog
from ui.dialogs.summary import SummaryDialog


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

    def get_episode_lines(self, ep_num):
        return self.lines_by_ep.get(str(ep_num), [])

    def switch_to_episode(self, ep_num):
        self.switched_to = ep_num


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
