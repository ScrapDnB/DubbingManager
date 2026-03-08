"""Точка входа приложения Dubbing Manager"""

import sys
import os
import logging
from pathlib import Path
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from ui.main_window import MainWindow


def get_log_path() -> Path:
    """Получить путь для лог-файла в пользовательской директории."""
    if sys.platform == 'win32':
        # Windows: используем %LOCALAPPDATA%
        base = os.environ.get('LOCALAPPDATA')
        if not base:
            base = os.environ.get('APPDATA', str(Path.home()))
        log_dir = Path(base) / 'DubbingManager' / 'logs'
    elif sys.platform == 'darwin':
        # macOS: ~/Library/Logs
        log_dir = Path.home() / 'Library' / 'Logs' / 'DubbingManager'
    else:
        # Linux и другие: ~/.local/share
        log_dir = Path.home() / '.local' / 'share' / 'dubbing-manager' / 'logs'
    
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir / 'dubbing_manager.log'


# Настройка логирования
log_path = get_log_path()
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_path, encoding='utf-8'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


def main() -> int:
    """Точка входа приложения"""
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