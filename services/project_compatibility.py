"""Compatibility upgrades for project dictionaries."""

from copy import deepcopy
from datetime import datetime
from typing import Any, Dict

from config.constants import (
    DEFAULT_DOCX_IMPORT_CONFIG,
    DEFAULT_EXPORT_CONFIG,
    DEFAULT_PROMPTER_CONFIG,
    DEFAULT_REPLICA_MERGE_CONFIG,
)


def ensure_project_compatibility(data: Dict[str, Any]) -> None:
    """Mutate project data so older files have the current required fields."""
    if "video_paths" not in data:
        data["video_paths"] = {}
    if "episode_texts" not in data:
        data["episode_texts"] = {}
    if "export_config" not in data:
        data["export_config"] = deepcopy(DEFAULT_EXPORT_CONFIG)
    else:
        export_config = deepcopy(DEFAULT_EXPORT_CONFIG)
        if isinstance(data["export_config"], dict):
            export_config.update(data["export_config"])
        data["export_config"] = export_config
    if "prompter_config" not in data:
        data["prompter_config"] = deepcopy(DEFAULT_PROMPTER_CONFIG)
    if "global_map" not in data:
        data["global_map"] = {}
    if "episode_actor_map" not in data:
        data["episode_actor_map"] = {}
    if "replica_merge_config" not in data:
        if "export_config" in data:
            # Older projects stored replica merge settings inside export_config.
            export_cfg = data["export_config"]
            data["replica_merge_config"] = {
                'merge': export_cfg.get('merge', True),
                'merge_gap': export_cfg.get('merge_gap', 5),
                'p_short': export_cfg.get('p_short', 0.5),
                'p_long': export_cfg.get('p_long', 2.0),
            }
        else:
            data["replica_merge_config"] = deepcopy(
                DEFAULT_REPLICA_MERGE_CONFIG
            )
    if "docx_import_config" not in data:
        data["docx_import_config"] = deepcopy(DEFAULT_DOCX_IMPORT_CONFIG)

    if "project_folder" not in data:
        data["project_folder"] = None

    if "metadata" not in data:
        now = datetime.now().isoformat()
        data["metadata"] = {
            "format_version": "0.9",  # Legacy format marker.
            "app_version": "pre-1.0",
            "created_at": now,
            "modified_at": now,
        }
    data["metadata"].setdefault("created_by", "")
    data["metadata"].setdefault("studio", "")
