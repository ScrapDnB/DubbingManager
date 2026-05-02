"""Actor summary dialog."""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QFrame, QPushButton, QLabel
)
from PySide6.QtGui import QColor
from typing import Dict, Any, Optional, List
from services import ExportService
from services.assignment_service import get_actor_for_character


class SummaryDialog(QDialog):
    """Summary Dialog dialog."""

    def __init__(
        self,
        data: Dict[str, Any],
        target_ep: Optional[str] = None,
        parent: Optional[QDialog] = None
    ) -> None:
        super().__init__(parent)
        self.target_ep: Optional[str] = target_ep
        self.setWindowTitle(
            f"Отчет: {'Серия ' + target_ep if target_ep else 'Проект'}"
        )
        self.resize(1000, 700)
        self.data: Dict[str, Any] = data
        self.main_app = parent

        self._table: QTableWidget
        self._init_ui()

    def _init_ui(self) -> None:
        layout: QVBoxLayout = QVBoxLayout(self)

        self._table = QTableWidget(0, 5)
        self._table.setHorizontalHeaderLabels([
            "Актер", "Цвет", "Колец", "Слов", "Персонажи"
        ])
        self._customize_table()
        self._table.horizontalHeader().setSectionResizeMode(
            4, QHeaderView.Stretch
        )
        self._table.verticalHeader().setSectionResizeMode(
            QHeaderView.ResizeToContents
        )
        layout.addWidget(self._table)

        self._calculate_stats()

        btn_close = QPushButton("Закрыть")
        btn_close.clicked.connect(self.accept)
        layout.addWidget(btn_close)

    def _customize_table(self) -> None:
        """Customize table."""
        self._table.setShowGrid(False)
        self._table.setAlternatingRowColors(True)
        self._table.setSelectionBehavior(
            QAbstractItemView.SelectRows
        )
        self._table.setFrameShape(QFrame.NoFrame)
        self._table.verticalHeader().setVisible(False)
        self._table.horizontalHeader().setHighlightSections(False)
        self._table.setStyleSheet(
            "QTableWidget::item { padding-left: 10px; }"
        )

    def _calculate_stats(self) -> None:
        """Calculate stats."""
        stats: Dict[str, Dict[str, Any]] = {
            aid: {"rings": 0, "words": 0, "roles": set()}
            for aid in self.data["actors"]
        }
        unassigned: Dict[str, Any] = {"rings": 0, "words": 0, "roles": set()}

        if self.target_ep:
            ep_nums = [self.target_ep]
        else:
            ep_nums = list(self.data.get("episodes", {}).keys())

        ep_num: str
        export_service = ExportService(self.data)
        for ep_num in ep_nums:
            lines = self._get_episode_lines(ep_num)

            if not lines:
                continue

            merged = export_service.process_merge_logic(
                lines,
                self.data.get("replica_merge_config", {})
            )

            line: Dict[str, Any]
            for line in merged:
                aid: Optional[str] = get_actor_for_character(
                    self.data, line['char'], ep_num
                )
                target = (
                    stats[aid]
                    if aid and aid in stats
                    else unassigned
                )
                target["rings"] += 1
                target["words"] += len(line['text'].split())
                target["roles"].add(line['char'])

        aid: str
        stat: Dict[str, Any]
        for aid, stat in stats.items():
            if stat["rings"] == 0 and self.target_ep:
                continue

            row: int = self._table.rowCount()
            self._table.insertRow(row)

            info = self.data["actors"][aid]
            self._table.setItem(
                row, 0, QTableWidgetItem(info["name"])
            )

            color_item = QTableWidgetItem()
            color_item.setBackground(QColor(info["color"]))
            self._table.setItem(row, 1, color_item)

            self._table.setItem(
                row, 2, QTableWidgetItem(str(stat["rings"]))
            )
            self._table.setItem(
                row, 3, QTableWidgetItem(str(stat["words"]))
            )

            roles_text: str = "\n".join([
                f"• {r}" for r in sorted(list(stat["roles"]))
            ])
            self._table.setItem(row, 4, QTableWidgetItem(roles_text))

        if unassigned["roles"]:
            row: int = self._table.rowCount()
            self._table.insertRow(row)

            name_item = QTableWidgetItem("НЕ РАСПРЕДЕЛЕНЫ")
            name_item.setForeground(QColor("red"))
            self._table.setItem(row, 0, name_item)
            self._table.setItem(
                row, 2, QTableWidgetItem(str(unassigned["rings"]))
            )
            self._table.setItem(
                row, 3, QTableWidgetItem(str(unassigned["words"]))
            )
            self._table.setItem(
                row, 4,
                QTableWidgetItem(", ".join(sorted(list(unassigned["roles"]))))
            )

    def _get_episode_lines(self, ep_num: str) -> List[Dict[str, Any]]:
        """Return episode lines, loading them when needed."""
        if self.main_app and hasattr(self.main_app, "get_episode_lines"):
            return self.main_app.get_episode_lines(ep_num)

        return self.data.get("loaded_episodes", {}).get(ep_num, [])
