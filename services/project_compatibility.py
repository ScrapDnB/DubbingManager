"""Compatibility upgrades for project dictionaries."""

from copy import deepcopy
from datetime import datetime
from typing import Any, Dict

from config.constants import (
    DEFAULT_ASS_IMPORT_CONFIG,
    DEFAULT_DOCX_IMPORT_CONFIG,
    DEFAULT_EXPORT_CONFIG,
    DEFAULT_PROMPTER_CONFIG,
    DEFAULT_REPLICA_MERGE_CONFIG,
    DEFAULT_SRT_IMPORT_CONFIG,
    PROJECT_VERSION,
)


def ensure_project_compatibility(data: Dict[str, Any]) -> None:
    """Mutate project data so older files have the current required fields."""
    if "book_chapters" not in data:
        data["book_chapters"] = {}
    if "audiobook_source" not in data:
        data["audiobook_source"] = {}
    if data.get("project_kind") not in ("subtitle", "audiobook"):
        data["project_kind"] = (
            "audiobook"
            if isinstance(data.get("book_chapters"), dict) and data["book_chapters"]
            else "subtitle"
        )
    if "audiobook_chapter_order" not in data:
        data["audiobook_chapter_order"] = (
            list(data.get("book_chapters", {}))
            if data.get("project_kind") == "audiobook" and
            isinstance(data.get("book_chapters"), dict)
            else []
        )
    elif not isinstance(data["audiobook_chapter_order"], list):
        data["audiobook_chapter_order"] = []
    if "video_paths" not in data:
        data["video_paths"] = {}
    if "episode_texts" not in data:
        data["episode_texts"] = {}
    if "episode_working_texts" not in data:
        data["episode_working_texts"] = {}
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
    if "ass_import_config" not in data:
        data["ass_import_config"] = deepcopy(DEFAULT_ASS_IMPORT_CONFIG)
    if "srt_import_config" not in data:
        data["srt_import_config"] = deepcopy(DEFAULT_SRT_IMPORT_CONFIG)

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
    data["metadata"]["format_version"] = PROJECT_VERSION

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
