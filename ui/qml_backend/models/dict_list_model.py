"""Reusable dictionary-backed list model for QML."""

from typing import Any, Dict, List, Optional

from PySide6.QtCore import (
    QAbstractListModel,
    QByteArray,
    QModelIndex,
    QObject,
    Slot,
    Qt,
)


class DictListModel(QAbstractListModel):
    """Expose a list of dictionaries through explicitly declared QML roles."""

    def __init__(
        self,
        roles: Dict[str, int],
        parent: Optional[QObject] = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("backend")
        self._roles = roles
        self._rows: List[Dict[str, Any]] = []

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self._rows)

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole):
        if not index.isValid() or not 0 <= index.row() < len(self._rows):
            return None
        role_name = next(
            (name for name, value in self._roles.items() if value == role),
            None,
        )
        return self._rows[index.row()].get(role_name) if role_name else None

    def roleNames(self) -> Dict[int, QByteArray]:
        return {
            value: QByteArray(name.encode("utf-8"))
            for name, value in self._roles.items()
        }

    def set_rows(self, rows: List[Dict[str, Any]]) -> None:
        self.beginResetModel()
        self._rows = rows
        self.endResetModel()

    def rows(self) -> List[Dict[str, Any]]:
        return list(self._rows)

    @Slot(int, result="QVariantMap")
    def get(self, row: int) -> Dict[str, Any]:
        if 0 <= row < len(self._rows):
            return dict(self._rows[row])
        return {}
