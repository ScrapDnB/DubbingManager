"""Main character table model and delegates."""

from typing import Any, Dict, List, Optional, TYPE_CHECKING

from PySide6.QtCore import (
    QModelIndex,
    QPersistentModelIndex,
    QAbstractTableModel,
    Qt,
)
from PySide6.QtGui import QColor, QBrush
from PySide6.QtWidgets import QComboBox, QStyle, QStyledItemDelegate

from services import (
    ASSIGNMENT_SCOPE_EPISODE,
    ASSIGNMENT_SCOPE_GLOBAL,
    get_actor_for_character,
)
from utils.i18n import tr, translate_source

if TYPE_CHECKING:
    from ui.main_window import MainWindow


CHAR_NAME_ROLE = Qt.UserRole
SCOPE_ROLE = Qt.UserRole + 1
ACTOR_ID_ROLE = Qt.UserRole + 2


class ScopeComboDelegate(QStyledItemDelegate):
    """Delegate for editing assignment scope."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._editing_index = QPersistentModelIndex()

    def createEditor(self, parent, option, index):
        self._editing_index = QPersistentModelIndex(index)
        combo = QComboBox(parent)
        combo.addItem(translate_source("Глобально"), ASSIGNMENT_SCOPE_GLOBAL)
        combo.addItem(translate_source("Серия"), ASSIGNMENT_SCOPE_EPISODE)
        return combo

    def setEditorData(self, editor, index) -> None:
        scope = index.data(SCOPE_ROLE) or ASSIGNMENT_SCOPE_GLOBAL
        found = editor.findData(scope)
        editor.setCurrentIndex(found if found >= 0 else 0)

    def setModelData(self, editor, model, index) -> None:
        model.setData(index, editor.currentData(), SCOPE_ROLE)
        model.setData(index, editor.currentText(), Qt.DisplayRole)

    def updateEditorGeometry(self, editor, option, index) -> None:
        editor.setGeometry(option.rect)

    def destroyEditor(self, editor, index) -> None:
        self._editing_index = QPersistentModelIndex()
        super().destroyEditor(editor, index)

    def paint(self, painter, option, index) -> None:
        if QPersistentModelIndex(index) == self._editing_index:
            brush = (
                option.palette.highlight()
                if option.state & QStyle.State_Selected
                else option.palette.base()
            )
            painter.fillRect(option.rect, brush)
            return
        super().paint(painter, option, index)


class ActorComboDelegate(QStyledItemDelegate):
    """Delegate for assigning actors to characters."""

    def __init__(self, main_window: "MainWindow") -> None:
        super().__init__(main_window)
        self.main_window = main_window
        self._editing_index = QPersistentModelIndex()

    def createEditor(self, parent, option, index):
        self._editing_index = QPersistentModelIndex(index)
        combo = QComboBox(parent)
        combo.addItem("-", None)
        for aid, info in self.main_window.data.get("actors", {}).items():
            combo.addItem(info.get("name", aid), aid)
        return combo

    def setEditorData(self, editor, index) -> None:
        actor_id = index.data(ACTOR_ID_ROLE)
        found = editor.findData(actor_id)
        editor.setCurrentIndex(found if found >= 0 else 0)

    def setModelData(self, editor, model, index) -> None:
        model.setData(index, editor.currentData(), ACTOR_ID_ROLE)
        model.setData(index, editor.currentText(), Qt.DisplayRole)

    def updateEditorGeometry(self, editor, option, index) -> None:
        editor.setGeometry(option.rect)

    def destroyEditor(self, editor, index) -> None:
        self._editing_index = QPersistentModelIndex()
        super().destroyEditor(editor, index)

    def paint(self, painter, option, index) -> None:
        if QPersistentModelIndex(index) == self._editing_index:
            brush = (
                option.palette.highlight()
                if option.state & QStyle.State_Selected
                else option.palette.base()
            )
            painter.fillRect(option.rect, brush)
            return
        super().paint(painter, option, index)


class MainTableModel(QAbstractTableModel):
    """Model for the main character statistics and assignment table."""

    HEADER_KEYS = [
        "table.character",
        "table.lines",
        "table.rings",
        "table.words",
        "table.scope",
        "table.actor",
        None,
    ]

    def __init__(self, main_window: "MainWindow") -> None:
        super().__init__(main_window)
        self.main_window = main_window
        self.rows: List[Dict[str, Any]] = []

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self.rows)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self.HEADER_KEYS)

    def headerData(self, section: int, orientation: Qt.Orientation, role: int):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            key = self.HEADER_KEYS[section]
            return tr(key) if key else "📺"
        return None

    def flags(self, index: QModelIndex):
        if not index.isValid():
            return Qt.NoItemFlags

        flags = Qt.ItemIsEnabled | Qt.ItemIsSelectable
        if index.column() in (0, 4, 5):
            flags |= Qt.ItemIsEditable
        return flags

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole):
        if not index.isValid():
            return None

        row = self.rows[index.row()]
        column = index.column()

        if role in (Qt.DisplayRole, Qt.EditRole):
            return self._display_value(row, column)

        if role == Qt.TextAlignmentRole and column == 6:
            return Qt.AlignCenter

        if role == Qt.ToolTipRole:
            if column == 5:
                return self._actor_tooltip(row.get("actor_id"))
            if column == 6:
                return translate_source("Открыть предпросмотр персонажа")

        if role == Qt.BackgroundRole and column == 5:
            return self._actor_brush(row.get("actor_id"))

        if role == CHAR_NAME_ROLE:
            return row.get("name")
        if role == SCOPE_ROLE and column == 4:
            return row.get("scope")
        if role == ACTOR_ID_ROLE and column == 5:
            return row.get("actor_id")

        return None

    def setData(self, index: QModelIndex, value: Any, role: int = Qt.EditRole) -> bool:
        if not index.isValid():
            return False

        row = self.rows[index.row()]
        column = index.column()

        if column == 0 and role == Qt.EditRole:
            old_name = row.get("name", "")
            new_name = str(value).strip()
            if not new_name or new_name == old_name:
                return False
            if self.main_window.rename_character_from_table(old_name, new_name):
                row["name"] = new_name
                self.dataChanged.emit(index, index, [Qt.DisplayRole, CHAR_NAME_ROLE])
                return True
            return False

        if column == 4 and role == SCOPE_ROLE:
            new_scope = value or ASSIGNMENT_SCOPE_GLOBAL
            if new_scope == row.get("scope"):
                return False
            row["scope"] = new_scope
            self.main_window.update_assignment_scope_value(
                row["name"], new_scope, row.get("actor_id")
            )
            self.dataChanged.emit(
                self.index(index.row(), 4),
                self.index(index.row(), 5),
                [Qt.DisplayRole, SCOPE_ROLE, ACTOR_ID_ROLE, Qt.BackgroundRole],
            )
            return True

        if column == 5 and role == ACTOR_ID_ROLE:
            if value == row.get("actor_id"):
                return False
            row["actor_id"] = value
            self.main_window.update_map_value(
                row["name"], row.get("actor_id"), row.get("scope")
            )
            self.dataChanged.emit(
                index,
                index,
                [Qt.DisplayRole, ACTOR_ID_ROLE, Qt.BackgroundRole, Qt.ToolTipRole],
            )
            return True

        if role == Qt.DisplayRole:
            return True

        return False

    def set_rows(self, rows: List[Dict[str, Any]]) -> None:
        self.beginResetModel()
        self.rows = rows
        self.endResetModel()

    def row_data(self, row: int) -> Optional[Dict[str, Any]]:
        if 0 <= row < len(self.rows):
            return self.rows[row]
        return None

    def update_actor_for_character(self, char_name: str) -> None:
        for row_idx, row in enumerate(self.rows):
            if row.get("name") != char_name:
                continue

            ep = self.main_window.ep_combo.currentData()
            row["actor_id"] = get_actor_for_character(
                self.main_window.data, char_name, ep
            )
            idx = self.index(row_idx, 5)
            self.dataChanged.emit(
                idx,
                idx,
                [Qt.DisplayRole, ACTOR_ID_ROLE, Qt.BackgroundRole, Qt.ToolTipRole],
            )
            return

    def _display_value(self, row: Dict[str, Any], column: int) -> Any:
        if column == 0:
            return row.get("name", "")
        if column == 1:
            return row.get("lines", 0)
        if column == 2:
            return row.get("rings", 0)
        if column == 3:
            return row.get("words", 0)
        if column == 4:
            return (
                translate_source("Серия")
                if row.get("scope") == ASSIGNMENT_SCOPE_EPISODE
                else translate_source("Глобально")
            )
        if column == 5:
            return self._actor_name(row.get("actor_id"))
        if column == 6:
            return "📺"
        return None

    def _actor_name(self, actor_id: Optional[str]) -> str:
        if not actor_id:
            return "-"
        return self.main_window.data.get("actors", {}).get(
            actor_id, {}
        ).get("name", "-")

    def _actor_tooltip(self, actor_id: Optional[str]) -> str:
        if not actor_id:
            return translate_source("Актёр не назначен")
        actor = self.main_window.data.get("actors", {}).get(actor_id, {})
        color = QColor(actor.get("color", ""))
        if color.isValid():
            return (
                f"{actor.get('name', actor_id)}\n"
                f"{translate_source('Цвет актёра:')} {color.name()}"
            )
        return actor.get("name", actor_id)

    def _actor_brush(self, actor_id: Optional[str]):
        if not actor_id:
            return None
        actor = self.main_window.data.get("actors", {}).get(actor_id, {})
        color = QColor(actor.get("color", ""))
        if not color.isValid():
            return None
        color.setAlpha(72)
        return QBrush(color)
