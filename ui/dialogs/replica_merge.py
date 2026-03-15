"""Диалог настроек объединения реплик"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QGroupBox,
    QCheckBox, QSpinBox, QDoubleSpinBox, QPushButton,
    QLabel, QHBoxLayout
)
from typing import Dict, Any, Optional
from PySide6.QtCore import Qt


class ReplicaMergeSettingsDialog(QDialog):
    """Диалог настройки параметров объединения реплик"""

    def __init__(
        self,
        current_settings: Dict[str, Any],
        parent: Optional[QDialog] = None
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Настройки объединения реплик")
        self.settings: Dict[str, Any] = current_settings.copy()

        self._merge_enabled: QCheckBox
        self._merge_gap: QDoubleSpinBox
        self._p_short: QDoubleSpinBox
        self._p_long: QDoubleSpinBox
        self._fps: QDoubleSpinBox

        self._init_ui()

    def _init_ui(self) -> None:
        layout: QVBoxLayout = QVBoxLayout(self)

        # Описание
        info_label = QLabel(
            "Эти настройки используются для:\n"
            "• Монтажного листа\n"
            "• Телесуфлёра\n"
            "• Экспорта (HTML, Excel)\n"
            "• Подсчёта колец в отчётах"
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #888; padding: 8px;")
        layout.addWidget(info_label)

        # Параметры слияния
        merge_group = QGroupBox("Параметры объединения реплик")
        merge_layout: QFormLayout = QFormLayout(merge_group)

        self._merge_enabled = QCheckBox("Включить объединение реплик")
        self._merge_enabled.setChecked(self.settings.get('merge', True))
        merge_layout.addRow(self._merge_enabled)

        self._fps = QDoubleSpinBox()
        self._fps.setRange(1.0, 120.0)
        self._fps.setSingleStep(0.001)
        self._fps.setValue(self.settings.get('fps', 25.0))
        self._fps.setToolTip(
            "Частота кадров видео (FPS). Используется для расчёта времени\n"
            "при объединении реплик (merge_gap указывается в кадрах)."
        )
        merge_layout.addRow("FPS:", self._fps)

        fps = self.settings.get('fps', 25.0)
        self._merge_gap = QDoubleSpinBox()
        self._merge_gap.setRange(0.0, 10.0)
        self._merge_gap.setSingleStep(0.1)
        self._merge_gap.setValue(self.settings.get('merge_gap', 5) / fps)  # Конвертируем кадры в секунды
        self._merge_gap.setToolTip(
            "Максимальный промежуток между репликами (в секундах),\n"
            "при котором они могут быть объединены"
        )
        merge_layout.addRow("Порог слияния (сек):", self._merge_gap)

        self._p_short = QDoubleSpinBox()
        self._p_short.setRange(0.0, 5.0)
        self._p_short.setSingleStep(0.1)
        self._p_short.setValue(self.settings.get('p_short', 0.5))
        self._p_short.setToolTip(
            "Если пауза между репликами >= этому значению (сек),\n"
            "используется разделитель ' / '"
        )
        merge_layout.addRow("Пауза для '/' (сек):", self._p_short)

        self._p_long = QDoubleSpinBox()
        self._p_long.setRange(0.0, 10.0)
        self._p_long.setSingleStep(0.1)
        self._p_long.setValue(self.settings.get('p_long', 2.0))
        self._p_long.setToolTip(
            "Если пауза между репликами >= этому значению (сек),\n"
            "используется разделитель ' // '"
        )
        merge_layout.addRow("Пауза для '//' (сек):", self._p_long)

        layout.addWidget(merge_group)

        # Пояснение
        explanation = QLabel(
            "<b>Как это работает:</b><br>"
            "1. Реплики одного персонажа объединяются, если пауза между ними "
            "< порога слияния<br>"
            "2. При объединении добавляется разделитель:<br>"
            "   • Нет разделителя — пауза < 0.5 сек<br>"
            "   • ' / ' — пауза 0.5–2.0 сек<br>"
            "   • ' // ' — пауза > 2.0 сек"
        )
        explanation.setWordWrap(True)
        explanation.setStyleSheet(
            "padding: 8px; background: #333; color: #fff; "
            "border-radius: 4px; border-left: 4px solid #5B9BD5;"
        )
        layout.addWidget(explanation)

        # Кнопки
        btn_layout: QHBoxLayout = QHBoxLayout()
        btn_layout.addStretch()

        btn_cancel = QPushButton("Отмена")
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_cancel)

        btn_ok = QPushButton("Сохранить")
        btn_ok.clicked.connect(self.accept)
        btn_ok.setStyleSheet("font-weight: bold;")
        btn_layout.addWidget(btn_ok)

        layout.addLayout(btn_layout)

    def get_settings(self) -> Dict[str, Any]:
        """Возвращает обновлённые настройки"""
        fps = self._fps.value()
        # Конвертируем секунды обратно в кадры
        merge_gap_frames = int(self._merge_gap.value() * fps)
        return {
            'merge': self._merge_enabled.isChecked(),
            'merge_gap': merge_gap_frames,
            'fps': fps,
            'p_short': self._p_short.value(),
            'p_long': self._p_long.value(),
        }
