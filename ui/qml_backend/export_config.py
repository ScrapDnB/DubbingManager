"""Shared validation for montage-style export settings exposed to QML."""

from typing import Any


def normalize_export_option(key: str, value: Any) -> Any:
    bool_keys = {
        "col_tc", "col_char", "col_actor", "col_text", "use_color",
        "soften_colors", "highlight_character_only", "open_auto",
        "round_time", "hide_leading_timecode_zeros", "allow_edit",
        "bold_time", "bold_char", "bold_actor", "bold_text",
        "format_html", "format_xls", "format_docx", "format_pdf",
    }
    if key in bool_keys:
        return bool(value)
    if key == "layout_type":
        value = str(value or "")
        return value if value in {
            "Таблица", "Сценарий 1", "Сценарий 2", "Сценарий 3",
        } else None
    if key == "time_display":
        value = str(value or "")
        return value if value in {"range", "start"} else None
    if key == "font_family":
        value = str(value or "").strip()
        if not value or len(value) > 100 or any(
            character in value for character in "\r\n\x00"
        ):
            return None
        return value
    if key == "color_softening_level":
        try:
            return max(-2, min(2, int(value)))
        except (TypeError, ValueError):
            return None
    if key in {"f_time", "f_char", "f_actor", "f_text"}:
        try:
            return max(8, min(72, int(value)))
        except (TypeError, ValueError):
            return None
    if key in {"table_width_time", "table_width_char", "table_width_actor"}:
        try:
            return max(4.0, min(24.0, round(float(value) * 2) / 2))
        except (TypeError, ValueError):
            return None
    return None
