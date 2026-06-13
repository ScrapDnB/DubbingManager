"""Episode preview window."""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QComboBox, QDoubleSpinBox, QSpinBox, QGroupBox, QFormLayout,
    QFrame, QCheckBox, QFileDialog, QMessageBox, QRadioButton
)
from PySide6.QtCore import Qt
from PySide6.QtWebChannel import QWebChannel
from typing import Dict, List, Any, Optional
import logging
import sys

try:
    from PySide6.QtWebEngineWidgets import QWebEngineView
    WEB_ENGINE_AVAILABLE = True
except ImportError:
    from PySide6.QtWidgets import QTextBrowser as QWebEngineView
    WEB_ENGINE_AVAILABLE = False

from config.constants import (
    PREVIEW_WINDOW_WIDTH,
    PREVIEW_WINDOW_HEIGHT,
    PREVIEW_SETTINGS_PANEL_WIDTH,
)
from utils.helpers import hex_to_rgba_string, log_exception, natural_sort_key
from utils.i18n import translate_source, translate_widget_tree
from utils.web_bridge import WebBridge
from services import ExportService
from .preview_helpers import (
    apply_preview_settings,
    build_preview_project_data,
    get_export_highlight_ids,
    get_export_negative_ids,
)
from .dialogs.actor_filter import ActorFilterDialog

logger = logging.getLogger(__name__)


class HtmlLivePreview(QDialog):
    """Html Live Preview class."""

    # Class attributes
    main_app: Any
    ep_num: str
    highlight_ids: Optional[List[str]]
    _has_text_changes: bool

    def __init__(
        self,
        main_app: Any,
        ep_num: str,
        override_lines: Optional[List[Dict[str, Any]]] = None,
        source_title: Optional[str] = None,
        register_preview: bool = True
    ) -> None:
        super().__init__(None)
        self.main_app: Any = main_app
        self.ep_num: str = ep_num
        self.override_lines = override_lines
        self.source_title = source_title
        self.register_preview = register_preview
        self._update_window_title()
        self.resize(PREVIEW_WINDOW_WIDTH, PREVIEW_WINDOW_HEIGHT)

        self.highlight_ids = self._get_export_highlight_ids()
        self.highlight_negative_ids = self._get_export_negative_ids()
        self._has_text_changes: bool = False

        self._init_ui()
        translate_widget_tree(self)

        try:
            self.browser.loadFinished.connect(self.on_page_loaded)
        except Exception as e:
            logger.error(f"Failed to connect loadFinished signal: {e}")
        
        if self.register_preview:
            self.main_app.preview_window = self

        if WEB_ENGINE_AVAILABLE:
            try:
                self.channel: QWebChannel = QWebChannel()
                self.bridge: WebBridge = WebBridge(self.main_app)
                self.channel.registerObject("backend", self.bridge)
                self.browser.page().setWebChannel(self.channel)
                logger.info("WebChannel initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize WebChannel: {e}")
        else:
            logger.warning("WebEngine not available, using QTextBrowser")

        logger.info(f"HtmlLivePreview initialized for ep={ep_num}")
        self.update_preview()

    def _init_ui(self) -> None:
        """Init ui."""
        self.root_layout: QVBoxLayout = QVBoxLayout(self)

        self.nav_panel: QHBoxLayout = QHBoxLayout()

        self.btn_toggle_sidebar = QPushButton("⬅ Скрыть настройки")
        self.btn_toggle_sidebar.setCheckable(True)
        self.btn_toggle_sidebar.clicked.connect(self.toggle_sidebar)

        self.nav_panel.addWidget(self.btn_toggle_sidebar)
        self.nav_panel.addWidget(QLabel("Серия:"))
        self.combo_episode = QComboBox()
        self._populate_episode_combo()
        self.combo_episode.currentIndexChanged.connect(self.on_episode_change)
        self.nav_panel.addWidget(self.combo_episode)
        self.nav_panel.addStretch()

        self.root_layout.addLayout(self.nav_panel)

        self.content_layout: QHBoxLayout = QHBoxLayout()
        self.root_layout.addLayout(self.content_layout)

        self.settings_panel = QFrame()
        self.settings_panel.setFixedWidth(PREVIEW_SETTINGS_PANEL_WIDTH)
        self.settings_panel.setFrameShape(QFrame.StyledPanel)
        sp_layout: QVBoxLayout = QVBoxLayout(self.settings_panel)

        sp_layout.addWidget(QLabel("<b>Настройки вида</b>"))

        self.combo_layout = QComboBox()
        self.combo_layout.addItem(translate_source("Таблица"), "Таблица")
        self.combo_layout.addItem("Сценарий 1", "Сценарий 1")
        self.combo_layout.addItem("Сценарий 2", "Сценарий 2")
        self.combo_layout.addItem("Сценарий 3", "Сценарий 3")
        current_type: str = self.main_app.data["export_config"].get(
            "layout_type", "Таблица"
        )
        if current_type == "Сценарий":
            current_type = "Сценарий 1"
        index = self.combo_layout.findData(current_type)
        self.combo_layout.setCurrentIndex(index if index >= 0 else 0)
        self.combo_layout.currentIndexChanged.connect(self.on_setting_change)
        sp_layout.addWidget(QLabel("Формат:"))
        sp_layout.addWidget(self.combo_layout)
        sp_layout.addSpacing(10)

        columns_group = QGroupBox("Колонки и время")
        columns_layout = QVBoxLayout(columns_group)
        cfg = self.main_app.data["export_config"]
        self.chk_col_tc = self._preview_check_box(
            "Тайминг", cfg.get("col_tc", True)
        )
        self.chk_col_char = self._preview_check_box(
            "Имя персонажа", cfg.get("col_char", True)
        )
        self.chk_col_actor = self._preview_check_box(
            "Актёр", cfg.get("col_actor", True)
        )
        self.chk_col_text = self._preview_check_box(
            "Текст реплики", cfg.get("col_text", True)
        )
        self.chk_round_time = self._preview_check_box(
            "Округлять время", cfg.get("round_time", False)
        )
        self.combo_time_display = QComboBox()
        self.combo_time_display.addItem(translate_source("Начало и конец"), "range")
        self.combo_time_display.addItem(translate_source("Только начало"), "start")
        time_display_index = self.combo_time_display.findData(
            cfg.get("time_display", "range")
        )
        if time_display_index < 0:
            time_display_index = 0
        self.combo_time_display.setCurrentIndex(time_display_index)
        self.combo_time_display.currentIndexChanged.connect(self.on_setting_change)
        for checkbox in [
            self.chk_col_tc,
            self.chk_col_char,
            self.chk_col_actor,
            self.chk_col_text,
        ]:
            columns_layout.addWidget(checkbox)
        columns_layout.addWidget(QLabel("Тайминг:"))
        columns_layout.addWidget(self.combo_time_display)
        columns_layout.addWidget(self.chk_round_time)
        sp_layout.addWidget(columns_group)
        
        font_group = QGroupBox("Размеры шрифтов")
        fg_layout = QFormLayout(font_group)
        
        self.s_time = QSpinBox()
        self.s_time.setRange(6, 48)
        self.s_time.setValue(
            self.main_app.data["export_config"].get("f_time", 12)
        )
        self.s_time.valueChanged.connect(self.on_setting_change)
        
        self.s_char = QSpinBox()
        self.s_char.setRange(6, 48)
        self.s_char.setValue(
            self.main_app.data["export_config"].get("f_char", 14)
        )
        self.s_char.valueChanged.connect(self.on_setting_change)
        
        self.s_actor = QSpinBox()
        self.s_actor.setRange(6, 48)
        self.s_actor.setValue(
            self.main_app.data["export_config"].get("f_actor", 14)
        )
        self.s_actor.valueChanged.connect(self.on_setting_change)
        
        self.s_text = QSpinBox()
        self.s_text.setRange(6, 48)
        self.s_text.setValue(
            self.main_app.data["export_config"].get("f_text", 16)
        )
        self.s_text.valueChanged.connect(self.on_setting_change)
        
        fg_layout.addRow("Таймкод:", self.s_time)
        fg_layout.addRow("Персонаж:", self.s_char)
        fg_layout.addRow("Актер:", self.s_actor)
        fg_layout.addRow("Текст:", self.s_text)
        sp_layout.addWidget(font_group)

        self.table_widths_group = QGroupBox("Ширина колонок таблицы")
        widths_layout = QFormLayout(self.table_widths_group)
        self.s_width_time = self._width_spin(
            cfg.get("table_width_time", 7.0)
        )
        self.s_width_char = self._width_spin(
            cfg.get("table_width_char", 10.0)
        )
        self.s_width_actor = self._width_spin(
            cfg.get("table_width_actor", 8.5)
        )
        widths_layout.addRow("Тайминг:", self.s_width_time)
        widths_layout.addRow("Персонаж:", self.s_width_char)
        widths_layout.addRow("Актер:", self.s_width_actor)
        sp_layout.addWidget(self.table_widths_group)
        self._update_table_width_controls_visibility()
        
        filter_group = QGroupBox("Подсветка")
        f_lay = QVBoxLayout(filter_group)
        self.chk_soften_colors = self._preview_check_box(
            "Смягчить цвета",
            cfg.get("soften_colors", True)
        )
        f_lay.addWidget(self.chk_soften_colors)
        btn_filter = QPushButton("Выбрать актеров...")
        btn_filter.clicked.connect(self.open_actor_filter)
        f_lay.addWidget(btn_filter)
        sp_layout.addWidget(filter_group)

        export_group = QGroupBox("Экспорт")
        export_layout = QVBoxLayout(export_group)
        formats_layout = QHBoxLayout()
        self.chk_exp_html = QCheckBox("HTML")
        self.chk_exp_html.setChecked(cfg.get("format_html", True))
        self.chk_exp_xls = QCheckBox("XLSX")
        self.chk_exp_xls.setChecked(cfg.get("format_xls", False))
        self.chk_exp_docx = QCheckBox("DOCX")
        self.chk_exp_docx.setChecked(cfg.get("format_docx", False))
        self.chk_exp_pdf = QCheckBox("PDF")
        self.chk_exp_pdf.setChecked(cfg.get("format_pdf", False))
        self.chk_exp_html.toggled.connect(self._update_export_format_config)
        self.chk_exp_xls.toggled.connect(self._update_export_format_config)
        self.chk_exp_docx.toggled.connect(self._update_export_format_config)
        self.chk_exp_pdf.toggled.connect(self._update_export_format_config)
        formats_layout.addWidget(self.chk_exp_html)
        formats_layout.addWidget(self.chk_exp_xls)
        formats_layout.addWidget(self.chk_exp_docx)
        formats_layout.addWidget(self.chk_exp_pdf)
        export_layout.addLayout(formats_layout)

        scope_layout = QHBoxLayout()
        self.radio_current_episode = QRadioButton("Текущая серия")
        self.radio_current_episode.setChecked(True)
        self.radio_all_episodes = QRadioButton("Все серии")
        scope_layout.addWidget(self.radio_current_episode)
        scope_layout.addWidget(self.radio_all_episodes)
        export_layout.addLayout(scope_layout)

        self.btn_export = QPushButton("Экспортировать")
        self.btn_export.clicked.connect(self.run_export)
        export_layout.addWidget(self.btn_export)
        if self.override_lines is not None:
            self.radio_current_episode.hide()
            self.radio_all_episodes.hide()
            self.btn_export.hide()
        sp_layout.addWidget(export_group)
        sp_layout.addStretch()
        
        btn_close = QPushButton("Закрыть")
        btn_close.clicked.connect(self.close)
        sp_layout.addWidget(btn_close)
        
        self.content_layout.addWidget(self.settings_panel)
        
        self.browser = QWebEngineView()
        if not WEB_ENGINE_AVAILABLE:
            self.browser.setOpenExternalLinks(False)
        self.content_layout.addWidget(self.browser)

    def _update_window_title(self) -> None:
        if self.override_lines is not None:
            title = self.source_title or translate_source("Быстрый конвертер")
            self.setWindowTitle(f"{translate_source('Монтажный лист:')} {title}")
            return
        self.setWindowTitle(
            f"{translate_source('Монтажный лист:')} "
            f"{translate_source('Серия')} {self.ep_num}"
        )

    def _populate_episode_combo(self) -> None:
        """Populate the preview episode selector."""
        if self.override_lines is not None:
            self.combo_episode.blockSignals(True)
            self.combo_episode.clear()
            self.combo_episode.addItem(
                self.source_title or translate_source("Файл"),
                self.ep_num
            )
            self.combo_episode.setEnabled(False)
            self.combo_episode.blockSignals(False)
            return

        episodes = self.main_app.data.get("episodes", {})
        episode_numbers = sorted(
            {str(ep) for ep in episodes.keys()} | {str(self.ep_num)},
            key=natural_sort_key,
        )
        self.combo_episode.blockSignals(True)
        self.combo_episode.clear()
        for ep in episode_numbers:
            self.combo_episode.addItem(f"Серия {ep}", ep)
        index = self.combo_episode.findData(str(self.ep_num))
        self.combo_episode.setCurrentIndex(index if index >= 0 else 0)
        self.combo_episode.blockSignals(False)

    def on_episode_change(self) -> None:
        """Switch the montage sheet preview to another episode."""
        if self.override_lines is not None:
            return
        ep = self.combo_episode.currentData()
        if not ep or str(ep) == str(self.ep_num):
            return
        self.ep_num = str(ep)
        self._update_window_title()
        if hasattr(self.main_app, "switch_to_episode"):
            self.main_app.switch_to_episode(self.ep_num)
        self.update_preview()

    def run_export(self) -> None:
        """Export the montage sheet from this window."""
        do_html = self.chk_exp_html.isChecked()
        do_xls = self.chk_exp_xls.isChecked()
        do_docx = self.chk_exp_docx.isChecked()
        do_pdf = self.chk_exp_pdf.isChecked()
        if not (do_html or do_xls or do_docx or do_pdf):
            QMessageBox.information(
                self,
                "Экспорт",
                "Выберите хотя бы один формат."
            )
            return

        if self.radio_all_episodes.isChecked():
            episodes = self.main_app.data.get("episodes", {})
        else:
            episodes = {
                self.ep_num: self.main_app.data.get("episodes", {}).get(
                    self.ep_num
                )
            }

        if not episodes or None in episodes.values():
            QMessageBox.warning(self, "Экспорт", "Нет серий для экспорта.")
            return

        selected_count = sum([do_html, do_xls, do_docx, do_pdf])
        if self.radio_all_episodes.isChecked() or selected_count > 1:
            folder = QFileDialog.getExistingDirectory(
                self,
                "Выберите папку"
            )
            if folder:
                self.main_app._execute_batch_export(
                    episodes,
                    do_html,
                    do_xls,
                    do_docx,
                    do_pdf,
                    folder
                )
            return

        ep = next(iter(episodes.keys()))
        if do_html:
            self.main_app.export_to_html(ep)
        elif do_xls:
            self.main_app.export_to_excel(ep)
        elif do_docx:
            self.main_app.export_to_docx(ep)
        else:
            self.main_app.export_to_pdf(ep)

    def _preview_check_box(self, text: str, checked: bool) -> QCheckBox:
        """Create a preview settings checkbox."""
        checkbox = QCheckBox(text)
        checkbox.setChecked(bool(checked))
        checkbox.toggled.connect(self.on_setting_change)
        return checkbox

    def _width_spin(self, value: Any) -> QDoubleSpinBox:
        """Create a table column width control."""
        spin = QDoubleSpinBox()
        spin.setRange(4.0, 24.0)
        spin.setSingleStep(0.5)
        spin.setDecimals(1)
        spin.setSuffix(" ед.")
        spin.setValue(float(value))
        spin.valueChanged.connect(self.on_setting_change)
        return spin

    def _update_table_width_controls_visibility(self) -> None:
        if hasattr(self, "table_widths_group"):
            self.table_widths_group.setVisible(
                self.combo_layout.currentData() == "Таблица"
            )

    def _update_export_format_config(self) -> None:
        """Persist selected export formats and sync main controls."""
        cfg = self.main_app.data.setdefault("export_config", {})
        cfg["format_html"] = self.chk_exp_html.isChecked()
        cfg["format_xls"] = self.chk_exp_xls.isChecked()
        cfg["format_docx"] = self.chk_exp_docx.isChecked()
        cfg["format_pdf"] = self.chk_exp_pdf.isChecked()
        if hasattr(self.main_app, "_sync_export_format_controls_from_config"):
            self.main_app._sync_export_format_controls_from_config()
        self._save_export_settings()

    def sync_export_format_controls(self) -> None:
        """Sync export format controls from the project settings."""
        if not hasattr(self, "chk_exp_html"):
            return
        cfg = self.main_app.data.get("export_config", {})
        controls = [
            (self.chk_exp_html, cfg.get("format_html", True)),
            (self.chk_exp_xls, cfg.get("format_xls", False)),
            (self.chk_exp_docx, cfg.get("format_docx", False)),
            (self.chk_exp_pdf, cfg.get("format_pdf", False)),
        ]
        for checkbox, checked in controls:
            checkbox.blockSignals(True)
            checkbox.setChecked(bool(checked))
            checkbox.blockSignals(False)

    def sync_export_settings(self, update_preview: bool = True) -> None:
        """Sync preview controls from the project's export settings."""
        cfg = self.main_app.data["export_config"]
        widgets = [
            self.combo_layout,
            self.chk_col_tc,
            self.chk_col_char,
            self.chk_col_actor,
            self.chk_col_text,
            self.chk_round_time,
            self.combo_time_display,
            self.s_time,
            self.s_char,
            self.s_actor,
            self.s_text,
            self.s_width_time,
            self.s_width_char,
            self.s_width_actor,
            self.chk_soften_colors,
        ]
        if hasattr(self, "chk_exp_html"):
            widgets.extend([
                self.chk_exp_html,
                self.chk_exp_xls,
                self.chk_exp_docx,
                self.chk_exp_pdf,
            ])
        for widget in widgets:
            widget.blockSignals(True)

        layout_index = self.combo_layout.findData(
            cfg.get("layout_type", "Таблица")
        )
        if layout_index < 0 and cfg.get("layout_type") == "Сценарий":
            layout_index = self.combo_layout.findData("Сценарий 1")
        self.combo_layout.setCurrentIndex(layout_index if layout_index >= 0 else 0)
        self.chk_col_tc.setChecked(cfg.get("col_tc", True))
        self.chk_col_char.setChecked(cfg.get("col_char", True))
        self.chk_col_actor.setChecked(cfg.get("col_actor", True))
        self.chk_col_text.setChecked(cfg.get("col_text", True))
        self.chk_round_time.setChecked(cfg.get("round_time", False))
        time_display_index = self.combo_time_display.findData(
            cfg.get("time_display", "range")
        )
        self.combo_time_display.setCurrentIndex(
            time_display_index if time_display_index >= 0 else 0
        )
        self.s_time.setValue(cfg.get("f_time", 12))
        self.s_char.setValue(cfg.get("f_char", 14))
        self.s_actor.setValue(cfg.get("f_actor", 14))
        self.s_text.setValue(cfg.get("f_text", 16))
        self.s_width_time.setValue(cfg.get("table_width_time", 7.0))
        self.s_width_char.setValue(cfg.get("table_width_char", 10.0))
        self.s_width_actor.setValue(cfg.get("table_width_actor", 8.5))
        self.chk_soften_colors.setChecked(cfg.get("soften_colors", True))
        if hasattr(self, "chk_exp_html"):
            self.chk_exp_html.setChecked(cfg.get("format_html", True))
            self.chk_exp_xls.setChecked(cfg.get("format_xls", False))
            self.chk_exp_docx.setChecked(cfg.get("format_docx", False))
            self.chk_exp_pdf.setChecked(cfg.get("format_pdf", False))

        for widget in widgets:
            widget.blockSignals(False)

        self.highlight_ids = self._get_export_highlight_ids()
        self.highlight_negative_ids = self._get_export_negative_ids()
        self._update_table_width_controls_visibility()

        if update_preview:
            self.update_preview()
    
    def on_page_loaded(self, ok: bool) -> None:
        """Handle page loaded."""
        pass

    def update_preview(self) -> None:
        """Update preview."""
        try:
            logger.info(f"update_preview: ep={self.ep_num}")

            lines = self._get_preview_lines()
            logger.info(f"update_preview: lines={len(lines) if lines else 0}")
            
            if not lines:
                self.browser.setHtml(f"<h3>{translate_source('Нет данных в серии')}</h3>")
                return

            try:
                self.browser.loadFinished.disconnect(self.on_page_loaded)
            except Exception:
                pass

            self.browser.loadFinished.connect(self.on_page_loaded)

            preview_data = self._get_preview_project_data()
            cfg = preview_data["export_config"]
            merge_cfg = preview_data.get("replica_merge_config", {})
            local_layout = self.combo_layout.currentData()

            logger.info(f"update_preview: generating HTML with layout={local_layout}")

            export_service = ExportService(preview_data)
            processed = export_service.process_merge_logic(lines, merge_cfg)
            logger.info(f"update_preview: processed={len(processed)} replicas")

            html = export_service.generate_html(
                self.ep_num,
                processed,
                cfg,
                self.highlight_ids,
                layout_type=local_layout,
                is_editable=cfg.get('allow_edit', True)
            )
            
            logger.info(f"update_preview: HTML generated ({len(html)} bytes)")
            self.browser.setHtml(html)
            
        except Exception as e:
            logger.error(f"update_preview failed: {e}", exc_info=True)
            self.browser.setHtml(f"<h3>{translate_source('Ошибка')}: {e}</h3>")

    def _get_preview_lines(self) -> List[Dict[str, Any]]:
        """Return lines for regular or temporary quick-converter preview."""
        if self.override_lines is not None:
            return self.override_lines
        return self.main_app.get_episode_lines(self.ep_num)

    def _get_preview_project_data(self) -> Dict[str, Any]:
        """Return project data to use for rendering the preview."""
        return build_preview_project_data(
            self.main_app.data,
            self.override_lines is not None
        )
    
    def toggle_sidebar(self) -> None:
        """Toggle sidebar."""
        is_hidden = self.settings_panel.isVisible()
        self.settings_panel.setVisible(not is_hidden)
        
        if is_hidden:
            self.btn_toggle_sidebar.setText(
                "➡ " + translate_source("Показать настройки")
            )
        else:
            self.btn_toggle_sidebar.setText(
                "⬅ " + translate_source("Скрыть настройки")
            )
    
    def on_setting_change(self) -> None:
        """Handle setting change."""
        cfg = self.main_app.data["export_config"]
        apply_preview_settings(cfg, {
            "layout_type": self.combo_layout.currentData(),
            "col_tc": self.chk_col_tc.isChecked(),
            "col_char": self.chk_col_char.isChecked(),
            "col_actor": self.chk_col_actor.isChecked(),
            "col_text": self.chk_col_text.isChecked(),
            "round_time": self.chk_round_time.isChecked(),
            "time_display": self.combo_time_display.currentData(),
            "f_time": self.s_time.value(),
            "f_char": self.s_char.value(),
            "f_actor": self.s_actor.value(),
            "f_text": self.s_text.value(),
            "table_width_time": self.s_width_time.value(),
            "table_width_char": self.s_width_char.value(),
            "table_width_actor": self.s_width_actor.value(),
            "soften_colors": self.chk_soften_colors.isChecked(),
        })
        self._update_table_width_controls_visibility()
        self._save_export_settings()
        self.update_preview()

    def _get_export_highlight_ids(self) -> Optional[List[str]]:
        """Return the current actor highlight filter from export settings."""
        return get_export_highlight_ids(self.main_app.data)

    def _get_export_negative_ids(self) -> List[str]:
        """Return actors that use white text over highlight color."""
        return get_export_negative_ids(self.main_app.data)

    def _save_export_settings(self) -> None:
        """Mark project-local preview export settings as changed."""
        if hasattr(self.main_app, "set_dirty"):
            self.main_app.set_dirty(True)
    
    def open_actor_filter(self) -> None:
        """Open actor filter."""
        all_aids = list(self.main_app.data["actors"].keys())
        current_selection = (
            self.highlight_ids 
            if self.highlight_ids is not None 
            else all_aids
        )
        
        dialog = ActorFilterDialog(
            self.main_app.data["actors"], 
            current_selection, 
            self.highlight_negative_ids,
            self
        )
        
        if dialog.exec():
            selected = dialog.get_selected()
            self.highlight_negative_ids = dialog.get_negative_selected()
            cfg = self.main_app.data["export_config"]
            if len(selected) == len(all_aids):
                self.highlight_ids = None
            else:
                self.highlight_ids = selected
            cfg["highlight_ids_export"] = self.highlight_ids
            cfg["highlight_negative_ids_export"] = self.highlight_negative_ids
            self._save_export_settings()
            self.update_preview()
    
    def keyPressEvent(self, event) -> None:
        """Keypressevent."""
        super().keyPressEvent(event)
    
    def closeEvent(self, event) -> None:
        """Closeevent."""
        event.accept()
