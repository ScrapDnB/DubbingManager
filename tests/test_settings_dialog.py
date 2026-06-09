"""Тесты единого окна настроек."""

import pytest
from PySide6.QtWidgets import QApplication, QMessageBox, QWidget

from ui.dialogs.settings import SettingsDialog


class DummySettingsParent(QWidget):
    def __init__(
        self,
        default_export_config,
        default_prompter_config=None,
    ):
        super().__init__()
        self.global_settings = {"language": "ru"}
        self.global_settings_service = self
        self.saved_default_export_config = None
        self.saved_default_prompter_config = None
        self.applied_default_export_config = default_export_config
        self.applied_default_prompter_config = default_prompter_config or {}
        self.prompter_color_presets = [None, None, None, None]
        self.applied_export_config = None
        self.applied_prompter_config = None

    def get_default_export_config(self):
        return self.applied_default_export_config

    def get_default_prompter_config(self):
        return self.applied_default_prompter_config

    def save_default_export_config(self, config):
        self.saved_default_export_config = config
        return True

    def save_default_prompter_config(self, config):
        self.saved_default_prompter_config = config
        return True

    def apply_default_export_config_to_project(self):
        return self.applied_default_export_config

    def apply_default_prompter_config_to_project(self):
        return self.applied_default_prompter_config

    def apply_export_config_to_project(self, config):
        self.applied_export_config = config
        return config

    def apply_prompter_config_to_project(self, config):
        self.applied_prompter_config = config
        return config

    def get_prompter_color_presets(self):
        return self.prompter_color_presets

    def clear_prompter_color_preset(self, index):
        self.prompter_color_presets[index] = None
        return True


@pytest.fixture
def app():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


@pytest.fixture
def project_data():
    return {
        "project_name": "Test",
        "metadata": {
            "created_by": "Producer",
            "studio": "Studio One",
        },
        "project_folder": "/tmp/project",
        "actors": {
            "actor1": {"name": "Actor One"},
            "actor2": {"name": "Actor Two"},
        },
        "episodes": {"1": "/tmp/episode.ass"},
        "episode_texts": {"1": "/tmp/text.json"},
        "export_config": {
            "layout_type": "Таблица",
            "col_tc": True,
            "col_char": True,
            "col_actor": True,
            "col_text": True,
            "f_time": 21,
            "f_char": 20,
            "f_actor": 14,
            "f_text": 30,
            "table_width_time": 7.0,
            "table_width_char": 10.0,
            "table_width_actor": 8.5,
            "use_color": True,
            "soften_colors": True,
            "allow_edit": True,
            "round_time": False,
            "time_display": "range",
            "open_auto": True,
            "highlight_ids_export": ["actor1"],
            "highlight_negative_ids_export": ["actor1"],
        },
        "replica_merge_config": {
            "merge": True,
            "merge_gap": 120,
            "fps": 25,
            "p_short": 0.5,
            "p_long": 2.0,
        },
        "prompter_config": {
            "f_tc": 20,
            "f_char": 24,
            "f_actor": 18,
            "f_text": 36,
            "focus_ratio": 0.5,
            "is_mirrored": False,
            "show_header": False,
            "port_in": 8000,
            "port_out": 9000,
            "osc_enabled": False,
            "sync_in": True,
            "sync_out": False,
            "reaper_offset_enabled": False,
            "reaper_offset_seconds": -2.0,
            "scroll_smoothness_slider": 18,
            "colors": {"bg": "#000000"},
        },
        "docx_import_config": {
            "mapping": {"character": 0, "text": 1},
            "time_separators": ["-", "–"],
        },
    }


def test_settings_dialog_creation(app, project_data):
    dialog = SettingsDialog(project_data)

    assert dialog.windowTitle() == "Настройки проекта"
    assert dialog.tabs.currentIndex() == 0
    assert dialog.tabs.tabText(0) == "Проект"
    assert dialog.tabs.tabText(1) == "Серии и файлы"
    assert dialog.tabs.tabText(2) == "Роли"
    assert dialog.tabs.tabText(3) == "Монтажный лист"
    assert dialog.tabs.tabText(6) == "Перенос"
    assert dialog.export_layout_type.currentText() == "Таблица"
    assert dialog.project_name_edit.text() == "Test"
    assert dialog.project_created_by_edit.text() == "Producer"
    assert dialog.project_studio_edit.text() == "Studio One"
    assert dialog.highlight_ids_export == ["actor1"]
    assert dialog.highlight_negative_ids_export == ["actor1"]
    assert dialog.merge_enabled.isChecked() is True
    assert dialog.prompter_port_in.value() == 8000
    assert dialog.docx_time_separators.text() == "-, –"


def test_settings_dialog_returns_updated_settings(app, project_data):
    dialog = SettingsDialog(project_data)

    dialog.export_layout_type.setCurrentText("Сценарий")
    dialog.export_table_width_time.setValue(6.5)
    dialog.export_table_width_char.setValue(11.5)
    dialog.export_table_width_actor.setValue(9.5)
    dialog.export_soften_colors.setChecked(False)
    dialog.merge_enabled.setChecked(False)
    dialog.merge_fps.setValue(30.0)
    dialog.merge_gap.setValue(0.5)
    dialog.prompter_sync_in.setChecked(False)
    dialog.prompter_osc_enabled.setChecked(True)
    dialog.prompter_offset_enabled.setChecked(True)
    dialog.docx_time_separators.setText("-, |")
    dialog.project_name_edit.setText("Updated Project")
    dialog.project_created_by_edit.setText("Editor")
    dialog.project_studio_edit.setText("Studio Two")

    settings = dialog.get_settings()

    assert settings["project_name"] == "Updated Project"
    assert settings["metadata"]["created_by"] == "Editor"
    assert settings["metadata"]["studio"] == "Studio Two"
    assert settings["export_config"]["layout_type"] == "Сценарий"
    assert settings["export_config"]["highlight_ids_export"] == ["actor1"]
    assert settings["export_config"]["table_width_time"] == 6.5
    assert settings["export_config"]["table_width_char"] == 11.5
    assert settings["export_config"]["table_width_actor"] == 9.5
    assert settings["export_config"]["soften_colors"] is False
    assert settings["export_config"]["highlight_negative_ids_export"] == ["actor1"]
    assert settings["replica_merge_config"]["merge"] is False
    assert settings["replica_merge_config"]["merge_gap"] == 15
    assert settings["prompter_config"]["sync_in"] is False
    assert settings["prompter_config"]["osc_enabled"] is True
    assert settings["prompter_config"]["reaper_offset_enabled"] is True
    assert settings["prompter_config"]["colors"]["bg"] == "#000000"
    assert settings["docx_import_config"]["time_separators"] == ["-", "|"]


def test_settings_dialog_saves_export_defaults_after_confirmation(
    app,
    project_data,
    monkeypatch,
):
    parent = DummySettingsParent({})
    dialog = SettingsDialog(project_data, parent=parent)
    dialog.export_layout_type.setCurrentText("Сценарий")
    dialog.export_col_tc.setChecked(False)

    monkeypatch.setattr(
        QMessageBox,
        "question",
        lambda *args, **kwargs: QMessageBox.Yes,
    )
    monkeypatch.setattr(QMessageBox, "information", lambda *args, **kwargs: None)

    dialog._save_export_defaults()

    assert parent.saved_default_export_config["layout_type"] == "Сценарий"
    assert parent.saved_default_export_config["col_tc"] is False
    assert parent.saved_default_export_config["highlight_ids_export"] == ["actor1"]
    assert (
        parent.saved_default_export_config["highlight_negative_ids_export"] ==
        ["actor1"]
    )


def test_settings_dialog_applies_export_defaults_after_confirmation(
    app,
    project_data,
    monkeypatch,
):
    default_export_config = {
        "layout_type": "Сценарий",
        "col_tc": False,
        "col_actor": False,
        "round_time": True,
        "time_display": "start",
        "highlight_ids_export": ["actor2"],
        "highlight_negative_ids_export": ["actor2"],
    }
    parent = DummySettingsParent(default_export_config)
    dialog = SettingsDialog(project_data, parent=parent)

    monkeypatch.setattr(
        QMessageBox,
        "question",
        lambda *args, **kwargs: QMessageBox.Yes,
    )
    monkeypatch.setattr(QMessageBox, "information", lambda *args, **kwargs: None)

    dialog._apply_export_defaults_to_project()
    settings = dialog.get_settings()

    assert settings["export_config"]["layout_type"] == "Сценарий"
    assert settings["export_config"]["col_tc"] is False
    assert settings["export_config"]["col_actor"] is False
    assert settings["export_config"]["round_time"] is True
    assert settings["export_config"]["time_display"] == "start"
    assert settings["export_config"]["highlight_ids_export"] == ["actor2"]
    assert settings["export_config"]["highlight_negative_ids_export"] == ["actor2"]


def test_settings_dialog_saves_prompter_defaults_after_confirmation(
    app,
    project_data,
    monkeypatch,
):
    parent = DummySettingsParent({})
    dialog = SettingsDialog(project_data, parent=parent, initial_tab="prompter")
    dialog.prompter_f_text.setValue(48)
    dialog.prompter_osc_enabled.setChecked(True)
    dialog.prompter_sync_in.setChecked(False)

    monkeypatch.setattr(
        QMessageBox,
        "question",
        lambda *args, **kwargs: QMessageBox.Yes,
    )
    monkeypatch.setattr(QMessageBox, "information", lambda *args, **kwargs: None)

    dialog._save_prompter_defaults()

    assert parent.saved_default_prompter_config["f_text"] == 48
    assert parent.saved_default_prompter_config["osc_enabled"] is True
    assert parent.saved_default_prompter_config["sync_in"] is False
    assert parent.saved_default_prompter_config["colors"]["bg"] == "#000000"


def test_settings_dialog_applies_prompter_defaults_after_confirmation(
    app,
    project_data,
    monkeypatch,
):
    default_prompter_config = {
        "f_text": 52,
        "focus_ratio": 0.35,
        "osc_enabled": True,
        "is_mirrored": True,
        "colors": {"bg": "#101010"},
    }
    parent = DummySettingsParent({}, default_prompter_config)
    dialog = SettingsDialog(project_data, parent=parent, initial_tab="prompter")

    monkeypatch.setattr(
        QMessageBox,
        "question",
        lambda *args, **kwargs: QMessageBox.Yes,
    )
    monkeypatch.setattr(QMessageBox, "information", lambda *args, **kwargs: None)

    dialog._apply_prompter_defaults_to_project()
    settings = dialog.get_settings()

    assert settings["prompter_config"]["f_text"] == 52
    assert settings["prompter_config"]["focus_ratio"] == 0.35
    assert settings["prompter_config"]["osc_enabled"] is True
    assert settings["prompter_config"]["is_mirrored"] is True
    assert settings["prompter_config"]["colors"]["bg"] == "#101010"


def test_settings_dialog_falls_back_to_default_docx_separator(app, project_data):
    dialog = SettingsDialog(project_data)

    dialog.docx_time_separators.setText("")
    settings = dialog.get_settings()

    assert settings["docx_import_config"]["time_separators"] == ["-"]


def test_settings_dialog_opens_requested_tab(app, project_data):
    dialog = SettingsDialog(project_data, initial_tab="prompter")

    assert dialog.tabs.currentIndex() == 5


def test_settings_dialog_opens_actor_bases_tab(app, project_data):
    dialog = SettingsDialog(project_data, initial_tab="actor_bases")

    assert dialog.tabs.currentIndex() == 6


def test_global_settings_dialog_contains_only_global_tabs(app, project_data):
    dialog = SettingsDialog(project_data, settings_scope="global")

    assert dialog.windowTitle() == "Настройки"
    assert dialog.tabs.count() == 4
    assert dialog.tabs.tabText(0) == "Монтажный лист"
    assert dialog.tabs.tabText(1) == "Телесуфлёр"
    assert dialog.tabs.tabText(2) == "Актёры"
    assert dialog.tabs.tabText(3) == "Интерфейс"
    settings = dialog.get_settings()
    assert set(settings.keys()) == {
        "language",
        "default_export_config",
        "default_prompter_config",
    }
    assert settings["default_export_config"]["layout_type"] == "Таблица"
    assert settings["default_prompter_config"]["f_text"] == 36


def test_global_settings_dialog_uses_default_export_config(app, project_data):
    default_export_config = {
        "layout_type": "Сценарий",
        "col_tc": False,
        "time_display": "start",
    }
    parent = DummySettingsParent(default_export_config)
    dialog = SettingsDialog(
        project_data,
        parent=parent,
        settings_scope="global",
    )

    settings = dialog.get_settings()

    assert settings["default_export_config"]["layout_type"] == "Сценарий"
    assert settings["default_export_config"]["col_tc"] is False
    assert settings["default_export_config"]["time_display"] == "start"


def test_global_settings_dialog_uses_default_prompter_config(app, project_data):
    default_prompter_config = {
        "f_text": 54,
        "focus_ratio": 0.4,
        "osc_enabled": True,
        "sync_out": True,
    }
    parent = DummySettingsParent({}, default_prompter_config)
    dialog = SettingsDialog(
        project_data,
        parent=parent,
        settings_scope="global",
        initial_tab="prompter",
    )

    settings = dialog.get_settings()

    assert settings["default_prompter_config"]["f_text"] == 54
    assert settings["default_prompter_config"]["focus_ratio"] == 0.4
    assert settings["default_prompter_config"]["osc_enabled"] is True
    assert settings["default_prompter_config"]["sync_out"] is True


def test_global_settings_dialog_applies_current_export_config_to_project(
    app,
    project_data,
    monkeypatch,
):
    parent = DummySettingsParent({})
    dialog = SettingsDialog(
        project_data,
        parent=parent,
        settings_scope="global",
    )
    dialog.export_layout_type.setCurrentText("Сценарий")
    dialog.export_col_actor.setChecked(False)

    monkeypatch.setattr(
        QMessageBox,
        "question",
        lambda *args, **kwargs: QMessageBox.Yes,
    )
    monkeypatch.setattr(QMessageBox, "information", lambda *args, **kwargs: None)

    dialog._apply_global_export_to_project()

    assert parent.applied_export_config["layout_type"] == "Сценарий"
    assert parent.applied_export_config["col_actor"] is False


def test_global_settings_dialog_applies_current_prompter_config_to_project(
    app,
    project_data,
    monkeypatch,
):
    parent = DummySettingsParent({})
    dialog = SettingsDialog(
        project_data,
        parent=parent,
        settings_scope="global",
        initial_tab="prompter",
    )
    dialog.prompter_f_text.setValue(50)
    dialog.prompter_osc_enabled.setChecked(True)
    dialog.prompter_mirrored.setChecked(True)

    monkeypatch.setattr(
        QMessageBox,
        "question",
        lambda *args, **kwargs: QMessageBox.Yes,
    )
    monkeypatch.setattr(QMessageBox, "information", lambda *args, **kwargs: None)

    dialog._apply_global_prompter_to_project()

    assert parent.applied_prompter_config["f_text"] == 50
    assert parent.applied_prompter_config["osc_enabled"] is True
    assert parent.applied_prompter_config["is_mirrored"] is True


def test_global_settings_dialog_clears_prompter_color_preset(
    app,
    project_data,
    monkeypatch,
):
    parent = DummySettingsParent({})
    parent.prompter_color_presets[0] = {
        "bg": "#111111",
        "active_text": "#eeeeee",
    }
    dialog = SettingsDialog(
        project_data,
        parent=parent,
        settings_scope="global",
        initial_tab="prompter",
    )

    monkeypatch.setattr(
        QMessageBox,
        "question",
        lambda *args, **kwargs: QMessageBox.Yes,
    )

    dialog._clear_prompter_color_preset(0)

    assert parent.prompter_color_presets[0] is None
    assert not dialog.prompter_preset_reset_buttons[0].isEnabled()
