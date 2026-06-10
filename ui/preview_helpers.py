"""Helpers for live preview state and project data."""

from copy import deepcopy
from typing import Any, Dict, List, Optional


def get_export_highlight_ids(
    project_data: Dict[str, Any]
) -> Optional[List[str]]:
    """Return the current actor highlight filter from export settings."""
    return project_data.get("export_config", {}).get("highlight_ids_export")


def get_export_negative_ids(project_data: Dict[str, Any]) -> List[str]:
    """Return actors that use white text over highlight color."""
    return list(
        project_data.get("export_config", {}).get(
            "highlight_negative_ids_export",
            []
        ) or []
    )


def build_preview_project_data(
    project_data: Dict[str, Any],
    use_override_lines: bool
) -> Dict[str, Any]:
    """Return project data for regular or temporary quick-converter preview."""
    if not use_override_lines:
        return project_data

    data = deepcopy(project_data)
    data["actors"] = {}
    data["global_map"] = {}
    data["episode_actor_map"] = {}
    cfg = deepcopy(data.get("export_config", {}))
    cfg["use_color"] = False
    cfg["highlight_ids_export"] = []
    cfg["highlight_negative_ids_export"] = []
    data["export_config"] = cfg
    return data


def apply_preview_settings(
    cfg: Dict[str, Any],
    values: Dict[str, Any]
) -> None:
    """Persist preview UI values into export config."""
    cfg["layout_type"] = values["layout_type"]
    cfg["col_tc"] = values["col_tc"]
    cfg["col_char"] = values["col_char"]
    cfg["col_actor"] = values["col_actor"]
    cfg["col_text"] = values["col_text"]
    cfg["round_time"] = values["round_time"]
    cfg["time_display"] = values["time_display"]
    cfg["f_time"] = values["f_time"]
    cfg["f_char"] = values["f_char"]
    cfg["f_actor"] = values["f_actor"]
    cfg["f_text"] = values["f_text"]
    cfg["table_width_time"] = values["table_width_time"]
    cfg["table_width_char"] = values["table_width_char"]
    cfg["table_width_actor"] = values["table_width_actor"]
    cfg["soften_colors"] = values["soften_colors"]
