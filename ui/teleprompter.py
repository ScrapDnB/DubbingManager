"""Teleprompter window."""

import platform
from copy import deepcopy
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QSpinBox, QSlider, QCheckBox, QFrame,
    QScrollArea, QSplitter, QToolBar, QListWidget,
    QListWidgetItem, QAbstractItemView, QMessageBox,
    QDoubleSpinBox, QSizePolicy, QWidget, QFormLayout,
    QGroupBox, QTextEdit, QDialogButtonBox, QGraphicsView,
    QGraphicsScene, QGraphicsTextItem, QApplication, QComboBox,
    QMenu
)
from PySide6.QtGui import (
    QColor, QFont, QPainter, QPen, QBrush, QCursor, QAction
)
from PySide6.QtCore import (
    Qt, QTimer, Signal, Slot, QRectF, QEvent, QProcess
)
from typing import Dict, List, Any, Optional, Set, Tuple, Union
import math
import logging

from config.constants import (
    DEFAULT_PROMPTER_CONFIG,
    PROMPTER_WINDOW_WIDTH,
    PROMPTER_WINDOW_HEIGHT,
    PROMPTER_FLOAT_WINDOW_WIDTH,
    PROMPTER_FLOAT_WINDOW_HEIGHT,
    EDIT_TEXT_DIALOG_WIDTH,
    EDIT_TEXT_DIALOG_HEIGHT,
    PROMPTER_SIDE_PANEL_MIN_WIDTH,
    PROMPTER_V_SPLITTER_SIZES,
    PROMPTER_H_SPLITTER_SIZES,
    PROMPTER_SIDE_MIN_WIDTH,
    PROMPTER_SIDE_MAX_WIDTH,
    PROMPTER_SCENE_WIDTH,
    PROMPTER_SCENE_CENTER_X,
    PROMPTER_FONT_MIN_SIZE,
    PROMPTER_FONT_TC_MAX,
    PROMPTER_FONT_CHAR_MAX,
    PROMPTER_FONT_ACTOR_MAX,
    PROMPTER_FONT_TEXT_MAX,
    PROMPTER_FOCUS_SLIDER_MAX,
    PROMPTER_SCROLL_SMOOTHNESS_MAX,
    PROMPTER_SCROLL_SMOOTHNESS_SCALE,
    PROMPTER_TIMECODE_Y_CURSOR,
    PROMPTER_SCENE_EXTRA_HEIGHT,
    SCROLL_TIMEOUT_MS,
    SCROLL_THRESHOLD_TOP,
    SCROLL_THRESHOLD_BOTTOM,
    PROMPTER_NAV_BUTTON_MIN_WIDTH,
    FLOAT_BTN_WIDTH,
    FLOAT_BTN_HEIGHT,
    FLOAT_BTN_Y_PREV,
    FLOAT_BTN_Y_NEXT,
    FLOAT_LABEL_Y,
    FLOAT_LABEL_HEIGHT,
    FLOAT_SCROLL_Y,
    FLOAT_SCROLL_HEIGHT,
    FLOAT_SCROLL_WIDTH,
    FLOAT_TEXT_VIEW_WIDTH,
    FLOAT_BTN_HIDE_WIDTH,
    FLOAT_BTN_HIDE_HEIGHT,
    FLOAT_BTN_HIDE_X,
    FLOAT_BTN_HIDE_Y,
    FLOAT_MARGIN_X,
)
from services import ExportService, ScriptTextService
from services.assignment_service import get_actor_for_character
from services.osc_worker import OscWorker, OSC_AVAILABLE
from services.teleprompter_navigation_service import TeleprompterNavigationService
from utils.helpers import (
    ass_time_to_seconds,
    format_seconds_to_tc,
    log_exception,
    natural_sort_key,
)
from utils.i18n import translate_source, translate_widget_tree
from .teleprompter_widgets import (
    EditableCharacterItem,
    EditableTextItem,
    SettingsSection,
    TeleprompterFloatWindow,
)

logger = logging.getLogger(__name__)


class TeleprompterWindow(QDialog):
    """Teleprompter Window class."""

    # Class attributes with type hints
    main_app: Any
    ep_num: str
    cfg: Dict[str, Any]
    time_map: List[Dict[str, Any]]
    osc_thread: Optional[OscWorker]
    last_known_time: float
    highlight_ids: Optional[List[str]]
    _has_text_changes: bool
    _initializing: bool

    def __init__(self, main_app: Any, ep_num: str) -> None:
        super().__init__(None)
        self.main_app: Any = main_app
        self.ep_num: str = ep_num
        self.setWindowTitle(
            f"{translate_source('Телесуфлёр')} - {translate_source('Серия')} {ep_num}"
        )
        self.resize(PROMPTER_WINDOW_WIDTH, PROMPTER_WINDOW_HEIGHT)

        self._init_config()

        self.time_map = []
        self.osc_thread: Optional[OscWorker] = None
        self.osc_client = None
        self.last_known_time: float = 0.0
        self.highlight_ids = None
        self._has_text_changes: bool = False
        self._initializing: bool = True
        self._manual_scroll_override: bool = False
        self.navigation_service = TeleprompterNavigationService()

        # UI
        self._init_ui()
        translate_widget_tree(self)
        self.build_prompter_content()
        self._apply_saved_osc_state()

        self._initializing = False

    def _init_config(self) -> None:
        """Init config."""
        if (
            "prompter_config" not in self.main_app.data or
            self.main_app.data["prompter_config"] is None
        ):
            self.main_app.data["prompter_config"] = deepcopy(
                DEFAULT_PROMPTER_CONFIG
            )

        self.cfg: Dict[str, Any] = self.main_app.data["prompter_config"]

        for key, value in DEFAULT_PROMPTER_CONFIG.items():
            if key != "colors" and key not in self.cfg:
                self.cfg[key] = deepcopy(value)

        if "colors" not in self.cfg or not isinstance(self.cfg["colors"], dict):
            self.cfg["colors"] = DEFAULT_PROMPTER_CONFIG["colors"].copy()
        else:
            color_key: str
            color_value: str
            for color_key, color_value in DEFAULT_PROMPTER_CONFIG["colors"].items():
                if color_key not in self.cfg["colors"]:
                    self.cfg["colors"][color_key] = color_value

    def _apply_saved_osc_state(self) -> None:
        """Apply saved OSC connection state after UI setup."""
        self._sync_osc_connection_to_config()

    def _sync_osc_connection_to_config(self) -> None:
        """Match live OSC connection to the saved config state."""
        desired = bool(self.cfg.get("osc_enabled", False))
        active = self.osc_thread is not None
        if desired == active:
            return

        was_initializing = self._initializing
        self._initializing = True
        try:
            self.toggle_osc_connection_status(desired)
        finally:
            self._initializing = was_initializing

    def sync_config_controls(self) -> None:
        """Refresh settings controls from the current config."""
        if not hasattr(self, "spin_font_tc"):
            return

        widgets = [
            self.spin_font_tc,
            self.spin_font_char,
            self.spin_font_actor,
            self.spin_font_text,
            self.slider_focus_pos,
            self.slider_scroll_smoothness,
            self.chk_show_header,
            self.chk_mirror,
            self.chk_follow_reaper,
            self.chk_reaper_follow,
            self.chk_offset,
            self.spin_offset,
        ]
        self._initializing = True
        try:
            for widget in widgets:
                widget.blockSignals(True)
            self.spin_font_tc.setValue(self.cfg.get("f_tc", 20))
            self.spin_font_char.setValue(self.cfg.get("f_char", 24))
            self.spin_font_actor.setValue(self.cfg.get("f_actor", 18))
            self.spin_font_text.setValue(self.cfg.get("f_text", 36))
            self.slider_focus_pos.setValue(
                int(self.cfg.get("focus_ratio", 0.5) * 100)
            )
            self.slider_scroll_smoothness.setValue(
                int(self.cfg.get("scroll_smoothness_slider", 18))
            )
            self.chk_show_header.setChecked(
                self.cfg.get("show_header", False)
            )
            self.chk_mirror.setChecked(
                self.cfg.get("is_mirrored", False)
            )
            self.chk_follow_reaper.setChecked(
                self.cfg.get("sync_in", True)
            )
            self.chk_reaper_follow.setChecked(
                self.cfg.get("sync_out", False)
            )
            self.chk_offset.setChecked(
                self.cfg.get("reaper_offset_enabled", False)
            )
            self.spin_offset.setValue(
                self.cfg.get("reaper_offset_seconds", -2.0)
            )
            self.btn_osc.setChecked(
                self.cfg.get("osc_enabled", False)
            )
            self.header_panel.setVisible(self.cfg.get("show_header", False))
            self.apply_mirror_transform()
        finally:
            for widget in widgets:
                widget.blockSignals(False)
            self._initializing = False
        self._sync_osc_connection_to_config()

    def _init_ui(self) -> None:
        """Init ui."""
        self.root_layout: QVBoxLayout = QVBoxLayout(self)
        self.root_layout.setContentsMargins(0, 0, 0, 0)
        self.root_layout.setSpacing(0)

        self._init_toolbar()

        self._init_splitters()

        self.smooth_scroll_timer = QTimer()
        self.smooth_scroll_timer.setInterval(16)
        self.smooth_scroll_timer.timeout.connect(self.smooth_scroll_step)
        self._scroll_target_y: Optional[float] = None
    
    def _init_toolbar(self) -> None:
        """Init toolbar."""
        self.toolbar: QToolBar = QToolBar("Управление")
        self.toolbar.setMovable(False)
        self.toolbar.setStyleSheet(
            "QToolBar { padding: 5px; }"
        )

        self.btn_toggle_settings = QPushButton("⚙ Панель настроек")
        self.btn_toggle_settings.setCheckable(True)
        self.btn_toggle_settings.clicked.connect(
            self.toggle_settings_panel_visibility
        )
        self.toolbar.addWidget(self.btn_toggle_settings)

        self.toolbar.addSeparator()

        self.toolbar.addWidget(QLabel("Серия:"))
        self.combo_episode = QComboBox()
        self.combo_episode.setMinimumWidth(120)
        self._populate_episode_combo()
        self.combo_episode.currentIndexChanged.connect(
            self.on_episode_combo_changed
        )
        self.toolbar.addWidget(self.combo_episode)

        self.toolbar.addSeparator()

        self.btn_refresh_cast = QPushButton("🔄 Обновить каст")
        self.btn_refresh_cast.clicked.connect(self.refresh_cast_assignments)
        self.toolbar.addWidget(self.btn_refresh_cast)

        self.toolbar.addSeparator()

        self.btn_go_prev = QPushButton("⏮ Предыдущая реплика")
        self.btn_go_prev.setMinimumWidth(PROMPTER_NAV_BUTTON_MIN_WIDTH)
        self.btn_go_prev.clicked.connect(
            lambda: self.navigate_to_replica_in_direction(-1)
        )
        self.toolbar.addWidget(self.btn_go_prev)

        self.btn_go_next = QPushButton("Следующая реплика ⏭")
        self.btn_go_next.setMinimumWidth(PROMPTER_NAV_BUTTON_MIN_WIDTH)
        self.btn_go_next.clicked.connect(
            lambda: self.navigate_to_replica_in_direction(1)
        )
        self.toolbar.addWidget(self.btn_go_next)

        self.toolbar.addSeparator()

        self.btn_float_window = QPushButton("🔼 Плавающее окно")
        self.btn_float_window.setCheckable(True)
        self.btn_float_window.clicked.connect(self.toggle_float_window)
        self.toolbar.addWidget(self.btn_float_window)

        toolbar_spacer: QWidget = QWidget()
        toolbar_spacer.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Preferred
        )
        self.toolbar.addWidget(toolbar_spacer)

        btn_close = QPushButton("Закрыть окно")
        btn_close.clicked.connect(self.close)
        self.toolbar.addWidget(btn_close)

        self.root_layout.addWidget(self.toolbar)

    def _populate_episode_combo(self) -> None:
        """Populate episode combo."""
        self.combo_episode.blockSignals(True)
        self.combo_episode.clear()

        episode_nums = sorted(
            self.main_app.data.get("episodes", {}).keys(),
            key=natural_sort_key
        )
        for ep_num in episode_nums:
            self.combo_episode.addItem(
                str(ep_num),
                str(ep_num)
            )

        index = self.combo_episode.findData(str(self.ep_num))
        if index >= 0:
            self.combo_episode.setCurrentIndex(index)

        self.combo_episode.blockSignals(False)

    def on_episode_combo_changed(self, index: int) -> None:
        """Handle episode combo change."""
        ep_num = self.combo_episode.itemData(index)
        if ep_num is not None:
            self.switch_episode(str(ep_num))

    def switch_episode(self, ep_num: str) -> None:
        """Switch episode."""
        if str(ep_num) == str(self.ep_num):
            return

        if str(ep_num) not in self.main_app.data.get("episodes", {}):
            QMessageBox.warning(
                self,
                translate_source("Ошибка"),
                f"{translate_source('Серия не найдена в проекте:')} {ep_num}"
            )
            self._populate_episode_combo()
            return

        if self.smooth_scroll_timer.isActive():
            self.smooth_scroll_timer.stop()
        self._scroll_target_y = None
        self.last_known_time = 0.0
        self.ep_num = str(ep_num)
        self.setWindowTitle(
            f"{translate_source('Телесуфлёр')} - "
            f"{translate_source('Серия')} {self.ep_num}"
        )

        combo_index = self.combo_episode.findData(str(self.ep_num))
        if combo_index >= 0:
            self.combo_episode.blockSignals(True)
            self.combo_episode.setCurrentIndex(combo_index)
            self.combo_episode.blockSignals(False)

        self._sync_main_episode_selection()
        self.build_prompter_content()
        if hasattr(self, 'float_window') and self.float_window:
            self.float_window.sync_episode_combo()

    def _sync_main_episode_selection(self) -> None:
        """Synchronize main episode selection."""
        combo = getattr(self.main_app, "ep_combo", None)
        if not combo:
            return

        index = combo.findData(str(self.ep_num))
        if index < 0:
            return

        combo.blockSignals(True)
        combo.setCurrentIndex(index)
        combo.blockSignals(False)
        if hasattr(self.main_app, "change_episode"):
            self.main_app.change_episode()

    def _init_splitters(self) -> None:
        """Init splitters."""
        self.v_splitter: QSplitter = QSplitter(Qt.Vertical)
        self.v_splitter.setHandleWidth(8)
        self.v_splitter.setStyleSheet(
            "QSplitter::handle { background: #444; }"
        )
        self.v_splitter.splitterMoved.connect(
            lambda pos, idx: self.update_big_timecode_font_size()
        )
        
        self.header_panel = QFrame()
        self.header_panel.setObjectName("HeaderPanel")
        self.header_panel.setMinimumHeight(0)
        header_layout = QVBoxLayout(self.header_panel)
        header_layout.setContentsMargins(0, 0, 0, 0)
        
        self.lbl_big_timecode = QLabel("0:00:00.000")
        self.lbl_big_timecode.setAlignment(Qt.AlignCenter)
        header_layout.addWidget(self.lbl_big_timecode)
        self.v_splitter.addWidget(self.header_panel)
        
        self.h_splitter = QSplitter(Qt.Horizontal)
        self.h_splitter.setHandleWidth(8)
        
        self._init_side_panel()
        self.h_splitter.addWidget(self.side_panel_widget)
        
        self.prompter_scene = QGraphicsScene()
        self.prompter_view = QGraphicsView(self.prompter_scene)
        self.prompter_view.setRenderHints(
            QPainter.Antialiasing | QPainter.TextAntialiasing
        )
        self.prompter_view.setDragMode(QGraphicsView.ScrollHandDrag)
        self.prompter_view.setFrameShape(QFrame.NoFrame)
        self.prompter_view.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.prompter_view.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.prompter_view.viewport().installEventFilter(self)
        self.prompter_view.installEventFilter(self)
        self.h_splitter.addWidget(self.prompter_view)

        self.v_splitter.addWidget(self.h_splitter)
        self.root_layout.addWidget(self.v_splitter)

        self.header_panel.setVisible(self.cfg["show_header"])
        self.v_splitter.setSizes(PROMPTER_V_SPLITTER_SIZES)
        self.h_splitter.setSizes(PROMPTER_H_SPLITTER_SIZES)

    def eventFilter(self, obj, event) -> bool:
        """Eventfilter."""
        manual_scroll_events = {
            QEvent.Wheel,
            QEvent.MouseButtonPress,
            QEvent.KeyPress,
            QEvent.TouchBegin,
        }
        if (
            obj in (self.prompter_view, self.prompter_view.viewport())
            and event.type() in manual_scroll_events
        ):
            self.enter_manual_scroll_override()

        return super().eventFilter(obj, event)

    def enter_manual_scroll_override(self) -> None:
        """Enter manual scroll override."""
        self._manual_scroll_override = True
        self.cancel_pending_prompter_scroll()

    def exit_manual_scroll_override(self) -> None:
        """Exit manual scroll override."""
        self._manual_scroll_override = False

    def cancel_pending_prompter_scroll(self) -> None:
        """Cancel pending prompter scroll."""
        self._scroll_target_y = None
        if (
            hasattr(self, "smooth_scroll_timer")
            and self.smooth_scroll_timer.isActive()
        ):
            self.smooth_scroll_timer.stop()
    
    def _init_side_panel(self) -> None:
        """Init side panel."""
        self.side_panel_widget = QWidget()
        self.side_panel_widget.setMinimumWidth(PROMPTER_SIDE_PANEL_MIN_WIDTH)
        self.side_layout = QVBoxLayout(self.side_panel_widget)
        
        self.settings_scroll_area = QScrollArea()
        self.settings_scroll_area.setWidgetResizable(True)
        self.settings_scroll_area.setFrameShape(QFrame.NoFrame)
        
        settings_container = QWidget()
        settings_v_layout = QVBoxLayout(settings_container)
        settings_v_layout.setSpacing(4)
        
        self._init_font_settings(settings_v_layout)
        self._init_focus_settings(settings_v_layout)
        self._init_scroll_settings(settings_v_layout)
        self._init_view_settings(settings_v_layout)
        self._init_osc_settings(settings_v_layout)
        
        self.settings_scroll_area.setWidget(settings_container)
        self.side_layout.addWidget(self.settings_scroll_area)
        
        self.btn_actor_filter = QPushButton(
            "🎭 Выбор актёров для суфлёра..."
        )
        self.btn_actor_filter.clicked.connect(self.open_actor_filter_dialog)
        self.side_layout.addWidget(self.btn_actor_filter)
        
        self.side_layout.addWidget(QLabel("<b>Список реплик актёра:</b>"))
        self.list_of_replicas = QListWidget()
        self.list_of_replicas.itemClicked.connect(
            self.on_replica_list_item_clicked
        )
        self.list_of_replicas.setSizePolicy(
            QSizePolicy.Preferred, QSizePolicy.Expanding
        )
        self.side_layout.addWidget(self.list_of_replicas)
    
    def _init_font_settings(self, layout) -> None:
        """Init font settings."""
        fonts_section = SettingsSection("Размеры шрифтов элементов")
        fonts_form = QFormLayout()

        self.spin_font_tc = QSpinBox()
        self.spin_font_tc.setRange(PROMPTER_FONT_MIN_SIZE, PROMPTER_FONT_TC_MAX)
        self.spin_font_tc.setValue(self.cfg["f_tc"])

        self.spin_font_char = QSpinBox()
        self.spin_font_char.setRange(PROMPTER_FONT_MIN_SIZE, PROMPTER_FONT_CHAR_MAX)
        self.spin_font_char.setValue(self.cfg["f_char"])

        self.spin_font_actor = QSpinBox()
        self.spin_font_actor.setRange(PROMPTER_FONT_MIN_SIZE, PROMPTER_FONT_ACTOR_MAX)
        self.spin_font_actor.setValue(self.cfg["f_actor"])

        self.spin_font_text = QSpinBox()
        self.spin_font_text.setRange(PROMPTER_FONT_MIN_SIZE, PROMPTER_FONT_TEXT_MAX)
        self.spin_font_text.setValue(self.cfg["f_text"])
        
        for s in [
            self.spin_font_tc, self.spin_font_char,
            self.spin_font_actor, self.spin_font_text
        ]:
            s.valueChanged.connect(self.handle_font_config_change)
        
        fonts_form.addRow("Таймкод:", self.spin_font_tc)
        fonts_form.addRow("Имя персонажа:", self.spin_font_char)
        fonts_form.addRow("Имя актёра:", self.spin_font_actor)
        fonts_form.addRow("Текст реплики:", self.spin_font_text)
        fonts_section.addLayout(fonts_form)
        layout.addWidget(fonts_section)
    
    def _init_focus_settings(self, layout) -> None:
        """Init focus settings."""
        focus_section = SettingsSection("Позиция линии чтения")
        focus_layout = QVBoxLayout()

        self.slider_focus_pos = QSlider(Qt.Horizontal)
        self.slider_focus_pos.setRange(10, PROMPTER_FOCUS_SLIDER_MAX)
        self.slider_focus_pos.setValue(int(self.cfg["focus_ratio"] * PROMPTER_SCROLL_SMOOTHNESS_SCALE))
        self.slider_focus_pos.valueChanged.connect(
            self.handle_focus_ratio_change
        )
        
        self.lbl_focus_percent = QLabel(
            f"{translate_source('Высота линии:')} {self.slider_focus_pos.value()}%"
        )
        self.lbl_focus_percent.setAlignment(Qt.AlignCenter)
        
        focus_layout.addWidget(self.lbl_focus_percent)
        focus_layout.addWidget(self.slider_focus_pos)
        focus_section.addLayout(focus_layout)
        layout.addWidget(focus_section)
    
    def _init_scroll_settings(self, layout) -> None:
        """Init scroll settings."""
        scroll_section = SettingsSection("Прокрутка")
        sg_layout = QVBoxLayout()

        self.slider_scroll_smoothness = QSlider(Qt.Horizontal)
        self.slider_scroll_smoothness.setRange(0, PROMPTER_SCROLL_SMOOTHNESS_MAX)

        if "scroll_smoothness_slider" in self.cfg:
            init_val = int(self.cfg.get("scroll_smoothness_slider", 18))
        else:
            init_val = int(round(self.cfg.get("scroll_smoothness", 0.18) * PROMPTER_SCROLL_SMOOTHNESS_SCALE))

        self.slider_scroll_smoothness.setValue(init_val)
        self.slider_scroll_smoothness.valueChanged.connect(
            self.handle_scroll_smoothness_change
        )
        
        self.lbl_scroll_value = QLabel(
            f"{self.cfg.get('scroll_smoothness', 0.18):.2f}"
        )
        self.lbl_scroll_descr = QLabel(
            "Плавность прокрутки (слева — быстрее, справа — дольше задержка):"
        )
        self.lbl_scroll_descr.setAlignment(Qt.AlignCenter)
        
        sg_layout.addWidget(self.lbl_scroll_descr)
        row_widget = QWidget()
        row_layout = QHBoxLayout(row_widget)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.addWidget(self.slider_scroll_smoothness)
        row_layout.addWidget(self.lbl_scroll_value)
        sg_layout.addWidget(row_widget)
        
        scroll_section.addLayout(sg_layout)
        layout.addWidget(scroll_section)
        self.handle_scroll_smoothness_change()
    
    def _init_view_settings(self, layout) -> None:
        """Init view settings."""
        view_section = SettingsSection("Отображение")
        view_lay = QVBoxLayout()
        
        btn_colors = QPushButton("🎨 Настроить цвета телесуфлёра...")
        btn_colors.clicked.connect(self.open_color_settings_dialog)
        self.color_preset_buttons = []
        presets_layout = QHBoxLayout()
        presets_layout.setContentsMargins(0, 0, 0, 0)
        presets_layout.setSpacing(6)
        for index in range(4):
            button = QPushButton(str(index + 1))
            button.setFixedHeight(28)
            button.setContextMenuPolicy(Qt.CustomContextMenu)
            button.clicked.connect(
                lambda checked=False, idx=index: (
                    self.apply_or_save_color_preset(idx)
                )
            )
            button.customContextMenuRequested.connect(
                lambda point, idx=index: self.show_color_preset_menu(idx)
            )
            self.color_preset_buttons.append(button)
            presets_layout.addWidget(button)
        self.update_color_preset_buttons()
        
        self.chk_show_header = QCheckBox(
            "Показать таймкод Reaper сверху",
            checked=self.cfg["show_header"]
        )
        self.chk_show_header.toggled.connect(self.toggle_header_visibility)
        
        self.chk_mirror = QCheckBox(
            "Зеркальный режим (отражение)",
            checked=self.cfg.get("is_mirrored", False)
        )
        self.chk_mirror.toggled.connect(self.toggle_mirror_mode)
        
        view_lay.addWidget(btn_colors)
        view_lay.addLayout(presets_layout)
        view_lay.addWidget(self.chk_show_header)
        view_lay.addWidget(self.chk_mirror)
        view_section.addLayout(view_lay)
        layout.addWidget(view_section)
    
    def _init_osc_settings(self, layout) -> None:
        """Init osc settings."""
        osc_section = SettingsSection("Синхронизация Reaper (OSC)")
        osc_layout = QVBoxLayout()
        
        self.chk_follow_reaper = QCheckBox(
            "Суфлёр следует за Reaper",
            checked=self.cfg["sync_in"]
        )
        self.chk_reaper_follow = QCheckBox(
            "Reaper следует за навигацией",
            checked=self.cfg["sync_out"]
        )
        
        self.chk_follow_reaper.toggled.connect(
            self.save_current_config_to_project
        )
        self.chk_reaper_follow.toggled.connect(
            self.save_current_config_to_project
        )
        
        self.btn_osc = QPushButton("Включить OSC связь")
        self.btn_osc.setCheckable(True)
        self.btn_osc.setChecked(self.cfg.get("osc_enabled", False))
        self.btn_osc.clicked.connect(self.toggle_osc_connection_status)
        
        osc_layout.addWidget(self.chk_follow_reaper)
        osc_layout.addWidget(self.chk_reaper_follow)
        osc_layout.addWidget(self.btn_osc)
        
        offset_layout = QHBoxLayout()
        self.chk_offset = QCheckBox(
            "Отступ -2 секунды",
            checked=self.cfg.get("reaper_offset_enabled", False)
        )
        self.spin_offset = QDoubleSpinBox()
        self.spin_offset.setRange(-10, 10)
        self.spin_offset.setSingleStep(0.5)
        self.spin_offset.setValue(self.cfg.get("reaper_offset_seconds", -2.0))
        self.spin_offset.setSuffix(f" {translate_source('сек')}")
        
        self.chk_offset.toggled.connect(self.save_current_config_to_project)
        self.spin_offset.valueChanged.connect(self.save_current_config_to_project)
        
        offset_layout.addWidget(self.chk_offset)
        offset_layout.addWidget(self.spin_offset)
        offset_layout.addStretch()
        osc_layout.addLayout(offset_layout)
        
        osc_section.addLayout(osc_layout)
        layout.addWidget(osc_section)
    
    def compute_scroll_tau(self) -> float:
        """Compute scroll tau."""
        s = None
        if hasattr(self, 'slider_scroll_smoothness'):
            try:
                s = int(self.slider_scroll_smoothness.value())
            except RuntimeError:
                s = int(self.cfg.get('scroll_smoothness_slider', 18))
        else:
            s = int(self.cfg.get('scroll_smoothness_slider', 18))
        
        return self.navigation_service.compute_scroll_tau(s)
    
    def update_big_timecode_font_size(self) -> None:
        """Update big timecode font size."""
        current_h = self.header_panel.height()
        if current_h > 10:
            font_size = int(current_h * 0.7)
            text_color = self.cfg['colors']['header_text']
            self.lbl_big_timecode.setStyleSheet(
                f"color: {text_color}; font-family: 'Courier New'; "
                f"font-weight: bold; font-size: {font_size}px;"
            )
    
    def adjust_prompter_view_scale(self) -> None:
        """Adjust prompter view scale."""
        try:
            scene_rect = self.prompter_scene.sceneRect()
            if scene_rect.width() <= 0:
                return
            
            vw = max(1, self.prompter_view.viewport().width())
            scale_x = vw / scene_rect.width()
            min_scale, max_scale = 0.5, 3.0
            scale = max(min_scale, min(scale_x, max_scale))
            
            self.prompter_view.resetTransform()
            self.prompter_view.scale(scale, scale)
        except Exception as e:
            logger.warning(f"Error adjusting scale: {e}")
    
    def toggle_settings_panel_visibility(self, is_hidden: bool) -> None:
        """Toggle settings panel visibility."""
        visible = not is_hidden
        self.side_panel_widget.setVisible(visible)
        
        if is_hidden:
            self.btn_toggle_settings.setText(
                "⚙ " + translate_source("Показать настройки")
            )
        else:
            self.btn_toggle_settings.setText(
                "⚙ " + translate_source("Скрыть настройки")
            )
        
        try:
            total_w = max(200, self.h_splitter.width())
            if not visible:
                self.h_splitter.setSizes([0, total_w])
            else:
                side_w = max(200, min(420, self.side_panel_widget.minimumWidth() or 320))
                self.h_splitter.setSizes([side_w, max(200, total_w - side_w)])
            
            QTimer.singleShot(60, self.adjust_prompter_view_scale)
        except Exception as e:
            logger.warning(f"Error toggling panel: {e}")
            QTimer.singleShot(60, self.adjust_prompter_view_scale)
    
    def toggle_float_window(self, show: bool) -> None:
        """Toggle float window."""
        if show:
            self.show_float_window()
        else:
            self.hide_float_window()

    def show_float_window(self) -> None:
        """Show float window."""
        if not hasattr(self, 'float_window') or self.float_window is None:
            self.float_window = TeleprompterFloatWindow(self)
        
        if self.float_window._cocoa_window:
            # macOS-specific handling
            self.float_window.show_cocoa_window()
        else:
            # Qt-specific handling
            self.float_window.show()
            self.float_window.raise_()
        
        self.btn_float_window.setChecked(True)
    
    def hide_float_window(self) -> None:
        """Hide float window."""
        if hasattr(self, 'float_window') and self.float_window:
            if self.float_window._cocoa_window:
                self.float_window.hide_cocoa_window()
            else:
                self.float_window.hide()
        self.btn_float_window.setChecked(False)
    
    def handle_font_config_change(self) -> None:
        """Handle font config change."""
        self.cfg["f_tc"] = self.spin_font_tc.value()
        self.cfg["f_char"] = self.spin_font_char.value()
        self.cfg["f_actor"] = self.spin_font_actor.value()
        self.cfg["f_text"] = self.spin_font_text.value()

        self.main_app.save_global_prompter_settings(self.cfg)

        if not getattr(self, '_initializing', False):
            self.main_app.set_dirty(True)
        self.build_prompter_content()
    
    def handle_focus_ratio_change(self) -> None:
        """Handle focus ratio change."""
        val = self.slider_focus_pos.value()
        self.cfg["focus_ratio"] = val / 100.0
        self.lbl_focus_percent.setText(f"{translate_source('Высота линии:')} {val}%")
        
        if not getattr(self, '_initializing', False):
            self.main_app.set_dirty(True)
        self.update_view_position_by_time(self.last_known_time)
    
    def handle_scroll_smoothness_change(self) -> None:
        """Handle scroll smoothness change."""
        sval = int(self.slider_scroll_smoothness.value())
        self.cfg["scroll_smoothness_slider"] = sval
        tau = self.compute_scroll_tau()
        
        if tau <= 0:
            self.lbl_scroll_value.setText("instant")
            self.lbl_scroll_descr.setText(
                translate_source("Плавность прокрутки: мгновенно")
            )
        else:
            self.lbl_scroll_value.setText(f"{tau:.2f}s")
            self.lbl_scroll_descr.setText(
                f"{translate_source('Плавность прокрутки: задержка ≈')} {tau:.2f}s"
            )
        
        if not getattr(self, '_initializing', False):
            self.main_app.set_dirty(True)
    
    def smooth_scroll_step(self) -> None:
        """Smooth scroll step."""
        if self._scroll_target_y is None:
            self.smooth_scroll_timer.stop()
            return
        
        view = self.prompter_view
        vp_center = view.viewport().rect().center()
        scene_center = view.mapToScene(vp_center)
        current_y = scene_center.y()
        target_y = self._scroll_target_y
        
        tau = self.compute_scroll_tau()
        if tau <= 0:
            view.centerOn(425, target_y)
            self._scroll_target_y = None
            self.smooth_scroll_timer.stop()
            return
        
        dt = max(0.001, float(self.smooth_scroll_timer.interval()) / 1000.0)
        alpha = 1.0 - math.exp(-dt / tau)
        new_y = current_y * (1.0 - alpha) + target_y * alpha
        
        if abs(new_y - target_y) < 0.5:
            view.centerOn(425, target_y)
            self._scroll_target_y = None
            self.smooth_scroll_timer.stop()
        else:
            view.centerOn(425, new_y)
    
    def open_color_settings_dialog(self) -> None:
        """Open color settings dialog."""
        from .dialogs.colors import PrompterColorDialog

        dialog = PrompterColorDialog(self.cfg["colors"], self)
        try:
            if dialog.exec():
                self.cfg["colors"] = dialog.get_final_colors()

                self.main_app.save_global_prompter_settings(self.cfg)

                self.main_app.set_dirty(True)
                self.build_prompter_content()
        finally:
            self._restore_after_color_preset_action()

    def get_color_presets(self) -> List[Optional[Dict[str, str]]]:
        """Return global color presets when the main app provides them."""
        if hasattr(self.main_app, "get_prompter_color_presets"):
            return self.main_app.get_prompter_color_presets()
        return [None, None, None, None]

    def update_color_preset_buttons(self) -> None:
        """Refresh color preset button previews."""
        if not hasattr(self, "color_preset_buttons"):
            return

        presets = self.get_color_presets()
        for index, button in enumerate(self.color_preset_buttons):
            preset = presets[index] if index < len(presets) else None
            if preset:
                bg = preset.get("bg", "#000000")
                text = preset.get("active_text", "#ffffff")
                button.setText(str(index + 1))
                button.setToolTip(
                    f"Пресет {index + 1}: фон {bg}, текст {text}."
                )
                button.setStyleSheet(
                    f"background-color: {bg}; color: {text}; "
                    "border: 1px solid #666; border-radius: 4px;"
                )
            else:
                button.setText(str(index + 1))
                button.setToolTip(
                    f"Пустой пресет {index + 1}. Нажмите, чтобы сохранить "
                    "текущую цветовую схему."
                )
                button.setStyleSheet(
                    "color: #666; border: 1px dashed #999; border-radius: 4px;"
                )

    def apply_or_save_color_preset(self, index: int) -> None:
        """Apply a filled preset or save current colors into an empty one."""
        presets = self.get_color_presets()
        preset = presets[index] if 0 <= index < len(presets) else None
        if preset:
            self.apply_color_preset(index)
        else:
            self.save_current_color_preset(index, ask=False)

    def show_color_preset_menu(self, index: int) -> None:
        """Show actions for one color preset slot."""
        menu = QMenu(self)
        apply_action = QAction("Применить", self)
        save_action = QAction("Сохранить текущую схему", self)

        presets = self.get_color_presets()
        has_preset = bool(presets[index]) if 0 <= index < len(presets) else False
        apply_action.setEnabled(has_preset)
        apply_action.triggered.connect(
            lambda checked=False, idx=index: self.apply_color_preset(idx)
        )
        save_action.triggered.connect(
            lambda checked=False, idx=index: (
                self.save_current_color_preset(idx, ask=has_preset)
            )
        )
        menu.addAction(apply_action)
        menu.addAction(save_action)
        menu.exec(QCursor.pos())
        self._restore_after_color_preset_action()

    def apply_color_preset(self, index: int) -> None:
        """Apply one global color preset to the current project."""
        presets = self.get_color_presets()
        if not (0 <= index < len(presets)) or not presets[index]:
            return

        self.cfg["colors"] = deepcopy(presets[index])
        self.main_app.save_global_prompter_settings(self.cfg)
        self.main_app.set_dirty(True)
        self.build_prompter_content()
        self._restore_after_color_preset_action()

    def save_current_color_preset(self, index: int, ask: bool = True) -> None:
        """Save current project colors into one global preset slot."""
        try:
            if not hasattr(self.main_app, "save_prompter_color_preset"):
                return

            if ask:
                answer = QMessageBox.question(
                    self,
                    "Перезаписать пресет?",
                    f"Пресет {index + 1} будет заменён текущей цветовой схемой. "
                    "Продолжить?",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No,
                )
                if answer != QMessageBox.Yes:
                    return

            if self.main_app.save_prompter_color_preset(
                index,
                deepcopy(self.cfg["colors"])
            ):
                self.update_color_preset_buttons()
        finally:
            self._restore_after_color_preset_action()

    def _restore_after_color_preset_action(self) -> None:
        """Bring the teleprompter back after popup menu/dialog actions."""
        QTimer.singleShot(0, self._activate_after_color_preset_action)
        QTimer.singleShot(100, self._activate_after_color_preset_action)

    def _activate_after_color_preset_action(self) -> None:
        """Raise and activate the teleprompter window."""
        if not self.isVisible():
            return
        self.show()
        self.setWindowState(
            (self.windowState() & ~Qt.WindowMinimized) | Qt.WindowActive
        )
        self.raise_()
        self.activateWindow()
        QApplication.setActiveWindow(self)
    
    def build_prompter_content(self) -> None:
        """Build prompter content."""
        clrs = self.cfg["colors"]
        self.prompter_scene.clear()
        self.time_map = []
        self.list_of_replicas.clear()

        self.prompter_scene.setBackgroundBrush(QColor(clrs["bg"]))
        self.header_panel.setStyleSheet(
            f"background-color: {clrs['header_bg']};"
        )
        self.update_big_timecode_font_size()

        lines = self.main_app.get_episode_lines(self.ep_num)
        if not lines:
            item = QGraphicsTextItem(
                "Рабочий текст не найден.\n"
                "Создайте его из субтитров в окне «Файлы проекта»."
            )
            item.setFont(QFont("Arial", self.cfg["f_text"], QFont.Bold))
            item.setDefaultTextColor(QColor(clrs["active_text"]))
            item.setTextWidth(760)
            item.setPos(40, 1000)
            self.prompter_scene.addItem(item)
            self.prompter_scene.setSceneRect(-50, 0, 900, 1800)
            return

        lines.sort(key=lambda x: x['s'])
        export_service = ExportService(self.main_app.data)
        
        merge_cfg = self.main_app.data.get("replica_merge_config", {})
        processed = export_service.process_merge_logic(
            lines, merge_cfg
        )
        
        y_cursor = 1000.0
        width = 850
        
        f_tc = QFont("Courier New", self.cfg["f_tc"])
        f_char = QFont("Arial", self.cfg["f_char"], QFont.Bold)
        f_actor = QFont("Arial", self.cfg["f_actor"])
        f_actor.setItalic(True)
        f_text = QFont("Arial", self.cfg["f_text"])
        
        all_actor_ids = set(self.main_app.data["actors"].keys())
        active_actor_ids = (
            set(self.highlight_ids) 
            if self.highlight_ids is not None 
            else all_actor_ids
        )
        
        for i, replica in enumerate(processed):
            actor_id = get_actor_for_character(
                self.main_app.data, replica['char'], self.ep_num
            )
            actor_info = self.main_app.data["actors"].get(
                actor_id, {"name": "-", "color": "#FFFFFF"}
            )
            is_active = actor_id in active_actor_ids
            
            if is_active:
                char_col = QColor(actor_info['color'])
                if char_col.value() < 100:
                    char_col = QColor("white")
                text_col = QColor(clrs["active_text"])
                tc_col = QColor(clrs["tc"])
                
                self.list_of_replicas.addItem(
                    f"{format_seconds_to_tc(replica['s'])} - {replica['char']}"
                )
                self.list_of_replicas.item(
                    self.list_of_replicas.count() - 1
                ).setData(Qt.UserRole, replica['s'])
                
                if self.last_known_time == 0.0:
                    self.last_known_time = replica['s']
            else:
                inactive_col = QColor(clrs["inactive_text"])
                char_col = text_col = tc_col = inactive_col
            
            row_y = y_cursor
            
            if replica.get('_working_text'):
                editable_ids = [replica.get('id', i)]
            else:
                editable_ids = replica.get('source_ids', [replica.get('id', i)])

            item_char = EditableCharacterItem(
                replica['char'], self, editable_ids
            )
            item_char.setFont(f_char)
            item_char.setDefaultTextColor(char_col)
            item_char.setPos(0, row_y)
            self.prompter_scene.addItem(item_char)
            
            # Timecode
            item_tc = QGraphicsTextItem(
                f"[{format_seconds_to_tc(replica['s'])}] "
            )
            item_tc.setFont(f_tc)
            item_tc.setDefaultTextColor(tc_col)
            item_tc.setPos(
                item_char.boundingRect().width() + 20,
                row_y + (self.cfg["f_char"] - self.cfg["f_tc"]) / 2
            )
            self.prompter_scene.addItem(item_tc)
            
            item_actor = QGraphicsTextItem(f"({actor_info['name']}) ")
            item_actor.setFont(f_actor)
            item_actor.setDefaultTextColor(char_col)
            item_actor.setPos(
                item_char.boundingRect().width() + 
                item_tc.boundingRect().width() + 40,
                row_y + (self.cfg["f_char"] - self.cfg["f_actor"]) / 2
            )
            self.prompter_scene.addItem(item_actor)
            
            y_cursor += item_char.boundingRect().height()
            
            item_text = EditableTextItem(
                replica.get('text', ''), self, editable_ids
            )
            item_text.setFont(f_text)
            item_text.setDefaultTextColor(text_col)
            item_text.setTextWidth(width)
            item_text.setPos(0, y_cursor)
            self.prompter_scene.addItem(item_text)
            
            self.time_map.append({
                'index': i,
                's': replica['s'],
                'e': replica['e'],
                'y_center': row_y + (
                    item_char.boundingRect().height() + 
                    item_text.boundingRect().height()
                ) / 2,
                'active': is_active
            })
            y_cursor += (
                item_text.boundingRect().height() + 
                (self.cfg["f_text"] * 1.8)
            )
        
        self.prompter_scene.setSceneRect(-50, 0, width + 100, y_cursor + 1000)
        self.update_view_position_by_time(self.last_known_time)
        
        if hasattr(self, 'float_window') and self.float_window:
            self.float_window.sync_episode_combo()
            self.float_window.sync_replica_list()
    
    def update_timecode_display(self, time_seconds: float) -> None:
        """Update timecode display."""
        self.last_known_time = time_seconds

        ms = int((time_seconds % 1) * 1000)
        self.lbl_big_timecode.setText(
            f"{format_seconds_to_tc(time_seconds)}.{ms:03d}"
        )

        if self.header_panel.isVisible():
            self.update_big_timecode_font_size()

    def update_view_position_by_time(self, time_seconds: float) -> None:
        """Update view position by time."""
        self.update_timecode_display(time_seconds)

        if not self.time_map:
            return

        target_y = 0
        target_list_idx = -1

        for i, segment in enumerate(self.time_map):
            if time_seconds >= segment['s'] and time_seconds <= segment['e']:
                target_y = segment['y_center']
                if segment['active']:
                    for row in range(self.list_of_replicas.count()):
                        if abs(
                            self.list_of_replicas.item(row).data(Qt.UserRole) -
                            segment['s']
                        ) < 0.01:
                            target_list_idx = row
                            break
                break
            elif time_seconds < segment['s']:
                prev = self.time_map[i - 1] if i > 0 else None
                if prev:
                    gap = segment['s'] - prev['e']
                    ratio = (
                        (time_seconds - prev['e']) / gap
                        if gap > 0 else 0
                    )
                    target_y = prev['y_center'] + (
                        segment['y_center'] - prev['y_center']
                    ) * ratio
                else:
                    target_y = segment['y_center']
                break

            if i == len(self.time_map) - 1:
                target_y = segment['y_center'] + (
                    time_seconds - segment['e']
                ) * 100

        if target_list_idx != -1:
            self.list_of_replicas.blockSignals(True)
            self.list_of_replicas.setCurrentRow(target_list_idx)
            self.list_of_replicas.scrollToItem(
                self.list_of_replicas.currentItem(),
                QAbstractItemView.PositionAtCenter
            )
            self.list_of_replicas.blockSignals(False)

        view_h = self.prompter_view.height()
        offset = (0.5 - self.cfg["focus_ratio"]) * view_h
        target_full_y = target_y + offset

        tau = self.compute_scroll_tau()
        if tau <= 0.0:
            self._scroll_target_y = None
            self.prompter_view.centerOn(425, target_full_y)
            if self.smooth_scroll_timer.isActive():
                self.smooth_scroll_timer.stop()
        else:
            self._scroll_target_y = target_full_y
            if not self.smooth_scroll_timer.isActive():
                self.smooth_scroll_timer.start()
    
    def jump_to_specific_time(self, t: float) -> None:
        """Jump to specific time."""
        self.exit_manual_scroll_override()
        self.last_known_time = t
        self.update_view_position_by_time(t)
        
        if (
            OSC_AVAILABLE and 
            self.btn_osc.isChecked() and 
            self.cfg["sync_out"]
        ):
            if self.osc_client:
                try:
                    reaper_time = t
                    if self.cfg.get("reaper_offset_enabled", False):
                        reaper_time = t + self.cfg.get(
                            "reaper_offset_seconds", -2.0
                        )
                    self.osc_client.send_message("/time", float(reaper_time))
                    self.osc_client.send_message("/track/0/pos", float(reaper_time))
                except Exception as e:
                    logger.warning(f"OSC send error: {e}")
    
    def navigate_to_replica_in_direction(self, direction: int) -> None:
        """Navigate to replica in direction."""
        if not self.time_map:
            return
        
        current_idx = -1
        min_d = 999999
        
        for i, seg in enumerate(self.time_map):
            if seg['active']:
                d = abs(self.last_known_time - seg['s'])
                if d < min_d:
                    min_d = d
                    current_idx = i
        
        if current_idx < 0:
            for i, seg in enumerate(self.time_map):
                if seg['active']:
                    current_idx = i
                    break
        
        if current_idx < 0:
            return
        
        step = 1 if direction > 0 else -1
        target_idx = current_idx
        
        for _ in range(len(self.time_map)):
            target_idx += step
            if 0 <= target_idx < len(self.time_map):
                if self.time_map[target_idx]['active']:
                    target_time = self.time_map[target_idx]['s']
                    self.jump_to_specific_time(target_time)
                    
                    list_idx = -1
                    for i in range(self.list_of_replicas.count()):
                        item = self.list_of_replicas.item(i)
                        if item and abs(
                            item.data(Qt.UserRole) - target_time
                        ) < 0.01:
                            list_idx = i
                            break
                    
                    if list_idx >= 0:
                        self.list_of_replicas.setCurrentRow(list_idx)
                        if hasattr(self, 'float_window') and self.float_window:
                            self.float_window.update_selection(list_idx)
                    return
            else:
                if direction > 0:
                    for i, seg in enumerate(self.time_map):
                        if seg['active']:
                            self.jump_to_specific_time(seg['s'])
                            if hasattr(self, 'float_window') and self.float_window:
                                self.float_window.update_selection(0)
                            return
                else:
                    for i in range(len(self.time_map) - 1, -1, -1):
                        if self.time_map[i]['active']:
                            self.jump_to_specific_time(self.time_map[i]['s'])
                            for li in range(self.list_of_replicas.count()):
                                item = self.list_of_replicas.item(li)
                                if item and abs(
                                    item.data(Qt.UserRole) - self.time_map[i]['s']
                                ) < 0.01:
                                    if hasattr(self, 'float_window') and self.float_window:
                                        self.float_window.update_selection(li)
                                    return
                            return
                break
    
    def on_replica_list_item_clicked(self, item: QListWidgetItem) -> None:
        """Handle replica list item click."""
        self.jump_to_specific_time(item.data(Qt.UserRole))
    
    def save_current_config_to_project(self) -> None:
        """Save current config to project."""
        self.cfg["sync_in"] = self.chk_follow_reaper.isChecked()
        self.cfg["sync_out"] = self.chk_reaper_follow.isChecked()
        self.cfg["osc_enabled"] = self.btn_osc.isChecked()
        self.cfg["reaper_offset_enabled"] = self.chk_offset.isChecked()
        self.cfg["reaper_offset_seconds"] = self.spin_offset.value()
        if self.cfg["sync_in"]:
            self.exit_manual_scroll_override()
        
        self.main_app.save_global_prompter_settings(self.cfg)
        
        self.main_app.set_dirty(True)
    
    def toggle_osc_connection_status(self, checked: bool) -> None:
        """Toggle osc connection status."""
        self.cfg["osc_enabled"] = bool(checked)
        if checked:
            try:
                if self.osc_thread:
                    self.osc_thread.stop()
                self.osc_thread = OscWorker(self.cfg["port_in"])
                self.osc_thread.time_changed.connect(
                    self.on_osc_time_packet_received
                )
                self.osc_thread.navigation_requested.connect(
                    self.navigate_from_osc
                )
                self.osc_thread.start()
                from pythonosc.udp_client import SimpleUDPClient
                self.osc_client = SimpleUDPClient(
                    "127.0.0.1", self.cfg["port_out"]
                )
                self.btn_osc.setText(translate_source("OSC Связь: Активна"))
            except Exception as e:
                logger.error(f"OSC client error: {e}")
                if self.osc_thread:
                    self.osc_thread.stop()
                    self.osc_thread = None
                self.osc_client = None
                self.cfg["osc_enabled"] = False
                self.btn_osc.blockSignals(True)
                self.btn_osc.setChecked(False)
                self.btn_osc.blockSignals(False)
                self.btn_osc.setText(translate_source("Ошибка OSC"))
        else:
            if self.osc_thread:
                self.osc_thread.stop()
                self.osc_thread = None
            self.osc_client = None
            self.btn_osc.setText(translate_source("Включить OSC связь"))
            self.btn_osc.setStyleSheet("")

        if not getattr(self, '_initializing', False):
            self.main_app.save_global_prompter_settings(self.cfg)
            self.main_app.set_dirty(True)
    
    @Slot(float)
    def on_osc_time_packet_received(self, time_val: float) -> None:
        """Handle osc time packet received."""
        # Reaper-specific handling
        if self.cfg.get("sync_in", False):
            if self._manual_scroll_override:
                self.update_timecode_display(time_val)
            else:
                self.update_view_position_by_time(time_val)
    
    @Slot(str)
    def navigate_from_osc(self, direction: str) -> None:
        """Navigate from osc."""
        self.exit_manual_scroll_override()
        step = 1 if direction == "next" else -1
        self.navigate_to_replica_in_direction(step)
    
    def toggle_mirror_mode(self, checked: bool) -> None:
        """Toggle mirror mode."""
        self.cfg["is_mirrored"] = checked
        self.prompter_view.resetTransform()
        if checked:
            self.prompter_view.scale(-1, 1)
        self.main_app.set_dirty(True)
    
    def toggle_header_visibility(self, checked: bool) -> None:
        """Toggle header visibility."""
        self.cfg["show_header"] = checked
        self.header_panel.setVisible(checked)
        QTimer.singleShot(50, self.update_big_timecode_font_size)
        self.main_app.set_dirty(True)
    
    def open_actor_filter_dialog(self) -> None:
        """Open actor filter dialog."""
        from .dialogs.actor_filter import ActorFilterDialog
        
        all_ids = list(self.main_app.data["actors"].keys())
        dialog = ActorFilterDialog(
            self.main_app.data["actors"],
            self.highlight_ids if self.highlight_ids is not None else all_ids,
            parent=self
        )
        if dialog.exec():
            sel = dialog.get_selected()
            self.highlight_ids = (
                None if len(sel) == len(all_ids) else sel
            )
            self.build_prompter_content()

    def keyPressEvent(self, event) -> None:
        """Keypressevent."""
        modifiers = event.modifiers()
        is_ctrl = modifiers & Qt.ControlModifier
        
        if event.key() == Qt.Key_Left:
            self.navigate_to_replica_in_direction(-1)
        elif event.key() == Qt.Key_Right:
            self.navigate_to_replica_in_direction(1)
        elif event.key() == Qt.Key_Up and is_ctrl:
            self.navigate_to_replica_in_direction(-1)
        elif event.key() == Qt.Key_Down and is_ctrl:
            self.navigate_to_replica_in_direction(1)
        else:
            super().keyPressEvent(event)
    
    def _split_merged_text(self, text: str, ids: List[int]) -> List[str]:
        """Split merged text."""
        return self.navigation_service.split_merged_text(text, ids)

    def get_project_character_names(self) -> List[str]:
        """Return all known project character names for autocompletion."""
        names: Set[str] = set()

        for char_name in self.main_app.data.get("global_map", {}).keys():
            if char_name:
                names.add(str(char_name))

        episode_maps = self.main_app.data.get("episode_actor_map", {})
        if isinstance(episode_maps, dict):
            for episode_map in episode_maps.values():
                if not isinstance(episode_map, dict):
                    continue
                for char_name in episode_map.keys():
                    if char_name:
                        names.add(str(char_name))

        for lines in self.main_app.data.get("loaded_episodes", {}).values():
            if not isinstance(lines, list):
                continue
            for line in lines:
                char_name = line.get("char") if isinstance(line, dict) else None
                if char_name:
                    names.add(str(char_name))

        for ep_num in self.main_app.data.get("episodes", {}).keys():
            try:
                for line in self.main_app.get_episode_lines(str(ep_num)):
                    char_name = line.get("char")
                    if char_name:
                        names.add(str(char_name))
            except Exception as e:
                logger.debug(
                    "Could not collect characters for episode %s: %s",
                    ep_num,
                    e
                )

        return sorted(names, key=str.lower)

    def handle_character_edited(self, line_id: Any, new_character: str) -> None:
        """Handle character edited."""
        new_character = new_character.strip()
        if not new_character:
            return

        if (
            hasattr(self.main_app, "ensure_working_text_for_episode") and
            not self.main_app.ensure_working_text_for_episode(
                str(self.ep_num),
                "изменить персонажа реплики"
            )
        ):
            return

        ids = []
        if isinstance(line_id, (list, tuple)):
            ids = [x for x in line_id]
        else:
            ids = [line_id]

        loaded = self.main_app.data.setdefault('loaded_episodes', {})
        ep_key = (
            self.ep_num if self.ep_num in loaded
            else str(self.ep_num) if str(self.ep_num) in loaded
            else None
        )

        try:
            if ep_key is not None:
                lines = loaded[ep_key]
            else:
                lines = self.main_app.get_episode_lines(self.ep_num)
        except Exception:
            lines = self.main_app.get_episode_lines(self.ep_num)

        def find_line(lid: Any):
            lid_str = str(lid)
            for idx, line in enumerate(lines):
                if str(line.get('id')) == lid_str:
                    return line
                try:
                    if int(lid) == idx:
                        return line
                except (TypeError, ValueError):
                    pass
            return None

        updated_any = False
        for sid in ids:
            target = find_line(sid)
            if target and target.get('char') != new_character:
                target['char'] = new_character
                updated_any = True

        if updated_any:
            try:
                script_text_service = ScriptTextService()
                for sid in ids:
                    script_text_service.update_line_character(
                        self.main_app.data,
                        str(self.ep_num),
                        sid,
                        new_character
                    )
            except Exception as e:
                logger.warning(f"Error saving working text character: {e}")

            try:
                self.main_app.data['loaded_episodes'][str(self.ep_num)] = lines
            except Exception:
                pass

            self._has_text_changes = True
            try:
                self.main_app.set_dirty(True)
            except Exception:
                pass

            try:
                self.build_prompter_content()
            except Exception as e:
                log_exception(logger, "Error rebuilding content", e)
    
    def handle_text_edited(self, line_id: Any, new_text: str) -> None:
        """Handle text edited."""
        if (
            hasattr(self.main_app, "ensure_working_text_for_episode") and
            not self.main_app.ensure_working_text_for_episode(
                str(self.ep_num),
                "редактировать текст реплики"
            )
        ):
            return

        ids = []
        if isinstance(line_id, (list, tuple)):
            ids = [int(x) for x in line_id]
        else:
            try:
                ids = [int(line_id)]
            except ValueError:
                return
        
        if 'loaded_episodes' not in self.main_app.data:
            self.main_app.data['loaded_episodes'] = {}
        
        loaded = self.main_app.data.get('loaded_episodes', {})
        ep_key = (
            self.ep_num if self.ep_num in loaded 
            else str(self.ep_num) if str(self.ep_num) in loaded 
            else None
        )
        
        try:
            if ep_key is not None:
                lines = loaded[ep_key]
            else:
                lines = self.main_app.get_episode_lines(self.ep_num)
        except Exception:
            lines = self.main_app.get_episode_lines(self.ep_num)
        
        def find_line(lid: int):
            return next(
                (l for l in lines if int(l.get('id', -1)) == int(lid)), 
                None
            )
        
        updated_any = False
        
        if len(ids) == 1:
            target = find_line(ids[0])
            if target:
                target['text'] = new_text
                updated_any = True
        else:
            parts = self._split_merged_text(new_text.strip(), ids)
            
            if len(parts) == len(ids):
                for sid, txt in zip(ids, parts):
                    t = find_line(sid)
                    if t:
                        t['text'] = txt
                        updated_any = True
            else:
                parts = [
                    p.strip() for p in new_text.strip().split('\n') 
                    if p.strip()
                ]
                if len(parts) == len(ids):
                    for sid, txt in zip(ids, parts):
                        t = find_line(sid)
                        if t:
                            t['text'] = txt
                            updated_any = True
                else:
                    originals = [find_line(sid) for sid in ids]
                    orig_texts = [
                        o.get('text', '') if o else '' for o in originals
                    ]
                    lengths = [max(1, len(t)) for t in orig_texts]
                    total = sum(lengths) if sum(lengths) > 0 else len(ids)
                    total_chars = len(new_text.strip())
                    
                    if total_chars == 0:
                        for o in originals:
                            if o:
                                o['text'] = ''
                                updated_any = True
                    else:
                        offsets = []
                        acc = 0
                        for L in lengths[:-1]:
                            take = int(round(total_chars * (L / total)))
                            offsets.append(take)
                            acc += take
                        offsets.append(total_chars - acc)
                        
                        pos = 0
                        for o, take in zip(originals, offsets):
                            piece = new_text.strip()[pos:pos + take].strip()
                            pos += take
                            if o is not None:
                                o['text'] = piece
                                updated_any = True
        
        if updated_any:
            try:
                script_text_service = ScriptTextService()
                if len(ids) == 1:
                    script_text_service.update_line_text(
                        self.main_app.data,
                        str(self.ep_num),
                        ids[0],
                        new_text
                    )
            except Exception as e:
                logger.warning(f"Error saving working text: {e}")

            try:
                self.main_app.data['loaded_episodes'][str(self.ep_num)] = lines
            except Exception:
                pass
            
            self._has_text_changes = True
            try:
                self.main_app.set_dirty(True)
            except Exception:
                pass
            
            try:
                self.build_prompter_content()
            except Exception as e:
                log_exception(logger, "Error rebuilding content", e)

    def handle_text_split_to_character(
        self,
        line_id: Any,
        remaining_text: str,
        split_text: str,
        split_character: str
    ) -> None:
        """Split selected text into a new character replica."""
        split_text = split_text.strip()
        split_character = split_character.strip()
        if not split_text or not split_character:
            return

        if (
            hasattr(self.main_app, "ensure_working_text_for_episode") and
            not self.main_app.ensure_working_text_for_episode(
                str(self.ep_num),
                "перенести часть реплики другому персонажу"
            )
        ):
            return

        if isinstance(line_id, (list, tuple)):
            if len(line_id) != 1:
                return
            target_id = line_id[0]
        else:
            target_id = line_id

        script_text_service = ScriptTextService()
        try:
            updated = script_text_service.split_line_to_character(
                self.main_app.data,
                str(self.ep_num),
                target_id,
                remaining_text,
                split_text,
                split_character
            )
        except Exception as e:
            logger.warning(f"Error splitting working text: {e}")
            return

        if not updated:
            return

        try:
            lines = script_text_service.load_episode_lines(
                self.main_app.data,
                str(self.ep_num)
            )
            if lines:
                self.main_app.data.setdefault(
                    'loaded_episodes',
                    {}
                )[str(self.ep_num)] = lines
        except Exception as e:
            logger.warning(f"Error reloading split working text: {e}")

        self._has_text_changes = True
        try:
            self.main_app.set_dirty(True)
        except Exception:
            pass

        try:
            self.build_prompter_content()
        except Exception as e:
            log_exception(logger, "Error rebuilding content", e)

    def refresh_episode_data(self) -> None:
        """Refresh episode data."""
        self.main_app.episode_service.invalidate_episode(self.ep_num)
        
        try:
            self.build_prompter_content()
        except Exception as e:
            log_exception(logger, "Error refreshing episode data", e)

    def refresh_cast_assignments(self) -> None:
        """Refresh actor assignments without reopening the teleprompter."""
        current_time = self.last_known_time
        vertical_scroll = self.prompter_view.verticalScrollBar().value()
        horizontal_scroll = self.prompter_view.horizontalScrollBar().value()
        manual_scroll_override = self._manual_scroll_override

        try:
            self.build_prompter_content()
            if current_time > 0:
                self.update_view_position_by_time(current_time)
            if manual_scroll_override:
                self._manual_scroll_override = True
                self.cancel_pending_prompter_scroll()
                self.prompter_view.verticalScrollBar().setValue(vertical_scroll)
                self.prompter_view.horizontalScrollBar().setValue(horizontal_scroll)
        except Exception as e:
            log_exception(logger, "Error refreshing cast assignments", e)

    def closeEvent(self, event) -> None:
        """Closeevent."""
        if self.osc_thread:
            self.osc_thread.stop()

        if hasattr(self, 'float_window') and self.float_window:
            self.float_window.close()
            self.float_window = None

        event.accept()
