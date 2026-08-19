"""Application constants."""

from colorsys import hls_to_rgb, rgb_to_hls

# =============================================================================
# Palette and Colors
# =============================================================================

_ACTOR_PALETTE_BASE = [
    "#D9775F", "#E46C0A", "#9B5333", "#C0504D", "#C4BD97",
    "#D4A017", "#938953", "#8A7F80", "#76923C", "#4F6228",
    "#31859B", "#669999", "#4F81BD", "#5B9BD5", "#2C4D75",
    "#708090", "#B65C72", "#8064A2", "#5F497A", "#7B3F61"
]

# Evenly distributed colour families used for the generated rows. The original
# custom colours above remain first; these anchors keep the rest of the palette
# from clustering around muted browns, blues, and purples.
_ACTOR_PALETTE_FAMILIES = [
    "#D64545", "#E05A2A", "#E67E22", "#D89B00", "#C8A600",
    "#7EA72D", "#2F9E44", "#178F66", "#168C8C", "#1597B8",
    "#2E86C1", "#3973C6", "#4C5BC0", "#744DB7", "#9249A8",
    "#B54891", "#D64F7A", "#C74E61", "#9A623E", "#66717D",
]


def _build_actor_palette() -> list[str]:
    """Build a broad but cohesive set of stable actor colours."""
    # Preserve the original custom colours, then add seven rows spanning the
    # full colour wheel. The result remains 160 stable choices.
    palette = list(_ACTOR_PALETTE_BASE)
    for lightness in (0.33, 0.40, 0.47, 0.54, 0.61, 0.68, 0.75):
        for base in _ACTOR_PALETTE_FAMILIES:
            red = int(base[1:3], 16) / 255
            green = int(base[3:5], 16) / 255
            blue = int(base[5:7], 16) / 255
            hue, _, saturation = rgb_to_hls(red, green, blue)
            color_hue = hue
            while True:
                variant = hls_to_rgb(
                    color_hue,
                    lightness,
                    max(0.18, min(0.78, saturation * 0.9)),
                )
                color = "#{:02X}{:02X}{:02X}".format(
                    *(round(channel * 255) for channel in variant)
                )
                if color not in palette:
                    palette.append(color)
                    break
                # Very similar legacy bases can round to the same RGB value.
                color_hue = (color_hue + 0.006) % 1
    return palette


MY_PALETTE = _build_actor_palette()

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

PROMPTER_LAYOUT_TYPES = ("Сценарий 1", "Сценарий 2", "Сценарий 3")
PROMPTER_FONT_KEYS = ("f_tc", "f_char", "f_actor", "f_text")
PROMPTER_FONT_BOLD_KEYS = (
    "bold_tc", "bold_char", "bold_actor", "bold_text",
)
DEFAULT_PROMPTER_FONT_SIZES = {
    "Сценарий 1": {
        "f_tc": 25, "f_char": 25, "f_actor": 18, "f_text": 30,
    },
    "Сценарий 2": {
        "f_tc": 24, "f_char": 24, "f_actor": 18, "f_text": 36,
    },
    "Сценарий 3": {
        "f_tc": 30, "f_char": 24, "f_actor": 18, "f_text": 29,
    },
}
DEFAULT_PROMPTER_FONT_BOLD = {
    "Сценарий 1": {
        "bold_tc": False, "bold_char": True,
        "bold_actor": False, "bold_text": False,
    },
    "Сценарий 2": {
        "bold_tc": True, "bold_char": True,
        "bold_actor": False, "bold_text": False,
    },
    "Сценарий 3": {
        "bold_tc": True, "bold_char": True,
        "bold_actor": False, "bold_text": False,
    },
}

DEFAULT_PROMPTER_CONFIG = {
    "f_tc": 30,
    "f_char": 24,
    "f_actor": 18,
    "f_text": 29,
    "bold_tc": True,
    "bold_char": True,
    "bold_actor": False,
    "bold_text": False,
    "layout_type": "Сценарий 3",
    "layout_font_sizes": DEFAULT_PROMPTER_FONT_SIZES,
    "layout_font_bold": DEFAULT_PROMPTER_FONT_BOLD,
    "show_timecode": True,
    "show_end_timecode": True,
    "show_character": True,
    "show_actor": True,
    "show_replica": True,
    "show_block_borders": True,
    "hide_leading_timecode_zeros": True,
    "focus_ratio": 0.1,
    "is_mirrored": False,
    "show_header": True,
    "port_in": 8000,
    "port_out": 9000,
    "osc_enabled": False,
    "sync_in": True,
    "sync_out": False,
    "sync_play_only": False,
    "reaper_offset_enabled": False,
    "reaper_offset_seconds": -2.0,
    "key_prev": "Left",
    "key_next": "Right",
    "scroll_smoothness_slider": 18,
    "page_scroll_mode": False,
    "page_timecode_highlight_enabled": False,
    "page_gap_prefetch_seconds": 1.0,
    "page_gap_prefetch_delay_seconds": 1.0,
    "page_target_highlight_enabled": True,
    "page_target_highlight_opacity": 0.2728,
    "page_target_highlight_fade_in_ms": 500,
    "page_target_highlight_fade_ms": 1000,
    "page_debug_overlay": False,
    "colors": {
        "bg": "#000000",
        "active_text": "#FFFFFF",
        "inactive_text": "#3b3b3b",
        "tc": "#ffffff",
        "actor": "#AAAAAA",
        "header_bg": "#111111",
        "header_text": "#8bf500",
        "block_border": "#4D4D4D",
        "page_target_highlight": "#FFD54F"
    }
}

EXPORT_LAYOUT_TYPES = (
    'Таблица', 'Сценарий 1', 'Сценарий 2', 'Сценарий 3',
)

EXPORT_LAYOUT_PROFILE_KEYS = (
    'font_family',
    'col_tc', 'col_char', 'col_actor', 'col_text',
    'table_width_time', 'table_width_char', 'table_width_actor',
    'time_display', 'round_time', 'hide_leading_timecode_zeros',
    'use_color', 'soften_colors', 'color_softening_level',
    'highlight_character_only',
    'f_time', 'f_char', 'f_actor', 'f_text',
    'bold_time', 'bold_char', 'bold_actor', 'bold_text',
)

DEFAULT_EXPORT_CONFIG = {
    'format_html': True,
    'format_xls': False,
    'format_docx': False,
    'format_pdf': False,
    'layout_type': 'Таблица',
    'font_family': 'Segoe UI',
    'col_tc': True,
    'col_char': True,
    'col_actor': False,
    'col_text': True,
    'f_time': 18,
    'f_char': 15,
    'f_actor': 14,
    'f_text': 20,
    'bold_time': True,
    'bold_char': True,
    'bold_actor': False,
    'bold_text': False,
    'table_width_time': 6.0,
    'table_width_char': 14.5,
    'table_width_actor': 8.5,
    'use_color': True,
    'soften_colors': True,
    'color_softening_level': -1,
    'highlight_character_only': False,
    'open_auto': True,
    'round_time': True,
    'hide_leading_timecode_zeros': True,
    'time_display': 'range',
    'allow_edit': True,
    'layout_profiles': {},
}

DEFAULT_EXPORT_CONFIG['layout_profiles'] = {
    layout_type: {
        key: DEFAULT_EXPORT_CONFIG[key]
        for key in EXPORT_LAYOUT_PROFILE_KEYS
    }
    for layout_type in EXPORT_LAYOUT_TYPES
}

DEFAULT_EXPORT_CONFIG['layout_profiles']['Сценарий 1'].update({
    'col_actor': True,
    'color_softening_level': 0,
    'f_time': 20,
    'f_char': 20,
    'bold_time': False,
})
DEFAULT_EXPORT_CONFIG['layout_profiles']['Сценарий 2'].update({
    'f_char': 19,
})
DEFAULT_EXPORT_CONFIG['layout_profiles']['Сценарий 3'].update({
    'soften_colors': False,
    'highlight_character_only': True,
    'f_time': 21,
    'f_char': 17,
    'bold_time': False,
})

DEFAULT_REPLICA_MERGE_CONFIG = {
    'merge': True,
    'merge_parallel_replicas': False,
    'respect_existing_separators': False,
    'merge_gap': 120,  # Maximum frame gap for merging adjacent replicas.
    'p_short': 0.5,
    'p_long': 2.0,
    'fps': 25,  # Frame rate used for time conversion.
}

DEFAULT_INLINE_TIMECODE_CONFIG = {
    'inline_timecodes_enabled': False,
    'inline_timecode_min_duration': 30.0,
    'inline_timecode_every': 3,
    'inline_timecode_brackets': 'square',
}

DEFAULT_GLOBAL_MERGE_CONFIG = {
    'merge': True,
    'merge_parallel_replicas': False,
    'respect_existing_separators': False,
    'merge_gap_seconds': 4.8,
    'p_short': 0.5,
    'p_long': 2.0,
    **DEFAULT_INLINE_TIMECODE_CONFIG,
}

DEFAULT_PROJECT_FPS = 25.0

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
    'replica_merge_config': None,  # Initialized from DEFAULT_GLOBAL_MERGE_CONFIG.
    'ass_import_config': DEFAULT_ASS_IMPORT_CONFIG,
    'srt_import_config': DEFAULT_SRT_IMPORT_CONFIG,
    'docx_import_config': None,  # DOCX-specific handling
    'audiobook_config': DEFAULT_AUDIOBOOK_CONFIG,
    'backup_config': DEFAULT_BACKUP_CONFIG,
    'language': 'ru',
}

# Application version shown in the UI and build metadata.
APP_VERSION = "2.0.0-rc9"

# Project file format version used for compatibility migrations.
PROJECT_VERSION = "2.0"

# Folder name for Dubbing Manager working text JSON files.
SCRIPT_TEXT_DIR_NAME = "texts_dm"
