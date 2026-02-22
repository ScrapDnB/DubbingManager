"""Вспомогательные функции"""

import re
from typing import Optional
from PySide6.QtGui import QColor
import logging

logger = logging.getLogger(__name__)

# Import UI constants
try:
    from config.constants import TABLE_ROW_HEIGHT
except ImportError:
    TABLE_ROW_HEIGHT = 32  # Default fallback


def ass_time_to_seconds(time_str: str) -> float:
    """Конвертация ASS времени в секунды"""
    try:
        h, m, s = time_str.split(':')
        return int(h) * 3600 + int(m) * 60 + float(s)
    except (ValueError, AttributeError) as e:
        logger.warning(f"Invalid time format: {time_str}, error: {e}")
        return 0.0


def format_seconds_to_tc(seconds: float, round_flag: bool = False) -> str:
    """Форматирование секунд в таймкод"""
    s = int(round(seconds)) if round_flag else int(seconds)
    hours = s // 3600
    minutes = (s % 3600) // 60
    secs = s % 60
    return f"{hours}:{minutes:02d}:{secs:02d}"


def hex_to_rgba_string(hex_code: str, alpha: float) -> str:
    """Преобразует HEX цвет в строку rgba(r, g, b, a)"""
    color = QColor(hex_code)
    if not color.isValid():
        return f"rgba(255, 255, 255, {alpha})"
    return f"rgba({color.red()}, {color.green()}, {color.blue()}, {alpha})"


def customize_table(table) -> None:
    """Настройка нативного вида таблиц"""
    from PySide6.QtWidgets import QAbstractItemView, QFrame, QHeaderView

    table.setShowGrid(False)
    table.setAlternatingRowColors(True)
    table.setSelectionBehavior(QAbstractItemView.SelectRows)
    table.setSelectionMode(QAbstractItemView.ExtendedSelection)
    table.setFrameShape(QFrame.NoFrame)
    table.verticalHeader().setVisible(False)
    table.verticalHeader().setDefaultSectionSize(TABLE_ROW_HEIGHT)
    table.horizontalHeader().setHighlightSections(False)
    table.setStyleSheet("QTableWidget::item { padding-left: 10px; }")


def wrap_widget(widget) -> 'QWidget':
    """Обертка для центрирования кнопок в таблице"""
    from PySide6.QtWidgets import QWidget, QHBoxLayout
    from PySide6.QtCore import Qt
    
    container = QWidget()
    layout = QHBoxLayout(container)
    layout.addWidget(widget)
    layout.setContentsMargins(4, 2, 4, 2)
    layout.setAlignment(Qt.AlignCenter)
    container.setLayout(layout)
    return container


def split_merged_text(text: str, ids: list) -> list:
    """
    Разделяет объединённый текст по семантическим разделителям
    """
    if not text or len(ids) < 2:
        return []
    
    parts = []
    
    # Сначала пробуем ' // '
    if ' // ' in text:
        parts = [p.strip() for p in text.split(' // ') if p.strip()]
    # Затем пробуем ' / '
    elif ' / ' in text:
        parts = [p.strip() for p in text.split(' / ') if p.strip()]
    
    # Возвращаем только если получили нужное количество частей
    if len(parts) == len(ids):
        return parts
    
    return []