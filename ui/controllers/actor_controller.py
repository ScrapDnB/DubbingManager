"""Controller for actor management."""

from PySide6.QtWidgets import (
    QTableWidget, QTableWidgetItem, QHeaderView,
    QAbstractItemView, QFrame, QPushButton, QWidget, QHBoxLayout
)
from PySide6.QtGui import QColor
from PySide6.QtCore import Qt
from typing import Dict, List, Any, Optional, Callable

from services import ActorService
from services.assignment_service import get_actor_roles
from utils.helpers import wrap_widget


class ActorController:
    """Actor Controller controller."""

    def __init__(
        self,
        actor_table: QTableWidget,
        actor_service: ActorService,
        data_ref: Dict[str, Any],
        on_dirty_callback: Optional[Callable] = None,
        on_edit_roles_callback: Optional[Callable] = None,
        on_color_click_callback: Optional[Callable] = None
    ) -> None:
        self.actor_table: QTableWidget = actor_table
        self.actor_service: ActorService = actor_service
        self.data_ref: Dict[str, Any] = data_ref  # Internal implementation detail
        self.on_dirty_callback = on_dirty_callback
        self.on_edit_roles_callback = on_edit_roles_callback
        self.on_color_click_callback = on_color_click_callback
        
        self._setup_table()

    def _setup_table(self) -> None:
        """Setup table."""
        self.actor_table.setHorizontalHeaderLabels(
            ["Актер", "Роли", "Цвет", "Пол"]
        )
        self.actor_table.setShowGrid(False)
        self.actor_table.setAlternatingRowColors(True)
        self.actor_table.setSortingEnabled(True)
        self.actor_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.actor_table.setFrameShape(QFrame.NoFrame)
        self.actor_table.verticalHeader().setVisible(False)
        self.actor_table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.Stretch
        )
        self.actor_table.setColumnWidth(1, 100)
        self.actor_table.setColumnWidth(2, 60)
        self.actor_table.setColumnWidth(3, 50)
        
        # Internal implementation detail
        self.actor_table.cellClicked.connect(self._on_cell_clicked)

    def _on_cell_clicked(self, row: int, col: int) -> None:
        """Handle cell click."""
        if col == 2 and self.on_color_click_callback:  # Internal implementation detail
            item: Optional[QTableWidgetItem] = self.actor_table.item(row, 0)
            if item:
                aid: Optional[str] = item.data(Qt.UserRole)
                if aid:
                    self.on_color_click_callback(aid)

    def _find_actor_row(self, actor_id: str) -> Optional[int]:
        """Find actor row."""
        for row in range(self.actor_table.rowCount()):
            item = self.actor_table.item(row, 0)
            if item and item.data(Qt.UserRole) == actor_id:
                return row
        return None

    def _get_actor_roles(self) -> Dict[str, List[str]]:
        """Return actor roles."""
        actor_roles: Dict[str, List[str]] = {
            aid: [] for aid in self.data_ref["actors"]
        }
        for aid in actor_roles:
            actor_roles[aid] = get_actor_roles(self.data_ref, aid)
        return actor_roles

    def refresh(self) -> None:
        """Refresh."""
        import logging
        logger = logging.getLogger(__name__)

        logger.info(f"ActorController.refresh: actors={len(self.data_ref.get('actors', {}))}, table={self.actor_table}")

        self.actor_table.blockSignals(True)
        self.actor_table.setSortingEnabled(False)
        self.actor_table.setHorizontalHeaderLabels(
            ["Актер", "Роли", "Цвет", "Пол"]
        )
        self.actor_table.setRowCount(0)

        actor_roles = self._get_actor_roles()

        aid: str
        info: Dict[str, Any]
        for aid, info in self.data_ref["actors"].items():
            row: int = self.actor_table.rowCount()
            self.actor_table.insertRow(row)

            # Internal implementation detail
            item: QTableWidgetItem = QTableWidgetItem(info["name"])
            item.setData(Qt.UserRole, aid)
            self.actor_table.setItem(row, 0, item)
            item.setFlags(item.flags() | Qt.ItemIsEditable)

            # Internal implementation detail
            btn: QPushButton = QPushButton(f"Роли ({len(actor_roles[aid])})")
            if self.on_edit_roles_callback:
                btn.clicked.connect(
                    lambda checked=False, a=aid, n=info["name"], r=actor_roles[aid]:
                    self.on_edit_roles_callback(a, n, r)
                )
            self.actor_table.setCellWidget(row, 1, wrap_widget(btn))

            # Internal implementation detail
            color_item: QTableWidgetItem = QTableWidgetItem()
            color_item.setBackground(QColor(info["color"]))
            self.actor_table.setItem(row, 2, color_item)

            gender_item: QTableWidgetItem = QTableWidgetItem(
                info.get("gender", "")
            )
            gender_item.setFlags(gender_item.flags() & ~Qt.ItemIsEditable)
            self.actor_table.setItem(row, 3, gender_item)

        self.actor_table.setSortingEnabled(True)
        self.actor_table.blockSignals(False)
        logger.info(f"ActorController.refresh: loaded {self.actor_table.rowCount()} actors")

    def update_actor_color(self, actor_id: str, color: str) -> None:
        """Update actor color."""
        self.actor_service.update_actor_color(
            self.data_ref["actors"], actor_id, color
        )
        
        # Internal implementation detail
        row = self._find_actor_row(actor_id)
        if row is not None:
            color_item = self.actor_table.item(row, 2)
            if color_item:
                color_item.setBackground(QColor(color))
            else:
                # Internal implementation detail
                color_item = QTableWidgetItem()
                color_item.setBackground(QColor(color))
                self.actor_table.setItem(row, 2, color_item)
        
        self._mark_dirty()

    def rename_actor(self, actor_id: str, new_name: str) -> None:
        """Rename actor."""
        self.actor_service.rename_actor(
            self.data_ref["actors"], actor_id, new_name
        )
        
        # Internal implementation detail
        row = self._find_actor_row(actor_id)
        if row is not None:
            item = self.actor_table.item(row, 0)
            if item:
                item.setText(new_name)
        
        self._mark_dirty()

    def update_actor_roles(
        self,
        actor_id: str,
        new_roles: List[str]
    ) -> None:
        """Update actor roles."""
        self.actor_service.update_actor_roles(
            self.data_ref["global_map"], actor_id, new_roles
        )
        
        # Internal implementation detail
        row = self._find_actor_row(actor_id)
        if row is not None:
            btn_widget = self.actor_table.cellWidget(row, 1)
            if btn_widget:
                btn = btn_widget.findChild(QPushButton)
                if btn:
                    btn.setText(f"Роли ({len(new_roles)})")
        
        self._mark_dirty()

    def bulk_assign_actors(
        self,
        characters: List[str],
        actor_id: Optional[str]
    ) -> None:
        """Bulk assign actors."""
        self.actor_service.bulk_assign_actors(
            self.data_ref["global_map"], characters, actor_id
        )
        self.refresh()
        self._mark_dirty()

    def get_actor_roles(self, actor_id: str) -> List[str]:
        """Return actor roles."""
        return get_actor_roles(self.data_ref, actor_id)

    def get_unassigned_characters(self) -> List[str]:
        """Return unassigned characters."""
        return self.actor_service.get_unassigned_characters(
            self.data_ref["global_map"], []
        )

    def _mark_dirty(self) -> None:
        """Mark dirty."""
        if self.on_dirty_callback:
            self.on_dirty_callback()
