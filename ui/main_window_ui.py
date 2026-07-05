"""Main-window layout construction."""

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QRadioButton,
    QStackedWidget,
    QTableView,
    QTableWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from config.constants import (
    ACTOR_PANEL_WIDTH,
    ABOUT_BTN_WIDTH,
    BTN_COMPOUND_ICON_WIDTH,
    BTN_RENAME_WIDTH,
    BTN_SAVE_ICON_WIDTH,
    DEFAULT_EXPORT_CONFIG,
    EPISODE_COMBO_MIN_WIDTH,
    EXPORT_PANEL_SPACING,
    MAIN_TABLE_COUNT_COL_WIDTH,
    MAIN_TABLE_SCOPE_COL_WIDTH,
    MAIN_TABLE_VIDEO_COL_WIDTH,
    PROJECT_FOLDER_BTN_WIDTH,
    SEARCH_EDIT_WIDTH,
    TOOLS_SIDEBAR_WIDTH,
)
from ui.controllers import ActorController
from ui.models import ActorComboDelegate, MainTableModel, ScopeComboDelegate
from ui.widgets import QuickSubtitleDropZone
from utils.helpers import customize_table


class MainWindowUiMixin:
    """Build the main window widget tree."""

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

        self.btn_export_project_archive = QPushButton("📦↑")
        self.btn_export_project_archive.setToolTip(
            "Экспортировать проект вместе с текстами"
        )
        self.btn_export_project_archive.clicked.connect(
            self.export_project_archive
        )
        top.addWidget(self.btn_export_project_archive)

        self.btn_import_project_archive = QPushButton("📦↓")
        self.btn_import_project_archive.setToolTip(
            "Импортировать проект вместе с текстами"
        )
        self.btn_import_project_archive.clicked.connect(
            self.import_project_archive
        )
        top.addWidget(self.btn_import_project_archive)

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

        self.btn_bulk_roles = QPushButton()
        self.btn_bulk_roles.clicked.connect(self.open_bulk_role_assignment_dialog)
        tools_sidebar_layout.addWidget(self.btn_bulk_roles)

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
        self.chk_exp_pdf = QCheckBox("PDF")
        self.chk_exp_pdf.setChecked(export_config.get("format_pdf", False))
        self.chk_exp_html.toggled.connect(self._update_export_format_config)
        self.chk_exp_xls.toggled.connect(self._update_export_format_config)
        self.chk_exp_docx.toggled.connect(self._update_export_format_config)
        self.chk_exp_pdf.toggled.connect(self._update_export_format_config)

        self.radio_cur = QRadioButton()
        self.radio_cur.setChecked(True)

        self.radio_all = QRadioButton()

        self.btn_run_export = QPushButton()
        self.btn_run_export.clicked.connect(self.run_unified_export)

        exp_lay.addWidget(self.chk_exp_html)
        exp_lay.addWidget(self.chk_exp_xls)
        exp_lay.addWidget(self.chk_exp_docx)
        exp_lay.addWidget(self.chk_exp_pdf)
        exp_lay.addSpacing(EXPORT_PANEL_SPACING)
        exp_lay.addWidget(self.radio_cur)
        exp_lay.addWidget(self.radio_all)
        exp_lay.addSpacing(EXPORT_PANEL_SPACING)
        exp_lay.addWidget(self.btn_run_export)

        bottom_panel.addWidget(self.exp_group)
        self.exp_group.setVisible(False)
        layout.addLayout(bottom_panel)
        self.retranslate_ui()
