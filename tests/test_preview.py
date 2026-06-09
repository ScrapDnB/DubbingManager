"""Tests for the live HTML preview settings."""

from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QGroupBox,
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
            "episodes": {
                "1": "/tmp/episode-1.ass",
                "2": "/tmp/episode-2.ass",
                "10": "/tmp/episode-10.ass",
            },
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
                "soften_colors": True,
                "highlight_negative_ids_export": [],
            }
        }
        self.dirty = False
        self.switched_to = []

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

    def switch_to_episode(self, ep_num):
        self.switched_to.append(ep_num)


def _spin(value):
    spin = QSpinBox()
    spin.setRange(1, 100)
    spin.setValue(value)
    return spin


def _width_spin(value):
    spin = QDoubleSpinBox()
    spin.setRange(4.0, 24.0)
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
    preview.s_width_time = _width_spin(6.5)
    preview.s_width_char = _width_spin(11.5)
    preview.s_width_actor = _width_spin(9.5)
    preview.chk_soften_colors = QCheckBox()
    preview.chk_soften_colors.setChecked(False)
    preview.table_widths_group = QGroupBox()

    preview.on_setting_change()

    cfg = preview.main_app.data["export_config"]
    assert cfg["round_time"] is True
    assert cfg["layout_type"] == "Таблица"
    assert cfg["f_time"] == 13
    assert cfg["table_width_time"] == 6.5
    assert cfg["table_width_char"] == 11.5
    assert cfg["table_width_actor"] == 9.5
    assert cfg["soften_colors"] is False
    assert preview.main_app.dirty is True


def test_preview_syncs_controls_from_export_config():
    _app()
    preview = HtmlLivePreview.__new__(HtmlLivePreview)
    preview.main_app = MainAppStub()
    calls = []
    preview.update_preview = lambda: calls.append(True)

    preview.combo_layout = QComboBox()
    preview.combo_layout.addItem("Таблица", "Таблица")
    preview.combo_layout.addItem("Сценарий", "Сценарий")
    preview.chk_col_tc = QCheckBox()
    preview.chk_col_char = QCheckBox()
    preview.chk_col_actor = QCheckBox()
    preview.chk_col_text = QCheckBox()
    preview.chk_round_time = QCheckBox()
    preview.combo_time_display = QComboBox()
    preview.combo_time_display.addItem("Начало и конец", "range")
    preview.combo_time_display.addItem("Только начало", "start")
    preview.s_time = _spin(12)
    preview.s_char = _spin(14)
    preview.s_actor = _spin(14)
    preview.s_text = _spin(16)
    preview.s_width_time = QDoubleSpinBox()
    preview.s_width_time.setRange(4.0, 24.0)
    preview.s_width_char = QDoubleSpinBox()
    preview.s_width_char.setRange(4.0, 24.0)
    preview.s_width_actor = QDoubleSpinBox()
    preview.s_width_actor.setRange(4.0, 24.0)
    preview.chk_soften_colors = QCheckBox()
    preview.table_widths_group = QGroupBox()

    preview.main_app.data["export_config"].update({
        "layout_type": "Сценарий",
        "col_tc": False,
        "col_char": False,
        "col_actor": True,
        "col_text": True,
        "round_time": True,
        "time_display": "start",
        "f_time": 18,
        "f_char": 19,
        "f_actor": 20,
        "f_text": 21,
        "table_width_time": 6.5,
        "table_width_char": 11.5,
        "table_width_actor": 9.5,
        "soften_colors": False,
        "highlight_ids_export": ["actor-1"],
        "highlight_negative_ids_export": ["actor-1"],
    })

    preview.sync_export_settings()

    assert preview.combo_layout.currentData() == "Сценарий"
    assert preview.chk_col_tc.isChecked() is False
    assert preview.chk_col_char.isChecked() is False
    assert preview.chk_col_actor.isChecked() is True
    assert preview.chk_col_text.isChecked() is True
    assert preview.chk_round_time.isChecked() is True
    assert preview.combo_time_display.currentData() == "start"
    assert preview.s_time.value() == 18
    assert preview.s_char.value() == 19
    assert preview.s_actor.value() == 20
    assert preview.s_text.value() == 21
    assert preview.s_width_time.value() == 6.5
    assert preview.s_width_char.value() == 11.5
    assert preview.s_width_actor.value() == 9.5
    assert preview.chk_soften_colors.isChecked() is False
    assert preview.highlight_negative_ids == ["actor-1"]
    assert preview.table_widths_group.isVisible() is False
    assert preview.highlight_ids == ["actor-1"]
    assert calls == [True]


def test_preview_actor_filter_updates_export_config(monkeypatch):
    _app()
    preview = HtmlLivePreview.__new__(HtmlLivePreview)
    preview.main_app = MainAppStub()
    preview.main_app.data["actors"]["actor-2"] = {
        "name": "Second Actor",
        "color": "#000000",
    }
    preview.highlight_ids = None
    preview.highlight_negative_ids = []
    calls = []
    preview.update_preview = lambda: calls.append(True)

    class ActorFilterStub:
        def __init__(self, actors, current_selection, negative_ids, parent):
            self.current_selection = current_selection
            self.negative_ids = negative_ids

        def exec(self):
            return True

        def get_selected(self):
            return ["actor-1"]

        def get_negative_selected(self):
            return ["actor-1"]

    monkeypatch.setattr(preview_module, "ActorFilterDialog", ActorFilterStub)

    preview.open_actor_filter()

    assert preview.highlight_ids == ["actor-1"]
    assert (
        preview.main_app.data["export_config"]["highlight_ids_export"] ==
        ["actor-1"]
    )
    assert (
        preview.main_app.data["export_config"]["highlight_negative_ids_export"] ==
        ["actor-1"]
    )
    assert preview.main_app.dirty is True
    assert calls == [True]


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


def test_preview_episode_selector_switches_current_episode(monkeypatch):
    _app()
    monkeypatch.setattr(preview_module, "WEB_ENGINE_AVAILABLE", False)
    monkeypatch.setattr(preview_module, "QWebEngineView", QTextBrowser)
    main_app = MainAppStub()
    preview = HtmlLivePreview(main_app, "1")
    calls = []
    preview.update_preview = lambda: calls.append(preview.ep_num)

    preview.combo_episode.setCurrentIndex(preview.combo_episode.findData("2"))

    assert preview.ep_num == "2"
    assert main_app.switched_to == ["2"]
    assert calls == ["2"]
    assert "2" in preview.windowTitle()
    preview.close()
