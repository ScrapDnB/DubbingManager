"""Episode preview window."""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QComboBox, QSpinBox, QGroupBox, QFormLayout,
    QFrame, QCheckBox
)
from PySide6.QtCore import Qt
from PySide6.QtWebChannel import QWebChannel
from typing import Dict, List, Any, Optional, Set
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
from utils.helpers import hex_to_rgba_string, log_exception
from utils.web_bridge import WebBridge
from services import ExportService
from .dialogs.actor_filter import ActorFilterDialog

logger = logging.getLogger(__name__)


class HtmlLivePreview(QDialog):
    """Html Live Preview class."""

    # Class attributes
    main_app: Any
    ep_num: str
    highlight_ids: Optional[List[str]]
    _has_text_changes: bool

    def __init__(self, main_app: Any, ep_num: str) -> None:
        super().__init__(None)
        self.main_app: Any = main_app
        self.ep_num: str = ep_num
        self.setWindowTitle(f"Предпросмотр монтажного листа: Серия {ep_num}")
        self.resize(PREVIEW_WINDOW_WIDTH, PREVIEW_WINDOW_HEIGHT)

        self.highlight_ids = None
        self._has_text_changes: bool = False

        self._init_ui()

        try:
            self.browser.loadFinished.connect(self.on_page_loaded)
        except Exception as e:
            logger.error(f"Failed to connect loadFinished signal: {e}")
        
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

        # Internal implementation detail
        self.nav_panel: QHBoxLayout = QHBoxLayout()

        self.btn_toggle_sidebar = QPushButton("⬅ Скрыть настройки")
        self.btn_toggle_sidebar.setCheckable(True)
        self.btn_toggle_sidebar.clicked.connect(self.toggle_sidebar)

        self.nav_panel.addWidget(self.btn_toggle_sidebar)
        self.nav_panel.addStretch()

        self.root_layout.addLayout(self.nav_panel)

        # Internal implementation detail
        self.content_layout: QHBoxLayout = QHBoxLayout()
        self.root_layout.addLayout(self.content_layout)

        # Internal implementation detail
        self.settings_panel = QFrame()
        self.settings_panel.setFixedWidth(PREVIEW_SETTINGS_PANEL_WIDTH)
        self.settings_panel.setFrameShape(QFrame.StyledPanel)
        sp_layout: QVBoxLayout = QVBoxLayout(self.settings_panel)

        sp_layout.addWidget(QLabel("<b>Настройки вида</b>"))

        self.combo_layout = QComboBox()
        self.combo_layout.addItems(["Таблица", "Сценарий"])
        current_type: str = self.main_app.data["export_config"].get(
            "layout_type", "Таблица"
        )
        self.combo_layout.setCurrentText(current_type)
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
        self.combo_time_display.addItem("Начало и конец", "range")
        self.combo_time_display.addItem("Только начало", "start")
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
            self.chk_round_time,
        ]:
            columns_layout.addWidget(checkbox)
        columns_layout.addWidget(QLabel("Тайминг:"))
        columns_layout.addWidget(self.combo_time_display)
        sp_layout.addWidget(columns_group)
        
        # Internal implementation detail
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
        
        # Internal implementation detail
        filter_group = QGroupBox("Подсветка")
        f_lay = QVBoxLayout(filter_group)
        btn_filter = QPushButton("Выбрать актеров...")
        btn_filter.clicked.connect(self.open_actor_filter)
        f_lay.addWidget(btn_filter)
        sp_layout.addWidget(filter_group)
        sp_layout.addStretch()
        
        btn_close = QPushButton("Закрыть")
        btn_close.clicked.connect(self.close)
        sp_layout.addWidget(btn_close)
        
        self.content_layout.addWidget(self.settings_panel)
        
        # Internal implementation detail
        self.browser = QWebEngineView()
        if not WEB_ENGINE_AVAILABLE:
            self.browser.setOpenExternalLinks(False)
        self.content_layout.addWidget(self.browser)

    def _preview_check_box(self, text: str, checked: bool) -> QCheckBox:
        """Create a preview settings checkbox."""
        checkbox = QCheckBox(text)
        checkbox.setChecked(bool(checked))
        checkbox.toggled.connect(self.on_setting_change)
        return checkbox
    
    def on_page_loaded(self, ok: bool) -> None:
        """Handle page loaded."""
        pass

    def update_preview(self) -> None:
        """Update preview."""
        try:
            logger.info(f"update_preview: ep={self.ep_num}")
            
            lines = self.main_app.get_episode_lines(self.ep_num)
            logger.info(f"update_preview: lines={len(lines) if lines else 0}")
            
            if not lines:
                self.browser.setHtml("<h3>Нет данных в серии</h3>")
                return

            try:
                self.browser.loadFinished.disconnect(self.on_page_loaded)
            except Exception:
                pass

            self.browser.loadFinished.connect(self.on_page_loaded)

            cfg = self.main_app.data["export_config"]
            merge_cfg = self.main_app.data.get("replica_merge_config", {})
            local_layout = self.combo_layout.currentText()

            logger.info(f"update_preview: generating HTML with layout={local_layout}")

            export_service = ExportService(self.main_app.data)
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
            self.browser.setHtml(f"<h3>Ошибка: {e}</h3>")
    
    def toggle_sidebar(self) -> None:
        """Toggle sidebar."""
        is_hidden = self.settings_panel.isVisible()
        self.settings_panel.setVisible(not is_hidden)
        
        if is_hidden:
            self.btn_toggle_sidebar.setText("➡ Показать настройки")
        else:
            self.btn_toggle_sidebar.setText("⬅ Скрыть настройки")
    
    def on_setting_change(self) -> None:
        """Handle setting change."""
        cfg = self.main_app.data["export_config"]
        cfg["layout_type"] = self.combo_layout.currentText()
        cfg["col_tc"] = self.chk_col_tc.isChecked()
        cfg["col_char"] = self.chk_col_char.isChecked()
        cfg["col_actor"] = self.chk_col_actor.isChecked()
        cfg["col_text"] = self.chk_col_text.isChecked()
        cfg["round_time"] = self.chk_round_time.isChecked()
        cfg["time_display"] = self.combo_time_display.currentData()
        cfg["f_time"] = self.s_time.value()
        cfg["f_char"] = self.s_char.value()
        cfg["f_actor"] = self.s_actor.value()
        cfg["f_text"] = self.s_text.value()
        self._save_export_settings()
        self.update_preview()

    def _save_export_settings(self) -> None:
        """Persist preview export settings as the main export defaults."""
        if not hasattr(self.main_app, "global_settings_service"):
            return
        self.main_app.global_settings["export_config"] = (
            self.main_app.data["export_config"]
        )
        self.main_app.global_settings_service.save_settings(
            self.main_app.global_settings
        )
    
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
            self
        )
        
        if dialog.exec():
            selected = dialog.get_selected()
            if len(selected) == len(all_aids) or len(selected) == 0:
                self.highlight_ids = None
            else:
                self.highlight_ids = selected
            self.update_preview()
    
    def keyPressEvent(self, event) -> None:
        """Keypressevent."""
        # Internal implementation detail
        super().keyPressEvent(event)
    
    def closeEvent(self, event) -> None:
        """Closeevent."""
        event.accept()
