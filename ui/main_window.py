"""Главное окно приложения"""

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QFileDialog, QTableWidget, QTableWidgetItem,
    QColorDialog, QComboBox, QLabel, QHeaderView, QInputDialog,
    QFrame, QSpinBox, QLineEdit, QListWidget, QListWidgetItem,
    QCheckBox, QGroupBox, QFormLayout, QMessageBox, QSlider,
    QAbstractItemView, QStackedWidget, QDoubleSpinBox, QRadioButton,
    QGridLayout, QScrollArea, QSplitter, QSizePolicy, QToolBar,
    QDialogButtonBox, QTextEdit, QDialog, QProgressDialog, QApplication,
    QStyledItemDelegate, QStyle
)
from PySide6.QtGui import QColor, QFont, QAction, QKeySequence, QPen, QBrush
from PySide6.QtCore import (
    Qt, QUrl, QTimer, Signal, QRectF, QEvent, Slot, QPersistentModelIndex
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
    get_video_fps
)
from services import (
    ProjectService,
    EpisodeService,
    ActorService,
    ExportService,
    GlobalSettingsService,
    ProjectFolderService,
    ScriptTextService,
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
    GlobalSearchDialog,
    SummaryDialog,
    ProjectFilesDialog,
    ProjectHealthDialog,
    SettingsDialog,
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
PREVIOUS_SCOPE_ROLE = Qt.UserRole + 3
PREVIOUS_ACTOR_ID_ROLE = Qt.UserRole + 4


class ScopeComboDelegate(QStyledItemDelegate):
    """Редактор области назначения без постоянного QComboBox в таблице."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._editing_index = QPersistentModelIndex()

    def createEditor(self, parent, option, index):
        self._editing_index = QPersistentModelIndex(index)
        combo = QComboBox(parent)
        combo.addItem("Глобально", ASSIGNMENT_SCOPE_GLOBAL)
        combo.addItem("Серия", ASSIGNMENT_SCOPE_EPISODE)
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
    """Редактор актёра без постоянного QComboBox в таблице."""

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


class MainWindow(QMainWindow):
    """Главное окно приложения Dubbing Manager"""

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

        # Сервисы
        self.project_service = ProjectService()
        self.actor_service = ActorService()
        self.global_settings_service = GlobalSettingsService()
        self.project_folder_service = ProjectFolderService()
        self.script_text_service = ScriptTextService()
        self.episode_service = EpisodeService()

        # Контроллеры
        self.actor_controller: Optional[ActorController] = None
        self.episode_controller: Optional[EpisodeController] = None
        self.export_controller: Optional[ExportController] = None
        self.project_controller: Optional[ProjectController] = None

        # Стек отмены/повтора действий
        self.undo_stack = UndoStack()
        self.undo_stack.on_change(self._on_undo_stack_change)

        # Состояние
        self.current_project_path = None
        self.is_dirty = False
        self.sort_col = 1
        self.sort_desc = True
        self.preview_window = None
        self.teleprompter_window = None

        # Загрузка глобальных настроек
        self.global_settings = self.global_settings_service.load_settings()

        # Данные проекта
        self.data = self.project_service.create_new_project("Новый проект")

        # Инициализация контроллеров
        self._init_controllers()

        # Применение глобальных настроек к проекту
        self._apply_global_settings_to_project()

        self.current_ep_stats = []
        self.character_names_changed = {}
        self.text_changes = {}  # Флаг изменений текста для каждого эпизода

        self._init_ui()
        self.update_window_title()

        # Автосохранение
        self.autosave_timer = QTimer(self)
        self.autosave_timer.timeout.connect(self._on_autosave_timer)
        self.autosave_timer.start(AUTOSAVE_INTERVAL_MS)

    def _init_controllers(self) -> None:
        """Инициализация контроллеров"""
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
        """Обработчик таймера автосохранения"""
        if self.project_controller:
            self.project_controller.auto_save()

    def _init_ui(self) -> None:
        """Инициализация интерфейса"""
        central: QWidget = QWidget()
        self.setCentralWidget(central)
        main_layout: QHBoxLayout = QHBoxLayout(central)

        # Левая панель - актёры
        self._init_actor_panel(main_layout)

        # Правая панель - основной контент
        self._init_main_panel(main_layout)

        # Горячие клавиши для Undo/Redo
        self._setup_undo_redo_shortcuts()

    def _setup_undo_redo_shortcuts(self) -> None:
        """Настройка горячих клавиш для Undo/Redo"""
        # Ctrl+Z для Undo
        undo_shortcut = QKeySequence("Ctrl+Z")
        undo_action = QAction("Undo", self)
        undo_action.setShortcut(undo_shortcut)
        undo_action.triggered.connect(self.undo)
        self.addAction(undo_action)

        # Ctrl+Shift+Z для Redo
        redo_shortcut = QKeySequence("Ctrl+Shift+Z")
        redo_action = QAction("Redo", self)
        redo_action.setShortcut(redo_shortcut)
        redo_action.triggered.connect(self.redo)
        self.addAction(redo_action)

    def _init_actor_panel(self, main_layout: QHBoxLayout) -> None:
        """Инициализация панели актёров"""
        left_panel: QVBoxLayout = QVBoxLayout()
        left_widget = QFrame()
        left_widget.setFixedWidth(ACTOR_PANEL_WIDTH)
        left_widget.setFrameShape(QFrame.StyledPanel)
        left_widget.setLayout(left_panel)

        left_panel.addWidget(QLabel("<b>БАЗА АКТЕРОВ</b>"))

        self.actor_table = QTableWidget(0, 3)
        customize_table(self.actor_table)

        # Создаём контроллер актёров
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

        # Кнопки управления актёрами
        btn_layout = QHBoxLayout()
        
        btn_add = QPushButton("+ Актер")
        btn_add.clicked.connect(self.add_actor_dialog)
        btn_layout.addWidget(btn_add)
        
        btn_delete = QPushButton("- Актер")
        btn_delete.setToolTip("Удалить выбранного актёра из базы")
        btn_delete.clicked.connect(self.delete_actor_dialog)
        btn_layout.addWidget(btn_delete)
        
        left_panel.addLayout(btn_layout)

        btn_sum = QPushButton("📋 Сводный отчет проекта")
        btn_sum.clicked.connect(self.show_project_summary)
        left_panel.addWidget(btn_sum)

        main_layout.addWidget(left_widget)

    def _init_main_panel(self, main_layout: QHBoxLayout) -> None:
        """Инициализация основной панели"""
        right_panel: QVBoxLayout = QVBoxLayout()

        # Верхняя строка - проект
        self._init_project_bar(right_panel)

        # Управление сериями
        self._init_episode_controls(right_panel)

        # Центральная область - таблица + инструменты
        self._init_center_area(right_panel)

        # Нижняя панель - экспорт
        self._init_bottom_panel(right_panel)

        main_layout.addLayout(right_panel)

    def _init_project_bar(self, layout: QHBoxLayout) -> None:
        """Инициализация панели проекта"""
        top: QHBoxLayout = QHBoxLayout()

        self.proj_edit = QLineEdit()
        self.proj_edit.textChanged.connect(self.on_project_name_changed)
        top.addWidget(QLabel("Проект:"))
        top.addWidget(self.proj_edit)

        btn_load = QPushButton("Открыть")
        btn_load.clicked.connect(self.load_project_dialog)
        top.addWidget(btn_load)

        btn_save = QPushButton("Сохранить")
        btn_save.clicked.connect(self.save_project)
        top.addWidget(btn_save)

        btn_copy = QPushButton("Копия")
        btn_copy.clicked.connect(self.save_project_as)
        top.addWidget(btn_copy)

        # Кнопки Undo/Redo
        self.btn_undo = QPushButton("↶")
        self.btn_undo.setToolTip("Отменить последнее действие (Ctrl+Z)")
        self.btn_undo.setFixedWidth(PROJECT_FOLDER_BTN_WIDTH)
        self.btn_undo.clicked.connect(self.undo)
        self.btn_undo.setEnabled(False)
        top.addWidget(self.btn_undo)

        self.btn_redo = QPushButton("↷")
        self.btn_redo.setToolTip("Повторить отменённое действие (Ctrl+Shift+Z)")
        self.btn_redo.setFixedWidth(PROJECT_FOLDER_BTN_WIDTH)
        self.btn_redo.clicked.connect(self.redo)
        self.btn_redo.setEnabled(False)
        top.addWidget(self.btn_redo)

        top.addSpacing(PROJECT_BAR_SPACING)

        # Папка проекта
        self.btn_folder = QPushButton("📁 Папка")
        self.btn_folder.setToolTip("Установить папку проекта")
        self.btn_folder.clicked.connect(self.set_project_folder_dialog)
        top.addWidget(self.btn_folder)

        btn_unlink = QPushButton("🔓")
        btn_unlink.setToolTip("Отвязать папку проекта")
        btn_unlink.setFixedWidth(PROJECT_FOLDER_BTN_WIDTH)
        btn_unlink.clicked.connect(self.clear_project_folder)
        top.addWidget(btn_unlink)

        top.addStretch()

        # Кнопка файлов проекта
        btn_files = QPushButton("📋 Файлы")
        btn_files.setToolTip("Просмотр структуры файлов проекта")
        btn_files.clicked.connect(self.open_project_files_dialog)
        top.addWidget(btn_files)

        btn_health = QPushButton("✓ Проверка")
        btn_health.setToolTip("Проверить проект на потерянные файлы и проблемы в тексте")
        btn_health.clicked.connect(self.open_project_health_dialog)
        top.addWidget(btn_health)

        btn_about = QPushButton("ℹ️")
        btn_about.setFixedWidth(ABOUT_BTN_WIDTH)
        btn_about.clicked.connect(self.show_about)
        top.addWidget(btn_about)

        layout.addLayout(top)

    def _init_episode_controls(self, layout: QHBoxLayout) -> None:
        """Инициализация управления сериями"""
        ep_ctrl = QHBoxLayout()

        self.ep_combo = QComboBox()
        self.ep_combo.setMinimumWidth(EPISODE_COMBO_MIN_WIDTH)
        self.ep_combo.currentIndexChanged.connect(self.change_episode)
        ep_ctrl.addWidget(QLabel("Серия:"))
        ep_ctrl.addWidget(self.ep_combo)

        # Кнопка "Импорт" с автоопределением типа файла
        btn_import = QPushButton("📥 Импорт")
        btn_import.clicked.connect(self.import_files)
        ep_ctrl.addWidget(btn_import)

        btn_ren = QPushButton("✎")
        btn_ren.setFixedWidth(BTN_RENAME_WIDTH)
        btn_ren.clicked.connect(self.rename_episode)
        ep_ctrl.addWidget(btn_ren)

        btn_del = QPushButton("🗑")
        btn_del.setFixedWidth(BTN_RENAME_WIDTH)
        btn_del.clicked.connect(self.delete_episode_dialog)
        ep_ctrl.addWidget(btn_del)

        btn_vid = QPushButton("🎬 Видео")
        btn_vid.clicked.connect(self.set_episode_video)
        ep_ctrl.addWidget(btn_vid)
        
        btn_ep_sum = QPushButton("📊 Отчет серии")
        btn_ep_sum.clicked.connect(self.show_episode_summary)
        ep_ctrl.addWidget(btn_ep_sum)
        
        ep_ctrl.addStretch()

        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Поиск...")
        self.search_edit.setFixedWidth(SEARCH_EDIT_WIDTH)
        self.search_edit.textChanged.connect(self.refresh_main_table)
        ep_ctrl.addWidget(self.search_edit)
        
        btn_glob_search = QPushButton("🔍 Глобальный поиск")
        btn_glob_search.clicked.connect(self.open_global_search)
        ep_ctrl.addWidget(btn_glob_search)
        
        self.filter_unassigned = QCheckBox("Пустые")
        self.filter_unassigned.toggled.connect(self.refresh_main_table)
        ep_ctrl.addWidget(self.filter_unassigned)
        
        layout.addLayout(ep_ctrl)
    
    def _init_center_area(self, layout: QHBoxLayout) -> None:
        """Инициализация центральной области"""
        middle_layout: QHBoxLayout = QHBoxLayout()

        # Стек таблиц
        self.table_stack = QStackedWidget()

        self.main_table = QTableWidget(0, 7)
        self.main_table.setHorizontalHeaderLabels([
            "Персонаж", "Строчек", "Колец", "Слов",
            "Область", "Актер", "📺"
        ])
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
        self.main_table.itemChanged.connect(
            self.on_main_table_item_changed
        )
        self.main_table.cellClicked.connect(self.on_main_table_cell_clicked)
        self.main_table.itemSelectionChanged.connect(
            self.update_selected_character_stats
        )

        self.missing_file_widget = QWidget()
        mf_lay: QVBoxLayout = QVBoxLayout(self.missing_file_widget)

        self.lbl_missing = QLabel("ФАЙЛ НЕ НАЙДЕН")
        self.lbl_missing.setStyleSheet(
            "color: red; font-weight: bold;"
        )
        self.lbl_missing.setAlignment(Qt.AlignCenter)

        btn_relink = QPushButton("Найти...")
        btn_relink.clicked.connect(self.relink_file)

        mf_lay.addStretch()
        mf_lay.addWidget(self.lbl_missing)
        mf_lay.addWidget(btn_relink)
        mf_lay.addStretch()

        self.table_stack.addWidget(self.main_table)
        self.table_stack.addWidget(self.missing_file_widget)

        middle_layout.addWidget(self.table_stack, stretch=1)

        # Панель инструментов
        self._init_tools_sidebar(middle_layout)

        layout.addLayout(middle_layout)

    def _init_tools_sidebar(self, layout: QHBoxLayout) -> None:
        """Инициализация панели инструментов"""
        tools_sidebar_widget = QWidget()
        tools_sidebar_widget.setFixedWidth(TOOLS_SIDEBAR_WIDTH)
        tools_sidebar_layout = QVBoxLayout(tools_sidebar_widget)
        tools_sidebar_layout.setContentsMargins(5, 0, 0, 0)
        
        tools_sidebar_layout.addWidget(QLabel("<b>Инструменты:</b>"))
        
        btn_all_v = QPushButton("📺 Просмотр серии")
        btn_all_v.clicked.connect(lambda: self.open_preview(None))
        tools_sidebar_layout.addWidget(btn_all_v)

        btn_prompter = QPushButton("🎤 Телесуфлёр")
        btn_prompter.clicked.connect(self.open_teleprompter)
        tools_sidebar_layout.addWidget(btn_prompter)

        btn_reaper = QPushButton("🎹 Reaper RPP")
        btn_reaper.clicked.connect(self.export_to_reaper_rpp)
        tools_sidebar_layout.addWidget(btn_reaper)

        tools_sidebar_layout.addStretch()

        self.character_stats_group = QGroupBox("Статистика персонажа")
        stats_layout = QVBoxLayout(self.character_stats_group)
        self.lbl_character_stats_name = QLabel("Выберите персонажа")
        self.lbl_character_stats_name.setWordWrap(True)
        self.lbl_character_stats_name.setStyleSheet("font-weight: bold;")
        stats_layout.addWidget(self.lbl_character_stats_name)

        self.lbl_character_stats_totals = QLabel("Колец: -\nСлов: -")
        stats_layout.addWidget(self.lbl_character_stats_totals)

        self.txt_character_stats_episodes = QTextEdit()
        self.txt_character_stats_episodes.setReadOnly(True)
        self.txt_character_stats_episodes.setFrameShape(QFrame.NoFrame)
        stats_layout.addWidget(self.txt_character_stats_episodes)
        self._reset_character_stats_panel()
        tools_sidebar_layout.addWidget(self.character_stats_group)

        layout.addWidget(tools_sidebar_widget)
    
    def _init_bottom_panel(self, layout) -> None:
        """Инициализация нижней панели"""
        bottom_panel = QHBoxLayout()

        # Левая часть: общие настройки
        btn_settings = QPushButton("⚙ Настройки")
        btn_settings.setToolTip("Общие настройки экспорта, объединения, телесуфлёра и DOCX")
        btn_settings.clicked.connect(self.open_settings)
        bottom_panel.addWidget(btn_settings)

        bottom_panel.addStretch()

        # Правая часть: экспорт монтажных листов
        exp_group = QGroupBox("Экспорт монтажных листов")
        exp_lay = QHBoxLayout(exp_group)
        exp_lay.setContentsMargins(5, 5, 5, 5)

        btn_cfg = QPushButton("⚙ Вид листа")
        btn_cfg.setToolTip("Быстрые настройки монтажного листа")
        btn_cfg.clicked.connect(self.open_export_settings)
        exp_lay.addWidget(btn_cfg)

        exp_lay.addSpacing(EXPORT_PANEL_SPACING)

        btn_preview = QPushButton("📃 Превью")
        btn_preview.clicked.connect(self.open_live_preview)
        exp_lay.addWidget(btn_preview)

        exp_lay.addSpacing(EXPORT_PANEL_SPACING)

        self.chk_exp_html = QCheckBox("Лист")
        self.chk_exp_html.setChecked(True)

        self.chk_exp_xls = QCheckBox("Excel")

        self.radio_cur = QRadioButton("Текущая")
        self.radio_cur.setChecked(True)

        self.radio_all = QRadioButton("Все")

        self.btn_run_export = QPushButton("ЭКСПОРТ")
        self.btn_run_export.clicked.connect(self.run_unified_export)

        exp_lay.addWidget(self.chk_exp_html)
        exp_lay.addWidget(self.chk_exp_xls)
        exp_lay.addSpacing(EXPORT_PANEL_SPACING)
        exp_lay.addWidget(self.radio_cur)
        exp_lay.addWidget(self.radio_all)
        exp_lay.addSpacing(EXPORT_PANEL_SPACING)
        exp_lay.addWidget(self.btn_run_export)

        bottom_panel.addWidget(exp_group)
        layout.addLayout(bottom_panel)
    
    # === Методы работы с данными ===

    def set_dirty(self, dirty: bool = True) -> None:
        """Установка флага изменений"""
        if self.project_controller:
            self.project_controller.set_dirty(dirty)
        else:
            self.project_service.set_dirty(dirty)
        self.update_window_title()
        self.update_save_ass_button()

    def update_window_title(self) -> None:
        """Обновление заголовка окна"""
        if self.project_controller:
            self.setWindowTitle(self.project_controller.get_window_title())
        else:
            self.setWindowTitle(self.project_service.get_window_title(self.data))
    
    def maybe_save(self) -> bool:
        """Проверка необходимости сохранения"""
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

    def on_project_name_changed(self, text: str) -> None:
        """Изменение имени проекта"""
        old_name = self.data.get("project_name", "")
        if text != old_name:
            # Используем команду для отмены действия
            command = UpdateProjectNameCommand(self.data, text)
            self.undo_stack.push(command)
            self.set_dirty()

    # === Методы работы с персонажами ===

    def on_main_table_item_changed(self, item: QTableWidgetItem) -> None:
        """Обработчик редактирования главной таблицы."""
        column = item.column()
        if column == 0:
            self.on_character_name_changed(item)
            return

        if column == 4:
            char_name = item.data(CHAR_NAME_ROLE)
            scope = item.data(SCOPE_ROLE) or ASSIGNMENT_SCOPE_GLOBAL
            if scope == item.data(PREVIOUS_SCOPE_ROLE):
                return
            item.setData(PREVIOUS_SCOPE_ROLE, scope)
            actor_item = self.main_table.item(item.row(), 5)
            actor_id = actor_item.data(ACTOR_ID_ROLE) if actor_item else None
            if char_name:
                self.update_assignment_scope_value(char_name, scope, actor_id)
            return

        if column == 5:
            char_name = item.data(CHAR_NAME_ROLE)
            actor_id = item.data(ACTOR_ID_ROLE)
            if actor_id == item.data(PREVIOUS_ACTOR_ID_ROLE):
                return
            item.setData(PREVIOUS_ACTOR_ID_ROLE, actor_id)
            scope_item = self.main_table.item(item.row(), 4)
            scope = (
                scope_item.data(SCOPE_ROLE)
                if scope_item
                else ASSIGNMENT_SCOPE_GLOBAL
            )
            if char_name:
                self.update_map_value(char_name, actor_id, scope)

    def on_main_table_cell_clicked(self, row: int, column: int) -> None:
        """Открыть предпросмотр персонажа по клику в колонке видео."""
        if column != 6:
            return
        item = self.main_table.item(row, column)
        char_name = item.data(CHAR_NAME_ROLE) if item else None
        if char_name:
            self.open_preview(char_name)
    
    def on_character_name_changed(self, item: QTableWidgetItem) -> None:
        """Обработчик изменения имени персонажа"""
        if item.column() != 0:
            return

        ep = self.ep_combo.currentData()
        if not ep:
            return

        old_name = item.data(Qt.UserRole)
        new_name = item.text().strip()

        if new_name == old_name or not new_name:
            return

        # Используем команду для отмены действия
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

        # Инвалидируем кэш в episode_service
        self.episode_service.invalidate_episode(ep)

        # Обновляем открытые окна (телесуфлёр, превью)
        self._refresh_open_windows(ep)

        item.setData(Qt.UserRole, new_name)
        self.character_names_changed[ep] = True
        self.update_save_ass_button()
        self.refresh_actor_list()
        self.set_dirty(True)

    def _refresh_open_windows(self, ep: str) -> None:
        """Обновление открытых окон после изменений"""
        # Обновляем превью, если открыто
        if hasattr(self, 'preview_window') and self.preview_window:
            self.preview_window.update_preview()

        # Обновляем телесуфлёр, если открыт
        if hasattr(self, 'teleprompter_window') and self.teleprompter_window:
            self.teleprompter_window.refresh_episode_data()
    
    def update_save_ass_button(self) -> None:
        """Совместимость со старым UI сохранения ASS/SRT."""
        pass

    def _reset_character_stats_panel(self) -> None:
        """Сброс панели статистики персонажа."""
        if not hasattr(self, "lbl_character_stats_name"):
            return
        self.lbl_character_stats_name.setText("Выберите персонажа")
        self.lbl_character_stats_totals.setText("Колец: -\nСлов: -")
        self.txt_character_stats_episodes.setPlainText("")

    def update_selected_character_stats(self) -> None:
        """Обновить статистику выбранного персонажа в правой панели."""
        selected_items = self.main_table.selectedItems()
        if not selected_items:
            self._reset_character_stats_panel()
            return

        row = min(item.row() for item in selected_items)
        name_item = self.main_table.item(row, 0)
        if not name_item:
            self._reset_character_stats_panel()
            return

        self.update_character_stats_panel(
            name_item.data(Qt.UserRole) or name_item.text()
        )

    def update_character_stats_panel(self, char_name: str) -> None:
        """Показать серии, кольца и слова для персонажа."""
        stats = self._calculate_character_project_stats(char_name)
        self.lbl_character_stats_name.setText(char_name)
        self.lbl_character_stats_totals.setText(
            f"Колец: {stats['rings']}\nСлов: {stats['words']}"
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
        """Посчитать статистику персонажа по всем сериям."""
        result: Dict[str, Any] = {
            "rings": 0,
            "words": 0,
            "episodes": []
        }
        export_service = ExportService(self.data)

        for ep in sorted(
            self.data.get("episodes", {}).keys(),
            key=lambda value: int(value) if str(value).isdigit() else 0
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

    # === Методы работы с проектом ===

    def save_project(self) -> bool:
        """Сохранение проекта"""
        if not self.project_controller:
            return False
        
        if self.project_controller.get_current_project_path():
            result = self.project_controller.save_project()
            if result:
                self.current_project_path = self.project_controller.get_current_project_path()
                self.update_window_title()
            return result
        return self.save_project_as()

    def save_project_as(self) -> bool:
        """Сохранение проекта как..."""
        if not self.project_controller:
            return False
        
        path, _ = QFileDialog.getSaveFileName(
            self, "Сохранить", "", "*.json"
        )
        if path:
            result = self.project_controller.save_project_as(path)
            self.current_project_path = self.project_controller.get_current_project_path()
            self.update_window_title()
            return result
        return False

    def load_project_dialog(self) -> None:
        """Диалог загрузки проекта"""
        if not self.project_controller:
            return
        
        if self.project_controller.maybe_save(self):
            path, _ = QFileDialog.getOpenFileName(
                self, "Открыть", "", "*.json"
            )
            if path:
                self._load_from_path(path)

    def _load_from_path(self, path: str) -> None:
        """Загрузка из файла"""
        if not self.project_controller:
            return
        
        try:
            data = self.project_controller.load_project(path)
            if not data:
                return
            
            self.current_project_path = self.project_controller.get_current_project_path()

            # Обновляем ссылку на данные в контроллере актёров
            if self.actor_controller:
                self.actor_controller.data_ref = self.data

            # Временно отключаем сигнал, чтобы не устанавливать dirty флаг
            self.proj_edit.blockSignals(True)
            self.proj_edit.setText(self.project_service.get_project_name(self.data))
            self.proj_edit.blockSignals(False)

            logger.info(f"Project loaded from {path}")
            logger.info(f"Actors count: {len(self.data.get('actors', {}))}")
            logger.info(f"Global map count: {len(self.data.get('global_map', {}))}")

            # Очищаем кэш загруженных эпизодов и статистику
            self.data["loaded_episodes"] = {}
            self.current_ep_stats = []
            self.episode_service.clear_cache()

            self.refresh_actor_list()
            self.update_ep_list()

        except Exception as e:
            log_exception(logger, "Load failed", e)
            QMessageBox.critical(
                self, "Ошибка", f"Не удалось загрузить проект: {e}"
            )
            return

        # Очищаем стек отмены при загрузке нового проекта
        self.undo_stack.clear()

        # Обновляем отображение папки проекта
        self._update_project_folder_button()

        # Сканируем папку проекта если она есть
        self._scan_project_folder()
        self._prompt_working_text_migration()

    def _update_project_folder_button(self) -> None:
        """Обновление состояния кнопки папки проекта"""
        folder = self.project_folder_service.get_project_folder(self.data)
        if folder:
            folder_name = os.path.basename(folder)
            self.btn_folder.setText("📁 Папка ✓")
            self.btn_folder.setToolTip(f"Папка проекта: {folder_name}\n{folder}")
        else:
            self.btn_folder.setText("📁 Папка")
            self.btn_folder.setToolTip("Установить папку проекта")

    def _scan_project_folder(self) -> None:
        """Сканирование папки проекта и связывание файлов"""
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
        """Проверить, есть ли рабочий текст серии на диске."""
        text_path = self.data.get("episode_texts", {}).get(str(ep))
        return bool(text_path and os.path.exists(text_path))

    def _episodes_needing_working_texts(self) -> List[str]:
        """Список серий, для которых рабочий текст ещё не создан."""
        episodes = self.data.get("episodes", {})
        return [
            str(ep)
            for ep, path in episodes.items()
            if (
                not self._episode_text_exists(str(ep)) and
                self._is_subtitle_source_path(path)
            )
        ]

    def _is_subtitle_source_path(self, path: str) -> bool:
        """Проверить, похож ли путь на исходный файл субтитров."""
        return os.path.splitext(path or "")[1].lower() in {'.ass', '.srt'}

    def _prompt_working_text_migration(self) -> None:
        """Предложить создать рабочие тексты для проекта старого формата."""
        missing_episodes = self._episodes_needing_working_texts()
        if not missing_episodes:
            return

        msg = QMessageBox(self)
        msg.setWindowTitle("Рабочие тексты")
        msg.setIcon(QMessageBox.Question)
        msg.setText(
            "Этот проект использует старый формат текстов.\n\n"
            "Можно создать рабочие тексты из найденных ASS/SRT-файлов сейчас. "
            "Если часть файлов была перенесена, их можно будет найти позже через менеджер файлов проекта."
        )
        create_button = msg.addButton(
            "Создать для найденных серий",
            QMessageBox.AcceptRole
        )
        msg.addButton("Позже", QMessageBox.RejectRole)
        msg.exec()

        if msg.clickedButton() == create_button:
            self.create_missing_working_texts(missing_episodes)

    def create_missing_working_texts(
        self,
        episodes: Optional[List[str]] = None
    ) -> Tuple[int, int]:
        """Создать рабочие тексты для серий, где найдены исходные субтитры."""
        target_episodes = episodes or self._episodes_needing_working_texts()
        created_count = 0
        skipped_count = 0

        for ep in target_episodes:
            path = self.data.get("episodes", {}).get(str(ep), "")
            if (
                not path or
                not self._is_subtitle_source_path(path) or
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

    def set_project_folder_dialog(self) -> None:
        """Диалог установки папки проекта"""
        current_folder = self.project_folder_service.get_project_folder(self.data)
        
        folder = QFileDialog.getExistingDirectory(
            self,
            "Выберите папку проекта",
            current_folder or ""
        )
        
        if folder:
            # Используем команду для отмены действия
            command = SetProjectFolderCommand(self.data, folder)
            self.undo_stack.push(command)
            
            # Устанавливаем папку
            self.project_folder_service.set_project_folder(self.data, folder)
            
            # Обновляем UI
            self._update_project_folder_button()
            self._scan_project_folder()
            self.set_dirty()

    def clear_project_folder(self) -> None:
        """Очистка папки проекта"""
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
            # Используем команду для отмены действия
            command = SetProjectFolderCommand(self.data, None)
            self.undo_stack.push(command)
            
            # Очищаем папку
            self.project_folder_service.clear_project_folder(self.data)
            
            # Обновляем UI
            self._update_project_folder_button()
            self.set_dirty()

    def _on_undo_stack_change(self) -> None:
        """Обработчик изменений стека отмены"""
        self.btn_undo.setEnabled(self.undo_stack.can_undo())
        self.btn_redo.setEnabled(self.undo_stack.can_redo())

    def undo(self) -> None:
        """Отмена последнего действия"""
        if self.undo_stack.undo():
            self.refresh_actor_list()
            self.refresh_main_table()
            self.set_dirty()

    def redo(self) -> None:
        """Повтор отменённого действия"""
        if self.undo_stack.redo():
            self.refresh_actor_list()
            self.refresh_main_table()
            self.set_dirty()

    # === Методы работы с сериями ===
    
    def on_header_clicked(self, index: int) -> None:
        """Клик по заголовку таблицы"""
        if index > 3:
            return
        if self.sort_col == index:
            self.sort_desc = not self.sort_desc
        else:
            self.sort_col = index
            self.sort_desc = True
        self.refresh_main_table()
    
    def add_actor_dialog(self) -> None:
        """Диалог добавления актёра"""
        if self.actor_controller:
            name: str
            ok: bool
            name, ok = QInputDialog.getText(self, "Новый актер", "Имя:")
            if ok and name:
                dialog = CustomColorDialog(self)
                if dialog.exec():
                    # Используем команду для отмены действия
                    actor_id = str(datetime.now().timestamp())
                    command = AddActorCommand(
                        self.data["actors"],
                        actor_id,
                        name,
                        dialog.selected_color
                    )
                    self.undo_stack.push(command)
                    self.actor_controller.refresh()
                    self.refresh_main_table()
                    self.set_dirty()

    def on_actor_renamed(self, item: QTableWidgetItem) -> None:
        """Переименование актёра"""
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

                # Используем команду для отмены действия
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

    def on_actor_color_clicked(self, aid: str) -> None:
        """Клик по цвету актёра"""
        if self.actor_controller:
            dialog = CustomColorDialog(self)
            if dialog.exec() and dialog.selected_color:
                # Используем команду для отмены действия
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
        """Диалог удаления актёра"""
        if not self.actor_controller:
            return

        # Получаем выбранную строку
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

        # Проверяем, есть ли у актёра роли
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
            # Используем команду для отмены действия
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
        """Установка видео для серии"""
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
                
                # Извлекаем FPS из видео и обновляем настройки
                fps = get_video_fps(path)
                self.data["replica_merge_config"]["fps"] = fps
                self.episode_service.set_fps(fps)
                
                self.set_dirty()
    
    def change_episode(self) -> None:
        """Смена серии"""
        ep: Optional[str] = self.ep_combo.currentData()
        if not ep:
            return

        lines = self.get_episode_lines(ep)
        if lines:
            self._recalculate_episode_stats(lines)
            self._display_episode_lines(lines)
            self.table_stack.setCurrentIndex(0)
            self.refresh_main_table()
            self.update_save_ass_button()
            return

        self.table_stack.setCurrentIndex(1)

        # При смене эпизода не сбрасываем флаг text_changes,
        # т.к. он нужен для отображения состояния кнопки

    def _display_episode_lines(self, lines: List[Dict[str, Any]]) -> None:
        """Отображение загруженных строк эпизода в таблице"""
        # Этот метод используется для DOCX импорта, когда данные уже в кэше
        pass  # Данные уже в main_table через refresh_main_table

    def _recalculate_episode_stats(self, lines: List[Dict[str, Any]]) -> None:
        """
        Пересчёт статистики эпизода из загруженных реплик.

        Args:
            lines: Список реплик эпизода
        """
        from collections import defaultdict

        char_data: Dict[str, Dict[str, Any]] = defaultdict(
            lambda: {"lines": 0, "raw": []}
        )

        # Собираем данные по персонажам
        for line in lines:
            char = line.get('char', '')
            if char:
                char_data[char]["lines"] += 1
                char_data[char]["raw"].append(line)

        # Вычисляем статистику
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
        """Парсинг эпизода и получение статистики"""
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
        """Создание рабочего текста эпизода после импорта."""
        if not lines:
            return

        self.script_text_service.create_episode_text(
            self.data,
            ep,
            path,
            lines,
            self.data.get("replica_merge_config", {}),
            self.current_project_path
        )

    def _convert_imported_lines_for_cache(
        self,
        lines: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Нормализовать импортированные реплики для кэша приложения."""
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
        """Импорт ASS файлов"""
        if not paths:
            paths, _ = QFileDialog.getOpenFileNames(
                self, "ASS", "", "*.ass"
            )

        if paths:
            for path in paths:
                self._import_single_file(path)

            self.update_ep_list()

    def import_srt(self, paths: Optional[List[str]] = None) -> None:
        """Импорт SRT файлов"""
        if not paths:
            paths, _ = QFileDialog.getOpenFileNames(
                self, "SRT", "", "*.srt"
            )

        if paths:
            for path in paths:
                self._import_single_file(path)

            self.update_ep_list()

    def _import_single_file(self, path: str) -> None:
        """
        Импорт отдельного файла с автоопределением типа.

        Args:
            path: Путь к файлу
        """
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
            # Используем команду для отмены действия
            command = AddEpisodeCommand(
                self.data["episodes"],
                name,
                path
            )
            self.undo_stack.push(command)

            # Парсим файл в зависимости от расширения
            ext = os.path.splitext(path)[1].lower()
            if ext == '.srt':
                lines = self._parse_srt_episode(name, path)
            else:
                lines = self._parse_episode(name, path)

            self._create_working_text_for_episode(name, path, lines)

            self.set_dirty()

    def import_files(self, paths: Optional[List[str]] = None) -> None:
        """
        Импорт файлов с автоопределением типа (ASS/SRT/DOCX).

        Args:
            paths: Список путей к файлам (если None, открывается диалог)
        """
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
                # Для DOCX открываем диалог с настройками, передавая путь к файлу
                self.import_docx_with_dialog(path)

        self.update_ep_list()

    def import_docx_with_dialog(self, file_path: str) -> None:
        """
        Импорт DOCX файла с показом диалога настройки колонок.

        Args:
            file_path: Путь к DOCX файлу
        """
        from ui.dialogs import DocxImportDialog
        from core.commands import AddEpisodeCommand
        import re
        import os

        # Показываем диалог импорта с переданным файлом
        dialog = DocxImportDialog(self, file_path)
        if dialog.exec() != QDialog.Accepted:
            return

        # Получаем результат
        result = dialog.get_result()
        if not result:
            return

        # Генерируем номер эпизода
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

        # Сохраняем данные в эпизод
        lines = result['lines']
        episode_lines = self._convert_imported_lines_for_cache(lines)

        # Добавляем эпизод в данные
        command = AddEpisodeCommand(
            self.data["episodes"],
            name,
            file_path
        )
        self.undo_stack.push(command)

        # Сохраняем распарсенные данные в кэш loaded_episodes
        if "loaded_episodes" not in self.data:
            self.data["loaded_episodes"] = {}
        self.data["loaded_episodes"][name] = episode_lines

        # Также сохраняем в кэш episode_service для совместимости
        self.episode_service._loaded_episodes[name] = episode_lines

        self._create_working_text_for_episode(name, file_path, episode_lines)
        working_lines = self.script_text_service.load_episode_lines(
            self.data,
            name
        )
        if working_lines:
            self.data["loaded_episodes"][name] = working_lines

        # Устанавливаем статистику
        self.current_ep_stats = result['stats']

        # Обновляем UI
        self.update_ep_list()
        self.set_dirty()

        QMessageBox.information(
            self, "Импорт завершён",
            f"Импортировано {len(lines)} реплик из DOCX файла." +
            (f"\n({result.get('tables_count', 1)} таблиц(ы))" if result.get('tables_count', 1) > 1 else "")
        )

    def _parse_srt_episode(self, ep: str, path: str) -> List[Dict[str, Any]]:
        """Парсинг SRT эпизода и получение статистики"""
        stats: List[Dict[str, Any]]
        lines: List[Dict[str, Any]]
        stats, lines = self.episode_service.parse_srt_file(path)
        self.current_ep_stats = stats
        return lines

    def import_docx(self, paths: Optional[List[str]] = None) -> None:
        """
        Импорт DOCX файлов с гибкой настройкой колонок.

        Args:
            paths: Список путей к файлам (если None, открывается диалог)
        """
        from ui.dialogs import DocxImportDialog
        from core.commands import AddEpisodeCommand
        import re
        import os

        # Для DOCX всегда показываем полный диалог с настройками
        dialog = DocxImportDialog(self)
        if dialog.exec() != QDialog.Accepted:
            return

        # Получаем результат
        result = dialog.get_result()
        if not result:
            return

        # Генерируем номер эпизода
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

        # Сохраняем данные в эпизод
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

        # Добавляем эпизод в данные
        command = AddEpisodeCommand(
            self.data["episodes"],
            name,
            docx_path
        )
        self.undo_stack.push(command)

        # Сохраняем распарсенные данные в кэш loaded_episodes
        if "loaded_episodes" not in self.data:
            self.data["loaded_episodes"] = {}
        self.data["loaded_episodes"][name] = episode_lines

        # Также сохраняем в кэш episode_service для совместимости
        self.episode_service._loaded_episodes[name] = episode_lines

        self._create_working_text_for_episode(name, docx_path, episode_lines)
        working_lines = self.script_text_service.load_episode_lines(
            self.data,
            name
        )
        if working_lines:
            self.data["loaded_episodes"][name] = working_lines

        # Устанавливаем статистику
        self.current_ep_stats = result['stats']

        # Обновляем UI
        self.update_ep_list()
        self.set_dirty()

        QMessageBox.information(
            self, "Импорт завершён",
            f"Импортировано {len(lines)} реплик из DOCX файла." +
            (f"\n({result.get('tables_count', 1)} таблиц(ы))" if result.get('tables_count', 1) > 1 else "")
        )

    def relink_file(self) -> None:
        """Перепривязка файла"""
        ep: Optional[str] = self.ep_combo.currentData()
        path: str
        path, _ = QFileDialog.getOpenFileName(
            self, "Файл", "", "Subtitle Files (*.ass *.srt)"
        )
        if path:
            self.data["episodes"][ep] = path
            self.change_episode()
            self.set_dirty()

    def update_map(
        self,
        char_name: str,
        actor_combo: QComboBox,
        scope_combo: Optional[QComboBox] = None
    ) -> None:
        """Обновление маппинга персонаж-актёр"""
        aid = actor_combo.currentData()
        scope = (
            scope_combo.currentData()
            if scope_combo is not None
            else ASSIGNMENT_SCOPE_GLOBAL
        )
        self.update_map_value(char_name, aid, scope)

    def update_map_value(
        self,
        char_name: str,
        actor_id: Optional[str],
        scope: str
    ) -> None:
        """Обновление назначения персонажа из лёгкой табличной ячейки."""
        ep = self.ep_combo.currentData()
        target_map = get_assignment_map(self.data, scope, ep)
        stored_aid = (
            LOCAL_UNASSIGNED_ACTOR_ID
            if scope == ASSIGNMENT_SCOPE_EPISODE and actor_id is None
            else actor_id
        )
        # Используем команду для отмены действия
        command = AssignActorToCharacterCommand(
            target_map,
            char_name,
            stored_aid
        )
        self.undo_stack.push(command)
        self.refresh_actor_list()
        self.set_dirty(True)

    def update_assignment_scope(
        self,
        char_name: str,
        scope_combo: QComboBox,
        actor_combo: QComboBox
    ) -> None:
        """Переключение назначения персонажа между проектом и серией."""
        self.update_assignment_scope_value(
            char_name,
            scope_combo.currentData(),
            actor_combo.currentData()
        )

    def update_assignment_scope_value(
        self,
        char_name: str,
        scope: str,
        actor_id: Optional[str]
    ) -> None:
        """Переключение области назначения из лёгкой табличной ячейки."""
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
        self.set_dirty(True)

    def _update_main_table_assignment_display(self, char_name: str) -> None:
        """Обновить отображение актёра после смены области назначения."""
        ep = self.ep_combo.currentData()
        actor_id = get_actor_for_character(self.data, char_name, ep)
        actor_name = (
            self.data.get("actors", {}).get(actor_id, {}).get("name", "-")
            if actor_id
            else "-"
        )

        self.main_table.blockSignals(True)
        try:
            for row in range(self.main_table.rowCount()):
                name_item = self.main_table.item(row, 0)
                if not name_item:
                    continue
                if (name_item.data(CHAR_NAME_ROLE) or name_item.text()) != char_name:
                    continue

                actor_item = self.main_table.item(row, 5)
                if actor_item:
                    actor_item.setData(ACTOR_ID_ROLE, actor_id)
                    actor_item.setData(PREVIOUS_ACTOR_ID_ROLE, actor_id)
                    actor_item.setText(actor_name)
                    self._apply_actor_color_to_item(actor_item, actor_id)
                break
        finally:
            self.main_table.blockSignals(False)

    def _apply_actor_color_to_item(
        self,
        item: QTableWidgetItem,
        actor_id: Optional[str]
    ) -> None:
        """Подкрасить ячейку актёра мягким цветом из базы актёров."""
        if not actor_id:
            item.setBackground(QBrush())
            item.setToolTip("Актёр не назначен")
            return

        actor = self.data.get("actors", {}).get(actor_id, {})
        color = QColor(actor.get("color", ""))
        if not color.isValid():
            item.setBackground(QBrush())
            item.setToolTip(actor.get("name", actor_id))
            return

        color.setAlpha(72)
        item.setBackground(QBrush(color))
        item.setToolTip(
            f"{actor.get('name', actor_id)}\nЦвет актёра: {color.name()}"
        )
    
    def refresh_main_table(self) -> None:
        """Обновление главной таблицы"""
        self.main_table.blockSignals(True)
        self.main_table.setRowCount(0)
        
        query = self.search_edit.text().lower()
        only_unassigned = self.filter_unassigned.isChecked()
        
        keys = ["name", "lines", "rings", "words"]
        sorted_stats = sorted(
            self.current_ep_stats,
            key=lambda x: x[keys[self.sort_col]],
            reverse=self.sort_desc
        )
        
        for stat in sorted_stats:
            if query and query not in stat["name"].lower():
                continue
            
            ep = self.ep_combo.currentData()
            actor_id = get_actor_for_character(self.data, stat["name"], ep)
            is_assigned = actor_id is not None
            if only_unassigned and is_assigned:
                continue
            
            row = self.main_table.rowCount()
            self.main_table.insertRow(row)
            
            name_item = QTableWidgetItem(stat["name"])
            name_item.setFlags(
                name_item.flags() | Qt.ItemIsEditable
            )
            name_item.setData(Qt.UserRole, stat["name"])
            self.main_table.setItem(row, 0, name_item)
            
            self.main_table.setItem(
                row, 1, QTableWidgetItem(str(stat["lines"]))
            )
            self.main_table.setItem(
                row, 2, QTableWidgetItem(str(stat["rings"]))
            )
            self.main_table.setItem(
                row, 3, QTableWidgetItem(str(stat["words"]))
            )

            scope = get_assignment_scope(self.data, stat["name"], ep)
            scope_item = QTableWidgetItem(
                "Серия"
                if scope == ASSIGNMENT_SCOPE_EPISODE
                else "Глобально"
            )
            scope_item.setData(CHAR_NAME_ROLE, stat["name"])
            scope_item.setData(SCOPE_ROLE, scope)
            scope_item.setData(PREVIOUS_SCOPE_ROLE, scope)
            self.main_table.setItem(row, 4, scope_item)

            actor_name = (
                self.data["actors"].get(actor_id, {}).get("name", "-")
                if actor_id
                else "-"
            )
            actor_item = QTableWidgetItem(actor_name)
            actor_item.setData(CHAR_NAME_ROLE, stat["name"])
            actor_item.setData(ACTOR_ID_ROLE, actor_id)
            actor_item.setData(PREVIOUS_ACTOR_ID_ROLE, actor_id)
            self._apply_actor_color_to_item(actor_item, actor_id)
            self.main_table.setItem(row, 5, actor_item)

            video_item = QTableWidgetItem("📺")
            video_item.setTextAlignment(Qt.AlignCenter)
            video_item.setToolTip("Открыть предпросмотр персонажа")
            video_item.setData(CHAR_NAME_ROLE, stat["name"])
            video_item.setFlags(
                video_item.flags() & ~Qt.ItemIsEditable
            )
            self.main_table.setItem(row, 6, video_item)
        
        self.main_table.blockSignals(False)

    def refresh_actor_list(self) -> None:
        """Обновление списка актёров"""
        logger.info(f"refresh_actor_list: actor_controller={self.actor_controller is not None}, actors={len(self.data.get('actors', {}))}")
        
        if self.actor_controller:
            self.actor_controller.refresh()
        else:
            # Fallback: если контроллер ещё не создан, используем старую логику
            logger.warning("refresh_actor_list: actor_controller is None, using fallback")
            self.actor_table.blockSignals(True)
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

                # Колонка 0: Актер
                item: QTableWidgetItem = QTableWidgetItem(info["name"])
                item.setData(Qt.UserRole, aid)
                self.actor_table.setItem(row, 0, item)

                # Колонка 1: Роли (кнопка)
                btn: QPushButton = QPushButton(f"Роли ({len(actor_roles[aid])})")
                self.actor_table.setCellWidget(row, 1, wrap_widget(btn))

                # Колонка 2: Цвет
                color_item: QTableWidgetItem = QTableWidgetItem()
                color_item.setBackground(QColor(info["color"]))
                self.actor_table.setItem(row, 2, color_item)

            self.actor_table.blockSignals(False)
            logger.info(f"refresh_actor_list: fallback loaded {self.actor_table.rowCount()} actors")

    def rename_episode(self) -> None:
        """Переименование серии"""
        old: Optional[str] = self.ep_combo.currentData()
        new_name: str
        ok: bool
        new_name, ok = QInputDialog.getText(
            self, "Rename", "New name:", text=str(old)
        )
        if ok and new_name and new_name != old:
            # Используем команду для отмены действия
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
        """Диалог удаления серии"""
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
        """Удаление серии из проекта"""
        # Используем команду для отмены действия
        command = DeleteEpisodeCommand(
            self.data["episodes"],
            self.data.get("video_paths", {}),
            self.data.get("loaded_episodes", {}),
            ep,
            self.data.get("episode_actor_map", {})
        )
        self.undo_stack.push(command)

        # Очищаем кэш в episode service
        self.episode_service.invalidate_episode(ep)

        # Обновляем список серий
        self.update_ep_list()

        # Сохраняем изменения
        self.set_dirty()

        QMessageBox.information(
            self, "Готово", f"Серия {ep} удалена из проекта."
        )
    
    def update_ep_list(self, select: Optional[str] = None) -> None:
        """Обновление списка серий"""
        self.ep_combo.blockSignals(True)
        self.ep_combo.clear()

        ep: str
        for ep in sorted(
            self.data["episodes"].keys(),
            key=lambda x: int(x) if x.isdigit() else 0
        ):
            self.ep_combo.addItem(f"Серия {ep}", ep)

        if select:
            self.ep_combo.setCurrentIndex(
                self.ep_combo.findData(select)
            )
        elif self.ep_combo.count() > 0:
            self.ep_combo.setCurrentIndex(0)

        self.ep_combo.blockSignals(False)
        self.change_episode()

    # === Экспорт ===

    def run_unified_export(self) -> None:
        """Запуск экспорта"""
        do_html: bool = self.chk_exp_html.isChecked()
        do_xls: bool = self.chk_exp_xls.isChecked()

        if not (do_html or do_xls):
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

        if is_all or (do_html and do_xls):
            dest = QFileDialog.getExistingDirectory(
                self, "Выберите папку"
            )
            if dest:
                self._execute_batch_export(
                    episodes, do_html, do_xls, dest
                )
        else:
            ep = list(episodes.keys())[0]
            if do_html:
                self.export_to_html(ep)
            else:
                self.export_to_excel(ep)

    def _execute_batch_export(
        self,
        episodes: Dict[str, str],
        do_html: bool,
        do_xls: bool,
        folder: str
    ) -> None:
        """Пакетный экспорт через ExportService с прогрессбаром"""
        export_service = ExportService(self.data)
        
        # Создаём прогрессбар
        progress = QProgressDialog(self)
        progress.setWindowTitle("Экспорт")
        progress.setLabelText("Экспорт серий...")
        progress.setRange(0, len(episodes))
        progress.setValue(0)
        progress.setCancelButton(None)  # Без кнопки отмены
        progress.setWindowModality(Qt.WindowModal)
        progress.show()
        
        # Callback для обновления прогресса
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
            folder=folder,
            progress_callback=progress_callback
        )
        
        progress.close()
        
        if success:
            logger.info(message)
            QMessageBox.information(self, "Экспорт завершён", message)
        else:
            QMessageBox.critical(self, "Ошибка экспорта", message)

    def _create_excel_book(
        self,
        ep: str,
        processed: List[Dict[str, Any]],
        cfg: Optional[Dict[str, Any]] = None
    ) -> Any:
        """Создание Excel книги (ус��арело, использовать ExportService)"""
        export_service = ExportService(self.data)
        return export_service.create_excel_book(ep, processed, cfg)

    def export_to_excel(self, ep: str) -> None:
        """Экспорт в Excel"""
        if not self.export_controller:
            return
        
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Excel", f"Script_{ep}.xlsx", "*.xlsx"
        )

        if path:
            success, message = self.export_controller.export_to_excel(ep, path)
            if success:
                if sys.platform == 'win32':
                    os.startfile(path)
                else:
                    os.system(f'open "{path}"')
            else:
                QMessageBox.warning(self, "Ошибка", message)

    def export_to_html(self, ep: str) -> None:
        """Экспорт в HTML"""
        if not self.export_controller:
            return
        
        path, _ = QFileDialog.getSaveFileName(
            self, "Save HTML", f"Script_{ep}.html", "*.html"
        )

        if path:
            success, message = self.export_controller.export_to_html(ep, path)
            if success:
                if sys.platform == 'win32':
                    os.startfile(path)
                else:
                    os.system(f'open "{path}"')
            else:
                QMessageBox.warning(self, "Ошибка", message)

    def save_episode_to_ass(
        self,
        ep_num: str,
        target_path: Optional[str] = None
    ) -> bool:
        """Сохранение серии в ASS/SRT отключено в UI."""
        QMessageBox.warning(
            self,
            "Сохранение отключено",
            "Запись изменений обратно в ASS/SRT отключена.\n"
            "Редактируйте рабочий текст, он сохраняется в JSON автоматически."
        )
        return False



    # === Диалоги и окна ===
    
    def open_preview(self, char: Optional[str]) -> None:
        """Открытие предпросмотра видео"""
        ep = self.ep_combo.currentData()
        lines = self.get_episode_lines(ep)
        
        if char:
            lines = [l for l in lines if l['char'] == char]
        
        vp = self.data.get("video_paths", {}).get(ep)
        
        if not vp or not os.path.exists(vp):
            self.set_episode_video()
            vp = self.data.get("video_paths", {}).get(ep)
        
        if vp:
            from .video import VideoPreviewWindow

            VideoPreviewWindow(vp, lines, ep, self).exec()
    
    def get_episode_lines(self, ep: str) -> List[Dict[str, Any]]:
        """Получение строк серии из рабочего текста проекта."""
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
        """Получение строк SRT серии"""
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
        source_path: Optional[str] = None
    ) -> bool:
        """Пересоздать рабочий текст эпизода из ASS/SRT."""
        path = source_path or self.data.get("episodes", {}).get(ep, "")

        if not path or not os.path.exists(path):
            QMessageBox.warning(
                self,
                "Ошибка",
                "Файл субтитров не найден."
            )
            return False

        if not self._build_working_text_from_source(ep, path):
            QMessageBox.warning(
                self,
                "Ошибка",
                "Не удалось получить реплики из файла субтитров."
            )
            return False

        self.get_episode_lines(ep)
        self.set_dirty(True)

        QMessageBox.information(
            self,
            "Готово",
            f"Рабочий текст серии {ep} пересоздан."
        )
        return True

    def _build_working_text_from_source(self, ep: str, path: str) -> bool:
        """Создать рабочий текст серии из исходного ASS/SRT без UI-сообщений."""
        try:
            ext = os.path.splitext(path)[1].lower()
            if ext == '.srt':
                stats, lines = self.episode_service.parse_srt_file(path)
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
        """Показать сводку проекта"""
        SummaryDialog(self.data, None, self).exec()

    def show_episode_summary(self) -> None:
        """Показать сводку серии"""
        ep: Optional[str] = self.ep_combo.currentData()
        if ep:
            SummaryDialog(self.data, ep, self).exec()

    def edit_roles(
        self,
        aid: str,
        name: str,
        roles: List[str]
    ) -> None:
        """Просмотр ролей актёра"""
        role_stats = self._get_actor_role_stats(aid, roles)
        ActorRolesDialog(name, roles, self, role_stats).exec()

    def _get_actor_role_stats(
        self,
        actor_id: str,
        roles: List[str]
    ) -> List[Dict[str, Any]]:
        """Посчитать кольца и слова по персонажам актёра."""
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
        """Открытие единого окна настроек на вкладке экспорта."""
        self.open_settings(initial_tab="export")

    def open_settings(self, initial_tab: str = "export") -> None:
        """Открытие единого окна настроек"""
        dialog = SettingsDialog(self.data, self, initial_tab=initial_tab)
        if dialog.exec():
            settings = dialog.get_settings()

            self.data["export_config"] = settings["export_config"]
            self.data["replica_merge_config"] = settings["replica_merge_config"]
            self.data["prompter_config"] = settings["prompter_config"]
            self.data["docx_import_config"] = settings["docx_import_config"]

            self.global_settings["export_config"] = self.data["export_config"]
            self.global_settings["replica_merge_config"] = (
                self.data["replica_merge_config"]
            )
            self.global_settings["prompter_config"] = self.data["prompter_config"]
            self.global_settings["docx_import_config"] = (
                self.data["docx_import_config"]
            )
            self.global_settings_service.save_settings(self.global_settings)

            self.episode_service.set_merge_gap_from_config(
                self.data["replica_merge_config"]
            )

            self.change_episode()
            self.set_dirty()

    def open_global_search(self) -> None:
        """Открытие глобального поиска"""
        GlobalSearchDialog(self.data, self).exec()

    def open_live_preview(self) -> None:
        """Открытие живого предпросмотра"""
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
        """Открытие телесуфлёра"""
        ep: Optional[str] = self.ep_combo.currentData()
        if not ep:
            QMessageBox.information(self, "Инфо", "Выберите серию.")
            return

        if not self.get_episode_lines(ep):
            QMessageBox.warning(
                self,
                "Рабочий текст не найден",
                "Для этой серии нет рабочего текста.\n\n"
                "Откройте «Файлы проекта» и создайте рабочий текст из субтитров."
            )
            return

        if self.teleprompter_window is not None:
            self.teleprompter_window.close()

        self.teleprompter_window = TeleprompterWindow(self, ep)
        self.teleprompter_window.show()

    def _apply_global_settings_to_project(self) -> None:
        """Применение глобальных настроек к текущему проекту"""
        # Применяем глобальные настройки экспорта
        if self.global_settings.get('export_config'):
            self.data["export_config"].update(
                self.global_settings['export_config']
            )
        
        # Применяем глобальные настройки телесуфлёра
        if self.global_settings.get('prompter_config'):
            self.data["prompter_config"].update(
                self.global_settings['prompter_config']
            )
        
        # Применяем глобальные настройки объединения
        if self.global_settings.get('replica_merge_config'):
            self.data["replica_merge_config"].update(
                self.global_settings['replica_merge_config']
            )
            # Обновляем episode_service
            self.episode_service.set_merge_gap_from_config(
                self.data["replica_merge_config"]
            )

        if self.global_settings.get('docx_import_config'):
            self.data.setdefault(
                "docx_import_config",
                deepcopy(DEFAULT_DOCX_IMPORT_CONFIG),
            )
            self.data["docx_import_config"].update(
                self.global_settings['docx_import_config']
            )

    def save_global_prompter_settings(self, config: Dict[str, Any]) -> None:
        """Сохранение настроек телесуфлёра в глобальные"""
        self.global_settings_service.update_prompter_config(config)
        self.global_settings_service.save_settings(self.global_settings)

    def export_to_reaper_rpp(self) -> None:
        """Экспорт в Reaper RPP"""
        ep_num: Optional[str] = self.ep_combo.currentData()
        if not ep_num:
            QMessageBox.warning(self, "Ошибка", "Выберите серию.")
            return
        
        video_path = self.data["video_paths"].get(ep_num)
        dialog = ReaperExportDialog(video_path, self)
        
        if dialog.exec() != QDialog.Accepted:
            return
        
        use_video, use_regions = dialog.get_options()
        
        if use_video and video_path:
            video_path = os.path.abspath(video_path)
        
        default_name = (
            f"{self.data.get('project_name', 'Project')} - "
            f"Ep{ep_num}.rpp"
        )
        save_path, _ = QFileDialog.getSaveFileName(
            self, "Сохран��ть RPP", default_name, "Reaper Project (*.rpp)"
        )
        if not save_path:
            return
        
        lines = self.get_episode_lines(ep_num)
        if not lines:
            QMessageBox.warning(
                self,
                "Рабочий текст не найден",
                "Для этой серии нет рабочего текста.\n\n"
                "Откройте «Файлы проекта» и создайте рабочий текст из субтитров."
            )
            return

        export_service = ExportService(self.data)
        rpp_content = export_service.generate_reaper_rpp(
            ep_num,
            lines,
            merge_cfg=self.data.get("replica_merge_config", {}),
            video_path=video_path,
            use_video=use_video,
            use_regions=use_regions
        )
        
        try:
            with open(save_path, 'w', encoding='utf-8') as f:
                f.write(rpp_content)
            
            reply = QMessageBox.question(
                self,
                "Готово",
                "Проект создан. Открыть в Reaper?",
                QMessageBox.Yes | QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                if sys.platform == 'win32':
                    os.startfile(save_path)
                elif sys.platform == 'darwin':
                    os.system(f'open "{save_path}"')
                else:
                    os.system(f'xdg-open "{save_path}"')
        except Exception as e:
            log_exception(logger, "Error saving RPP", e)
            QMessageBox.critical(
                self, "Ошибка", f"Не удалось сохранить: {e}"
            )
    
    def switch_to_episode(self, ep_num: str) -> None:
        """Переключение на серию"""
        index = self.ep_combo.findData(ep_num)
        if index >= 0:
            self.ep_combo.setCurrentIndex(index)
    
    # === Drag & Drop ===
    
    def dragEnterEvent(self, event) -> None:
        """Обработка входа перетаскивания"""
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()
    
    def dropEvent(self, event) -> None:
        """Обработка сброса файлов"""
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
        """Закрытие приложения"""
        if self.maybe_save():
            event.accept()
        else:
            event.ignore()

    def show_about(self) -> None:
        """Показ диалога About"""
        QMessageBox.about(
            self,
            "О программе",
            "<h2>Dubbing Manager</h2>"
            "<p>Приложение для управления проектами дубляжа и озвучивания.</p>"
            "<p><b>Версия:</b> {}</p>"
            "<p><b>GitHub:</b> <a href='https://github.com/ScrapDnB/DubbingManager/'>ScrapDnB/DubbingManager</a></p>"
            "<p><b>Python:</b> {}.{}.{}</p>"
            "<p><b>PySide6:</b> {}</p>"
            "<p>© 2026 Юрий Романов</p>".format(
                APP_VERSION,
                sys.version_info.major,
                sys.version_info.minor,
                sys.version_info.micro,
                "6.10.2"
            )
        )

    def open_project_files_dialog(self) -> None:
        """Открытие диалога файлов проекта"""
        dialog = ProjectFilesDialog(self.data, self)
        dialog.exec()

    def open_project_health_dialog(self) -> None:
        """Открытие диалога проверки проекта"""
        dialog = ProjectHealthDialog(self.data, self)
        dialog.exec()

    def _on_files_changed(self) -> None:
        """Обработчик изменений в файлах проекта"""
        # Обновляем список эпизодов
        self.update_ep_list()
        
        # Обновляем таблицу
        self.change_episode()
        
        # Помечаем проект как изменённый
        self.set_dirty()
