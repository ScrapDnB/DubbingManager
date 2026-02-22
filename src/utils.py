"""Utility functions and constants for Dubbing Manager"""

import sys
import platform
import json
import re
import os
import math
from datetime import datetime
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout,
    QHBoxLayout, QPushButton, QFileDialog, QTableWidget,
    QTableWidgetItem, QColorDialog, QComboBox, QLabel,
    QHeaderView, QInputDialog, QFrame, QSpinBox, QLineEdit,
    QDialog, QListWidget, QListWidgetItem, QCheckBox, QGroupBox, QFormLayout,
    QMessageBox, QSlider, QAbstractItemView, QStackedWidget,
    QDoubleSpinBox, QRadioButton, QGridLayout, QScrollArea,
    QGraphicsView, QGraphicsScene, QGraphicsTextItem,
    QSplitter, QSizePolicy, QToolBar, QKeySequenceEdit, QDialogButtonBox, QTextEdit
)
from PySide6.QtGui import (
    QColor, QFont, QPainter, QAction, QKeySequence, QPen, QBrush
)
from PySide6.QtCore import (
    Qt, QUrl, QTimer, QThread, Signal, QRectF, QEvent, Slot, QObject
)

# --- CONSTANTS ---
MY_PALETTE = [
    "#D9775F", "#E46C0A", "#9B5333", "#C0504D", "#C4BD97",
    "#D4A017", "#938953", "#8A7F80", "#76923C", "#4F6228",
    "#31859B", "#669999", "#4F81BD", "#5B9BD5", "#2C4D75",
    "#708090", "#B65C72", "#8064A2", "#5F497A", "#7B3F61"
]

# --- UTILITY FUNCTIONS ---

def customize_table(table):
    """Настройка нативного вида таблиц"""
    table.setShowGrid(False)
    table.setAlternatingRowColors(True)
    table.setSelectionBehavior(QAbstractItemView.SelectRows)
    table.setSelectionMode(QAbstractItemView.ExtendedSelection)
    table.setFrameShape(QFrame.NoFrame)
    table.verticalHeader().setVisible(False)
    table.verticalHeader().setDefaultSectionSize(32)
    table.horizontalHeader().setHighlightSections(False)
    table.setStyleSheet("QTableWidget::item { padding-left: 10px; }")

def wrap_widget(widget):
    """Обертка для центрирования кнопок в таблице"""
    container = QWidget()
    layout = QHBoxLayout(container)
    layout.addWidget(widget)
    layout.setContentsMargins(4, 2, 4, 2)
    layout.setAlignment(Qt.AlignCenter)
    container.setLayout(layout)
    return container

def ass_time_to_seconds(time_str):
    try:
        h, m, s = time_str.split(':')
        return int(h) * 3600 + int(m) * 60 + float(s)
    except:
        return 0.0

def format_seconds_to_tc(seconds, round_flag=False):
    s = int(round(seconds)) if round_flag else int(seconds)
    hours = s // 3600
    minutes = (s % 3600) // 60
    secs = s % 60
    return f"{hours}:{minutes:02d}:{secs:02d}"

def hex_to_rgba_string(hex_code, alpha):
    """Преобразует HEX цвет в строку rgba(r, g, b, a)"""
    color = QColor(hex_code)
    if not color.isValid():
        return f"rgba(255, 255, 255, {alpha})"
    return f"rgba({color.red()}, {color.green()}, {color.blue()}, {alpha})"

class CollapsibleSection(QFrame):
    """Сворачиваемый раздел настроек с кнопкой-стрелкой"""
    def __init__(self, title, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.StyledPanel)
        self.setStyleSheet("CollapsibleSection { background: #2b2b2b; border-radius: 4px; }")
        
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        
        # Заголовок с кнопкой
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(8, 6, 8, 6)
        
        self.toggle_btn = QPushButton()
        self.toggle_btn.setFixedSize(20, 20)
        self.toggle_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                color: #aaa;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover { color: white; }
        """)
        self.toggle_btn.clicked.connect(self.toggle)
        header_layout.addWidget(self.toggle_btn)
        
        title_label = QLabel(title)
        title_label.setStyleSheet("color: white; font-weight: bold; font-size: 13px;")
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        
        self.header_widget = QWidget()
        self.header_widget.setLayout(header_layout)
        self.header_widget.setStyleSheet("background: transparent;")
        self.main_layout.addWidget(self.header_widget)
        
        # Контент
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(8, 0, 8, 8)
        self.content_layout.setSpacing(4)
        self.main_layout.addWidget(self.content_widget)
        
        # По умолчанию свёрнут
        self.expanded = False
        self.content_widget.setVisible(False)
        self.update_arrow()
    
    def update_arrow(self):
        if self.expanded:
            self.toggle_btn.setText("▼")
        else:
            self.toggle_btn.setText("▶")
            self.toggle_btn.setStyleSheet("""
                QPushButton {
                    background: transparent;
                    border: none;
                    color: #666;
                    font-size: 14px;
                    font-weight: bold;
                }
                QPushButton:hover { color: #888; }
            """)
    
    def toggle(self):
        self.expanded = not self.expanded
        self.content_widget.setVisible(self.expanded)
        self.update_arrow()
    
    def addWidget(self, widget):
        self.content_layout.addWidget(widget)
    
    def addLayout(self, layout):
        self.content_layout.addLayout(layout)