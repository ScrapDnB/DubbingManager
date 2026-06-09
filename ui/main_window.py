"""Main application window."""

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QFileDialog, QTableWidget, QTableWidgetItem, QTableView,
    QColorDialog, QComboBox, QLabel, QHeaderView, QInputDialog,
    QFrame, QSpinBox, QLineEdit, QListWidget, QListWidgetItem,
    QCheckBox, QGroupBox, QFormLayout, QMessageBox, QSlider,
    QAbstractItemView, QStackedWidget, QDoubleSpinBox, QRadioButton,
    QGridLayout, QScrollArea, QSplitter, QSizePolicy, QToolBar,
    QDialogButtonBox, QTextEdit, QDialog, QProgressDialog, QApplication,
    QStyledItemDelegate, QStyle
)
from PySide6.QtGui import (
    QColor, QFont, QAction, QKeySequence, QPen, QBrush, QDesktopServices
)
from PySide6.QtCore import (
    Qt, QUrl, QTimer, Signal, QRectF, QEvent, Slot, QPersistentModelIndex,
    QAbstractTableModel, QModelIndex
)
from typing import Dict, List, Any, Optional, Set, Tuple, Callable
import json
import re
import os
import sys
from copy import deepcopy
from datetime import datetime
import logging

try:
    import openpyxl
    from openpyxl.styles import Font, Alignment, PatternFill
    from openpyxl.utils import get_column_letter
    EXCEL_AVAILABLE = True
except ImportError:
    EXCEL_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning("openpyxl not available - Excel export disabled")

from config.constants import (
    DEFAULT_DOCX_IMPORT_CONFIG,
    MY_PALETTE,
    DEFAULT_PROMPTER_CONFIG,
    DEFAULT_EXPORT_CONFIG,
    MAIN_WINDOW_WIDTH,
    MAIN_WINDOW_HEIGHT,
    ACTOR_PANEL_WIDTH,
    TOOLS_SIDEBAR_WIDTH,
    SEARCH_EDIT_WIDTH,
    EPISODE_COMBO_MIN_WIDTH,
    BTN_RENAME_WIDTH,
    BTN_ICON_WIDTH,
    BTN_COMPOUND_ICON_WIDTH,
    BTN_SAVE_ICON_WIDTH,
    TABLE_ROW_HEIGHT,
    MAIN_TABLE_COUNT_COL_WIDTH,
    MAIN_TABLE_SCOPE_COL_WIDTH,
    MAIN_TABLE_VIDEO_COL_WIDTH,
    AUTOSAVE_INTERVAL_MS,
    PROJECT_BAR_SPACING,
    PROJECT_FOLDER_BTN_WIDTH,
    ABOUT_BTN_WIDTH,
    EXPORT_PANEL_SPACING,
    APP_VERSION,
)
from utils.helpers import (
    ass_time_to_seconds,
    format_seconds_to_tc,
    customize_table,
    wrap_widget,
    log_exception,
    get_video_fps,
    natural_sort_key
)
from utils.i18n import set_language, tr, translate_source, translate_widget_tree
from services import (
    ProjectService,
    EpisodeService,
    ActorService,
    ExportService,
    GlobalSettingsService,
    ProjectFolderService,
    ScriptTextService,
    AssignmentTransferService,
    UpdateService,
    ASSIGNMENT_SCOPE_GLOBAL,
    ASSIGNMENT_SCOPE_EPISODE,
    LOCAL_UNASSIGNED_ACTOR_ID,
    get_actor_for_character,
    get_actor_roles,
    get_assignment_map,
    get_assignment_scope,
    rename_character_assignments,
)
from ui.controllers import (
    ActorController,
    EpisodeController,
    ExportController,
    ProjectController,
)
from .dialogs import (
    ActorFilterDialog,
    PrompterColorDialog,
    CustomColorDialog,
    ReaperExportDialog,
    ActorRolesDialog,
    ProjectRolesDialog,
    GlobalSearchDialog,
    SummaryDialog,
    ProjectFilesDialog,
    SettingsDialog,
    DocxImportDialog,
)
from .teleprompter import TeleprompterWindow
from core.commands import (
    UndoStack,
    AddActorCommand,
    DeleteActorCommand,
    RenameActorCommand,
    UpdateActorColorCommand,
    AssignActorToCharacterCommand,
    RenameCharacterCommand,
    AddEpisodeCommand,
    RenameEpisodeCommand,
    DeleteEpisodeCommand,
    UpdateProjectNameCommand,
    SetProjectFolderCommand,
)

logger = logging.getLogger(__name__)


CHAR_NAME_ROLE = Qt.UserRole
SCOPE_ROLE = Qt.UserRole + 1
ACTOR_ID_ROLE = Qt.UserRole + 2


class QuickSubtitleDropZone(QFrame):
    """Drop zone for quick subtitle-to-montage conversion."""

    filesDropped = Signal(list, bool)

    SUPPORTED_EXTENSIONS = {".ass", ".srt"}

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setMinimumHeight(92)
        self.setFrameShape(QFrame.StyledPanel)
        self.setCursor(Qt.PointingHandCursor)
        self.setToolTip(
            "Зажмите Option/Alt при перетаскивании, чтобы сначала открыть превью."
        )
        self.setStyleSheet(
            """
            QuickSubtitleDropZone {
                border: 1px dashed palette(placeholder-text);
                border-radius: 6px;
                background: transparent;
            }
            QuickSubtitleDropZone[dragActive="true"] {
                border: 2px solid palette(highlight);
                background: palette(alternate-base);
            }
            QLabel {
                color: palette(text);
            }
            """
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(4)

        title = QLabel("Быстрый конвертер")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-weight: 600; color: palette(text);")
        layout.addWidget(title)

        hint = QLabel("Перетащите ASS или SRT\nМонтажные листы появятся рядом")
        hint.setAlignment(Qt.AlignCenter)
        hint.setWordWrap(True)
        layout.addWidget(hint)

    def _set_drag_active(self, active: bool) -> None:
        """Update drop zone visual state."""
        self.setProperty("dragActive", active)
        self.style().unpolish(self)
        self.style().polish(self)

    def _supported_files(self, event) -> List[str]:
        """Return supported local files from a drag event."""
        if not event.mimeData().hasUrls():
            return []

        files = []
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if self.is_supported_path(path):
                files.append(path)
        return files

    @classmethod
    def is_supported_path(cls, path: str) -> bool:
        """Return True if path is a supported subtitle source."""
        return os.path.splitext(path)[1].lower() in cls.SUPPORTED_EXTENSIONS

    def dragEnterEvent(self, event) -> None:
        """Accept ASS/SRT files."""
        if self._supported_files(event):
            self._set_drag_active(True)
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event) -> None:
        """Keep drag accepted while hovering."""
        if self._supported_files(event):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragLeaveEvent(self, event) -> None:
        """Reset visual state when drag leaves."""
        self._set_drag_active(False)
        event.accept()

    def dropEvent(self, event) -> None:
        """Emit dropped subtitle files."""
        files = self._supported_files(event)
        self._set_drag_active(False)
        if files:
            event.acceptProposedAction()
            preview_first = bool(event.keyboardModifiers() & Qt.AltModifier)
            self.filesDropped.emit(files, preview_first)
        else:
            event.ignore()


class ScopeComboDelegate(QStyledItemDelegate):
    """Scope Combo Delegate class."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._editing_index = QPersistentModelIndex()

    def createEditor(self, parent, option, index):
        self._editing_index = QPersistentModelIndex(index)
        combo = QComboBox(parent)
        combo.addItem(translate_source("Глобально"), ASSIGNMENT_SCOPE_GLOBAL)
        combo.addItem(translate_source("Серия"), ASSIGNMENT_SCOPE_EPISODE)
        return combo

    def setEditorData(self, editor, index) -> None:
        scope = index.data(SCOPE_ROLE) or ASSIGNMENT_SCOPE_GLOBAL
        found = editor.findData(scope)
        editor.setCurrentIndex(found if found >= 0 else 0)

    def setModelData(self, editor, model, index) -> None:
        model.setData(index, editor.currentData(), SCOPE_ROLE)
        model.setData(index, editor.currentText(), Qt.DisplayRole)

    def updateEditorGeometry(self, editor, option, index) -> None:
        editor.setGeometry(option.rect)

    def destroyEditor(self, editor, index) -> None:
        self._editing_index = QPersistentModelIndex()
        super().destroyEditor(editor, index)

    def paint(self, painter, option, index) -> None:
        if QPersistentModelIndex(index) == self._editing_index:
            brush = (
                option.palette.highlight()
                if option.state & QStyle.State_Selected
                else option.palette.base()
            )
            painter.fillRect(option.rect, brush)
            return
        super().paint(painter, option, index)


class ActorComboDelegate(QStyledItemDelegate):
    """Actor Combo Delegate class."""

    def __init__(self, main_window: "MainWindow") -> None:
        super().__init__(main_window)
        self.main_window = main_window
        self._editing_index = QPersistentModelIndex()

    def createEditor(self, parent, option, index):
        self._editing_index = QPersistentModelIndex(index)
        combo = QComboBox(parent)
        combo.addItem("-", None)
        for aid, info in self.main_window.data.get("actors", {}).items():
            combo.addItem(info.get("name", aid), aid)
        return combo

    def setEditorData(self, editor, index) -> None:
        actor_id = index.data(ACTOR_ID_ROLE)
        found = editor.findData(actor_id)
        editor.setCurrentIndex(found if found >= 0 else 0)

    def setModelData(self, editor, model, index) -> None:
        model.setData(index, editor.currentData(), ACTOR_ID_ROLE)
        model.setData(index, editor.currentText(), Qt.DisplayRole)

    def updateEditorGeometry(self, editor, option, index) -> None:
        editor.setGeometry(option.rect)

    def destroyEditor(self, editor, index) -> None:
        self._editing_index = QPersistentModelIndex()
        super().destroyEditor(editor, index)

    def paint(self, painter, option, index) -> None:
        if QPersistentModelIndex(index) == self._editing_index:
            brush = (
                option.palette.highlight()
                if option.state & QStyle.State_Selected
                else option.palette.base()
            )
            painter.fillRect(option.rect, brush)
            return
        super().paint(painter, option, index)


class MainTableModel(QAbstractTableModel):
    """Main Table Model class."""

    HEADER_KEYS = [
        "table.character",
        "table.lines",
        "table.rings",
        "table.words",
        "table.scope",
        "table.actor",
        None,
    ]

    def __init__(self, main_window: "MainWindow") -> None:
        super().__init__(main_window)
        self.main_window = main_window
        self.rows: List[Dict[str, Any]] = []

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self.rows)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self.HEADER_KEYS)

    def headerData(self, section: int, orientation: Qt.Orientation, role: int):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            key = self.HEADER_KEYS[section]
            return tr(key) if key else "📺"
        return None

    def flags(self, index: QModelIndex):
        if not index.isValid():
            return Qt.NoItemFlags

        flags = Qt.ItemIsEnabled | Qt.ItemIsSelectable
        if index.column() in (0, 4, 5):
            flags |= Qt.ItemIsEditable
        return flags

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole):
        if not index.isValid():
            return None

        row = self.rows[index.row()]
        column = index.column()

        if role in (Qt.DisplayRole, Qt.EditRole):
            return self._display_value(row, column)

        if role == Qt.TextAlignmentRole and column == 6:
            return Qt.AlignCenter

        if role == Qt.ToolTipRole:
            if column == 5:
                return self._actor_tooltip(row.get("actor_id"))
            if column == 6:
                return translate_source("Открыть предпросмотр персонажа")

        if role == Qt.BackgroundRole and column == 5:
            return self._actor_brush(row.get("actor_id"))

        if role == CHAR_NAME_ROLE:
            return row.get("name")
        if role == SCOPE_ROLE and column == 4:
            return row.get("scope")
        if role == ACTOR_ID_ROLE and column == 5:
            return row.get("actor_id")

        return None

    def setData(self, index: QModelIndex, value: Any, role: int = Qt.EditRole) -> bool:
        if not index.isValid():
            return False

        row = self.rows[index.row()]
        column = index.column()

        if column == 0 and role == Qt.EditRole:
            old_name = row.get("name", "")
            new_name = str(value).strip()
            if not new_name or new_name == old_name:
                return False
            if self.main_window.rename_character_from_table(old_name, new_name):
                row["name"] = new_name
                self.dataChanged.emit(index, index, [Qt.DisplayRole, CHAR_NAME_ROLE])
                return True
            return False

        if column == 4 and role == SCOPE_ROLE:
            new_scope = value or ASSIGNMENT_SCOPE_GLOBAL
            if new_scope == row.get("scope"):
                return False
            row["scope"] = new_scope
            self.main_window.update_assignment_scope_value(
                row["name"], new_scope, row.get("actor_id")
            )
            self.dataChanged.emit(
                self.index(index.row(), 4),
                self.index(index.row(), 5),
                [Qt.DisplayRole, SCOPE_ROLE, ACTOR_ID_ROLE, Qt.BackgroundRole],
            )
            return True

        if column == 5 and role == ACTOR_ID_ROLE:
            if value == row.get("actor_id"):
                return False
            row["actor_id"] = value
            self.main_window.update_map_value(
                row["name"], row.get("actor_id"), row.get("scope")
            )
            self.dataChanged.emit(
                index,
                index,
                [Qt.DisplayRole, ACTOR_ID_ROLE, Qt.BackgroundRole, Qt.ToolTipRole],
            )
            return True

        if role == Qt.DisplayRole:
            return True

        return False

    def set_rows(self, rows: List[Dict[str, Any]]) -> None:
        self.beginResetModel()
        self.rows = rows
        self.endResetModel()

    def row_data(self, row: int) -> Optional[Dict[str, Any]]:
        if 0 <= row < len(self.rows):
            return self.rows[row]
        return None

    def update_actor_for_character(self, char_name: str) -> None:
        for row_idx, row in enumerate(self.rows):
            if row.get("name") != char_name:
                continue

            ep = self.main_window.ep_combo.currentData()
            row["actor_id"] = get_actor_for_character(
                self.main_window.data, char_name, ep
            )
            idx = self.index(row_idx, 5)
            self.dataChanged.emit(
                idx,
                idx,
                [Qt.DisplayRole, ACTOR_ID_ROLE, Qt.BackgroundRole, Qt.ToolTipRole],
            )
            return

    def _display_value(self, row: Dict[str, Any], column: int) -> Any:
        if column == 0:
            return row.get("name", "")
        if column == 1:
            return row.get("lines", 0)
        if column == 2:
            return row.get("rings", 0)
        if column == 3:
            return row.get("words", 0)
        if column == 4:
            return (
                translate_source("Серия")
                if row.get("scope") == ASSIGNMENT_SCOPE_EPISODE
                else translate_source("Глобально")
            )
        if column == 5:
            return self._actor_name(row.get("actor_id"))
        if column == 6:
            return "📺"
        return None

    def _actor_name(self, actor_id: Optional[str]) -> str:
        if not actor_id:
            return "-"
        return self.main_window.data.get("actors", {}).get(
            actor_id, {}
        ).get("name", "-")

    def _actor_tooltip(self, actor_id: Optional[str]) -> str:
        if not actor_id:
            return translate_source("Актёр не назначен")
        actor = self.main_window.data.get("actors", {}).get(actor_id, {})
        color = QColor(actor.get("color", ""))
        if color.isValid():
            return (
                f"{actor.get('name', actor_id)}\n"
                f"{translate_source('Цвет актёра:')} {color.name()}"
            )
        return actor.get("name", actor_id)

    def _actor_brush(self, actor_id: Optional[str]):
        if not actor_id:
            return None
        actor = self.main_window.data.get("actors", {}).get(actor_id, {})
        color = QColor(actor.get("color", ""))
        if not color.isValid():
            return None
        color.setAlpha(72)
        return QBrush(color)


class MainWindow(QMainWindow):
    """Main Window class."""

    # Class attributes with type hints
    current_project_path: Optional[str]
    preview_window: Optional['HtmlLivePreview']
    teleprompter_window: Optional['TeleprompterWindow']
    data: Dict[str, Any]
    current_ep_stats: List[Dict[str, Any]]
    character_names_changed: Dict[str, bool]
    sort_col: int
    sort_desc: bool

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Dubbing Manager")
        self.resize(MAIN_WINDOW_WIDTH, MAIN_WINDOW_HEIGHT)
        self.setAcceptDrops(True)

        self.project_service = ProjectService()
        self.actor_service = ActorService()
        self.global_settings_service = GlobalSettingsService()
        self.project_folder_service = ProjectFolderService()
        self.script_text_service = ScriptTextService()
        self.assignment_transfer_service = AssignmentTransferService()
        self.update_service = UpdateService()
        self.episode_service = EpisodeService()

        self.actor_controller: Optional[ActorController] = None
        self.episode_controller: Optional[EpisodeController] = None
        self.export_controller: Optional[ExportController] = None
        self.project_controller: Optional[ProjectController] = None

        self.undo_stack = UndoStack()
        self.undo_stack.on_change(self._on_undo_stack_change)

        self.current_project_path = None
        self.is_dirty = False
        self.sort_col = 1
        self.sort_desc = True
        self.preview_window = None
        self.teleprompter_window = None

        self.global_settings = self.global_settings_service.load_settings()
        set_language(self.global_settings.get("language", "ru"))

        self.data = self.project_service.create_new_project("Новый проект")
        self._apply_global_settings_to_project_data(self.data)

        self._init_controllers()

        self._apply_global_settings_to_project()

        self.current_ep_stats = []
        self.character_names_changed = {}
        self.text_changes = {}

        self._init_ui()
        self.update_window_title()
        self._update_new_project_button()

        self.autosave_timer = QTimer(self)
        self.autosave_timer.timeout.connect(self._on_autosave_timer)
        self.autosave_timer.start(AUTOSAVE_INTERVAL_MS)

    def _init_controllers(self) -> None:
        """Init controllers."""
        self.episode_controller = EpisodeController(
            episode_service=self.episode_service,
            data_ref=self.data,
            on_dirty_callback=self.set_dirty
        )
        self.export_controller = ExportController(
            data_ref=self.data,
            episode_service=self.episode_service,
            on_dirty_callback=self.set_dirty
        )
        self.project_controller = ProjectController(
            project_service=self.project_service,
            data_ref=self.data,
            undo_stack=self.undo_stack,
            on_dirty_callback=self.set_dirty
        )

    def _on_autosave_timer(self) -> None:
        """Handle autosave timer."""
        if self.project_controller:
            self.project_controller.auto_save()

    def _init_ui(self) -> None:
        """Init ui."""
        central: QWidget = QWidget()
        self.setCentralWidget(central)
        main_layout: QHBoxLayout = QHBoxLayout(central)

        self._init_actor_panel(main_layout)

        self._init_main_panel(main_layout)

        self._setup_undo_redo_shortcuts()

    def _setup_undo_redo_shortcuts(self) -> None:
        """Setup undo redo shortcuts."""
        undo_shortcut = QKeySequence("Ctrl+Z")
        undo_action = QAction("Undo", self)
        undo_action.setShortcut(undo_shortcut)
        undo_action.triggered.connect(self.undo)
        self.addAction(undo_action)

        redo_shortcut = QKeySequence("Ctrl+Shift+Z")
        redo_action = QAction("Redo", self)
        redo_action.setShortcut(redo_shortcut)
        redo_action.triggered.connect(self.redo)
        self.addAction(redo_action)

    def _init_actor_panel(self, main_layout: QHBoxLayout) -> None:
        """Init actor panel."""
        left_panel: QVBoxLayout = QVBoxLayout()
        left_widget = QFrame()
        left_widget.setFixedWidth(ACTOR_PANEL_WIDTH)
        left_widget.setFrameShape(QFrame.StyledPanel)
        left_widget.setLayout(left_panel)

        actor_header = QHBoxLayout()
        self.lbl_actor_header = QLabel()
        actor_header.addWidget(self.lbl_actor_header)
        self.actor_base_mode = QComboBox()
        self.actor_base_mode.addItem("", "project")
        self.actor_base_mode.addItem("", "global")
        self.actor_base_mode.currentIndexChanged.connect(
            self._on_actor_base_mode_changed
        )
        actor_header.addWidget(self.actor_base_mode, stretch=1)
        left_panel.addLayout(actor_header)

        self.actor_table = QTableWidget(0, 4)
        customize_table(self.actor_table)

        self.actor_controller = ActorController(
            actor_table=self.actor_table,
            actor_service=self.actor_service,
            data_ref=self.data,
            on_dirty_callback=self.set_dirty,
            on_edit_roles_callback=self.edit_roles,
            on_color_click_callback=self.on_actor_color_clicked
        )
        self.actor_table.itemChanged.connect(self.on_actor_renamed)

        left_panel.addWidget(self.actor_table)

        btn_layout = QHBoxLayout()
        
        self.btn_add_actor = QPushButton()
        self.btn_add_actor.clicked.connect(self.add_actor_button_clicked)
        btn_layout.addWidget(self.btn_add_actor)
        
        self.btn_delete_actor = QPushButton()
        self.btn_delete_actor.clicked.connect(self.delete_actor_button_clicked)
        btn_layout.addWidget(self.btn_delete_actor)

        self.btn_add_project_actors_to_global = QPushButton()
        self.btn_add_project_actors_to_global.clicked.connect(
            self.actor_transfer_button_clicked
        )
        btn_layout.addWidget(self.btn_add_project_actors_to_global)
        
        left_panel.addLayout(btn_layout)

        self.btn_project_summary = QPushButton()
        self.btn_project_summary.clicked.connect(self.show_project_summary)
        left_panel.addWidget(self.btn_project_summary)

        main_layout.addWidget(left_widget)

    def _init_main_panel(self, main_layout: QHBoxLayout) -> None:
        """Init main panel."""
        right_panel: QVBoxLayout = QVBoxLayout()

        self._init_project_bar(right_panel)

        self._init_episode_controls(right_panel)

        self._init_center_area(right_panel)

        self._init_bottom_panel(right_panel)

        main_layout.addLayout(right_panel)

    def _init_project_bar(self, layout: QHBoxLayout) -> None:
        """Init project bar."""
        top: QHBoxLayout = QHBoxLayout()

        self.recent_projects_combo = QComboBox()
        self.recent_projects_combo.setMinimumWidth(EPISODE_COMBO_MIN_WIDTH)
        self.recent_projects_combo.activated.connect(
            self._on_recent_project_activated
        )
        top.addWidget(self.recent_projects_combo)
        self._update_recent_projects_combo()

        self.btn_new_project = QPushButton("📄")
        self.btn_new_project.setMinimumWidth(BTN_SAVE_ICON_WIDTH)
        self.btn_new_project.clicked.connect(self.create_new_project)
        top.addWidget(self.btn_new_project)

        self.btn_load = QPushButton("📂")
        self.btn_load.setMinimumWidth(BTN_SAVE_ICON_WIDTH)
        self.btn_load.clicked.connect(self.load_project_dialog)
        top.addWidget(self.btn_load)

        self.btn_save = QPushButton("💾")
        self.btn_save.setMinimumWidth(BTN_SAVE_ICON_WIDTH)
        self.btn_save.clicked.connect(self.save_project)
        top.addWidget(self.btn_save)

        self.btn_copy = QPushButton("💾 +")
        self.btn_copy.setMinimumWidth(BTN_COMPOUND_ICON_WIDTH)
        self.btn_copy.clicked.connect(self.save_project_as)
        top.addWidget(self.btn_copy)

        # Buttons Undo/Redo
        self.btn_undo = QPushButton("↶")
        self.btn_undo.setFixedWidth(PROJECT_FOLDER_BTN_WIDTH)
        self.btn_undo.clicked.connect(self.undo)
        self.btn_undo.setEnabled(False)
        top.addWidget(self.btn_undo)

        self.btn_redo = QPushButton("↷")
        self.btn_redo.setFixedWidth(PROJECT_FOLDER_BTN_WIDTH)
        self.btn_redo.clicked.connect(self.redo)
        self.btn_redo.setEnabled(False)
        top.addWidget(self.btn_redo)

        top.addStretch()

        self.btn_health = QPushButton()
        self.btn_health.clicked.connect(self.open_project_health_dialog)
        top.addWidget(self.btn_health)

        btn_about = QPushButton("ℹ️")
        btn_about.setFixedWidth(ABOUT_BTN_WIDTH)
        btn_about.clicked.connect(self.show_about)
        top.addWidget(btn_about)

        layout.addLayout(top)

    def _init_episode_controls(self, layout: QHBoxLayout) -> None:
        """Init episode controls."""
        ep_ctrl = QHBoxLayout()

        self.ep_combo = QComboBox()
        self.ep_combo.setMinimumWidth(EPISODE_COMBO_MIN_WIDTH)
        self.ep_combo.currentIndexChanged.connect(self.change_episode)
        self.lbl_episode = QLabel()
        ep_ctrl.addWidget(self.lbl_episode)
        ep_ctrl.addWidget(self.ep_combo)

        self.btn_import = QPushButton()
        self.btn_import.clicked.connect(self.import_files)
        ep_ctrl.addWidget(self.btn_import)

        self.btn_vid = QPushButton("🎬 +")
        self.btn_vid.setMinimumWidth(BTN_COMPOUND_ICON_WIDTH)
        self.btn_vid.clicked.connect(self.set_episode_video)
        ep_ctrl.addWidget(self.btn_vid)

        btn_ren = QPushButton("✎")
        btn_ren.setMinimumWidth(BTN_RENAME_WIDTH)
        btn_ren.clicked.connect(self.rename_episode)
        ep_ctrl.addWidget(btn_ren)

        btn_del = QPushButton("🗑")
        btn_del.setMinimumWidth(BTN_RENAME_WIDTH)
        btn_del.clicked.connect(self.delete_episode_dialog)
        ep_ctrl.addWidget(btn_del)
        
        ep_ctrl.addStretch()

        self.actor_filter_combo = QComboBox()
        self.actor_filter_combo.setMinimumWidth(150)
        self.actor_filter_combo.currentIndexChanged.connect(self.refresh_main_table)
        self.lbl_actor_filter = QLabel()
        ep_ctrl.addWidget(self.lbl_actor_filter)
        ep_ctrl.addWidget(self.actor_filter_combo)

        self.filter_unassigned = QCheckBox()
        self.filter_unassigned.toggled.connect(self.refresh_main_table)
        ep_ctrl.addWidget(self.filter_unassigned)

        self.search_edit = QLineEdit()
        self.search_edit.setFixedWidth(SEARCH_EDIT_WIDTH)
        self.search_edit.textChanged.connect(self.refresh_main_table)
        ep_ctrl.addWidget(self.search_edit)
        
        self.btn_glob_search = QPushButton()
        self.btn_glob_search.clicked.connect(self.open_global_search)
        ep_ctrl.addWidget(self.btn_glob_search)
        
        layout.addLayout(ep_ctrl)
    
    def _init_center_area(self, layout: QHBoxLayout) -> None:
        """Init center area."""
        middle_layout: QHBoxLayout = QHBoxLayout()

        self.table_stack = QStackedWidget()

        self.main_table = QTableView()
        self.main_table_model = MainTableModel(self)
        self.main_table.setModel(self.main_table_model)
        customize_table(self.main_table)
        header = self.main_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.Fixed)
        header.setSectionResizeMode(2, QHeaderView.Fixed)
        header.setSectionResizeMode(3, QHeaderView.Fixed)
        header.setSectionResizeMode(4, QHeaderView.Fixed)
        header.setSectionResizeMode(5, QHeaderView.Stretch)
        header.setSectionResizeMode(6, QHeaderView.Fixed)
        self.main_table.setColumnWidth(1, MAIN_TABLE_COUNT_COL_WIDTH)
        self.main_table.setColumnWidth(2, MAIN_TABLE_COUNT_COL_WIDTH)
        self.main_table.setColumnWidth(3, MAIN_TABLE_COUNT_COL_WIDTH)
        self.main_table.setColumnWidth(4, MAIN_TABLE_SCOPE_COL_WIDTH)
        self.main_table.setColumnWidth(6, MAIN_TABLE_VIDEO_COL_WIDTH)
        self.main_table.setItemDelegateForColumn(4, ScopeComboDelegate(self))
        self.main_table.setItemDelegateForColumn(5, ActorComboDelegate(self))
        self.main_table.horizontalHeader().setSectionsClickable(True)
        self.main_table.horizontalHeader().sectionClicked.connect(
            self.on_header_clicked
        )
        self.main_table.clicked.connect(self.on_main_table_cell_clicked)
        self.main_table.selectionModel().selectionChanged.connect(
            lambda *_: self.update_selected_character_stats()
        )

        self.missing_file_widget = QWidget()
        mf_lay: QVBoxLayout = QVBoxLayout(self.missing_file_widget)

        self.lbl_missing = QLabel()
        self.lbl_missing.setStyleSheet(
            "color: red; font-weight: bold;"
        )
        self.lbl_missing.setAlignment(Qt.AlignCenter)

        self.btn_relink = QPushButton()
        self.btn_relink.clicked.connect(self.relink_file)

        mf_lay.addStretch()
        mf_lay.addWidget(self.lbl_missing)
        mf_lay.addWidget(self.btn_relink)
        mf_lay.addStretch()

        self.table_stack.addWidget(self.main_table)
        self.table_stack.addWidget(self.missing_file_widget)

        middle_layout.addWidget(self.table_stack, stretch=1)

        self._init_tools_sidebar(middle_layout)

        layout.addLayout(middle_layout)

    def _init_tools_sidebar(self, layout: QHBoxLayout) -> None:
        """Init tools sidebar."""
        tools_sidebar_widget = QWidget()
        tools_sidebar_widget.setFixedWidth(TOOLS_SIDEBAR_WIDTH)
        tools_sidebar_layout = QVBoxLayout(tools_sidebar_widget)
        tools_sidebar_layout.setContentsMargins(5, 0, 0, 0)
        
        self.lbl_tools = QLabel()
        tools_sidebar_layout.addWidget(self.lbl_tools)
        
        self.btn_all_v = QPushButton()
        self.btn_all_v.clicked.connect(self.open_live_preview)
        tools_sidebar_layout.addWidget(self.btn_all_v)

        self.btn_prompter = QPushButton()
        self.btn_prompter.clicked.connect(self.open_teleprompter)
        tools_sidebar_layout.addWidget(self.btn_prompter)

        self.btn_reaper = QPushButton()
        self.btn_reaper.clicked.connect(self.export_to_reaper_rpp)
        tools_sidebar_layout.addWidget(self.btn_reaper)

        self.btn_ep_sum = QPushButton()
        self.btn_ep_sum.clicked.connect(self.show_episode_summary)
        tools_sidebar_layout.addWidget(self.btn_ep_sum)

        self.quick_converter_drop_zone = QuickSubtitleDropZone()
        self.quick_converter_drop_zone.filesDropped.connect(
            self.convert_dropped_subtitles
        )
        tools_sidebar_layout.addWidget(self.quick_converter_drop_zone)

        tools_sidebar_layout.addStretch()

        self.character_stats_group = QGroupBox()
        stats_layout = QVBoxLayout(self.character_stats_group)
        self.lbl_character_stats_name = QLabel()
        self.lbl_character_stats_name.setWordWrap(True)
        self.lbl_character_stats_name.setStyleSheet("font-weight: bold;")
        stats_layout.addWidget(self.lbl_character_stats_name)

        self.lbl_character_stats_totals = QLabel()
        stats_layout.addWidget(self.lbl_character_stats_totals)

        self.txt_character_stats_episodes = QTextEdit()
        self.txt_character_stats_episodes.setReadOnly(True)
        self.txt_character_stats_episodes.setFrameShape(QFrame.NoFrame)
        stats_layout.addWidget(self.txt_character_stats_episodes)
        self._reset_character_stats_panel()
        tools_sidebar_layout.addWidget(self.character_stats_group)

        layout.addWidget(tools_sidebar_widget)
    
    def _init_bottom_panel(self, layout) -> None:
        """Init bottom panel."""
        bottom_panel = QHBoxLayout()

        self.btn_settings = QPushButton()
        self.btn_settings.clicked.connect(self.open_global_settings)
        bottom_panel.addWidget(self.btn_settings)

        self.btn_project_settings = QPushButton()
        self.btn_project_settings.clicked.connect(self.open_project_settings)
        bottom_panel.addWidget(self.btn_project_settings)

        bottom_panel.addStretch()

        self.exp_group = QGroupBox()
        exp_lay = QHBoxLayout(self.exp_group)
        exp_lay.setContentsMargins(5, 5, 5, 5)

        self.btn_cfg = QPushButton()
        self.btn_cfg.clicked.connect(self.open_export_settings)
        exp_lay.addWidget(self.btn_cfg)

        exp_lay.addSpacing(EXPORT_PANEL_SPACING)

        self.btn_preview = QPushButton()
        self.btn_preview.clicked.connect(self.open_live_preview)
        exp_lay.addWidget(self.btn_preview)

        exp_lay.addSpacing(EXPORT_PANEL_SPACING)

        export_config = self.data.get("export_config", DEFAULT_EXPORT_CONFIG)
        self.chk_exp_html = QCheckBox()
        self.chk_exp_html.setChecked(export_config.get("format_html", True))

        self.chk_exp_xls = QCheckBox("Excel")
        self.chk_exp_xls.setChecked(export_config.get("format_xls", False))
        self.chk_exp_docx = QCheckBox("DOCX")
        self.chk_exp_docx.setChecked(export_config.get("format_docx", False))
        self.chk_exp_html.toggled.connect(self._update_export_format_config)
        self.chk_exp_xls.toggled.connect(self._update_export_format_config)
        self.chk_exp_docx.toggled.connect(self._update_export_format_config)

        self.radio_cur = QRadioButton()
        self.radio_cur.setChecked(True)

        self.radio_all = QRadioButton()

        self.btn_run_export = QPushButton()
        self.btn_run_export.clicked.connect(self.run_unified_export)

        exp_lay.addWidget(self.chk_exp_html)
        exp_lay.addWidget(self.chk_exp_xls)
        exp_lay.addWidget(self.chk_exp_docx)
        exp_lay.addSpacing(EXPORT_PANEL_SPACING)
        exp_lay.addWidget(self.radio_cur)
        exp_lay.addWidget(self.radio_all)
        exp_lay.addSpacing(EXPORT_PANEL_SPACING)
        exp_lay.addWidget(self.btn_run_export)

        bottom_panel.addWidget(self.exp_group)
        self.exp_group.setVisible(False)
        layout.addLayout(bottom_panel)
        self.retranslate_ui()
    

    def set_dirty(self, dirty: bool = True) -> None:
        """Set dirty."""
        if self.project_controller:
            self.project_controller.set_dirty(dirty)
        else:
            self.project_service.set_dirty(dirty)
        self.update_window_title()

    def retranslate_ui(self) -> None:
        """Apply the selected interface language to the main window."""
        if hasattr(self, "lbl_actor_header"):
            self.lbl_actor_header.setText(tr("actor.header"))
            self.actor_base_mode.setItemText(0, tr("actor.base.project"))
            self.actor_base_mode.setItemText(1, tr("actor.base.global"))
            self.btn_project_summary.setText(tr("main.summary"))

        if hasattr(self, "recent_projects_combo"):
            self._update_recent_projects_combo()
            self.btn_new_project.setToolTip(tr("main.new_project.tooltip"))
            self.btn_load.setToolTip(tr("main.open.tooltip"))
            self.btn_save.setToolTip(tr("main.save.tooltip"))
            self.btn_copy.setToolTip(tr("main.save_copy.tooltip"))
            self.btn_undo.setToolTip(tr("main.undo.tooltip"))
            self.btn_redo.setToolTip(tr("main.redo.tooltip"))
            self.btn_health.setText(tr("main.health"))
            self.btn_health.setToolTip(tr("main.health.tooltip"))

        if hasattr(self, "lbl_episode"):
            self.lbl_episode.setText(tr("episode.label"))
            self.btn_import.setText(tr("episode.import"))
            self.btn_vid.setToolTip(tr("main.video.add.tooltip"))
            self.lbl_actor_filter.setText(tr("actor.filter"))
            self.filter_unassigned.setText(tr("episode.unassigned"))
            self.search_edit.setPlaceholderText(tr("main.search.placeholder"))
            self.btn_glob_search.setText(tr("main.global_search"))
            self.lbl_missing.setText(tr("main.missing_file"))
            self.btn_relink.setText(tr("main.relink"))

        if hasattr(self, "lbl_tools"):
            self.lbl_tools.setText("Сценарии")
            self.btn_all_v.setText("Монтажный лист")
            self.btn_prompter.setText("Телесуфлёр")
            self.btn_reaper.setText("Reaper")
            self.btn_ep_sum.setText("Отчёт серии")
            self.character_stats_group.setTitle(tr("stats.group"))

        if hasattr(self, "btn_settings"):
            self.btn_settings.setText(tr("main.settings"))
            self.btn_settings.setToolTip(tr("main.settings.tooltip"))
            self.btn_project_settings.setText(tr("main.project_settings"))
            self.btn_project_settings.setToolTip(
                tr("main.project_settings.tooltip")
            )
            self.exp_group.setTitle(tr("export.group"))
            self.btn_cfg.setText(tr("export.sheet_view"))
            self.btn_cfg.setToolTip(tr("export.sheet_view.tooltip"))
            self.btn_preview.setText(tr("export.preview"))
            self.chk_exp_html.setText(tr("export.html"))
            self.chk_exp_docx.setText("DOCX")
            self.radio_cur.setText(tr("episode.current"))
            self.radio_all.setText(tr("common.all"))
            self.btn_run_export.setText(tr("export.run"))

        self._update_actor_base_buttons()
        self._reset_character_stats_panel()
        self._update_project_folder_button()
        self._update_actor_filter_combo()
        if hasattr(self, "main_table_model"):
            self.main_table_model.headerDataChanged.emit(
                Qt.Horizontal,
                0,
                self.main_table_model.columnCount() - 1
            )
        translate_widget_tree(self)
        self.update_save_ass_button()
        self._update_new_project_button()

    def update_window_title(self) -> None:
        """Update window title."""
        if self.project_controller:
            self.setWindowTitle(self.project_controller.get_window_title())
        else:
            self.setWindowTitle(self.project_service.get_window_title(self.data))

    def _update_new_project_button(self) -> None:
        """Update the new-project button state."""
        if not hasattr(self, "btn_new_project"):
            return
        has_saved_path = bool(
            self.project_controller and
            self.project_controller.get_current_project_path()
        )
        is_dirty = (
            self.project_controller.is_dirty()
            if self.project_controller
            else self.project_service.is_dirty
        )
        self.btn_new_project.setEnabled(has_saved_path or is_dirty)

    def create_new_project(self) -> None:
        """Close the current project and create a new one."""
        if not self.project_controller:
            return
        if not self.project_controller.maybe_save(self):
            return

        new_data = self.project_service.create_new_project("Новый проект")
        self._apply_global_settings_to_project_data(new_data)
        self.data.clear()
        self.data.update(new_data)
        self.episode_service.set_merge_gap_from_config(
            self.data["replica_merge_config"]
        )
        self.project_service.current_project_path = None
        self.current_project_path = None
        self.project_service.set_dirty(False)
        self.undo_stack.clear()
        self.episode_service.clear_cache()
        self.current_ep_stats = []
        self.character_names_changed = {}
        self.text_changes = {}

        self.refresh_actor_list()
        self.update_ep_list()
        self.refresh_main_table()
        self._sync_export_format_controls_from_config()
        self._update_project_folder_button()
        self.update_window_title()
        self._update_new_project_button()
    
    def maybe_save(self) -> bool:
        """Check whether to save."""
        if self.project_controller:
            return self.project_controller.maybe_save(self)
        if not self.project_service.is_dirty:
            return True

        reply = QMessageBox.question(
            self,
            "Сохранить?",
            "Сохранить изменения?",
            QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel
        )

        if reply == QMessageBox.Save:
            return self.save_project()
        return reply == QMessageBox.Discard

    def export_actor_assignments(self) -> None:
        """Export actor base and assignments."""
        default_name = (
            f"{self.data.get('project_name', 'Project')} - "
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
            self.assignment_transfer_service.save_export(self.data, path)
        except Exception as e:
            log_exception(logger, "Failed to export actor assignments", e)
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

    def import_actor_assignments(self) -> None:
        """Import actor base and assignments."""
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
            stats = self.assignment_transfer_service.import_from_file(
                self.data,
                path
            )
            for actor_id, actor in self.data.get("actors", {}).items():
                self.global_settings_service.add_global_actor(
                    actor.get("name", actor_id),
                    gender=actor.get("gender", "")
                )
            self.global_settings["global_actor_base"] = (
                self.global_settings_service.get_global_actor_base()
            )
            self.global_settings_service.save_settings(self.global_settings)
        except Exception as e:
            log_exception(logger, "Failed to import actor assignments", e)
            QMessageBox.critical(
                self,
                "Ошибка",
                f"Не удалось импортировать распределение:\n{e}"
            )
            return

        self.refresh_actor_list()
        self.refresh_main_table()
        self.set_dirty(True)

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

    def on_project_name_changed(self, text: str) -> None:
        """Handle project name change."""
        old_name = self.data.get("project_name", "")
        if text != old_name:
            command = UpdateProjectNameCommand(self.data, text)
            self.undo_stack.push(command)
            self.set_dirty()


    def on_main_table_cell_clicked(self, index: QModelIndex) -> None:
        """Handle main table cell click."""
        if not index.isValid() or index.column() != 6:
            return
        row = self.main_table_model.row_data(index.row())
        char_name = row.get("name") if row else None
        if char_name:
            self.open_preview(char_name)
    
    def rename_character_from_table(self, old_name: str, new_name: str) -> bool:
        """Rename character from table."""
        ep = self.ep_combo.currentData()
        if not ep or new_name == old_name or not new_name:
            return False
        if not self.ensure_working_text_for_episode(
            ep,
            "переименовать персонажа в тексте серии"
        ):
            return False

        command = RenameCharacterCommand(
            self.data["global_map"],
            self.data.get("loaded_episodes", {}),
            self.current_ep_stats,
            ep,
            old_name,
            new_name,
            lambda from_name, to_name: (
                rename_character_assignments(self.data, from_name, to_name),
                self.script_text_service.rename_character(
                    self.data,
                    from_name,
                    to_name,
                    ep
                )
            )
        )
        self.undo_stack.push(command)
        self.episode_service.invalidate_episode(ep)
        self._refresh_open_windows(ep)
        self.character_names_changed[ep] = True
        self.update_save_ass_button()
        self.refresh_actor_list()
        self.set_dirty(True)
        return True

    def _refresh_open_windows(self, ep: str) -> None:
        """Refresh open windows."""
        if hasattr(self, 'preview_window') and self.preview_window:
            self.preview_window.update_preview()

        if hasattr(self, 'teleprompter_window') and self.teleprompter_window:
            self.teleprompter_window.refresh_episode_data()
    
    def update_save_ass_button(self) -> None:
        """Update save ass button."""
        pass

    def _reset_character_stats_panel(self) -> None:
        """Reset character stats panel."""
        if not hasattr(self, "lbl_character_stats_name"):
            return
        self.lbl_character_stats_name.setText(tr("stats.empty"))
        self.lbl_character_stats_totals.setText(tr("stats.totals.empty"))
        self.txt_character_stats_episodes.setPlainText("")

    def update_selected_character_stats(self) -> None:
        """Update selected character stats."""
        selected_rows = self.main_table.selectionModel().selectedRows()
        if not selected_rows:
            self._reset_character_stats_panel()
            return

        row_data = self.main_table_model.row_data(selected_rows[0].row())
        if not row_data:
            self._reset_character_stats_panel()
            return

        self.update_character_stats_panel(row_data["name"])

    def update_character_stats_panel(self, char_name: str) -> None:
        """Update character stats panel."""
        stats = self._calculate_character_project_stats(char_name)
        self.lbl_character_stats_name.setText(char_name)
        self.lbl_character_stats_totals.setText(
            tr("stats.totals", rings=stats["rings"], words=stats["words"])
        )

        if not stats["episodes"]:
            self.txt_character_stats_episodes.setPlainText("Нет в сериях")
            return

        lines = [
            f"Серия {item['episode']}: {item['rings']} колец, {item['words']} слов"
            for item in stats["episodes"]
        ]
        self.txt_character_stats_episodes.setPlainText("\n".join(lines))

    def _calculate_character_project_stats(
        self,
        char_name: str
    ) -> Dict[str, Any]:
        """Calculate character project stats."""
        result: Dict[str, Any] = {
            "rings": 0,
            "words": 0,
            "episodes": []
        }
        export_service = ExportService(self.data)

        for ep in sorted(
            self.data.get("episodes", {}).keys(),
            key=natural_sort_key
        ):
            lines = self.get_episode_lines(str(ep))
            if not lines:
                continue

            processed = export_service.process_merge_logic(
                lines,
                self.data.get("replica_merge_config", {})
            )
            ep_rings = 0
            ep_words = 0

            for line in processed:
                if line.get("char") != char_name:
                    continue
                ep_rings += 1
                ep_words += len(line.get("text", "").split())

            if ep_rings:
                result["episodes"].append({
                    "episode": str(ep),
                    "rings": ep_rings,
                    "words": ep_words
                })
                result["rings"] += ep_rings
                result["words"] += ep_words

        return result


    def save_project(self) -> bool:
        """Save project."""
        if not self.project_controller:
            return False
        
        if self.project_controller.get_current_project_path():
            result = self.project_controller.save_project()
            if result:
                self.current_project_path = self.project_controller.get_current_project_path()
                self._remember_recent_project(self.current_project_path)
                self.update_window_title()
                self._update_new_project_button()
            return result
        return self.save_project_as()

    def save_project_as(self) -> bool:
        """Save project as."""
        if not self.project_controller:
            return False
        
        path, _ = QFileDialog.getSaveFileName(
            self, "Сохранить", "", "*.json"
        )
        if path:
            result = self.project_controller.save_project_as(path)
            if result:
                self.current_project_path = self.project_controller.get_current_project_path()
                self._remember_recent_project(self.current_project_path)
                self.update_window_title()
                self._update_new_project_button()
            return result
        return False

    def load_project_dialog(self) -> None:
        """Load project dialog."""
        if not self.project_controller:
            return
        
        if self.project_controller.maybe_save(self):
            path, _ = QFileDialog.getOpenFileName(
                self, "Открыть", "", "*.json"
            )
            if path:
                self._load_from_path(path)

    def _remember_recent_project(self, path: Optional[str]) -> None:
        """Store a project path in the recent-project list."""
        if not path:
            return
        self.global_settings_service.add_recent_project(path)
        self.global_settings["recent_projects"] = (
            self.global_settings_service.get_recent_projects()
        )
        self.global_settings_service.save_settings(self.global_settings)
        self._update_recent_projects_combo()

    def _update_recent_projects_combo(self) -> None:
        """Refresh the recent-project combo box."""
        if not hasattr(self, "recent_projects_combo"):
            return

        combo = self.recent_projects_combo
        combo.blockSignals(True)
        combo.clear()
        combo.addItem(tr("main.recent"), None)

        recent = self.global_settings_service.get_recent_projects()
        existing = [path for path in recent if os.path.exists(path)]

        if not existing:
            combo.addItem(translate_source("Нет недавних проектов"), None)
            combo.setCurrentIndex(0)
            combo.blockSignals(False)
            return

        for path in existing:
            label = os.path.basename(path) or path
            combo.addItem(label, path)
            combo.setItemData(combo.count() - 1, path, Qt.ToolTipRole)

        combo.insertSeparator(combo.count())
        combo.addItem(translate_source("Очистить список"), "__clear__")
        combo.setCurrentIndex(0)
        combo.blockSignals(False)

    def _on_recent_project_activated(self, index: int) -> None:
        """Handle choosing an item from the recent-project combo."""
        if not hasattr(self, "recent_projects_combo"):
            return

        action = self.recent_projects_combo.itemData(index)
        self.recent_projects_combo.setCurrentIndex(0)
        if action == "__clear__":
            self.clear_recent_projects()
        elif action:
            self.load_recent_project(str(action))

    def clear_recent_projects(self) -> None:
        """Clear recent projects."""
        self.global_settings_service.clear_recent_projects()
        self.global_settings["recent_projects"] = []
        self.global_settings_service.save_settings(self.global_settings)
        self._update_recent_projects_combo()

    def load_recent_project(self, path: str) -> None:
        """Load a project from the recent-project list."""
        if not self.project_controller:
            return
        if not os.path.exists(path):
            QMessageBox.warning(
                self,
                "Проект не найден",
                f"Файл больше не существует:\n{path}"
            )
            self._update_recent_projects_combo()
            return
        if self.project_controller.maybe_save(self):
            self._load_from_path(path)

    def _load_from_path(self, path: str) -> None:
        """Load from path."""
        if not self.project_controller:
            return
        
        try:
            data = self.project_controller.load_project(path)
            if not data:
                return
            
            self.current_project_path = self.project_controller.get_current_project_path()
            self._remember_recent_project(self.current_project_path)
            self._update_new_project_button()

            if self.actor_controller:
                self.actor_controller.data_ref = self.data

            logger.info(f"Project loaded from {path}")
            logger.info(f"Actors count: {len(self.data.get('actors', {}))}")
            logger.info(f"Global map count: {len(self.data.get('global_map', {}))}")

            self.data["loaded_episodes"] = {}
            self.current_ep_stats = []
            self.episode_service.clear_cache()

            self._sync_project_actors_with_global_base()
            self.refresh_actor_list()
            self.update_ep_list()
            self._sync_export_format_controls_from_config()

        except Exception as e:
            log_exception(logger, "Load failed", e)
            QMessageBox.critical(
                self, "Ошибка", f"Не удалось загрузить проект: {e}"
            )
            return

        self.undo_stack.clear()

        self._update_project_folder_button()

        self._scan_project_folder()
        self._link_existing_working_texts()
        self._prompt_working_text_migration()

    def _update_project_folder_button(self) -> None:
        """Update project folder button."""
        if not hasattr(self, "btn_folder"):
            return
        folder = self.project_folder_service.get_project_folder(self.data)
        if folder:
            folder_name = os.path.basename(folder)
            self.btn_folder.setText(tr("main.folder.linked"))
            self.btn_folder.setToolTip(
                tr("main.folder.tooltip", name=folder_name, path=folder)
            )
        else:
            self.btn_folder.setText(tr("main.folder"))
            self.btn_folder.setToolTip(tr("main.folder.set.tooltip"))

    def _scan_project_folder(self) -> None:
        """Scan project folder."""
        folder = self.project_folder_service.get_project_folder(self.data)
        if folder:
            ass_count, video_count, text_count = (
                self.project_folder_service.scan_and_link_files(self.data, folder)
            )
            if ass_count > 0 or video_count > 0 or text_count > 0:
                self.update_ep_list()
                QMessageBox.information(
                    self,
                    "Папка проекта",
                    f"Обновлены пути:\n"
                    f"• Субтитры: {ass_count}\n"
                    f"• Видео: {video_count}\n"
                    f"• Рабочие тексты: {text_count}"
                )

    def _episode_text_exists(self, ep: str) -> bool:
        """Episode text exists."""
        text_path = self.data.get("episode_texts", {}).get(str(ep))
        return bool(text_path and os.path.exists(text_path))

    def _link_existing_working_texts(self) -> int:
        """Link already generated working texts before migration prompt."""
        found = self.script_text_service.find_existing_episode_texts(
            self.data,
            self.current_project_path
        )
        linked_count = 0
        episode_texts = self.data.setdefault("episode_texts", {})

        for ep_num, text_path in found.items():
            current_path = episode_texts.get(str(ep_num))
            if current_path == text_path and os.path.exists(current_path):
                continue
            episode_texts[str(ep_num)] = text_path
            linked_count += 1

        if linked_count:
            self.update_ep_list()
            self.set_dirty(True)
            logger.info(f"Linked {linked_count} existing working text files")

        return linked_count

    def _episodes_needing_working_texts(self) -> List[str]:
        """Episodes needing working texts."""
        self._link_existing_working_texts()
        episodes = self.data.get("episodes", {})
        return [
            str(ep)
            for ep, path in episodes.items()
            if (
                not self._episode_text_exists(str(ep)) and
                self._is_text_source_path(path)
            )
        ]

    def _is_subtitle_source_path(self, path: str) -> bool:
        """Is subtitle source path."""
        return os.path.splitext(path or "")[1].lower() in {'.ass', '.srt'}

    def _is_text_source_path(self, path: str) -> bool:
        """Return whether a path can generate a working text."""
        return os.path.splitext(path or "")[1].lower() in {'.ass', '.srt', '.docx'}

    def _prompt_working_text_migration(self) -> None:
        """Tell the user that old projects need working texts."""
        missing_episodes = self._episodes_needing_working_texts()
        if not missing_episodes:
            return

        QMessageBox.information(
            self,
            "Рабочие тексты",
            "Этот проект использует старый формат текстов.\n\n"
            "В новой версии редактирование реплик выполняется через рабочие JSON. "
            "Откройте «Файлы проекта» и создайте рабочие тексты для нужных серий. "
            "Там же можно создать их массово для всех найденных источников."
        )

    def create_missing_working_texts(
        self,
        episodes: Optional[List[str]] = None
    ) -> Tuple[int, int]:
        """Create missing working texts."""
        target_episodes = episodes or self._episodes_needing_working_texts()
        created_count = 0
        skipped_count = 0

        for ep in target_episodes:
            path = self.data.get("episodes", {}).get(str(ep), "")
            if (
                not path or
                not self._is_text_source_path(path) or
                not os.path.exists(path)
            ):
                skipped_count += 1
                continue

            if self._build_working_text_from_source(str(ep), path):
                created_count += 1
            else:
                skipped_count += 1

        if created_count:
            self.update_ep_list()
            self.set_dirty(True)

        QMessageBox.information(
            self,
            "Рабочие тексты",
            f"Создано рабочих текстов: {created_count}\n"
            f"Пропущено: {skipped_count}"
        )
        return created_count, skipped_count

    def ensure_working_text_for_episode(
        self,
        ep: str,
        action_label: str = "выполнить это действие"
    ) -> bool:
        """Ensure an episode has a working JSON before editable actions."""
        ep = str(ep)
        if self._episode_text_exists(ep):
            return True

        source_path = self.data.get("episodes", {}).get(ep, "")
        if not source_path or not self._is_text_source_path(source_path):
            QMessageBox.warning(
                self,
                "Рабочий текст не найден",
                f"Чтобы {action_label}, нужно создать рабочий JSON для этой серии.\n\n"
                "Откройте «Файлы проекта», привяжите исходный ASS/SRT/DOCX и создайте рабочий текст."
            )
            return False

        reply = QMessageBox.question(
            self,
            "Рабочий текст не найден",
            f"Чтобы {action_label}, нужно создать рабочий JSON для этой серии.\n\n"
            "Создать его сейчас?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes
        )
        if reply != QMessageBox.Yes:
            return False

        return self.regenerate_episode_text(ep, source_path, show_result=False)

    def set_project_folder_dialog(self) -> None:
        """Set project folder dialog."""
        current_folder = self.project_folder_service.get_project_folder(self.data)
        
        folder = QFileDialog.getExistingDirectory(
            self,
            "Выберите папку проекта",
            current_folder or ""
        )
        
        if folder:
            command = SetProjectFolderCommand(self.data, folder)
            self.undo_stack.push(command)
            
            self.project_folder_service.set_project_folder(self.data, folder)
            
            # Update UI
            self._update_project_folder_button()
            self._scan_project_folder()
            self.set_dirty()

    def clear_project_folder(self) -> None:
        """Clear the project folder."""
        current_folder = self.project_folder_service.get_project_folder(self.data)
        
        if not current_folder:
            return

        reply = QMessageBox.question(
            self,
            "Отвязать папку",
            "Отвязать папку проекта?\n\nФайлы останутся в проекте, но автоматический поиск будет отключен.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            command = SetProjectFolderCommand(self.data, None)
            self.undo_stack.push(command)
            
            self.project_folder_service.clear_project_folder(self.data)
            
            # Update UI
            self._update_project_folder_button()
            self.set_dirty()

    def _on_undo_stack_change(self) -> None:
        """Handle undo stack change."""
        self.btn_undo.setEnabled(self.undo_stack.can_undo())
        self.btn_redo.setEnabled(self.undo_stack.can_redo())

    def undo(self) -> None:
        """Undo."""
        if self.undo_stack.undo():
            self.refresh_actor_list()
            self.refresh_main_table()
            self.set_dirty()

    def redo(self) -> None:
        """Redo."""
        if self.undo_stack.redo():
            self.refresh_actor_list()
            self.refresh_main_table()
            self.set_dirty()

    
    def on_header_clicked(self, index: int) -> None:
        """Handle header click."""
        if index > 3:
            return
        if self.sort_col == index:
            self.sort_desc = not self.sort_desc
        else:
            self.sort_col = index
            self.sort_desc = True
        self.refresh_main_table()

    def _is_global_actor_mode(self) -> bool:
        """Return whether the actor panel shows the global actor base."""
        return (
            hasattr(self, "actor_base_mode") and
            self.actor_base_mode.currentData() == "global"
        )

    def _on_actor_base_mode_changed(self) -> None:
        """Handle actor panel mode changes."""
        is_global = self._is_global_actor_mode()
        self.actor_table.setEditTriggers(
            QAbstractItemView.DoubleClicked | QAbstractItemView.EditKeyPressed
        )
        self._update_actor_base_buttons()

        if is_global:
            self.refresh_global_actor_table()
        else:
            self.refresh_actor_list()

    def _update_actor_base_buttons(self) -> None:
        """Update actor panel buttons for the current actor-base mode."""
        if not hasattr(self, "btn_add_actor"):
            return

        if self._is_global_actor_mode():
            self.btn_add_actor.setText(tr("actor.add"))
            self.btn_add_actor.setToolTip(tr("actor.add.global.tooltip"))
            self.btn_delete_actor.setText(tr("actor.delete"))
            self.btn_delete_actor.setToolTip(tr("actor.delete.global.tooltip"))
            self.btn_add_project_actors_to_global.setText(tr("actor.add.to.project"))
            self.btn_add_project_actors_to_global.setToolTip(
                tr("actor.add.to.project.tooltip")
            )
        else:
            self.btn_add_actor.setText(tr("actor.add"))
            self.btn_add_actor.setToolTip(tr("actor.add.project.tooltip"))
            self.btn_delete_actor.setText(tr("actor.delete"))
            self.btn_delete_actor.setToolTip(tr("actor.delete.project.tooltip"))
            self.btn_add_project_actors_to_global.setText(tr("actor.add.to.global"))
            self.btn_add_project_actors_to_global.setToolTip(
                tr("actor.add.to.global.tooltip")
            )

        self.btn_add_actor.setEnabled(True)
        self.btn_delete_actor.setEnabled(True)
        self.btn_add_project_actors_to_global.setEnabled(True)

    def refresh_global_actor_table(self) -> None:
        """Refresh the global actor-base view."""
        self.actor_table.blockSignals(True)
        self.actor_table.setSortingEnabled(False)
        self.actor_table.setColumnCount(3)
        self.actor_table.setRowCount(0)
        self.actor_table.setHorizontalHeaderLabels([
            tr("actor.table.actor"),
            tr("actor.table.status"),
            tr("actor.table.gender"),
        ])
        actor_base = self.global_settings_service.get_global_actor_base()
        project_actor_names = {
            actor.get("name", "").strip().casefold()
            for actor in self.data.get("actors", {}).values()
            if isinstance(actor, dict)
        }

        for actor_id, info in sorted(
            actor_base.items(),
            key=lambda item: item[1].get("name", "").lower()
        ):
            row = self.actor_table.rowCount()
            self.actor_table.insertRow(row)

            item = QTableWidgetItem(info.get("name", actor_id))
            item.setData(Qt.UserRole, actor_id)
            item.setFlags(item.flags() | Qt.ItemIsEditable)
            self.actor_table.setItem(row, 0, item)

            in_project = (
                info.get("name", "").strip().casefold()
                in project_actor_names
            )
            roles_item = QTableWidgetItem("В проекте" if in_project else "")
            roles_item.setFlags(roles_item.flags() & ~Qt.ItemIsEditable)
            self.actor_table.setItem(row, 1, roles_item)

            gender_item = QTableWidgetItem(info.get("gender", ""))
            gender_item.setData(Qt.UserRole, actor_id)
            gender_item.setToolTip("Введите М или Ж")
            gender_item.setFlags(gender_item.flags() | Qt.ItemIsEditable)
            self.actor_table.setItem(row, 2, gender_item)

        self.actor_table.setSortingEnabled(True)
        self.actor_table.blockSignals(False)

    def add_actor_button_clicked(self) -> None:
        """Handle the add-actor button for the selected actor-base mode."""
        if self._is_global_actor_mode():
            self.add_global_actor_dialog()
            return
        self.add_actor_dialog()

    def delete_actor_button_clicked(self) -> None:
        """Handle the delete-actor button for the selected actor-base mode."""
        if self._is_global_actor_mode():
            self.delete_global_actor_dialog()
            return
        self.delete_actor_dialog()

    def actor_transfer_button_clicked(self) -> None:
        """Move actors between project and global bases."""
        if self._is_global_actor_mode():
            self.add_selected_global_actor_to_project()
            return
        self.add_project_actors_to_global_dialog()

    def add_global_actor_dialog(self) -> None:
        """Add an actor directly to the global actor base."""
        name, ok = QInputDialog.getText(self, "Новый актёр", "Имя:")
        if not ok or not name.strip():
            return

        gender, gender_ok = QInputDialog.getItem(
            self,
            "Пол актёра",
            "Пол:",
            ["", "М", "Ж"],
            0,
            False
        )
        if not gender_ok:
            return

        existing_id = self.global_settings_service.find_global_actor_by_name(name)
        if existing_id:
            QMessageBox.information(
                self,
                "Актёр уже есть",
                f"{name.strip()} уже есть в глобальной базе."
            )
            return

        self.global_settings_service.add_global_actor(
            name,
            gender=gender
        )
        self.global_settings["global_actor_base"] = (
            self.global_settings_service.get_global_actor_base()
        )
        self.global_settings_service.save_settings(self.global_settings)
        self.refresh_global_actor_table()

    def delete_global_actor_dialog(self) -> None:
        """Delete the selected actor from the global actor base."""
        actor_id, actor_name = self._selected_global_actor()
        if not actor_id:
            QMessageBox.information(
                self,
                "Инфо",
                "Выберите актёра для удаления."
            )
            return

        reply = QMessageBox.question(
            self,
            "Удалить актёра?",
            f"Удалить {actor_name} из глобальной базы?\n\n"
            "Это не удалит актёра из текущего проекта.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return

        if self.global_settings_service.remove_global_actor(actor_id):
            self.global_settings["global_actor_base"] = (
                self.global_settings_service.get_global_actor_base()
            )
            self.global_settings_service.save_settings(self.global_settings)
            self.refresh_global_actor_table()

    def add_selected_global_actor_to_project(self) -> None:
        """Add the selected global actor to the current project."""
        actor_id, actor_name = self._selected_global_actor()
        if not actor_id:
            QMessageBox.information(
                self,
                "Инфо",
                "Выберите актёра для добавления в проект."
            )
            return

        actor = self.global_settings_service.get_global_actor_base().get(actor_id)
        if not actor:
            return

        self._add_actor_to_project(
            actor.get("name", actor_name),
            self.actor_service._get_next_color(self.data.get("actors", {})),
            actor.get("gender", "")
        )
        if self._is_global_actor_mode():
            self.refresh_global_actor_table()

    def _selected_global_actor(self) -> Tuple[Optional[str], str]:
        """Return selected global actor id and name."""
        selected_rows = self.actor_table.selectionModel().selectedRows()
        if not selected_rows:
            return None, ""

        row = selected_rows[0].row()
        item = self.actor_table.item(row, 0)
        if not item:
            return None, ""
        return item.data(Qt.UserRole), item.text()

    def _sync_project_actors_with_global_base(self) -> int:
        """Sync project actor records with global actor records by name."""
        actors = self.data.get("actors", {})
        if not isinstance(actors, dict) or not actors:
            return 0

        actor_base = self.global_settings_service.get_global_actor_base()
        if not actor_base:
            return 0

        global_by_name = {
            self._actor_name_key(actor.get("name", "")): (actor_id, actor)
            for actor_id, actor in actor_base.items()
            if isinstance(actor, dict) and self._actor_name_key(actor.get("name", ""))
        }

        changed = 0
        for project_actor_id, project_actor in list(actors.items()):
            if not isinstance(project_actor, dict):
                continue

            match = global_by_name.get(
                self._actor_name_key(project_actor.get("name", ""))
            )
            if not match:
                continue

            global_actor_id, global_actor = match
            if self._merge_project_actor_with_global(
                project_actor_id,
                global_actor_id,
                global_actor
            ):
                changed += 1

        if changed:
            self.set_dirty(True)
            logger.info(
                f"Synced {changed} project actors with the global actor base"
            )

        return changed

    def _actor_name_key(self, name: str) -> str:
        """Return a stable comparison key for actor names."""
        return " ".join(str(name or "").split()).casefold()

    def _merge_project_actor_with_global(
        self,
        project_actor_id: str,
        global_actor_id: str,
        global_actor: Dict[str, Any]
    ) -> bool:
        """Merge one project actor with a global actor record."""
        actors = self.data.setdefault("actors", {})
        old_actor = actors.get(project_actor_id)
        if not isinstance(old_actor, dict):
            return False

        merged_actor = old_actor.copy()
        merged_actor.update({
            "name": global_actor.get("name", old_actor.get("name", "")),
            "gender": global_actor.get("gender", old_actor.get("gender", "")),
        })

        changed = False
        if project_actor_id != global_actor_id:
            if global_actor_id in actors and isinstance(actors[global_actor_id], dict):
                target_actor = actors[global_actor_id].copy()
                target_actor.update(merged_actor)
                actors[global_actor_id] = target_actor
            else:
                actors[global_actor_id] = merged_actor
            del actors[project_actor_id]
            self._replace_project_actor_references(
                project_actor_id,
                global_actor_id
            )
            changed = True
        elif actors.get(project_actor_id) != merged_actor:
            actors[project_actor_id] = merged_actor
            changed = True

        return changed

    def _replace_project_actor_references(
        self,
        old_actor_id: str,
        new_actor_id: str
    ) -> None:
        """Replace actor ids in project assignment and filter data."""
        for mapping_name in ("global_map",):
            mapping = self.data.get(mapping_name, {})
            if not isinstance(mapping, dict):
                continue
            for char_name, actor_id in list(mapping.items()):
                if actor_id == old_actor_id:
                    mapping[char_name] = new_actor_id

        episode_maps = self.data.get("episode_actor_map", {})
        if isinstance(episode_maps, dict):
            for episode_map in episode_maps.values():
                if not isinstance(episode_map, dict):
                    continue
                for char_name, actor_id in list(episode_map.items()):
                    if actor_id == old_actor_id:
                        episode_map[char_name] = new_actor_id

        export_config = self.data.get("export_config", {})
        if (
            isinstance(export_config, dict) and
            isinstance(export_config.get("highlight_ids_export"), list)
        ):
            export_config["highlight_ids_export"] = (
                self._replace_actor_ids_in_list(
                    export_config.get("highlight_ids_export"),
                    old_actor_id,
                    new_actor_id
                )
            )

    def _replace_actor_ids_in_list(
        self,
        values: Any,
        old_actor_id: str,
        new_actor_id: str
    ) -> Any:
        """Replace an actor id in a list while preserving order."""
        if not isinstance(values, list):
            return values

        result = []
        for value in values:
            next_value = new_actor_id if value == old_actor_id else value
            if next_value not in result:
                result.append(next_value)
        return result

    def add_project_actors_to_global_dialog(self) -> None:
        """Batch-add project actors to the global actor base."""
        project_actors = self.data.get("actors", {})
        if not project_actors:
            QMessageBox.information(
                self,
                "Глобальная база",
                "В проекте пока нет актёров."
            )
            return

        global_names = {
            actor.get("name", "").strip().casefold()
            for actor in self.global_settings_service.get_global_actor_base().values()
            if isinstance(actor, dict)
        }

        dialog = QDialog(self)
        dialog.setWindowTitle("Добавить актёров в глобальную базу")
        layout = QVBoxLayout(dialog)
        layout.addWidget(QLabel("Выберите актёров проекта для добавления:"))

        actor_list = QListWidget()
        available_count = 0
        for actor_id, actor in sorted(
            project_actors.items(),
            key=lambda item: item[1].get("name", "").lower()
        ):
            name = actor.get("name", actor_id)
            exists = name.strip().casefold() in global_names
            item = QListWidgetItem(
                f"{name} — уже есть в глобальной базе" if exists else name
            )
            item.setData(Qt.UserRole, actor_id)
            if exists:
                item.setFlags(item.flags() & ~Qt.ItemIsEnabled)
                item.setCheckState(Qt.Unchecked)
            else:
                item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
                item.setCheckState(Qt.Checked)
                available_count += 1
            actor_list.addItem(item)

        layout.addWidget(actor_list)

        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        buttons.button(QDialogButtonBox.Ok).setText("Добавить")
        buttons.button(QDialogButtonBox.Ok).setEnabled(available_count > 0)
        buttons.button(QDialogButtonBox.Cancel).setText("Отмена")
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)

        if available_count == 0:
            layout.addWidget(QLabel("Все актёры проекта уже есть в глобальной базе."))

        if dialog.exec() != QDialog.Accepted:
            return

        selected_ids = []
        for row in range(actor_list.count()):
            item = actor_list.item(row)
            if item.flags() & Qt.ItemIsEnabled and item.checkState() == Qt.Checked:
                selected_ids.append(item.data(Qt.UserRole))

        if not selected_ids:
            QMessageBox.information(
                self,
                "Глобальная база",
                "Не выбрано ни одного актёра."
            )
            return

        stats = self.global_settings_service.add_project_actors_to_global(
            project_actors,
            selected_ids
        )
        self.global_settings["global_actor_base"] = (
            self.global_settings_service.get_global_actor_base()
        )
        self.global_settings_service.save_settings(self.global_settings)

        if self._is_global_actor_mode():
            self.refresh_global_actor_table()

        QMessageBox.information(
            self,
            "Готово",
            "Актёры добавлены в глобальную базу.\n\n"
            f"Добавлено: {stats.get('added', 0)}\n"
            f"Уже было: {stats.get('skipped_existing', 0)}"
        )
    
    def add_actor_dialog(self) -> None:
        """Add actor dialog."""
        if not self.actor_controller:
            return

        actor_base = self.global_settings_service.get_global_actor_base()
        if actor_base:
            options = ["Новый актёр..."]
            sorted_global = sorted(
                actor_base.items(),
                key=lambda item: item[1].get("name", "").lower()
            )
            options.extend(
                info.get("name", actor_id)
                for actor_id, info in sorted_global
            )
            choice, ok = QInputDialog.getItem(
                self,
                "Добавить актёра",
                "Выберите актёра из глобальной базы или создайте нового:",
                options,
                0,
                False
            )
            if not ok:
                return
            if choice != "Новый актёр...":
                for _global_id, info in sorted_global:
                    if info.get("name") == choice:
                        self._add_actor_to_project(
                            info.get("name", choice),
                            self.actor_service._get_next_color(
                                self.data.get("actors", {})
                            ),
                            info.get("gender", "")
                        )
                        return

        name, ok = QInputDialog.getText(self, "Новый актер", "Имя:")
        if ok and name:
            dialog = CustomColorDialog(self)
            if dialog.exec():
                gender, gender_ok = QInputDialog.getItem(
                    self,
                    "Пол актёра",
                    "Пол:",
                    ["", "М", "Ж"],
                    0,
                    False
                )
                if gender_ok:
                    self._add_actor_to_project(
                        name,
                        dialog.selected_color,
                        gender
                    )

    def _add_actor_to_project(
        self,
        name: str,
        color: str,
        gender: str = ""
    ) -> None:
        """Add an actor to the current project and remember them globally."""
        actor_name = name.strip()
        if not actor_name:
            return

        for actor in self.data.get("actors", {}).values():
            if actor.get("name", "").strip().casefold() == actor_name.casefold():
                QMessageBox.information(
                    self,
                    "Актёр уже в проекте",
                    f"{actor_name} уже добавлен в этот проект."
                )
                return

        actor_id = str(datetime.now().timestamp())
        command = AddActorCommand(
            self.data["actors"],
            actor_id,
            actor_name,
            color,
            gender
        )
        self.undo_stack.push(command)
        self.global_settings_service.add_global_actor(actor_name, gender=gender)
        self.global_settings["global_actor_base"] = (
            self.global_settings_service.get_global_actor_base()
        )
        self.global_settings_service.save_settings(self.global_settings)
        self.actor_controller.refresh()
        self.refresh_main_table()
        self.set_dirty()

    def on_actor_renamed(self, item: QTableWidgetItem) -> None:
        """Handle actor renamed."""
        if self._is_global_actor_mode():
            self._update_global_actor_from_table_item(item)
            return

        if item.column() != 0:
            return

        if self.actor_controller:
            aid: Optional[str] = item.data(Qt.UserRole)
            if aid:
                old_name = self.data.get("actors", {}).get(aid, {}).get("name", "")
                new_name = item.text().strip()
                if not new_name:
                    self.actor_table.blockSignals(True)
                    item.setText(old_name)
                    self.actor_table.blockSignals(False)
                    return

                if new_name == old_name:
                    return

                command = RenameActorCommand(
                    self.data["actors"],
                    aid,
                    new_name
                )
                self.undo_stack.push(command)
                self.actor_controller.refresh()
                self.refresh_main_table()
                self._refresh_open_windows(self.ep_combo.currentData())
                self.set_dirty()

    def _update_global_actor_from_table_item(self, item: QTableWidgetItem) -> None:
        """Update global actor-base data from an edited table item."""
        if item.column() not in (0, 2):
            return

        actor_id = item.data(Qt.UserRole)
        actor_base = self.global_settings_service.get_global_actor_base()
        if actor_id not in actor_base:
            return

        if item.column() == 0:
            new_name = item.text().strip()
            if not new_name:
                self.actor_table.blockSignals(True)
                item.setText(actor_base[actor_id].get("name", ""))
                self.actor_table.blockSignals(False)
                return
            actor_base[actor_id]["name"] = new_name
        else:
            gender = self.global_settings_service._normalize_actor_gender(
                item.text()
            )
            actor_base[actor_id]["gender"] = gender
            if item.text() != gender:
                self.actor_table.blockSignals(True)
                item.setText(gender)
                self.actor_table.blockSignals(False)

        self.global_settings_service.set_global_actor_base(actor_base)
        self.global_settings["global_actor_base"] = (
            self.global_settings_service.get_global_actor_base()
        )
        self.global_settings_service.save_settings(self.global_settings)
        self.refresh_global_actor_table()

    def on_actor_color_clicked(self, aid: str) -> None:
        """Handle actor color click."""
        if self._is_global_actor_mode():
            return

        if self.actor_controller:
            dialog = CustomColorDialog(self)
            if dialog.exec() and dialog.selected_color:
                command = UpdateActorColorCommand(
                    self.data["actors"],
                    aid,
                    dialog.selected_color
                )
                self.undo_stack.push(command)
                self.actor_controller.refresh()
                self.refresh_main_table()
                self.set_dirty()

    def delete_actor_dialog(self) -> None:
        """Delete actor dialog."""
        if not self.actor_controller:
            return

        selected_rows = self.actor_table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.information(
                self, "Инфо", "Выберите актёра для удаления."
            )
            return

        row = selected_rows[0].row()
        item = self.actor_table.item(row, 0)
        if not item:
            return

        actor_id = item.data(Qt.UserRole)
        actor_name = item.text()

        roles = self.actor_controller.get_actor_roles(actor_id)
        
        warning_message = f"Вы уверены, что хотите удалить актёра \"{actor_name}\"?"
        if roles:
            warning_message += (
                f"\n\n⚠️ У актёра есть роли ({len(roles)}):\n"
                f"{', '.join(roles[:5])}"
                f"{('...' if len(roles) > 5 else '')}"
                "\n\nВсе назначения будут удалены."
            )

        reply = QMessageBox.question(
            self,
            "Удаление актёра",
            warning_message,
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            command = DeleteActorCommand(
                self.data["actors"],
                self.data["global_map"],
                actor_id,
                [
                    mapping for mapping in
                    self.data.get("episode_actor_map", {}).values()
                    if isinstance(mapping, dict)
                ]
            )
            self.undo_stack.push(command)
            self.actor_controller.refresh()
            self.refresh_main_table()
            self.set_dirty()

    def set_episode_video(self) -> None:
        """Set episode video."""
        ep: Optional[str] = self.ep_combo.currentData()
        if ep:
            path: str
            path, _ = QFileDialog.getOpenFileName(
                self,
                "Видео",
                "",
                "Video (*.mp4 *.mkv *.avi *.mov)"
            )
            if path:
                if "video_paths" not in self.data:
                    self.data["video_paths"] = {}
                self.data["video_paths"][ep] = path
                
                fps = get_video_fps(path)
                self.data["replica_merge_config"]["fps"] = fps
                self.episode_service.set_fps(fps)
                
                self.set_dirty()
    
    def change_episode(self) -> None:
        """Change episode."""
        ep: Optional[str] = self.ep_combo.currentData()
        if not ep:
            return

        lines = self.get_episode_lines(ep)
        if lines:
            self._recalculate_episode_stats(lines)
            self._display_episode_lines(lines)
            self.table_stack.setCurrentIndex(0)
            self._update_actor_filter_combo()
            self.refresh_main_table()
            self.update_save_ass_button()
            return

        self.table_stack.setCurrentIndex(1)


    def _display_episode_lines(self, lines: List[Dict[str, Any]]) -> None:
        """Display episode lines."""
        # DOCX-specific handling
        pass

    def _recalculate_episode_stats(self, lines: List[Dict[str, Any]]) -> None:
        """Recalculate episode stats."""
        from collections import defaultdict

        char_data: Dict[str, Dict[str, Any]] = defaultdict(
            lambda: {"lines": 0, "raw": []}
        )

        for line in lines:
            char = line.get('char', '')
            if char:
                char_data[char]["lines"] += 1
                char_data[char]["raw"].append(line)

        merge_gap_seconds = self.episode_service.merge_gap / self.episode_service.fps

        stats = []
        for char, info in char_data.items():
            rings = 1
            words = 0
            char_lines = info["raw"]

            if char_lines:
                words = len(char_lines[0]['text'].split())

                for i in range(1, len(char_lines)):
                    if char_lines[i]['s'] - char_lines[i-1]['e'] >= merge_gap_seconds:
                        rings += 1
                    words += len(char_lines[i]['text'].split())

            stats.append({
                "name": char,
                "lines": info["lines"],
                "rings": rings,
                "words": words
            })

        self.current_ep_stats = stats

    def _parse_episode(self, ep: str, path: str) -> List[Dict[str, Any]]:
        """Parse episode."""
        stats: List[Dict[str, Any]]
        lines: List[Dict[str, Any]]
        stats, lines = self.episode_service.parse_ass_file(path)
        self.current_ep_stats = stats
        return lines

    def _create_working_text_for_episode(
        self,
        ep: str,
        path: str,
        lines: List[Dict[str, Any]]
    ) -> None:
        """Create working text for episode."""
        if not lines:
            return

        merge_config = self.data.get("replica_merge_config", {})
        if os.path.splitext(path or "")[1].lower() == '.docx':
            merge_config = {**merge_config, "merge": False}

        self.script_text_service.create_episode_text(
            self.data,
            ep,
            path,
            lines,
            merge_config,
            self.current_project_path
        )

    def _convert_imported_lines_for_cache(
        self,
        lines: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Convert imported lines for cache."""
        episode_lines = []
        for idx, line_data in enumerate(lines):
            episode_lines.append({
                'id': idx,
                's': line_data['s'],
                'e': line_data['e'],
                'char': line_data['char'],
                'text': line_data['text'],
                's_raw': line_data.get('s_raw', ''),
                'e_raw': line_data.get('e_raw', ''),
            })
        return episode_lines

    def import_ass(self, paths: Optional[List[str]] = None) -> None:
        """Import ass."""
        if not paths:
            paths, _ = QFileDialog.getOpenFileNames(
                self, "ASS", "", "*.ass"
            )

        if paths:
            for path in paths:
                self._import_single_file(path)

            self.update_ep_list()

    def import_srt(self, paths: Optional[List[str]] = None) -> None:
        """Import srt."""
        if not paths:
            paths, _ = QFileDialog.getOpenFileNames(
                self, "SRT", "", "*.srt"
            )

        if paths:
            for path in paths:
                self._import_single_file(path)

            self.update_ep_list()

    def _import_single_file(self, path: str) -> None:
        """Import single file."""
        numbers: List[str] = re.findall(r'\d+', os.path.basename(path))
        num: str = " ".join(numbers) or "1"

        name: str
        ok: bool
        name, ok = QInputDialog.getText(
            self,
            "Ep",
            f"Ep для {os.path.basename(path)}:",
            text=num
        )

        if ok and name:
            command = AddEpisodeCommand(
                self.data["episodes"],
                name,
                path
            )
            self.undo_stack.push(command)

            ext = os.path.splitext(path)[1].lower()
            if ext == '.srt':
                lines = self._parse_srt_episode(name, path)
            else:
                lines = self._parse_episode(name, path)

            self._create_working_text_for_episode(name, path, lines)

            self.set_dirty()

    def import_files(self, paths: Optional[List[str]] = None) -> None:
        """Import files."""
        if not paths:
            paths, _ = QFileDialog.getOpenFileNames(
                self,
                "Импорт субтитров",
                "",
                "Поддерживаемые форматы (*.ass *.srt *.docx);;Все файлы (*)"
            )

        if not paths:
            return

        for path in paths:
            ext = os.path.splitext(path)[1].lower()

            if ext in {'.ass', '.srt'}:
                self._import_single_file(path)
            elif ext == '.docx':
                # DOCX-specific handling
                self.import_docx_with_dialog(path)

        self.update_ep_list()

    def import_docx_with_dialog(self, file_path: str) -> None:
        """Import docx with dialog."""
        from ui.dialogs import DocxImportDialog
        from core.commands import AddEpisodeCommand
        import re
        import os

        dialog = DocxImportDialog(self, file_path)
        if dialog.exec() != QDialog.Accepted:
            return

        result = dialog.get_result()
        if not result:
            return

        numbers: List[str] = re.findall(r'\d+', os.path.basename(file_path))
        num: str = " ".join(numbers) or "1"

        name: str
        ok: bool
        name, ok = QInputDialog.getText(
            self,
            "Ep",
            f"Номер эпизода для импорта:",
            text=num
        )

        if not ok or not name:
            return

        lines = result['lines']
        episode_lines = self._convert_imported_lines_for_cache(lines)

        command = AddEpisodeCommand(
            self.data["episodes"],
            name,
            file_path
        )
        self.undo_stack.push(command)

        if "loaded_episodes" not in self.data:
            self.data["loaded_episodes"] = {}
        self.data["loaded_episodes"][name] = episode_lines

        self.episode_service._loaded_episodes[name] = episode_lines

        self._create_working_text_for_episode(name, file_path, episode_lines)
        working_lines = self.script_text_service.load_episode_lines(
            self.data,
            name
        )
        if working_lines:
            self.data["loaded_episodes"][name] = working_lines

        self.current_ep_stats = result['stats']

        # Update UI
        self.update_ep_list()
        self.set_dirty()

        QMessageBox.information(
            self, "Импорт завершён",
            f"Импортировано {len(lines)} реплик из DOCX файла." +
            (f"\n({result.get('tables_count', 1)} таблиц(ы))" if result.get('tables_count', 1) > 1 else "")
        )

    def _parse_srt_episode(self, ep: str, path: str) -> List[Dict[str, Any]]:
        """Parse srt episode."""
        stats: List[Dict[str, Any]]
        lines: List[Dict[str, Any]]
        stats, lines = self.episode_service.parse_srt_file(path)
        self.current_ep_stats = stats
        return lines

    def import_docx(self, paths: Optional[List[str]] = None) -> None:
        """Import docx."""
        from ui.dialogs import DocxImportDialog
        from core.commands import AddEpisodeCommand
        import re
        import os

        # DOCX-specific handling
        dialog = DocxImportDialog(self)
        if dialog.exec() != QDialog.Accepted:
            return

        result = dialog.get_result()
        if not result:
            return

        numbers: List[str] = re.findall(r'\d+', dialog.file_label.text())
        num: str = " ".join(numbers) or "1"

        name: str
        ok: bool
        name, ok = QInputDialog.getText(
            self,
            "Ep",
            f"Номер эпизода для импорта:",
            text=num
        )

        if not ok or not name:
            return

        lines = result['lines']
        episode_lines = self._convert_imported_lines_for_cache(lines)
        docx_path = (
            result.get('source_path') or
            (
                dialog.file_label.text().replace('📄 ', '')
                if hasattr(dialog, 'file_label')
                else "DOCX Import"
            )
        )

        command = AddEpisodeCommand(
            self.data["episodes"],
            name,
            docx_path
        )
        self.undo_stack.push(command)

        if "loaded_episodes" not in self.data:
            self.data["loaded_episodes"] = {}
        self.data["loaded_episodes"][name] = episode_lines

        self.episode_service._loaded_episodes[name] = episode_lines

        self._create_working_text_for_episode(name, docx_path, episode_lines)
        working_lines = self.script_text_service.load_episode_lines(
            self.data,
            name
        )
        if working_lines:
            self.data["loaded_episodes"][name] = working_lines

        self.current_ep_stats = result['stats']

        # Update UI
        self.update_ep_list()
        self.set_dirty()

        QMessageBox.information(
            self, "Импорт завершён",
            f"Импортировано {len(lines)} реплик из DOCX файла." +
            (f"\n({result.get('tables_count', 1)} таблиц(ы))" if result.get('tables_count', 1) > 1 else "")
        )

    def relink_file(self) -> None:
        """Relink file."""
        ep: Optional[str] = self.ep_combo.currentData()
        path: str
        path, _ = QFileDialog.getOpenFileName(
            self, "Файл", "", "Subtitle Files (*.ass *.srt)"
        )
        if path:
            self.data["episodes"][ep] = path
            self.change_episode()
            self.set_dirty()

    def update_map_value(
        self,
        char_name: str,
        actor_id: Optional[str],
        scope: str
    ) -> None:
        """Update map value."""
        ep = self.ep_combo.currentData()
        target_map = get_assignment_map(self.data, scope, ep)
        stored_aid = (
            LOCAL_UNASSIGNED_ACTOR_ID
            if scope == ASSIGNMENT_SCOPE_EPISODE and actor_id is None
            else actor_id
        )
        command = AssignActorToCharacterCommand(
            target_map,
            char_name,
            stored_aid
        )
        self.undo_stack.push(command)
        self.refresh_actor_list()
        if hasattr(self, "actor_filter_combo") and self.actor_filter_combo.currentData():
            self.refresh_main_table()
        self.set_dirty(True)

    def update_assignment_scope_value(
        self,
        char_name: str,
        scope: str,
        actor_id: Optional[str]
    ) -> None:
        """Update assignment scope value."""
        ep = self.ep_combo.currentData()
        if not ep:
            return

        local_map = get_assignment_map(self.data, ASSIGNMENT_SCOPE_EPISODE, ep)

        if scope == ASSIGNMENT_SCOPE_EPISODE:
            stored_aid = actor_id or LOCAL_UNASSIGNED_ACTOR_ID
            command = AssignActorToCharacterCommand(
                local_map, char_name, stored_aid
            )
        else:
            command = AssignActorToCharacterCommand(local_map, char_name, None)

        self.undo_stack.push(command)

        self._update_main_table_assignment_display(char_name)

        self.refresh_actor_list()
        if hasattr(self, "actor_filter_combo") and self.actor_filter_combo.currentData():
            self.refresh_main_table()
        self.set_dirty(True)

    def _update_main_table_assignment_display(self, char_name: str) -> None:
        """Update main table assignment display."""
        self.main_table_model.update_actor_for_character(char_name)
    
    def refresh_main_table(self) -> None:
        """Refresh main table."""
        query = self.search_edit.text().lower()
        only_unassigned = self.filter_unassigned.isChecked()
        actor_filter_id = (
            self.actor_filter_combo.currentData()
            if hasattr(self, "actor_filter_combo")
            else None
        )
        
        keys = ["name", "lines", "rings", "words"]
        sorted_stats = sorted(
            self.current_ep_stats,
            key=lambda x: x[keys[self.sort_col]],
            reverse=self.sort_desc
        )

        rows: List[Dict[str, Any]] = []
        for stat in sorted_stats:
            if query and query not in stat["name"].lower():
                continue
            
            ep = self.ep_combo.currentData()
            actor_id = get_actor_for_character(self.data, stat["name"], ep)
            is_assigned = actor_id is not None
            if only_unassigned and is_assigned:
                continue
            if actor_filter_id and actor_id != actor_filter_id:
                continue

            scope = get_assignment_scope(self.data, stat["name"], ep)
            rows.append({
                "name": stat["name"],
                "lines": stat["lines"],
                "rings": stat["rings"],
                "words": stat["words"],
                "scope": scope,
                "actor_id": actor_id,
            })

        self.main_table_model.set_rows(rows)

    def _update_actor_filter_combo(self) -> None:
        """Refresh the quick actor filter."""
        if not hasattr(self, "actor_filter_combo"):
            return

        current = self.actor_filter_combo.currentData()
        self.actor_filter_combo.blockSignals(True)
        self.actor_filter_combo.clear()
        self.actor_filter_combo.addItem(tr("common.all"), None)

        episode_actor_ids = self._get_current_episode_actor_ids()
        actors = self.data.get("actors", {})
        for actor_id, info in sorted(
            (
                (actor_id, actors[actor_id])
                for actor_id in episode_actor_ids
                if actor_id in actors
            ),
            key=lambda item: item[1].get("name", "").lower()
        ):
            self.actor_filter_combo.addItem(info.get("name", actor_id), actor_id)

        index = self.actor_filter_combo.findData(current)
        self.actor_filter_combo.setCurrentIndex(index if index >= 0 else 0)
        self.actor_filter_combo.blockSignals(False)

    def _get_current_episode_actor_ids(self) -> Set[str]:
        """Return actor ids that appear in the current episode."""
        ep = self.ep_combo.currentData() if hasattr(self, "ep_combo") else None
        actor_ids: Set[str] = set()
        for stat in self.current_ep_stats:
            actor_id = get_actor_for_character(self.data, stat["name"], ep)
            if actor_id:
                actor_ids.add(actor_id)
        return actor_ids

    def refresh_actor_list(self) -> None:
        """Refresh actor list."""
        self._sync_project_actors_with_global_base()
        if self._is_global_actor_mode():
            self.refresh_global_actor_table()
            self._update_actor_filter_combo()
            return

        logger.info(f"refresh_actor_list: actor_controller={self.actor_controller is not None}, actors={len(self.data.get('actors', {}))}")
        
        if self.actor_controller:
            self.actor_controller.refresh()
        else:
            logger.warning("refresh_actor_list: actor_controller is None, using fallback")
            self.actor_table.blockSignals(True)
            self.actor_table.setSortingEnabled(False)
            self.actor_table.setColumnCount(4)
            self.actor_table.setHorizontalHeaderLabels(
                [
                    tr("actor.table.actor"),
                    tr("actor.table.roles"),
                    tr("actor.table.color"),
                    tr("actor.table.gender"),
                ]
            )
            self.actor_table.setRowCount(0)

            actor_roles: Dict[str, List[str]] = {
                aid: [] for aid in self.data["actors"]
            }

            for aid in actor_roles:
                actor_roles[aid] = get_actor_roles(self.data, aid)

            aid: str
            info: Dict[str, Any]
            for aid, info in self.data["actors"].items():
                row: int = self.actor_table.rowCount()
                self.actor_table.insertRow(row)

                item: QTableWidgetItem = QTableWidgetItem(info["name"])
                item.setData(Qt.UserRole, aid)
                self.actor_table.setItem(row, 0, item)

                btn: QPushButton = QPushButton(f"Роли ({len(actor_roles[aid])})")
                self.actor_table.setCellWidget(row, 1, wrap_widget(btn))

                color_item: QTableWidgetItem = QTableWidgetItem()
                color_item.setBackground(QColor(info["color"]))
                self.actor_table.setItem(row, 2, color_item)

                gender_item = QTableWidgetItem(info.get("gender", ""))
                gender_item.setFlags(gender_item.flags() & ~Qt.ItemIsEditable)
                self.actor_table.setItem(row, 3, gender_item)

            self.actor_table.setSortingEnabled(True)
            self.actor_table.blockSignals(False)
            logger.info(f"refresh_actor_list: fallback loaded {self.actor_table.rowCount()} actors")
        self._update_actor_filter_combo()

    def rename_episode(self) -> None:
        """Rename episode."""
        old: Optional[str] = self.ep_combo.currentData()
        new_name: str
        ok: bool
        new_name, ok = QInputDialog.getText(
            self, "Rename", "New name:", text=str(old)
        )
        if ok and new_name and new_name != old:
            command = RenameEpisodeCommand(
                self.data["episodes"],
                old,
                new_name,
                self.data.get("episode_actor_map", {})
            )
            self.undo_stack.push(command)
            self.update_ep_list(new_name)
            self.set_dirty()

    def delete_episode_dialog(self) -> None:
        """Delete episode dialog."""
        ep: Optional[str] = self.ep_combo.currentData()
        if not ep:
            QMessageBox.information(self, "Инфо", "Нет серий для удаления.")
            return

        reply: int = QMessageBox.question(
            self,
            "Удаление серии",
            f"Вы уверены, что хотите удалить серию {ep}?\n\n"
            f"Это удалит серию из проекта, но не затронет .ass файл.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            self.delete_episode(ep)

    def delete_episode(self, ep: str) -> None:
        """Delete episode."""
        command = DeleteEpisodeCommand(
            self.data["episodes"],
            self.data.get("video_paths", {}),
            self.data.get("loaded_episodes", {}),
            ep,
            self.data.get("episode_actor_map", {}),
            self.data.get("episode_texts", {})
        )
        self.undo_stack.push(command)

        self.episode_service.invalidate_episode(ep)

        self.update_ep_list()

        self.set_dirty()

        QMessageBox.information(
            self, "Готово", f"Серия {ep} удалена из проекта."
        )
    
    def update_ep_list(self, select: Optional[str] = None) -> None:
        """Update ep list."""
        self.ep_combo.blockSignals(True)
        self.ep_combo.clear()

        ep: str
        for ep in sorted(
            self.data["episodes"].keys(),
            key=natural_sort_key
        ):
            self.ep_combo.addItem(str(ep), ep)

        if select:
            self.ep_combo.setCurrentIndex(
                self.ep_combo.findData(select)
            )
        elif self.ep_combo.count() > 0:
            self.ep_combo.setCurrentIndex(0)

        self.ep_combo.blockSignals(False)
        if self.ep_combo.count() == 0:
            self.current_ep_stats = []
            self.refresh_main_table()
            return
        self.change_episode()


    def run_unified_export(self) -> None:
        """Run unified export."""
        do_html: bool = self.chk_exp_html.isChecked()
        do_xls: bool = self.chk_exp_xls.isChecked()
        do_docx: bool = self.chk_exp_docx.isChecked()

        if not (do_html or do_xls or do_docx):
            return

        is_all: bool = self.radio_all.isChecked()

        episodes: Dict[str, Optional[str]]
        if is_all:
            episodes = self.data["episodes"]
        else:
            ep: Optional[str] = self.ep_combo.currentData()
            episodes = {ep: self.data["episodes"].get(ep)}

        if not episodes or None in episodes.values():
            return

        selected_count = sum([do_html, do_xls, do_docx])
        if is_all or selected_count > 1:
            dest = QFileDialog.getExistingDirectory(
                self, "Выберите папку"
            )
            if dest:
                self._execute_batch_export(
                    episodes, do_html, do_xls, do_docx, dest
                )
        else:
            ep = list(episodes.keys())[0]
            if do_html:
                self.export_to_html(ep)
            elif do_xls:
                self.export_to_excel(ep)
            else:
                self.export_to_docx(ep)

    def _update_export_format_config(self) -> None:
        """Persist selected export formats in project settings."""
        if not hasattr(self, "chk_exp_html"):
            return

        export_config = self.data.setdefault(
            "export_config",
            deepcopy(DEFAULT_EXPORT_CONFIG)
        )
        export_config["format_html"] = self.chk_exp_html.isChecked()
        export_config["format_xls"] = self.chk_exp_xls.isChecked()
        export_config["format_docx"] = self.chk_exp_docx.isChecked()

        if hasattr(self, "preview_window") and self.preview_window:
            self.preview_window.sync_export_format_controls()
        if hasattr(self, "set_dirty"):
            self.set_dirty(True)

    def _sync_export_format_controls_from_config(self) -> None:
        """Update main export format checkboxes from project settings."""
        if not hasattr(self, "chk_exp_html"):
            return

        cfg = self.data.get("export_config", DEFAULT_EXPORT_CONFIG)
        controls = [
            (self.chk_exp_html, cfg.get("format_html", True)),
            (self.chk_exp_xls, cfg.get("format_xls", False)),
            (self.chk_exp_docx, cfg.get("format_docx", False)),
        ]
        for checkbox, checked in controls:
            checkbox.blockSignals(True)
            checkbox.setChecked(bool(checked))
            checkbox.blockSignals(False)

        if hasattr(self, "preview_window") and self.preview_window:
            self.preview_window.sync_export_format_controls()

    def _execute_batch_export(
        self,
        episodes: Dict[str, str],
        do_html: bool,
        do_xls: bool,
        do_docx: bool,
        folder: str
    ) -> None:
        """Execute batch export."""
        export_service = ExportService(self.data)
        
        progress = QProgressDialog(self)
        progress.setWindowTitle("Экспорт")
        progress.setLabelText("Экспорт серий...")
        progress.setRange(0, len(episodes))
        progress.setValue(0)
        progress.setCancelButton(None)
        progress.setWindowModality(Qt.WindowModal)
        progress.show()
        
        def progress_callback(current: int, total: int, message: str):
            progress.setValue(current)
            progress.setLabelText(message)
            progress.repaint()
            QApplication.processEvents()
        
        success, message = export_service.export_batch(
            episodes=episodes,
            get_lines_callback=self.get_episode_lines,
            do_html=do_html,
            do_xls=do_xls,
            do_docx=do_docx,
            folder=folder,
            progress_callback=progress_callback
        )
        
        progress.close()
        
        if success:
            logger.info(message)
            QMessageBox.information(self, "Экспорт завершён", message)
        else:
            QMessageBox.critical(self, "Ошибка экспорта", message)

    def _open_exported_file_if_needed(self, path: str) -> None:
        """Open an exported file when export settings allow it."""
        if not self.data.get("export_config", {}).get("open_auto", True):
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(path))

    def export_to_excel(self, ep: str) -> None:
        """Export data to an Excel file."""
        if not self.export_controller:
            return
        
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Excel", f"Script_{ep}.xlsx", "*.xlsx"
        )

        if path:
            success, message = self.export_controller.export_to_excel(ep, path)
            if success:
                self._open_exported_file_if_needed(path)
            else:
                QMessageBox.warning(self, "Ошибка", message)

    def export_to_docx(self, ep: str) -> None:
        """Export data to a DOCX file."""
        if not self.export_controller:
            return

        path, _ = QFileDialog.getSaveFileName(
            self, "Save DOCX", f"Script_{ep}.docx", "*.docx"
        )

        if path:
            success, message = self.export_controller.export_to_docx(ep, path)
            if success:
                self._open_exported_file_if_needed(path)
            else:
                QMessageBox.warning(self, "Ошибка", message)

    def export_to_html(self, ep: str) -> None:
        """Export to html."""
        if not self.export_controller:
            return
        
        path, _ = QFileDialog.getSaveFileName(
            self, "Save HTML", f"Script_{ep}.html", "*.html"
        )

        if path:
            success, message = self.export_controller.export_to_html(ep, path)
            if success:
                self._open_exported_file_if_needed(path)
            else:
                QMessageBox.warning(self, "Ошибка", message)

    def save_episode_to_ass(
        self,
        ep_num: str,
        target_path: Optional[str] = None
    ) -> bool:
        """Save episode to ass."""
        QMessageBox.warning(
            self,
            "Сохранение отключено",
            "Запись изменений обратно в ASS/SRT отключена.\n"
            "Редактируйте рабочий текст, он сохраняется в JSON автоматически."
        )
        return False



    
    def open_preview(self, char: Optional[str]) -> None:
        """Open preview."""
        ep = self.ep_combo.currentData()
        lines = self.get_episode_lines(ep)
        
        if char:
            lines = [l for l in lines if l['char'] == char]
        
        vp = self.data.get("video_paths", {}).get(ep)
        resolved_vp = self.project_folder_service.resolve_project_path(
            self.data,
            vp
        )
        
        if not resolved_vp or not os.path.exists(resolved_vp):
            self.set_episode_video()
            vp = self.data.get("video_paths", {}).get(ep)
            resolved_vp = self.project_folder_service.resolve_project_path(
                self.data,
                vp
            )
        
        if resolved_vp:
            from .video import VideoPreviewWindow

            VideoPreviewWindow(resolved_vp, lines, ep, self).exec()
    
    def get_episode_lines(self, ep: str) -> List[Dict[str, Any]]:
        """Return episode lines, loading them when needed."""
        if "loaded_episodes" not in self.data:
            self.data["loaded_episodes"] = {}

        working_lines = self.script_text_service.load_episode_lines(self.data, ep)
        if working_lines:
            self.data["loaded_episodes"][ep] = working_lines
            return working_lines

        path = self.data["episodes"].get(ep, "")
        if self._is_subtitle_source_path(path):
            self.data["loaded_episodes"].pop(ep, None)
            return []

        return self.data["loaded_episodes"].get(ep, [])

    def get_srt_episode_lines(self, ep: str) -> List[Dict[str, Any]]:
        """Return srt episode lines."""
        if "loaded_episodes" not in self.data:
            self.data["loaded_episodes"] = {}

        if ep in self.data["loaded_episodes"]:
            return self.data["loaded_episodes"][ep]

        lines = self.episode_service.load_srt_episode(ep, self.data["episodes"])

        if lines:
            self.data["loaded_episodes"][ep] = lines

        return lines

    def regenerate_episode_text(
        self,
        ep: str,
        source_path: Optional[str] = None,
        show_result: bool = True
    ) -> bool:
        """Regenerate episode text."""
        path = source_path or self.data.get("episodes", {}).get(ep, "")

        if not path or not os.path.exists(path):
            QMessageBox.warning(
                self,
                "Ошибка",
                "Исходный файл серии не найден."
            )
            return False

        if not self._build_working_text_from_source(ep, path):
            QMessageBox.warning(
                self,
                "Ошибка",
                "Не удалось получить реплики из исходного файла."
            )
            return False

        self.get_episode_lines(ep)
        self.set_dirty(True)

        if show_result:
            QMessageBox.information(
                self,
                "Готово",
                f"Рабочий текст серии {ep} пересоздан."
            )
        return True

    def _build_working_text_from_source(self, ep: str, path: str) -> bool:
        """Build working text from source."""
        try:
            ext = os.path.splitext(path)[1].lower()
            if ext == '.srt':
                stats, lines = self.episode_service.parse_srt_file(path)
            elif ext == '.docx':
                dialog = DocxImportDialog(self, path)
                if dialog.exec() != QDialog.Accepted:
                    return False
                result = dialog.get_result()
                if not result:
                    return False
                stats = result.get('stats', [])
                lines = self._convert_imported_lines_for_cache(
                    result.get('lines', [])
                )
            else:
                stats, lines = self.episode_service.parse_ass_file(path)
        except Exception as e:
            log_exception(logger, f"Failed to build working text for episode {ep}", e)
            return False

        if not lines:
            return False

        self.data.setdefault("episodes", {})[str(ep)] = path
        self.current_ep_stats = stats
        self.script_text_service.create_episode_text(
            self.data,
            str(ep),
            path,
            lines,
            self.data.get("replica_merge_config", {}),
            self.current_project_path
        )

        self.data.get("loaded_episodes", {}).pop(str(ep), None)
        self.episode_service.invalidate_episode(str(ep))
        return True
    
    def show_project_summary(self) -> None:
        """Show project summary."""
        SummaryDialog(self.data, None, self).exec()

    def show_episode_summary(self) -> None:
        """Show episode summary."""
        ep: Optional[str] = self.ep_combo.currentData()
        if ep:
            SummaryDialog(self.data, ep, self).exec()

    def edit_roles(
        self,
        aid: str,
        name: str,
        roles: List[str]
    ) -> None:
        """Edit roles."""
        role_stats = self._get_actor_role_stats(aid, roles)
        ActorRolesDialog(name, roles, self, role_stats).exec()

    def open_project_roles_dialog(self) -> None:
        """Open project-wide roles dialog."""
        dialog = ProjectRolesDialog(
            self.data,
            self,
            get_episode_lines=self.get_episode_lines,
            on_changed=self._on_project_roles_changed,
        )
        dialog.exec()

    def _on_project_roles_changed(self) -> None:
        """Refresh UI after project role assignments change."""
        self.refresh_actor_list()
        self.refresh_main_table()
        self.set_dirty(True)

    def _get_actor_role_stats(
        self,
        actor_id: str,
        roles: List[str]
    ) -> List[Dict[str, Any]]:
        """Return actor role stats."""
        stats = {
            role: {"name": role, "rings": 0, "words": 0}
            for role in roles
        }
        export_service = ExportService(self.data)

        for ep in self.data.get("episodes", {}).keys():
            lines = self.get_episode_lines(str(ep))
            if not lines:
                continue

            processed = export_service.process_merge_logic(
                lines,
                self.data.get("replica_merge_config", {})
            )

            for line in processed:
                char_name = line.get("char", "")
                if get_actor_for_character(self.data, char_name, str(ep)) != actor_id:
                    continue

                if char_name not in stats:
                    stats[char_name] = {
                        "name": char_name,
                        "rings": 0,
                        "words": 0
                    }

                stats[char_name]["rings"] += 1
                stats[char_name]["words"] += len(
                    line.get("text", "").split()
                )

        return sorted(stats.values(), key=lambda item: item["name"].lower())

    def open_export_settings(self) -> None:
        """Open export settings."""
        self.open_project_settings(initial_tab="export")

    def open_global_settings(self, initial_tab: str = "export") -> None:
        """Open global application settings."""
        dialog = SettingsDialog(
            self.data,
            self,
            initial_tab=initial_tab,
            settings_scope="global",
        )
        if dialog.exec():
            settings = dialog.get_settings()
            old_language = self.global_settings.get("language", "ru")
            self.global_settings["language"] = settings.get("language", old_language)
            if "default_export_config" in settings:
                self.global_settings["default_export_config"] = (
                    settings["default_export_config"]
                )
            if "default_prompter_config" in settings:
                self.global_settings["default_prompter_config"] = (
                    settings["default_prompter_config"]
                )
            self.global_settings_service.save_settings(self.global_settings)
            self.global_settings = self.global_settings_service.get_settings()
            if "default_prompter_config" in settings:
                self.apply_prompter_reaper_ports_to_project(
                    settings["default_prompter_config"]
                )

            if self.global_settings["language"] != old_language:
                set_language(self.global_settings["language"])
                self.retranslate_ui()

    def open_project_settings(self, initial_tab: str = "project") -> None:
        """Open project-specific settings."""
        dialog = SettingsDialog(
            self.data,
            self,
            initial_tab=initial_tab,
            settings_scope="project",
        )
        if dialog.exec():
            settings = dialog.get_settings()

            self.data["project_name"] = settings["project_name"]
            self.data.setdefault("metadata", {}).update(settings["metadata"])
            self.data["export_config"] = settings["export_config"]
            self.data["replica_merge_config"] = settings["replica_merge_config"]
            self.data["prompter_config"] = settings["prompter_config"]
            self.data["docx_import_config"] = settings["docx_import_config"]

            self.episode_service.set_merge_gap_from_config(
                self.data["replica_merge_config"]
            )

            self.change_episode()
            self._sync_export_format_controls_from_config()
            self._sync_preview_export_settings()
            self.set_dirty()

    def _sync_preview_export_settings(self) -> None:
        """Refresh open preview controls after export settings change."""
        if not getattr(self, "preview_window", None):
            return
        if hasattr(self.preview_window, "sync_export_settings"):
            self.preview_window.sync_export_settings(update_preview=True)
        else:
            self.preview_window.update_preview()

    def open_global_search(self) -> None:
        """Open global search."""
        GlobalSearchDialog(self.data, self).exec()

    def open_live_preview(self) -> None:
        """Open live preview."""
        ep: Optional[str] = self.ep_combo.currentData()
        if not ep:
            QMessageBox.information(self, "Инфо", "Выберите серию.")
            return

        if self.preview_window is not None:
            self.preview_window.close()

        from .preview import HtmlLivePreview

        self.preview_window = HtmlLivePreview(self, ep)
        self.preview_window.show()

    def open_teleprompter(self) -> None:
        """Open teleprompter."""
        ep: Optional[str] = self.ep_combo.currentData()
        if not ep:
            QMessageBox.information(self, "Инфо", "Выберите серию.")
            return

        if not self.ensure_working_text_for_episode(
            ep,
            "открыть телесуфлёр"
        ):
            return

        if not self.get_episode_lines(ep):
            return

        if self.teleprompter_window is not None:
            self.teleprompter_window.close()

        self.teleprompter_window = TeleprompterWindow(self, ep)
        self.teleprompter_window.show()

    def _apply_global_settings_to_project(self) -> None:
        """Apply global settings to project."""
        self.episode_service.set_merge_gap_from_config(
            self.data["replica_merge_config"]
        )

    def _apply_global_settings_to_project_data(
        self,
        project_data: Dict[str, Any]
    ) -> None:
        """Apply global defaults that are intended for new projects."""
        project_data["export_config"] = (
            self.global_settings_service.get_default_export_config()
        )
        project_data["prompter_config"] = (
            self.global_settings_service.get_default_prompter_config()
        )
        project_data.setdefault(
            "docx_import_config",
            deepcopy(DEFAULT_DOCX_IMPORT_CONFIG),
        )

    def save_default_export_config(self, config: Dict[str, Any]) -> bool:
        """Save default export settings for future projects."""
        self.global_settings_service.set_default_export_config(config)
        self.global_settings["default_export_config"] = (
            self.global_settings_service.get_default_export_config()
        )
        return self.global_settings_service.save_settings(self.global_settings)

    def apply_default_export_config_to_project(self) -> Dict[str, Any]:
        """Apply default export settings to the current project."""
        return self.apply_export_config_to_project(
            self.global_settings_service.get_default_export_config()
        )

    def apply_export_config_to_project(
        self,
        config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Apply export settings to the current project."""
        export_config = deepcopy(DEFAULT_EXPORT_CONFIG)
        export_config.update(deepcopy(config))
        self.data["export_config"] = export_config
        self._sync_export_format_controls_from_config()
        self._sync_preview_export_settings()
        self.set_dirty(True)
        return deepcopy(self.data["export_config"])

    def save_default_prompter_config(self, config: Dict[str, Any]) -> bool:
        """Save default teleprompter settings for future projects."""
        self.global_settings_service.set_default_prompter_config(config)
        self.global_settings["default_prompter_config"] = (
            self.global_settings_service.get_default_prompter_config()
        )
        return self.global_settings_service.save_settings(self.global_settings)

    def apply_default_prompter_config_to_project(self) -> Dict[str, Any]:
        """Apply default teleprompter settings to the current project."""
        return self.apply_prompter_config_to_project(
            self.global_settings_service.get_default_prompter_config()
        )

    def apply_prompter_config_to_project(
        self,
        config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Apply teleprompter settings to the current project."""
        self.data["prompter_config"] = deepcopy(config)
        self._sync_teleprompter_settings()
        self.set_dirty(True)
        return deepcopy(self.data["prompter_config"])

    def apply_prompter_reaper_ports_to_project(
        self,
        config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Apply Reaper sync ports to the current project."""
        prompter_config = deepcopy(
            self.data.get("prompter_config") or DEFAULT_PROMPTER_CONFIG
        )
        changed = False
        for key in ("port_in", "port_out"):
            if key in config and prompter_config.get(key) != config[key]:
                prompter_config[key] = config[key]
                changed = True

        if changed:
            self.data["prompter_config"] = prompter_config
            self._sync_teleprompter_settings()
            self.set_dirty(True)
        return deepcopy(prompter_config)

    def _sync_teleprompter_settings(self) -> None:
        """Refresh an open teleprompter after settings change."""
        if not getattr(self, "teleprompter_window", None):
            return
        self.teleprompter_window.cfg = self.data["prompter_config"]
        if hasattr(self.teleprompter_window, "sync_config_controls"):
            self.teleprompter_window.sync_config_controls()
        self.teleprompter_window.build_prompter_content()

    def get_prompter_color_presets(self) -> List[Optional[Dict[str, str]]]:
        """Return global teleprompter color presets."""
        return self.global_settings_service.get_prompter_color_presets()

    def save_prompter_color_preset(
        self,
        index: int,
        colors: Dict[str, str]
    ) -> bool:
        """Save one global teleprompter color preset."""
        self.global_settings_service.set_prompter_color_preset(index, colors)
        self.global_settings["prompter_color_presets"] = (
            self.global_settings_service.get_prompter_color_presets()
        )
        return self.global_settings_service.save_settings(self.global_settings)

    def clear_prompter_color_preset(self, index: int) -> bool:
        """Clear one global teleprompter color preset."""
        self.global_settings_service.clear_prompter_color_preset(index)
        self.global_settings["prompter_color_presets"] = (
            self.global_settings_service.get_prompter_color_presets()
        )
        return self.global_settings_service.save_settings(self.global_settings)

    def save_global_prompter_settings(self, config: Dict[str, Any]) -> None:
        """Compatibility shim for teleprompter callers; settings are project-local."""
        self.data["prompter_config"] = config

    def export_to_reaper_rpp(self) -> None:
        """Export to reaper rpp."""
        ep_num: Optional[str] = self.ep_combo.currentData()
        if not ep_num:
            QMessageBox.warning(self, "Ошибка", "Выберите серию.")
            return

        lines = self.get_episode_lines(ep_num)
        if not lines:
            self.ensure_working_text_for_episode(ep_num, "экспортировать RPP")
            return

        video_path = self.project_folder_service.resolve_project_path(
            self.data,
            self.data["video_paths"].get(ep_num)
        )
        export_service = ExportService(self.data)

        def make_preview(
            use_video: bool,
            use_regions: bool,
            transliterate_actor_names: bool
        ) -> Dict[str, Any]:
            preview_video_path = video_path
            return export_service.get_reaper_rpp_preview(
                ep_num,
                lines,
                merge_cfg=self.data.get("replica_merge_config", {}),
                video_path=preview_video_path,
                use_video=use_video,
                use_regions=use_regions,
                transliterate_actor_names=transliterate_actor_names
            )

        dialog = ReaperExportDialog(
            video_path,
            self,
            preview_provider=make_preview
        )

        if dialog.exec() != QDialog.Accepted:
            return

        use_video, use_regions, transliterate_actor_names = dialog.get_options()

        default_name = (
            f"{self.data.get('project_name', 'Project')} - "
            f"Ep{ep_num}.rpp"
        )
        save_path, _ = QFileDialog.getSaveFileName(
            self, "Сохранить RPP", default_name, "Reaper Project (*.rpp)"
        )
        if not save_path:
            return

        rpp_content = export_service.generate_reaper_rpp(
            ep_num,
            lines,
            merge_cfg=self.data.get("replica_merge_config", {}),
            video_path=video_path,
            use_video=use_video,
            use_regions=use_regions,
            transliterate_actor_names=transliterate_actor_names
        )
        
        try:
            export_service.save_reaper_rpp(save_path, rpp_content)
            
            reply = QMessageBox.question(
                self,
                "Готово",
                "Проект создан. Открыть в Reaper?",
                QMessageBox.Yes | QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                QDesktopServices.openUrl(QUrl.fromLocalFile(save_path))
        except Exception as e:
            log_exception(logger, "Error saving RPP", e)
            QMessageBox.critical(
                self, "Ошибка", f"Не удалось сохранить: {e}"
            )
    
    def switch_to_episode(self, ep_num: str) -> None:
        """Switch to episode."""
        index = self.ep_combo.findData(ep_num)
        if index >= 0:
            self.ep_combo.setCurrentIndex(index)

    # === Quick subtitle converter ===

    def convert_dropped_subtitles(
        self,
        paths: List[str],
        preview_first: bool = False
    ) -> None:
        """Convert dropped ASS/SRT files to selected montage formats."""
        files = [
            path for path in paths
            if os.path.isfile(path) and
            QuickSubtitleDropZone.is_supported_path(path)
        ]
        if not files:
            QMessageBox.warning(
                self,
                "Быстрый конвертер",
                "Перетащите файлы ASS или SRT."
            )
            return

        if preview_first:
            self._preview_dropped_subtitle_conversion(files)
            return

        if not self._quick_montage_should_export_html() and not (
            self._quick_montage_should_export_docx()
        ):
            QMessageBox.information(
                self,
                "Быстрый конвертер",
                "Выберите HTML или DOCX в настройках экспорта."
            )
            return

        progress = QProgressDialog(
            "Конвертация субтитров...",
            "Отмена",
            0,
            len(files),
            self
        )
        progress.setWindowTitle("Быстрый конвертер")
        progress.setWindowModality(Qt.WindowModal)
        progress.setMinimumDuration(0)

        exported: List[str] = []
        errors: List[str] = []

        for idx, path in enumerate(files, 1):
            if progress.wasCanceled():
                break

            progress.setLabelText(
                f"Конвертация {idx} из {len(files)}:\n"
                f"{os.path.basename(path)}"
            )
            progress.setValue(idx - 1)
            QApplication.processEvents()

            try:
                exported.extend(self._export_quick_subtitle_montage(path))
            except Exception as exc:
                log_exception(logger, "Quick subtitle conversion failed", exc)
                errors.append(f"{os.path.basename(path)}: {exc}")

        progress.setValue(len(files))

        if exported:
            shown_paths = "\n".join(exported[:5])
            extra_count = len(exported) - 5
            if extra_count > 0:
                shown_paths += f"\n...и ещё {extra_count}"
            QMessageBox.information(
                self,
                "Быстрый конвертер",
                f"Готово. Экспортировано файлов: {len(exported)}\n\n"
                f"{shown_paths}"
            )

        if errors:
            QMessageBox.warning(
                self,
                "Быстрый конвертер",
                "Не удалось конвертировать некоторые файлы:\n\n" +
                "\n".join(errors[:8])
            )

    def _preview_dropped_subtitle_conversion(self, files: List[str]) -> None:
        """Open quick preview for the first dropped subtitle, then convert all."""
        first_path = files[0]
        try:
            _stats, lines = self._parse_quick_subtitle_file(first_path)
            if not lines:
                raise ValueError("в файле нет реплик")
            lines = self._normalize_quick_subtitle_lines(lines)
        except Exception as exc:
            log_exception(logger, "Quick subtitle preview failed", exc)
            QMessageBox.warning(
                self,
                "Быстрый конвертер",
                f"Не удалось открыть превью: {exc}"
            )
            return

        from .preview import HtmlLivePreview

        preview = HtmlLivePreview(
            self,
            "1",
            override_lines=lines,
            source_title=os.path.basename(first_path),
            register_preview=False
        )
        preview.exec()
        self.convert_dropped_subtitles(files, preview_first=False)

    def _export_quick_subtitle_montage(self, path: str) -> List[str]:
        """Export one subtitle file to montage files next to it."""
        _stats, lines = self._parse_quick_subtitle_file(path)
        if not lines:
            raise ValueError("в файле нет реплик")
        lines = self._normalize_quick_subtitle_lines(lines)

        cfg = self._quick_montage_export_config()
        project_data = {
            "project_name": os.path.splitext(os.path.basename(path))[0],
            "actors": {},
            "global_map": {},
            "episode_actor_map": {},
            "export_config": cfg,
            "replica_merge_config": deepcopy(
                self.data.get("replica_merge_config", {})
            ),
        }
        export_service = ExportService(project_data)
        processed = export_service.process_merge_logic(
            lines,
            project_data["replica_merge_config"]
        )
        exported: List[str] = []

        if self._quick_montage_should_export_html():
            html_path = self._quick_montage_output_path(path, ".html")
            html = export_service.generate_html(
                "1",
                processed,
                cfg,
                highlight_ids=[],
                layout_type=cfg.get("layout_type", "Таблица"),
                is_editable=False
            )
            with open(html_path, "w", encoding="utf-8") as file:
                file.write(html)
            exported.append(html_path)

        if self._quick_montage_should_export_docx():
            docx_path = self._quick_montage_output_path(path, ".docx")
            document = export_service.create_docx_document({"1": processed}, cfg)
            document.save(docx_path)
            exported.append(docx_path)

        return exported

    def _parse_quick_subtitle_file(
        self,
        path: str
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Parse a subtitle file for quick conversion."""
        extension = os.path.splitext(path)[1].lower()
        if extension == ".srt":
            return self.episode_service.parse_srt_file(path)
        if extension == ".ass":
            return self.episode_service.parse_ass_file(path)
        raise ValueError("поддерживаются только ASS и SRT")

    def _normalize_quick_subtitle_lines(
        self,
        lines: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Ensure quick-converted subtitle lines have stable ids."""
        normalized = []
        for idx, line in enumerate(lines):
            line_data = line.copy()
            line_data.setdefault("id", idx)
            normalized.append(line_data)
        return normalized

    def _quick_montage_export_config(self) -> Dict[str, Any]:
        """Return current export config without actor color highlighting."""
        cfg = deepcopy(DEFAULT_EXPORT_CONFIG)
        cfg.update(deepcopy(self.data.get("export_config", {})))
        cfg["use_color"] = False
        cfg["highlight_ids_export"] = []
        cfg["highlight_negative_ids_export"] = []
        cfg["allow_edit"] = False
        return cfg

    def _quick_montage_should_export_html(self) -> bool:
        """Return True when HTML is enabled in current export controls."""
        return hasattr(self, "chk_exp_html") and self.chk_exp_html.isChecked()

    def _quick_montage_should_export_docx(self) -> bool:
        """Return True when DOCX is enabled in current export controls."""
        return hasattr(self, "chk_exp_docx") and self.chk_exp_docx.isChecked()

    def _quick_montage_output_path(
        self,
        source_path: str,
        extension: str
    ) -> str:
        """Return a unique montage path next to the source subtitle file."""
        folder = os.path.dirname(source_path)
        stem = os.path.splitext(os.path.basename(source_path))[0]
        base = os.path.join(folder, stem)
        candidate = f"{base}{extension}"
        counter = 2
        while os.path.exists(candidate):
            candidate = f"{base} ({counter}){extension}"
            counter += 1
        return candidate
    
    # === Drag & Drop ===
    
    def dragEnterEvent(self, event) -> None:
        """Dragenterevent."""
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()
    
    def dropEvent(self, event) -> None:
        """Dropevent."""
        files = [
            url.toLocalFile() 
            for url in event.mimeData().urls()
        ]
        
        ass_files = [f for f in files if f.endswith('.ass')]
        json_files = [f for f in files if f.endswith('.json')]
        
        if json_files and self.maybe_save():
            self._load_from_path(json_files[0])
        elif ass_files:
            self.import_ass(ass_files)
    
    def closeEvent(self, event) -> None:
        """Closeevent."""
        if self.maybe_save():
            event.accept()
        else:
            event.ignore()

    def show_about(self) -> None:
        """Show about."""
        dialog = QDialog(self)
        dialog.setWindowTitle("О программе")
        dialog.setMinimumWidth(420)

        layout = QVBoxLayout(dialog)
        about_text = QLabel(
            "<h2>Dubbing Manager</h2>"
            "<p>Приложение для управления проектами дубляжа и озвучивания.</p>"
            f"<p><b>Версия:</b> {APP_VERSION}</p>"
            "<p><b>GitHub:</b> "
            "<a href='https://github.com/ScrapDnB/DubbingManager/'>"
            "ScrapDnB/DubbingManager</a></p>"
            f"<p><b>Python:</b> "
            f"{sys.version_info.major}.{sys.version_info.minor}."
            f"{sys.version_info.micro}</p>"
            "<p><b>PySide6:</b> 6.10.2</p>"
            "<p>© 2026 Юрий Романов</p>"
        )
        about_text.setOpenExternalLinks(True)
        about_text.setWordWrap(True)
        layout.addWidget(about_text)

        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        btn_updates = buttons.addButton(
            tr("main.check_updates"),
            QDialogButtonBox.ActionRole
        )
        btn_updates.clicked.connect(
            lambda: self.check_for_updates(
                button=btn_updates,
                force_install=self._is_force_update_modifier_pressed(),
                source_dialog=dialog,
            )
        )
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)

        dialog.exec()

    def _is_force_update_modifier_pressed(self) -> bool:
        """Return whether the update button was clicked with Option/Alt."""
        return bool(QApplication.keyboardModifiers() & Qt.AltModifier)

    def check_for_updates(
        self,
        button: Optional[QPushButton] = None,
        force_install: bool = False,
        source_dialog: Optional[QDialog] = None,
    ) -> None:
        """Check GitHub Releases for a newer application version."""
        if button is not None:
            button.setEnabled(False)
        try:
            update_info = self.update_service.check_for_updates(APP_VERSION)
        except Exception as e:
            log_exception(logger, "Error checking updates", e)
            QMessageBox.warning(
                self,
                "Проверка обновлений",
                "Не удалось проверить обновления.\n\n"
                "Проверьте подключение к интернету или откройте страницу "
                "релизов вручную."
            )
            return
        finally:
            if button is not None:
                button.setEnabled(True)

        if update_info.is_update_available or force_install:
            title = (
                "Принудительное обновление"
                if force_install and not update_info.is_update_available
                else "Доступно обновление"
            )
            message = (
                f"Будет переустановлена текущая версия "
                f"{update_info.current_version}.\n\n"
                "Установить обновление автоматически?"
                if force_install and not update_info.is_update_available
                else (
                    f"Доступна версия {update_info.latest_version}.\n"
                    f"Установленная версия: {update_info.current_version}.\n\n"
                    "Установить обновление автоматически?"
                )
            )
            reply = QMessageBox.question(
                self,
                title,
                message,
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes
            )
            if reply == QMessageBox.Yes:
                if source_dialog is not None:
                    source_dialog.close()
                    QApplication.processEvents()
                self.install_update(update_info)
            else:
                QDesktopServices.openUrl(QUrl(update_info.release_url))
            return

        QMessageBox.information(
            self,
            "Проверка обновлений",
            f"Установлена актуальная версия {update_info.current_version}."
        )

    def install_update(self, update_info) -> None:
        """Install an available update for source or packaged app modes."""
        try:
            if self.update_service.is_source_checkout(os.getcwd()):
                output = self.update_service.install_source_update(os.getcwd())
                QMessageBox.information(
                    self,
                    "Обновление установлено",
                    "Исходники обновлены из GitHub.\n\n"
                    f"{output or 'Репозиторий уже актуален.'}\n\n"
                    "Перезапустите приложение, чтобы запустить новую версию."
                )
                return

            if not getattr(sys, "frozen", False):
                QMessageBox.warning(
                    self,
                    "Автообновление недоступно",
                    "Приложение запущено из Python, но рядом не найден git-репозиторий. "
                    "Открою страницу релиза."
                )
                QDesktopServices.openUrl(QUrl(update_info.release_url))
                return

            asset = self.update_service.find_platform_asset(update_info)
            if asset is None:
                QMessageBox.warning(
                    self,
                    "Обновление недоступно",
                    "Для вашей платформы не найден готовый установочный файл. "
                    "Открою страницу релиза."
                )
                QDesktopServices.openUrl(QUrl(update_info.release_url))
                return

            asset_path = self._download_update_asset(asset)
            replace_progress = QProgressDialog(
                "Готовлю замену файлов приложения...",
                None,
                0,
                0,
                self
            )
            replace_progress.setWindowTitle("Обновление")
            replace_progress.setWindowModality(Qt.WindowModal)
            replace_progress.setMinimumDuration(0)
            replace_progress.show()
            QApplication.processEvents()
            self.update_service.start_binary_update(asset_path)
            replace_progress.close()
            QMessageBox.information(
                self,
                "Обновление запускается",
                "Обновление скачано. Приложение сейчас закроется, "
                "внешний updater заменит файлы и запустит новую версию.\n\n"
                "О ходе замены появятся системные уведомления."
            )
            QApplication.quit()
        except Exception as e:
            log_exception(logger, "Error installing update", e)
            QMessageBox.warning(
                self,
                "Ошибка обновления",
                "Не удалось установить обновление автоматически.\n\n"
                f"{e}\n\n"
                "Открою страницу релиза, чтобы можно было обновиться вручную."
            )
            QDesktopServices.openUrl(QUrl(update_info.release_url))

    def _download_update_asset(self, asset) -> str:
        """Download an update asset with visible progress."""
        progress = QProgressDialog(
            f"Скачиваю обновление: {asset.name}",
            "Отмена",
            0,
            int(asset.size or 0),
            self
        )
        progress.setWindowTitle("Скачивание обновления")
        progress.setWindowModality(Qt.WindowModal)
        progress.setMinimumDuration(0)
        if not asset.size:
            progress.setRange(0, 0)

        def on_progress(downloaded: int, total: int) -> None:
            if total > 0 and progress.maximum() != total:
                progress.setRange(0, total)
            if total > 0:
                progress.setValue(min(downloaded, total))
            QApplication.processEvents()
            if progress.wasCanceled():
                raise RuntimeError("Скачивание обновления отменено.")

        try:
            return self.update_service.download_asset(
                asset,
                progress_callback=on_progress
            )
        finally:
            progress.close()

    def open_project_files_dialog(self) -> None:
        """Open project files dialog."""
        dialog = ProjectFilesDialog(self.data, self)
        dialog.exec()

    def open_project_health_dialog(self) -> None:
        """Open project health dialog."""
        dialog = ProjectFilesDialog(self.data, self, initial_tab="health")
        dialog.exec()

    def _on_files_changed(self) -> None:
        """Handle files change."""
        self.update_ep_list()
        
        self.change_episode()
        
        self.set_dirty()
