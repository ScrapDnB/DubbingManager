"""QML entry point for Dubbing Manager."""

import logging
import os
import sys
from pathlib import Path


WINDOWS_UI_SCALE_DEFAULT = 75
WINDOWS_UI_SCALE_MINIMUM = 50
WINDOWS_UI_SCALE_MAXIMUM = 200


def _windows_ui_scale_percent() -> int:
    """Read the saved Qt UI scale without importing Qt before startup."""
    try:
        import winreg

        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\DubbingTools\Dubbing Manager\ui",
        ) as key:
            value, _kind = winreg.QueryValueEx(key, "main.uiScalePercent")
        return max(
            WINDOWS_UI_SCALE_MINIMUM,
            min(WINDOWS_UI_SCALE_MAXIMUM, int(value)),
        )
    except (ImportError, OSError, TypeError, ValueError):
        return WINDOWS_UI_SCALE_DEFAULT


def configure_windows_ui_scale(platform: str | None = None) -> None:
    """Apply the saved Windows UI scale without bypassing system DPI."""
    target_platform = platform or sys.platform
    if not target_platform.startswith("win"):
        return

    # QT_SCALE_FACTOR is multiplied by Qt's per-monitor system DPI factor, so
    # Windows scaling at 100-200% still works normally. An explicit
    # environment override remains useful for diagnostics on unusual display
    # setups and takes precedence over the saved application preference.
    if "QT_SCALE_FACTOR" not in os.environ:
        scale = _windows_ui_scale_percent() / 100
        os.environ["QT_SCALE_FACTOR"] = f"{scale:g}"


def configure_windows_dpi_awareness(platform: str | None = None) -> None:
    """Opt into Windows per-monitor DPI before Qt creates its first window."""
    target_platform = platform or sys.platform
    if not target_platform.startswith("win"):
        return

    # The packaged executable has no custom application manifest.  Marking the
    # process as Per Monitor V2 here lets Qt receive the same logical DPI that
    # Explorer and Windows Settings use, including after moving a window
    # between displays with different scaling.
    try:
        import ctypes

        user32 = ctypes.windll.user32
        set_context = user32.SetProcessDpiAwarenessContext
        set_context.argtypes = [ctypes.c_void_p]
        set_context.restype = ctypes.c_bool
        if set_context(ctypes.c_void_p(-4)):  # DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2
            return
    except (AttributeError, OSError):
        pass

    # Windows 8.1 and older Windows 10 versions do not expose Per Monitor V2.
    try:
        shcore = ctypes.windll.shcore
        if shcore.SetProcessDpiAwareness(2) == 0:  # PROCESS_PER_MONITOR_DPI_AWARE
            return
    except (AttributeError, OSError):
        pass

    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except (AttributeError, OSError):
        pass


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
# Set process-wide graphics and scaling choices before importing PySide6.
configure_platform_graphics()
configure_windows_dpi_awareness()
configure_windows_ui_scale()


from PySide6.QtCore import QEvent, QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtWebEngineQuick import QtWebEngineQuick

from app_startup import initial_project_path, setup_logging
from ui.macos_integration import MacOSIntegration
from ui.project_open_router import ProjectOpenRouter
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
        self.project_router: ProjectOpenRouter | None = None
        self._project_open_callback = None
        self._pending_project_paths: list[str] = []

    def event(self, event) -> bool:
        if event.type() == QEvent.FileOpen:
            path = event.file()
            if path:
                self.open_project_path(path)
                return True
        return super().event(event)

    def open_project_path(self, path: str) -> None:
        """Forward to the primary instance or open locally when this is it."""
        if (
            self.project_router is not None
            and not self.project_router.owns_listener
        ):
            if self.project_router.forward_project(path):
                return
            self.project_router.start_listener()
        if self._project_open_callback is None:
            self._pending_project_paths.append(path)
            return
        self._project_open_callback(path)

    def set_project_open_callback(self, callback) -> None:
        self._project_open_callback = callback
        pending, self._pending_project_paths = self._pending_project_paths, []
        for path in dict.fromkeys(pending):
            callback(path)


def main() -> int:
    """Run the QML application."""
    configure_platform_graphics()
    configure_windows_dpi_awareness()
    configure_windows_ui_scale()
    configure_qml_controls_style()
    setup_logging()
    QtWebEngineQuick.initialize()
    app = DubbingQmlApplication(sys.argv)
    app.setApplicationName("Dubbing Manager")
    app.setOrganizationName("DubbingTools")

    start_project = initial_project_path(sys.argv)
    project_router = ProjectOpenRouter(parent=app)
    app.project_router = project_router
    if start_project and project_router.forward_project(start_project):
        return 0
    owns_project_listener = project_router.start_listener()
    if (
        start_project
        and not owns_project_listener
        and project_router.forward_project(start_project)
    ):
        return 0
    app.aboutToQuit.connect(project_router.close)

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

    def open_project_in_current_window(path: str) -> None:
        try:
            current_path = (
                Path(bridge.project.path).expanduser().resolve()
                if bridge.project.path else None
            )
            requested_path = Path(path).expanduser().resolve()
        except OSError:
            current_path = None
            requested_path = Path(path)
        if current_path != requested_path:
            bridge.project.open(path)
        root_window.show()
        root_window.raise_()
        root_window.requestActivate()

    project_router.projectOpenRequested.connect(open_project_in_current_window)
    app.set_project_open_callback(open_project_in_current_window)
    if start_project:
        app.open_project_path(start_project)
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
