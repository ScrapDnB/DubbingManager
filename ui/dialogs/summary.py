"""Диалог сводного отчёта"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QTableWidget, QTableWidgetItem, 
    QHeaderView, QAbstractItemView, QFrame, QPushButton, QLabel
)
from PySide6.QtGui import QColor
from typing import Dict, Any, Optional, Set
import os
import re
from utils.helpers import ass_time_to_seconds


class SummaryDialog(QDialog):
    """Диалог отображения сводной статистики"""
    
    def __init__(
        self, 
        data: Dict[str, Any], 
        target_ep: Optional[str] = None,
        parent=None
    ):
        super().__init__(parent)
        self.target_ep = target_ep
        self.setWindowTitle(
            f"Отчет: {'Серия ' + target_ep if target_ep else 'Проект'}"
        )
        self.resize(1000, 700)
        self.data = data
        
        self._init_ui()
    
    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        
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
        """Настройка вида таблицы"""
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
        """Расчёт статистики по актёрам"""
        gap = self.data["export_config"].get('merge_gap', 5)
        
        stats = {
            aid: {"rings": 0, "words": 0, "roles": set()} 
            for aid in self.data["actors"]
        }
        unassigned = {"rings": 0, "words": 0, "roles": set()}
        
        if self.target_ep:
            eps = {self.target_ep: self.data["episodes"][self.target_ep]}
        else:
            eps = self.data["episodes"]
        
        for ep_num, path in eps.items():
            if not os.path.exists(path):
                continue
            
            lines = []
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    for line in f:
                        if line.startswith("Dialogue:"):
                            parts = line.split(',', 9)
                            text = re.sub(
                                r'\{.*?\}', '', parts[9]
                            ).strip()
                            if text:
                                lines.append({
                                    's': ass_time_to_seconds(parts[1]),
                                    'e': ass_time_to_seconds(parts[2]),
                                    'char': parts[4].strip(),
                                    'text': text
                                })
            except Exception:
                continue
            
            if not lines:
                continue
            
            # Слияние реплик
            merged = []
            curr = lines[0].copy()
            for i in range(1, len(lines)):
                nxt = lines[i]
                if (
                    nxt['char'] == curr['char'] and 
                    (nxt['s'] - curr['e']) < gap
                ):
                    curr['text'] += "  " + nxt['text']
                    curr['e'] = nxt['e']
                else:
                    merged.append(curr)
                    curr = nxt.copy()
            merged.append(curr)
            
            # Подсчёт статистики
            for line in merged:
                aid = self.data["global_map"].get(line['char'])
                target = (
                    stats[aid] 
                    if aid and aid in stats 
                    else unassigned
                )
                target["rings"] += 1
                target["words"] += len(line['text'].split())
                target["roles"].add(line['char'])
        
        # Заполнение таблицы
        for aid, stat in stats.items():
            if stat["rings"] == 0 and self.target_ep:
                continue
            
            row = self._table.rowCount()
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
            
            roles_text = "\n".join([
                f"• {r}" for r in sorted(list(stat["roles"]))
            ])
            self._table.setItem(row, 4, QTableWidgetItem(roles_text))
        
        # Нераспределённые персонажи
        if unassigned["roles"]:
            row = self._table.rowCount()
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