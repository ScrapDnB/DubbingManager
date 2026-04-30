"""Tests for actor renaming from the actor table."""

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QTableWidget, QTableWidgetItem

from core.commands import UndoStack
from ui.main_window import MainWindow


@pytest.fixture
def app():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


class ControllerStub:
    def __init__(self):
        self.refreshed = False

    def refresh(self):
        self.refreshed = True


class ComboStub:
    def currentData(self):
        return "1"


def _make_window_stub():
    window = MainWindow.__new__(MainWindow)
    window.data = {
        "actors": {
            "actor-1": {"name": "Old Name", "color": "#ffffff", "roles": []}
        }
    }
    window.actor_table = QTableWidget(1, 3)
    window.actor_controller = ControllerStub()
    window.undo_stack = UndoStack()
    window.ep_combo = ComboStub()
    window.main_refreshed = False
    window.windows_refreshed = False
    window.dirty = False
    window.refresh_main_table = lambda: setattr(window, "main_refreshed", True)
    window._refresh_open_windows = (
        lambda ep: setattr(window, "windows_refreshed", True)
    )
    window.set_dirty = lambda dirty=True: setattr(window, "dirty", dirty)
    return window


def test_actor_rename_updates_model_and_can_undo(app):
    window = _make_window_stub()
    item = QTableWidgetItem("New Name")
    item.setData(Qt.UserRole, "actor-1")
    window.actor_table.setItem(0, 0, item)

    window.on_actor_renamed(item)

    assert window.data["actors"]["actor-1"]["name"] == "New Name"
    assert window.actor_controller.refreshed is True
    assert window.main_refreshed is True
    assert window.windows_refreshed is True
    assert window.dirty is True

    window.undo_stack.undo()

    assert window.data["actors"]["actor-1"]["name"] == "Old Name"


def test_actor_rename_rejects_empty_name(app):
    window = _make_window_stub()
    item = QTableWidgetItem("")
    item.setData(Qt.UserRole, "actor-1")
    window.actor_table.setItem(0, 0, item)

    window.on_actor_renamed(item)

    assert window.data["actors"]["actor-1"]["name"] == "Old Name"
    assert item.text() == "Old Name"
    assert window.dirty is False
