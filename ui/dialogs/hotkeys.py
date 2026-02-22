"""Диалог настройки горячих клавиш"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, 
    QGroupBox, QLabel, QPushButton, QKeySequenceEdit, 
    QMessageBox
)
from PySide6.QtGui import QKeySequence
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class HotkeySettingsDialog(QDialog):
    """Диалог настройки глобальных горячих клавиш"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Настройка горячих клавиш")
        self.resize(500, 400)
        self.main_app = parent
        
        self._init_ui()
    
    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        
        # Заголовок
        layout.addWidget(QLabel("<b>Глобальные горячие клавиши</b>"))
        
        # Проверка доступности pynput
        from services.hotkey_manager import PYNPUT_AVAILABLE
        if not PYNPUT_AVAILABLE:
            info_label = QLabel(
                "⚠️ Глобальные горячие клавиши недоступны на macOS "
                "из-за ограничений системы."
            )
            info_label.setStyleSheet(
                "color: #d9534f; font-weight: bold;"
            )
            info_label.setWordWrap(True)
            layout.addWidget(info_label)
            
            layout.addWidget(QLabel(
                "\nЛокальные горячие клавиши работают, когда окно активно:"
            ))
        
        # Секция телесуфлёра
        tp_group = QGroupBox("Телесуфлёр")
        tp_layout = QFormLayout(tp_group)
        
        prompter_cfg = self.main_app.data.get("prompter_config", {})
        
        self._tp_prev_edit = QKeySequenceEdit()
        self._tp_prev_edit.setKeySequence(
            QKeySequence(f"Ctrl+{prompter_cfg.get('key_prev', 'Left')}")
        )
        tp_layout.addRow("Назад:", self._tp_prev_edit)
        
        self._tp_next_edit = QKeySequenceEdit()
        self._tp_next_edit.setKeySequence(
            QKeySequence(f"Ctrl+{prompter_cfg.get('key_next', 'Right')}")
        )
        tp_layout.addRow("Вперёд:", self._tp_next_edit)
        
        layout.addWidget(tp_group)
        
        # Секция предпросмотра
        preview_group = QGroupBox("Монтажный лист (HtmlLivePreview)")
        preview_layout = QFormLayout(preview_group)
        
        self._preview_prev_edit = QKeySequenceEdit()
        self._preview_prev_edit.setKeySequence(QKeySequence("Alt+Left"))
        preview_layout.addRow("Назад:", self._preview_prev_edit)
        
        self._preview_next_edit = QKeySequenceEdit()
        self._preview_next_edit.setKeySequence(QKeySequence("Alt+Right"))
        preview_layout.addRow("Вперёд:", self._preview_next_edit)
        
        layout.addWidget(preview_group)
        
        # Информация
        info = QLabel(
            "\nПримечание: Глобальные горячие клавиши работают даже "
            "когда окно не в фокусе (только Windows/Linux)."
        )
        info.setWordWrap(True)
        info.setStyleSheet("color: #666; font-size: 11px;")
        layout.addWidget(info)
        
        # Кнопки
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        btn_reset = QPushButton("Сбросить")
        btn_reset.clicked.connect(self._reset_to_defaults)
        btn_layout.addWidget(btn_reset)
        
        btn_save = QPushButton("Сохранить")
        btn_save.clicked.connect(self._save_and_close)
        btn_layout.addWidget(btn_save)
        
        btn_cancel = QPushButton("Отмена")
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_cancel)
        
        layout.addLayout(btn_layout)
    
    def _reset_to_defaults(self) -> None:
        self._tp_prev_edit.setKeySequence(QKeySequence("Ctrl+Left"))
        self._tp_next_edit.setKeySequence(QKeySequence("Ctrl+Right"))
        self._preview_prev_edit.setKeySequence(QKeySequence("Alt+Left"))
        self._preview_next_edit.setKeySequence(QKeySequence("Alt+Right"))
    
    def _extract_key(self, seq: str) -> str:
        """Извлекает основную клавишу из строки комбинации"""
        parts = seq.split('+')
        return parts[-1] if parts else "Left"
    
    def _save_and_close(self) -> None:
        if "prompter_config" not in self.main_app.data:
            self.main_app.data["prompter_config"] = {}
        
        cfg = self.main_app.data["prompter_config"]
        
        seq_prev = self._tp_prev_edit.keySequence().toString()
        seq_next = self._tp_next_edit.keySequence().toString()
        
        cfg["key_prev"] = self._extract_key(seq_prev)
        cfg["key_next"] = self._extract_key(seq_next)
        
        self.main_app.set_dirty(True)
        
        # Перенастраиваем горячие клавиши если телесуфлёр открыт
        if (
            self.main_app.teleprompter_window and 
            hasattr(self.main_app.teleprompter_window, 'setup_global_hotkeys')
        ):
            self.main_app.teleprompter_window.setup_global_hotkeys()
        
        QMessageBox.information(
            self, "Готово", "Настройки горячих клавиш сохранены!"
        )
        self.accept()