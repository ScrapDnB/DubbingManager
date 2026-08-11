"""Tests for target-specific user layout templates."""

from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import patch

from services.global_settings_service import GlobalSettingsService
from services.export_service import ExportService
from services.layout_template_service import (
    builtin_layout_templates,
    find_layout_node,
    flatten_layout_tree,
    layout_template_rows,
    new_layout_template,
    normalize_layout_library,
    normalize_layout_template,
    preview_html,
)
from ui.qml_backend.features.layout_templates_bridge import LayoutTemplatesBridge


def test_layout_library_keeps_targets_separate_and_sanitizes_nodes():
    montage = new_layout_template("montage", "Печатный")
    prompter = new_layout_template("teleprompter", "Экранный")
    montage["root"]["children"][0]["gap"] = 999
    montage["root"]["children"][0]["children"][0]["style"][
        "font_size"
    ] = 999

    library = normalize_layout_library({
        "montage": [montage],
        "teleprompter": [prompter],
    })

    assert [item["kind"] for item in library["montage"]] == ["montage"]
    assert [item["kind"] for item in library["teleprompter"]] == [
        "teleprompter"
    ]
    row = library["montage"][0]["root"]["children"][0]
    assert row["gap"] == 48
    assert row["children"][0]["style"]["font_size"] == 300


def test_builtins_are_target_specific_and_preview_is_self_contained():
    montage_ids = {item["id"] for item in builtin_layout_templates("montage")}
    prompter_ids = {
        item["id"] for item in builtin_layout_templates("teleprompter")
    }

    assert "builtin.montage.table" in montage_ids
    assert "builtin.teleprompter.scenario3" in prompter_ids
    assert montage_ids.isdisjoint(prompter_ids)
    html = preview_html(builtin_layout_templates("teleprompter")[0])
    assert "ГЕРОЙ" in html
    assert "#050505" in html


def test_interactive_preview_exposes_direct_manipulation_commands():
    template = new_layout_template("montage", "Интерактивный")
    field = next(
        row for row in flatten_layout_tree(template["root"])
        if row["field"] == "replica"
    )

    html = preview_html(
        template,
        selected_node_id=field["nodeId"],
        interactive=True,
        editable=True,
    )

    assert "__DM_LAYOUT__" in html
    assert "data-action='remove'" in html
    assert "resize-handle" in html
    assert "layout-node field selected" in html


def test_template_normalization_preserves_unique_tree_ids():
    template = new_layout_template("montage")
    duplicate_id = template["root"]["id"]
    template["root"]["children"][0]["id"] = duplicate_id

    normalized = normalize_layout_template(template)
    rows = flatten_layout_tree(normalized["root"])

    assert len({row["nodeId"] for row in rows}) == len(rows)
    assert find_layout_node(normalized["root"], rows[-1]["nodeId"])


def test_teleprompter_tree_projects_to_non_recursive_rows():
    scenario3 = builtin_layout_templates("teleprompter")[-1]

    rows = layout_template_rows(scenario3["root"])

    assert len(rows) == 1
    assert len(rows[0]["cells"]) == 2
    assert [
        item["field"] for item in rows[0]["cells"][0]["items"]
    ] == ["timecode", "character", "actor"]
    assert rows[0]["cells"][1]["items"][0]["field"] == "replica"


def test_global_settings_round_trip_layout_library(tmp_path):
    settings_file = tmp_path / "global_settings.json"
    with patch(
        "services.global_settings_service.SETTINGS_FILE", settings_file
    ):
        service = GlobalSettingsService()
        service.load_settings()
        library = service.get_layout_templates()
        custom = new_layout_template("montage", "Студийный")
        library["montage"].append(custom)
        service.set_layout_templates(library)
        service.set_active_layout_template_id("montage", custom["id"])
        assert service.save_settings(service.settings)

        restored = GlobalSettingsService()
        restored.load_settings()

    assert restored.get_layout_templates()["montage"][0]["name"] == "Студийный"
    assert restored.get_layout_templates()["teleprompter"] == []
    assert restored.get_active_layout_template_id("montage") == custom["id"]
    assert restored.get_active_layout_template("montage")["kind"] == "montage"


def test_bridge_saves_and_activates_new_draft(tmp_path):
    settings_file = tmp_path / "global_settings.json"
    with patch(
        "services.global_settings_service.SETTINGS_FILE", settings_file
    ):
        service = GlobalSettingsService()
        service.load_settings()
        bridge = LayoutTemplatesBridge(service)
        bridge.begin("teleprompter")
        bridge.createTemplate("Крупный экран")
        draft_id = bridge.draftId
        root_id = bridge.selectedNodeId

        assert not bridge.draftPersisted
        assert bridge.draftDirty
        assert not bridge.draftModified

        bridge.addNode("separator", "")

        assert bridge.draftDirty
        assert bridge.draftModified
        assert bridge.activateTemplate(draft_id)
        assert bridge.draftPersisted

    assert service.get_active_layout_template_id("teleprompter") == draft_id
    saved = service.get_active_layout_template("teleprompter")
    assert saved["name"] == "Крупный экран"
    assert saved["kind"] == "teleprompter"
    assert root_id != bridge.selectedNodeId
    assert any(
        row["nodeType"] == "separator"
        for row in flatten_layout_tree(saved["root"])
    )


def test_bridge_does_not_modify_built_in_template():
    service = GlobalSettingsService()
    service.settings = deepcopy(service._get_defaults())
    bridge = LayoutTemplatesBridge(service)
    original = bridge.previewHtml

    bridge.addNode("separator", "")

    assert bridge.draftBuiltIn
    assert not bridge.draftDirty
    assert bridge.previewHtml == original


def test_bridge_reports_duplicate_field_without_changing_draft():
    service = GlobalSettingsService()
    service.settings = deepcopy(service._get_defaults())
    bridge = LayoutTemplatesBridge(service)
    bridge.createTemplate("Без дублей")
    bridge.selectNode(bridge._draft["root"]["id"])
    errors = []
    bridge.errorRequested.connect(errors.append)
    before = deepcopy(bridge._draft)

    bridge.addNode("field", "replica")

    assert errors == ["Поле «Реплика» уже добавлено"]
    assert bridge._draft == before


def test_bridge_undo_redo_and_used_fields_follow_canvas_edits():
    service = GlobalSettingsService()
    service.settings = deepcopy(service._get_defaults())
    bridge = LayoutTemplatesBridge(service)
    bridge.createTemplate("История")
    replica = next(
        row for row in flatten_layout_tree(bridge._draft["root"])
        if row["field"] == "replica"
    )

    assert bridge.usedFields == [
        "timecode", "character", "actor", "replica"
    ]
    bridge.removeNode(replica["nodeId"])
    assert "replica" not in bridge.usedFields
    assert bridge.canUndo

    bridge.undo()
    assert "replica" in bridge.usedFields
    assert bridge.canRedo

    bridge.redo()
    assert "replica" not in bridge.usedFields


def test_bridge_can_preview_current_project_data():
    class SampleTextService:
        @staticmethod
        def load_episode_lines(data, episode):
            return [{
                "s": 65,
                "e": 68,
                "char": "КАПИТАН",
                "text": "Настоящая реплика проекта",
            }]

    service = GlobalSettingsService()
    service.settings = deepcopy(service._get_defaults())
    session = SimpleNamespace(
        current_episode="1",
        data={
            "actors": {"actor-1": {"name": "Мария Волкова"}},
            "global_map": {"КАПИТАН": "actor-1"},
        },
    )
    bridge = LayoutTemplatesBridge(
        service,
        session=session,
        script_text_service=SampleTextService(),
    )

    assert bridge.previewProjectDataAvailable
    bridge.setPreviewUsesProjectData(True)

    assert bridge.previewUsesProjectData
    assert "Настоящая реплика проекта" in bridge.previewHtml
    assert "Мария Волкова" in bridge.previewHtml
    assert "00:01:05 — 00:01:08" in bridge.previewHtml


def test_bridge_drag_reorders_only_siblings():
    service = GlobalSettingsService()
    service.settings = deepcopy(service._get_defaults())
    bridge = LayoutTemplatesBridge(service)
    bridge.createTemplate("Перестановка")
    before = flatten_layout_tree(bridge._draft["root"])
    first_row = next(row for row in before if row["nodeType"] == "row")
    sibling_fields = [
        row for row in before if row["parentId"] == first_row["nodeId"]
    ]

    bridge.moveNodeBefore(
        sibling_fields[-1]["nodeId"], sibling_fields[0]["nodeId"]
    )

    after = [
        row for row in flatten_layout_tree(bridge._draft["root"])
        if row["parentId"] == first_row["nodeId"]
    ]
    assert after[0]["nodeId"] == sibling_fields[-1]["nodeId"]
    assert bridge.selectedNodeId == sibling_fields[-1]["nodeId"]


def test_montage_custom_template_drives_html_renderer():
    template = new_layout_template("montage", "Тестовый")
    replica = next(
        row for row in flatten_layout_tree(template["root"])
        if row["field"] == "replica"
    )
    find_layout_node(template["root"], replica["nodeId"])["style"][
        "font_size"
    ] = 41
    service = ExportService({
        "project_name": "Demo",
        "actors": {},
        "global_map": {},
        "episode_actor_map": {},
    })

    html = service.generate_html(
        "1",
        [{"s": 1.0, "e": 2.0, "char": "Hero", "text": "Custom text"}],
        {
            "layout_template": template,
            "col_tc": True,
            "col_char": True,
            "col_actor": True,
            "col_text": True,
            "time_display": "range",
        },
        layout_type="Таблица",
        is_editable=False,
    )

    assert "custom-layout-container" in html
    assert "font-size:41px" in html
    assert "Custom text" in html
