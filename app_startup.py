"""Shared startup helpers for the Widgets and QML entry points."""

import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional

from config.constants import (
    PROJECT_BACKUP_FILE_EXTENSION,
    PROJECT_FILE_EXTENSION,
    PROJECT_LEGACY_FILE_EXTENSION,
)


logger = logging.getLogger(__name__)


def get_log_path() -> Path:
    """Return the platform log path in a user-writable directory."""
    if sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA")
        log_dir = Path(base or Path.home()) / "DubbingManager" / "logs"
    elif sys.platform == "darwin":
        log_dir = Path.home() / "Library" / "Logs" / "DubbingManager"
    else:
        log_dir = (
            Path.home() / ".local" / "share" / "dubbing-manager" / "logs"
        )
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir / "dubbing_manager.log"


def is_project_file(path: str) -> bool:
    return Path(path).suffix.lower() in {
        PROJECT_FILE_EXTENSION,
        PROJECT_BACKUP_FILE_EXTENSION,
        PROJECT_LEGACY_FILE_EXTENSION,
    }


def initial_project_path(argv: list[str]) -> Optional[str]:
    for arg in argv[1:]:
        if is_project_file(arg) and Path(arg).exists():
            return arg
    return None


def setup_logging() -> None:
    root_logger = logging.getLogger()
    if any(
        getattr(handler, "_dubbing_manager_handler", False)
        for handler in root_logger.handlers
    ):
        return

    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    stream_handler.setLevel(logging.INFO)
    stream_handler._dubbing_manager_handler = True
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(stream_handler)

    try:
        file_handler = RotatingFileHandler(
            get_log_path(),
            encoding="utf-8",
            maxBytes=10 * 1024 * 1024,
            backupCount=5,
        )
    except OSError as exc:
        logger.warning("File logging is disabled: %s", exc)
        return
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.DEBUG)
    file_handler._dubbing_manager_handler = True
    root_logger.addHandler(file_handler)
