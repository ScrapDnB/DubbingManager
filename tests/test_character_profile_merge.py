"""Character collisions, scope selection and lossless Undo/Redo."""

from copy import deepcopy

import pytest
from PySide6.QtCore import QCoreApplication, QSettings

from core.commands import UpdateWorkingTextLineCommand
from services.audiobook_document_service import AudiobookDocumentService
from services.assignment_service import LOCAL_UNASSIGNED_ACTOR_ID
from ui.qml_backend.app_bridge import AppBridge
from ui.qml_backend.features.ui_state_bridge import UiStateBridge


@pytest.fixture
def bridge(tmp_path, monkeypatch):
    app = QCoreApplication.instance() or QCoreApplication([])
    monkeypatch.setattr(
        "services.global_settings_service.SETTINGS_FILE", tmp_path / "global.json"
    )
    ui = UiStateBridge(QSettings(str(tmp_path / "ui.ini"), QSettings.IniFormat))
    result = AppBridge(ui_state=ui)
    result._project_service.set_backup_config({"enabled": False})
    yield result
    result.audiobook.shutdown()
    result.deleteLater()
    assert app is not None


def configure(bridge, tmp_path, storage="dynamic", multiple=True):
    data = bridge._session.data
    names = ["1", "2"] if multiple else ["1"]
    data["episodes"] = {ep: str(tmp_path / f"{ep}.ass") for ep in names}
    data["actors"] = {
        actor: {"name": actor, "color": "#123456"}
        for actor in ("source", "target", "local-source", "local-target")
    }
    data["global_map"] = {"Hero": "source", "Lead": "target"}
    data["episode_actor_map"] = {
        ep: {"Hero": "local-source", "Lead": ["local-target", "target"]}
        for ep in names
    }
    data["character_aliases"] = {"Hero": ["Old alias"], "Lead": ["Target alias"]}
    rows = [("Hero", "Source replica"), ("Lead", "Target replica"), ("Other", "Untouched")]
    if storage == "audiobook":
        data["project_kind"] = "audiobook"
        data["audiobook_document"] = AudiobookDocumentService().create_document(
            str(tmp_path / "book.pdf"), [
                (ep, "<html><body>" + "".join(
                    f'<p><span data-dm-character="{name}">{text}</span></p>'
                    for name, text in rows
                ) + "</body></html>") for ep in names
            ],
        )
    elif storage == "legacy":
        data.pop("script_storage", None)
        data["episode_working_texts"] = {
            ep: {
                "characters": {name: {"display_name": name} for name, _ in rows},
                "lines": [
                    {"id": str(i), "start": i * 10, "end": i * 10 + 1,
                     "character": name, "display_character": name, "text": text}
                    for i, (name, text) in enumerate(rows)
                ],
            } for ep in names
        }
    else:
        for ep in names:
            bridge._script_text_service.create_episode_text(
                data, ep, data["episodes"][ep], [
                    {"id": i, "s": i * 10, "e": i * 10 + 1, "char": name, "text": text}
                    for i, (name, text) in enumerate(rows)
                ], bridge._script_text_service.get_merge_config(data),
            )
    bridge.refresh()
    bridge.casting.selectCharacter("Hero")
    return data


def characters(bridge, episode):
    return [line["char"] for line in bridge._script_text_service.load_atomic_episode_lines(
        bridge._session.data, episode
    )]


@pytest.mark.parametrize("storage", ["dynamic", "legacy", "audiobook"])
@pytest.mark.parametrize("all_episodes", [False, True])
def test_merge_preserves_destination_and_exact_undo_redo(bridge, tmp_path, storage, all_episodes):
    data = configure(bridge, tmp_path, storage)
    before = deepcopy(data)
    requests = []
    bridge.casting.characterProfileConfirmationRequested.connect(
        lambda *args: requests.append(args)
    )

    bridge.casting.renameCharacter("Hero", "Lead")
    assert requests == [("merge", "Hero", "Lead")]
    assert data == before
    assert not bridge.project.canUndo

    bridge.casting.confirmCharacterProfileUpdate(True)
    assert requests[-1] == ("scope", "Hero", "Lead")
    assert data == before
    bridge.casting.confirmCharacterProfileUpdate(all_episodes)

    assert characters(bridge, "1") == ["Lead", "Lead", "Other"]
    assert characters(bridge, "2") == (
        ["Lead", "Lead", "Other"] if all_episodes else ["Hero", "Lead", "Other"]
    )
    assert data["global_map"]["Lead"] == "target"
    assert ("Hero" in data["global_map"]) is not all_episodes
    assert data["episode_actor_map"]["1"] == {"Lead": ["local-target", "target"]}
    assert data["episode_actor_map"]["2"] == (
        {"Lead": ["local-target", "target"]} if all_episodes
        else before["episode_actor_map"]["2"]
    )
    assert data["character_aliases"]["Lead"] == (
        ["Target alias", "Old alias"] if all_episodes else ["Target alias"]
    )
    assert bridge.casting.selectedCharacter == "Lead"
    lead = next(row for row in bridge.casting.charactersModel.rows() if row["character"] == "Lead")
    assert lead["lines"] == 2
    after = deepcopy(data)
    bridge.project.undo()
    assert data == before
    assert not bridge.project.canUndo  # One operation for every affected episode.
    assert characters(bridge, "1") == ["Hero", "Lead", "Other"]
    bridge.project.redo()
    assert data == after
    assert characters(bridge, "1") == ["Lead", "Lead", "Other"]


@pytest.mark.parametrize("stage", ["merge", "scope"])
def test_cancel_confirmation_does_not_change_project(bridge, tmp_path, stage):
    data = configure(bridge, tmp_path)
    before = deepcopy(data)
    bridge.casting.renameCharacter("Hero", "Lead")
    if stage == "scope":
        bridge.casting.confirmCharacterProfileUpdate(True)
    bridge.casting.cancelCharacterProfileUpdate()
    bridge.casting.confirmCharacterProfileUpdate(True)
    assert data == before
    assert not bridge.project.canUndo


def test_reject_merge_does_not_offer_scope(bridge, tmp_path):
    data = configure(bridge, tmp_path)
    before = deepcopy(data)
    requests = []
    bridge.casting.characterProfileConfirmationRequested.connect(lambda *args: requests.append(args))
    bridge.casting.renameCharacter("Hero", "Lead")
    bridge.casting.confirmCharacterProfileUpdate(False)
    assert requests == [("merge", "Hero", "Lead")]
    assert data == before


@pytest.mark.parametrize("all_episodes", [False, True])
def test_rename_without_collision_offers_scope_and_preserves_other_assignments(bridge, tmp_path, all_episodes):
    data = configure(bridge, tmp_path)
    before = deepcopy(data)
    requests = []
    bridge.casting.characterProfileConfirmationRequested.connect(lambda *args: requests.append(args))
    bridge.casting.renameCharacter("Hero", "New")
    assert requests == [("scope", "Hero", "New")]
    bridge.casting.confirmCharacterProfileUpdate(all_episodes)
    assert characters(bridge, "1") == ["New", "Lead", "Other"]
    assert characters(bridge, "2")[0] == ("New" if all_episodes else "Hero")
    assert data["global_map"]["New"] == "source"
    assert ("Hero" in data["global_map"]) is not all_episodes
    assert data["episode_actor_map"]["1"]["New"] == "local-source"
    bridge.project.undo()
    assert data == before


@pytest.mark.parametrize("assignment", [None, LOCAL_UNASSIGNED_ACTOR_ID])
def test_merge_keeps_destination_unassigned(bridge, tmp_path, assignment):
    data = configure(bridge, tmp_path, multiple=False)
    data["global_map"].pop("Lead")
    data["episode_actor_map"]["1"].pop("Lead")
    if assignment is not None:
        data["episode_actor_map"]["1"]["Lead"] = assignment
    before = deepcopy(data)
    requests = []
    bridge.casting.characterProfileConfirmationRequested.connect(lambda *args: requests.append(args))
    bridge.casting.renameCharacter("Hero", "Lead")
    bridge.casting.confirmCharacterProfileUpdate(True)
    assert requests == [("merge", "Hero", "Lead")]
    lead = next(row for row in bridge.casting.charactersModel.rows() if row["character"] == "Lead")
    assert lead["actorIds"] == []
    assert "Lead" not in data["global_map"]
    bridge.project.undo()
    assert data == before


def test_episode_change_discards_pending_confirmation(bridge, tmp_path):
    data = configure(bridge, tmp_path)
    before = deepcopy(data)
    bridge.casting.renameCharacter("Hero", "Lead")
    bridge._session.current_episode = "2"
    bridge.casting.confirmCharacterProfileUpdate(True)
    assert data == before
    assert not bridge.project.canUndo


def test_partial_merge_preserves_alias_ownership(bridge, tmp_path):
    data = configure(bridge, tmp_path)
    bridge.casting.renameCharacter("Hero", "Lead")
    bridge.casting.confirmCharacterProfileUpdate(True)
    bridge.casting.confirmCharacterProfileUpdate(False)
    assert data["character_aliases"] == {
        "Hero": ["Old alias"], "Lead": ["Target alias"]
    }
    errors = []
    bridge.casting.errorRequested.connect(errors.append)
    bridge._session.current_episode = "2"
    bridge.casting.updateCharacterProfile("Hero", "Hero", ["Old alias"])
    assert errors == []


@pytest.mark.parametrize("scope", ["global", "episode"])
def test_undo_merge_keeps_earlier_actor_assignment_undoable(bridge, tmp_path, scope):
    data = configure(bridge, tmp_path, multiple=False)
    if scope == "global":
        data["episode_actor_map"]["1"].pop("Hero")
    original = deepcopy(data)
    bridge.casting.assignActor("Hero", "target")
    assigned = deepcopy(data)
    assert assigned != original
    bridge.casting.renameCharacter("Hero", "Lead")
    bridge.casting.confirmCharacterProfileUpdate(True)
    merged = deepcopy(data)
    bridge.project.undo()
    assert data == assigned
    bridge.project.undo()
    assert data == original
    bridge.project.redo()
    assert data == assigned
    bridge.project.redo()
    assert data == merged


def test_undo_merge_keeps_earlier_legacy_text_edit_undoable(bridge, tmp_path):
    data = configure(bridge, tmp_path, "legacy", multiple=False)
    original = deepcopy(data)
    bridge._session.execute(UpdateWorkingTextLineCommand(
        data["episode_working_texts"], "1", "0", "Edited replica"
    ), "working_text")
    edited = deepcopy(data)
    bridge.casting.renameCharacter("Hero", "Lead")
    bridge.casting.confirmCharacterProfileUpdate(True)
    bridge.project.undo()
    assert data == edited
    bridge.project.undo()
    assert data == original


@pytest.mark.parametrize("storage", ["dynamic", "legacy"])
def test_merge_does_not_rename_source_that_already_has_another_display_name(bridge, tmp_path, storage):
    data = configure(bridge, tmp_path, storage, multiple=False)
    scripts = bridge._script_text_service
    if storage == "dynamic":
        for line in scripts.load_atomic_episode_lines(data, "1"):
            assert scripts.update_line_text(data, "1", line["id"], line["text"] + " edited")
    scripts.rename_character(data, "Hero", "Already renamed", "1")
    # Only the imported Other replica currently belongs to Hero.
    scripts.rename_character(data, "Other", "Hero", "1")
    bridge.casting.refresh("working_text")
    before = deepcopy(data)
    bridge.casting.renameCharacter("Hero", "Lead")
    bridge.casting.confirmCharacterProfileUpdate(True)
    assert characters(bridge, "1") == ["Already renamed", "Lead", "Lead"]
    if storage == "legacy":
        assert data["episode_working_texts"]["1"]["characters"]["Hero"]["display_name"] == "Already renamed"
    bridge.project.undo()
    assert characters(bridge, "1") == ["Already renamed", "Lead", "Hero"]
    assert data == before


def test_merge_into_character_found_only_in_another_episode(bridge, tmp_path):
    data = configure(bridge, tmp_path)
    payload = data["script_storage"]["episodes"]["1"]
    payload["source_lines"] = [
        line for line in payload["source_lines"] if line["character"] != "Lead"
    ]
    data["episode_actor_map"]["1"].pop("Lead")
    bridge.casting.refresh("working_text")
    requests = []
    bridge.casting.characterProfileConfirmationRequested.connect(lambda *args: requests.append(args))
    before = deepcopy(data)
    bridge.casting.renameCharacter("Hero", "Lead")
    assert requests == [("merge", "Hero", "Lead")]
    bridge.casting.confirmCharacterProfileUpdate(True)
    assert requests[-1] == ("scope", "Hero", "Lead")
    bridge.casting.confirmCharacterProfileUpdate(False)
    assert characters(bridge, "1") == ["Lead", "Other"]
    assert data["global_map"]["Lead"] == "target"
    assert data["episode_actor_map"]["1"] == {}
    assert data["episode_actor_map"]["2"] == before["episode_actor_map"]["2"]
    bridge.project.undo()
    assert data == before


def test_merge_of_edited_fragment_without_an_imported_source_for_its_name(bridge, tmp_path):
    data = configure(bridge, tmp_path, multiple=False)
    scripts = bridge._script_text_service
    first = scripts.load_atomic_episode_lines(data, "1")[0]
    assert scripts.update_line_character(data, "1", first["id"], "New role")
    before = deepcopy(data)
    bridge.casting.renameCharacter("New role", "Lead")
    bridge.casting.confirmCharacterProfileUpdate(True)
    assert characters(bridge, "1") == ["Lead", "Lead", "Other"]
    bridge.project.undo()
    assert data == before
