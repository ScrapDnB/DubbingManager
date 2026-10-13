"""Application appearance preference backed by the platform's Qt palette."""

from PySide6.QtCore import QObject, Property, Qt, Signal, Slot
from PySide6.QtGui import QGuiApplication


class ThemeBridge(QObject):
    modeChanged = Signal()
    SCHEMES = {
        "light": Qt.ColorScheme.Light,
        "dark": Qt.ColorScheme.Dark,
        "system": Qt.ColorScheme.Unknown,
    }

    def __init__(self, ui_state, parent=None, *, style_hints=None):
        super().__init__(parent)
        self._ui_state = ui_state
        stored = ui_state.stringValue("main.theme", "system")
        self._mode = stored if stored in self.SCHEMES else "system"
        self._style_hints = style_hints
        if self._style_hints is None and isinstance(QGuiApplication.instance(), QGuiApplication):
            self._style_hints = QGuiApplication.styleHints()
        self._apply()

    @Property(str, notify=modeChanged)
    def mode(self):
        return self._mode

    @Slot(str)
    def setMode(self, mode):
        if mode not in self.SCHEMES or mode == self._mode:
            return
        self._mode = mode
        self._ui_state.setStringValue("main.theme", mode)
        self._apply()
        self.modeChanged.emit()

    def _apply(self):
        if self._style_hints is not None:
            # Unknown removes the override and follows future system changes.
            self._style_hints.setColorScheme(self.SCHEMES[self._mode])
