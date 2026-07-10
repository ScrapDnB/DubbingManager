"""Helpers for project-level metadata updates."""

from pathlib import Path
from typing import Any, Dict, Optional, Set


DEFAULT_PROJECT_NAMES = {
    "",
    "Новый проект",
    "New Project",
    "Project",
    "Untitled",
}


def maybe_set_project_name_from_first_import(
    project_data: Dict[str, Any],
    source_path: str,
    allowed_extensions: Optional[Set[str]] = None
) -> bool:
    """Set project name from the first imported source file when safe."""
    ext = Path(source_path or "").suffix.lower()
    if allowed_extensions is not None and ext not in allowed_extensions:
        return False

    if project_data.get("episodes") or project_data.get("book_chapters"):
        return False

    current_name = str(project_data.get("project_name", "")).strip()
    if current_name not in DEFAULT_PROJECT_NAMES:
        return False

    imported_name = Path(source_path or "").stem.strip()
    if not imported_name:
        return False

    project_data["project_name"] = imported_name
    return True
