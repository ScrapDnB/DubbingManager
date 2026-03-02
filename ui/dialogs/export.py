"""Диалог настроек экспорта"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QGroupBox,
    QComboBox, QCheckBox, QSpinBox, QDoubleSpinBox,
    QPushButton, QMessageBox, QLabel
)
from typing import Dict, Any, Optional, List


class ExportSettingsDialog(QDialog):
    """Диалог настройки параметров экспорта"""

    def __init__(
        self,
        current_settings: Dict[str, Any],
        parent: Optional[QDialog] = None
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Настройки монтажного листа")
        self.settings: Dict[str, Any] = current_settings.copy()
        self.parent_app: Optional[Any] = parent
        self.highlight_ids_export: Optional[List[str]] = self.settings.get(
            'highlight_ids_export'
        )

        self._layout_type: QComboBox
        self._col_tc: QCheckBox
        self._col_char: QCheckBox
        self._col_actor: QCheckBox
        self._col_text: QCheckBox
        self._f_time: QSpinBox
        self._f_char: QSpinBox
        self._f_actor: QSpinBox
        self._f_text: QSpinBox
        self._use_color: QCheckBox
        self._allow_edit: QCheckBox
        self._round_time: QCheckBox
        self._open_auto: QCheckBox
        self._init_ui()

    def _init_ui(self) -> None:
        layout: QVBoxLayout = QVBoxLayout(self)
        form: QFormLayout = QFormLayout()

        # Тип разметки
        self._layout_type = QComboBox()
        self._layout_type.addItems(["Таблица", "Сценарий"])
        self._layout_type.setCurrentText(
            self.settings.get('layout_type', "Таблица")
        )
        form.addRow("Тип разметки:", self._layout_type)
        layout.addLayout(form)

        # Элементы в листе
        col_group = QGroupBox("Элементы в листе")
        col_layout: QVBoxLayout = QVBoxLayout(col_group)

        self._col_tc = QCheckBox("Таймкоды")
        self._col_tc.setChecked(self.settings.get('col_tc', True))
        self._col_char = QCheckBox("Имя персонажа")
        self._col_char.setChecked(self.settings.get('col_char', True))
        self._col_actor = QCheckBox("Имя актера")
        self._col_actor.setChecked(self.settings.get('col_actor', True))
        self._col_text = QCheckBox("Текст реплики")
        self._col_text.setChecked(self.settings.get('col_text', True))

        cb: QCheckBox
        for cb in [
            self._col_tc, self._col_char,
            self._col_actor, self._col_text
        ]:
            col_layout.addWidget(cb)

        layout.addWidget(col_group)

        # Размеры шрифтов
        font_group = QGroupBox("Размеры шрифтов (px)")
        font_layout: QFormLayout = QFormLayout(font_group)

        self._f_time = QSpinBox()
        self._f_time.setRange(6, 72)
        self._f_time.setValue(self.settings.get('f_time', 12))

        self._f_char = QSpinBox()
        self._f_char.setRange(6, 72)
        self._f_char.setValue(self.settings.get('f_char', 14))

        self._f_actor = QSpinBox()
        self._f_actor.setRange(6, 72)
        self._f_actor.setValue(self.settings.get('f_actor', 14))

        self._f_text = QSpinBox()
        self._f_text.setRange(6, 72)
        self._f_text.setValue(self.settings.get('f_text', 16))

        font_layout.addRow("Таймкод:", self._f_time)
        font_layout.addRow("Персонаж:", self._f_char)
        font_layout.addRow("Актер:", self._f_actor)
        font_layout.addRow("Текст:", self._f_text)
        layout.addWidget(font_group)

        # Пояснение об объединении реплик
        merge_info = QLabel(
            "⚙ Параметры объединения реплик настраиваются отдельно.\n"
            "Они используются в монтажном листе, телесуфлёре и отчётах."
        )
        merge_info.setStyleSheet("color: #666; padding: 8px; background: #f5f5f5; border-radius: 4px;")
        merge_info.setWordWrap(True)
        layout.addWidget(merge_info)

        # Цвета и актёры
        color_group = QGroupBox("Отображение цветов")
        color_layout: QVBoxLayout = QVBoxLayout(color_group)

        self._use_color = QCheckBox("Использовать цвета актёров")
        self._use_color.setChecked(self.settings.get('use_color', True))
        color_layout.addWidget(self._use_color)

        btn_filter = QPushButton("Выбрать актёров для подсветки...")
        btn_filter.clicked.connect(self._open_actor_filter)
        color_layout.addWidget(btn_filter)
        layout.addWidget(color_group)

        # Редактирование
        edit_group = QGroupBox("Редактирование в экспорте")
        edit_layout: QVBoxLayout = QVBoxLayout(edit_group)
        self._allow_edit = QCheckBox("Разрешить редактирование текста")
        self._allow_edit.setChecked(self.settings.get('allow_edit', True))
        edit_layout.addWidget(self._allow_edit)
        layout.addWidget(edit_group)

        # Дополнительные опции
        self._round_time = QCheckBox("Округлять время")
        self._round_time.setChecked(self.settings.get('round_time', False))
        self._open_auto = QCheckBox("Открыть после экспорта")
        self._open_auto.setChecked(self.settings.get('open_auto', True))

        for cb in [self._round_time, self._open_auto]:
            layout.addWidget(cb)

        # Кнопка сохранения
        btn_ok = QPushButton("Сохранить настройки")
        btn_ok.clicked.connect(self.accept)
        layout.addWidget(btn_ok)

    def _open_actor_filter(self) -> None:
        from .actor_filter import ActorFilterDialog

        if not self.parent_app or not hasattr(self.parent_app, 'data'):
            QMessageBox.warning(
                self, "Ошибка", "Не удалось получить доступ к данным актёров"
            )
            return

        all_aids: List[str] = list(self.parent_app.data["actors"].keys())
        current_selection: List[str] = (
            self.highlight_ids_export
            if self.highlight_ids_export is not None
            else all_aids
        )

        dialog: ActorFilterDialog = ActorFilterDialog(
            self.parent_app.data["actors"],
            current_selection,
            self
        )
        if dialog.exec():
            selected: List[str] = dialog.get_selected()
            if len(selected) == len(all_aids) or len(selected) == 0:
                self.highlight_ids_export = None
            else:
                self.highlight_ids_export = selected

    def get_settings(self) -> Dict[str, Any]:
        """Возвращает обновлённые настройки"""
        settings: Dict[str, Any] = self.settings.copy()
        settings.update({
            'layout_type': self._layout_type.currentText(),
            'col_tc': self._col_tc.isChecked(),
            'col_char': self._col_char.isChecked(),
            'col_actor': self._col_actor.isChecked(),
            'col_text': self._col_text.isChecked(),
            'f_time': self._f_time.value(),
            'f_char': self._f_char.value(),
            'f_actor': self._f_actor.value(),
            'f_text': self._f_text.value(),
            'use_color': self._use_color.isChecked(),
            'round_time': self._round_time.isChecked(),
            'open_auto': self._open_auto.isChecked(),
            'allow_edit': self._allow_edit.isChecked(),
            'highlight_ids_export': self.highlight_ids_export
        })
        return settings