"""QML entry point for Dubbing Manager."""

import logging
import sys
from pathlib import Path

from PySide6.QtCore import QEvent, QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtWebEngineQuick import QtWebEngineQuick

from app_startup import initial_project_path, setup_logging
from ui.qml_backend.app_bridge import AppBridge
from utils.i18n import JsonSourceTranslator


logger = logging.getLogger(__name__)


class DubbingQmlApplication(QGuiApplication):
    """QML application that accepts project files opened by the OS."""

    def __init__(self, argv: list[str]) -> None:
        super().__init__(argv)
        self.bridge: AppBridge | None = None

    def event(self, event) -> bool:
        if event.type() == QEvent.FileOpen and self.bridge:
            path = event.file()
            if path:
                self.bridge.project.open(path)
                return True
        return super().event(event)


def main() -> int:
    """Run the QML application."""
    setup_logging()
    QtWebEngineQuick.initialize()
    app = DubbingQmlApplication(sys.argv)
    app.setApplicationName("Dubbing Manager")
    app.setOrganizationName("DubbingTools")

    engine = QQmlApplicationEngine()
    bridge = AppBridge()
    translator = JsonSourceTranslator(app)
    app.installTranslator(translator)
    app._source_translator = translator
    app.bridge = bridge
    start_project = initial_project_path(sys.argv)
    if start_project:
        bridge.project.open(start_project)
    engine.setInitialProperties({"appBridge": bridge})

    qml_file = Path(__file__).resolve().parent / "qml" / "Main.qml"
    engine.load(QUrl.fromLocalFile(str(qml_file)))
    if not engine.rootObjects():
        logger.error("Could not load QML interface from %s", qml_file)
        return 1
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
