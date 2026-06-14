"""Tests for actor roles statistics dialog."""

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from ui.dialogs.roles import (
    ActorRolesDialog,
    BulkRoleAssignmentDialog,
    ProjectRolesDialog,
    assign_project_roles,
)
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


def test_project_roles_dialog_collects_roles_and_episode_numbers(app):
    project_data = {
        "actors": {
            "actor-1": {"name": "Actor One", "color": "#ff0000"},
        },
        "episodes": {"1": "/tmp/one.ass", "2": "/tmp/two.ass"},
        "global_map": {"Hero": "actor-1", "Mapped Only": "actor-1"},
        "episode_actor_map": {"2": {"Guest": "actor-1"}},
    }
    lines_by_ep = {
        "1": [{"char": "Hero", "text": "hello"}],
        "2": [{"char": "Hero", "text": "again"}, {"char": "Guest", "text": "hi"}],
    }

    dialog = ProjectRolesDialog(
        project_data,
        get_episode_lines=lambda ep: lines_by_ep.get(str(ep), []),
    )

    rows = {
        dialog._table.item(row, 0).text(): dialog._table.item(row, 2).text()
        for row in range(dialog._table.rowCount())
    }

    assert rows["Hero"] == "1, 2"
    assert rows["Guest"] == "2"
    assert rows["Mapped Only"] == "—"


def test_project_roles_dialog_reassigns_role_and_clears_episode_override(app):
    project_data = {
        "actors": {
            "actor-1": {"name": "Actor One", "color": "#ff0000"},
            "actor-2": {"name": "Actor Two", "color": "#00ff00"},
        },
        "episodes": {"1": "/tmp/one.ass"},
        "global_map": {"Hero": "actor-1"},
        "episode_actor_map": {"1": {"Hero": "actor-2"}},
    }
    changed = []

    dialog = ProjectRolesDialog(
        project_data,
        get_episode_lines=lambda ep: [{"char": "Hero", "text": "hello"}],
        on_changed=lambda: changed.append(True),
    )

    dialog._assign_role("Hero", "actor-2")

    assert project_data["global_map"]["Hero"] == "actor-2"
    assert "Hero" not in project_data["episode_actor_map"]["1"]
    assert changed


def test_project_roles_dialog_filters_by_role_and_actor(app):
    project_data = {
        "actors": {
            "actor-1": {"name": "Alice Voice", "color": "#ff0000"},
            "actor-2": {"name": "Bob Voice", "color": "#00ff00"},
        },
        "episodes": {"1": "/tmp/one.ass"},
        "global_map": {"Hero": "actor-1", "Villain": "actor-2"},
        "episode_actor_map": {},
    }
    dialog = ProjectRolesDialog(
        project_data,
        get_episode_lines=lambda ep: [
            {"char": "Hero", "text": "hello"},
            {"char": "Villain", "text": "boo"},
        ],
    )

    dialog._search_edit.setText("hero")

    visible_by_role = [
        dialog._table.item(row, 0).text()
        for row in range(dialog._table.rowCount())
        if not dialog._table.isRowHidden(row)
    ]
    assert visible_by_role == ["Hero"]

    dialog._search_edit.setText("bob")

    visible_by_actor = [
        dialog._table.item(row, 0).text()
        for row in range(dialog._table.rowCount())
        if not dialog._table.isRowHidden(row)
    ]
    assert visible_by_actor == ["Villain"]


def test_project_roles_dialog_resets_role_assignments(app):
    project_data = {
        "actors": {"actor-1": {"name": "Actor One", "color": "#ff0000"}},
        "episodes": {},
        "global_map": {"Hero": "actor-1"},
        "episode_actor_map": {"1": {"Hero": "actor-1"}},
    }
    dialog = ProjectRolesDialog(project_data)
    dialog._reset_role_assignment("Hero")

    assert "Hero" not in project_data["global_map"]
    assert "Hero" not in project_data["episode_actor_map"]["1"]


def test_assign_project_roles_assigns_globally_and_clears_local_overrides():
    project_data = {
        "global_map": {"Hero": "actor-1"},
        "episode_actor_map": {
            "1": {"Hero": "actor-2", "Villain": "actor-1"},
            "2": {"Hero": "actor-1"},
        },
    }

    changed = assign_project_roles(project_data, ["Hero", "Villain"], "actor-3")

    assert changed == 5
    assert project_data["global_map"]["Hero"] == "actor-3"
    assert project_data["global_map"]["Villain"] == "actor-3"
    assert "Hero" not in project_data["episode_actor_map"]["1"]
    assert "Villain" not in project_data["episode_actor_map"]["1"]
    assert "Hero" not in project_data["episode_actor_map"]["2"]


def test_bulk_role_assignment_dialog_assigns_checked_roles(app):
    project_data = {
        "actors": {
            "actor-1": {"name": "Actor One", "color": "#ff0000"},
            "actor-2": {"name": "Actor Two", "color": "#00ff00"},
        },
        "episodes": {"1": "/tmp/one.ass"},
        "global_map": {"Hero": "actor-1"},
        "episode_actor_map": {"1": {"Hero": "actor-1", "Villain": "actor-1"}},
    }
    changed = []
    dialog = BulkRoleAssignmentDialog(
        project_data,
        get_episode_lines=lambda ep: [
            {"char": "Hero", "text": "hello"},
            {"char": "Villain", "text": "boo"},
        ],
        on_changed=lambda: changed.append(True),
    )
    actor_index = dialog._actor_combo.findData("actor-2")
    dialog._actor_combo.setCurrentIndex(actor_index)

    for row in range(dialog._table.rowCount()):
        role = dialog._table.item(row, 1).text()
        if role in {"Hero", "Villain"}:
            dialog._table.item(row, 0).setCheckState(Qt.Checked)

    dialog._apply_assignment()

    assert project_data["global_map"]["Hero"] == "actor-2"
    assert project_data["global_map"]["Villain"] == "actor-2"
    assert project_data["episode_actor_map"]["1"] == {}
    assert dialog.assigned_count == 2
    assert changed
