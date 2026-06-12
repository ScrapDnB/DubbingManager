"""Tests for switching episodes inside teleprompter."""

import pytest
from PySide6.QtCore import QEvent
from PySide6.QtWidgets import QApplication

from ui.teleprompter import TeleprompterWindow


@pytest.fixture
def app():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


class MainAppStub:
    def __init__(self):
        self.data = {
            "actors": {
                "actor-1": {"name": "Actor", "color": "#ffffff"},
                "actor-2": {"name": "Fresh Actor", "color": "#ffcc00"},
            },
            "global_map": {"Hero": "actor-1"},
            "episodes": {"1": "/tmp/ep1.ass", "2": "/tmp/ep2.ass"},
            "loaded_episodes": {},
            "replica_merge_config": {"merge": False},
            "prompter_config": {
                "f_tc": 12,
                "f_char": 16,
                "f_actor": 12,
                "f_text": 18,
                "focus_ratio": 0.45,
                "show_header": True,
                "is_mirrored": False,
                "sync_in": True,
                "sync_out": True,
                "port_in": 9000,
                "port_out": 9001,
                "colors": {
                    "bg": "#000000",
                    "header_bg": "#111111",
                    "header_text": "#ffffff",
                    "active_text": "#ffffff",
                    "inactive_text": "#777777",
                    "tc": "#cccccc",
                },
            },
        }
        self.dirty = False
        self.selected_episode = None
        self.prompter_color_presets = [None, None, None, None]

    def get_episode_lines(self, ep_num):
        start = 1.0 if str(ep_num) == "1" else 11.0
        return [{
            "id": 0,
            "s": start,
            "e": start + 1,
            "char": "Hero",
            "text": f"Line {ep_num}",
            "source_ids": [0],
        }]

    def save_global_prompter_settings(self, cfg):
        self.data["prompter_config"] = cfg

    def set_dirty(self, dirty=True):
        self.dirty = dirty

    def get_prompter_color_presets(self):
        return self.prompter_color_presets

    def save_prompter_color_preset(self, index, colors):
        self.prompter_color_presets[index] = colors
        return True


class DummySignal:
    def connect(self, callback):
        self.callback = callback


class DummyOscWorker:
    def __init__(self, port):
        self.port = port
        self.time_changed = DummySignal()
        self.navigation_requested = DummySignal()
        self.started = False
        self.stopped = False

    def start(self):
        self.started = True

    def stop(self):
        self.stopped = True


def test_switch_episode_keeps_filter_and_sync_settings(app):
    main_app = MainAppStub()
    window = TeleprompterWindow(main_app, "1")
    window.highlight_ids = ["actor-1"]
    window.btn_osc.setChecked(True)
    window.last_known_time = 123.0

    window.switch_episode("2")

    assert window.ep_num == "2"
    assert window.windowTitle() == "Телесуфлёр - Серия 2"
    assert window.highlight_ids == ["actor-1"]
    assert window.chk_follow_reaper.isChecked()
    assert window.chk_reaper_follow.isChecked()
    assert window.btn_osc.isChecked()
    assert window.list_of_replicas.item(0).text().endswith("Hero")
    assert window.last_known_time == 11.0

    window.close()


def test_osc_connection_state_is_saved_to_project(app, monkeypatch):
    monkeypatch.setattr("ui.teleprompter.OscWorker", DummyOscWorker)
    main_app = MainAppStub()
    main_app.data["prompter_config"]["osc_enabled"] = False
    window = TeleprompterWindow(main_app, "1")

    window.toggle_osc_connection_status(True)

    assert main_app.data["prompter_config"]["osc_enabled"] is True
    assert main_app.dirty is True
    assert window.btn_osc.text() == "OSC Связь: Активна"

    main_app.dirty = False
    window.toggle_osc_connection_status(False)

    assert main_app.data["prompter_config"]["osc_enabled"] is False
    assert main_app.dirty is True

    window.close()


def test_color_preset_button_saves_and_applies_colors(app):
    main_app = MainAppStub()
    window = TeleprompterWindow(main_app, "1")
    current_bg = window.cfg["colors"]["bg"]
    current_text = window.cfg["colors"]["active_text"]

    window.apply_or_save_color_preset(0)

    assert main_app.prompter_color_presets[0]["bg"] == current_bg
    assert main_app.prompter_color_presets[0]["active_text"] == current_text

    main_app.prompter_color_presets[1] = {
        **window.cfg["colors"],
        "bg": "#123456",
        "active_text": "#abcdef",
    }
    window.apply_or_save_color_preset(1)

    assert main_app.data["prompter_config"]["colors"]["bg"] == "#123456"
    assert main_app.data["prompter_config"]["colors"]["active_text"] == "#abcdef"
    assert main_app.dirty is True

    window.close()


def test_saving_color_preset_restores_teleprompter_window(app, monkeypatch):
    main_app = MainAppStub()
    window = TeleprompterWindow(main_app, "1")
    calls = []

    monkeypatch.setattr(
        "ui.teleprompter.QTimer.singleShot",
        lambda delay, callback: calls.append((delay, callback))
    )

    window.save_current_color_preset(0, ask=False)

    assert calls == [
        (0, window._activate_after_color_preset_action),
        (100, window._activate_after_color_preset_action),
    ]

    window.close()


def test_color_settings_dialog_restores_teleprompter_window(app, monkeypatch):
    main_app = MainAppStub()
    window = TeleprompterWindow(main_app, "1")
    calls = []

    class ColorDialogStub:
        def __init__(self, colors, parent):
            self.colors = colors
            self.parent = parent

        def exec(self):
            return True

        def get_final_colors(self):
            return {
                **window.cfg["colors"],
                "bg": "#112233",
            }

    monkeypatch.setattr(
        "ui.dialogs.colors.PrompterColorDialog",
        ColorDialogStub
    )
    monkeypatch.setattr(
        "ui.teleprompter.QTimer.singleShot",
        lambda delay, callback: calls.append((delay, callback))
    )

    window.open_color_settings_dialog()

    assert main_app.data["prompter_config"]["colors"]["bg"] == "#112233"
    assert calls == [
        (0, window._activate_after_color_preset_action),
        (100, window._activate_after_color_preset_action),
    ]

    window.close()


def test_manual_prompter_scroll_cancels_pending_smooth_scroll(app):
    main_app = MainAppStub()
    window = TeleprompterWindow(main_app, "1")
    window.cfg["sync_in"] = True
    window._scroll_target_y = 1500.0
    window.smooth_scroll_timer.start()

    window.eventFilter(window.prompter_view.viewport(), QEvent(QEvent.Wheel))

    assert window._manual_scroll_override is True
    assert window._scroll_target_y is None
    assert not window.smooth_scroll_timer.isActive()

    window.close()


def test_manual_scroll_override_ignores_reaper_until_explicit_jump(app):
    main_app = MainAppStub()
    window = TeleprompterWindow(main_app, "1")
    calls = []

    def fake_update(time_val):
        calls.append(time_val)

    window.update_view_position_by_time = fake_update
    window.enter_manual_scroll_override()

    window.on_osc_time_packet_received(42.0)

    assert calls == []
    assert window.last_known_time == 42.0
    assert window._manual_scroll_override is True

    window.jump_to_specific_time(1.0)

    assert calls == [1.0]
    assert window._manual_scroll_override is False

    window.close()


def test_refresh_cast_assignments_rebuilds_actor_names(app):
    main_app = MainAppStub()
    window = TeleprompterWindow(main_app, "1")

    main_app.data["global_map"]["Hero"] = "actor-2"
    window.btn_refresh_cast.click()

    scene_text = "\n".join(
        item.toPlainText()
        for item in window.prompter_scene.items()
        if hasattr(item, "toPlainText")
    )
    assert "(Fresh Actor)" in scene_text
    assert window.ep_num == "1"

    window.close()
