"""QML entry point for Dubbing Manager."""

import logging
import os
import sys
from pathlib import Path

def configure_platform_graphics(platform: str | None = None) -> None:
    """Select stable Qt WebEngine graphics paths for each desktop platform."""
    target_platform = platform or sys.platform
    if target_platform == "darwin":
        # Chromium enables experimental Skia Graphite on Apple Silicon, but
        # Qt WebEngine's bundled backend can fall back to Ganesh at each start.
        # Select that stable path directly without disabling GPU acceleration.
        flags = os.environ.get("QTWEBENGINE_CHROMIUM_FLAGS", "").split()
        if "--disable-skia-graphite" not in flags:
            flags.append("--disable-skia-graphite")
            os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = " ".join(flags)
        return

    if not target_platform.startswith("win"):
        return

    flags = os.environ.get("QTWEBENGINE_CHROMIUM_FLAGS", "").split()
    if "--disable-vulkan" not in flags:
        flags.append("--disable-vulkan")
        os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = " ".join(flags)

    # Qt Quick can select Vulkan independently of Chromium. Direct3D 11 is
    # the native Windows RHI backend and remains reliable in virtual GPUs.
    os.environ.setdefault("QSG_RHI_BACKEND", "d3d11")


# QtWebEngine may probe its graphics stack while its Python module is loaded.
# Set the process-wide backend choice before importing any PySide6 module.
configure_platform_graphics()


from PySide6.QtCore import QEvent, QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtWebEngineQuick import QtWebEngineQuick

from app_startup import initial_project_path, setup_logging
from ui.macos_integration import MacOSIntegration
from ui.qml_backend.app_bridge import AppBridge
from utils.i18n import JsonSourceTranslator


logger = logging.getLogger(__name__)


def configure_qml_controls_style() -> None:
    """Use platform-appropriate Qt Quick Controls styles."""
    if sys.platform.startswith("win"):
        os.environ.setdefault("QT_QUICK_CONTROLS_STYLE", "FluentWinUI3")
    elif sys.platform == "darwin":
        # A parent shell or a previous Windows test must not leak Fluent/Fusion
        # controls into the macOS application.
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
    macos_integration = MacOSIntegration(app)
    engine.rootContext().setContextProperty(
        "platformIntegration", macos_integration
    )
    translator = JsonSourceTranslator(app)
    app.installTranslator(translator)
    app._source_translator = translator
    app.bridge = bridge
    start_project = initial_project_path(sys.argv)
    if start_project:
        bridge.project.open(start_project)
    engine.setInitialProperties({
        "appBridge": bridge,
        "macOSIntegration": macos_integration,
    })

    qml_file = Path(__file__).resolve().parent / "qml" / "Main.qml"
    engine.load(QUrl.fromLocalFile(str(qml_file)))
    if not engine.rootObjects():
        logger.error("Could not load QML interface from %s", qml_file)
        return 1
    root_window = engine.rootObjects()[0]
    macos_integration.configure_main_window(root_window, bridge.project)
    if sys.platform == "darwin":
        app.focusWindowChanged.connect(macos_integration.configure_window)
        for window in app.allWindows():
            macos_integration.configure_window(window)
        # The QML shell intentionally stays hidden until the native toolbar is
        # attached. This keeps AppKit's frame adjustment out of persisted size.
        root_window.setProperty("startupChromeReady", True)
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
