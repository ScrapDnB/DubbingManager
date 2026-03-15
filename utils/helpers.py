"""Вспомогательные функции"""

import re
import subprocess
import traceback
from pathlib import Path
from typing import Optional
from PySide6.QtGui import QColor
import logging
import json

logger = logging.getLogger(__name__)

# Import UI constants
try:
    from config.constants import TABLE_ROW_HEIGHT, FPS
except ImportError:
    TABLE_ROW_HEIGHT = 32  # Default fallback
    FPS = 25  # Default fallback


def log_exception(logger_obj: logging.Logger, message: str, exc: Exception) -> None:
    """
    Логирование исключения с полным traceback

    Args:
        logger_obj: логгер для записи
        message: сообщение перед traceback
        exc: исключение
    """
    tb = traceback.format_exc()
    logger_obj.error(f"{message}: {exc}\n{tb}")


def ass_time_to_seconds(time_str: str) -> float:
    """Конвертация ASS времени в секунды"""
    try:
        h, m, s = time_str.split(':')
        return int(h) * 3600 + int(m) * 60 + float(s)
    except (ValueError, AttributeError) as e:
        logger.warning(f"Invalid time format: {time_str}, error: {e}")
        return 0.0


def srt_time_to_seconds(time_str: str) -> float:
    """Конвертация SRT времени в секунды (формат: HH:MM:SS,mmm)"""
    try:
        # SRT format: 00:00:01,000
        main_part = time_str.replace(',', '.')
        h, m, s = main_part.split(':')
        return int(h) * 3600 + int(m) * 60 + float(s)
    except (ValueError, AttributeError) as e:
        logger.warning(f"Invalid SRT time format: {time_str}, error: {e}")
        return 0.0


def format_seconds_to_tc(seconds: float, round_flag: bool = False) -> str:
    """Форматирование секунд в таймкод"""
    s = int(round(seconds)) if round_flag else int(seconds)
    hours = s // 3600
    minutes = (s % 3600) // 60
    secs = s % 60
    return f"{hours}:{minutes:02d}:{secs:02d}"


def format_seconds_to_full_tc(seconds: float) -> str:
    """Форматирование секунд в полный таймкод HH:MM:SS,mmm"""
    total_ms = int(round(seconds * 1000))
    hours = total_ms // 3600000
    minutes = (total_ms % 3600000) // 60000
    seconds_part = (total_ms % 60000) // 1000
    milliseconds = total_ms % 1000
    return f"{hours}:{minutes:02d}:{seconds_part:02d},{milliseconds:03d}"


def format_timing_range(start_seconds: float, end_seconds: float) -> str:
    """Форматирование диапазона таймингов HH:MM:SS,mmm-HH:MM:SS,mmm"""
    start_tc = format_seconds_to_full_tc(start_seconds)
    end_tc = format_seconds_to_full_tc(end_seconds)
    return f"{start_tc}-{end_tc}"


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


def get_video_fps(video_path: str) -> float:
    """
    Извлечение FPS из видеофайла через ffprobe

    Args:
        video_path: путь к видеофайлу

    Returns:
        FPS видео или 25.0 по умолчанию при ошибке
    """
    # Валидация пути: запрещаем path traversal
    if '..' in video_path:
        logger.warning(f"Invalid video path (path traversal detected): {video_path}")
        return FPS

    try:
        path = Path(video_path).resolve()
        
        # Проверка существования файла
        if not path.exists() or not path.is_file():
            logger.warning(f"Video file not found: {video_path}")
            return FPS

        cmd = [
            'ffprobe',
            '-v', 'quiet',
            '-print_format', 'json',
            '-show_streams',
            str(path)
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)

        if result.returncode != 0:
            logger.warning(f"ffprobe failed for {video_path}")
            return FPS

        data = json.loads(result.stdout)

        # Ищем видеопоток
        for stream in data.get('streams', []):
            if stream.get('codec_type') == 'video':
                # Пробуем получить avg_frame_rate
                avg_frame_rate = stream.get('avg_frame_rate')
                if avg_frame_rate:
                    num, den = avg_frame_rate.split('/')
                    if den and int(den) != 0:
                        return float(num) / float(den)

                # Если нет, пробуем r_frame_rate
                r_frame_rate = stream.get('r_frame_rate')
                if r_frame_rate:
                    num, den = r_frame_rate.split('/')
                    if den and int(den) != 0:
                        return float(num) / float(den)

                # Если нет, пробуем nb_frames и duration
                avg_fps = stream.get('avg_frame_rate')
                if avg_fps:
                    return float(avg_fps)

        logger.warning(f"Could not find video stream in {video_path}")
        return FPS

    except FileNotFoundError:
        logger.warning(f"ffprobe not found in PATH for {video_path}")
        return FPS
    except (subprocess.TimeoutExpired, subprocess.SubprocessError) as e:
        logger.warning(f"Error getting FPS from {video_path}: {e}")
        return FPS
    except (json.JSONDecodeError, KeyError, ValueError, ZeroDivisionError) as e:
        logger.warning(f"Error parsing ffprobe output for {video_path}: {e}")
        return FPS
    except Exception as e:
        logger.warning(f"Unexpected error getting FPS from {video_path}: {e}")
        return FPS