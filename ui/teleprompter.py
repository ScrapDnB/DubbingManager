"""Окно телесуфлёра"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, 
    QLabel, QSpinBox, QSlider, QCheckBox, QFrame,
    QScrollArea, QSplitter, QToolBar, QListWidget, 
    QListWidgetItem, QAbstractItemView, QMessageBox,
    QDoubleSpinBox, QSizePolicy, QWidget, QFormLayout,
    QGroupBox, QTextEdit, QDialogButtonBox, QGraphicsView,
    QGraphicsScene, QGraphicsTextItem
)
from PySide6.QtGui import (
    QColor, QFont, QPainter, QPen, QBrush
)
from PySide6.QtCore import (
    Qt, QTimer, Signal, Slot, QRectF, QEvent
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
)
from services import ExportService
from services.osc_worker import OscWorker, OSC_AVAILABLE
from services.hotkey_manager import GlobalHotkeyManager, PYNPUT_AVAILABLE
from utils.helpers import ass_time_to_seconds, format_seconds_to_tc, log_exception

logger = logging.getLogger(__name__)


class CollapsibleSection(QFrame):
    """Сворачиваемый раздел настроек"""
    
    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.StyledPanel)
        self.setStyleSheet(
            "CollapsibleSection { background: #2b2b2b; border-radius: 4px; }"
        )
        
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        
        # Заголовок
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(8, 6, 8, 6)
        
        self.toggle_btn = QPushButton()
        self.toggle_btn.setFixedSize(20, 20)
        self.toggle_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                color: #aaa;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover { color: white; }
        """)
        self.toggle_btn.clicked.connect(self.toggle)
        header_layout.addWidget(self.toggle_btn)
        
        title_label = QLabel(title)
        title_label.setStyleSheet(
            "color: white; font-weight: bold; font-size: 13px;"
        )
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        
        self.header_widget = QWidget()
        self.header_widget.setLayout(header_layout)
        self.header_widget.setStyleSheet("background: transparent;")
        self.main_layout.addWidget(self.header_widget)
        
        # Контент
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(8, 0, 8, 8)
        self.content_layout.setSpacing(4)
        self.main_layout.addWidget(self.content_widget)
        
        self.expanded = False
        self.content_widget.setVisible(False)
        self.update_arrow()
    
    def update_arrow(self) -> None:
        if self.expanded:
            self.toggle_btn.setText("▼")
        else:
            self.toggle_btn.setText("▶")
            self.toggle_btn.setStyleSheet("""
                QPushButton {
                    background: transparent;
                    border: none;
                    color: #666;
                    font-size: 14px;
                    font-weight: bold;
                }
                QPushButton:hover { color: #888; }
            """)
    
    def toggle(self) -> None:
        self.expanded = not self.expanded
        self.content_widget.setVisible(self.expanded)
        self.update_arrow()
    
    def addWidget(self, widget) -> None:
        self.content_layout.addWidget(widget)
    
    def addLayout(self, layout) -> None:
        self.content_layout.addLayout(layout)


class EditTextDialog(QDialog):
    """Диалог редактирования текста реплики"""
    
    def __init__(self, parent=None, initial_text: str = ""):
        super().__init__(parent)
        self.setWindowTitle("Редактирование реплики")
        self.resize(EDIT_TEXT_DIALOG_WIDTH, EDIT_TEXT_DIALOG_HEIGHT)
        
        layout = QVBoxLayout(self)
        self.text_edit = QTextEdit()
        self.text_edit.setPlainText(initial_text)
        layout.addWidget(self.text_edit)
        
        btn_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)


class EditableTextItem(QGraphicsTextItem):
    """Редактируемый текстовый элемент на сцене"""
    
    def __init__(
        self, 
        text: str, 
        window: 'TeleprompterWindow', 
        line_id: Optional[Union[int, List[int]]] = None
    ):
        super().__init__(text)
        self.window = window
        self.line_id = line_id
    
    def mouseDoubleClickEvent(self, event) -> None:
        try:
            initial = self.toPlainText()
            dialog = EditTextDialog(self.window, initial)
            if dialog.exec() == QDialog.Accepted:
                new_text = dialog.text_edit.toPlainText()
                if new_text != initial:
                    try:
                        self.window.handle_text_edited(self.line_id, new_text)
                    except Exception as e:
                        log_exception(logger, "Error editing text", e)
        except Exception as e:
            log_exception(logger, "Error in mouseDoubleClickEvent", e)
        # Не вызываем базовую реализацию — избегаем use-after-free


class TeleprompterFloatWindow(QDialog):
    """Плавающее окно управления телесуфлёром"""
    
    def __init__(self, teleprompter: 'TeleprompterWindow'):
        super().__init__(None)
        self.teleprompter = teleprompter
        self.setWindowTitle("Управление телесуфлёром")
        self.setWindowFlags(
            Qt.Window |
            Qt.WindowStaysOnTopHint |
            Qt.CustomizeWindowHint |
            Qt.WindowTitleHint |
            Qt.WindowCloseButtonHint
        )
        self.setAttribute(Qt.WA_MacAlwaysShowToolWindow)
        self.resize(PROMPTER_FLOAT_WINDOW_WIDTH, PROMPTER_FLOAT_WINDOW_HEIGHT)
        
        self._init_ui()
    
    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        
        # Кнопки навигации
        btn_layout = QHBoxLayout()
        
        self.btn_prev = QPushButton("⏮ Назад")
        self.btn_prev.setMinimumHeight(50)
        self.btn_prev.clicked.connect(
            lambda: self.teleprompter.navigate_to_replica_in_direction(-1)
        )
        btn_layout.addWidget(self.btn_prev)
        
        self.btn_next = QPushButton("Вперёд ⏭")
        self.btn_next.setMinimumHeight(50)
        self.btn_next.clicked.connect(
            lambda: self.teleprompter.navigate_to_replica_in_direction(1)
        )
        btn_layout.addWidget(self.btn_next)
        
        layout.addLayout(btn_layout)
        
        # Список реплик
        layout.addWidget(QLabel("<b>Список реплик:</b>"))
        self.replica_list = QListWidget()
        self.replica_list.itemClicked.connect(self.on_replica_clicked)
        layout.addWidget(self.replica_list)
        
        # Кнопка скрытия
        btn_close = QPushButton("Скрыть")
        btn_close.clicked.connect(self.hide_window)
        layout.addWidget(btn_close)
        
        self.sync_replica_list()
    
    def sync_replica_list(self) -> None:
        """Синхронизация списка реплик"""
        if not self.teleprompter:
            return
        
        current_row = self.replica_list.currentRow()
        self.replica_list.blockSignals(True)
        self.replica_list.clear()
        
        for i in range(self.teleprompter.list_of_replicas.count()):
            item = self.teleprompter.list_of_replicas.item(i)
            new_item = QListWidgetItem(item.text())
            new_item.setData(Qt.UserRole, item.data(Qt.UserRole))
            self.replica_list.addItem(new_item)
        
        if 0 <= current_row < self.replica_list.count():
            self.replica_list.setCurrentRow(current_row)
        self.replica_list.blockSignals(False)
    
    def on_replica_clicked(self, item: QListWidgetItem) -> None:
        """Переход к выбранной реплике"""
        if self.teleprompter:
            self.teleprompter.jump_to_specific_time(
                item.data(Qt.UserRole)
            )
    
    def update_selection(self, index: int) -> None:
        """Обновление выбранного элемента"""
        if 0 <= index < self.replica_list.count():
            self.replica_list.blockSignals(True)
            self.replica_list.setCurrentRow(index)
            self.replica_list.blockSignals(False)
    
    def hide_window(self) -> None:
        """Скрыть окно"""
        self.hide()
        if hasattr(self, 'teleprompter') and self.teleprompter:
            self.teleprompter.hide_float_window()
            # Возвращаем фокус окну телесуфлёра
            self.teleprompter.activateWindow()
            self.teleprompter.raise_()

    def closeEvent(self, event) -> None:
        """Обработка закрытия — скрываем вместо закрытия"""
        self.hide_window()
        event.ignore()


class TeleprompterWindow(QDialog):
    """Основное окно телесуфлёра"""
    
    def __init__(self, main_app: Any, ep_num: str):
        super().__init__(None)
        self.main_app = main_app
        self.ep_num = ep_num
        self.setWindowTitle(f"Телесуфлёр - Серия {ep_num}")
        self.resize(PROMPTER_WINDOW_WIDTH, PROMPTER_WINDOW_HEIGHT)
        
        # Инициализация настроек
        self._init_config()
        
        # Переменные состояния
        self.time_map: List[Dict[str, Any]] = []
        self.osc_thread: Optional[OscWorker] = None
        self.osc_client = None
        self.last_known_time = 0.0
        self.highlight_ids: Optional[List[str]] = None
        self._has_text_changes = False
        self._initializing = True
        
        # UI
        self._init_ui()
        self.build_prompter_content()
        self.setup_global_hotkeys()
        
        self._initializing = False
    
    def _init_config(self) -> None:
        """Инициализация конфигурации с защитой от падений"""
        if (
            "prompter_config" not in self.main_app.data or 
            self.main_app.data["prompter_config"] is None
        ):
            self.main_app.data["prompter_config"] = DEFAULT_PROMPTER_CONFIG.copy()
        
        self.cfg = self.main_app.data["prompter_config"]
        
        # Проверка словаря цветов для совместимости
        if "colors" not in self.cfg or not isinstance(self.cfg["colors"], dict):
            self.cfg["colors"] = DEFAULT_PROMPTER_CONFIG["colors"].copy()
        else:
            for color_key, color_value in DEFAULT_PROMPTER_CONFIG["colors"].items():
                if color_key not in self.cfg["colors"]:
                    self.cfg["colors"][color_key] = color_value
    
    def _init_ui(self) -> None:
        """Инициализация интерфейса"""
        self.root_layout = QVBoxLayout(self)
        self.root_layout.setContentsMargins(0, 0, 0, 0)
        self.root_layout.setSpacing(0)
        
        # Тулбар
        self._init_toolbar()
        
        # Сплиттеры
        self._init_splitters()
        
        # Таймер плавной прокрутки
        self.smooth_scroll_timer = QTimer()
        self.smooth_scroll_timer.setInterval(16)
        self.smooth_scroll_timer.timeout.connect(self.smooth_scroll_step)
        self._scroll_target_y: Optional[float] = None
    
    def _init_toolbar(self) -> None:
        """Инициализация тулбара"""
        self.toolbar = QToolBar("Управление")
        self.toolbar.setMovable(False)
        self.toolbar.setStyleSheet(
            "QToolBar { padding: 5px; background: #333; "
            "border-bottom: 1px solid #111; }"
        )
        
        self.btn_toggle_settings = QPushButton("⚙ Панель настроек")
        self.btn_toggle_settings.setCheckable(True)
        self.btn_toggle_settings.clicked.connect(
            self.toggle_settings_panel_visibility
        )
        self.toolbar.addWidget(self.btn_toggle_settings)
        
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
        
        toolbar_spacer = QWidget()
        toolbar_spacer.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Preferred
        )
        self.toolbar.addWidget(toolbar_spacer)
        
        btn_close = QPushButton("Закрыть окно")
        btn_close.clicked.connect(self.close)
        self.toolbar.addWidget(btn_close)
        
        self.root_layout.addWidget(self.toolbar)
    
    def _init_splitters(self) -> None:
        """Инициализация сплиттеров"""
        self.v_splitter = QSplitter(Qt.Vertical)
        self.v_splitter.setHandleWidth(8)
        self.v_splitter.setStyleSheet(
            "QSplitter::handle { background: #444; }"
        )
        self.v_splitter.splitterMoved.connect(
            lambda pos, idx: self.update_big_timecode_font_size()
        )
        
        # Хедер
        self.header_panel = QFrame()
        self.header_panel.setObjectName("HeaderPanel")
        self.header_panel.setMinimumHeight(0)
        header_layout = QVBoxLayout(self.header_panel)
        header_layout.setContentsMargins(0, 0, 0, 0)
        
        self.lbl_big_timecode = QLabel("0:00:00.000")
        self.lbl_big_timecode.setAlignment(Qt.AlignCenter)
        header_layout.addWidget(self.lbl_big_timecode)
        self.v_splitter.addWidget(self.header_panel)
        
        # Горизонтальный сплиттер
        self.h_splitter = QSplitter(Qt.Horizontal)
        self.h_splitter.setHandleWidth(8)
        
        # Левая панель
        self._init_side_panel()
        self.h_splitter.addWidget(self.side_panel_widget)
        
        # Графическая сцена
        self.prompter_scene = QGraphicsScene()
        self.prompter_view = QGraphicsView(self.prompter_scene)
        self.prompter_view.setRenderHints(
            QPainter.Antialiasing | QPainter.TextAntialiasing
        )
        self.prompter_view.setDragMode(QGraphicsView.ScrollHandDrag)
        self.prompter_view.setFrameShape(QFrame.NoFrame)
        self.prompter_view.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.prompter_view.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.h_splitter.addWidget(self.prompter_view)

        self.v_splitter.addWidget(self.h_splitter)
        self.root_layout.addWidget(self.v_splitter)

        # Начальные размеры
        self.header_panel.setVisible(self.cfg["show_header"])
        self.v_splitter.setSizes(PROMPTER_V_SPLITTER_SIZES)
        self.h_splitter.setSizes(PROMPTER_H_SPLITTER_SIZES)
    
    def _init_side_panel(self) -> None:
        """Инициализация боковой панели настроек"""
        self.side_panel_widget = QWidget()
        self.side_panel_widget.setMinimumWidth(PROMPTER_SIDE_PANEL_MIN_WIDTH)
        self.side_layout = QVBoxLayout(self.side_panel_widget)
        
        # Скролл для настроек
        self.settings_scroll_area = QScrollArea()
        self.settings_scroll_area.setWidgetResizable(True)
        self.settings_scroll_area.setFrameShape(QFrame.NoFrame)
        
        settings_container = QWidget()
        settings_v_layout = QVBoxLayout(settings_container)
        settings_v_layout.setSpacing(4)
        
        # Секции настроек
        self._init_font_settings(settings_v_layout)
        self._init_focus_settings(settings_v_layout)
        self._init_scroll_settings(settings_v_layout)
        self._init_view_settings(settings_v_layout)
        self._init_osc_settings(settings_v_layout)
        
        self.settings_scroll_area.setWidget(settings_container)
        self.side_layout.addWidget(self.settings_scroll_area)
        
        # Список реплик
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
        """Настройка шрифтов"""
        fonts_section = CollapsibleSection("Размеры шрифтов элементов")
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
        """Настройка позиции линии чтения"""
        focus_section = CollapsibleSection("Позиция линии чтения")
        focus_layout = QVBoxLayout()

        self.slider_focus_pos = QSlider(Qt.Horizontal)
        self.slider_focus_pos.setRange(10, PROMPTER_FOCUS_SLIDER_MAX)
        self.slider_focus_pos.setValue(int(self.cfg["focus_ratio"] * PROMPTER_SCROLL_SMOOTHNESS_SCALE))
        self.slider_focus_pos.valueChanged.connect(
            self.handle_focus_ratio_change
        )
        
        self.lbl_focus_percent = QLabel(
            f"Высота линии: {self.slider_focus_pos.value()}%"
        )
        self.lbl_focus_percent.setAlignment(Qt.AlignCenter)
        
        focus_layout.addWidget(self.lbl_focus_percent)
        focus_layout.addWidget(self.slider_focus_pos)
        focus_section.addLayout(focus_layout)
        layout.addWidget(focus_section)
    
    def _init_scroll_settings(self, layout) -> None:
        """Настройка прокрутки"""
        scroll_section = CollapsibleSection("Прокрутка")
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
        """Настройка отображения"""
        view_section = CollapsibleSection("Отображение")
        view_lay = QVBoxLayout()
        
        btn_colors = QPushButton("🎨 Настроить цвета телесуфлёра...")
        btn_colors.clicked.connect(self.open_color_settings_dialog)
        
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
        view_lay.addWidget(self.chk_show_header)
        view_lay.addWidget(self.chk_mirror)
        view_section.addLayout(view_lay)
        layout.addWidget(view_section)
    
    def _init_osc_settings(self, layout) -> None:
        """Настройка синхронизации Reaper"""
        osc_section = CollapsibleSection("Синхронизация Reaper (OSC)")
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
        self.btn_osc.clicked.connect(self.toggle_osc_connection_status)
        
        osc_layout.addWidget(self.chk_follow_reaper)
        osc_layout.addWidget(self.chk_reaper_follow)
        osc_layout.addWidget(self.btn_osc)
        
        # Отступ
        offset_layout = QHBoxLayout()
        self.chk_offset = QCheckBox(
            "Отступ -2 секунды",
            checked=self.cfg.get("reaper_offset_enabled", False)
        )
        self.spin_offset = QDoubleSpinBox()
        self.spin_offset.setRange(-10, 10)
        self.spin_offset.setSingleStep(0.5)
        self.spin_offset.setValue(self.cfg.get("reaper_offset_seconds", -2.0))
        self.spin_offset.setSuffix(" сек")
        
        self.chk_offset.toggled.connect(self.save_current_config_to_project)
        self.spin_offset.valueChanged.connect(self.save_current_config_to_project)
        
        offset_layout.addWidget(self.chk_offset)
        offset_layout.addWidget(self.spin_offset)
        offset_layout.addStretch()
        osc_layout.addLayout(offset_layout)
        
        osc_section.addLayout(osc_layout)
        layout.addWidget(osc_section)
    
    def compute_scroll_tau(self) -> float:
        """Вычисление временной константы прокрутки"""
        s = None
        if hasattr(self, 'slider_scroll_smoothness'):
            try:
                s = int(self.slider_scroll_smoothness.value())
            except RuntimeError:
                s = int(self.cfg.get('scroll_smoothness_slider', 18))
        else:
            s = int(self.cfg.get('scroll_smoothness_slider', 18))
        
        if s <= 0:
            return 0.0
        
        min_tau = 0.01
        max_tau = 2.0
        p = 1.15
        n = float(s) / 100.0
        tau = min_tau + (n ** p) * (max_tau - min_tau)
        return tau
    
    def update_big_timecode_font_size(self) -> None:
        """Динамический пересчет шрифта таймкода"""
        current_h = self.header_panel.height()
        if current_h > 10:
            font_size = int(current_h * 0.7)
            text_color = self.cfg['colors']['header_text']
            self.lbl_big_timecode.setStyleSheet(
                f"color: {text_color}; font-family: 'Courier New'; "
                f"font-weight: bold; font-size: {font_size}px;"
            )
    
    def adjust_prompter_view_scale(self) -> None:
        """Подстройка масштаба сцены"""
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
        """Скрытие/показ панели настроек"""
        visible = not is_hidden
        self.side_panel_widget.setVisible(visible)
        
        if is_hidden:
            self.btn_toggle_settings.setText("⚙ Показать настройки")
        else:
            self.btn_toggle_settings.setText("⚙ Скрыть настройки")
        
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
        """Показать/скрыть плавающее окно"""
        if show:
            self.show_float_window()
        else:
            self.hide_float_window()
    
    def show_float_window(self) -> None:
        """Показать плавающее окно"""
        if not hasattr(self, 'float_window') or self.float_window is None:
            self.float_window = TeleprompterFloatWindow(self)
        self.float_window.show()
        self.float_window.activateWindow()
        self.float_window.raise_()
        self.btn_float_window.setChecked(True)
    
    def hide_float_window(self) -> None:
        """Скрыть плавающее окно"""
        if hasattr(self, 'float_window') and self.float_window:
            self.float_window.hide()
        self.btn_float_window.setChecked(False)
    
    def handle_font_config_change(self) -> None:
        """Сохранение размеров шрифтов"""
        self.cfg["f_tc"] = self.spin_font_tc.value()
        self.cfg["f_char"] = self.spin_font_char.value()
        self.cfg["f_actor"] = self.spin_font_actor.value()
        self.cfg["f_text"] = self.spin_font_text.value()
        
        if not getattr(self, '_initializing', False):
            self.main_app.set_dirty(True)
        self.build_prompter_content()
    
    def handle_focus_ratio_change(self) -> None:
        """Изменение точки фокуса"""
        val = self.slider_focus_pos.value()
        self.cfg["focus_ratio"] = val / 100.0
        self.lbl_focus_percent.setText(f"Высота линии: {val}%")
        
        if not getattr(self, '_initializing', False):
            self.main_app.set_dirty(True)
        self.update_view_position_by_time(self.last_known_time)
    
    def handle_scroll_smoothness_change(self) -> None:
        """Сохранение параметра плавности"""
        sval = int(self.slider_scroll_smoothness.value())
        self.cfg["scroll_smoothness_slider"] = sval
        tau = self.compute_scroll_tau()
        
        if tau <= 0:
            self.lbl_scroll_value.setText("instant")
            self.lbl_scroll_descr.setText("Плавность прокрутки: мгновенно")
        else:
            self.lbl_scroll_value.setText(f"{tau:.2f}s")
            self.lbl_scroll_descr.setText(f"Плавность прокрутки: задержка ≈ {tau:.2f}s")
        
        if not getattr(self, '_initializing', False):
            self.main_app.set_dirty(True)
    
    def smooth_scroll_step(self) -> None:
        """Шаг интерполяции прокрутки"""
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
        """Открытие диалога цветов"""
        from .dialogs.colors import PrompterColorDialog
        
        dialog = PrompterColorDialog(self.cfg["colors"], self)
        if dialog.exec():
            self.cfg["colors"] = dialog.get_final_colors()
            self.main_app.set_dirty(True)
            self.build_prompter_content()
    
    def build_prompter_content(self) -> None:
        """Построение графической сцены"""
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
            return

        lines.sort(key=lambda x: x['s'])
        export_service = ExportService(self.main_app.data)
        processed = export_service.process_merge_logic(
            lines, self.main_app.data["export_config"]
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
            actor_id = self.main_app.data["global_map"].get(replica['char'])
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
            else:
                inactive_col = QColor(clrs["inactive_text"])
                char_col = text_col = tc_col = inactive_col
            
            row_y = y_cursor
            
            # Имя персонажа
            item_char = QGraphicsTextItem(replica['char'])
            item_char.setFont(f_char)
            item_char.setDefaultTextColor(char_col)
            item_char.setPos(0, row_y)
            self.prompter_scene.addItem(item_char)
            
            # Таймкод
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
            
            # Имя актёра
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
            
            # Текст реплики
            source_ids = replica.get('source_ids', [replica.get('id', i)])
            item_text = EditableTextItem(
                replica.get('text', ''), self, source_ids
            )
            item_text.setFont(f_text)
            item_text.setDefaultTextColor(text_col)
            item_text.setTextWidth(width)
            item_text.setPos(0, y_cursor)
            self.prompter_scene.addItem(item_text)
            
            # Маппинг для скролла
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
            self.float_window.sync_replica_list()
    
    def update_view_position_by_time(self, time_seconds: float) -> None:
        """Синхронизация позиции по времени"""
        self.last_known_time = time_seconds
        
        ms = int((time_seconds % 1) * 1000)
        self.lbl_big_timecode.setText(
            f"{format_seconds_to_tc(time_seconds)}.{ms:03d}"
        )
        
        if self.header_panel.isVisible():
            self.update_big_timecode_font_size()
        
        if not self.cfg["sync_in"] or not self.time_map:
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
        
        # Синхронизация списка
        if target_list_idx != -1:
            self.list_of_replicas.blockSignals(True)
            self.list_of_replicas.setCurrentRow(target_list_idx)
            self.list_of_replicas.scrollToItem(
                self.list_of_replicas.currentItem(),
                QAbstractItemView.PositionAtCenter
            )
            self.list_of_replicas.blockSignals(False)
        
        # Прокрутка сцены
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
        """Прыжок к таймкоду"""
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
        """Навигация по репликам"""
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
        """Клик по элементу списка"""
        self.jump_to_specific_time(item.data(Qt.UserRole))
    
    def save_current_config_to_project(self) -> None:
        """Сохранение конфигурации"""
        self.cfg["sync_in"] = self.chk_follow_reaper.isChecked()
        self.cfg["sync_out"] = self.chk_reaper_follow.isChecked()
        self.cfg["reaper_offset_enabled"] = self.chk_offset.isChecked()
        self.cfg["reaper_offset_seconds"] = self.spin_offset.value()
        self.main_app.set_dirty(True)
    
    def toggle_osc_connection_status(self, checked: bool) -> None:
        """Включение OSC"""
        if checked:
            self.osc_thread = OscWorker(self.cfg["port_in"])
            self.osc_thread.time_changed.connect(
                self.on_osc_time_packet_received
            )
            self.osc_thread.navigation_requested.connect(
                self.navigate_from_osc
            )
            self.osc_thread.start()
            
            try:
                from pythonosc.udp_client import SimpleUDPClient
                self.osc_client = SimpleUDPClient(
                    "127.0.0.1", self.cfg["port_out"]
                )
                self.btn_osc.setText("OSC Связь: Активна")
            except Exception as e:
                logger.error(f"OSC client error: {e}")
                self.btn_osc.setText("Ошибка OSC")
        else:
            if self.osc_thread:
                self.osc_thread.stop()
                self.osc_thread = None
            self.osc_client = None
            self.btn_osc.setText("Включить OSC связь")
            self.btn_osc.setStyleSheet("")
    
    @Slot(float)
    def on_osc_time_packet_received(self, time_val: float) -> None:
        """Получение времени из OSC"""
        self.update_view_position_by_time(time_val)
    
    @Slot(str)
    def navigate_from_osc(self, direction: str) -> None:
        """Навигация из OSC"""
        step = 1 if direction == "next" else -1
        self.navigate_to_replica_in_direction(step)
    
    def toggle_mirror_mode(self, checked: bool) -> None:
        """Зеркальный режим"""
        self.cfg["is_mirrored"] = checked
        self.prompter_view.resetTransform()
        if checked:
            self.prompter_view.scale(-1, 1)
        self.main_app.set_dirty(True)
    
    def toggle_header_visibility(self, checked: bool) -> None:
        """Видимость хедера"""
        self.cfg["show_header"] = checked
        self.header_panel.setVisible(checked)
        QTimer.singleShot(50, self.update_big_timecode_font_size)
        self.main_app.set_dirty(True)
    
    def open_actor_filter_dialog(self) -> None:
        """Диалог фильтра актёров"""
        from .dialogs.actor_filter import ActorFilterDialog
        
        all_ids = list(self.main_app.data["actors"].keys())
        dialog = ActorFilterDialog(
            self.main_app.data["actors"],
            self.highlight_ids or all_ids,
            self
        )
        if dialog.exec():
            sel = dialog.get_selected()
            self.highlight_ids = (
                None if len(sel) == len(all_ids) or len(sel) == 0 else sel
            )
            self.build_prompter_content()
    
    def setup_global_hotkeys(self) -> None:
        """Настройка горячих клавиш"""
        if not PYNPUT_AVAILABLE:
            logger.info("pynput недоступен, только локальные хоткеи")
            return
        
        try:
            if self.main_app.global_hotkey_manager is None:
                self.main_app.global_hotkey_manager = GlobalHotkeyManager(
                    self.main_app
                )
            
            self.main_app.global_hotkey_manager.clear_hotkeys()
            
            key_prev = self.cfg.get("key_prev", "Left")
            key_next = self.cfg.get("key_next", "Right")
            
            prev_key_str = f"ctrl+{key_prev}"
            next_key_str = f"ctrl+{key_next}"
            
            self.main_app.global_hotkey_manager.register_hotkey(
                "prev", prev_key_str, self.go_prev_hotkey
            )
            self.main_app.global_hotkey_manager.register_hotkey(
                "next", next_key_str, self.go_next_hotkey
            )
            
            if not self.main_app.global_hotkey_manager._running:
                QTimer.singleShot(
                    100, self.main_app.global_hotkey_manager.start
                )
        except Exception as e:
            log_exception(logger, "Error setting up hotkeys", e)
    
    def go_prev_hotkey(self) -> None:
        """Хоткей назад"""
        QTimer.singleShot(
            0, lambda: self.navigate_to_replica_in_direction(-1)
        )
    
    def go_next_hotkey(self) -> None:
        """Хоткей вперёд"""
        QTimer.singleShot(
            0, lambda: self.navigate_to_replica_in_direction(1)
        )
    
    def keyPressEvent(self, event) -> None:
        """Обработка клавиш"""
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
        """Разделение объединённого текста"""
        if not text or len(ids) < 2:
            return []
        
        parts = []
        
        if ' // ' in text:
            parts = [p.strip() for p in text.split(' // ') if p.strip()]
        elif ' / ' in text:
            parts = [p.strip() for p in text.split(' / ') if p.strip()]
        
        if len(parts) == len(ids):
            return parts
        
        return []
    
    def handle_text_edited(self, line_id: Any, new_text: str) -> None:
        """Обработка редактирования текста"""
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

    def refresh_episode_data(self) -> None:
        """Обновление данных эпизода (после переименования персонажа)"""
        # Инвалидируем кэш
        self.main_app.episode_service.invalidate_episode(self.ep_num)
        
        # Перезагружаем данные и перестраиваем контент
        try:
            self.build_prompter_content()
        except Exception as e:
            log_exception(logger, "Error refreshing episode data", e)

    def closeEvent(self, event) -> None:
        """Закрытие окна"""
        if self.osc_thread:
            self.osc_thread.stop()
        
        if hasattr(self, 'float_window') and self.float_window:
            self.float_window.close()
            self.float_window = None

        if self._has_text_changes:
            reply = QMessageBox.question(
                self,
                "Несохраненные изменения",
                "У вас есть несохраненные изменения в тексте.\n"
                "Хотите сохранить их в .ASS перед выходом?",
                QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel
            )
            if reply == QMessageBox.Yes:
                if self.main_app.save_episode_to_ass(self.ep_num):
                    self._has_text_changes = False
                    event.accept()
                else:
                    event.ignore()
            elif reply == QMessageBox.No:
                # Пользователь отказался от сохранения — сбрасываем флаги
                self._has_text_changes = False
                # Сбрасываем dirty флаг главного окна, т.к. изменения не были сохранены
                self.main_app.set_dirty(False)
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()