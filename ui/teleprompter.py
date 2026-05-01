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
    QGraphicsScene, QGraphicsTextItem, QApplication, QComboBox
)
from PySide6.QtGui import (
    QColor, QFont, QPainter, QPen, QBrush, QCursor
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
    # Internal implementation detail
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
from utils.helpers import ass_time_to_seconds, format_seconds_to_tc, log_exception

logger = logging.getLogger(__name__)


class SettingsSection(QFrame):
    """Settings Section class."""

    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.StyledPanel)
        self.setAutoFillBackground(True)
        self.setStyleSheet(
            "SettingsSection { border-radius: 4px; }"
        )

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(8, 6, 8, 8)
        self.main_layout.setSpacing(4)

        # Internal implementation detail
        title_label = QLabel(title)
        title_label.setStyleSheet(
            "font-weight: bold; font-size: 13px;"
        )
        self.main_layout.addWidget(title_label)

    def addWidget(self, widget) -> None:
        self.main_layout.addWidget(widget)

    def addLayout(self, layout) -> None:
        self.main_layout.addLayout(layout)


class EditTextDialog(QDialog):
    """Edit Text Dialog dialog."""
    
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
    """Editable Text Item class."""
    
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
        # Internal implementation detail


class TeleprompterFloatWindow(QDialog):
    """Teleprompter Float Window class."""

    def __init__(self, teleprompter: 'TeleprompterWindow') -> None:
        super().__init__(None)
        self.teleprompter: 'TeleprompterWindow' = teleprompter
        self._drag_pos = None  # Internal implementation detail
        self._cocoa_window = None  # macOS-specific handling

        # macOS-specific handling
        if platform.system() == "Darwin":
            self._init_cocoa_window()
        else:
            # Qt-specific handling
            flags = (
                Qt.Tool |
                Qt.WindowStaysOnTopHint |
                Qt.CustomizeWindowHint |
                Qt.WindowDoesNotAcceptFocus |
                Qt.FramelessWindowHint
            )
            self.setWindowFlags(flags)
            self.setAttribute(Qt.WA_ShowWithoutActivating)
            self.resize(PROMPTER_FLOAT_WINDOW_WIDTH, PROMPTER_FLOAT_WINDOW_HEIGHT)
            self._init_qt_ui()

    def _init_cocoa_window(self) -> None:
        """Init cocoa window."""
        try:
            from AppKit import (
                NSPanel, NSNonactivatingPanelMask, NSUtilityWindowMask,
                NSFloatingWindowLevel, NSMakeRect, NSButton, NSSmallSquareBezelStyle,
                NSFont, NSScrollView, NSTextView, NSNoBorder, NSView,
                NSBezelBorder
            )
            import objc
            
            # Internal implementation detail
            self._cocoa_window = NSPanel.alloc().initWithContentRect_styleMask_backing_defer_(
                NSMakeRect(100, 100, PROMPTER_FLOAT_WINDOW_WIDTH, PROMPTER_FLOAT_WINDOW_HEIGHT),
                NSUtilityWindowMask | NSNonactivatingPanelMask,
                2,  # NSBackingStoreBuffered
                False
            )
            self._cocoa_window.setLevel_(NSFloatingWindowLevel)
            self._cocoa_window.setCollectionBehavior_(2)
            self._cocoa_window.setWorksWhenModal_(True)
            self._cocoa_window.setTitle_("Управление")
            self._cocoa_window.setMovableByWindowBackground_(True)
            
            # Internal implementation detail
            content_view = NSView.alloc().initWithFrame_(
                NSMakeRect(0, 0, PROMPTER_FLOAT_WINDOW_WIDTH, PROMPTER_FLOAT_WINDOW_HEIGHT)
            )
            
            # Internal implementation detail
            # Internal implementation detail
            btn_next = NSButton.alloc().initWithFrame_(
                NSMakeRect(FLOAT_MARGIN_X, FLOAT_BTN_Y_PREV, FLOAT_BTN_WIDTH, FLOAT_BTN_HEIGHT)
            )
            btn_next.setTitle_("Вперёд ⏭")
            btn_next.setBezelStyle_(NSSmallSquareBezelStyle)
            btn_next.setTarget_(self)
            btn_next.setAction_(objc.selector(self.onNextClicked_, signature=b'v@:@'))
            content_view.addSubview_(btn_next)
            
            # Internal implementation detail
            btn_prev = NSButton.alloc().initWithFrame_(
                NSMakeRect(FLOAT_MARGIN_X, FLOAT_BTN_Y_NEXT, FLOAT_BTN_WIDTH, FLOAT_BTN_HEIGHT)
            )
            btn_prev.setTitle_("⏮ Назад")
            btn_prev.setBezelStyle_(NSSmallSquareBezelStyle)
            btn_prev.setTarget_(self)
            btn_prev.setAction_(objc.selector(self.onPrevClicked_, signature=b'v@:@'))
            content_view.addSubview_(btn_prev)
            
            # Internal implementation detail
            from AppKit import NSTextField, NSCenterTextAlignment
            label = NSTextField.alloc().initWithFrame_(
                NSMakeRect(FLOAT_MARGIN_X, FLOAT_LABEL_Y, FLOAT_BTN_WIDTH, FLOAT_LABEL_HEIGHT)
            )
            label.setStringValue_("Список реплик:")
            label.setEditable_(False)
            label.setSelectable_(False)
            label.setBezeled_(False)
            label.setDrawsBackground_(False)
            label.setFont_(NSFont.boldSystemFontOfSize_(12))
            label.setAlignment_(NSCenterTextAlignment)
            content_view.addSubview_(label)
            
            # Internal implementation detail
            from AppKit import NSTextView, NSScrollView, NSBezelBorder, NSTextViewDidChangeSelectionNotification
            from Foundation import NSNotificationCenter
            
            scroll_view = NSScrollView.alloc().initWithFrame_(
                NSMakeRect(FLOAT_MARGIN_X, FLOAT_SCROLL_Y, FLOAT_SCROLL_WIDTH, FLOAT_SCROLL_HEIGHT)
            )
            scroll_view.setHasVerticalScroller_(True)
            scroll_view.setBorderType_(NSBezelBorder)
            scroll_view.setDrawsBackground_(True)
            
            text_view = NSTextView.alloc().initWithFrame_(
                NSMakeRect(0, 0, FLOAT_TEXT_VIEW_WIDTH, FLOAT_SCROLL_HEIGHT)
            )
            text_view.setEditable_(False)
            text_view.setSelectable_(True)
            text_view.setRichText_(False)
            text_view.setFont_(NSFont.systemFontOfSize_(11))
            text_view.setString_("")
            text_view.setAllowsUndo_(False)
            scroll_view.setDocumentView_(text_view)
            content_view.addSubview_(scroll_view)
            
            # Internal implementation detail
            NSNotificationCenter.defaultCenter().addObserver_selector_name_object_(
                self,
                'onReplicaSelected:',
                NSTextViewDidChangeSelectionNotification,
                text_view
            )
            
            # Initialize list
            self._replica_text_view = text_view
            self._replica_scroll_view = scroll_view
            self._replica_items = []

            # Internal implementation detail
            btn_hide = NSButton.alloc().initWithFrame_(
                NSMakeRect(FLOAT_BTN_HIDE_X, FLOAT_BTN_HIDE_Y, FLOAT_BTN_HIDE_WIDTH, FLOAT_BTN_HIDE_HEIGHT)
            )
            btn_hide.setTitle_("Скрыть")
            btn_hide.setBezelStyle_(NSSmallSquareBezelStyle)
            btn_hide.setTarget_(self)
            btn_hide.setAction_(objc.selector(self.onHideClicked_, signature=b'v@:@'))
            content_view.addSubview_(btn_hide)

            self._cocoa_window.setContentView_(content_view)
            self._content_view = content_view

            # Internal implementation detail
            self._btn_prev = btn_prev
            self._btn_next = btn_next
            
        except Exception as e:
            logger.debug(f"macOS Cocoa window init error: {e}")
            # Qt-specific handling
            flags = (
                Qt.Tool |
                Qt.WindowStaysOnTopHint |
                Qt.CustomizeWindowHint |
                Qt.WindowDoesNotAcceptFocus |
                Qt.FramelessWindowHint
            )
            self.setWindowFlags(flags)
            self.setAttribute(Qt.WA_ShowWithoutActivating)
            self.resize(PROMPTER_FLOAT_WINDOW_WIDTH, PROMPTER_FLOAT_WINDOW_HEIGHT)
            self._init_qt_ui()

    # macOS-specific handling

    def _init_qt_ui(self) -> None:
        """Init qt ui."""
        layout: QVBoxLayout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(4)

        # Internal implementation detail
        self.drag_label = QLabel("☰ Управление")
        self.drag_label.setStyleSheet("""
            QLabel {
                background: #444;
                color: white;
                padding: 4px;
                border-radius: 4px;
                font-weight: bold;
                font-size: 11px;
            }
        """)
        self.drag_label.setAlignment(Qt.AlignCenter)
        self.drag_label.setCursor(Qt.OpenHandCursor)
        layout.addWidget(self.drag_label)

        # Internal implementation detail
        btn_layout: QHBoxLayout = QHBoxLayout()

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

        # Internal implementation detail
        layout.addWidget(QLabel("<b>Список реплик:</b>"))
        self.replica_list = QListWidget()
        self.replica_list.itemClicked.connect(
            lambda item: self.teleprompter.jump_to_specific_time(item.data(Qt.UserRole))
        )
        layout.addWidget(self.replica_list)

        # Internal implementation detail
        btn_close = QPushButton("Скрыть")
        btn_close.clicked.connect(self.hide_window)
        layout.addWidget(btn_close)

        self.sync_replica_list()

    def onPrevClicked_(self, sender) -> None:
        """Onprevclicked."""
        if self.teleprompter:
            self.teleprompter.navigate_to_replica_in_direction(-1)

    def onNextClicked_(self, sender) -> None:
        """Onnextclicked."""
        if self.teleprompter:
            self.teleprompter.navigate_to_replica_in_direction(1)

    def onHideClicked_(self, sender) -> None:
        """Onhideclicked."""
        if self._cocoa_window:
            self._cocoa_window.orderOut_(None)
        if hasattr(self, 'teleprompter') and self.teleprompter:
            self.teleprompter.hide_float_window()

    def show_cocoa_window(self) -> None:
        """Show cocoa window."""
        if self._cocoa_window:
            # Internal implementation detail
            self.update_cocoa_replica_list()
            
            # Internal implementation detail
            if hasattr(self, 'teleprompter') and self.teleprompter:
                current_time = self.teleprompter.last_known_time
                for i, item in enumerate(self._replica_items):
                    if abs(item['time'] - current_time) < 0.01:
                        self.update_cocoa_selection(i)
                        break
            
            # Internal implementation detail
            self._cocoa_window.orderFrontRegardless()
            self._cocoa_window.makeKeyAndOrderFront_(None)

    def hide_cocoa_window(self) -> None:
        """Hide cocoa window."""
        if self._cocoa_window:
            self._cocoa_window.orderOut_(None)

    def update_cocoa_replica_list(self) -> None:
        """Update cocoa replica list."""
        if not self._cocoa_window or not hasattr(self, '_replica_text_view'):
            logger.debug("Cocoa: окно или текст-вью не найдены")
            return
        
        # Qt-specific handling
        self._replica_items = []
        replicas = []
        
        for i in range(self.teleprompter.list_of_replicas.count()):
            item = self.teleprompter.list_of_replicas.item(i)
            if item:
                replicas.append(item.text())
                self._replica_items.append({
                    'text': item.text(),
                    'time': item.data(Qt.UserRole)
                })
        
        logger.debug(f"Cocoa: найдено {len(self._replica_items)} реплик")
        
        # Internal implementation detail
        text = '\n'.join(replicas) if replicas else "Нет реплик"
        self._replica_text_view.setString_(text)
        
        # Internal implementation detail
        from Foundation import NSMakeRange
        self._replica_text_view.scrollRangeToVisible_(NSMakeRange(0, 0))
        logger.debug("Cocoa: текст обновлён")

    def onReplicaSelected_(self, notification) -> None:
        """Onreplicaselected."""
        text_view = notification.object()
        selected_range = text_view.selectedRange()
        selected_location = selected_range.location
        
        if selected_location >= 0 and hasattr(self, '_replica_items'):
            # Internal implementation detail
            text = text_view.string()
            if text:
                lines = text.split('\n')
                current_pos = 0
                
                for i, line in enumerate(lines):
                    line_start = current_pos
                    line_end = current_pos + len(line)
                    
                    if line_start <= selected_location <= line_end:
                        # Internal implementation detail
                        if i < len(self._replica_items):
                            time_code = self._replica_items[i].get('time')
                            if time_code:
                                self.on_replica_clicked(time_code)
                        break
                    
                    current_pos = line_end + 1  # Internal implementation detail

    def update_cocoa_selection(self, index: int) -> None:
        """Update cocoa selection."""
        if not hasattr(self, '_replica_text_view') or not self._replica_items:
            return
        
        # Internal implementation detail
        if 0 <= index < len(self._replica_items):
            # Internal implementation detail
            text = self._replica_text_view.string()
            if text:
                lines = text.split('\n')
                pos = 0
                for i in range(index):
                    pos += len(lines[i]) + 1  # Internal implementation detail
                
                # Internal implementation detail
                from Foundation import NSMakeRange
                line_length = len(lines[index]) if index < len(lines) else 0
                self._replica_text_view.setSelectedRange_(NSMakeRange(pos, line_length))
                
                # Internal implementation detail
                self._replica_text_view.scrollRangeToVisible_(NSMakeRange(pos, line_length))

    def on_replica_clicked(self, time_code: float) -> None:
        """Handle replica click."""
        if self.teleprompter and time_code is not None:
            self.teleprompter.jump_to_specific_time(time_code)

    # Qt-specific handling

    def showEvent(self, event) -> None:
        """Showevent."""
        super().showEvent(event)

    def closeEvent(self, event) -> None:
        """Closeevent."""
        self.hide_window()
        event.ignore()

    def hide_window(self) -> None:
        """Hide window."""
        if platform.system() == "Darwin":
            self.hide_cocoa_window()
        else:
            self.hide()
        if hasattr(self, 'teleprompter') and self.teleprompter:
            self.teleprompter.hide_float_window()

    def sync_replica_list(self) -> None:
        """Synchronize replica list."""
        if platform.system() == "Darwin":
            self.update_cocoa_replica_list()
        else:
            # Qt-specific handling
            if not self.teleprompter:
                return

            current_row: int = self.replica_list.currentRow()
            self.replica_list.blockSignals(True)
            self.replica_list.clear()

            i: int
            for i in range(self.teleprompter.list_of_replicas.count()):
                item: QListWidgetItem = self.teleprompter.list_of_replicas.item(i)
                new_item: QListWidgetItem = QListWidgetItem(item.text())
                new_item.setData(Qt.UserRole, item.data(Qt.UserRole))
                self.replica_list.addItem(new_item)

            if 0 <= current_row < self.replica_list.count():
                self.replica_list.setCurrentRow(current_row)
            self.replica_list.blockSignals(False)

    def update_selection(self, index: int) -> None:
        """Update selection."""
        if platform.system() == "Darwin":
            self.update_cocoa_selection(index)
        else:
            if 0 <= index < self.replica_list.count():
                self.replica_list.blockSignals(True)
                self.replica_list.setCurrentRow(index)
                self.replica_list.blockSignals(False)

    # Qt-specific handling

    def mousePressEvent(self, event) -> None:
        """Mousepressevent."""
        if event.button() == Qt.LeftButton:
            # Internal implementation detail
            if event.pos().y() < 30:  # Internal implementation detail
                self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
                self.drag_label.setCursor(Qt.ClosedHandCursor)
                event.accept()
                return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        """Mousemoveevent."""
        if self._drag_pos is not None:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        """Mousereleaseevent."""
        if event.button() == Qt.LeftButton:
            self._drag_pos = None
            self.drag_label.setCursor(Qt.OpenHandCursor)
            event.accept()
            return
        super().mouseReleaseEvent(event)


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
        self.setWindowTitle(f"Телесуфлёр - Серия {ep_num}")
        self.resize(PROMPTER_WINDOW_WIDTH, PROMPTER_WINDOW_HEIGHT)

        # Internal implementation detail
        self._init_config()

        # Internal implementation detail
        self.time_map = []
        self.osc_thread: Optional[OscWorker] = None
        self.osc_client = None
        self.last_known_time: float = 0.0
        self.highlight_ids = None
        self._has_text_changes: bool = False
        self._initializing: bool = True
        self._manual_scroll_override: bool = False

        # UI
        self._init_ui()
        self.build_prompter_content()

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

        # Internal implementation detail
        if "colors" not in self.cfg or not isinstance(self.cfg["colors"], dict):
            self.cfg["colors"] = DEFAULT_PROMPTER_CONFIG["colors"].copy()
        else:
            color_key: str
            color_value: str
            for color_key, color_value in DEFAULT_PROMPTER_CONFIG["colors"].items():
                if color_key not in self.cfg["colors"]:
                    self.cfg["colors"][color_key] = color_value

    def _init_ui(self) -> None:
        """Init ui."""
        self.root_layout: QVBoxLayout = QVBoxLayout(self)
        self.root_layout.setContentsMargins(0, 0, 0, 0)
        self.root_layout.setSpacing(0)

        # Internal implementation detail
        self._init_toolbar()

        # Internal implementation detail
        self._init_splitters()

        # Internal implementation detail
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

    def _episode_sort_key(self, ep_num: str) -> Tuple[int, str]:
        """Return a natural sort key for episode identifiers."""
        return (int(ep_num), ep_num) if str(ep_num).isdigit() else (0, str(ep_num))

    def _populate_episode_combo(self) -> None:
        """Populate episode combo."""
        self.combo_episode.blockSignals(True)
        self.combo_episode.clear()

        episode_nums = sorted(
            self.main_app.data.get("episodes", {}).keys(),
            key=self._episode_sort_key
        )
        for ep_num in episode_nums:
            self.combo_episode.addItem(f"Серия {ep_num}", str(ep_num))

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
                "Ошибка",
                f"Серия {ep_num} не найдена в проекте."
            )
            self._populate_episode_combo()
            return

        if self.smooth_scroll_timer.isActive():
            self.smooth_scroll_timer.stop()
        self._scroll_target_y = None
        self.last_known_time = 0.0
        self.ep_num = str(ep_num)
        self.setWindowTitle(f"Телесуфлёр - Серия {self.ep_num}")

        self._sync_main_episode_selection()
        self.build_prompter_content()

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
        
        # Internal implementation detail
        self.header_panel = QFrame()
        self.header_panel.setObjectName("HeaderPanel")
        self.header_panel.setMinimumHeight(0)
        header_layout = QVBoxLayout(self.header_panel)
        header_layout.setContentsMargins(0, 0, 0, 0)
        
        self.lbl_big_timecode = QLabel("0:00:00.000")
        self.lbl_big_timecode.setAlignment(Qt.AlignCenter)
        header_layout.addWidget(self.lbl_big_timecode)
        self.v_splitter.addWidget(self.header_panel)
        
        # Internal implementation detail
        self.h_splitter = QSplitter(Qt.Horizontal)
        self.h_splitter.setHandleWidth(8)
        
        # Internal implementation detail
        self._init_side_panel()
        self.h_splitter.addWidget(self.side_panel_widget)
        
        # Internal implementation detail
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

        # Internal implementation detail
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
        
        # Internal implementation detail
        self.settings_scroll_area = QScrollArea()
        self.settings_scroll_area.setWidgetResizable(True)
        self.settings_scroll_area.setFrameShape(QFrame.NoFrame)
        
        settings_container = QWidget()
        settings_v_layout = QVBoxLayout(settings_container)
        settings_v_layout.setSpacing(4)
        
        # Internal implementation detail
        self._init_font_settings(settings_v_layout)
        self._init_focus_settings(settings_v_layout)
        self._init_scroll_settings(settings_v_layout)
        self._init_view_settings(settings_v_layout)
        self._init_osc_settings(settings_v_layout)
        
        self.settings_scroll_area.setWidget(settings_container)
        self.side_layout.addWidget(self.settings_scroll_area)
        
        # Internal implementation detail
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
            f"Высота линии: {self.slider_focus_pos.value()}%"
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
        self.btn_osc.clicked.connect(self.toggle_osc_connection_status)
        
        osc_layout.addWidget(self.chk_follow_reaper)
        osc_layout.addWidget(self.chk_reaper_follow)
        osc_layout.addWidget(self.btn_osc)
        
        # Internal implementation detail
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
        """Compute scroll tau."""
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
        """Toggle float window."""
        if show:
            self.show_float_window()
        else:
            self.hide_float_window()

    def show_float_window(self) -> None:
        """Show float window."""
        if not hasattr(self, 'float_window') or self.float_window is None:
            self.float_window = TeleprompterFloatWindow(self)
        
        if platform.system() == "Darwin":
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
            if platform.system() == "Darwin":
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

        # Internal implementation detail
        self.main_app.save_global_prompter_settings(self.cfg)

        if not getattr(self, '_initializing', False):
            self.main_app.set_dirty(True)
        self.build_prompter_content()
    
    def handle_focus_ratio_change(self) -> None:
        """Handle focus ratio change."""
        val = self.slider_focus_pos.value()
        self.cfg["focus_ratio"] = val / 100.0
        self.lbl_focus_percent.setText(f"Высота линии: {val}%")
        
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
            self.lbl_scroll_descr.setText("Плавность прокрутки: мгновенно")
        else:
            self.lbl_scroll_value.setText(f"{tau:.2f}s")
            self.lbl_scroll_descr.setText(f"Плавность прокрутки: задержка ≈ {tau:.2f}s")
        
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
        if dialog.exec():
            self.cfg["colors"] = dialog.get_final_colors()
            
            # Internal implementation detail
            self.main_app.save_global_prompter_settings(self.cfg)
            
            self.main_app.set_dirty(True)
            self.build_prompter_content()
    
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
        
        # Internal implementation detail
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
                
                # Internal implementation detail
                if self.last_known_time == 0.0:
                    self.last_known_time = replica['s']
            else:
                inactive_col = QColor(clrs["inactive_text"])
                char_col = text_col = tc_col = inactive_col
            
            row_y = y_cursor
            
            # Internal implementation detail
            item_char = QGraphicsTextItem(replica['char'])
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
            
            # Internal implementation detail
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
            
            # Internal implementation detail
            if replica.get('_working_text'):
                editable_ids = [replica.get('id', i)]
            else:
                editable_ids = replica.get('source_ids', [replica.get('id', i)])
            item_text = EditableTextItem(
                replica.get('text', ''), self, editable_ids
            )
            item_text.setFont(f_text)
            item_text.setDefaultTextColor(text_col)
            item_text.setTextWidth(width)
            item_text.setPos(0, y_cursor)
            self.prompter_scene.addItem(item_text)
            
            # Internal implementation detail
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

        # Internal implementation detail
        if target_list_idx != -1:
            self.list_of_replicas.blockSignals(True)
            self.list_of_replicas.setCurrentRow(target_list_idx)
            self.list_of_replicas.scrollToItem(
                self.list_of_replicas.currentItem(),
                QAbstractItemView.PositionAtCenter
            )
            self.list_of_replicas.blockSignals(False)

        # Internal implementation detail
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
        self.cfg["reaper_offset_enabled"] = self.chk_offset.isChecked()
        self.cfg["reaper_offset_seconds"] = self.spin_offset.value()
        if self.cfg["sync_in"]:
            self.exit_manual_scroll_override()
        
        # Internal implementation detail
        self.main_app.save_global_prompter_settings(self.cfg)
        
        self.main_app.set_dirty(True)
    
    def toggle_osc_connection_status(self, checked: bool) -> None:
        """Toggle osc connection status."""
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
            self.btn_osc.setText("Включи��ь OSC связь")
            self.btn_osc.setStyleSheet("")
    
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
            self.highlight_ids or all_ids,
            self
        )
        if dialog.exec():
            sel = dialog.get_selected()
            self.highlight_ids = (
                None if len(sel) == len(all_ids) or len(sel) == 0 else sel
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
        """Handle text edited."""
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

    def refresh_episode_data(self) -> None:
        """Refresh episode data."""
        # Internal implementation detail
        self.main_app.episode_service.invalidate_episode(self.ep_num)
        
        # Internal implementation detail
        try:
            self.build_prompter_content()
        except Exception as e:
            log_exception(logger, "Error refreshing episode data", e)

    def closeEvent(self, event) -> None:
        """Closeevent."""
        if self.osc_thread:
            self.osc_thread.stop()

        if hasattr(self, 'float_window') and self.float_window:
            self.float_window.close()
            self.float_window = None

        event.accept()
