"""Persist application appearance and release explicit overrides in system mode."""

import pytest
from PySide6.QtCore import QCoreApplication, QSettings, Qt

from ui.qml_backend.features.theme_bridge import ThemeBridge
from ui.qml_backend.features.ui_state_bridge import UiStateBridge


class StyleHints:
    def __init__(self):
        self.scheme = None

    def setColorScheme(self, scheme):
        self.scheme = scheme


@pytest.mark.parametrize("stored,expected", [
    (None, "system"), ("system", "system"), ("light", "light"),
    ("dark", "dark"), ("invalid", "system"),
])
def test_theme_is_restored_before_windows_open(tmp_path, stored, expected):
    app = QCoreApplication.instance() or QCoreApplication([])
    ui = UiStateBridge(QSettings(str(tmp_path / "ui.ini"), QSettings.IniFormat))
    if stored is not None:
        ui.setStringValue("main.theme", stored)
    hints = StyleHints()
    theme = ThemeBridge(ui, style_hints=hints)
    assert theme.mode == expected
    assert hints.scheme == ThemeBridge.SCHEMES[expected]


def test_switching_theme_persists_and_system_releases_override(tmp_path):
    app = QCoreApplication.instance() or QCoreApplication([])
    settings_path = str(tmp_path / "ui.ini")
    ui = UiStateBridge(QSettings(settings_path, QSettings.IniFormat))
    hints = StyleHints()
    theme = ThemeBridge(ui, style_hints=hints)
    changes = []
    theme.modeChanged.connect(lambda: changes.append(theme.mode))
    for mode, scheme in [("dark", Qt.ColorScheme.Dark), ("light", Qt.ColorScheme.Light),
                         ("system", Qt.ColorScheme.Unknown)]:
        theme.setMode(mode)
        assert hints.scheme == scheme
        restored = ThemeBridge(UiStateBridge(QSettings(settings_path, QSettings.IniFormat)),
                               style_hints=StyleHints())
        assert restored.mode == mode
    theme.setMode("invalid")
    theme.setMode("system")
    assert theme.mode == "system"
    assert changes == ["dark", "light", "system"]
