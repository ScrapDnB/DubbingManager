import json

from config.constants import DEFAULT_REPLICA_MERGE_CONFIG
from services.project_service import ProjectService
from services.script_text_service import ScriptTextService


def _lines():
    return [
        {
            "id": 0,
            "s": 1.0,
            "e": 2.0,
            "s_raw": "0:00:01.00",
            "char": "Hero",
            "text": "One",
        },
        {
            "id": 1,
            "s": 2.1,
            "e": 3.0,
            "s_raw": "0:00:02.10",
            "char": "Hero",
            "text": "Two",
        },
    ]


def test_new_project_uses_dynamic_text_model_with_format_2():
    data = ProjectService().create_new_project("Dynamic")

    assert data["metadata"]["format_version"] == "2.0"
    assert data["script_storage"]["model"] == "dynamic_source"
    assert data["script_storage"]["schema_revision"] == 1
    assert "merge_config" not in data["script_storage"]
    assert data["project_settings"]["fps"] == 25.0


def test_old_dynamic_project_migrates_only_project_fps(tmp_path):
    source_path = tmp_path / "old-dynamic.dub"
    data = ProjectService().create_new_project("Old dynamic")
    data["script_storage"]["merge_config"] = {
        "merge": False,
        "merge_gap": 300,
        "fps": 30.0,
    }
    source_path.write_text(json.dumps(data), encoding="utf-8")

    loaded = ProjectService().load_project(str(source_path))

    assert loaded["project_settings"]["fps"] == 30.0
    assert loaded["project_settings"]["fps_source"] == "legacy"
    assert "merge_config" not in loaded["script_storage"]


def test_dynamic_edits_survive_merge_rule_changes(tmp_path):
    source = tmp_path / "episode.ass"
    source.write_text("[Events]\n", encoding="utf-8")
    data = ProjectService().create_new_project("Dynamic")
    data["episodes"]["1"] = str(source)
    scripts = ScriptTextService()
    scripts.create_episode_text(
        data,
        "1",
        str(source),
        _lines(),
        DEFAULT_REPLICA_MERGE_CONFIG,
    )

    merged = scripts.load_episode_lines(data, "1")
    assert [line["text"] for line in merged] == ["One  Two"]
    first_id, second_id = merged[0]["edit_ids"]
    assert scripts.update_line_text(data, "1", first_id, "Edited")

    scripts.set_merge_config(data, {
        **DEFAULT_REPLICA_MERGE_CONFIG,
        "merge": False,
    })
    assert [line["text"] for line in scripts.load_episode_lines(data, "1")] == [
        "Edited",
        "Two",
    ]

    scripts.set_merge_config(data, DEFAULT_REPLICA_MERGE_CONFIG)
    restored = scripts.load_episode_lines(data, "1")
    assert [line["text"] for line in restored] == ["Edited  Two"]
    assert restored[0]["edit_ids"] == [first_id, second_id]


def test_premerged_source_rows_ignore_dynamic_merge_rules(tmp_path):
    source = tmp_path / "episode.docx"
    source.write_bytes(b"docx-placeholder")
    data = ProjectService().create_new_project("Dynamic")
    data["episodes"]["1"] = str(source)
    scripts = ScriptTextService()
    scripts.create_episode_text(
        data,
        "1",
        str(source),
        _lines(),
        DEFAULT_REPLICA_MERGE_CONFIG,
        import_config={"mapping": {"text": 2}},
        line_mode="premerged",
    )

    payload = data["script_storage"]["episodes"]["1"]
    assert payload["source"]["line_mode"] == "premerged"
    assert payload["source"]["import_config"] == {
        "mapping": {"text": 2}
    }
    assert [line["text"] for line in scripts.load_episode_lines(data, "1")] == [
        "One",
        "Two",
    ]

    scripts.set_merge_config(data, {
        **DEFAULT_REPLICA_MERGE_CONFIG,
        "merge": True,
        "merge_gap": 9999,
    })
    scripts.set_inline_timecode_config({
        "inline_timecodes_enabled": True,
        "inline_timecode_min_duration": 0,
        "inline_timecode_every": 1,
    })
    assert [line["text"] for line in scripts.load_episode_lines(data, "1")] == [
        "One",
        "Two",
    ]


def test_old_dynamic_docx_without_line_mode_is_preserved(tmp_path):
    source = tmp_path / "episode.docx"
    source.write_bytes(b"docx-placeholder")
    data = ProjectService().create_new_project("Dynamic")
    data["episodes"]["1"] = str(source)
    scripts = ScriptTextService()
    scripts.create_episode_text(
        data,
        "1",
        str(source),
        _lines(),
        DEFAULT_REPLICA_MERGE_CONFIG,
    )
    del data["script_storage"]["episodes"]["1"]["source"]["line_mode"]

    assert [line["text"] for line in scripts.load_episode_lines(data, "1")] == [
        "One",
        "Two",
    ]


def test_dynamic_split_is_stored_as_fragments(tmp_path):
    source = tmp_path / "episode.ass"
    source.write_text("[Events]\n", encoding="utf-8")
    data = ProjectService().create_new_project("Dynamic")
    data["episodes"]["1"] = str(source)
    scripts = ScriptTextService()
    scripts.create_episode_text(
        data,
        "1",
        str(source),
        [_lines()[0]],
        {**DEFAULT_REPLICA_MERGE_CONFIG, "merge": False},
    )
    fragment_id = scripts.load_episode_lines(data, "1")[0]["edit_ids"][0]

    assert scripts.split_line_to_character(
        data, "1", fragment_id, "O", "ne", "Narrator"
    )
    atomic = scripts.load_atomic_episode_lines(data, "1")
    assert [(line["text"], line["char"]) for line in atomic] == [
        ("O", "Hero"),
        ("ne", "Narrator"),
    ]
    blocks = data["script_storage"]["episodes"]["1"]["edit_blocks"]
    assert len(blocks) == 1
    assert len(blocks[0]["fragments"]) == 2


def test_dynamic_character_rename_can_be_reversed(tmp_path):
    source = tmp_path / "episode.ass"
    source.write_text("[Events]\n", encoding="utf-8")
    data = ProjectService().create_new_project("Dynamic")
    data["episodes"]["1"] = str(source)
    scripts = ScriptTextService()
    scripts.create_episode_text(
        data,
        "1",
        str(source),
        [_lines()[0]],
        DEFAULT_REPLICA_MERGE_CONFIG,
    )

    assert scripts.rename_character(data, "Hero", "Lead", "1") == 1
    assert scripts.load_atomic_episode_lines(data, "1")[0]["char"] == "Lead"
    assert scripts.rename_character(data, "Lead", "Hero", "1") == 1
    assert scripts.load_atomic_episode_lines(data, "1")[0]["char"] == "Hero"
    assert data["script_storage"]["episodes"]["1"][
        "character_aliases"
    ] == {}


def test_dynamic_project_disk_payload_has_no_materialized_lines(tmp_path):
    source = tmp_path / "episode.ass"
    source.write_text("[Events]\n", encoding="utf-8")
    path = tmp_path / "dynamic.dub"
    service = ProjectService()
    data = service.create_new_project("Dynamic")
    data["episodes"]["1"] = str(source)
    ScriptTextService().create_episode_text(
        data,
        "1",
        str(source),
        _lines(),
        DEFAULT_REPLICA_MERGE_CONFIG,
        import_config={"strip_override_tags": True},
    )

    assert service.save_project(data, str(path))
    stored = json.loads(path.read_text(encoding="utf-8"))
    assert stored["metadata"]["format_version"] == "2.0"
    assert "merge_config" not in stored["script_storage"]
    assert "episode_working_texts" not in stored
    episode = stored["script_storage"]["episodes"]["1"]
    assert len(episode["source_lines"]) == 2
    assert episode["edit_blocks"] == []
    assert "lines" not in episode
    assert episode["source"]["import_config"] == {
        "strip_override_tags": True
    }

    loaded = service.load_project(str(path))
    assert [
        line["text"] for line in ScriptTextService().load_episode_lines(
            loaded, "1"
        )
    ] == ["One  Two"]


def test_legacy_project_continues_to_use_saved_merged_lines():
    data = {
        "metadata": {"format_version": "1.0"},
        "project_name": "Legacy",
        "project_kind": "subtitle",
        "actors": {},
        "global_map": {},
        "episode_actor_map": {},
        "episodes": {"1": "episode.ass"},
        "video_paths": {},
        "episode_texts": {},
        "episode_working_texts": {
            "1": {
                "lines": [{
                    "id": "legacy-1",
                    "start": 1.0,
                    "end": 3.0,
                    "character": "Hero",
                    "text": "Already merged",
                }]
            }
        },
        "replica_merge_config": {"merge": False, "fps": 24},
        "audiobook_document": {},
    }

    scripts = ScriptTextService()
    assert not scripts.uses_dynamic_storage(data)
    assert [line["text"] for line in scripts.load_episode_lines(data, "1")] == [
        "Already merged"
    ]


def test_loaded_legacy_project_keeps_its_format_version_on_save(tmp_path):
    source_path = tmp_path / "legacy.dub"
    saved_path = tmp_path / "legacy-saved.dub"
    data = {
        "metadata": {
            "format_version": "1.0",
            "app_version": "1.0",
            "created_at": "2025-01-01T00:00:00",
            "modified_at": "2025-01-01T00:00:00",
        },
        "project_name": "Legacy",
        "project_kind": "subtitle",
        "actors": {},
        "global_map": {},
        "episode_actor_map": {},
        "episodes": {"1": "episode.ass"},
        "video_paths": {},
        "episode_texts": {},
        "episode_working_texts": {
            "1": {
                "lines": [{
                    "id": "legacy-1",
                    "start": 1.0,
                    "end": 2.0,
                    "character": "Hero",
                    "text": "Saved merged line",
                }]
            }
        },
        "replica_merge_config": {"merge": False, "fps": 24},
        "audiobook_document": {},
    }
    source_path.write_text(json.dumps(data), encoding="utf-8")
    service = ProjectService()

    loaded = service.load_project(str(source_path))
    assert service.save_project(loaded, str(saved_path))

    stored = json.loads(saved_path.read_text(encoding="utf-8"))
    assert stored["metadata"]["format_version"] == "1.0"
    assert stored["episode_working_texts"]["1"]["lines"][0]["text"] == (
        "Saved merged line"
    )
    assert stored["replica_merge_config"] == {"merge": False, "fps": 24}
    assert "script_storage" not in stored
