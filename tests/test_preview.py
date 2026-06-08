"""Tests for the live HTML preview settings."""

from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QSpinBox,
    QTextBrowser,
)

import ui.preview as preview_module
from ui.preview import HtmlLivePreview


def _app():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


class MainAppStub:
    def __init__(self):
        self.data = {
            "actors": {
                "actor-1": {"name": "Actor", "color": "#ffffff"},
            },
            "global_map": {"Hero": "actor-1"},
            "replica_merge_config": {"merge": False},
            "export_config": {
                "layout_type": "Таблица",
                "col_tc": True,
                "col_char": True,
                "col_actor": True,
                "col_text": True,
                "round_time": False,
                "time_display": "range",
                "f_time": 12,
                "f_char": 14,
                "f_actor": 14,
                "f_text": 16,
            }
        }
        self.dirty = False

    def get_episode_lines(self, ep_num):
        return [{
            "id": 1,
            "s": 0.0,
            "e": 2.0,
            "char": "Hero",
            "text": "Hello",
        }]

    def set_dirty(self, dirty=True):
        self.dirty = dirty


def _spin(value):
    spin = QSpinBox()
    spin.setRange(1, 100)
    spin.setValue(value)
    return spin


def test_preview_round_time_checkbox_updates_export_config():
    _app()
    preview = HtmlLivePreview.__new__(HtmlLivePreview)
    preview.main_app = MainAppStub()
    preview.update_preview = lambda: None

    preview.combo_layout = QComboBox()
    preview.combo_layout.addItem("Таблица", "Таблица")
    preview.chk_col_tc = QCheckBox()
    preview.chk_col_tc.setChecked(True)
    preview.chk_col_char = QCheckBox()
    preview.chk_col_char.setChecked(True)
    preview.chk_col_actor = QCheckBox()
    preview.chk_col_actor.setChecked(True)
    preview.chk_col_text = QCheckBox()
    preview.chk_col_text.setChecked(True)
    preview.chk_round_time = QCheckBox()
    preview.chk_round_time.setChecked(True)
    preview.combo_time_display = QComboBox()
    preview.combo_time_display.addItem("Начало и конец", "range")
    preview.s_time = _spin(13)
    preview.s_char = _spin(15)
    preview.s_actor = _spin(17)
    preview.s_text = _spin(19)

    preview.on_setting_change()

    cfg = preview.main_app.data["export_config"]
    assert cfg["round_time"] is True
    assert cfg["layout_type"] == "Таблица"
    assert cfg["f_time"] == 13
    assert preview.main_app.dirty is True


def test_preview_places_round_time_checkbox_below_timing_dropdown(monkeypatch):
    _app()
    monkeypatch.setattr(preview_module, "WEB_ENGINE_AVAILABLE", False)
    monkeypatch.setattr(preview_module, "QWebEngineView", QTextBrowser)
    main_app = MainAppStub()
    preview = HtmlLivePreview(main_app, "1")

    columns_layout = preview.chk_round_time.parentWidget().layout()
    timing_index = columns_layout.indexOf(preview.combo_time_display)
    round_index = columns_layout.indexOf(preview.chk_round_time)

    assert round_index == timing_index + 1
    preview.close()
