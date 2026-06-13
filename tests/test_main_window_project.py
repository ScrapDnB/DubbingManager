import json
import pytest
from unittest.mock import Mock, patch
from PySide6.QtWidgets import QApplication, QMessageBox, QPushButton

from services.update_service import UpdateInfo
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


def test_update_check_can_run_from_about_button(window):
    button = QPushButton()
    window.update_service.check_for_updates = Mock(
        return_value=UpdateInfo("1.4.3", "1.4.3", "https://example.test", False)
    )

    with patch("ui.main_window.QMessageBox.information") as information:
        window.check_for_updates(button=button)

    assert button.isEnabled()
    information.assert_called_once()


def test_force_update_installs_even_when_version_is_current(window):
    update_info = UpdateInfo("1.4.3", "1.4.3", "https://example.test", False)
    window.update_service.check_for_updates = Mock(return_value=update_info)
    window.install_update = Mock()

    with patch(
        "ui.main_window.QMessageBox.question",
        return_value=QMessageBox.Yes
    ):
        window.check_for_updates(force_install=True)

    window.install_update.assert_called_once_with(update_info)


def test_update_closes_source_dialog_before_install(window):
    update_info = UpdateInfo("1.4.4", "1.4.3", "https://example.test", True)
    window.update_service.check_for_updates = Mock(return_value=update_info)
    source_dialog = Mock()
    calls = []

    source_dialog.close.side_effect = lambda: calls.append("close")
    window.install_update = Mock(side_effect=lambda _info: calls.append("install"))

    with patch(
        "ui.main_window.QMessageBox.question",
        return_value=QMessageBox.Yes
    ):
        window.check_for_updates(source_dialog=source_dialog)

    assert calls == ["close", "install"]


def test_sync_preview_export_settings_calls_open_preview(window):
    window.preview_window = Mock()

    window._sync_preview_export_settings()

    window.preview_window.sync_export_settings.assert_called_once_with(
        update_preview=True
    )


def test_open_exported_file_respects_open_auto(window):
    window.data["export_config"] = {"open_auto": False}

    with patch("ui.main_window.QDesktopServices.openUrl") as open_url:
        window._open_exported_file_if_needed("/tmp/export.docx")

    open_url.assert_not_called()


def test_open_exported_file_runs_when_open_auto_enabled(window):
    window.data["export_config"] = {"open_auto": True}

    with patch("ui.main_window.QDesktopServices.openUrl") as open_url:
        window._open_exported_file_if_needed("/tmp/export.docx")

    open_url.assert_called_once()
    assert open_url.call_args.args[0].toLocalFile() == "/tmp/export.docx"


def test_new_project_uses_default_export_config(window):
    window.global_settings_service.set_default_export_config({
        "layout_type": "Сценарий 1",
        "col_tc": False,
        "time_display": "start",
    })
    window.global_settings_service.set_default_prompter_config({
        "f_text": 48,
        "osc_enabled": True,
        "sync_in": False,
    })
    project_data = window.project_service.create_new_project("Test")

    window._apply_global_settings_to_project_data(project_data)

    assert project_data["export_config"]["layout_type"] == "Сценарий 1"
    assert project_data["export_config"]["col_tc"] is False
    assert project_data["export_config"]["time_display"] == "start"
    assert project_data["export_config"]["col_char"] is True
    assert project_data["prompter_config"]["f_text"] == 48
    assert project_data["prompter_config"]["osc_enabled"] is True
    assert project_data["prompter_config"]["sync_in"] is False
    assert project_data["prompter_config"]["f_tc"] == 20


def test_initial_project_uses_global_default_export_config(
    app,
    tmp_path,
    monkeypatch
):
    settings_file = tmp_path / "global_settings.json"
    settings_file.write_text(
        json.dumps({
            "default_export_config": {
                "layout_type": "Сценарий 2",
                "format_html": False,
                "format_docx": True,
                "format_pdf": True,
                "time_display": "start",
            }
        }),
        encoding="utf-8"
    )
    monkeypatch.setattr(
        "services.global_settings_service.SETTINGS_FILE",
        settings_file
    )

    initial_window = MainWindow()

    assert initial_window.data["export_config"]["layout_type"] == "Сценарий 2"
    assert initial_window.data["export_config"]["format_html"] is False
    assert initial_window.data["export_config"]["format_docx"] is True
    assert initial_window.data["export_config"]["format_pdf"] is True
    assert initial_window.data["export_config"]["time_display"] == "start"
    assert initial_window.chk_exp_html.isChecked() is False
    assert initial_window.chk_exp_docx.isChecked() is True
    assert initial_window.chk_exp_pdf.isChecked() is True
    initial_window.close()


def test_apply_default_export_config_to_project_updates_current_project(window):
    window.global_settings_service.set_default_export_config({
        "layout_type": "Сценарий 1",
        "col_actor": False,
    })
    window.data["export_config"] = {
        "layout_type": "Таблица",
        "col_actor": True,
        "format_html": True,
        "format_docx": False,
    }
    window.preview_window = Mock()
    window.set_dirty = Mock()

    export_config = window.apply_default_export_config_to_project()

    assert window.data["export_config"]["layout_type"] == "Сценарий 1"
    assert window.data["export_config"]["col_actor"] is False
    assert export_config == window.data["export_config"]
    window.preview_window.sync_export_settings.assert_called_once_with(
        update_preview=True
    )
    window.set_dirty.assert_called_once_with(True)


def test_apply_export_config_to_project_updates_current_project(window):
    window.data["export_config"] = {
        "layout_type": "Таблица",
        "col_actor": True,
    }
    window.preview_window = Mock()
    window.set_dirty = Mock()

    export_config = window.apply_export_config_to_project({
        "layout_type": "Сценарий 1",
        "col_actor": False,
        "time_display": "start",
        "format_html": False,
        "format_docx": True,
        "format_pdf": True,
    })

    assert window.data["export_config"]["layout_type"] == "Сценарий 1"
    assert window.data["export_config"]["col_actor"] is False
    assert window.data["export_config"]["time_display"] == "start"
    assert window.chk_exp_html.isChecked() is False
    assert window.chk_exp_docx.isChecked() is True
    assert window.chk_exp_pdf.isChecked() is True
    assert export_config == window.data["export_config"]
    window.preview_window.sync_export_settings.assert_called_once_with(
        update_preview=True
    )
    window.set_dirty.assert_called_once_with(True)


def test_apply_default_prompter_config_to_project_updates_current_project(window):
    window.global_settings_service.set_default_prompter_config({
        "f_text": 50,
        "osc_enabled": True,
        "is_mirrored": True,
    })
    window.data["prompter_config"] = {
        "f_text": 36,
        "is_mirrored": False,
    }
    window.teleprompter_window = Mock()
    window.set_dirty = Mock()

    prompter_config = window.apply_default_prompter_config_to_project()

    assert window.data["prompter_config"]["f_text"] == 50
    assert window.data["prompter_config"]["osc_enabled"] is True
    assert window.data["prompter_config"]["is_mirrored"] is True
    assert prompter_config == window.data["prompter_config"]
    assert window.teleprompter_window.cfg == window.data["prompter_config"]
    window.teleprompter_window.sync_config_controls.assert_called_once_with()
    window.teleprompter_window.build_prompter_content.assert_called_once_with()
    window.set_dirty.assert_called_once_with(True)


def test_apply_prompter_config_to_project_updates_current_project(window):
    window.data["prompter_config"] = {
        "f_text": 36,
        "sync_in": True,
    }
    window.teleprompter_window = Mock()
    window.set_dirty = Mock()

    prompter_config = window.apply_prompter_config_to_project({
        "f_text": 44,
        "sync_in": False,
    })

    assert window.data["prompter_config"]["f_text"] == 44
    assert window.data["prompter_config"]["sync_in"] is False
    assert prompter_config == window.data["prompter_config"]
    window.teleprompter_window.sync_config_controls.assert_called_once_with()
    window.teleprompter_window.build_prompter_content.assert_called_once_with()
    window.set_dirty.assert_called_once_with(True)


def test_apply_prompter_reaper_ports_to_project_updates_only_ports(window):
    window.data["prompter_config"] = {
        "f_text": 36,
        "port_in": 8000,
        "port_out": 9000,
        "sync_in": True,
    }
    window.teleprompter_window = Mock()
    window.set_dirty = Mock()

    prompter_config = window.apply_prompter_reaper_ports_to_project({
        "f_text": 52,
        "port_in": 8100,
        "port_out": 9100,
        "sync_in": False,
    })

    assert window.data["prompter_config"]["port_in"] == 8100
    assert window.data["prompter_config"]["port_out"] == 9100
    assert window.data["prompter_config"]["f_text"] == 36
    assert window.data["prompter_config"]["sync_in"] is True
    assert prompter_config == window.data["prompter_config"]
    window.teleprompter_window.sync_config_controls.assert_called_once_with()
    window.teleprompter_window.build_prompter_content.assert_called_once_with()
    window.set_dirty.assert_called_once_with(True)


def test_apply_prompter_reaper_ports_to_project_skips_unchanged_ports(window):
    window.data["prompter_config"] = {
        "port_in": 8000,
        "port_out": 9000,
    }
    window.teleprompter_window = Mock()
    window.set_dirty = Mock()

    prompter_config = window.apply_prompter_reaper_ports_to_project({
        "port_in": 8000,
        "port_out": 9000,
    })

    assert prompter_config == window.data["prompter_config"]
    window.teleprompter_window.sync_config_controls.assert_not_called()
    window.teleprompter_window.build_prompter_content.assert_not_called()
    window.set_dirty.assert_not_called()


def test_actor_filter_combo_only_shows_actors_in_current_episode(window):
    window.data["actors"] = {
        "actor1": {"name": "Actor One", "color": "#111111"},
        "actor2": {"name": "Actor Two", "color": "#222222"},
        "unused": {"name": "Unused Actor", "color": "#333333"},
    }
    window.data["global_map"] = {
        "Hero": "actor1",
        "Villain": "actor2",
    }
    window.current_ep_stats = [
        {"name": "Hero", "lines": 1, "rings": 1, "words": 2},
        {"name": "Villain", "lines": 1, "rings": 1, "words": 2},
        {"name": "Unassigned", "lines": 1, "rings": 1, "words": 2},
    ]
    window.ep_combo.clear()
    window.ep_combo.addItem("1", "1")

    window._update_actor_filter_combo()

    values = [
        window.actor_filter_combo.itemData(index)
        for index in range(window.actor_filter_combo.count())
    ]
    assert values == [None, "actor1", "actor2"]


def test_actor_filter_resets_when_actor_not_in_current_episode(window):
    window.data["actors"] = {
        "actor1": {"name": "Actor One", "color": "#111111"},
        "actor2": {"name": "Actor Two", "color": "#222222"},
    }
    window.data["global_map"] = {
        "Hero": "actor1",
    }
    window.current_ep_stats = [
        {"name": "Hero", "lines": 1, "rings": 1, "words": 2},
    ]
    window.ep_combo.clear()
    window.ep_combo.addItem("1", "1")
    window.actor_filter_combo.clear()
    window.actor_filter_combo.addItem("Actor Two", "actor2")
    window.actor_filter_combo.setCurrentIndex(0)

    window._update_actor_filter_combo()

    assert window.actor_filter_combo.currentData() is None


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
    assert window.actor_table.columnCount() == 3
    assert window.actor_table.item(0, 0).text() == "Global Actor"
    assert window.actor_table.item(0, 2).text() == "Ж"
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

    gender_item = window.actor_table.item(0, 2)
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
    assert actors[0]["color"] != "#123456"
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
    assert window.data["actors"]["global1"]["color"] == "#FFFFFF"
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


def test_quick_subtitle_converter_writes_html_without_actor_colors(
    window,
    tmp_path
):
    srt_path = tmp_path / "quick.srt"
    srt_path.write_text(
        "1\n"
        "00:00:01,000 --> 00:00:02,500\n"
        "Hero: Быстрая реплика\n",
        encoding="utf-8"
    )
    window.data["actors"] = {
        "actor-1": {"name": "Актёр", "color": "#123456"}
    }
    window.data["global_map"] = {"Hero": "actor-1"}
    window.data["export_config"] = {
        "layout_type": "Таблица",
        "use_color": True,
        "highlight_ids_export": ["actor-1"],
    }
    window.chk_exp_html.setChecked(True)
    window.chk_exp_docx.setChecked(False)

    with patch("ui.main_window.QMessageBox.information") as information:
        with patch("ui.main_window.QMessageBox.warning") as warning:
            window.convert_dropped_subtitles([str(srt_path)])

    output_path = tmp_path / "quick.html"
    assert output_path.exists()
    html = output_path.read_text(encoding="utf-8")
    assert "Быстрая реплика" in html
    assert "Hero" in html
    assert "#123456" not in html
    information.assert_called_once()
    warning.assert_not_called()


def test_quick_subtitle_converter_writes_docx_when_selected(
    window,
    tmp_path
):
    pytest.importorskip("docx")
    srt_path = tmp_path / "quick-docx.srt"
    srt_path.write_text(
        "1\n"
        "00:00:01,000 --> 00:00:02,500\n"
        "Hero: DOCX реплика\n",
        encoding="utf-8"
    )
    window.data["export_config"] = {
        "layout_type": "Таблица",
        "use_color": True,
    }
    window.chk_exp_html.setChecked(False)
    window.chk_exp_docx.setChecked(True)

    with patch("ui.main_window.QMessageBox.information"):
        with patch("ui.main_window.QMessageBox.warning") as warning:
            window.convert_dropped_subtitles([str(srt_path)])

    assert not (tmp_path / "quick-docx.html").exists()
    assert (tmp_path / "quick-docx.docx").exists()
    warning.assert_not_called()


def test_quick_subtitle_converter_writes_pdf_when_selected(
    window,
    tmp_path
):
    srt_path = tmp_path / "quick-pdf.srt"
    srt_path.write_text(
        "1\n"
        "00:00:01,000 --> 00:00:02,500\n"
        "Hero: PDF реплика\n",
        encoding="utf-8"
    )
    window.data["export_config"] = {
        "layout_type": "Таблица",
        "use_color": True,
    }
    window.chk_exp_html.setChecked(False)
    window.chk_exp_docx.setChecked(False)
    window.chk_exp_pdf.setChecked(True)

    with patch("ui.main_window.QMessageBox.information"):
        with patch("ui.main_window.QMessageBox.warning") as warning:
            window.convert_dropped_subtitles([str(srt_path)])

    pdf_path = tmp_path / "quick-pdf.pdf"
    assert not (tmp_path / "quick-pdf.html").exists()
    assert pdf_path.exists()
    assert pdf_path.read_bytes().startswith(b"%PDF")
    warning.assert_not_called()


def test_quick_subtitle_converter_previews_first_file_then_converts_all(
    window,
    tmp_path,
    monkeypatch
):
    first_path = tmp_path / "first.srt"
    second_path = tmp_path / "second.srt"
    for path, text in [
        (first_path, "First"),
        (second_path, "Second"),
    ]:
        path.write_text(
            "1\n"
            "00:00:01,000 --> 00:00:02,500\n"
            f"Hero: {text}\n",
            encoding="utf-8"
        )

    preview_calls = []
    exported_paths = []

    class PreviewStub:
        def __init__(
            self,
            main_app,
            ep_num,
            override_lines=None,
            source_title=None,
            register_preview=True
        ):
            preview_calls.append({
                "lines": override_lines,
                "source_title": source_title,
                "register_preview": register_preview,
            })

        def exec(self):
            window.data["export_config"]["format_html"] = True
            return 0

    monkeypatch.setattr("ui.preview.HtmlLivePreview", PreviewStub)
    monkeypatch.setattr(
        window,
        "_export_quick_subtitle_montage",
        lambda path: exported_paths.append(path) or [path]
    )
    window.chk_exp_html.setChecked(True)

    with patch("ui.main_window.QMessageBox.information"):
        window.convert_dropped_subtitles(
            [str(first_path), str(second_path)],
            preview_first=True
        )

    assert len(preview_calls) == 1
    assert preview_calls[0]["source_title"] == "first.srt"
    assert preview_calls[0]["register_preview"] is False
    assert preview_calls[0]["lines"][0]["text"] == "First"
    assert exported_paths == [str(first_path), str(second_path)]
