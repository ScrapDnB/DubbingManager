"""Точка входа приложения Dubbing Manager"""

import sys
import logging
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from ui.main_window import MainWindow

# Настройка логирования
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('dubbing_manager.log', encoding='utf-8'),
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