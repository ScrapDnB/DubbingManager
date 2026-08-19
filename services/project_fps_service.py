"""Project-scoped FPS detection and normalization."""

from __future__ import annotations

from pathlib import Path
import re
from typing import Any, Dict, Optional

from config.constants import DEFAULT_PROJECT_FPS
from utils.helpers import probe_video_fps


FPS_SOURCES = {"default", "ass", "video", "manual", "legacy"}


def new_project_settings() -> Dict[str, Any]:
    """Return default project-only settings."""
    return {
        "fps": DEFAULT_PROJECT_FPS,
        "fps_source": "default",
        "fps_source_path": "",
        "fps_ass_checked": False,
        "fps_video_checked": False,
    }


def ensure_project_settings(project_data: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize project FPS and migrate the old project merge container."""
    incoming = project_data.get("project_settings")
    settings = new_project_settings()
    if isinstance(incoming, dict):
        settings.update(incoming)

    storage = project_data.get("script_storage")
    old_merge = storage.get("merge_config") if isinstance(storage, dict) else None
    if (
        settings.get("fps_source") == "default"
        and isinstance(old_merge, dict)
        and "fps" in old_merge
    ):
        migrated = _normalized_fps(old_merge.get("fps"))
        if migrated is not None:
            settings.update({
                "fps": migrated,
                "fps_source": "legacy",
            })
    if isinstance(storage, dict):
        storage.pop("merge_config", None)

    legacy_merge = project_data.get("replica_merge_config")
    if (
        settings.get("fps_source") == "default"
        and isinstance(legacy_merge, dict)
        and "fps" in legacy_merge
    ):
        migrated = _normalized_fps(legacy_merge.get("fps"))
        if migrated is not None:
            settings.update({
                "fps": migrated,
                "fps_source": "legacy",
            })

    settings["fps"] = _normalized_fps(settings.get("fps")) or DEFAULT_PROJECT_FPS
    source = str(settings.get("fps_source") or "default").lower()
    settings["fps_source"] = source if source in FPS_SOURCES else "default"
    settings["fps_source_path"] = str(
        settings.get("fps_source_path") or ""
    )
    settings["fps_ass_checked"] = bool(settings.get("fps_ass_checked", False))
    settings["fps_video_checked"] = bool(
        settings.get("fps_video_checked", False)
    )
    project_data["project_settings"] = settings
    return settings


def project_fps(project_data: Dict[str, Any]) -> float:
    """Return the normalized FPS stored in a project."""
    return float(ensure_project_settings(project_data)["fps"])


def effective_merge_config(
    project_data: Dict[str, Any],
    global_config: Dict[str, Any],
) -> Dict[str, Any]:
    """Combine global merge preferences with project FPS."""
    config = dict(global_config or {})
    fps = project_fps(project_data)
    config["fps"] = fps
    try:
        raw_seconds = config.get("merge_gap_seconds")
        if raw_seconds is None and "merge_gap" in config:
            legacy_fps = max(
                0.001, float((global_config or {}).get("fps", fps))
            )
            raw_seconds = float(config["merge_gap"]) / legacy_fps
        seconds = max(0.0, float(
            4.8 if raw_seconds is None else raw_seconds
        ))
    except (TypeError, ValueError):
        seconds = 4.8
    config["merge_gap_seconds"] = seconds
    # Transitional consumers still accept the old frame-based field.
    config["merge_gap"] = seconds * fps
    return config


def consider_ass_fps(project_data: Dict[str, Any], path: str) -> bool:
    """Use FPS metadata from the first imported ASS when available."""
    settings = ensure_project_settings(project_data)
    if settings["fps_source"] == "manual" or settings["fps_ass_checked"]:
        return False
    settings["fps_ass_checked"] = True
    detected = detect_ass_fps(path)
    if detected is not None:
        settings.update({
            "fps": detected,
            "fps_source": "ass",
            "fps_source_path": str(path),
        })
    return True


def consider_video_fps(project_data: Dict[str, Any], path: str) -> bool:
    """Use FPS from the first imported video unless ASS/manual has priority."""
    settings = ensure_project_settings(project_data)
    if (
        settings["fps_source"] in {"manual", "ass"}
        or settings["fps_video_checked"]
    ):
        return False
    settings["fps_video_checked"] = True
    detected = probe_video_fps(path)
    if detected is not None:
        settings.update({
            "fps": detected,
            "fps_source": "video",
            "fps_source_path": str(path),
        })
    return True


def set_project_fps(project_data: Dict[str, Any], value: Any) -> bool:
    """Set FPS manually and prevent later automatic replacement."""
    fps = _normalized_fps(value)
    if fps is None:
        return False
    settings = ensure_project_settings(project_data)
    changed = (
        settings["fps"] != fps
        or settings["fps_source"] != "manual"
        or settings["fps_source_path"]
    )
    settings.update({
        "fps": fps,
        "fps_source": "manual",
        "fps_source_path": "",
    })
    return changed


def detect_ass_fps(path: str) -> Optional[float]:
    """Read common non-standard FPS metadata keys from an ASS header."""
    try:
        with open(path, "r", encoding="utf-8-sig") as source:
            for index, line in enumerate(source):
                if index > 1000 or line.lstrip().startswith("Dialogue:"):
                    break
                match = re.match(
                    r"^\s*(?:Video\s+FPS|Video\s+Frame\s*Rate|"
                    r"Frame\s*Rate|FrameRate|FPS)\s*:\s*([^;#\s]+)",
                    line,
                    re.IGNORECASE,
                )
                if not match:
                    continue
                value = match.group(1).replace(",", ".")
                if "/" in value:
                    numerator, denominator = value.split("/", 1)
                    value = str(float(numerator) / float(denominator))
                return _normalized_fps(value)
    except (OSError, UnicodeError, ValueError, ZeroDivisionError):
        return None
    return None


def fps_source_label(project_data: Dict[str, Any]) -> str:
    """Return a concise user-facing FPS source description."""
    settings = ensure_project_settings(project_data)
    labels = {
        "default": "Значение по умолчанию",
        "ass": "Определено из первого ASS",
        "video": "Определено из первого видео",
        "manual": "Задано вручную",
        "legacy": "Перенесено из старого проекта",
    }
    label = labels[settings["fps_source"]]
    path = settings.get("fps_source_path")
    return f"{label}: {Path(path).name}" if path else label


def _normalized_fps(value: Any) -> Optional[float]:
    try:
        fps = float(value)
    except (TypeError, ValueError):
        return None
    return fps if 1.0 <= fps <= 120.0 else None
