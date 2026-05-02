"""Actor roles dialog."""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QPushButton, QTableWidget,
    QTableWidgetItem, QHeaderView, QAbstractItemView, QFrame
)
from PySide6.QtCore import Qt
from typing import Any, Dict, List, Optional

from config.constants import (
    ACTOR_ROLES_DIALOG_HEIGHT,
    ACTOR_ROLES_DIALOG_WIDTH,
)
from utils.i18n import translate_widget_tree


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
