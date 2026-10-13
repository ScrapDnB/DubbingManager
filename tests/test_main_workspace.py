"""Behavioral contracts for the redesigned main workspace."""
from copy import deepcopy
import json

import pytest
from PySide6.QtCore import QCoreApplication, QSettings

from services.dynamic_script_storage import DynamicScriptStorage
from services.project_schema_service import ProjectSchemaService
from ui.qml_backend.app_bridge import AppBridge
from ui.qml_backend.features.ui_state_bridge import UiStateBridge
from ui.qml_backend.features.workspace_bridge import format_timecode, parse_timecode


@pytest.fixture
def bridge(tmp_path, monkeypatch):
    app = QCoreApplication.instance() or QCoreApplication([])
    import services.global_settings_service as gs
    monkeypatch.setattr(gs, "SETTINGS_FILE", tmp_path / "settings.json")
    ui = UiStateBridge(QSettings(str(tmp_path / "ui.ini"), QSettings.IniFormat))
    bridge = AppBridge(ui_state=ui)
    bridge._project_service.set_backup_config({"enabled": False})
    data = bridge._session.data
    data["actors"] = {"a": {"name": "Анна", "color": "#367dc4"},
                      "b": {"name": "Борис", "color": "#c88d25"}}
    data["global_map"] = {"Алиса": "a"}
    for episode in ("1", "2"):
        data["episodes"][episode] = str(tmp_path / (episode + ".ass"))
        bridge._script_text_service.create_episode_text(
            data, episode, data["episodes"][episode], [
                {"s": 42.32, "e": 45.48, "char": "Алиса", "text": "Маяк работает."},
                {"s": 46, "e": 49.4, "char": "Марк", "text": "Проверим ещё раз."},
                {"s": 50, "e": 53, "char": "Алиса", "text": "Ещё одна реплика."},
            ], bridge._script_text_service.get_merge_config(data))
    bridge.refresh()
    yield bridge
    bridge.audiobook.shutdown()
    bridge.deleteLater()


def select_first(bridge):
    key = bridge.workspace.model.get(0)["lineId"]
    assert bridge.workspace.selectLine(key)
    return key


def test_audiobook_toolbar_is_available_for_new_projects_and_audiobooks(bridge, tmp_path):
    assert not bridge.project.canOpenAudiobook  # An imported serial, even before saving.
    bridge.project.create()
    assert bridge.project.canOpenAudiobook
    bridge.project.name = "Новая книга"
    assert bridge.project.canOpenAudiobook  # Naming a new project is allowed.
    bridge._session.data["project_kind"] = "audiobook"
    bridge._session.notify_changed("project_files")
    assert bridge.project.canOpenAudiobook
    bridge.project.create()
    bridge.project.resolvePendingChanges("discard")
    assert bridge.project.canOpenAudiobook
    path = tmp_path / "empty-project.dmproj"
    bridge.project.saveAs(str(path))
    assert bridge.project.path
    assert not bridge.project.canOpenAudiobook
    saved_path = bridge.project.path
    bridge.project.create()
    assert bridge.project.canOpenAudiobook
    bridge.project.open(saved_path)
    assert not bridge.project.canOpenAudiobook  # Opening an empty serial is not New.
    from services.audiobook_document_service import AudiobookDocumentService
    bridge._session.data["project_kind"] = "audiobook"
    bridge._session.data["audiobook_document"] = AudiobookDocumentService().create_document("", [])
    bridge._session.notify_changed("project_files")
    bridge.project.saveAs(str(tmp_path / "audiobook.dmproj"))
    audiobook_path = bridge.project.path
    assert audiobook_path != saved_path
    bridge.project.create()
    bridge.project.open(audiobook_path)
    assert bridge._session.data["project_kind"] == "audiobook"
    assert bridge.project.canOpenAudiobook


@pytest.mark.parametrize("fps,seconds", [(25,42.32), (24,125.25), (29.97,3600), (60,2.5)])
def test_non_drop_timecode_round_trip(fps, seconds):
    encoded = format_timecode(seconds, fps)
    assert abs(parse_timecode(encoded, fps) - seconds) <= 0.5 / fps + 1e-8


@pytest.mark.parametrize("value", ["", "00:60:00:00", "00:00:60:00", "00:00:00:25", "-1:00:00:00", "nan"])
def test_invalid_timecode_is_rejected(value):
    with pytest.raises(ValueError):
        parse_timecode(value, 25)


def test_filter_counts_and_character_navigation(bridge):
    workspace = bridge.workspace
    assert workspace.totalCount == 3
    assert workspace.characterCount == 2
    assert workspace.unassignedCount == 1
    workspace.setActorFilter("__unassigned__")
    assert workspace.count == 1
    assert workspace.model.get(0)["character"] == "Марк"
    workspace.setActorFilter("a")
    assert workspace.count == 2
    workspace.setSearchText("еще")
    assert workspace.count == 1
    workspace.openCharacter("Алиса")
    assert workspace.workflow == 1 and workspace.count == 2
    assert workspace.selected["character"] == "Алиса"


def test_full_replica_edit_is_one_undo_and_preserves_source(bridge):
    select_first(bridge)
    workspace = bridge.workspace
    original = deepcopy(bridge._session.data["script_storage"])
    for field, value in {"text": "Новая реплика", "character": "Новая роль",
                         "inTime": "00:00:41:10", "outTime": "00:00:44:20"}.items():
        workspace.setDraftField(field, value)
    assert workspace.flush()
    assert workspace.selected["text"] == "Новая реплика"
    assert workspace.selected["character"] == "Новая роль"
    assert workspace.selected["start"] == pytest.approx(41.4)
    assert workspace.selected["end"] == pytest.approx(44.8)
    current = bridge._session.data["script_storage"]
    assert current["episodes"]["1"]["source_lines"] == original["episodes"]["1"]["source_lines"]
    ProjectSchemaService().validate_current(bridge._session.data)
    bridge.project.undo()
    assert bridge._session.data["script_storage"] == original
    bridge.project.redo()
    assert workspace.selected["text"] == "Новая реплика"


def test_invalid_draft_blocks_save_close_mode_and_episode(bridge, tmp_path):
    select_first(bridge)
    workspace = bridge.workspace
    workspace.setDraftField("outTime", "00:00:00:01")
    errors, closes = [], []
    bridge.errorOccurred.connect(errors.append)
    bridge.project.closeApproved.connect(lambda: closes.append(True))
    bridge.project.selectEpisode("2")
    workspace.setWorkflow(1)
    bridge.project.saveAs(str(tmp_path / "invalid.dub"))
    bridge.project.requestClose()
    assert bridge.project.currentEpisode == "1"
    assert workspace.workflow == 0 and workspace.draftDirty
    assert errors and not closes and not (tmp_path / "invalid.dub").exists()


def test_save_flushes_valid_draft_and_reopen_retains_timing(bridge, tmp_path):
    select_first(bridge)
    workspace = bridge.workspace
    workspace.setDraftField("text", "Сохранённая правка")
    workspace.setDraftField("inTime", "00:00:40:00")
    path = tmp_path / "edited.dub"
    bridge.project.saveAs(str(path))
    assert path.is_file()
    assert not workspace.draftDirty and not bridge.project.dirty
    bridge.project.open(str(path))
    assert bridge.workspace.model.get(0)["text"] == "Сохранённая правка"
    assert bridge.workspace.model.get(0)["start"] == 40


def test_assignment_refresh_keeps_draft_and_updates_all_actors(bridge):
    select_first(bridge)
    workspace = bridge.workspace
    workspace.setDraftField("text", "Черновик")
    bridge.casting.addActorToCharacter("Алиса", "b")
    assert workspace.selected["actorIds"] == ["a", "b"]
    assert workspace.draft["text"] == "Черновик"
    assert workspace.draftDirty


def test_mode_and_episode_navigation_flush_valid_edits(bridge):
    select_first(bridge)
    bridge.workspace.setDraftField("text", "Применено при переходе")
    bridge.workspace.setWorkflow(1)
    assert bridge.workspace.selected["text"] == "Применено при переходе"
    assert not bridge.workspace.draftDirty
    bridge.workspace.setDraftField("text", "Ещё одна правка")
    bridge.project.selectEpisode("2")
    assert not bridge.workspace.selected
    bridge.project.selectEpisode("1")
    assert bridge.workspace.model.get(0)["text"] == "Ещё одна правка"


def test_split_fragment_timing_does_not_change_siblings(bridge):
    data = bridge._session.data
    dynamic = DynamicScriptStorage()
    first = bridge.workspace.model.get(0)["lineId"]
    assert dynamic.split_fragment(data, "1", first, "Первая часть", "Вторая часть", "Марк")
    bridge.refresh()
    second = bridge.workspace.model.get(1)["lineId"]
    assert bridge.workspace.selectLine(second)
    bridge.workspace.setDraftField("inTime", "00:00:43:00")
    bridge.workspace.setDraftField("outTime", "00:00:44:00")
    assert bridge.workspace.flush()
    atomic = bridge._script_text_service.load_atomic_episode_lines(data, "1")
    assert atomic[0]["s"] == 42.32 and atomic[0]["e"] == 45.48
    assert atomic[1]["s"] == 43 and atomic[1]["e"] == 44


def test_legacy_working_text_edit_uses_stable_id(bridge):
    data = bridge._session.data
    data.pop("script_storage")
    data["episode_working_texts"] = {
        "1": {"lines": [{"id": "legacy-id", "start": 1, "end": 3,
                        "character": "Алиса", "text": "Исходный текст"}]}
    }
    bridge.refresh()
    assert bridge.workspace.selectLine("legacy-id")
    bridge.workspace.setDraftField("text", "Правка старого проекта")
    assert bridge.workspace.flush()
    assert data["episode_working_texts"]["1"]["lines"][0]["text"] == "Правка старого проекта"
    bridge.project.undo()
    assert data["episode_working_texts"]["1"]["lines"][0]["text"] == "Исходный текст"


def test_text_only_edit_preserves_subframe_precision(bridge):
    data = bridge._session.data
    source = data["script_storage"]["episodes"]["1"]["source_lines"][0]
    source["start"], source["end"] = 42.3219, 45.4871
    bridge.refresh()
    select_first(bridge)
    bridge.workspace.setDraftField("text", "Только текст")
    assert bridge.workspace.flush()
    assert bridge.workspace.selected["start"] == 42.3219
    assert bridge.workspace.selected["end"] == 45.4871


def test_unavailable_video_resets_when_switching_episode(bridge, tmp_path):
    video = tmp_path / "example.mp4"
    video.write_bytes(b"test")
    bridge._session.data["video_paths"]["1"] = str(video)
    bridge.workspace.refresh()
    assert bridge.workspace.hasVideo
    bridge.project.selectEpisode("2")
    assert not bridge.workspace.hasVideo and bridge.workspace.videoUrl.isEmpty()


def test_backup_failure_keeps_draft_and_canonical_text(bridge, monkeypatch):
    select_first(bridge)
    before = deepcopy(bridge._session.data["script_storage"])
    bridge.workspace.setDraftField("text", "Не применено")
    monkeypatch.setattr(bridge._session, "ensure_edit_backup", lambda scope: False)
    assert not bridge.workspace.flush()
    assert bridge.workspace.draftDirty
    assert bridge._session.data["script_storage"] == before


def test_external_legacy_text_is_embedded_atomically_and_undoable(bridge, tmp_path):
    data = bridge._session.data
    data.pop("script_storage")
    data["episode_working_texts"] = {}
    payload = {"lines": [{"id": "external-id", "start": 1, "end": 3,
                          "character": "Алиса", "text": "Внешний текст"}]}
    path = tmp_path / "working.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    data["episode_texts"] = {"1": str(path)}
    bridge.refresh()
    assert bridge.workspace.selectLine("external-id")
    bridge.workspace.setDraftField("text", "Правка внешнего текста")
    assert bridge.workspace.flush()
    assert "1" not in data["episode_texts"]
    assert data["episode_working_texts"]["1"]["lines"][0]["text"] == "Правка внешнего текста"
    assert json.loads(path.read_text(encoding="utf-8")) == payload
    bridge.project.undo()
    assert data["episode_texts"]["1"] == str(path)
    assert "1" not in data["episode_working_texts"]
    assert bridge.workspace.model.get(0)["text"] == "Внешний текст"


def test_missing_selected_fragment_does_not_discard_draft(bridge):
    select_first(bridge)
    bridge.workspace.setDraftField("text", "Сохранить черновик")
    bridge._session.data["script_storage"]["episodes"]["1"]["source_lines"] = []
    assert not bridge.workspace.flush()
    assert bridge.workspace.draftDirty
    assert bridge.workspace.draft["text"] == "Сохранить черновик"


def test_timeline_navigation_clears_filters_and_seeks_matching_replica(bridge):
    workspace = bridge.workspace
    workspace.setSearchText("ничего")
    seeks = []
    workspace.seekRequested.connect(seeks.append)
    workspace.openAtTime(50, "Алиса")
    assert workspace.workflow == 1 and workspace.count == 3
    assert workspace.selected["text"] == "Ещё одна реплика."
    assert seeks[-1] == 50000


def test_text_edit_preserves_character_alias_link(bridge):
    data = bridge._session.data
    payload = data["script_storage"]["episodes"]["1"]
    payload["character_aliases"] = {"Алиса": "Алиса новая"}
    bridge.refresh()
    select_first(bridge)
    bridge.workspace.setDraftField("text", "Правка текста с псевдонимом")
    assert bridge.workspace.flush()
    atomic = bridge._script_text_service.load_atomic_episode_lines(data, "1")
    assert atomic[0]["source_char"] == "Алиса"
    assert atomic[0]["char"] == "Алиса новая"


@pytest.mark.parametrize("seconds,expected", [
    (44.9, "Маяк работает."), (47.1, "Проверим ещё раз."),
    (49.5, "Проверим ещё раз."), (51.5, "Ещё одна реплика."),
])
def test_ruler_selects_covering_or_nearest_interval_and_seeks_exact_time(bridge, seconds, expected):
    workspace = bridge.workspace
    seeks = []
    workspace.seekRequested.connect(seeks.append)
    workspace.openAtTime(seconds, "")
    assert workspace.selected["text"] == expected
    assert seeks == [round(seconds * 1000)]


def test_timeline_navigation_preserves_invalid_draft_and_selection(bridge):
    select_first(bridge)
    workspace = bridge.workspace
    workspace.setWorkflow(1)
    workspace.setDraftField("outTime", "invalid")
    original = workspace.selected
    seeks = []
    workspace.seekRequested.connect(seeks.append)
    workspace.openAtTime(51, "Алиса")
    assert workspace.selected == original and workspace.draftDirty
    assert not seeks


def test_only_two_workflows_are_accepted_without_changing_startup(bridge):
    workspace = bridge.workspace
    workspace.setWorkflow(1)
    workspace.setWorkflow(2)
    assert workspace.workflow == 1
    assert workspace.startupWorkflow == 0


@pytest.mark.parametrize("kind", ["subtitle", "docx", "direct"])
def test_import_rejects_invalid_pending_edit_before_changing_project(bridge, kind):
    select_first(bridge)
    workspace = bridge.workspace
    workspace.setDraftField("outTime", "invalid")
    before = deepcopy(bridge._session.data)
    if kind == "subtitle":
        assert not bridge.subtitleImport.importAll()
    elif kind == "docx":
        assert not bridge.docxImport.importEpisode("3", False)
    else:
        bridge.project.importSubtitle("missing.ass")
    assert workspace.draftDirty and bridge._session.data == before


@pytest.mark.parametrize("configured,expected", [(None, 0), (0, 0), (1, 1), (2, 0), (-1, 0)])
def test_startup_workflow_uses_explicit_preference_instead_of_last_section(bridge, configured, expected):
    from ui.qml_backend.features.workspace_bridge import WorkspaceBridge
    ui = bridge.uiState
    ui.setIntValue("main.workflow", 1)  # Legacy last visited section is ignored.
    if configured is not None:
        ui.setIntValue("main.startupWorkflow", configured)
    workspace = WorkspaceBridge(bridge._session, bridge._script_text_service,
                                bridge._project_folder_service, bridge.casting, ui)
    assert workspace.workflow == expected
    workspace.setWorkflow(1 - expected)
    assert workspace.startupWorkflow == expected


def test_setting_startup_section_does_not_navigate_or_commit_active_draft(bridge):
    select_first(bridge)
    workspace = bridge.workspace
    workspace.setDraftField("outTime", "invalid")
    workspace.setStartupWorkflow(1)
    assert workspace.workflow == 0 and workspace.draftDirty
    assert workspace.startupWorkflow == 1
    assert bridge.uiState.intValue("main.startupWorkflow", -1) == 1
    workspace.setStartupWorkflow(2)
    assert workspace.startupWorkflow == 1
