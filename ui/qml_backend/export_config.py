"""Shared validation for montage-style export settings exposed to QML."""

from typing import Any


def normalize_export_option(key: str, value: Any) -> Any:
    bool_keys = {
        "col_tc", "col_char", "col_actor", "col_text", "use_color",
        "soften_colors", "open_auto", "round_time", "allow_edit",
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
