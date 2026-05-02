"""Project health dialog."""

from typing import Any, Dict, List

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QDialog,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from services import ProjectHealthIssue, ProjectHealthService
from utils.i18n import translate_source, translate_widget_tree


class ProjectHealthDialog(QDialog):
    """Project Health Dialog dialog."""

    SEVERITY_LABELS = {
        ProjectHealthService.SEVERITY_ERROR: "Ошибка",
        ProjectHealthService.SEVERITY_WARNING: "Предупреждение",
        ProjectHealthService.SEVERITY_INFO: "Инфо",
    }

    SEVERITY_COLORS = {
        ProjectHealthService.SEVERITY_ERROR: QColor("#dc3545"),
        ProjectHealthService.SEVERITY_WARNING: QColor("#e0a800"),
        ProjectHealthService.SEVERITY_INFO: QColor("#0d6efd"),
    }

    def __init__(self, data: Dict[str, Any], parent=None):
        super().__init__(parent)
        self.data = data
        self.health_service = ProjectHealthService()
        self.issues: List[ProjectHealthIssue] = []

        self.setWindowTitle("Проверка проекта")
        self.resize(920, 560)

        self._init_ui()
        translate_widget_tree(self)
        self._refresh()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)

        title = QLabel("Проверка проекта")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title)

        self.lbl_summary = QLabel("")
        self.lbl_summary.setStyleSheet("color: #666;")
        layout.addWidget(self.lbl_summary)

        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels([
            "Уровень", "Серия", "Категория", "Сообщение", "Путь"
        ])
        self.table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeToContents
        )
        self.table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeToContents
        )
        self.table.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.ResizeToContents
        )
        self.table.horizontalHeader().setSectionResizeMode(
            3, QHeaderView.Stretch
        )
        self.table.horizontalHeader().setSectionResizeMode(
            4, QHeaderView.Stretch
        )
        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        layout.addWidget(self.table)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.btn_refresh = QPushButton("Обновить")
        self.btn_refresh.clicked.connect(self._refresh)
        btn_layout.addWidget(self.btn_refresh)

        self.btn_close = QPushButton("Закрыть")
        self.btn_close.clicked.connect(self.accept)
        btn_layout.addWidget(self.btn_close)

        layout.addLayout(btn_layout)

    def _refresh(self) -> None:
        self.issues = self.health_service.check_project(self.data)
        self._update_summary()
        self._populate_table()

    def _update_summary(self) -> None:
        summary = self.health_service.get_summary(self.issues)
        if summary["total"] == 0:
            self.lbl_summary.setText(translate_source("Проблем не найдено."))
            return

        self.lbl_summary.setText(
            f"{translate_source('Ошибки:')} {summary['errors']} | "
            f"{translate_source('Предупреждения:')} {summary['warnings']} | "
            f"{translate_source('Инфо:')} {summary['info']}"
        )

    def _populate_table(self) -> None:
        self.table.setRowCount(len(self.issues))

        for row, issue in enumerate(self.issues):
            values = [
                translate_source(
                    self.SEVERITY_LABELS.get(issue.severity, issue.severity)
                ),
                issue.episode or "",
                translate_source(issue.category),
                translate_source(issue.message),
                issue.path or "",
            ]

            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setToolTip(value)
                if column == 0:
                    color = self.SEVERITY_COLORS.get(issue.severity)
                    if color:
                        item.setForeground(color)
                if column in {0, 1, 2}:
                    item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(row, column, item)
