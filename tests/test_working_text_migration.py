"""Tests for working text migration from old projects."""

import json
from pathlib import Path

from PySide6.QtWidgets import QMessageBox

from services import EpisodeService, ScriptTextService
from ui.main_window import MainWindow


def _make_window_stub(tmp_path):
    window = MainWindow.__new__(MainWindow)
    window.data = {
        "episodes": {},
        "episode_texts": {},
        "loaded_episodes": {},
        "replica_merge_config": {},
    }
    window.current_project_path = str(tmp_path / "project.json")
    window.current_ep_stats = []
    window.episode_service = EpisodeService()
    window.script_text_service = ScriptTextService()
    window.update_ep_list = lambda: None
    window.set_dirty = lambda dirty=True: None
    return window


def test_episodes_needing_working_texts_ignores_existing_file(tmp_path):
    window = _make_window_stub(tmp_path)
    existing_text = tmp_path / "episode_1.json"
    existing_text.write_text("{}", encoding="utf-8")
    window.data["episodes"] = {
        "1": "/missing/one.srt",
        "2": "/missing/two.srt",
        "3": "/missing/three.docx",
    }
    window.data["episode_texts"] = {"1": str(existing_text)}

    assert window._episodes_needing_working_texts() == ["2", "3"]
    assert window.data["episode_working_texts"]["1"] == {}
    assert window.data["episode_texts"] == {}


def test_episodes_needing_working_texts_links_text_next_to_project(tmp_path):
    window = _make_window_stub(tmp_path)
    texts_dir = tmp_path / "project_texts_dm"
    texts_dir.mkdir()
    text_path = texts_dir / "episode_1.json"
    text_path.write_text(
        json.dumps({"episode": "1", "lines": []}),
        encoding="utf-8"
    )
    window.data["episodes"] = {"1": str(tmp_path / "episode_1.srt")}

    assert window._episodes_needing_working_texts() == []
    assert window.data["episode_working_texts"]["1"]["episode"] == "1"
    assert window.data["episode_texts"] == {}


def test_episodes_needing_working_texts_links_text_from_project_folder(tmp_path):
    window = _make_window_stub(tmp_path)
    project_folder = tmp_path / "Work"
    texts_dir = project_folder / "texts_dm"
    texts_dir.mkdir(parents=True)
    text_path = texts_dir / "episode_1.json"
    text_path.write_text(
        json.dumps({"episode": "1", "lines": []}),
        encoding="utf-8"
    )
    window.data["project_folder"] = str(project_folder)
    window.data["episodes"] = {"1": str(tmp_path / "episode_1.srt")}

    assert window._episodes_needing_working_texts() == []
    assert window.data["episode_working_texts"]["1"]["episode"] == "1"
    assert window.data["episode_texts"] == {}


def test_create_missing_working_texts_builds_found_sources(tmp_path, monkeypatch):
    window = _make_window_stub(tmp_path)
    srt_path = tmp_path / "episode_1.srt"
    srt_path.write_text(
        "1\n"
        "00:00:01,000 --> 00:00:04,000\n"
        "John: Hello there\n",
        encoding="utf-8"
    )
    window.data["episodes"] = {
        "1": str(srt_path),
        "2": str(tmp_path / "missing.srt"),
    }

    messages = []
    monkeypatch.setattr(
        "ui.main_window.QMessageBox.information",
        lambda *args: messages.append(args)
    )

    created, skipped = window.create_missing_working_texts(["1", "2"])

    assert created == 1
    assert skipped == 1
    payload = window.data["episode_working_texts"]["1"]
    assert payload["lines"][0]["text"] == "Hello there"
    assert window.data["episode_texts"] == {}
    assert messages


def test_create_missing_working_texts_uses_project_folder(tmp_path, monkeypatch):
    window = _make_window_stub(tmp_path)
    project_folder = tmp_path / "Work"
    project_folder.mkdir()
    srt_path = tmp_path / "episode_1.srt"
    srt_path.write_text(
        "1\n"
        "00:00:01,000 --> 00:00:04,000\n"
        "John: Hello there\n",
        encoding="utf-8"
    )
    window.data["project_folder"] = str(project_folder)
    window.data["episodes"] = {"1": str(srt_path)}

    monkeypatch.setattr("ui.main_window.QMessageBox.information", lambda *args: None)

    created, skipped = window.create_missing_working_texts(["1"])

    assert created == 1
    assert skipped == 0
    payload = window.data["episode_working_texts"]["1"]
    assert payload["lines"][0]["text"] == "Hello there"
    assert window.data["episode_texts"] == {}


def test_migration_prompt_only_informs_user(tmp_path, monkeypatch):
    window = _make_window_stub(tmp_path)
    source_path = tmp_path / "episode_1.srt"
    source_path.write_text("1\n00:00:01,000 --> 00:00:02,000\nHi\n", encoding="utf-8")
    window.data["episodes"] = {"1": str(source_path)}

    messages = []
    monkeypatch.setattr(
        "ui.main_window.QMessageBox.information",
        lambda *args: messages.append(args)
    )
    window.create_missing_working_texts = lambda *args, **kwargs: (_ for _ in ()).throw(
        AssertionError("migration prompt must not create working texts")
    )

    window._prompt_working_text_migration()

    assert messages
    assert window.data["episode_texts"] == {}


def test_ensure_working_text_offers_to_create_json(tmp_path, monkeypatch):
    window = _make_window_stub(tmp_path)
    source_path = tmp_path / "episode_1.srt"
    source_path.write_text("1\n00:00:01,000 --> 00:00:02,000\nHi\n", encoding="utf-8")
    window.data["episodes"] = {"1": str(source_path)}

    monkeypatch.setattr(
        "ui.main_window.QMessageBox.question",
        lambda *args: QMessageBox.Yes
    )
    called = []
    window.regenerate_episode_text = (
        lambda ep, source_path=None, show_result=True: called.append(
            (ep, source_path, show_result)
        ) or True
    )

    assert window.ensure_working_text_for_episode("1", "редактировать текст")
    assert called == [("1", str(source_path), False)]
