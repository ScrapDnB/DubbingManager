import pytest
from PySide6.QtWidgets import QApplication

from ui.main_window import MainWindow


@pytest.fixture(scope="module")
def app():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


@pytest.fixture
def window(app, tmp_path, monkeypatch):
    settings_file = tmp_path / "global_settings.json"
    monkeypatch.setattr(
        "services.global_settings_service.SETTINGS_FILE",
        settings_file
    )
    return MainWindow()


def test_update_ep_list_clears_main_table_when_project_has_no_episodes(window):
    window.current_ep_stats = [
        {"name": "Old Character", "lines": 1, "rings": 1, "words": 2}
    ]
    window.refresh_main_table()
    assert window.main_table_model.rowCount() == 1

    window.data["episodes"] = {}
    window.update_ep_list()

    assert window.current_ep_stats == []
    assert window.main_table_model.rowCount() == 0


def test_global_actor_mode_shows_global_actor_base(window):
    window.global_settings_service.settings = window.global_settings
    window.global_settings["global_actor_base"] = {}
    window.global_settings_service.add_global_actor(
        "Global Actor",
        "#123456",
        actor_id="global1",
        gender="Ж"
    )

    window.actor_base_mode.setCurrentIndex(
        window.actor_base_mode.findData("global")
    )

    assert window.actor_table.rowCount() == 1
    assert window.actor_table.item(0, 0).text() == "Global Actor"
    assert window.actor_table.item(0, 3).text() == "Ж"
    assert window.btn_add_actor.isEnabled()
    assert window.btn_add_project_actors_to_global.text() == "В проект"


def test_global_actor_mode_marks_actors_already_in_project(window):
    window.data["actors"] = {
        "project_actor": {"name": "Busy Actor", "color": "#FF0000"}
    }
    window.global_settings_service.settings = window.global_settings
    window.global_settings["global_actor_base"] = {}
    window.global_settings_service.add_global_actor(
        "Busy Actor",
        "#123456",
        actor_id="global1"
    )
    window.global_settings_service.add_global_actor(
        "Free Actor",
        "#654321",
        actor_id="global2"
    )

    window.actor_base_mode.setCurrentIndex(
        window.actor_base_mode.findData("global")
    )

    rows = {
        window.actor_table.item(row, 0).text(): window.actor_table.item(row, 1).text()
        for row in range(window.actor_table.rowCount())
    }
    assert rows["Busy Actor"] == "В проекте"
    assert rows["Free Actor"] == ""


def test_global_actor_gender_can_be_edited_in_table(window):
    window.global_settings_service.settings = window.global_settings
    window.global_settings["global_actor_base"] = {}
    window.global_settings_service.add_global_actor(
        "Editable Actor",
        "#123456",
        actor_id="global1",
    )
    window.actor_base_mode.setCurrentIndex(
        window.actor_base_mode.findData("global")
    )

    gender_item = window.actor_table.item(0, 3)
    gender_item.setText("F")

    assert window.global_settings_service.get_global_actor_base()["global1"]["gender"] == "Ж"


def test_selected_global_actor_can_be_added_to_project(window):
    window.global_settings_service.settings = window.global_settings
    window.global_settings["global_actor_base"] = {}
    window.global_settings_service.add_global_actor(
        "Global Actor",
        "#123456",
        actor_id="global1",
        gender="М"
    )
    window.actor_base_mode.setCurrentIndex(
        window.actor_base_mode.findData("global")
    )
    window.actor_table.selectRow(0)

    window.add_selected_global_actor_to_project()

    actors = list(window.data["actors"].values())
    assert len(actors) == 1
    assert actors[0]["name"] == "Global Actor"
    assert actors[0]["color"] == "#123456"
    assert actors[0]["gender"] == "М"
    rows = {
        window.actor_table.item(row, 0).text(): window.actor_table.item(row, 1).text()
        for row in range(window.actor_table.rowCount())
    }
    assert rows["Global Actor"] == "В проекте"


def test_project_actors_sync_with_global_base_by_name(window):
    window.global_settings_service.settings = window.global_settings
    window.global_settings["global_actor_base"] = {}
    window.global_settings_service.add_global_actor(
        "Same Actor",
        "#123456",
        actor_id="global1",
        gender="Ж"
    )
    window.data["actors"] = {
        "project1": {
            "name": "Same Actor",
            "color": "#FFFFFF",
            "gender": "",
        }
    }
    window.data["global_map"] = {"Hero": "project1"}
    window.data["episode_actor_map"] = {"1": {"Hero": "project1"}}
    window.data["export_config"]["highlight_ids_export"] = ["project1"]

    changed = window._sync_project_actors_with_global_base()

    assert changed == 1
    assert "project1" not in window.data["actors"]
    assert window.data["actors"]["global1"]["gender"] == "Ж"
    assert window.data["actors"]["global1"]["color"] == "#123456"
    assert window.data["global_map"]["Hero"] == "global1"
    assert window.data["episode_actor_map"]["1"]["Hero"] == "global1"
    assert window.data["export_config"]["highlight_ids_export"] == ["global1"]


def test_project_actor_with_global_id_gets_missing_gender(window):
    window.global_settings_service.settings = window.global_settings
    window.global_settings["global_actor_base"] = {}
    window.global_settings_service.add_global_actor(
        "Same Actor",
        "#123456",
        actor_id="global1",
        gender="М"
    )
    window.data["actors"] = {
        "global1": {
            "name": "Same Actor",
            "color": "#FFFFFF",
            "gender": "",
        }
    }

    changed = window._sync_project_actors_with_global_base()

    assert changed == 1
    assert window.data["actors"]["global1"]["gender"] == "М"
