"""Role management dialogs."""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QPushButton, QTableWidget,
    QTableWidgetItem, QHeaderView, QAbstractItemView, QFrame,
    QHBoxLayout, QComboBox, QWidget, QToolButton, QStyle,
    QLineEdit, QStyledItemDelegate
)
from PySide6.QtCore import Qt
from typing import Any, Callable, Dict, List, Optional, Set

from config.constants import (
    ACTOR_ROLES_DIALOG_HEIGHT,
    ACTOR_ROLES_DIALOG_WIDTH,
)
from services.assignment_service import get_actor_for_character
from utils.i18n import translate_widget_tree


class _ActorComboDelegate(QStyledItemDelegate):
    """Combo editor for project role actor cells."""

    def __init__(self, dialog: "ProjectRolesDialog") -> None:
        super().__init__(dialog)
        self.dialog = dialog

    def createEditor(self, parent, option, index):
        combo = QComboBox(parent)
        combo.addItem("Без актёра", ProjectRolesDialog.NO_ACTOR)
        for actor_id, actor in self.dialog._sorted_actors():
            combo.addItem(actor.get("name", actor_id), actor_id)
        return combo

    def setEditorData(self, editor, index) -> None:
        actor_id = index.data(Qt.UserRole) or ProjectRolesDialog.NO_ACTOR
        combo_index = editor.findData(actor_id)
        editor.setCurrentIndex(combo_index if combo_index >= 0 else 0)

    def setModelData(self, editor, model, index) -> None:
        actor_id = editor.currentData()
        model.setData(index, editor.currentText(), Qt.DisplayRole)
        model.setData(index, actor_id, Qt.UserRole)


class ActorRolesDialog(QDialog):
    """Actor Roles Dialog dialog."""

    def __init__(
        self,
        actor_name: str,
        current_roles: List[str],
        parent: Optional[QDialog] = None,
        role_stats: Optional[List[Dict[str, Any]]] = None
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"Роли: {actor_name}")
        self.resize(ACTOR_ROLES_DIALOG_WIDTH, ACTOR_ROLES_DIALOG_HEIGHT)

        self._table: QTableWidget
        self._roles = current_roles
        self._init_ui(role_stats or self._roles_to_stats(current_roles))
        translate_widget_tree(self)

    def _init_ui(self, role_stats: List[Dict[str, Any]]) -> None:
        layout = QVBoxLayout(self)

        self._table = QTableWidget(0, 3)
        self._table.setHorizontalHeaderLabels([
            "Персонаж", "Колец", "Слов"
        ])
        self._table.setSortingEnabled(True)
        self._table.setShowGrid(False)
        self._table.setAlternatingRowColors(True)
        self._table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._table.setFrameShape(QFrame.NoFrame)
        self._table.verticalHeader().setVisible(False)
        self._table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.Stretch
        )
        self._table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeToContents
        )
        self._table.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.ResizeToContents
        )

        layout.addWidget(self._table)
        self._populate_table(role_stats)

        btn_close = QPushButton("Закрыть")
        btn_close.clicked.connect(self.accept)
        layout.addWidget(btn_close)

    def _populate_table(self, role_stats: List[Dict[str, Any]]) -> None:
        self._table.setSortingEnabled(False)
        self._table.setRowCount(0)

        for stat in role_stats:
            row = self._table.rowCount()
            self._table.insertRow(row)

            name_item = QTableWidgetItem(stat.get("name", ""))
            self._table.setItem(row, 0, name_item)

            rings_item = QTableWidgetItem()
            rings_item.setData(Qt.DisplayRole, int(stat.get("rings", 0)))
            self._table.setItem(row, 1, rings_item)

            words_item = QTableWidgetItem()
            words_item.setData(Qt.DisplayRole, int(stat.get("words", 0)))
            self._table.setItem(row, 2, words_item)

        self._table.setSortingEnabled(True)
        self._table.sortItems(0, Qt.AscendingOrder)

    def _roles_to_stats(self, roles: List[str]) -> List[Dict[str, Any]]:
        return [
            {"name": role, "rings": 0, "words": 0}
            for role in roles
        ]

    def get_roles(self) -> List[str]:
        """Return roles."""
        return self._roles.copy()


class ProjectRolesDialog(QDialog):
    """Dialog for viewing and editing all project roles."""

    NO_ACTOR = "__no_actor__"
    MIXED_ACTOR = "__mixed_actor__"

    def __init__(
        self,
        project_data: Dict[str, Any],
        parent: Optional[QWidget] = None,
        get_episode_lines: Optional[Callable[[str], List[Dict[str, Any]]]] = None,
        on_changed: Optional[Callable[[], None]] = None,
    ) -> None:
        super().__init__(parent)
        self.project_data = project_data
        self.get_episode_lines = get_episode_lines
        self.on_changed = on_changed
        self._role_rows: List[Dict[str, Any]] = []
        self._is_populating = False

        self.setWindowTitle("Роли проекта")
        self.resize(820, 520)
        self._init_ui()
        self.refresh()
        translate_widget_tree(self)

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)

        self._search_edit = QLineEdit()
        self._search_edit.setPlaceholderText("Поиск по роли или актёру...")
        self._search_edit.setClearButtonEnabled(True)
        self._search_edit.textChanged.connect(self._apply_filter)
        layout.addWidget(self._search_edit)

        self._table = QTableWidget(0, 4)
        self._table.setHorizontalHeaderLabels([
            "Роль", "Актёр", "Серии", ""
        ])
        self._table.setShowGrid(False)
        self._table.setAlternatingRowColors(True)
        self._table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._table.setEditTriggers(
            QAbstractItemView.DoubleClicked | QAbstractItemView.SelectedClicked
        )
        self._table.setFrameShape(QFrame.NoFrame)
        self._table.verticalHeader().setVisible(False)
        self._table.setItemDelegateForColumn(1, _ActorComboDelegate(self))
        self._table.itemChanged.connect(self._on_item_changed)
        self._table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.Stretch
        )
        self._table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeToContents
        )
        self._table.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.Stretch
        )
        self._table.horizontalHeader().setSectionResizeMode(
            3, QHeaderView.ResizeToContents
        )
        layout.addWidget(self._table)

        buttons = QHBoxLayout()
        buttons.addStretch()
        btn_close = QPushButton("Закрыть")
        btn_close.clicked.connect(self.accept)
        buttons.addWidget(btn_close)
        layout.addLayout(buttons)

    def refresh(self) -> None:
        """Refresh table content."""
        self._role_rows = self._collect_roles()
        self._table.setUpdatesEnabled(False)
        self._table.viewport().setUpdatesEnabled(False)
        self._is_populating = True
        self._table.setSortingEnabled(False)
        self._table.blockSignals(True)
        self._table.setRowCount(0)

        for role in self._role_rows:
            self._add_role_row(role)

        self._table.blockSignals(False)
        self._table.setSortingEnabled(True)
        self._table.sortItems(0, Qt.AscendingOrder)
        self._is_populating = False
        self._apply_filter()
        self._table.viewport().setUpdatesEnabled(True)
        self._table.setUpdatesEnabled(True)

    def _add_role_row(self, role: Dict[str, Any]) -> None:
        row = self._table.rowCount()
        self._table.insertRow(row)

        role_item = QTableWidgetItem(role["name"])
        role_item.setData(Qt.UserRole, role["name"])
        self._table.setItem(row, 0, role_item)

        actor_item = QTableWidgetItem(role["actor_name"])
        actor_item.setData(Qt.UserRole, role["actor_id"] or self.NO_ACTOR)
        actor_item.setToolTip("Двойной клик, чтобы сменить актёра")
        actor_item.setFlags(actor_item.flags() | Qt.ItemIsEditable)
        self._table.setItem(row, 1, actor_item)

        episodes_item = QTableWidgetItem(", ".join(role["episodes"]) or "—")
        episodes_item.setToolTip(episodes_item.text())
        self._table.setItem(row, 2, episodes_item)

        btn_reset = QToolButton()
        btn_reset.setIcon(self.style().standardIcon(QStyle.SP_TrashIcon))
        btn_reset.setToolTip("Сбросить привязку роли к актёру")
        btn_reset.setAutoRaise(True)
        btn_reset.clicked.connect(
            lambda checked=False, name=role["name"]:
            self._reset_role_assignment(name)
        )
        self._table.setCellWidget(row, 3, btn_reset)

    def _collect_roles(self) -> List[Dict[str, Any]]:
        roles: Set[str] = set()
        episodes_by_role: Dict[str, Set[str]] = {}

        global_map = self.project_data.get("global_map", {})
        if isinstance(global_map, dict):
            roles.update(str(role) for role in global_map.keys())

        episode_maps = self.project_data.get("episode_actor_map", {})
        if isinstance(episode_maps, dict):
            for ep, episode_map in episode_maps.items():
                if not isinstance(episode_map, dict):
                    continue
                for role in episode_map.keys():
                    role_name = str(role)
                    roles.add(role_name)
                    episodes_by_role.setdefault(role_name, set()).add(str(ep))

        for ep in self.project_data.get("episodes", {}).keys():
            for line in self._lines_for_episode(str(ep)):
                role_name = str(line.get("char", "")).strip()
                if not role_name:
                    continue
                roles.add(role_name)
                episodes_by_role.setdefault(role_name, set()).add(str(ep))

        result = []
        for role in sorted(roles, key=str.lower):
            actor_id = self._role_actor_id(role, episodes_by_role.get(role, set()))
            result.append({
                "name": role,
                "actor_id": actor_id,
                "actor_name": self._role_actor_name(actor_id),
                "episodes": sorted(
                    episodes_by_role.get(role, set()),
                    key=self._episode_sort_key
                ),
            })
        return result

    def _lines_for_episode(self, ep: str) -> List[Dict[str, Any]]:
        if self.get_episode_lines is not None:
            return self.get_episode_lines(ep)

        lines = self.project_data.get("loaded_episodes", {}).get(ep, [])
        return lines if isinstance(lines, list) else []

    def _role_actor_id(self, role: str, episodes: Set[str]) -> Optional[str]:
        actor_ids = set()
        for ep in episodes:
            actor_ids.add(get_actor_for_character(self.project_data, role, ep))

        if not actor_ids:
            actor_ids.add(self.project_data.get("global_map", {}).get(role))

        if len(actor_ids) == 1:
            return actor_ids.pop()
        return self.MIXED_ACTOR

    def _role_actor_name(self, actor_id: Optional[str]) -> str:
        if actor_id == self.MIXED_ACTOR:
            return "Разные"
        if not actor_id:
            return "Без актёра"
        actor = self.project_data.get("actors", {}).get(actor_id, {})
        if isinstance(actor, dict):
            return actor.get("name", actor_id)
        return str(actor_id)

    def _assign_role(self, role: str, actor_id: Optional[str]) -> None:
        if actor_id == self.MIXED_ACTOR:
            return

        global_map = self.project_data.setdefault("global_map", {})
        if actor_id == self.NO_ACTOR:
            global_map.pop(role, None)
        else:
            global_map[role] = actor_id

        episode_maps = self.project_data.get("episode_actor_map", {})
        if isinstance(episode_maps, dict):
            for episode_map in episode_maps.values():
                if isinstance(episode_map, dict):
                    episode_map.pop(role, None)

        self._notify_changed()
        self.refresh()

    def _on_item_changed(self, item: QTableWidgetItem) -> None:
        if self._is_populating or item.column() != 1:
            return
        role_item = self._table.item(item.row(), 0)
        if role_item is None:
            return
        self._assign_role(role_item.data(Qt.UserRole), item.data(Qt.UserRole))

    def _reset_role_assignment(self, role: str) -> None:
        """Clear actor assignments for a role without touching episode text."""
        self.project_data.setdefault("global_map", {}).pop(role, None)
        episode_maps = self.project_data.get("episode_actor_map", {})
        if isinstance(episode_maps, dict):
            for episode_map in episode_maps.values():
                if isinstance(episode_map, dict):
                    episode_map.pop(role, None)

        self._notify_changed()
        self.refresh()

    def _notify_changed(self) -> None:
        if self.on_changed is not None:
            self.on_changed()

    def _apply_filter(self) -> None:
        query = self._search_edit.text().strip().casefold()
        for row in range(self._table.rowCount()):
            role_item = self._table.item(row, 0)
            actor_item = self._table.item(row, 1)
            haystack = " ".join([
                role_item.text() if role_item else "",
                actor_item.text() if actor_item else "",
            ]).casefold()
            self._table.setRowHidden(row, bool(query) and query not in haystack)

    def _sorted_actors(self) -> List[tuple]:
        actors = self.project_data.get("actors", {})
        if not isinstance(actors, dict):
            return []
        return sorted(
            actors.items(),
            key=lambda item: item[1].get("name", "").lower()
        )

    def _episode_sort_key(self, value: str) -> tuple:
        if value.isdigit():
            return (0, int(value), value)
        return (1, value.lower(), value)
