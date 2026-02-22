"""Main entry point for Dubbing Manager"""

import sys
from PySide6.QtWidgets import QApplication
from src.ui_main import DubbingApp

def main():
    app = QApplication(sys.argv)
    window = DubbingApp()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()