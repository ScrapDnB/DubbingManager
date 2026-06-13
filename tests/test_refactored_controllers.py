"""Direct tests for controllers/services split out of MainWindow."""

import csv
from pathlib import Path
from io import StringIO
from unittest.mock import MagicMock

from core.commands import UndoStack
from services import (
    CharacterStatsService,
    EpisodeService,
    ScriptTextService,
)
from ui.controllers import (
    GlobalActorController,
    ImportController,
    ReaperExportController,
    SettingsController,
)


def test_character_stats_service_counts_episode_and_project_stats():
    data = {
        "episodes": {"1": "one.ass"},
        "replica_merge_config": {"merge": False},
        "actors": {},
        "global_map": {},
    }
    lines = [
        {"id": 0, "s": 0.0, "e": 1.0, "char": "Hero", "text": "one two"},
        {"id": 1, "s": 1.1, "e": 2.0, "char": "Hero", "text": "three"},
        {"id": 2, "s": 5.0, "e": 6.0, "char": "Other", "text": "skip"},
    ]
    service = CharacterStatsService(data)

    episode_stats = service.episode_stats(lines, merge_gap=5, fps=25.0)
    hero_stats = next(item for item in episode_stats if item["name"] == "Hero")

    assert hero_stats == {"name": "Hero", "lines": 2, "rings": 1, "words": 3}

    project_stats = service.project_stats("Hero", lambda ep: lines)

    assert project_stats["rings"] == 2
    assert project_stats["words"] == 3
    assert project_stats["episodes"] == [
        {"episode": "1", "rings": 2, "words": 3}
    ]


def test_character_stats_service_builds_google_sheets_csv():
    data = {
        "episodes": {"2": "two.ass", "1": "one.ass"},
        "replica_merge_config": {"merge": False},
        "actors": {
            "actor-1": {"name": "Actor One"},
            "actor-2": {"name": "Actor Two"},
        },
        "global_map": {"Hero": "actor-1", "Other": "actor-2"},
    }
    lines_by_ep = {
        "1": [
            {"id": 0, "s": 0.0, "e": 1.0, "char": "Hero", "text": "one"},
            {"id": 1, "s": 1.1, "e": 2.0, "char": "Hero", "text": "two"},
        ],
        "2": [
            {"id": 2, "s": 0.0, "e": 1.0, "char": "Other", "text": "three"},
            {"id": 3, "s": 1.1, "e": 2.0, "char": "Hero", "text": "four"},
        ],
    }
    service = CharacterStatsService(data)

    csv_text = service.project_casting_csv(lambda ep: lines_by_ep.get(ep, []))
    rows = list(csv.reader(StringIO(csv_text)))

    assert rows[0] == ["Персонаж", "Актёр", "1", "2", "Всего"]
    assert rows[1] == ["Hero", "Actor One", "2", "1", "3"]
    assert rows[2] == ["2 серия", "", "", "", "0"]
    assert rows[3] == ["Other", "Actor Two", "", "1", "1"]


def test_import_controller_adds_srt_episode_and_working_text(tmp_path):
    srt_path = tmp_path / "Episode_02.srt"
    srt_path.write_text(
        "1\n00:00:01,000 --> 00:00:02,000\nHero: Hello\n",
        encoding="utf-8"
    )
    data = {
        "episodes": {},
        "episode_texts": {},
        "loaded_episodes": {},
        "replica_merge_config": {},
        "actors": {},
        "global_map": {},
    }
    controller = ImportController(
        data_ref=data,
        episode_service=EpisodeService(),
        script_text_service=ScriptTextService(),
        undo_stack=UndoStack(),
        get_current_project_path=lambda: str(tmp_path / "project.json"),
    )

    stats, lines = controller.add_subtitle_episode("2", str(srt_path))

    assert data["episodes"]["2"] == str(srt_path)
    assert data["episode_texts"]["2"].endswith("episode_2.json")
    assert Path(data["episode_texts"]["2"]).exists()
    assert stats[0]["name"] == "Hero"
    assert lines[0]["text"] == "Hello"


def test_settings_controller_applies_defaults_and_ports():
    data = {"export_config": {}, "prompter_config": {"port_in": 9000}}
    global_settings = {}
    service = MagicMock()
    service.get_default_export_config.return_value = {"format_html": False}
    service.get_default_prompter_config.return_value = {"font_size": 42}
    service.get_prompter_color_presets.return_value = [None, None]
    service.save_settings.return_value = True
    controller = SettingsController(data, global_settings, service)

    export_config = controller.apply_default_export_config_to_project()
    prompter_config = controller.apply_default_prompter_config_to_project()
    ports, changed = controller.apply_prompter_reaper_ports_to_project(
        {"port_in": 9001, "port_out": 9002}
    )

    assert export_config["format_html"] is False
    assert data["export_config"]["format_html"] is False
    assert prompter_config == {"font_size": 42}
    assert changed is True
    assert ports["port_in"] == 9001
    assert ports["port_out"] == 9002


def test_global_actor_controller_syncs_and_transfers():
    data = {
        "actors": {
            "local": {"name": "Alice", "color": "#fff"},
            "other": {"name": "Bob", "color": "#000"},
        },
        "global_map": {"Hero": "local"},
        "episode_actor_map": {"1": {"Hero": "local"}},
        "export_config": {"highlight_ids_export": ["local", "other"]},
    }
    service = MagicMock()
    service.get_global_actor_base.return_value = {
        "global-alice": {"name": "Alice", "gender": "Ж"}
    }
    service.save_settings.return_value = True
    controller = GlobalActorController(data, service)

    assert controller.sync_project_actors_with_global_base() == 1
    assert "local" not in data["actors"]
    assert data["actors"]["global-alice"]["gender"] == "Ж"
    assert data["global_map"]["Hero"] == "global-alice"
    assert data["episode_actor_map"]["1"]["Hero"] == "global-alice"
    assert data["export_config"]["highlight_ids_export"] == [
        "global-alice",
        "other",
    ]

    rows, available_count = controller.project_actor_transfer_rows()

    assert available_count == 1
    assert any(row["name"] == "Bob" and not row["exists"] for row in rows)


def test_reaper_export_controller_delegates_preview_and_save(tmp_path):
    data = {
        "project_name": "Show",
        "video_paths": {"1": "video.mov"},
        "replica_merge_config": {},
        "actors": {},
        "global_map": {},
    }
    folder_service = MagicMock()
    folder_service.resolve_project_path.return_value = "/resolved/video.mov"
    controller = ReaperExportController(data, folder_service)
    lines = [{"id": 0, "s": 0.0, "e": 1.0, "char": "Hero", "text": "Hello"}]
    save_path = tmp_path / "out.rpp"

    assert controller.resolve_video_path("1") == "/resolved/video.mov"
    assert controller.default_filename("1") == "Show - Ep1.rpp"

    preview = controller.preview(
        "1",
        lines,
        "/resolved/video.mov",
        use_video=True,
        use_regions=True,
        transliterate_actor_names=False,
    )
    controller.save(
        "1",
        lines,
        str(save_path),
        "/resolved/video.mov",
        use_video=False,
        use_regions=True,
        transliterate_actor_names=False,
    )

    assert preview["regions"] == 1
    assert preview["video"] is True
    assert preview["sample_regions"]
    assert save_path.exists()
