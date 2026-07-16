"""Application entry point for Dubbing Manager."""

import sys
import logging
from typing import Optional
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt, QEvent

from app_startup import (
    get_log_path,
    initial_project_path,
    is_project_file,
    setup_logging,
)
from ui.main_window import MainWindow


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
