"""Global search dialog."""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QFrame, QMessageBox, QLabel
)
from PySide6.QtCore import Qt
from typing import Dict, Any, Optional
from utils.helpers import format_seconds_to_tc


class GlobalSearchDialog(QDialog):
    """Global Search Dialog dialog."""

    def __init__(
        self,
        project_data: Dict[str, Any],
        parent: Optional[QDialog] = None
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Глобальный поиск по проекту")
        self.resize(900, 600)
        self.project_data: Dict[str, Any] = project_data
        self.main_app: Optional[Any] = parent

        self._search_input: QLineEdit
        self._table: QTableWidget
        self._init_ui()

    def _init_ui(self) -> None:
        layout: QVBoxLayout = QVBoxLayout(self)

        search_layout: QHBoxLayout = QHBoxLayout()
        self._search_input = QLineEdit()
        self._search_input.setPlaceholderText(
            "Введите текст или имя персонажа..."
        )
        self._search_input.returnPressed.connect(self._perform_search)

        btn_search = QPushButton("Найти")
        btn_search.clicked.connect(self._perform_search)

        search_layout.addWidget(QLabel("Поиск:"))
        search_layout.addWidget(self._search_input)
        search_layout.addWidget(btn_search)
        layout.addLayout(search_layout)

        self._table = QTableWidget(0, 4)
        self._table.setHorizontalHeaderLabels([
            "Серия", "Таймкод", "Персонаж", "Текст"
        ])
        self._customize_table()
        self._table.horizontalHeader().setSectionResizeMode(
            3, QHeaderView.Stretch
        )
        self._table.cellDoubleClicked.connect(self._go_to_result)
        layout.addWidget(self._table)

    def _customize_table(self) -> None:
        """Customize table."""
        self._table.setShowGrid(False)
        self._table.setAlternatingRowColors(True)
        self._table.setSelectionBehavior(
            QAbstractItemView.SelectRows
        )
        self._table.setSelectionMode(
            QAbstractItemView.ExtendedSelection
        )
        self._table.setFrameShape(QFrame.NoFrame)
        self._table.verticalHeader().setVisible(False)
        self._table.verticalHeader().setDefaultSectionSize(32)
        self._table.horizontalHeader().setHighlightSections(False)
        self._table.setStyleSheet(
            "QTableWidget::item { padding-left: 10px; }"
        )

    def _perform_search(self) -> None:
        """Perform search."""
        query: str = self._search_input.text().lower().strip()
        if not query:
            return

        self._table.setRowCount(0)
        episodes: Dict[str, str] = self.project_data.get("episodes", {})

        for ep_num in sorted(
            episodes.keys(),
            key=lambda x: int(x) if x.isdigit() else 0
        ):
            for line in self._get_episode_lines(ep_num):
                char_name = line.get("char", "")
                text_clean = line.get("text", "")

                if (
                    query in char_name.lower() or
                    query in text_clean.lower()
                ):
                    start_time = line.get("s_raw") or format_seconds_to_tc(
                        float(line.get("s", 0.0))
                    )
                    self._add_result_row(
                        ep_num, start_time, char_name, text_clean
                    )

        if self._table.rowCount() == 0:
            QMessageBox.information(
                self, "Поиск", "Ничего не найдено."
            )

    def _add_result_row(
        self,
        ep: str,
        time: str,
        char: str,
        text: str
    ) -> None:
        """Add result row."""
        row: int = self._table.rowCount()
        self._table.insertRow(row)

        item_ep: QTableWidgetItem = QTableWidgetItem(str(ep))
        item_ep.setData(Qt.UserRole, ep)
        self._table.setItem(row, 0, item_ep)
        self._table.setItem(row, 1, QTableWidgetItem(time))
        self._table.setItem(row, 2, QTableWidgetItem(char))
        self._table.setItem(row, 3, QTableWidgetItem(text))

    def _go_to_result(self, row: int, col: int) -> None:
        """Go to result."""
        ep_num: str = self._table.item(row, 0).data(Qt.UserRole)
        if self.main_app:
            self.main_app.switch_to_episode(ep_num)

    def _get_episode_lines(self, ep_num: str) -> list:
        """Return episode lines, loading them when needed."""
        if self.main_app and hasattr(self.main_app, "get_episode_lines"):
            return self.main_app.get_episode_lines(ep_num)

        return self.project_data.get("loaded_episodes", {}).get(ep_num, [])
