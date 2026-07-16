"""Application constants."""

# =============================================================================
# Palette and Colors
# =============================================================================

MY_PALETTE = [
    "#D9775F", "#E46C0A", "#9B5333", "#C0504D", "#C4BD97",
    "#D4A017", "#938953", "#8A7F80", "#76923C", "#4F6228",
    "#31859B", "#669999", "#4F81BD", "#5B9BD5", "#2C4D75",
    "#708090", "#B65C72", "#8064A2", "#5F497A", "#7B3F61"
]

# =============================================================================
# Main Window UI Constants
# =============================================================================

PROJECT_FILE_EXTENSION = ".dub"
PROJECT_LEGACY_FILE_EXTENSION = ".json"
PROJECT_BACKUP_FILE_EXTENSION = ".dub_backup"
PROJECT_FILE_FILTER = (
    "Dubbing Manager Project (*.dub);;"
    "Dubbing Manager Backup (*.dub_backup);;"
    "Legacy JSON Project (*.json);;"
    "All Files (*)"
)

MAIN_WINDOW_WIDTH = 1350
MAIN_WINDOW_HEIGHT = 850

ACTOR_PANEL_WIDTH = 350
TOOLS_SIDEBAR_WIDTH = 250

SEARCH_EDIT_WIDTH = 160

# Buttons
EPISODE_COMBO_MIN_WIDTH = 120
BTN_RENAME_WIDTH = 42
BTN_ICON_WIDTH = 42
BTN_COMPOUND_ICON_WIDTH = 58
BTN_SAVE_ICON_WIDTH = 46
BTN_SAVE_ASS_WIDTH = 120

# Table
TABLE_ROW_HEIGHT = 32
VIDEO_BTN_WIDTH = 40
MAIN_TABLE_COUNT_COL_WIDTH = 72
MAIN_TABLE_SCOPE_COL_WIDTH = 130
MAIN_TABLE_VIDEO_COL_WIDTH = 64

# =============================================================================
# Teleprompter UI Constants
# =============================================================================

PROMPTER_WINDOW_WIDTH = 1200
PROMPTER_WINDOW_HEIGHT = 900
PROMPTER_FLOAT_WINDOW_WIDTH = 300
PROMPTER_FLOAT_WINDOW_HEIGHT = 440
EDIT_TEXT_DIALOG_WIDTH = 600
EDIT_TEXT_DIALOG_HEIGHT = 400

# macOS-specific handling
FLOAT_BTN_WIDTH = 280
FLOAT_BTN_HEIGHT = 50
FLOAT_BTN_Y_PREV = 380  # Back button in the upper slot.
FLOAT_BTN_Y_NEXT = 320  # Forward button in the lower slot.
FLOAT_EPISODE_LABEL_Y = 290
FLOAT_EPISODE_COMBO_Y = 260
FLOAT_EPISODE_COMBO_HEIGHT = 26
FLOAT_LABEL_Y = 235
FLOAT_LABEL_HEIGHT = 20
FLOAT_SCROLL_Y = 50
FLOAT_SCROLL_HEIGHT = 180
FLOAT_SCROLL_WIDTH = 280
FLOAT_TEXT_VIEW_WIDTH = 260
FLOAT_BTN_HIDE_WIDTH = 90
FLOAT_BTN_HIDE_HEIGHT = 30
FLOAT_BTN_HIDE_X = 105
FLOAT_BTN_HIDE_Y = 10
FLOAT_MARGIN_X = 10

PROMPTER_SETTINGS_PANEL_MIN_WIDTH = 320
PROMPTER_SIDE_PANEL_MIN_WIDTH = 320
PROMPTER_SETTINGS_WIDTH = 280
PROMPTER_NAV_BUTTON_MIN_WIDTH = 160

PROMPTER_V_SPLITTER_SIZES = [100, 800]
PROMPTER_H_SPLITTER_SIZES = [320, 900]
PROMPTER_SIDE_MIN_WIDTH = 200
PROMPTER_SIDE_MAX_WIDTH = 420
PROMPTER_SCENE_WIDTH = 850
PROMPTER_SCENE_CENTER_X = 425

PROMPTER_FONT_MIN_SIZE = 10
PROMPTER_FONT_TC_MAX = 150
PROMPTER_FONT_CHAR_MAX = 150
PROMPTER_FONT_ACTOR_MAX = 150
PROMPTER_FONT_TEXT_MAX = 300

PROMPTER_FOCUS_SLIDER_MAX = 100
PROMPTER_SCROLL_SMOOTHNESS_MAX = 100
PROMPTER_SCROLL_SMOOTHNESS_SCALE = 100

PROMPTER_TIMECODE_Y_CURSOR = 1000.0
PROMPTER_SCENE_EXTRA_HEIGHT = 1000

# =============================================================================
# Preview UI Constants
# =============================================================================

PREVIEW_WINDOW_WIDTH = 1200
PREVIEW_WINDOW_HEIGHT = 900
PREVIEW_SETTINGS_PANEL_WIDTH = 280

# =============================================================================
# Dialog UI Constants
# =============================================================================

DOCX_IMPORT_DIALOG_WIDTH = 900
DOCX_IMPORT_DIALOG_HEIGHT = 620
ACTOR_ROLES_DIALOG_WIDTH = 520
ACTOR_ROLES_DIALOG_HEIGHT = 420

# =============================================================================
# Video UI Constants
# =============================================================================

VIDEO_WINDOW_WIDTH = 1000
VIDEO_WINDOW_HEIGHT = 800
VIDEO_WIDGET_MIN_HEIGHT = 400

# =============================================================================
# Shared UI Constants
# =============================================================================

DEFAULT_MARGIN = 5
DEFAULT_SPACING = 4
HEADER_MARGIN = (8, 6, 8, 6)  # left, top, right, bottom
CONTENT_MARGIN = (8, 0, 8, 8)

PROJECT_BAR_SPACING = 20
PROJECT_FOLDER_BTN_WIDTH = 30
ABOUT_BTN_WIDTH = 30
EXPORT_PANEL_SPACING = 10

AUTOSAVE_INTERVAL_MS = 300000  # 5 minutes.
SCROLL_TIMEOUT_MS = 50

SCROLL_THRESHOLD_TOP = 50
SCROLL_THRESHOLD_BOTTOM = 160

FPS = 25

# =============================================================================
# Default Configuration
# =============================================================================

DEFAULT_PROMPTER_CONFIG = {
    "f_tc": 20,
    "f_char": 24,
    "f_actor": 18,
    "f_text": 36,
    "focus_ratio": 0.5,
    "is_mirrored": False,
    "show_header": False,
    "port_in": 8000,
    "port_out": 9000,
    "osc_enabled": False,
    "sync_in": True,
    "sync_out": False,
    "reaper_offset_enabled": False,
    "reaper_offset_seconds": -2.0,
    "key_prev": "Left",
    "key_next": "Right",
    "scroll_smoothness_slider": 18,
    "use_cocoa_float_window": True,
    "colors": {
        "bg": "#000000",
        "active_text": "#FFFFFF",
        "inactive_text": "#444444",
        "tc": "#888888",
        "actor": "#AAAAAA",
        "header_bg": "#111111",
        "header_text": "#00FF00"
    }
}

DEFAULT_EXPORT_CONFIG = {
    'format_html': True,
    'format_xls': False,
    'format_docx': False,
    'format_pdf': False,
    'layout_type': 'Таблица',
    'col_tc': True,
    'col_char': True,
    'col_actor': True,
    'col_text': True,
    'f_time': 21,
    'f_char': 20,
    'f_actor': 14,
    'f_text': 30,
    'table_width_time': 7.0,
    'table_width_char': 10.0,
    'table_width_actor': 8.5,
    'use_color': True,
    'soften_colors': True,
    'open_auto': True,
    'round_time': False,
    'time_display': 'range',
    'allow_edit': True,
    'highlight_negative_ids_export': [],
}

DEFAULT_REPLICA_MERGE_CONFIG = {
    'merge': True,
    'merge_gap': 120,  # Maximum frame gap for merging adjacent replicas.
    'p_short': 0.5,
    'p_long': 2.0,
    'fps': 25,  # Frame rate used for time conversion.
}

DEFAULT_ASS_IMPORT_CONFIG = {
    'split_character_names': True,
    'character_separator': ';',
    'strip_override_tags': True,
}

DEFAULT_SRT_IMPORT_CONFIG = {
    'detect_character_prefix': True,
    'character_separator': ':',
    'keep_multiline': True,
    'default_character': '',
}

# DOCX-specific handling
DEFAULT_DOCX_IMPORT_CONFIG = {
    'mapping': {},
    'time_separators': ['-', '–', '—', '|'],
    'header_mode': 'auto',
    'header_search_rows': 5,
    'minimum_header_matches': 2,
    'rows_to_skip': 0,
    'default_duration': 1.0,
    'field_priority': [
        'character', 'time_start', 'time_end', 'time_split', 'text'
    ],
    'aliases': {
        'character': [
            'персонаж', 'имя', 'роль', 'actor', 'character', 'char',
            'speaker', 'voice'
        ],
        'time_start': ['начало', 'старт', 'start', 'time start', 'in', 'from'],
        'time_end': ['конец', 'end', 'time end', 'out', 'to'],
        'time_split': ['тайминг', 'таймкод', 'время', 'timing', 'timecode', 'time'],
        'text': [
            'текст', 'реплика', 'фраза', 'text', 'replica', 'dialog',
            'speech', 'line'
        ],
    },
    'fallback_mapping': {
        'character': 0,
        'time_start': None,
        'time_end': None,
        'time_split': 1,
        'text': 2,
    },
}

DEFAULT_AUDIOBOOK_CONFIG = {
    "chapter_keywords": ["Глава", "Chapter"],
}

DEFAULT_BACKUP_CONFIG = {
    "enabled": True,
    "path_mode": "relative",
    "directory": ".backups",
    "interval_minutes": 5,
    "max_backups": 10,
}

DEFAULT_GLOBAL_SETTINGS = {
    'export_config': None,  # Initialized from DEFAULT_EXPORT_CONFIG.
    'prompter_config': None,  # Initialized from DEFAULT_PROMPTER_CONFIG.
    'replica_merge_config': None,  # Initialized from DEFAULT_REPLICA_MERGE_CONFIG.
    'ass_import_config': DEFAULT_ASS_IMPORT_CONFIG,
    'srt_import_config': DEFAULT_SRT_IMPORT_CONFIG,
    'docx_import_config': None,  # DOCX-specific handling
    'audiobook_config': DEFAULT_AUDIOBOOK_CONFIG,
    'backup_config': DEFAULT_BACKUP_CONFIG,
    'language': 'ru',
}

# Application version shown in the UI and build metadata.
APP_VERSION = "2.0.0-beta1"

# Project file format version used for compatibility migrations.
PROJECT_VERSION = "1.4"

# Folder name for Dubbing Manager working text JSON files.
SCRIPT_TEXT_DIR_NAME = "texts_dm"
