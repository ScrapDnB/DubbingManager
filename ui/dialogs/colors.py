"""Prompter color settings dialog."""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QPushButton, QColorDialog, QLabel, QGridLayout
)
from PySide6.QtGui import QColor
from typing import Dict, Optional
from config.constants import MY_PALETTE


class PrompterColorDialog(QDialog):
    """Prompter Color Dialog dialog."""

    def __init__(
        self,
        current_colors: Dict[str, str],
        parent: Optional[QDialog] = None
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Настройка цветовой схемы телесуфлёра")
        self.resize(450, 400)
        self.colors: Dict[str, str] = current_colors.copy()

        self._btns: Dict[str, QPushButton]
        self._color_names: Dict[str, str]
        self._init_ui()

    def _init_ui(self) -> None:
        main_layout: QVBoxLayout = QVBoxLayout(self)
        form_layout: QFormLayout = QFormLayout()

        self._btns = {}
        self._color_names = {
            "bg": "Фоновый цвет сцены суфлёра",
            "active_text": "Цвет текста активной реплики",
            "inactive_text": "Цвет текста неактивной реплики",
            "tc": "Цвет таймкода внутри реплики",
            "actor": "Цвет имени актёра в реплике",
            "header_bg": "Фон верхней панели таймкода",
            "header_text": "Цвет цифр таймкода Reaper"
        }

        key: str
        display_name: str
        for key, display_name in self._color_names.items():
            btn: QPushButton = QPushButton()
            btn.setFixedSize(80, 25)
            btn.setStyleSheet(
                f"background-color: {self.colors[key]}; "
                "border: 1px solid #555; border-radius: 4px;"
            )
            btn.clicked.connect(
                lambda checked=False, k=key: self._pick_color_for(k)
            )
            self._btns[key] = btn
            form_layout.addRow(display_name, btn)

        main_layout.addLayout(form_layout)

        # Internal implementation detail
        dialog_buttons: QHBoxLayout = QHBoxLayout()
        btn_save = QPushButton("Сохранить цветовую схему")
        btn_save.clicked.connect(self.accept)
        btn_cancel = QPushButton("Отмена")
        btn_cancel.clicked.connect(self.reject)

        dialog_buttons.addWidget(btn_save)
        dialog_buttons.addWidget(btn_cancel)
        main_layout.addLayout(dialog_buttons)

    def _pick_color_for(self, key: str) -> None:
        initial: QColor = QColor(self.colors[key])
        new_color: QColor = QColorDialog.getColor(initial, self, "Выберите цвет")
        if new_color.isValid():
            hex_val: str = new_color.name()
            self.colors[key] = hex_val
            self._btns[key].setStyleSheet(
                f"background-color: {hex_val}; "
                "border: 1px solid #555; border-radius: 4px;"
            )

    def get_final_colors(self) -> Dict[str, str]:
        return self.colors


class CustomColorDialog(QDialog):
    """Custom Color Dialog dialog."""

    def __init__(self, parent: Optional[QDialog] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Выберите цвет")
        self.selected_color: Optional[str] = None

        self._init_ui()

    def _init_ui(self) -> None:
        layout: QVBoxLayout = QVBoxLayout(self)
        grid: QGridLayout = QGridLayout()

        r: int = 0
        c: int = 0
        color_hex: str
        for color_hex in MY_PALETTE:
            btn: QPushButton = QPushButton()
            btn.setFixedSize(35, 35)
            btn.setStyleSheet(
                f"background-color: {color_hex}; "
                "border-radius: 4px; border: 1px solid #999;"
            )
            btn.clicked.connect(
                lambda ch=False, clr=color_hex: self._select_color(clr)
            )
            grid.addWidget(btn, r, c)
            c += 1
            if c > 4:
                c = 0
                r += 1

        layout.addLayout(grid)

        btn_custom = QPushButton("Другой цвет...")
        btn_custom.clicked.connect(self._open_system_picker)
        layout.addWidget(btn_custom)

    def _select_color(self, clr: str) -> None:
        self.selected_color = clr
        self.accept()

    def _open_system_picker(self) -> None:
        color: QColor = QColorDialog.getColor()
        if color.isValid():
            self.selected_color = color.name()
            self.accept()