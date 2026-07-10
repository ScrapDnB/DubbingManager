"""Application entry point for Dubbing Manager."""

import sys
import os
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt, QEvent

from config.constants import (
    PROJECT_FILE_EXTENSION,
    PROJECT_LEGACY_FILE_EXTENSION,
)
from ui.main_window import MainWindow


def get_log_path() -> Path:
    """Return the log file path in the user's writable data directory."""
    if sys.platform == 'win32':
        # Windows: prefer %LOCALAPPDATA%.
        base = os.environ.get('LOCALAPPDATA') or os.environ.get('APPDATA')
        if not base:
            base = str(Path.home())
        log_dir = Path(base) / 'DubbingManager' / 'logs'
    elif sys.platform == 'darwin':
        # macOS: ~/Library/Logs
        log_dir = Path.home() / 'Library' / 'Logs' / 'DubbingManager'
    else:
        # Linux and other Unix-like systems: ~/.local/share.
        log_dir = Path.home() / '.local' / 'share' / 'dubbing-manager' / 'logs'

    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir / 'dubbing_manager.log'


logger = logging.getLogger(__name__)


class DubbingManagerApplication(QApplication):
    """Application object that accepts project files opened by the OS."""

    def __init__(self, argv: list[str]) -> None:
        super().__init__(argv)
        self.main_window: Optional[MainWindow] = None

    def event(self, event) -> bool:
        """Handle macOS/Finder file-open events."""
        if event.type() == QEvent.FileOpen and self.main_window:
            path = event.file()
            if is_project_file(path):
                self.main_window.open_project_file(path)
                return True
        return super().event(event)


def is_project_file(path: str) -> bool:
    """Return whether path looks like a project file."""
    return Path(path).suffix.lower() in {
        PROJECT_FILE_EXTENSION,
        PROJECT_LEGACY_FILE_EXTENSION,
    }


def initial_project_path(argv: list[str]) -> Optional[str]:
    """Return the first project path passed on the command line."""
    for arg in argv[1:]:
        if is_project_file(arg) and Path(arg).exists():
            return arg
    return None


def setup_logging() -> None:
    """Configure application logging with rotating file logs."""
    root_logger = logging.getLogger()
    if any(getattr(handler, "_dubbing_manager_handler", False) for handler in root_logger.handlers):
        return

    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
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
            encoding='utf-8',
            maxBytes=10 * 1024 * 1024,
            backupCount=5
        )
    except OSError as exc:
        logger.warning("File logging is disabled: %s", exc)
        return

    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.DEBUG)
    file_handler._dubbing_manager_handler = True
    root_logger.addHandler(file_handler)


def main() -> int:
    """Run the application."""
    setup_logging()
    logger.info("Starting Dubbing Manager")
    
    # High DPI setup.
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    
    app = DubbingManagerApplication(sys.argv)
    app.setApplicationName("Dubbing Manager")
    app.setOrganizationName("DubbingTools")
    
    window = MainWindow()
    app.main_window = window
    window.show()
    start_project = initial_project_path(sys.argv)
    if start_project:
        window.open_project_file(start_project)
    
    logger.info("Application started successfully")
    
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
