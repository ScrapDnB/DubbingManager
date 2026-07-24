"""QML entry point for Dubbing Manager."""

import logging
import os
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


def configure_platform_graphics(platform: str | None = None) -> None:
    """Avoid Vulkan-only virtual GPU issues in Windows WebEngine hosts."""
    if not (platform or sys.platform).startswith("win"):
        return

    flags = os.environ.get("QTWEBENGINE_CHROMIUM_FLAGS", "").split()
    if "--disable-vulkan" not in flags:
        flags.append("--disable-vulkan")
        os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = " ".join(flags)


def configure_qml_controls_style() -> None:
    """Use platform-appropriate Qt Quick Controls styles."""
    if sys.platform.startswith("win"):
        os.environ.setdefault("QT_QUICK_CONTROLS_STYLE", "Basic")
    elif sys.platform == "darwin":
        current_style = os.environ.get("QT_QUICK_CONTROLS_STYLE")
        if not current_style or current_style == "Basic":
            os.environ["QT_QUICK_CONTROLS_STYLE"] = "macOS"


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
    configure_platform_graphics()
    configure_qml_controls_style()
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
