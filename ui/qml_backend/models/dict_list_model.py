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
        self._role_names = {value: name for name, value in roles.items()}
        self._identity_role = next(
            (
                name
                for name in ("id", "character", "episode", "name")
                if name in roles
            ),
            None,
        )
        self._rows: List[Dict[str, Any]] = []

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self._rows)

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole):
        if not index.isValid() or not 0 <= index.row() < len(self._rows):
            return None
        role_name = self._role_names.get(role)
        return self._rows[index.row()].get(role_name) if role_name else None

    def roleNames(self) -> Dict[int, QByteArray]:
        return {
            value: QByteArray(name.encode("utf-8"))
            for name, value in self._roles.items()
        }

    def set_rows(self, rows: List[Dict[str, Any]]) -> None:
        rows = list(rows)
        if rows == self._rows:
            return
        if self._can_update_in_place(rows):
            changed_rows = []
            changed_roles = set()
            for row, (old, new) in enumerate(zip(self._rows, rows)):
                if old == new:
                    continue
                changed_rows.append(row)
                changed_roles.update(
                    self._roles[name]
                    for name in self._roles
                    if old.get(name) != new.get(name)
                )
            self._rows = rows
            if changed_rows:
                self.dataChanged.emit(
                    self.index(changed_rows[0], 0),
                    self.index(changed_rows[-1], 0),
                    sorted(changed_roles),
                )
            return
        self.beginResetModel()
        self._rows = rows
        self.endResetModel()

    def _can_update_in_place(self, rows: List[Dict[str, Any]]) -> bool:
        if not self._identity_role or len(rows) != len(self._rows):
            return False
        return all(
            old.get(self._identity_role) == new.get(self._identity_role)
            for old, new in zip(self._rows, rows)
        )

    def update_rows(self, updates: Dict[int, Dict[str, Any]]) -> None:
        """Update selected rows without resetting the complete QML model."""
        changed_rows = []
        changed_roles = set()
        for row, values in updates.items():
            if not 0 <= row < len(self._rows):
                continue
            changed = False
            for name, value in values.items():
                if name not in self._roles or self._rows[row].get(name) == value:
                    continue
                self._rows[row][name] = value
                changed_roles.add(self._roles[name])
                changed = True
            if changed:
                changed_rows.append(row)
        if changed_rows:
            self.dataChanged.emit(
                self.index(min(changed_rows), 0),
                self.index(max(changed_rows), 0),
                sorted(changed_roles),
            )

    def rows(self) -> List[Dict[str, Any]]:
        return list(self._rows)

    @Slot(int, result="QVariantMap")
    def get(self, row: int) -> Dict[str, Any]:
        if 0 <= row < len(self._rows):
            return dict(self._rows[row])
        return {}
