"""Compatibility upgrades for project dictionaries."""

from copy import deepcopy
from datetime import datetime
from typing import Any, Dict

from config.constants import (
    APP_VERSION,
    DEFAULT_EXPORT_CONFIG,
    DEFAULT_PROMPTER_CONFIG,
    PROJECT_VERSION,
)
from core.export_config_profiles import (
    hydrate_layout_profile,
    sync_active_layout_profile,
)
from services.dynamic_script_storage import is_dynamic_script_project
from services.project_fps_service import ensure_project_settings


def ensure_project_compatibility(data: Dict[str, Any]) -> None:
    """Mutate project data so older files have the current required fields."""
    dynamic_scripts = is_dynamic_script_project(data)
    if "audiobook_document" not in data:
        data["audiobook_document"] = {}
    if data.get("project_kind") not in ("subtitle", "audiobook"):
        data["project_kind"] = "subtitle"
    if "video_paths" not in data:
        data["video_paths"] = {}
    if not dynamic_scripts and "episode_texts" not in data:
        data["episode_texts"] = {}
    if not dynamic_scripts and "episode_working_texts" not in data:
        data["episode_working_texts"] = {}
    if "export_config" not in data:
        data["export_config"] = deepcopy(DEFAULT_EXPORT_CONFIG)
    else:
        export_config = deepcopy(DEFAULT_EXPORT_CONFIG)
        if isinstance(data["export_config"], dict):
            export_config.update(data["export_config"])
            if "layout_profiles" not in data["export_config"]:
                export_config["layout_profiles"] = {}
        data["export_config"] = hydrate_layout_profile(
            sync_active_layout_profile(export_config)
        )
    if "prompter_config" not in data:
        data["prompter_config"] = deepcopy(DEFAULT_PROMPTER_CONFIG)
    if "global_map" not in data:
        data["global_map"] = {}
    aliases = data.get("character_aliases")
    if not isinstance(aliases, dict):
        data["character_aliases"] = {}
    else:
        data["character_aliases"] = {
            str(character): list(dict.fromkeys(
                str(alias).strip()
                for alias in values
                if str(alias).strip()
            ))
            for character, values in aliases.items()
            if str(character).strip() and isinstance(values, list)
        }
    if "episode_actor_map" not in data:
        data["episode_actor_map"] = {}
    ensure_project_settings(data)
    # Import rules belong to the application, not to a project.  Drop legacy
    # copies while loading so the next save transparently migrates old files.
    for key in (
        "replica_merge_config", "ass_import_config", "srt_import_config",
        "docx_import_config",
    ):
        data.pop(key, None)

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
    now = datetime.now().isoformat()
    data["metadata"].setdefault("created_at", now)
    data["metadata"].setdefault("modified_at", now)
    data["metadata"].setdefault("app_version", APP_VERSION)
    data["metadata"]["format_version"] = PROJECT_VERSION

    if not dynamic_scripts:
        _ensure_working_text_source_layers(data)


def _ensure_working_text_source_layers(data: Dict[str, Any]) -> None:
    """Add source-line containers to embedded working texts from older projects."""
    for payload in data.get("episode_working_texts", {}).values():
        if not isinstance(payload, dict):
            continue
        payload["format_version"] = "1.1"
        payload.setdefault("source_ass", None)
        if isinstance(payload.get("source_lines"), list):
            payload.setdefault(
                "source_lines_origin",
                _infer_existing_source_lines_origin(payload)
            )
            continue

        source_lines = []
        for line in payload.get("lines", []):
            if not isinstance(line, dict):
                continue
            source_ids = line.get("source_ids") or [line.get("id")]
            source_texts = line.get("source_texts") or [line.get("text", "")]
            for idx, source_id in enumerate(source_ids):
                source_lines.append({
                    "id": source_id,
                    "start": line.get("start", 0.0),
                    "end": line.get("end", 0.0),
                    "s_raw": line.get("s_raw", ""),
                    "character": line.get("character", ""),
                    "text": (
                        source_texts[idx]
                        if idx < len(source_texts)
                        else line.get("text", "")
                    ),
                })
        payload["source_lines"] = source_lines
        payload["source_lines_origin"] = "reconstructed"


def _infer_existing_source_lines_origin(payload: Dict[str, Any]) -> str:
    """Infer source line quality for payloads saved before this marker existed."""
    if payload.get("source_lines_origin"):
        return str(payload["source_lines_origin"])

    source = payload.get("source") if isinstance(payload.get("source"), dict) else {}
    source_type = str(source.get("type") or "").lower()
    source_ass = payload.get("source_ass")
    if source_type == "ass" and not (
        isinstance(source_ass, dict) and source_ass.get("raw_content")
    ):
        return "reconstructed"

    return "imported"
