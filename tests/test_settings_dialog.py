"""Тесты единого окна настроек."""

import pytest
from PySide6.QtWidgets import QApplication

from ui.dialogs.settings import SettingsDialog


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
            "use_color": True,
            "allow_edit": True,
            "round_time": False,
            "time_display": "range",
            "open_auto": True,
            "highlight_ids_export": ["actor1"],
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
    assert dialog.tabs.tabText(0) == "Главные"
    assert dialog.tabs.tabText(5) == "Базы актёров"
    assert dialog.export_layout_type.currentText() == "Таблица"
    assert dialog.project_name_edit.text() == "Test"
    assert dialog.project_created_by_edit.text() == "Producer"
    assert dialog.project_studio_edit.text() == "Studio One"
    assert dialog.highlight_ids_export == ["actor1"]
    assert dialog.merge_enabled.isChecked() is True
    assert dialog.prompter_port_in.value() == 8000
    assert dialog.docx_time_separators.text() == "-, –"


def test_settings_dialog_returns_updated_settings(app, project_data):
    dialog = SettingsDialog(project_data)

    dialog.export_layout_type.setCurrentText("Сценарий")
    dialog.merge_enabled.setChecked(False)
    dialog.merge_fps.setValue(30.0)
    dialog.merge_gap.setValue(0.5)
    dialog.prompter_sync_in.setChecked(False)
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
    assert settings["replica_merge_config"]["merge"] is False
    assert settings["replica_merge_config"]["merge_gap"] == 15
    assert settings["prompter_config"]["sync_in"] is False
    assert settings["prompter_config"]["reaper_offset_enabled"] is True
    assert settings["prompter_config"]["colors"]["bg"] == "#000000"
    assert settings["docx_import_config"]["time_separators"] == ["-", "|"]


def test_settings_dialog_falls_back_to_default_docx_separator(app, project_data):
    dialog = SettingsDialog(project_data)

    dialog.docx_time_separators.setText("")
    settings = dialog.get_settings()

    assert settings["docx_import_config"]["time_separators"] == ["-"]


def test_settings_dialog_opens_requested_tab(app, project_data):
    dialog = SettingsDialog(project_data, initial_tab="prompter")

    assert dialog.tabs.currentIndex() == 3


def test_settings_dialog_opens_actor_bases_tab(app, project_data):
    dialog = SettingsDialog(project_data, initial_tab="actor_bases")

    assert dialog.tabs.currentIndex() == 5


def test_global_settings_dialog_contains_only_global_tabs(app, project_data):
    dialog = SettingsDialog(project_data, settings_scope="global")

    assert dialog.windowTitle() == "Настройки"
    assert dialog.tabs.count() == 2
    assert dialog.tabs.tabText(0) == "Базы актёров"
    assert dialog.tabs.tabText(1) == "Интерфейс"
    settings = dialog.get_settings()
    assert set(settings.keys()) == {"language"}
