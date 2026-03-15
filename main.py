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


# Настройка логирования с ротацией файлов
log_path = get_log_path()

# Создаём formatter
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Создаём handler с ротацией: макс. 10MB, храним 5 последних файлов
file_handler = RotatingFileHandler(
    log_path,
    encoding='utf-8',
    maxBytes=10 * 1024 * 1024,  # 10 MB
    backupCount=5
)
file_handler.setFormatter(formatter)
file_handler.setLevel(logging.DEBUG)

# Консольный handler
stream_handler = logging.StreamHandler()
stream_handler.setFormatter(formatter)
stream_handler.setLevel(logging.INFO)

# Настраиваем корневой логгер
logging.basicConfig(
    level=logging.DEBUG,
    handlers=[file_handler, stream_handler]
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