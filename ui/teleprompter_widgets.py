"""Reusable teleprompter widgets and floating controls."""

import logging
import platform
from typing import List, Optional, Union

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QCompleter,
    QDialog,
    QDialogButtonBox,
    QFrame,
    QGraphicsTextItem,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)

from config.constants import (
    EDIT_TEXT_DIALOG_HEIGHT,
    EDIT_TEXT_DIALOG_WIDTH,
    FLOAT_BTN_HEIGHT,
    FLOAT_BTN_HIDE_HEIGHT,
    FLOAT_BTN_HIDE_WIDTH,
    FLOAT_BTN_HIDE_X,
    FLOAT_BTN_HIDE_Y,
    FLOAT_BTN_WIDTH,
    FLOAT_BTN_Y_NEXT,
    FLOAT_BTN_Y_PREV,
    FLOAT_EPISODE_COMBO_HEIGHT,
    FLOAT_EPISODE_COMBO_Y,
    FLOAT_EPISODE_LABEL_Y,
    FLOAT_LABEL_HEIGHT,
    FLOAT_LABEL_Y,
    FLOAT_MARGIN_X,
    FLOAT_SCROLL_HEIGHT,
    FLOAT_SCROLL_WIDTH,
    FLOAT_SCROLL_Y,
    FLOAT_TEXT_VIEW_WIDTH,
    PROMPTER_FLOAT_WINDOW_HEIGHT,
    PROMPTER_FLOAT_WINDOW_WIDTH,
)
from utils.helpers import log_exception
from utils.i18n import translate_source

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
    
    def __init__(
        self,
        parent=None,
        initial_text: str = "",
        can_split_character: bool = True
    ):
        super().__init__(parent)
        self.setWindowTitle("Редактирование реплики")
        self.resize(EDIT_TEXT_DIALOG_WIDTH, EDIT_TEXT_DIALOG_HEIGHT)
        self.split_character: Optional[str] = None
        self.split_text: str = ""
        self.remaining_text: str = ""
        
        layout = QVBoxLayout(self)
        self.text_edit = QTextEdit()
        self.text_edit.setPlainText(initial_text)
        layout.addWidget(self.text_edit)

        self.btn_split_character = QPushButton(
            "Перенести в другого персонажа"
        )
        self.btn_split_character.setEnabled(can_split_character)
        self.btn_split_character.clicked.connect(self.split_selection_to_character)
        layout.addWidget(self.btn_split_character)
        
        btn_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)

    def split_selection_to_character(self) -> None:
        """Move selected text into a new character replica."""
        cursor = self.text_edit.textCursor()
        selected_text = cursor.selectedText().replace("\u2029", "\n").strip()
        if not selected_text:
            return

        character_names = []
        if hasattr(self.parent(), "get_project_character_names"):
            character_names = self.parent().get_project_character_names()

        dialog = EditCharacterDialog(
            self,
            "",
            character_names
        )
        if dialog.exec() != QDialog.Accepted:
            return

        character = dialog.selected_character()
        if not character:
            return

        cursor.removeSelectedText()
        self.split_character = character
        self.split_text = selected_text
        self.remaining_text = self.text_edit.toPlainText()
        self.accept()


class EditCharacterDialog(QDialog):
    """Dialog for changing one teleprompter replica character."""

    def __init__(
        self,
        parent=None,
        initial_name: str = "",
        character_names: Optional[List[str]] = None
    ):
        super().__init__(parent)
        self.setWindowTitle("Изменение персонажа")
        self.resize(360, 110)

        layout = QVBoxLayout(self)
        self.character_combo = QComboBox()
        self.character_combo.setEditable(True)
        self.character_combo.setInsertPolicy(QComboBox.NoInsert)
        self.character_combo.addItems(character_names or [])
        self.character_combo.setCurrentText(initial_name)

        completer = QCompleter(character_names or [], self)
        completer.setCaseSensitivity(Qt.CaseInsensitive)
        completer.setFilterMode(Qt.MatchContains)
        self.character_combo.setCompleter(completer)
        layout.addWidget(self.character_combo)

        btn_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)

    def selected_character(self) -> str:
        """Return selected character name."""
        return self.character_combo.currentText().strip()


class EditableCharacterItem(QGraphicsTextItem):
    """Graphics item that edits a replica character on double click."""

    def __init__(
        self,
        text: str,
        window: 'TeleprompterWindow',
        line_id: Optional[Union[int, List[int]]] = None
    ):
        super().__init__(text)
        self.window = window
        self.line_id = line_id
        self.setCursor(Qt.PointingHandCursor)

    def mouseDoubleClickEvent(self, event) -> None:
        try:
            initial = self.toPlainText()
            dialog = EditCharacterDialog(
                self.window,
                initial,
                self.window.get_project_character_names()
            )
            if dialog.exec() == QDialog.Accepted:
                new_name = dialog.selected_character()
                if new_name and new_name != initial:
                    self.window.handle_character_edited(
                        self.line_id,
                        new_name
                    )
        except Exception as e:
            log_exception(logger, "Error editing character", e)


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
            can_split_character = not isinstance(
                self.line_id, (list, tuple)
            ) or len(self.line_id) == 1
            dialog = EditTextDialog(
                self.window,
                initial,
                can_split_character=can_split_character
            )
            if dialog.exec() == QDialog.Accepted:
                if dialog.split_character:
                    try:
                        self.window.handle_text_split_to_character(
                            self.line_id,
                            dialog.remaining_text,
                            dialog.split_text,
                            dialog.split_character
                        )
                    except Exception as e:
                        log_exception(logger, "Error splitting text", e)
                    return

                new_text = dialog.text_edit.toPlainText()
                if new_text != initial:
                    try:
                        self.window.handle_text_edited(self.line_id, new_text)
                    except Exception as e:
                        log_exception(logger, "Error editing text", e)
        except Exception as e:
            log_exception(logger, "Error in mouseDoubleClickEvent", e)


class TeleprompterFloatWindow(QDialog):
    """Teleprompter Float Window class."""

    def __init__(self, teleprompter: 'TeleprompterWindow') -> None:
        super().__init__(None)
        self.teleprompter: 'TeleprompterWindow' = teleprompter
        self._drag_pos = None
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
                NSBezelBorder, NSPopUpButton
            )
            import objc
            
            self._cocoa_window = NSPanel.alloc().initWithContentRect_styleMask_backing_defer_(
                NSMakeRect(100, 100, PROMPTER_FLOAT_WINDOW_WIDTH, PROMPTER_FLOAT_WINDOW_HEIGHT),
                NSUtilityWindowMask | NSNonactivatingPanelMask,
                2,  # NSBackingStoreBuffered
                False
            )
            self._cocoa_window.setLevel_(NSFloatingWindowLevel)
            self._cocoa_window.setCollectionBehavior_(2)
            self._cocoa_window.setWorksWhenModal_(True)
            self._cocoa_window.setTitle_(translate_source("Управление"))
            self._cocoa_window.setMovableByWindowBackground_(True)
            
            content_view = NSView.alloc().initWithFrame_(
                NSMakeRect(0, 0, PROMPTER_FLOAT_WINDOW_WIDTH, PROMPTER_FLOAT_WINDOW_HEIGHT)
            )
            
            btn_next = NSButton.alloc().initWithFrame_(
                NSMakeRect(FLOAT_MARGIN_X, FLOAT_BTN_Y_PREV, FLOAT_BTN_WIDTH, FLOAT_BTN_HEIGHT)
            )
            btn_next.setTitle_(translate_source("Вперёд ⏭"))
            btn_next.setBezelStyle_(NSSmallSquareBezelStyle)
            btn_next.setTarget_(self)
            btn_next.setAction_(objc.selector(self.onNextClicked_, signature=b'v@:@'))
            content_view.addSubview_(btn_next)
            
            btn_prev = NSButton.alloc().initWithFrame_(
                NSMakeRect(FLOAT_MARGIN_X, FLOAT_BTN_Y_NEXT, FLOAT_BTN_WIDTH, FLOAT_BTN_HEIGHT)
            )
            btn_prev.setTitle_(translate_source("⏮ Назад"))
            btn_prev.setBezelStyle_(NSSmallSquareBezelStyle)
            btn_prev.setTarget_(self)
            btn_prev.setAction_(objc.selector(self.onPrevClicked_, signature=b'v@:@'))
            content_view.addSubview_(btn_prev)

            from AppKit import NSTextField, NSCenterTextAlignment
            episode_label = NSTextField.alloc().initWithFrame_(
                NSMakeRect(
                    FLOAT_MARGIN_X,
                    FLOAT_EPISODE_LABEL_Y,
                    FLOAT_BTN_WIDTH,
                    FLOAT_LABEL_HEIGHT
                )
            )
            episode_label.setStringValue_(translate_source("Серия:"))
            episode_label.setEditable_(False)
            episode_label.setSelectable_(False)
            episode_label.setBezeled_(False)
            episode_label.setDrawsBackground_(False)
            episode_label.setFont_(NSFont.boldSystemFontOfSize_(12))
            episode_label.setAlignment_(NSCenterTextAlignment)
            content_view.addSubview_(episode_label)

            episode_popup = NSPopUpButton.alloc().initWithFrame_pullsDown_(
                NSMakeRect(
                    FLOAT_MARGIN_X,
                    FLOAT_EPISODE_COMBO_Y,
                    FLOAT_BTN_WIDTH,
                    FLOAT_EPISODE_COMBO_HEIGHT
                ),
                False
            )
            episode_popup.setTarget_(self)
            episode_popup.setAction_(objc.selector(self.onEpisodeSelected_, signature=b'v@:@'))
            content_view.addSubview_(episode_popup)

            label = NSTextField.alloc().initWithFrame_(
                NSMakeRect(FLOAT_MARGIN_X, FLOAT_LABEL_Y, FLOAT_BTN_WIDTH, FLOAT_LABEL_HEIGHT)
            )
            label.setStringValue_(translate_source("Список реплик:"))
            label.setEditable_(False)
            label.setSelectable_(False)
            label.setBezeled_(False)
            label.setDrawsBackground_(False)
            label.setFont_(NSFont.boldSystemFontOfSize_(12))
            label.setAlignment_(NSCenterTextAlignment)
            content_view.addSubview_(label)
            
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
            self._episode_popup = episode_popup
            self._cocoa_episode_items = []

            btn_hide = NSButton.alloc().initWithFrame_(
                NSMakeRect(FLOAT_BTN_HIDE_X, FLOAT_BTN_HIDE_Y, FLOAT_BTN_HIDE_WIDTH, FLOAT_BTN_HIDE_HEIGHT)
            )
            btn_hide.setTitle_(translate_source("Скрыть"))
            btn_hide.setBezelStyle_(NSSmallSquareBezelStyle)
            btn_hide.setTarget_(self)
            btn_hide.setAction_(objc.selector(self.onHideClicked_, signature=b'v@:@'))
            content_view.addSubview_(btn_hide)

            self._cocoa_window.setContentView_(content_view)
            self._content_view = content_view

            self._btn_prev = btn_prev
            self._btn_next = btn_next
            self.sync_cocoa_episode_combo()
            
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

        episode_layout = QHBoxLayout()
        episode_layout.addWidget(QLabel("Серия:"))
        self.episode_combo = QComboBox()
        self.episode_combo.setMinimumWidth(160)
        self.episode_combo.currentIndexChanged.connect(
            self.on_qt_episode_changed
        )
        episode_layout.addWidget(self.episode_combo, 1)
        layout.addLayout(episode_layout)

        layout.addWidget(QLabel("<b>Список реплик:</b>"))
        self.replica_list = QListWidget()
        self.replica_list.itemClicked.connect(
            lambda item: self.teleprompter.jump_to_specific_time(item.data(Qt.UserRole))
        )
        layout.addWidget(self.replica_list)

        btn_close = QPushButton("Скрыть")
        btn_close.clicked.connect(self.hide_window)
        layout.addWidget(btn_close)

        self.sync_replica_list()
        self.sync_episode_combo()

    def _episode_items(self):
        """Return episode items from the main teleprompter combo."""
        combo = getattr(self.teleprompter, "combo_episode", None)
        if not combo:
            return []

        items = []
        for index in range(combo.count()):
            text = combo.itemText(index)
            data = combo.itemData(index)
            items.append((text, str(data if data is not None else text)))
        return items

    def _current_episode_index(self, items) -> int:
        """Return current episode index in a copied item list."""
        current = str(getattr(self.teleprompter, "ep_num", ""))
        for index, (_, data) in enumerate(items):
            if str(data) == current:
                return index
        return -1

    def _switch_to_episode(self, ep_num: str) -> None:
        """Switch teleprompter episode from the floating window."""
        if not self.teleprompter:
            return
        self.teleprompter.switch_episode(str(ep_num))
        self.sync_episode_combo()

    def onPrevClicked_(self, sender) -> None:
        """Onprevclicked."""
        if self.teleprompter:
            self.teleprompter.navigate_to_replica_in_direction(-1)

    def onNextClicked_(self, sender) -> None:
        """Onnextclicked."""
        if self.teleprompter:
            self.teleprompter.navigate_to_replica_in_direction(1)

    def onEpisodeSelected_(self, sender) -> None:
        """Handle Cocoa episode selection."""
        if not hasattr(self, "_cocoa_episode_items"):
            return

        index = sender.indexOfSelectedItem()
        if 0 <= index < len(self._cocoa_episode_items):
            self._switch_to_episode(self._cocoa_episode_items[index][1])

    def onHideClicked_(self, sender) -> None:
        """Onhideclicked."""
        if self._cocoa_window:
            self._cocoa_window.orderOut_(None)
        if hasattr(self, 'teleprompter') and self.teleprompter:
            self.teleprompter.hide_float_window()

    def show_cocoa_window(self) -> None:
        """Show cocoa window."""
        if self._cocoa_window:
            self.sync_cocoa_episode_combo()
            self.update_cocoa_replica_list()
            
            if hasattr(self, 'teleprompter') and self.teleprompter:
                current_time = self.teleprompter.last_known_time
                for i, item in enumerate(self._replica_items):
                    if abs(item['time'] - current_time) < 0.01:
                        self.update_cocoa_selection(i)
                        break
            
            self._cocoa_window.orderFrontRegardless()
            self._cocoa_window.makeKeyAndOrderFront_(None)

    def sync_cocoa_episode_combo(self) -> None:
        """Synchronize Cocoa episode popup."""
        if not hasattr(self, "_episode_popup"):
            return

        items = self._episode_items()
        self._cocoa_episode_items = items
        self._episode_popup.removeAllItems()
        for text, _ in items:
            self._episode_popup.addItemWithTitle_(text)

        current_index = self._current_episode_index(items)
        if current_index >= 0:
            self._episode_popup.selectItemAtIndex_(current_index)

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
        
        text = '\n'.join(replicas) if replicas else translate_source("Нет реплик")
        self._replica_text_view.setString_(text)
        
        from Foundation import NSMakeRange
        self._replica_text_view.scrollRangeToVisible_(NSMakeRange(0, 0))
        logger.debug("Cocoa: текст обновлён")

    def onReplicaSelected_(self, notification) -> None:
        """Onreplicaselected."""
        text_view = notification.object()
        selected_range = text_view.selectedRange()
        selected_location = selected_range.location
        
        if selected_location >= 0 and hasattr(self, '_replica_items'):
            text = text_view.string()
            if text:
                lines = text.split('\n')
                current_pos = 0
                
                for i, line in enumerate(lines):
                    line_start = current_pos
                    line_end = current_pos + len(line)
                    
                    if line_start <= selected_location <= line_end:
                        if i < len(self._replica_items):
                            time_code = self._replica_items[i].get('time')
                            if time_code:
                                self.on_replica_clicked(time_code)
                        break
                    
                    current_pos = line_end + 1

    def update_cocoa_selection(self, index: int) -> None:
        """Update cocoa selection."""
        if not hasattr(self, '_replica_text_view') or not self._replica_items:
            return
        
        if 0 <= index < len(self._replica_items):
            text = self._replica_text_view.string()
            if text:
                lines = text.split('\n')
                pos = 0
                for i in range(index):
                    pos += len(lines[i]) + 1
                
                from Foundation import NSMakeRange
                line_length = len(lines[index]) if index < len(lines) else 0
                self._replica_text_view.setSelectedRange_(NSMakeRange(pos, line_length))
                
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

    def sync_episode_combo(self) -> None:
        """Synchronize episode combo."""
        if platform.system() == "Darwin":
            self.sync_cocoa_episode_combo()
            return

        if not hasattr(self, "episode_combo"):
            return

        items = self._episode_items()
        self.episode_combo.blockSignals(True)
        self.episode_combo.clear()
        for text, data in items:
            self.episode_combo.addItem(text, data)

        current_index = self._current_episode_index(items)
        if current_index >= 0:
            self.episode_combo.setCurrentIndex(current_index)
        self.episode_combo.blockSignals(False)

    def on_qt_episode_changed(self, index: int) -> None:
        """Handle Qt episode selection."""
        if not hasattr(self, "episode_combo"):
            return

        ep_num = self.episode_combo.itemData(index)
        if ep_num is not None:
            self._switch_to_episode(str(ep_num))

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
            if event.pos().y() < 30:
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
