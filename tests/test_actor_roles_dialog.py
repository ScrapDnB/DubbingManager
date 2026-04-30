"""Tests for actor roles statistics dialog."""

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from ui.dialogs.roles import ActorRolesDialog
from ui.main_window import MainWindow


@pytest.fixture
def app():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_actor_roles_dialog_shows_stats_and_sorts_numbers(app):
    dialog = ActorRolesDialog(
        "Actor",
        ["Hero", "Villain"],
        role_stats=[
            {"name": "Hero", "rings": 2, "words": 10},
            {"name": "Villain", "rings": 12, "words": 3},
        ]
    )

    dialog._table.sortItems(1, Qt.DescendingOrder)

    assert dialog._table.item(0, 0).text() == "Villain"
    assert dialog._table.item(0, 1).data(Qt.DisplayRole) == 12
    assert dialog.get_roles() == ["Hero", "Villain"]


def test_actor_role_stats_uses_working_lines():
    window = MainWindow.__new__(MainWindow)
    window.data = {
        "episodes": {"1": "/source.ass", "2": "/source.docx"},
        "global_map": {"Hero": "actor-1", "Villain": "actor-1", "Other": "actor-2"},
        "replica_merge_config": {"merge": False},
    }
    lines_by_ep = {
        "1": [
            {"char": "Hero", "text": "one two", "s": 1.0, "e": 2.0, "_working_text": True},
            {"char": "Other", "text": "skip me", "s": 3.0, "e": 4.0, "_working_text": True},
        ],
        "2": [
            {"char": "Hero", "text": "three", "s": 1.0, "e": 2.0, "_working_text": True},
            {"char": "Villain", "text": "four five six", "s": 3.0, "e": 4.0, "_working_text": True},
        ],
    }
    window.get_episode_lines = lambda ep: lines_by_ep.get(str(ep), [])

    stats = window._get_actor_role_stats("actor-1", ["Hero", "Villain"])

    assert stats == [
        {"name": "Hero", "rings": 2, "words": 3},
        {"name": "Villain", "rings": 1, "words": 3},
    ]
