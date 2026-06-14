"""Actor summary dialog."""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QFrame, QPushButton, QFileDialog,
    QMessageBox, QHBoxLayout, QInputDialog
)
from PySide6.QtGui import QColor
from typing import Dict, Any, Optional, List
from services import CharacterStatsService, ExportService
from services.assignment_service import get_actor_for_character
from utils.i18n import translate_source, translate_widget_tree

PROJECT_EXPORT_METRIC_LABELS = {
    "rings": "Кольца",
    "lines": "Строчки",
    "words": "Слова",
}
PROJECT_EXPORT_METRIC_BY_LABEL = {
    label: metric for metric, label in PROJECT_EXPORT_METRIC_LABELS.items()
}


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
        target = (
            f"{translate_source('Серия')} {target_ep}"
            if target_ep
            else translate_source("Проект")
        )
        self.setWindowTitle(f"{translate_source('Отчет:')} {target}")
        self.resize(1000, 700)
        self.data: Dict[str, Any] = data
        self.main_app = parent

        self._table: QTableWidget
        self._init_ui()
        translate_widget_tree(self)

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

        buttons_layout = QHBoxLayout()
        if not self.target_ep:
            btn_export_xlsx = QPushButton("Экспорт для Google Sheets")
            btn_export_xlsx.clicked.connect(self._export_project_xlsx)
            buttons_layout.addWidget(btn_export_xlsx)
        buttons_layout.addStretch()

        btn_close = QPushButton("Закрыть")
        btn_close.clicked.connect(self.accept)
        buttons_layout.addWidget(btn_close)
        layout.addLayout(buttons_layout)

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

            name_item = QTableWidgetItem(translate_source("НЕ РАСПРЕДЕЛЕНЫ"))
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

    def _export_project_xlsx(self) -> None:
        """Export formatted project casting summary to XLSX."""
        metric = self._choose_project_export_metric()
        if not metric:
            return
        self._save_project_export_metric(metric)

        project_name = self.data.get("project_name", "project")
        default_name = f"{project_name}.xlsx"
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Сохранить XLSX",
            default_name,
            "Excel (*.xlsx)"
        )
        if not path:
            return

        try:
            service = CharacterStatsService(self.data)
            workbook = service.create_project_casting_xlsx(
                self._get_episode_lines,
                metric=metric,
            )
            workbook.save(path)
        except ImportError as exc:
            QMessageBox.warning(self, "Экспорт XLSX", str(exc))
            return

        QMessageBox.information(
            self,
            "Экспорт XLSX",
            f"XLSX сохранён: {path}"
        )

    def _choose_project_export_metric(self) -> Optional[str]:
        """Ask which metric should be exported to the spreadsheet."""
        labels = list(PROJECT_EXPORT_METRIC_LABELS.values())
        current_metric = self._get_project_export_metric()
        current_label = PROJECT_EXPORT_METRIC_LABELS.get(
            current_metric,
            PROJECT_EXPORT_METRIC_LABELS["rings"],
        )
        current_index = labels.index(current_label)
        label, accepted = QInputDialog.getItem(
            self,
            "Экспорт для Google Sheets",
            "Что считать:",
            labels,
            current_index,
            False,
        )
        if not accepted:
            return None
        return PROJECT_EXPORT_METRIC_BY_LABEL.get(label, "rings")

    def _get_project_export_metric(self) -> str:
        """Return the last selected project spreadsheet export metric."""
        settings_service = getattr(
            self.main_app,
            "global_settings_service",
            None
        )
        if (
            settings_service and
            hasattr(settings_service, "get_project_summary_export_metric")
        ):
            return settings_service.get_project_summary_export_metric()
        return self.data.get("_project_summary_export_metric", "rings")

    def _save_project_export_metric(self, metric: str) -> None:
        """Persist the selected project spreadsheet export metric."""
        settings_service = getattr(
            self.main_app,
            "global_settings_service",
            None
        )
        if (
            settings_service and
            hasattr(settings_service, "set_project_summary_export_metric")
        ):
            settings_service.set_project_summary_export_metric(metric)
            settings = settings_service.get_settings()
            settings["project_summary_export_metric"] = metric
            settings_service.save_settings(settings)
            if hasattr(self.main_app, "global_settings"):
                self.main_app.global_settings = settings_service.get_settings()
            return
        self.data["_project_summary_export_metric"] = metric
