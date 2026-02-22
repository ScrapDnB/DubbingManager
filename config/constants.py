"""Константы приложения Dubbing Manager"""

MY_PALETTE = [
    "#D9775F", "#E46C0A", "#9B5333", "#C0504D", "#C4BD97",
    "#D4A017", "#938953", "#8A7F80", "#76923C", "#4F6228",
    "#31859B", "#669999", "#4F81BD", "#5B9BD5", "#2C4D75",
    "#708090", "#B65C72", "#8064A2", "#5F497A", "#7B3F61"
]

# Настройки суфлёра по умолчанию
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
    "sync_in": True,
    "sync_out": False,
    "reaper_offset_enabled": False,
    "reaper_offset_seconds": -2.0,
    "key_prev": "Left",
    "key_next": "Right",
    "scroll_smoothness_slider": 18,
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

# Настройки экспорта по умолчанию
DEFAULT_EXPORT_CONFIG = {
    'layout_type': 'Таблица',
    'col_tc': True,
    'col_char': True,
    'col_actor': True,
    'col_text': True,
    'f_time': 21,
    'f_char': 20,
    'f_actor': 14,
    'f_text': 30,
    'use_color': True,
    'merge': True,
    'merge_gap': 5,
    'p_short': 0.5,
    'p_long': 2.0,
    'open_auto': True,
    'round_time': False,
    'allow_edit': True
}

# Версия формата проекта для совместимости
PROJECT_VERSION = "1.0"