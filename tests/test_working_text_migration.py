"""Tests for working text migration from old projects."""

from pathlib import Path

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

    assert window._episodes_needing_working_texts() == ["2"]


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
    text_path = Path(window.data["episode_texts"]["1"])
    assert text_path.exists()
    assert text_path.parent.name == "project_texts_dm"
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
    text_path = Path(window.data["episode_texts"]["1"])
    assert text_path == project_folder / "texts_dm" / "episode_1.json"
    assert text_path.exists()
