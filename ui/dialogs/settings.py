"""Unified application settings dialog."""

from copy import deepcopy
from typing import Any, Dict, List, Optional

from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QGridLayout,
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
from utils.i18n import available_languages, tr, translate_source, translate_widget_tree
from .actor_filter import ActorFilterDialog
from .colors import PrompterColorDialog
from .settings_helpers import (
    check_box,
    double_spin,
    hint_label,
    int_spin,
    parse_separators,
)


class SettingsDialog(QDialog):
    """Settings Dialog dialog."""

    def __init__(
        self,
        project_data: Dict[str, Any],
        parent: Optional[QWidget] = None,
        initial_tab: str = "project",
        settings_scope: str = "project",
    ) -> None:
        super().__init__(parent)
        self.settings_scope = settings_scope
        self.setWindowTitle(
            tr("settings.title")
            if settings_scope == "global"
            else tr("settings.project_title")
        )
        self.resize(720, 560)

        self.project_data = project_data
        self.main_window = parent
        self.initial_tab = initial_tab
        self.export_config = self._load_initial_export_config(project_data)
        self.highlight_ids_export = self.export_config.get(
            "highlight_ids_export"
        )
        self.highlight_negative_ids_export = self.export_config.get(
            "highlight_negative_ids_export",
            []
        )
        self.prompter_config = deepcopy(
            self._load_initial_prompter_config(project_data)
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
        self.language = "ru"
        if parent is not None and hasattr(parent, "global_settings"):
            self.language = parent.global_settings.get("language", "ru")
        self.prompter_colors = deepcopy(DEFAULT_PROMPTER_CONFIG["colors"])
        self.prompter_colors.update(self.prompter_config.get("colors", {}))

        self._init_ui()

    def _load_initial_export_config(
        self,
        project_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        if (
            self.settings_scope == "global" and
            self.main_window is not None and
            hasattr(self.main_window, "global_settings_service")
        ):
            return deepcopy(
                self.main_window.global_settings_service
                .get_default_export_config()
            )

        return deepcopy(
            project_data.get("export_config", DEFAULT_EXPORT_CONFIG)
        )

    def _load_initial_prompter_config(
        self,
        project_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        if (
            self.settings_scope == "global" and
            self.main_window is not None and
            hasattr(self.main_window, "global_settings_service")
        ):
            return deepcopy(
                self.main_window.global_settings_service
                .get_default_prompter_config()
            )

        return deepcopy(
            project_data.get("prompter_config", DEFAULT_PROMPTER_CONFIG)
        )

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)

        self.tabs = QTabWidget()
        self._tab_indexes: Dict[str, int] = {}
        if self.settings_scope == "project":
            self._add_tab("project", self._build_project_tab(), "Проект")
            self._add_tab(
                "series_files",
                self._build_series_files_tab(),
                "Серии и файлы"
            )
            self._add_tab("roles", self._build_roles_tab(), "Роли")
            self._add_tab("export", self._build_export_tab(), "Монтажный лист")
            self._add_tab("merge", self._build_merge_tab(), "Реплики")
            self._add_tab("prompter", self._build_prompter_tab(), tr("settings.tab.prompter"))
            self._add_tab(
                "actor_bases",
                self._build_actor_bases_tab(),
                "Перенос",
            )
        else:
            self._add_tab("export", self._build_export_tab(), "Монтажный лист")
            self._add_tab(
                "prompter",
                self._build_prompter_tab(),
                tr("settings.tab.prompter")
            )
            self._add_tab(
                "actor_bases",
                self._build_actor_bases_tab(),
                "Актёры",
            )
            self._add_tab("interface", self._build_interface_tab(), tr("settings.interface"))
        layout.addWidget(self.tabs)
        self._select_initial_tab()

        footer_layout = QHBoxLayout()
        if self.settings_scope == "project":
            self._init_export_default_buttons()
            self._init_prompter_default_buttons()
            footer_layout.addWidget(self.btn_apply_export_defaults)
            footer_layout.addWidget(self.btn_save_export_defaults)
            footer_layout.addWidget(self.btn_apply_prompter_defaults)
            footer_layout.addWidget(self.btn_save_prompter_defaults)
        elif self.settings_scope == "global":
            self.btn_apply_global_export_to_project = QPushButton(
                "Перенести в проект"
            )
            self.btn_apply_global_export_to_project.setToolTip(
                "Применить эти настройки монтажного листа к открытому проекту."
            )
            self.btn_apply_global_export_to_project.setEnabled(
                self._has_export_apply_service()
            )
            self.btn_apply_global_export_to_project.clicked.connect(
                self._apply_global_export_to_project
            )
            footer_layout.addWidget(self.btn_apply_global_export_to_project)
            self.btn_apply_global_prompter_to_project = QPushButton(
                "Перенести в проект"
            )
            self.btn_apply_global_prompter_to_project.setToolTip(
                "Применить эти настройки телесуфлёра к открытому проекту."
            )
            self.btn_apply_global_prompter_to_project.setEnabled(
                self._has_prompter_apply_service()
            )
            self.btn_apply_global_prompter_to_project.clicked.connect(
                self._apply_global_prompter_to_project
            )
            footer_layout.addWidget(self.btn_apply_global_prompter_to_project)
        footer_layout.addStretch()

        buttons = QDialogButtonBox(
            QDialogButtonBox.Save | QDialogButtonBox.Cancel
        )
        buttons.button(QDialogButtonBox.Save).setText(tr("common.save"))
        buttons.button(QDialogButtonBox.Cancel).setText(tr("common.cancel"))
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        footer_layout.addWidget(buttons)
        layout.addLayout(footer_layout)
        self.tabs.currentChanged.connect(self._update_footer_action_visibility)
        self._update_footer_action_visibility()
        translate_widget_tree(self)

    def _add_tab(self, key: str, widget: QWidget, title: str) -> None:
        self._tab_indexes[key] = self.tabs.count()
        self.tabs.addTab(widget, title)

    def _build_export_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)

        layout.addWidget(self._hint(
            "Эти параметры влияют на HTML, Excel, DOCX, PDF и быстрый просмотр "
            "монтажного листа. На исходные ASS/SRT и рабочие тексты они не "
            "влияют."
        ))

        formats = QGroupBox("Форматы экспорта")
        formats_layout = QHBoxLayout(formats)
        self.export_format_html = self._check_box(
            "HTML", self.export_config.get("format_html", True)
        )
        self.export_format_xls = self._check_box(
            "Excel", self.export_config.get("format_xls", False)
        )
        self.export_format_docx = self._check_box(
            "DOCX", self.export_config.get("format_docx", False)
        )
        self.export_format_pdf = self._check_box(
            "PDF", self.export_config.get("format_pdf", False)
        )
        self.export_format_html.setToolTip(
            "Создавать HTML-монтажный лист при экспорте."
        )
        self.export_format_xls.setToolTip(
            "Создавать Excel-файл при экспорте."
        )
        self.export_format_docx.setToolTip(
            "Создавать DOCX-файл при экспорте."
        )
        self.export_format_pdf.setToolTip(
            "Создавать PDF-файл при экспорте."
        )
        formats_layout.addWidget(self.export_format_html)
        formats_layout.addWidget(self.export_format_xls)
        formats_layout.addWidget(self.export_format_docx)
        formats_layout.addWidget(self.export_format_pdf)
        formats_layout.addStretch()
        layout.addWidget(formats)

        form = QFormLayout()
        self.export_layout_type = QComboBox()
        self.export_layout_type.addItem(translate_source("Таблица"), "Таблица")
        self.export_layout_type.addItem("Сценарий 1", "Сценарий 1")
        self.export_layout_type.addItem("Сценарий 2", "Сценарий 2")
        self.export_layout_type.addItem("Сценарий 3", "Сценарий 3")
        current_layout_type = self.export_config.get("layout_type", "Таблица")
        if current_layout_type == "Сценарий":
            current_layout_type = "Сценарий 1"
        layout_index = self.export_layout_type.findData(
            current_layout_type
        )
        self.export_layout_type.setCurrentIndex(layout_index if layout_index >= 0 else 0)
        self.export_layout_type.currentIndexChanged.connect(
            self._update_table_width_controls_visibility
        )
        self.export_layout_type.setToolTip(
            "Таблица удобна для сверки и записи. Сценарий 1 повторяет "
            "классическую сценарную разметку, Сценарий 2 делает реплики "
            "крупными цветными блоками, Сценарий 3 разделяет служебные "
            "данные и реплику на две колонки."
        )
        form.addRow("Тип разметки:", self.export_layout_type)
        layout.addLayout(form)

        columns = QGroupBox("Элементы в листе")
        columns_layout = QVBoxLayout(columns)
        columns_top_layout = QHBoxLayout()
        column_checks_layout = QVBoxLayout()
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
            column_checks_layout.addWidget(checkbox)
        column_checks_layout.addStretch()
        columns_top_layout.addLayout(column_checks_layout)
        self.table_widths_group = QGroupBox("Ширина колонок таблицы")
        widths_layout = QFormLayout(self.table_widths_group)
        self.export_table_width_time = self._double_spin(
            4.0,
            24.0,
            self.export_config.get("table_width_time", 7.0),
            step=0.5,
        )
        self.export_table_width_char = self._double_spin(
            4.0,
            24.0,
            self.export_config.get("table_width_char", 10.0),
            step=0.5,
        )
        self.export_table_width_actor = self._double_spin(
            4.0,
            24.0,
            self.export_config.get("table_width_actor", 8.5),
            step=0.5,
        )
        for spin in [
            self.export_table_width_time,
            self.export_table_width_char,
            self.export_table_width_actor,
        ]:
            spin.setSuffix(" ед.")
            spin.setToolTip(
                "Ширина служебной колонки в табличной разметке. "
                "Колонка реплики занимает оставшееся место."
            )
        widths_layout.addRow("Тайминг:", self.export_table_width_time)
        widths_layout.addRow("Персонаж:", self.export_table_width_char)
        widths_layout.addRow("Актёр:", self.export_table_width_actor)
        columns_top_layout.addWidget(self.table_widths_group)
        columns_layout.addLayout(columns_top_layout)
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
        self.export_f_time.setToolTip("Размер таймкодов в монтажном экспорте.")
        self.export_f_char.setToolTip("Размер имён персонажей в монтажном экспорте.")
        self.export_f_actor.setToolTip("Размер имён актёров в монтажном экспорте.")
        self.export_f_text.setToolTip("Размер текста реплик в монтажном экспорте.")
        fonts_layout.addRow("Таймкод:", self.export_f_time)
        fonts_layout.addRow("Персонаж:", self.export_f_char)
        fonts_layout.addRow("Актёр:", self.export_f_actor)
        fonts_layout.addRow("Текст:", self.export_f_text)
        fonts_layout.addRow(self._hint(
            "Больший размер текста удобен для записи с экрана или печати; "
            "меньшие размеры делают таблицу плотнее."
        ))
        layout.addWidget(fonts)
        self._update_table_width_controls_visibility()

        self.export_use_color = self._check_box(
            "Использовать цвета актёров",
            self.export_config.get("use_color", True)
        )
        self.export_use_color.setToolTip(
            "Подсвечивает строки или имена цветами актёров, чтобы роли легче "
            "читались в листе."
        )
        self.export_soften_colors = self._check_box(
            "Смягчить цвета",
            self.export_config.get("soften_colors", True)
        )
        self.export_soften_colors.setToolTip(
            "Использует мягкую заливку вместо плотного цвета актёра."
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
        self.export_time_display = QComboBox()
        self.export_time_display.addItem(translate_source("Начало и конец"), "range")
        self.export_time_display.addItem(translate_source("Только начало"), "start")
        current_time_display = self.export_config.get("time_display", "range")
        time_display_index = self.export_time_display.findData(current_time_display)
        if time_display_index < 0:
            time_display_index = 0
        self.export_time_display.setCurrentIndex(time_display_index)
        self.export_time_display.setToolTip(
            "Определяет, показывать ли в таймкоде конец реплики или только "
            "момент её начала."
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
            self.export_soften_colors,
            self.export_allow_edit,
            self.export_open_auto,
        ]:
            layout.addWidget(checkbox)
        time_display_form = QFormLayout()
        time_display_form.addRow("Тайминг:", self.export_time_display)
        layout.addLayout(time_display_form)
        layout.addWidget(self.export_round_time)
        layout.addWidget(self.btn_export_actor_filter)
        layout.addWidget(self.export_actor_filter_summary)

        layout.addStretch()
        return tab

    def _init_export_default_buttons(self) -> None:
        self.btn_apply_export_defaults = QPushButton("Сделать по умолчанию")
        self.btn_apply_export_defaults.setToolTip(
            "Заменить настройки монтажного листа в текущем проекте "
            "сохранёнными настройками по умолчанию."
        )
        self.btn_save_export_defaults = QPushButton("Сохранить по умолчанию")
        self.btn_save_export_defaults.setToolTip(
            "Использовать текущие настройки монтажного листа для новых "
            "проектов."
        )
        self.btn_apply_export_defaults.clicked.connect(
            self._apply_export_defaults_to_project
        )
        self.btn_save_export_defaults.clicked.connect(
            self._save_export_defaults
        )
        defaults_enabled = self._has_export_defaults_service()
        self.btn_apply_export_defaults.setEnabled(defaults_enabled)
        self.btn_save_export_defaults.setEnabled(defaults_enabled)

    def _init_prompter_default_buttons(self) -> None:
        self.btn_apply_prompter_defaults = QPushButton("Сделать по умолчанию")
        self.btn_apply_prompter_defaults.setToolTip(
            "Заменить настройки телесуфлёра в текущем проекте сохранёнными "
            "настройками по умолчанию."
        )
        self.btn_save_prompter_defaults = QPushButton("Сохранить по умолчанию")
        self.btn_save_prompter_defaults.setToolTip(
            "Использовать текущие настройки телесуфлёра для новых проектов."
        )
        self.btn_apply_prompter_defaults.clicked.connect(
            self._apply_prompter_defaults_to_project
        )
        self.btn_save_prompter_defaults.clicked.connect(
            self._save_prompter_defaults
        )
        defaults_enabled = self._has_prompter_defaults_service()
        self.btn_apply_prompter_defaults.setEnabled(defaults_enabled)
        self.btn_save_prompter_defaults.setEnabled(defaults_enabled)

    def _current_tab_key(self) -> str:
        current_index = self.tabs.currentIndex()
        for key, index in self._tab_indexes.items():
            if index == current_index:
                return key
        return ""

    def _update_footer_action_visibility(self) -> None:
        current_key = self._current_tab_key()
        if self.settings_scope == "project":
            if hasattr(self, "btn_apply_export_defaults"):
                export_visible = current_key == "export"
                self.btn_apply_export_defaults.setVisible(export_visible)
                self.btn_save_export_defaults.setVisible(export_visible)
            if hasattr(self, "btn_apply_prompter_defaults"):
                prompter_visible = current_key == "prompter"
                self.btn_apply_prompter_defaults.setVisible(prompter_visible)
                self.btn_save_prompter_defaults.setVisible(prompter_visible)
        elif self.settings_scope == "global":
            if hasattr(self, "btn_apply_global_export_to_project"):
                self.btn_apply_global_export_to_project.setVisible(
                    current_key == "export"
                )
            if hasattr(self, "btn_apply_global_prompter_to_project"):
                self.btn_apply_global_prompter_to_project.setVisible(
                    current_key == "prompter"
                )

    def _build_interface_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)

        note = QLabel(tr("settings.interface.note"))
        note.setWordWrap(True)
        note.setStyleSheet("color: #666;")
        layout.addWidget(note)

        form = QFormLayout()
        self.language_combo = QComboBox()
        for code, name in available_languages().items():
            self.language_combo.addItem(name, code)
        index = self.language_combo.findData(self.language)
        self.language_combo.setCurrentIndex(index if index >= 0 else 0)
        form.addRow(tr("settings.interface.language"), self.language_combo)
        layout.addLayout(form)

        restart_note = QLabel(tr("settings.language.restart_note"))
        restart_note.setWordWrap(True)
        restart_note.setStyleSheet("color: #666;")
        layout.addWidget(restart_note)
        layout.addStretch()
        return tab

    def _build_merge_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)

        info = QLabel(
            "Эти настройки используются в монтажных листах, телесуфлёре, "
            "экспорте и отчётах."
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
        grid = QGridLayout()
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)

        fonts = QGroupBox("Шрифты")
        fonts_layout = QFormLayout(fonts)
        fonts_layout.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
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
        grid.addWidget(fonts, 0, 0)

        behavior = QGroupBox("Поведение")
        behavior_layout = QFormLayout(behavior)
        behavior_layout.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
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
        grid.addWidget(behavior, 0, 1)

        osc = QGroupBox("Reaper / OSC")
        osc_layout = QFormLayout(osc)
        osc_layout.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        self.prompter_port_in = self._spin(
            1, 65535, self.prompter_config.get("port_in", 8000)
        )
        self.prompter_port_out = self._spin(
            1, 65535, self.prompter_config.get("port_out", 9000)
        )
        self.prompter_osc_enabled = self._check_box(
            "Включать OSC связь",
            self.prompter_config.get("osc_enabled", False)
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
        self.prompter_osc_enabled.setToolTip(
            "Запоминает, должна ли OSC-связь с Reaper включаться при "
            "открытии телесуфлёра."
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
        osc_layout.addRow(self.prompter_osc_enabled)
        osc_layout.addRow(self.prompter_sync_in)
        osc_layout.addRow(self.prompter_sync_out)
        osc_layout.addRow(self.prompter_offset_enabled)
        osc_layout.addRow("Offset, сек:", self.prompter_offset_seconds)
        grid.addWidget(osc, 1, 0, 1, 2)
        layout.addLayout(grid)

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
        if self.settings_scope == "global":
            layout.addWidget(self._build_prompter_color_presets_group())

        layout.addStretch()
        return tab

    def _build_prompter_color_presets_group(self) -> QWidget:
        group = QGroupBox("Пресеты цветовых схем")
        grid = QGridLayout(group)
        grid.setColumnStretch(1, 1)
        self.prompter_preset_preview_buttons = []
        self.prompter_preset_reset_buttons = []

        for index in range(4):
            label = QLabel(f"{index + 1}:")
            preview = QPushButton()
            preview.setEnabled(False)
            preview.setMinimumHeight(26)
            reset = QPushButton("Сбросить")
            reset.clicked.connect(
                lambda checked=False, idx=index: (
                    self._clear_prompter_color_preset(idx)
                )
            )
            self.prompter_preset_preview_buttons.append(preview)
            self.prompter_preset_reset_buttons.append(reset)
            grid.addWidget(label, index, 0)
            grid.addWidget(preview, index, 1)
            grid.addWidget(reset, index, 2)

        self._update_prompter_color_preset_controls()
        return group

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

        details_group = QGroupBox("Сведения о проекте")
        details_form = QFormLayout(details_group)
        metadata = self.project_data.setdefault("metadata", {})
        self.project_name_edit = QLineEdit(
            self.project_data.get("project_name", "")
        )
        self.project_created_by_edit = QLineEdit(
            metadata.get("created_by", "")
        )
        self.project_studio_edit = QLineEdit(
            metadata.get("studio", "")
        )
        details_form.addRow("Название проекта:", self.project_name_edit)
        details_form.addRow("Автор проекта:", self.project_created_by_edit)
        details_form.addRow("Студия:", self.project_studio_edit)
        details_form.addRow(self._hint(
            "Эти сведения сохраняются в файле проекта и используются для "
            "заголовка окна и будущих отчётов."
        ))
        layout.addWidget(details_group)

        self.project_info_label = QLabel()
        self.project_info_label.setWordWrap(True)
        self.project_info_label.setStyleSheet("color: #666;")
        layout.addWidget(self.project_info_label)

        folder_group = QGroupBox("Папка проекта")
        folder_layout = QVBoxLayout(folder_group)
        folder_layout.addWidget(self._hint(
            "Рабочая папка используется для поиска исходников, видео и рабочих JSON."
        ))
        folder_buttons = QHBoxLayout()
        self.btn_set_project_folder = QPushButton("Выбрать папку...")
        self.btn_set_project_folder.clicked.connect(self._set_project_folder)
        folder_buttons.addWidget(self.btn_set_project_folder)

        self.btn_clear_project_folder = QPushButton("Отвязать папку")
        self.btn_clear_project_folder.clicked.connect(self._clear_project_folder)
        folder_buttons.addWidget(self.btn_clear_project_folder)
        folder_layout.addLayout(folder_buttons)
        layout.addWidget(folder_group)

        self._refresh_project_info()
        layout.addStretch()
        return tab

    def _build_series_files_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)

        files_group = QGroupBox("Файлы и рабочие тексты")
        files_layout = QVBoxLayout(files_group)
        files_layout.addWidget(self._hint(
            "Здесь можно проверить привязанные файлы, перепривязать потерянные "
            "пути, создать рабочие JSON и посмотреть проблемы проекта."
        ))
        files_buttons = QHBoxLayout()
        self.btn_project_files = QPushButton("Файлы проекта...")
        self.btn_project_files.clicked.connect(self._open_project_files)
        files_buttons.addWidget(self.btn_project_files)
        self.btn_project_health = QPushButton("Проверка проекта...")
        self.btn_project_health.clicked.connect(self._open_project_health)
        files_buttons.addWidget(self.btn_project_health)
        files_buttons.addStretch()
        files_layout.addLayout(files_buttons)
        layout.addWidget(files_group)

        docx_group = QGroupBox("Импорт DOCX")
        docx_layout = QVBoxLayout(docx_group)
        docx_layout.addWidget(self._build_docx_tab())
        layout.addWidget(docx_group)
        layout.addStretch()
        return tab

    def _build_roles_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        roles_group = QGroupBox("Роли проекта")
        roles_layout = QVBoxLayout(roles_group)
        roles_layout.addWidget(self._hint(
            "Список ролей собирается из назначений и текстов серий. В нём "
            "можно найти роль, увидеть серии появления, сбросить привязку к "
            "актёру или назначить другого актёра."
        ))
        self.btn_project_roles = QPushButton("Открыть роли проекта...")
        self.btn_project_roles.clicked.connect(self._open_project_roles)
        self.btn_project_roles.setEnabled(self._has_project_roles_dialog())
        roles_layout.addWidget(self.btn_project_roles)
        layout.addWidget(roles_group)
        layout.addStretch()
        return tab

    def _refresh_project_info(self) -> None:
        """Refresh project tab summary."""
        if not hasattr(self, "project_info_label"):
            return

        project_folder = (
            self.project_data.get("project_folder") or
            translate_source("не задана")
        )
        texts_count = len(self.project_data.get("episode_texts", {}))
        episodes_count = len(self.project_data.get("episodes", {}))
        self.project_info_label.setText(
            f"{translate_source('Папка проекта:')} {project_folder}\n"
            f"{translate_source('Серий:')} {episodes_count}\n"
            f"{translate_source('Рабочих текстов:')} {texts_count}"
        )
        if hasattr(self, "btn_clear_project_folder"):
            self.btn_clear_project_folder.setEnabled(bool(
                self.project_data.get("project_folder")
            ))

    def _set_project_folder(self) -> None:
        if self.main_window and hasattr(self.main_window, "set_project_folder_dialog"):
            self.main_window.set_project_folder_dialog()
            self._refresh_project_info()

    def _clear_project_folder(self) -> None:
        if self.main_window and hasattr(self.main_window, "clear_project_folder"):
            self.main_window.clear_project_folder()
            self._refresh_project_info()

    def _open_project_files(self) -> None:
        if self.main_window and hasattr(self.main_window, "open_project_files_dialog"):
            self.main_window.open_project_files_dialog()
            self._refresh_project_info()

    def _open_project_health(self) -> None:
        if self.main_window and hasattr(self.main_window, "open_project_health_dialog"):
            self.main_window.open_project_health_dialog()

    def _has_project_roles_dialog(self) -> bool:
        return bool(
            self.main_window is not None and
            hasattr(self.main_window, "open_project_roles_dialog")
        )

    def _open_project_roles(self) -> None:
        if self._has_project_roles_dialog():
            self.main_window.open_project_roles_dialog()
            self._refresh_project_info()

    def _build_actor_bases_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)

        if self.settings_scope == "global":
            layout.addWidget(self._hint(
                "Глобальная база хранит имена актёров и пол отдельно от "
                "проектов. Её можно перенести на другой компьютер или "
                "импортировать в другую установку Dubbing Manager."
            ))
        else:
            layout.addWidget(self._hint(
                "Здесь находятся операции переноса проектного распределения. "
                "В файл попадут актёры проекта, глобальные назначения "
                "персонажей и серийные назначения."
            ))

        if self.settings_scope == "global":
            actor_base_group = QGroupBox("Глобальная база актёров")
            actor_base_layout = QVBoxLayout(actor_base_group)
            actor_base_layout.addWidget(self._hint(
                "Используйте этот JSON как общую адресную книгу актёров. "
                "Цвета в глобальной базе не хранятся: они остаются настройкой "
                "конкретного проекта."
            ))
            actor_buttons = QHBoxLayout()
            btn_export_actor_base = QPushButton("Экспорт...")
            btn_export_actor_base.setToolTip(
                "Сохранить глобальную базу актёров в JSON-файл."
            )
            btn_export_actor_base.clicked.connect(self._export_global_actor_base)
            actor_buttons.addWidget(btn_export_actor_base)

            btn_import_actor_base = QPushButton("Импорт...")
            btn_import_actor_base.setToolTip(
                "Загрузить глобальную базу актёров из JSON-файла."
            )
            btn_import_actor_base.clicked.connect(self._import_global_actor_base)
            actor_buttons.addWidget(btn_import_actor_base)
            actor_base_layout.addLayout(actor_buttons)

            if not self._has_global_actor_base_service():
                actor_base_layout.addWidget(self._hint(
                    "Импорт и экспорт доступны из главного окна приложения."
                ))
                btn_export_actor_base.setEnabled(False)
                btn_import_actor_base.setEnabled(False)

            layout.addWidget(actor_base_group)
        else:
            assignment_group = QGroupBox("Распределение текущего проекта")
            assignment_layout = QVBoxLayout(assignment_group)
            assignment_layout.addWidget(self._hint(
                "Этот экспорт нужен для переноса кастинга в другой проект, "
                "например в новый сезон. В файл попадут актёры проекта, "
                "глобальные назначения персонажей и серийные назначения. "
                "При импорте актёры сопоставляются по имени, чтобы не плодить "
                "дубли."
            ))
            assignment_buttons = QHBoxLayout()
            btn_export_assignments = QPushButton("Экспорт...")
            btn_export_assignments.setToolTip(
                "Экспортировать актёров проекта и распределение ролей в JSON."
            )
            btn_export_assignments.clicked.connect(
                self._export_project_assignments
            )
            assignment_buttons.addWidget(btn_export_assignments)

            btn_import_assignments = QPushButton("Импорт...")
            btn_import_assignments.setToolTip(
                "Импортировать актёров проекта и распределение ролей из JSON."
            )
            btn_import_assignments.clicked.connect(
                self._import_project_assignments
            )
            assignment_buttons.addWidget(btn_import_assignments)
            assignment_layout.addLayout(assignment_buttons)

            if not self._has_project_assignment_service():
                assignment_layout.addWidget(self._hint(
                    "Импорт и экспорт распределения доступны из главного окна "
                    "приложения."
                ))
                btn_export_assignments.setEnabled(False)
                btn_import_assignments.setEnabled(False)

            layout.addWidget(assignment_group)
        layout.addStretch()
        return tab

    def _has_global_actor_base_service(self) -> bool:
        return bool(
            self.main_window is not None and
            hasattr(self.main_window, "global_settings_service") and
            hasattr(self.main_window, "global_settings")
        )

    def _has_project_assignment_service(self) -> bool:
        return bool(
            self.main_window is not None and
            hasattr(self.main_window, "assignment_transfer_service") and
            hasattr(self.main_window, "data")
        )

    def _export_global_actor_base(self) -> None:
        if not self._has_global_actor_base_service():
            return

        path, _ = QFileDialog.getSaveFileName(
            self,
            "Экспорт глобальной базы актёров",
            "global_actor_base.json",
            "JSON (*.json)"
        )
        if not path:
            return

        try:
            self.main_window.global_settings_service.export_global_actor_base(path)
        except Exception as e:
            QMessageBox.critical(
                self,
                "Ошибка",
                f"Не удалось экспортировать глобальную базу актёров:\n{e}"
            )
            return

        QMessageBox.information(
            self,
            "Готово",
            f"Глобальная база актёров сохранена:\n{path}"
        )

    def _import_global_actor_base(self) -> None:
        if not self._has_global_actor_base_service():
            return

        path, _ = QFileDialog.getOpenFileName(
            self,
            "Импорт глобальной базы актёров",
            "",
            "JSON (*.json)"
        )
        if not path:
            return

        try:
            stats = self.main_window.global_settings_service.import_global_actor_base(
                path
            )
            self.main_window.global_settings["global_actor_base"] = (
                self.main_window.global_settings_service.get_global_actor_base()
            )
            self.main_window.global_settings_service.save_settings(
                self.main_window.global_settings
            )
            if hasattr(self.main_window, "refresh_actor_list"):
                self.main_window.refresh_actor_list()
        except Exception as e:
            QMessageBox.critical(
                self,
                "Ошибка",
                f"Не удалось импортировать глобальную базу актёров:\n{e}"
            )
            return

        QMessageBox.information(
            self,
            "Готово",
            "Глобальная база актёров импортирована.\n\n"
            f"Добавлено: {stats.get('added', 0)}\n"
            f"Уже было: {stats.get('matched', 0)}"
        )

    def _export_project_assignments(self) -> None:
        if not self._has_project_assignment_service():
            return

        default_name = (
            f"{self.project_data.get('project_name', 'Project')} - "
            "распределение актёров.json"
        )
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Экспорт распределения актёров",
            default_name,
            "JSON (*.json)"
        )
        if not path:
            return

        try:
            self.main_window.assignment_transfer_service.save_export(
                self.main_window.data,
                path
            )
        except Exception as e:
            QMessageBox.critical(
                self,
                "Ошибка",
                f"Не удалось экспортировать распределение:\n{e}"
            )
            return

        QMessageBox.information(
            self,
            "Готово",
            f"Распределение актёров сохранено:\n{path}"
        )

    def _import_project_assignments(self) -> None:
        if not self._has_project_assignment_service():
            return

        path, _ = QFileDialog.getOpenFileName(
            self,
            "Импорт распределения актёров",
            "",
            "JSON (*.json)"
        )
        if not path:
            return

        reply = QMessageBox.question(
            self,
            "Импорт распределения актёров",
            "Импорт добавит актёров, которых нет в текущем проекте, "
            "и обновит назначения ролей. Продолжить?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes
        )
        if reply != QMessageBox.Yes:
            return

        try:
            stats = self.main_window.assignment_transfer_service.import_from_file(
                self.main_window.data,
                path
            )
            for actor_id, actor in self.main_window.data.get("actors", {}).items():
                self.main_window.global_settings_service.add_global_actor(
                    actor.get("name", actor_id),
                    gender=actor.get("gender", "")
                )
            self.main_window.global_settings["global_actor_base"] = (
                self.main_window.global_settings_service.get_global_actor_base()
            )
            self.main_window.global_settings_service.save_settings(
                self.main_window.global_settings
            )
            self.main_window.refresh_actor_list()
            self.main_window.refresh_main_table()
            self.main_window.set_dirty(True)
        except Exception as e:
            QMessageBox.critical(
                self,
                "Ошибка",
                f"Не удалось импортировать распределение:\n{e}"
            )
            return

        skipped = stats.get("skipped_episode_assignments", 0)
        skipped_text = (
            f"\nСерийных назначений пропущено: {skipped}"
            if skipped else ""
        )
        QMessageBox.information(
            self,
            "Готово",
            "Распределение импортировано.\n\n"
            f"Актёров добавлено: {stats.get('actors_added', 0)}\n"
            f"Актёров сопоставлено: {stats.get('actors_matched', 0)}\n"
            f"Глобальных назначений: {stats.get('global_assignments', 0)}\n"
            f"Серийных назначений: {stats.get('episode_assignments', 0)}"
            f"{skipped_text}"
        )

    def _open_prompter_colors(self) -> None:
        dialog = PrompterColorDialog(self.prompter_colors, self)
        if dialog.exec():
            self.prompter_colors = dialog.get_final_colors()

    def _get_prompter_color_presets(self) -> List[Optional[Dict[str, str]]]:
        if (
            self.main_window is not None and
            hasattr(self.main_window, "get_prompter_color_presets")
        ):
            return self.main_window.get_prompter_color_presets()
        return [None, None, None, None]

    def _update_prompter_color_preset_controls(self) -> None:
        if not hasattr(self, "prompter_preset_preview_buttons"):
            return

        presets = self._get_prompter_color_presets()
        for index, preview in enumerate(self.prompter_preset_preview_buttons):
            preset = presets[index] if index < len(presets) else None
            reset = self.prompter_preset_reset_buttons[index]
            if preset:
                bg = preset.get("bg", "#000000")
                text = preset.get("active_text", "#ffffff")
                preview.setText(f"Фон {bg} / Текст {text}")
                preview.setStyleSheet(
                    f"background-color: {bg}; color: {text}; "
                    "border: 1px solid #777; border-radius: 4px;"
                )
                reset.setEnabled(True)
            else:
                preview.setText("Пусто")
                preview.setStyleSheet(
                    "color: #666; border: 1px dashed #999; border-radius: 4px;"
                )
                reset.setEnabled(False)

    def _clear_prompter_color_preset(self, index: int) -> None:
        if (
            self.main_window is None or
            not hasattr(self.main_window, "clear_prompter_color_preset")
        ):
            return

        answer = QMessageBox.question(
            self,
            "Сбросить пресет?",
            f"Пресет цветовой схемы {index + 1} будет очищен. Продолжить?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            return

        if self.main_window.clear_prompter_color_preset(index):
            self._update_prompter_color_preset_controls()

    def _has_export_defaults_service(self) -> bool:
        return (
            self.main_window is not None and
            hasattr(self.main_window, "save_default_export_config") and
            hasattr(self.main_window, "apply_default_export_config_to_project")
        )

    def _has_export_apply_service(self) -> bool:
        return (
            self.main_window is not None and
            hasattr(self.main_window, "apply_export_config_to_project")
        )

    def _has_prompter_defaults_service(self) -> bool:
        return (
            self.main_window is not None and
            hasattr(self.main_window, "save_default_prompter_config") and
            hasattr(self.main_window, "apply_default_prompter_config_to_project")
        )

    def _has_prompter_apply_service(self) -> bool:
        return (
            self.main_window is not None and
            hasattr(self.main_window, "apply_prompter_config_to_project")
        )

    def _update_table_width_controls_visibility(self) -> None:
        if hasattr(self, "table_widths_group"):
            self.table_widths_group.setVisible(
                self.export_layout_type.currentData() == "Таблица"
            )

    def _current_export_config(self) -> Dict[str, Any]:
        export_config = deepcopy(self.export_config)
        export_config.update({
            "layout_type": self.export_layout_type.currentData(),
            "format_html": self.export_format_html.isChecked(),
            "format_xls": self.export_format_xls.isChecked(),
            "format_docx": self.export_format_docx.isChecked(),
            "format_pdf": self.export_format_pdf.isChecked(),
            "col_tc": self.export_col_tc.isChecked(),
            "col_char": self.export_col_char.isChecked(),
            "col_actor": self.export_col_actor.isChecked(),
            "col_text": self.export_col_text.isChecked(),
            "f_time": self.export_f_time.value(),
            "f_char": self.export_f_char.value(),
            "f_actor": self.export_f_actor.value(),
            "f_text": self.export_f_text.value(),
            "table_width_time": self.export_table_width_time.value(),
            "table_width_char": self.export_table_width_char.value(),
            "table_width_actor": self.export_table_width_actor.value(),
            "use_color": self.export_use_color.isChecked(),
            "soften_colors": self.export_soften_colors.isChecked(),
            "allow_edit": self.export_allow_edit.isChecked(),
            "round_time": self.export_round_time.isChecked(),
            "time_display": self.export_time_display.currentData(),
            "open_auto": self.export_open_auto.isChecked(),
            "highlight_ids_export": deepcopy(self.highlight_ids_export or []),
            "highlight_negative_ids_export": deepcopy(
                self.highlight_negative_ids_export or []
            ),
        })
        return export_config

    def _set_export_config_controls(self, config: Dict[str, Any]) -> None:
        export_config = deepcopy(DEFAULT_EXPORT_CONFIG)
        export_config.update(config or {})
        self.export_config = export_config

        layout_type = export_config.get("layout_type", "Таблица")
        if layout_type == "Сценарий":
            layout_type = "Сценарий 1"
        layout_index = self.export_layout_type.findData(layout_type)
        self.export_layout_type.setCurrentIndex(
            layout_index if layout_index >= 0 else 0
        )
        self.export_format_html.setChecked(
            export_config.get("format_html", True)
        )
        self.export_format_xls.setChecked(
            export_config.get("format_xls", False)
        )
        self.export_format_docx.setChecked(
            export_config.get("format_docx", False)
        )
        self.export_format_pdf.setChecked(
            export_config.get("format_pdf", False)
        )
        self.export_col_tc.setChecked(export_config.get("col_tc", True))
        self.export_col_char.setChecked(export_config.get("col_char", True))
        self.export_col_actor.setChecked(export_config.get("col_actor", True))
        self.export_col_text.setChecked(export_config.get("col_text", True))
        self.export_f_time.setValue(export_config.get("f_time", 21))
        self.export_f_char.setValue(export_config.get("f_char", 20))
        self.export_f_actor.setValue(export_config.get("f_actor", 14))
        self.export_f_text.setValue(export_config.get("f_text", 30))
        self.export_table_width_time.setValue(
            export_config.get("table_width_time", 7.0)
        )
        self.export_table_width_char.setValue(
            export_config.get("table_width_char", 10.0)
        )
        self.export_table_width_actor.setValue(
            export_config.get("table_width_actor", 8.5)
        )
        self.export_use_color.setChecked(export_config.get("use_color", True))
        self.export_soften_colors.setChecked(
            export_config.get("soften_colors", True)
        )
        self.export_allow_edit.setChecked(export_config.get("allow_edit", True))
        self.export_round_time.setChecked(export_config.get("round_time", False))
        self.export_open_auto.setChecked(export_config.get("open_auto", True))

        time_display_index = self.export_time_display.findData(
            export_config.get("time_display", "range")
        )
        self.export_time_display.setCurrentIndex(
            time_display_index if time_display_index >= 0 else 0
        )
        self.highlight_ids_export = deepcopy(
            export_config.get("highlight_ids_export", [])
        )
        self.highlight_negative_ids_export = deepcopy(
            export_config.get("highlight_negative_ids_export", [])
        )
        self._update_table_width_controls_visibility()
        self._update_export_actor_filter_summary()

    def _current_prompter_config(self) -> Dict[str, Any]:
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
            "osc_enabled": self.prompter_osc_enabled.isChecked(),
            "sync_in": self.prompter_sync_in.isChecked(),
            "sync_out": self.prompter_sync_out.isChecked(),
            "reaper_offset_enabled": self.prompter_offset_enabled.isChecked(),
            "reaper_offset_seconds": self.prompter_offset_seconds.value(),
            "scroll_smoothness_slider": self.prompter_smoothness.value(),
            "colors": deepcopy(self.prompter_colors),
        })
        return prompter_config

    def _set_prompter_config_controls(self, config: Dict[str, Any]) -> None:
        prompter_config = deepcopy(DEFAULT_PROMPTER_CONFIG)
        prompter_config.update(config or {})
        prompter_colors = deepcopy(DEFAULT_PROMPTER_CONFIG["colors"])
        prompter_colors.update(prompter_config.get("colors", {}))
        prompter_config["colors"] = prompter_colors
        self.prompter_config = prompter_config
        self.prompter_colors = prompter_colors

        self.prompter_f_tc.setValue(prompter_config.get("f_tc", 20))
        self.prompter_f_char.setValue(prompter_config.get("f_char", 24))
        self.prompter_f_actor.setValue(prompter_config.get("f_actor", 18))
        self.prompter_f_text.setValue(prompter_config.get("f_text", 36))
        self.prompter_focus_ratio.setValue(
            prompter_config.get("focus_ratio", 0.5)
        )
        self.prompter_smoothness.setValue(
            prompter_config.get("scroll_smoothness_slider", 18)
        )
        self.prompter_mirrored.setChecked(
            prompter_config.get("is_mirrored", False)
        )
        self.prompter_show_header.setChecked(
            prompter_config.get("show_header", False)
        )
        self.prompter_port_in.setValue(prompter_config.get("port_in", 8000))
        self.prompter_port_out.setValue(prompter_config.get("port_out", 9000))
        self.prompter_osc_enabled.setChecked(
            prompter_config.get("osc_enabled", False)
        )
        self.prompter_sync_in.setChecked(
            prompter_config.get("sync_in", True)
        )
        self.prompter_sync_out.setChecked(
            prompter_config.get("sync_out", False)
        )
        self.prompter_offset_enabled.setChecked(
            prompter_config.get("reaper_offset_enabled", False)
        )
        self.prompter_offset_seconds.setValue(
            prompter_config.get("reaper_offset_seconds", -2.0)
        )

    def _save_export_defaults(self) -> None:
        if not self._has_export_defaults_service():
            return

        answer = QMessageBox.question(
            self,
            "Сохранить по умолчанию?",
            "Текущие настройки монтажного листа будут использоваться для "
            "новых проектов. Старые проекты сохранят свои настройки. "
            "Продолжить?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            return

        if self.main_window.save_default_export_config(
            self._current_export_config()
        ):
            QMessageBox.information(
                self,
                "Готово",
                "Настройки монтажного листа сохранены по умолчанию."
            )
        else:
            QMessageBox.warning(
                self,
                "Не удалось сохранить",
                "Настройки по умолчанию не были записаны."
            )

    def _apply_export_defaults_to_project(self) -> None:
        if not self._has_export_defaults_service():
            return

        answer = QMessageBox.question(
            self,
            "Сделать по умолчанию?",
            "Настройки монтажного листа текущего проекта будут заменены "
            "сохранёнными настройками по умолчанию. Продолжить?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            return

        export_config = self.main_window.apply_default_export_config_to_project()
        self._set_export_config_controls(export_config)
        QMessageBox.information(
            self,
            "Готово",
            "К текущему проекту применены настройки монтажного листа по "
            "умолчанию."
        )

    def _apply_global_export_to_project(self) -> None:
        if not self._has_export_apply_service():
            return

        answer = QMessageBox.question(
            self,
            "Перенести настройки?",
            "Настройки монтажного листа из глобальных настроек будут "
            "применены к текущему проекту. Продолжить?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            return

        export_config = self.main_window.apply_export_config_to_project(
            self._current_export_config()
        )
        self._set_export_config_controls(export_config)
        QMessageBox.information(
            self,
            "Готово",
            "Настройки монтажного листа применены к текущему проекту."
        )

    def _save_prompter_defaults(self) -> None:
        if not self._has_prompter_defaults_service():
            return

        answer = QMessageBox.question(
            self,
            "Сохранить по умолчанию?",
            "Текущие настройки телесуфлёра будут использоваться для новых "
            "проектов. Старые проекты сохранят свои настройки. Продолжить?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            return

        if self.main_window.save_default_prompter_config(
            self._current_prompter_config()
        ):
            QMessageBox.information(
                self,
                "Готово",
                "Настройки телесуфлёра сохранены по умолчанию."
            )
        else:
            QMessageBox.warning(
                self,
                "Не удалось сохранить",
                "Настройки по умолчанию не были записаны."
            )

    def _apply_prompter_defaults_to_project(self) -> None:
        if not self._has_prompter_defaults_service():
            return

        answer = QMessageBox.question(
            self,
            "Сделать по умолчанию?",
            "Настройки телесуфлёра текущего проекта будут заменены "
            "сохранёнными настройками по умолчанию. Продолжить?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            return

        prompter_config = (
            self.main_window.apply_default_prompter_config_to_project()
        )
        self._set_prompter_config_controls(prompter_config)
        QMessageBox.information(
            self,
            "Готово",
            "К текущему проекту применены настройки телесуфлёра по умолчанию."
        )

    def _apply_global_prompter_to_project(self) -> None:
        if not self._has_prompter_apply_service():
            return

        answer = QMessageBox.question(
            self,
            "Перенести настройки?",
            "Настройки телесуфлёра из глобальных настроек будут применены к "
            "текущему проекту. Продолжить?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            return

        prompter_config = self.main_window.apply_prompter_config_to_project(
            self._current_prompter_config()
        )
        self._set_prompter_config_controls(prompter_config)
        QMessageBox.information(
            self,
            "Готово",
            "Настройки телесуфлёра применены к текущему проекту."
        )

    def get_settings(self) -> Dict[str, Dict[str, Any]]:
        """Return settings."""
        if self.settings_scope == "global":
            return {
                "language": self.language_combo.currentData(),
                "default_export_config": self._current_export_config(),
                "default_prompter_config": self._current_prompter_config(),
            }

        export_config = self._current_export_config()

        fps = self.merge_fps.value()
        merge_config = deepcopy(self.merge_config)
        merge_config.update({
            "merge": self.merge_enabled.isChecked(),
            "merge_gap": int(self.merge_gap.value() * fps),
            "fps": fps,
            "p_short": self.merge_p_short.value(),
            "p_long": self.merge_p_long.value(),
        })

        prompter_config = self._current_prompter_config()

        docx_config = deepcopy(self.docx_config)
        docx_config["time_separators"] = self._parse_separators(
            self.docx_time_separators.text()
        )

        return {
            "project_name": self.project_name_edit.text().strip() or translate_source("Новый проект"),
            "metadata": {
                "created_by": self.project_created_by_edit.text().strip(),
                "studio": self.project_studio_edit.text().strip(),
            },
            "export_config": export_config,
            "replica_merge_config": merge_config,
            "prompter_config": prompter_config,
            "docx_import_config": docx_config,
        }

    def _parse_separators(self, text: str) -> List[str]:
        return parse_separators(text)

    def _select_initial_tab(self) -> None:
        aliases = {
            "docx": "series_files",
            "files": "series_files",
            "health": "series_files",
            "project_roles": "roles",
        }
        key = aliases.get(self.initial_tab, self.initial_tab)
        self.tabs.setCurrentIndex(self._tab_indexes.get(key, 0))

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

        dialog = ActorFilterDialog(
            actors,
            current_selection,
            self.highlight_negative_ids_export,
            self
        )
        if dialog.exec():
            selected = dialog.get_selected()
            self.highlight_negative_ids_export = dialog.get_negative_selected()
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
        if self.highlight_negative_ids_export:
            negative_names = [
                actors.get(actor_id, {}).get("name", actor_id)
                for actor_id in self.highlight_negative_ids_export
            ]
            text += "\nНегатив: " + ", ".join(negative_names)
        self.export_actor_filter_summary.setText(text)

    def _hint(self, text: str) -> QLabel:
        return hint_label(text)

    def _check_box(self, text: str, checked: bool) -> QCheckBox:
        return check_box(text, checked)

    def _spin(self, minimum: int, maximum: int, value: Any) -> QSpinBox:
        return int_spin(minimum, maximum, value)

    def _double_spin(
        self,
        minimum: float,
        maximum: float,
        value: Any,
        step: float = 1.0,
        decimals: int = 1
    ) -> QDoubleSpinBox:
        return double_spin(minimum, maximum, value, step, decimals)
