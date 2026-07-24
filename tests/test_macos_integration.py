"""Platform-boundary tests for the optional AppKit integration."""

from unittest.mock import Mock

from PySide6.QtCore import QCoreApplication

from ui import macos_integration


def _app() -> QCoreApplication:
    app = QCoreApplication.instance()
    if app is None:
        app = QCoreApplication([])
    return app


def test_macos_integration_is_a_safe_noop_on_other_platforms(monkeypatch):
    _app()
    monkeypatch.setattr(macos_integration.sys, "platform", "win32")
    integration = macos_integration.MacOSIntegration()
    window = Mock()
    project = Mock()

    integration.configure_main_window(window, project)
    integration.configure_window(window)
    integration.showToolTip("Подсказка", 10, 10)
    integration.hideToolTip()
    integration.showComboMenu("combo-1", ["Первый"], 0, 10, 10)

    assert not integration.available
    assert not integration.nativeToolbarActive
    assert not integration.liquidGlassAvailable
    assert integration.toolbar_identifiers == list(integration.ACTIONS)
    window.winId.assert_not_called()


def test_native_toolbar_defines_every_project_action_once():
    integration = macos_integration.MacOSIntegration()

    expected = {
        integration.NEW,
        integration.OPEN,
        integration.SAVE,
        integration.SAVE_AS,
        integration.SETTINGS,
        integration.PROJECT_SETTINGS,
        integration.UNDO,
        integration.REDO,
        integration.HEALTH,
        integration.ABOUT,
    }

    assert set(integration.ACTIONS) == expected
    assert all(label and symbol for label, symbol, _callback in integration.ACTIONS.values())
