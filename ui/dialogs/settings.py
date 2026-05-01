"""Единое окно настроек приложения."""

from copy import deepcopy
from typing import Any, Dict, List, Optional

from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
    QComboBox,
)

from config.constants import (
    DEFAULT_DOCX_IMPORT_CONFIG,
    DEFAULT_EXPORT_CONFIG,
    DEFAULT_PROMPTER_CONFIG,
    DEFAULT_REPLICA_MERGE_CONFIG,
)
from .actor_filter import ActorFilterDialog
from .colors import PrompterColorDialog


class SettingsDialog(QDialog):
    """Объединённые настройки проекта и глобальных значений по умолчанию."""

    def __init__(
        self,
        project_data: Dict[str, Any],
        parent: Optional[QWidget] = None,
        initial_tab: str = "export",
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Настройки")
        self.resize(720, 560)

        self.project_data = project_data
        self.initial_tab = initial_tab
        self.export_config = deepcopy(
            project_data.get("export_config", DEFAULT_EXPORT_CONFIG)
        )
        self.highlight_ids_export = self.export_config.get(
            "highlight_ids_export"
        )
        self.prompter_config = deepcopy(
            project_data.get("prompter_config", DEFAULT_PROMPTER_CONFIG)
        )
        self.merge_config = deepcopy(
            project_data.get(
                "replica_merge_config",
                DEFAULT_REPLICA_MERGE_CONFIG
            )
        )
        self.docx_config = deepcopy(
            project_data.get("docx_import_config", DEFAULT_DOCX_IMPORT_CONFIG)
        )
        self.prompter_colors = deepcopy(DEFAULT_PROMPTER_CONFIG["colors"])
        self.prompter_colors.update(self.prompter_config.get("colors", {}))

        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)

        self.tabs = QTabWidget()
        self.tabs.addTab(self._build_export_tab(), "Экспорт")
        self.tabs.addTab(self._build_merge_tab(), "Объединение")
        self.tabs.addTab(self._build_prompter_tab(), "Телесуфлёр")
        self.tabs.addTab(self._build_docx_tab(), "DOCX")
        self.tabs.addTab(self._build_project_tab(), "Проект")
        layout.addWidget(self.tabs)
        self._select_initial_tab()

        buttons = QDialogButtonBox(
            QDialogButtonBox.Save | QDialogButtonBox.Cancel
        )
        buttons.button(QDialogButtonBox.Save).setText("Сохранить")
        buttons.button(QDialogButtonBox.Cancel).setText("Отмена")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _build_export_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)

        layout.addWidget(self._hint(
            "Эти параметры влияют на HTML, Excel и быстрый просмотр "
            "монтажного листа. На исходные ASS/SRT и рабочие тексты они не "
            "влияют."
        ))

        form = QFormLayout()
        self.export_layout_type = QComboBox()
        self.export_layout_type.addItems(["Таблица", "Сценарий"])
        self.export_layout_type.setCurrentText(
            self.export_config.get("layout_type", "Таблица")
        )
        self.export_layout_type.setToolTip(
            "Таблица удобна для сверки и записи. Сценарий делает лист "
            "похожим на читабельный текст с репликами."
        )
        form.addRow("Тип разметки:", self.export_layout_type)
        layout.addLayout(form)

        columns = QGroupBox("Элементы в листе")
        columns_layout = QVBoxLayout(columns)
        self.export_col_tc = self._check_box(
            "Таймкоды", self.export_config.get("col_tc", True)
        )
        self.export_col_tc.setToolTip(
            "Показывает начало и конец реплики в экспортированном листе."
        )
        self.export_col_char = self._check_box(
            "Имя персонажа", self.export_config.get("col_char", True)
        )
        self.export_col_char.setToolTip(
            "Добавляет колонку или подпись с персонажем из текста серии."
        )
        self.export_col_actor = self._check_box(
            "Имя актёра", self.export_config.get("col_actor", True)
        )
        self.export_col_actor.setToolTip(
            "Показывает назначенного актёра с учётом глобальных и локальных "
            "назначений."
        )
        self.export_col_text = self._check_box(
            "Текст реплики", self.export_config.get("col_text", True)
        )
        self.export_col_text.setToolTip(
            "Добавляет сам текст реплики. Обычно это главный столбец листа."
        )
        for checkbox in [
            self.export_col_tc,
            self.export_col_char,
            self.export_col_actor,
            self.export_col_text,
        ]:
            columns_layout.addWidget(checkbox)
        columns_layout.addWidget(self._hint(
            "Отключайте лишние элементы, если нужен компактный лист для "
            "печати или раздачи актёрам."
        ))
        layout.addWidget(columns)

        fonts = QGroupBox("Размеры шрифтов")
        fonts_layout = QFormLayout(fonts)
        self.export_f_time = self._spin(6, 72, self.export_config.get("f_time", 21))
        self.export_f_char = self._spin(6, 72, self.export_config.get("f_char", 20))
        self.export_f_actor = self._spin(6, 72, self.export_config.get("f_actor", 14))
        self.export_f_text = self._spin(6, 72, self.export_config.get("f_text", 30))
        self.export_f_time.setToolTip("Размер таймкодов в HTML/Excel экспорте.")
        self.export_f_char.setToolTip("Размер имён персонажей в HTML/Excel экспорте.")
        self.export_f_actor.setToolTip("Размер имён актёров в HTML/Excel экспорте.")
        self.export_f_text.setToolTip("Размер текста реплик в HTML/Excel экспорте.")
        fonts_layout.addRow("Таймкод:", self.export_f_time)
        fonts_layout.addRow("Персонаж:", self.export_f_char)
        fonts_layout.addRow("Актёр:", self.export_f_actor)
        fonts_layout.addRow("Текст:", self.export_f_text)
        fonts_layout.addRow(self._hint(
            "Больший размер текста удобен для записи с экрана или печати; "
            "меньшие размеры делают таблицу плотнее."
        ))
        layout.addWidget(fonts)

        self.export_use_color = self._check_box(
            "Использовать цвета актёров",
            self.export_config.get("use_color", True)
        )
        self.export_use_color.setToolTip(
            "Подсвечивает строки или имена цветами актёров, чтобы роли легче "
            "читались в листе."
        )
        self.btn_export_actor_filter = QPushButton(
            "Выбрать актёров для подсветки..."
        )
        self.btn_export_actor_filter.setToolTip(
            "Ограничивает цветовую подсветку монтажного листа только "
            "выбранными актёрами."
        )
        self.btn_export_actor_filter.clicked.connect(
            self._open_export_actor_filter
        )
        self.export_actor_filter_summary = self._hint("")
        self._update_export_actor_filter_summary()
        self.export_allow_edit = self._check_box(
            "Разрешить редактирование в HTML",
            self.export_config.get("allow_edit", True)
        )
        self.export_allow_edit.setToolTip(
            "Делает текст реплик редактируемым прямо в HTML-файле. Изменения "
            "в браузере не записываются обратно в проект автоматически."
        )
        self.export_round_time = self._check_box(
            "Округлять время",
            self.export_config.get("round_time", False)
        )
        self.export_round_time.setToolTip(
            "Убирает дробную точность таймкодов в листе, если нужна более "
            "простая визуальная разметка."
        )
        self.export_open_auto = self._check_box(
            "Открывать после экспорта",
            self.export_config.get("open_auto", True)
        )
        self.export_open_auto.setToolTip(
            "После успешного экспорта сразу открывает созданный файл."
        )
        for checkbox in [
            self.export_use_color,
            self.export_allow_edit,
            self.export_round_time,
            self.export_open_auto,
        ]:
            layout.addWidget(checkbox)
        layout.addWidget(self.btn_export_actor_filter)
        layout.addWidget(self.export_actor_filter_summary)

        layout.addStretch()
        return tab

    def _build_merge_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)

        info = QLabel(
            "Эти настройки используются в монтажных листах, телесуфлёре, "
            "HTML/Excel экспорте и отчётах."
        )
        info.setWordWrap(True)
        info.setStyleSheet("color: #666;")
        layout.addWidget(info)

        group = QGroupBox("Объединение реплик")
        form = QFormLayout(group)

        self.merge_enabled = self._check_box(
            "Включить объединение реплик",
            self.merge_config.get("merge", True)
        )
        self.merge_enabled.setToolTip(
            "Склеивает близкие реплики одного персонажа в одну строку."
        )
        form.addRow(self.merge_enabled)

        fps = float(self.merge_config.get("fps", 25.0) or 25.0)
        self.merge_fps = self._double_spin(1.0, 120.0, fps, decimals=3)
        self.merge_gap = self._double_spin(
            0.0,
            10.0,
            float(self.merge_config.get("merge_gap", 120)) / fps,
            step=0.1
        )
        self.merge_p_short = self._double_spin(
            0.0, 5.0, self.merge_config.get("p_short", 0.5), step=0.1
        )
        self.merge_p_long = self._double_spin(
            0.0, 10.0, self.merge_config.get("p_long", 2.0), step=0.1
        )
        self.merge_fps.setToolTip(
            "Используется только для пересчёта порога слияния из кадров в "
            "секунды и обратно."
        )
        self.merge_gap.setToolTip(
            "Максимальная пауза между репликами одного персонажа, при "
            "которой они ещё объединяются."
        )
        self.merge_p_short.setToolTip(
            "Пауза внутри объединённой реплики, после которой ставится один "
            "разделитель '/'."
        )
        self.merge_p_long.setToolTip(
            "Пауза внутри объединённой реплики, после которой ставится "
            "двойной разделитель '//'."
        )

        form.addRow("FPS:", self.merge_fps)
        form.addRow("Порог слияния, сек:", self.merge_gap)
        form.addRow("Пауза для '/' , сек:", self.merge_p_short)
        form.addRow("Пауза для '//' , сек:", self.merge_p_long)
        layout.addWidget(group)

        explanation = QLabel(
            "Реплики одного персонажа объединяются, если пауза между ними "
            "меньше порога слияния. Длинные паузы отмечаются разделителями "
            "' / ' и ' // '."
        )
        explanation.setWordWrap(True)
        explanation.setStyleSheet(
            "padding: 8px; background: #f5f5f5; color: #666; "
            "border-radius: 4px;"
        )
        layout.addWidget(explanation)
        layout.addStretch()
        return tab

    def _build_prompter_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)

        fonts = QGroupBox("Шрифты")
        fonts_layout = QFormLayout(fonts)
        self.prompter_f_tc = self._spin(
            8, 96, self.prompter_config.get("f_tc", 20)
        )
        self.prompter_f_char = self._spin(
            8, 96, self.prompter_config.get("f_char", 24)
        )
        self.prompter_f_actor = self._spin(
            8, 96, self.prompter_config.get("f_actor", 18)
        )
        self.prompter_f_text = self._spin(
            8, 120, self.prompter_config.get("f_text", 36)
        )
        fonts_layout.addRow("Таймкод:", self.prompter_f_tc)
        fonts_layout.addRow("Персонаж:", self.prompter_f_char)
        fonts_layout.addRow("Актёр:", self.prompter_f_actor)
        fonts_layout.addRow("Текст:", self.prompter_f_text)
        layout.addWidget(fonts)

        behavior = QGroupBox("Поведение")
        behavior_layout = QFormLayout(behavior)
        self.prompter_focus_ratio = self._double_spin(
            0.1,
            0.9,
            self.prompter_config.get("focus_ratio", 0.5),
            step=0.05,
            decimals=2
        )
        self.prompter_smoothness = self._spin(
            1,
            60,
            self.prompter_config.get("scroll_smoothness_slider", 18)
        )
        self.prompter_mirrored = self._check_box(
            "Зеркальный режим",
            self.prompter_config.get("is_mirrored", False)
        )
        self.prompter_show_header = self._check_box(
            "Показывать верхнюю панель",
            self.prompter_config.get("show_header", False)
        )
        self.prompter_focus_ratio.setToolTip(
            "Где на экране держать активную реплику: 0.5 — центр, меньше — "
            "выше, больше — ниже."
        )
        self.prompter_smoothness.setToolTip(
            "Насколько плавно телесуфлёр прокручивается к активной реплике."
        )
        self.prompter_mirrored.setToolTip(
            "Отражает текст для использования с зеркальным телесуфлёрным "
            "стеклом."
        )
        self.prompter_show_header.setToolTip(
            "Показывает служебную верхнюю панель в окне телесуфлёра."
        )
        behavior_layout.addRow("Позиция фокуса:", self.prompter_focus_ratio)
        behavior_layout.addRow("Плавность скролла:", self.prompter_smoothness)
        behavior_layout.addRow(self.prompter_mirrored)
        behavior_layout.addRow(self.prompter_show_header)
        layout.addWidget(behavior)

        osc = QGroupBox("Reaper / OSC")
        osc_layout = QFormLayout(osc)
        self.prompter_port_in = self._spin(
            1, 65535, self.prompter_config.get("port_in", 8000)
        )
        self.prompter_port_out = self._spin(
            1, 65535, self.prompter_config.get("port_out", 9000)
        )
        self.prompter_sync_in = self._check_box(
            "Принимать синхронизацию из Reaper",
            self.prompter_config.get("sync_in", True)
        )
        self.prompter_sync_out = self._check_box(
            "Отправлять синхронизацию в Reaper",
            self.prompter_config.get("sync_out", False)
        )
        self.prompter_offset_enabled = self._check_box(
            "Использовать offset телесуфлёра",
            self.prompter_config.get("reaper_offset_enabled", False)
        )
        self.prompter_offset_seconds = self._double_spin(
            -60.0,
            60.0,
            self.prompter_config.get("reaper_offset_seconds", -2.0),
            step=0.1
        )
        self.prompter_port_in.setToolTip(
            "Порт, на котором телесуфлёр слушает входящие OSC-сообщения от "
            "Reaper."
        )
        self.prompter_port_out.setToolTip(
            "Порт, на который приложение отправляет OSC-сообщения в Reaper."
        )
        self.prompter_sync_in.setToolTip(
            "Позволяет Reaper вести телесуфлёр по текущей позиции проекта."
        )
        self.prompter_sync_out.setToolTip(
            "Позволяет телесуфлёру отправлять переходы и позицию обратно в "
            "Reaper."
        )
        self.prompter_offset_enabled.setToolTip(
            "Сдвигает отображение активной реплики в телесуфлёре относительно "
            "позиции Reaper."
        )
        self.prompter_offset_seconds.setToolTip(
            "Сколько секунд прибавлять к позиции Reaper для телесуфлёра. "
            "Не влияет на RPP-экспорт."
        )
        osc_layout.addRow("OSC вход:", self.prompter_port_in)
        osc_layout.addRow("OSC выход:", self.prompter_port_out)
        osc_layout.addRow(self.prompter_sync_in)
        osc_layout.addRow(self.prompter_sync_out)
        osc_layout.addRow(self.prompter_offset_enabled)
        osc_layout.addRow("Offset, сек:", self.prompter_offset_seconds)
        layout.addWidget(osc)

        offset_note = QLabel(
            "Offset применяется только к телесуфлёру и не влияет на экспорт "
            "регионов RPP."
        )
        offset_note.setWordWrap(True)
        offset_note.setStyleSheet("color: #666;")
        layout.addWidget(offset_note)

        colors_row = QHBoxLayout()
        colors_row.addStretch()
        btn_colors = QPushButton("Цветовая схема...")
        btn_colors.clicked.connect(self._open_prompter_colors)
        colors_row.addWidget(btn_colors)
        layout.addLayout(colors_row)

        layout.addStretch()
        return tab

    def _build_docx_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)

        form = QFormLayout()
        separators = self.docx_config.get("time_separators", ["-"])
        self.docx_time_separators = QLineEdit(", ".join(separators))
        self.docx_time_separators.setToolTip(
            "Разделители начала и конца таймкода. Например: -, –, —"
        )
        form.addRow("Разделители тайминга:", self.docx_time_separators)
        layout.addLayout(form)

        mapping = self.docx_config.get("mapping") or {}
        mapping_text = QLabel(
            "Маппинг колонок сохраняется из диалога импорта DOCX.\n"
            f"Текущий маппинг: {mapping if mapping else 'не задан'}"
        )
        mapping_text.setWordWrap(True)
        mapping_text.setStyleSheet(
            "padding: 8px; background: #f5f5f5; color: #666; "
            "border-radius: 4px;"
        )
        layout.addWidget(mapping_text)
        layout.addStretch()
        return tab

    def _build_project_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)

        project_folder = self.project_data.get("project_folder") or "не задана"
        texts_count = len(self.project_data.get("episode_texts", {}))
        episodes_count = len(self.project_data.get("episodes", {}))

        info = QLabel(
            f"Папка проекта: {project_folder}\n"
            f"Серий: {episodes_count}\n"
            f"Рабочих текстов: {texts_count}\n\n"
            "Папка проекта и проверка целостности доступны с верхней панели."
        )
        info.setWordWrap(True)
        info.setStyleSheet("color: #666;")
        layout.addWidget(info)
        layout.addStretch()
        return tab

    def _open_prompter_colors(self) -> None:
        dialog = PrompterColorDialog(self.prompter_colors, self)
        if dialog.exec():
            self.prompter_colors = dialog.get_final_colors()

    def get_settings(self) -> Dict[str, Dict[str, Any]]:
        """Вернуть обновлённые настройки по разделам."""
        export_config = deepcopy(self.export_config)
        export_config.update({
            "layout_type": self.export_layout_type.currentText(),
            "col_tc": self.export_col_tc.isChecked(),
            "col_char": self.export_col_char.isChecked(),
            "col_actor": self.export_col_actor.isChecked(),
            "col_text": self.export_col_text.isChecked(),
            "f_time": self.export_f_time.value(),
            "f_char": self.export_f_char.value(),
            "f_actor": self.export_f_actor.value(),
            "f_text": self.export_f_text.value(),
            "use_color": self.export_use_color.isChecked(),
            "allow_edit": self.export_allow_edit.isChecked(),
            "round_time": self.export_round_time.isChecked(),
            "open_auto": self.export_open_auto.isChecked(),
            "highlight_ids_export": self.highlight_ids_export,
        })

        fps = self.merge_fps.value()
        merge_config = deepcopy(self.merge_config)
        merge_config.update({
            "merge": self.merge_enabled.isChecked(),
            "merge_gap": int(self.merge_gap.value() * fps),
            "fps": fps,
            "p_short": self.merge_p_short.value(),
            "p_long": self.merge_p_long.value(),
        })

        prompter_config = deepcopy(self.prompter_config)
        prompter_config.update({
            "f_tc": self.prompter_f_tc.value(),
            "f_char": self.prompter_f_char.value(),
            "f_actor": self.prompter_f_actor.value(),
            "f_text": self.prompter_f_text.value(),
            "focus_ratio": self.prompter_focus_ratio.value(),
            "is_mirrored": self.prompter_mirrored.isChecked(),
            "show_header": self.prompter_show_header.isChecked(),
            "port_in": self.prompter_port_in.value(),
            "port_out": self.prompter_port_out.value(),
            "sync_in": self.prompter_sync_in.isChecked(),
            "sync_out": self.prompter_sync_out.isChecked(),
            "reaper_offset_enabled": self.prompter_offset_enabled.isChecked(),
            "reaper_offset_seconds": self.prompter_offset_seconds.value(),
            "scroll_smoothness_slider": self.prompter_smoothness.value(),
            "colors": deepcopy(self.prompter_colors),
        })

        docx_config = deepcopy(self.docx_config)
        docx_config["time_separators"] = self._parse_separators(
            self.docx_time_separators.text()
        )

        return {
            "export_config": export_config,
            "replica_merge_config": merge_config,
            "prompter_config": prompter_config,
            "docx_import_config": docx_config,
        }

    def _parse_separators(self, text: str) -> List[str]:
        separators = [
            item.strip()
            for item in text.split(",")
            if item.strip()
        ]
        return separators or deepcopy(
            DEFAULT_DOCX_IMPORT_CONFIG["time_separators"]
        )

    def _select_initial_tab(self) -> None:
        tab_indexes = {
            "export": 0,
            "merge": 1,
            "prompter": 2,
            "docx": 3,
            "project": 4,
        }
        self.tabs.setCurrentIndex(tab_indexes.get(self.initial_tab, 0))

    def _open_export_actor_filter(self) -> None:
        actors = self.project_data.get("actors", {})
        if not actors:
            QMessageBox.information(
                self,
                "Подсветка актёров",
                "В проекте пока нет актёров для выбора.",
            )
            return

        all_actor_ids = list(actors.keys())
        current_selection = (
            self.highlight_ids_export
            if self.highlight_ids_export is not None
            else all_actor_ids
        )

        dialog = ActorFilterDialog(actors, current_selection, self)
        if dialog.exec():
            selected = dialog.get_selected()
            if len(selected) == len(all_actor_ids) or len(selected) == 0:
                self.highlight_ids_export = None
            else:
                self.highlight_ids_export = selected
            self._update_export_actor_filter_summary()

    def _update_export_actor_filter_summary(self) -> None:
        actors = self.project_data.get("actors", {})
        if self.highlight_ids_export is None:
            text = "Подсветка применяется ко всем актёрам."
        elif not self.highlight_ids_export:
            text = "Подсветка применяется ко всем актёрам."
        else:
            selected_names = [
                actors.get(actor_id, {}).get("name", actor_id)
                for actor_id in self.highlight_ids_export
            ]
            text = "Подсветка выбрана для: " + ", ".join(selected_names)
        self.export_actor_filter_summary.setText(text)

    def _hint(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setWordWrap(True)
        label.setStyleSheet("color: #666; font-size: 11px;")
        return label

    def _check_box(self, text: str, checked: bool) -> QCheckBox:
        checkbox = QCheckBox(text)
        checkbox.setChecked(bool(checked))
        return checkbox

    def _spin(self, minimum: int, maximum: int, value: Any) -> QSpinBox:
        spin = QSpinBox()
        spin.setRange(minimum, maximum)
        spin.setValue(int(value))
        return spin

    def _double_spin(
        self,
        minimum: float,
        maximum: float,
        value: Any,
        step: float = 1.0,
        decimals: int = 1
    ) -> QDoubleSpinBox:
        spin = QDoubleSpinBox()
        spin.setRange(minimum, maximum)
        spin.setSingleStep(step)
        spin.setDecimals(decimals)
        spin.setValue(float(value))
        return spin
