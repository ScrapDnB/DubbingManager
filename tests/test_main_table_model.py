from PySide6.QtCore import QObject, Qt
from PySide6.QtGui import QBrush

from services import ASSIGNMENT_SCOPE_EPISODE, ASSIGNMENT_SCOPE_GLOBAL
from ui.main_window import ACTOR_ID_ROLE, SCOPE_ROLE, MainTableModel


class FakeEpisodeCombo:
    def currentData(self):
        return "1"


class FakeMainWindow(QObject):
    def __init__(self):
        super().__init__()
        self.ep_combo = FakeEpisodeCombo()
        self.data = {
            "actors": {
                "actor-1": {"name": "Alice", "color": "#112233"},
                "actor-2": {"name": "Bob", "color": "#445566"},
            },
            "global_map": {"Hero": "actor-1"},
            "episode_actor_map": {},
        }
        self.calls = []

    def rename_character_from_table(self, old_name, new_name):
        self.calls.append(("rename", old_name, new_name))
        return True

    def update_assignment_scope_value(self, char_name, scope, actor_id):
        self.calls.append(("scope", char_name, scope, actor_id))

    def update_map_value(self, char_name, actor_id, scope):
        self.calls.append(("actor", char_name, actor_id, scope))


def make_model():
    window = FakeMainWindow()
    model = MainTableModel(window)
    model.set_rows([
        {
            "name": "Hero",
            "lines": 2,
            "rings": 1,
            "words": 5,
            "scope": ASSIGNMENT_SCOPE_GLOBAL,
            "actor_id": "actor-1",
        }
    ])
    return model, window


def test_main_table_model_exposes_assignment_roles_and_actor_color():
    model, _window = make_model()

    assert model.data(model.index(0, 0), Qt.DisplayRole) == "Hero"
    assert model.data(model.index(0, 4), Qt.DisplayRole) == "Глобально"
    assert model.data(model.index(0, 4), SCOPE_ROLE) == ASSIGNMENT_SCOPE_GLOBAL
    assert model.data(model.index(0, 5), Qt.DisplayRole) == "Alice"
    assert model.data(model.index(0, 5), ACTOR_ID_ROLE) == "actor-1"
    assert "#112233" in model.data(model.index(0, 5), Qt.ToolTipRole)

    brush = model.data(model.index(0, 5), Qt.BackgroundRole)
    assert isinstance(brush, QBrush)
    assert brush.color().name() == "#112233"
    assert brush.color().alpha() == 72


def test_main_table_model_updates_actor_assignment():
    model, window = make_model()

    changed = model.setData(model.index(0, 5), "actor-2", ACTOR_ID_ROLE)

    assert changed is True
    assert model.data(model.index(0, 5), Qt.DisplayRole) == "Bob"
    assert model.data(model.index(0, 5), ACTOR_ID_ROLE) == "actor-2"
    assert window.calls == [
        ("actor", "Hero", "actor-2", ASSIGNMENT_SCOPE_GLOBAL)
    ]


def test_main_table_model_updates_scope_and_renames_character():
    model, window = make_model()

    scope_changed = model.setData(
        model.index(0, 4), ASSIGNMENT_SCOPE_EPISODE, SCOPE_ROLE
    )
    rename_changed = model.setData(model.index(0, 0), "Heroine", Qt.EditRole)

    assert scope_changed is True
    assert rename_changed is True
    assert model.data(model.index(0, 4), Qt.DisplayRole) == "Серия"
    assert model.data(model.index(0, 0), Qt.DisplayRole) == "Heroine"
    assert window.calls == [
        ("scope", "Hero", ASSIGNMENT_SCOPE_EPISODE, "actor-1"),
        ("rename", "Hero", "Heroine"),
    ]
