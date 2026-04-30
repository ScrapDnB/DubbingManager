"""Точка входа приложения Dubbing Manager"""

import sys
import os
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from ui.main_window import MainWindow


def get_log_path() -> Path:
    """Получить путь для лог-файла в пользовательской директории."""
    if sys.platform == 'win32':
        # Windows: используем %LOCALAPPDATA%
        base = os.environ.get('LOCALAPPDATA') or os.environ.get('APPDATA')
        if not base:
            base = str(Path.home())
        log_dir = Path(base) / 'DubbingManager' / 'logs'
    elif sys.platform == 'darwin':
        # macOS: ~/Library/Logs
        log_dir = Path.home() / 'Library' / 'Logs' / 'DubbingManager'
    else:
        # Linux и другие: ~/.local/share
        log_dir = Path.home() / '.local' / 'share' / 'dubbing-manager' / 'logs'

    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir / 'dubbing_manager.log'


logger = logging.getLogger(__name__)


def setup_logging() -> None:
    """Настроить логирование приложения с ротацией файлов."""
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
    """Точка входа приложения"""
    setup_logging()
    logger.info("Starting Dubbing Manager")
    
    # Настройка High DPI
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    
    app = QApplication(sys.argv)
    app.setApplicationName("Dubbing Manager")
    app.setOrganizationName("DubbingTools")
    
    window = MainWindow()
    window.show()
    
    logger.info("Application started successfully")
    
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
