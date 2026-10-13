"""Optional Windows 11 DWM chrome; Qt continues to own the system frame."""

import ctypes
import logging
import sys
from weakref import WeakSet

from PySide6.QtCore import QObject, Qt
from PySide6.QtGui import QGuiApplication

logger = logging.getLogger(__name__)


class WindowsIntegration(QObject):
    """Apply system dark titlebars, rounded corners, and supported Mica backdrop."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._window = None
        self._auxiliary_windows = WeakSet()

    def configure_main_window(self, window):
        if sys.platform != "win32":
            return
        self._window = window
        self._apply()
        QGuiApplication.styleHints().colorSchemeChanged.connect(self._apply)

    def configure_window(self, window):
        """Theme native tool/dialog frames without adding a custom titlebar."""
        if sys.platform != "win32" or window is None or window is self._window:
            return
        if (window.flags() & Qt.WindowType_Mask) not in (Qt.Window, Qt.Dialog):
            return
        self._auxiliary_windows.add(window)
        self._apply_window(window, backdrop=False)

    def _apply(self, *_args):
        if self._window is None:
            return
        self._apply_window(self._window, backdrop=True)
        for window in list(self._auxiliary_windows):
            self._apply_window(window, backdrop=False)

    def _apply_window(self, window, *, backdrop):
        try:
            build = sys.getwindowsversion().build
            dark = QGuiApplication.styleHints().colorScheme() == Qt.ColorScheme.Dark
            dwm = ctypes.windll.dwmapi.DwmSetWindowAttribute
            dwm.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_void_p, ctypes.c_uint]
            dwm.restype = ctypes.c_long
            handle = ctypes.c_void_p(int(window.winId()))
            attributes = [(20, int(dark))]  # DWMWA_USE_IMMERSIVE_DARK_MODE
            if build >= 22000:
                attributes.append((33, 2))  # DWMWA_WINDOW_CORNER_PREFERENCE: round
            if backdrop and build >= 22621:
                attributes.append((38, 2))  # DWMWA_SYSTEMBACKDROP_TYPE: main window
            for attribute, value in attributes:
                data = ctypes.c_int(value)
                result = dwm(handle, attribute, ctypes.byref(data), ctypes.sizeof(data))
                if result < 0:
                    logger.debug("DWM attribute %s unavailable: %s", attribute, result)
        except (AttributeError, OSError, TypeError, RuntimeError):
            logger.debug("System window materials unavailable", exc_info=True)
