"""Tests for actor highlight filter dialog."""

from PySide6.QtWidgets import QApplication

from ui.dialogs.actor_filter import ActorFilterDialog


def test_actor_filter_dialog_returns_negative_selection():
    app = QApplication.instance() or QApplication([])
    _ = app

    dialog = ActorFilterDialog(
        {
            "actor1": {"name": "Actor One"},
            "actor2": {"name": "Actor Two"},
        },
        selected_ids=["actor1"],
        negative_ids=["actor2"],
    )

    assert dialog.get_selected() == ["actor1"]
    assert dialog.get_negative_selected() == ["actor2"]
