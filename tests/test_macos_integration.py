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
        integration.TELEPROMPTER,
        integration.MONTAGE,
        integration.REAPER,
        integration.AUDIOBOOK,
        integration.EPISODE_SUMMARY,
        integration.ROLES,
        integration.CONVERTER,
    }

    assert set(integration.ACTIONS) == expected
    assert all(label and symbol for label, symbol, _callback in integration.ACTIONS.values())


def test_auxiliary_window_keeps_standard_macos_title_bar(monkeypatch):
    monkeypatch.setattr(macos_integration, "NSWindowTitleHidden", 1, raising=False)
    monkeypatch.setattr(
        macos_integration,
        "NSTitlebarSeparatorStyleNone",
        0,
        raising=False,
    )
    monkeypatch.setattr(macos_integration, "NSWindowCloseButton", 0, raising=False)
    ns_window = Mock()
    close_button = Mock()
    ns_window.standardWindowButton_.return_value = close_button

    macos_integration.MacOSIntegration._configure_auxiliary_window(ns_window)

    ns_window.setTitlebarAppearsTransparent_.assert_called_once_with(True)
    ns_window.setTitleVisibility_.assert_called_once_with(1)
    ns_window.setTitlebarSeparatorStyle_.assert_called_once_with(0)
    ns_window.setMovableByWindowBackground_.assert_called_once_with(False)
    close_button.setEnabled_.assert_called_once_with(True)
