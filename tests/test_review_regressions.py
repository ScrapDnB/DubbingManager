"""Reproductions for the project-wide review findings."""

from copy import deepcopy
from pathlib import Path
import os
import shutil
import subprocess
import sys
from threading import Event
from time import monotonic, sleep

import pytest
from PySide6.QtCore import QSettings

from application.import_controller import ImportController
from core.commands import (
    AssignActorToCharacterCommand, DeleteEpisodeCommand, RenameEpisodeCommand,
    ReplaceMappingValueCommand, UndoStack, UpdateProjectFileStateCommand,
)
from services.assignment_service import LOCAL_UNASSIGNED_ACTOR_ID
from services.audiobook_document_service import AudiobookDocumentService
from services.episode_service import EpisodeService
from services.export_service import ExportService
from services.project_health_service import ProjectHealthService
from services.project_service import ProjectService
from services.reaper_rpp_service import ReaperRppService
from services.role_service import ROLE_MIXED_ACTOR, resolve_role_actor
from services.script_text_service import ScriptTextService
from ui.qml_backend.app_bridge import AppBridge
from ui.qml_backend.features.ui_state_bridge import UiStateBridge
from ui.qml_backend.features.update_bridge import UpdateBridge, _UpdateWorker


@pytest.fixture
def bridge(tmp_path, monkeypatch, qt_app):
    monkeypatch.setattr("services.global_settings_service.SETTINGS_FILE", tmp_path / "settings.json")
    ui = UiStateBridge(QSettings(str(tmp_path / "ui.ini"), QSettings.IniFormat))
    bridge = AppBridge(ui_state=ui)
    bridge._project_service.set_backup_config({"enabled": False})
    data = bridge._session.data
    data["actors"] = {"a": {"name": "Anna", "color": "#123456"},
                      "b": {"name": "Boris", "color": "#654321"}}
    data["episodes"] = {"1": ""}
    bridge._script_text_service.create_episode_text(
        data, "1", "", [{"s": 1, "e": 2, "char": "Hero", "text": "Hello world"}], {},
    )
    bridge.refresh()
    yield bridge
    bridge.updates.shutdown()
    bridge.audiobook.shutdown()
    bridge.deleteLater()


@pytest.mark.parametrize("mode", ["relative", "absolute"])
def test_backups_isolate_prefix_collisions_and_rotation(tmp_path, mode):
    config = {"max_backups": 1, "path_mode": mode,
              "directory": str(tmp_path / "central") if mode == "absolute" else ".backups"}
    other = ProjectService(config)
    other.current_project_path = str(tmp_path / "Film_part.dub")
    assert other.create_backup(other.create_new_project("Film part"))
    original = other.list_backups()[0]
    service = ProjectService(config)
    service.current_project_path = str(tmp_path / "Film.dub")
    assert service.list_backups() == []
    for _ in range(3):
        assert service.create_backup(service.create_new_project("Film"))
    assert len(service.list_backups()) == 1
    assert other.list_backups() == [original]
    assert original.exists()
    assert original.parent != service.get_backup_directory()


def test_legacy_backups_remain_available_without_cross_project_rotation(tmp_path):
    legacy_dir = tmp_path / ".backups"
    legacy_dir.mkdir()
    own = legacy_dir / "Film_autosave_20261011_120000_000000.dub_backup"
    other = legacy_dir / "Film_part_autosave_20261011_120000_000000.dub_backup"
    own.write_text("{}")
    other.write_text("{}")
    service = ProjectService({"max_backups": 1})
    service.current_project_path = str(tmp_path / "Film.dub")
    assert service.list_backups() == [own]
    assert service.create_backup(service.create_new_project("Film"))
    assert own in service.list_backups()
    assert other not in service.list_backups()
    assert own.exists() and other.exists()


def test_relative_backups_remain_accessible_after_moving_project_folder(tmp_path):
    original = tmp_path / "original"
    original.mkdir()
    service = ProjectService()
    service.current_project_path = str(original / "Film.dub")
    assert service.create_backup(service.create_new_project("Film"))
    backup_name = service.list_backups()[0].name
    moved = tmp_path / "moved"
    shutil.move(str(original), str(moved))
    service.current_project_path = str(moved / "Film.dub")
    assert [backup.name for backup in service.list_backups()] == [backup_name]


@pytest.mark.parametrize("saved", [False, True])
def test_backup_directory_failure_returns_false(tmp_path, saved):
    blocked = tmp_path / "blocked"
    blocked.write_text("ordinary file")
    service = ProjectService({"path_mode": "absolute", "directory": str(blocked)})
    if saved:
        service.current_project_path = str(tmp_path / "Film.dub")
    assert service.create_backup(service.create_new_project("Film")) is False
    assert blocked.read_text() == "ordinary file"


def test_global_role_assignment_undo_does_not_detach_older_commands(bridge):
    data = bridge._session.data
    original = data["global_map"]
    bridge.casting.assignActor("Hero", "a")
    bridge.roles.assign(["Hero"], "b")
    bridge.project.undo()
    bridge.project.undo()
    assert data["global_map"] is original
    assert data["global_map"] == {}
    bridge.project.redo()
    bridge.project.redo()
    assert data["global_map"] == {"Hero": "b"}


def test_episode_rename_and_line_edit_undo_redo_stay_consistent(bridge):
    data = bridge._session.data
    original_scripts = deepcopy(data["script_storage"])
    bridge.project.renameCurrentEpisode("First")
    assert bridge.workspace.selectLine(bridge.workspace.model.get(0)["lineId"])
    bridge.workspace.setDraftField("text", "changed")
    assert bridge.workspace.flush()
    bridge.project.undo()
    bridge.project.undo()
    assert data["episodes"] == {"1": ""}
    assert data["script_storage"] == original_scripts
    bridge.project.redo()
    bridge.project.redo()
    assert data["episodes"] == {"First": ""}
    assert list(data["script_storage"]["episodes"]) == ["First"]
    assert bridge._script_text_service.load_episode_lines(data, "First")[0]["text"] == "changed"


@pytest.mark.parametrize("replacement", ["field", "mapping"])
def test_snapshot_restores_removed_nested_containers_for_older_commands(replacement):
    local = {}
    data = {"episode_actor_map": {"1": local}}
    stack = UndoStack()
    stack.push(AssignActorToCharacterCommand(local, "Hero", "a"))
    if replacement == "field":
        command = UpdateProjectFileStateCommand(data, {"episode_actor_map": {}}, "replace")
    else:
        command = ReplaceMappingValueCommand(data, "episode_actor_map", {}, "replace")
    stack.push(command)
    stack.undo()
    assert data["episode_actor_map"]["1"] is local
    stack.undo()
    assert data == {"episode_actor_map": {"1": {}}}
    stack.redo()
    stack.redo()
    assert data == {"episode_actor_map": {}}


def test_delete_episode_undo_restores_empty_values_and_embedded_data():
    episodes, videos, loaded = {"1": ""}, {"1": ""}, {"1": []}
    assignments, texts, working, order = {"1": {}}, {"1": ""}, {"1": {}}, ["1"]
    command = DeleteEpisodeCommand(episodes, videos, loaded, "1", assignments, texts, working, order)
    for _ in range(2):
        command.execute()
        assert all(not mapping for mapping in (episodes, videos, loaded, assignments, texts, working))
        command.undo()
        assert episodes == videos == texts == {"1": ""}
        assert loaded == {"1": []}
        assert assignments == working == {"1": {}}
        assert order == ["1"]


@pytest.mark.parametrize("entry", ["subtitle", "docx", "direct", "folder"])
def test_audiobook_rejects_screenplay_import_without_changing_data(bridge, tmp_path, entry):
    data = bridge._session.data
    data["project_kind"] = "audiobook"
    data["episodes"] = {"Chapter": "audiobook"}
    data["audiobook_document"] = AudiobookDocumentService().create_document(
        "", [("Chapter", "<html><body><p>Valuable book text</p></body></html>")],
    )
    bridge.refresh()
    source = tmp_path / "2.srt"
    source.write_text("1\n00:00:01,000 --> 00:00:02,000\nHero: Hello\n")
    before = deepcopy(data)
    undo_count = len(bridge._session.undo_stack._undo_stack)
    if entry == "subtitle":
        feature = bridge.subtitleImport
        feature.prepare([str(source)])
        invoke = feature.importAll
    elif entry == "docx":
        feature = bridge.docxImport
        invoke = lambda: feature.importEpisode("2", True)
    elif entry == "direct":
        feature = bridge.project
        invoke = lambda: feature.importSubtitle(str(source))
    else:
        feature = bridge.projectFiles
        invoke = feature.batchImportFolder
    errors = []
    feature.errorRequested.connect(errors.append)
    assert not invoke()
    assert errors and "аудиокниги" in errors[0]
    assert data == before
    assert len(bridge._session.undo_stack._undo_stack) == undo_count


@pytest.mark.parametrize("source_kind", ["subtitle", "docx"])
def test_import_controller_rejects_audiobook_before_any_mutation(source_kind):
    data = ProjectService().create_new_project("Book")
    data["project_kind"] = "audiobook"
    before = deepcopy(data)
    stack = UndoStack()
    controller = ImportController(data, EpisodeService(), ScriptTextService(), stack, lambda: None)
    with pytest.raises(ValueError, match="аудиокниги"):
        if source_kind == "subtitle":
            controller.add_subtitle_episode("1", "missing.ass")
        else:
            controller.add_docx_episode("1", "missing.docx", {})
    assert data == before
    assert stack._undo_stack == []


@pytest.fixture(params=["global", "local"])
def multi_actor_project(request):
    data = {"project_name": "Film", "actors": {
        "a": {"name": "Anna", "color": "#123456"},
        "b": {"name": "Boris", "color": "#654321"},
    }, "global_map": {"Hero": ["a", "b"]}, "episode_actor_map": {}}
    if request.param == "local":
        data["global_map"] = {"Hero": "a"}
        data["episode_actor_map"] = {"1": {"Hero": ["a", "b"]}}
    return data


def test_reaper_exports_tracks_for_every_assigned_actor(multi_actor_project):
    service = ReaperRppService(multi_actor_project)
    lines = [{"id": 1, "s": 1, "e": 2, "char": "Hero", "text": "Hello world"}]
    rpp = service.generate("1", lines, {"merge": False})
    assert 'NAME "Anna"' in rpp and 'NAME "Boris"' in rpp
    preview = service.preview("1", lines, {"merge": False})
    assert "Anna" in str(preview) and "Boris" in str(preview)


def test_excel_exports_names_and_full_words_for_each_actor(multi_actor_project):
    service = ExportService(multi_actor_project)
    lines = service.process_merge_logic(
        [{"id": 1, "s": 1, "e": 2, "char": "Hero", "text": "Hello world"}], {"merge": False},
    )
    workbook = service.create_excel_book({"1": lines}, {"col_actor": True})
    summary = list(workbook["Сводка"].values)
    assert {row[0]: row[-1] for row in summary[1:]} == {"Anna": 2, "Boris": 2}
    episode = workbook.worksheets[1]
    assert "Anna / Boris" in [cell.value for cell in episode[2]]


@pytest.mark.parametrize("layout", ["Таблица", "Сценарий 1", "Сценарий 2", "Сценарий 3"])
def test_docx_exports_every_assigned_actor_in_each_layout(multi_actor_project, layout):
    service = ExportService(multi_actor_project)
    lines = service.process_merge_logic(
        [{"id": 1, "s": 1, "e": 2, "char": "Hero", "text": "Hello world"}], {"merge": False},
    )
    document = service.create_docx_document({"1": lines}, {"layout_type": layout, "col_actor": True})
    text = "\n".join(cell.text for table in document.tables for row in table.rows for cell in row.cells)
    assert "Anna / Boris" in text


@pytest.mark.parametrize("assigned", [True, False])
def test_dynamic_health_check_resolves_char_and_assignment(bridge, assigned):
    data = bridge._session.data
    if assigned:
        data["global_map"] = {"Hero": "a"}
    messages = [issue.message for issue in ProjectHealthService().check_project(data)]
    assert not any("не указан персонаж" in message for message in messages)
    assert any("Hero" in message and "актёр" in message for message in messages) is not assigned


@pytest.mark.parametrize("episodes, local, expected", [
    ({"1"}, {}, ""),
    ({"1"}, {"1": {"Hero": LOCAL_UNASSIGNED_ACTOR_ID}}, ""),
    (set(), {}, "a"),
    ({"1", "2"}, {"1": {"Hero": "b"}}, ROLE_MIXED_ACTOR),
])
def test_role_actor_respects_empty_and_local_assignments(episodes, local, expected):
    data = {"actors": {"a": {"name": "Anna"}, "b": {"name": "Boris"}},
            "global_map": {"Hero": "a"} if local or not episodes else {},
            "episode_actor_map": local}
    result = resolve_role_actor(data, "Hero", episodes)
    assert result["actor_id"] == expected
    if not expected:
        assert result["actor_name"] == "Без актёра"


def test_update_shutdown_waits_and_suppresses_queued_installer(qt_app, monkeypatch):
    bridge = UpdateBridge()
    started = Event()
    calls = []
    monkeypatch.setattr(bridge._service, "start_binary_update", calls.append)
    def operation(progress):
        started.set()
        sleep(0.03)
        return "installer.dmg"
    assert bridge._start_task(operation, bridge._binary_download_completed)
    assert started.wait(2)
    assert bridge._thread.wait(2000)  # Completion is queued but not yet delivered.
    bridge.shutdown()
    qt_app.processEvents()
    assert calls == []
    assert not bridge.busy
    assert not bridge._start_task(operation, calls.append)


def test_update_completion_is_delivered_normally_and_allows_another_task(qt_app):
    bridge = UpdateBridge()
    calls = []
    try:
        for result in ("first", "second"):
            assert bridge._start_task(lambda progress: result, calls.append)
            deadline = monotonic() + 2
            while bridge.busy and monotonic() < deadline:
                qt_app.processEvents()
                sleep(0.001)
            assert not bridge.busy
        assert calls == ["first", "second"]
    finally:
        bridge.shutdown()


def test_update_cancel_suppresses_completion_and_releases_worker(qt_app):
    bridge = UpdateBridge()
    started, release = Event(), Event()
    calls = []
    def operation(progress):
        started.set()
        assert release.wait(2)
        return "result"
    try:
        assert bridge._start_task(operation, calls.append)
        assert started.wait(2)
        bridge.cancel()
        release.set()
        deadline = monotonic() + 2
        while bridge.busy and monotonic() < deadline:
            qt_app.processEvents()
            sleep(0.001)
        assert not bridge.busy
        assert calls == []
        assert bridge.status == "Операция отменена"
    finally:
        release.set()
        bridge.shutdown()


def test_update_cancel_before_worker_start_does_not_execute_operation():
    calls, finished = [], []
    worker = _UpdateWorker(lambda progress: calls.append("executed"))
    worker.finished.connect(lambda: finished.append(True))
    worker.cancel()
    worker.run()
    assert calls == []
    assert finished == [True]


def test_application_exit_during_update_does_not_abort():
    source = '''
from time import sleep
from PySide6.QtCore import QCoreApplication, QTimer
from ui.qml_backend.features.update_bridge import UpdateBridge
app = QCoreApplication([])
bridge = UpdateBridge()
app.aboutToQuit.connect(bridge.shutdown)
bridge._start_task(lambda progress: sleep(0.2), lambda result: None)
QTimer.singleShot(20, app.quit)
app.exec()
'''
    result = subprocess.run([sys.executable, "-c", source], capture_output=True, text=True,
                            cwd=Path(__file__).resolve().parents[1], timeout=10,
                            env={**os.environ, "QT_QPA_PLATFORM": "offscreen"})
    assert result.returncode == 0, result.stderr
    assert "Destroyed while thread" not in result.stderr
