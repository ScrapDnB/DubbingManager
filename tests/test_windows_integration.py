"""DWM feature boundaries without requiring Windows on the test host."""
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from PySide6.QtCore import Qt

from ui import windows_integration as integration


def test_windows_integration_is_noop_on_other_platforms(monkeypatch):
    monkeypatch.setattr(integration.sys, "platform", "darwin")
    window = Mock()
    native = integration.WindowsIntegration()
    native.configure_main_window(window)
    window.winId.assert_not_called()


@pytest.mark.parametrize("build,expected", [
    (19045, [20]), (22000, [20, 33]), (22621, [20, 33, 38]),
])
def test_dwm_attributes_follow_os_support(monkeypatch, build, expected):
    monkeypatch.setattr(integration.sys, "platform", "win32")
    monkeypatch.setattr(integration.sys, "getwindowsversion", lambda: SimpleNamespace(build=build), raising=False)
    dwm = Mock(return_value=0)
    monkeypatch.setattr(integration.ctypes, "windll", SimpleNamespace(dwmapi=SimpleNamespace(DwmSetWindowAttribute=dwm)), raising=False)
    hints = Mock()
    hints.colorScheme.return_value = Qt.ColorScheme.Dark
    monkeypatch.setattr(integration, "QGuiApplication", SimpleNamespace(styleHints=lambda: hints))
    window = Mock()
    window.winId.return_value = 123
    native = integration.WindowsIntegration()
    native.configure_main_window(window)
    assert [call.args[1] for call in dwm.call_args_list] == expected
    hints.colorSchemeChanged.connect.assert_called_once()


def test_dwm_failure_does_not_block_window_startup(monkeypatch):
    monkeypatch.setattr(integration.sys, "platform", "win32")
    monkeypatch.setattr(integration.sys, "getwindowsversion", lambda: SimpleNamespace(build=22621), raising=False)
    monkeypatch.setattr(integration.ctypes, "windll", SimpleNamespace(), raising=False)
    native = integration.WindowsIntegration()
    native.configure_main_window(Mock())


def test_auxiliary_windows_keep_native_frame_and_follow_theme(monkeypatch):
    monkeypatch.setattr(integration.sys, "platform", "win32")
    monkeypatch.setattr(integration.sys, "getwindowsversion", lambda: SimpleNamespace(build=22621), raising=False)
    dwm = Mock(return_value=0)
    monkeypatch.setattr(integration.ctypes, "windll", SimpleNamespace(dwmapi=SimpleNamespace(DwmSetWindowAttribute=dwm)), raising=False)
    hints = Mock()
    hints.colorScheme.return_value = Qt.ColorScheme.Dark
    monkeypatch.setattr(integration, "QGuiApplication", SimpleNamespace(styleHints=lambda: hints))
    main, tool, popup = Mock(), Mock(), Mock()
    main.winId.return_value = 100
    tool.winId.return_value = 200
    tool.flags.return_value = Qt.Window
    popup.flags.return_value = Qt.Popup
    native = integration.WindowsIntegration()
    native.configure_main_window(main)
    dwm.reset_mock()
    native.configure_window(tool)
    native.configure_window(popup)
    assert [call.args[1] for call in dwm.call_args_list] == [20, 33]
    popup.winId.assert_not_called()
    dwm.reset_mock()
    hints.colorScheme.return_value = Qt.ColorScheme.Light
    native._apply()
    assert [call.args[1] for call in dwm.call_args_list] == [20, 33, 38, 20, 33]
