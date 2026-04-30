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
                "actor-1": {"name": "Actor", "color": "#ffffff"}
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
