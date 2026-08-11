"""QML bridge for the separate montage and teleprompter layout libraries."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, List, Optional, Tuple

from PySide6.QtCore import QObject, Property, Signal, Slot, Qt

from services.assignment_service import get_actor_for_character
from services.global_settings_service import GlobalSettingsService
from services.layout_template_service import (
    FIELD_LABELS,
    LAYOUT_FIELDS,
    builtin_layout_templates,
    duplicate_layout_template,
    find_layout_node,
    flatten_layout_tree,
    new_layout_template,
    normalize_layout_kind,
    normalize_layout_template,
    preview_html,
)
from ui.qml_backend.models import DictListModel


class LayoutTemplatesBridge(QObject):
    """Own template drafts and persist only explicit save/apply operations."""

    changed = Signal()
    draftChanged = Signal()
    statusRequested = Signal(str)
    errorRequested = Signal(str)
    montageTemplateChanged = Signal()
    teleprompterTemplateChanged = Signal()

    def __init__(
        self,
        global_settings_service: GlobalSettingsService,
        parent: Optional[QObject] = None,
        *,
        session: Optional[Any] = None,
        script_text_service: Optional[Any] = None,
    ) -> None:
        super().__init__(parent)
        self._settings = global_settings_service
        self._session = session
        self._script_text_service = script_text_service
        self._kind = "montage"
        self._draft: Dict[str, Any] = {}
        self._original: Dict[str, Any] = {}
        self._draft_persisted = True
        self._selected_node_id = ""
        self._preview_html = ""
        self._preview_uses_project_data = False
        self._undo_stack: List[Tuple[Dict[str, Any], str]] = []
        self._redo_stack: List[Tuple[Dict[str, Any], str]] = []
        self._library_model = DictListModel({
            "templateId": Qt.UserRole + 1,
            "name": Qt.UserRole + 2,
            "builtIn": Qt.UserRole + 3,
            "active": Qt.UserRole + 4,
            "kind": Qt.UserRole + 5,
        }, self)
        self._tree_model = DictListModel({
            "nodeId": Qt.UserRole + 1,
            "parentId": Qt.UserRole + 2,
            "depth": Qt.UserRole + 3,
            "nodeType": Qt.UserRole + 4,
            "field": Qt.UserRole + 5,
            "label": Qt.UserRole + 6,
            "container": Qt.UserRole + 7,
        }, self)
        self.begin("montage")

    @Property(QObject, constant=True)
    def libraryModel(self) -> QObject:
        return self._library_model

    @Property(QObject, constant=True)
    def treeModel(self) -> QObject:
        return self._tree_model

    @Property(str, notify=changed)
    def kind(self) -> str:
        return self._kind

    @Property(str, notify=draftChanged)
    def draftId(self) -> str:
        return str(self._draft.get("id") or "")

    @Property(str, notify=draftChanged)
    def draftName(self) -> str:
        return str(self._draft.get("name") or "")

    @Property(bool, notify=draftChanged)
    def draftBuiltIn(self) -> bool:
        return bool(self._draft.get("built_in"))

    @Property(bool, notify=draftChanged)
    def draftDirty(self) -> bool:
        return bool(self._draft) and (
            not self._draft_persisted or self._draft != self._original
        )

    @Property(bool, notify=draftChanged)
    def draftPersisted(self) -> bool:
        return self._draft_persisted

    @Property(bool, notify=draftChanged)
    def draftModified(self) -> bool:
        return bool(self._draft) and self._draft != self._original

    @Property(bool, notify=draftChanged)
    def canUndo(self) -> bool:
        return bool(self._undo_stack) and not self.draftBuiltIn

    @Property(bool, notify=draftChanged)
    def canRedo(self) -> bool:
        return bool(self._redo_stack) and not self.draftBuiltIn

    @Property(str, notify=draftChanged)
    def selectedNodeId(self) -> str:
        return self._selected_node_id

    @Property("QVariantMap", notify=draftChanged)
    def selectedNode(self) -> Dict[str, Any]:
        root = self._draft.get("root")
        if not isinstance(root, dict):
            return {}
        return deepcopy(find_layout_node(root, self._selected_node_id) or {})

    @Property(bool, notify=draftChanged)
    def selectedCanRemove(self) -> bool:
        root = self._draft.get("root")
        return bool(
            not self.draftBuiltIn
            and isinstance(root, dict)
            and str(root.get("id")) != self._selected_node_id
            and self._node_location(root, self._selected_node_id) is not None
        )

    @Property(bool, notify=draftChanged)
    def selectedCanMoveEarlier(self) -> bool:
        return self._selected_can_move(-1)

    @Property(bool, notify=draftChanged)
    def selectedCanMoveLater(self) -> bool:
        return self._selected_can_move(1)

    @Property(str, notify=draftChanged)
    def previewHtml(self) -> str:
        return self._preview_html

    @Property("QStringList", notify=draftChanged)
    def usedFields(self) -> List[str]:
        root = self._draft.get("root")
        if not isinstance(root, dict):
            return []
        used = {
            str(row.get("field") or "")
            for row in flatten_layout_tree(root)
            if row.get("nodeType") == "field"
        }
        return [field for field in LAYOUT_FIELDS if field in used]

    @Property(bool, notify=draftChanged)
    def previewProjectDataAvailable(self) -> bool:
        return self._project_sample_values() is not None

    @Property(bool, notify=draftChanged)
    def previewUsesProjectData(self) -> bool:
        return self._preview_uses_project_data

    @Property("QStringList", constant=True)
    def fieldKeys(self) -> List[str]:
        return list(LAYOUT_FIELDS)

    @Slot(str)
    def begin(self, kind: str) -> None:
        self._kind = normalize_layout_kind(kind)
        self._refresh_library()
        templates = self._templates()
        active_id = self._settings.get_active_layout_template_id(self._kind)
        selected = next(
            (item for item in templates if item["id"] == active_id),
            templates[0],
        )
        self._load_draft(selected)
        self.changed.emit()

    @Slot()
    def refresh(self) -> None:
        """Refresh active markers without replacing an in-progress draft."""
        self._refresh_library()

    @Slot(str)
    def createTemplate(self, name: str = "") -> None:
        label = str(name or "Новый макет").strip()[:80]
        self._load_draft(
            new_layout_template(self._kind, label), persisted=False
        )

    @Slot(str)
    def loadTemplate(self, template_id: str) -> None:
        template = self._find_template(template_id)
        if template is not None:
            self._load_draft(template)

    @Slot(str)
    def duplicateTemplate(self, template_id: str) -> None:
        template = self._find_template(template_id)
        if template is None:
            return
        self._load_draft(
            duplicate_layout_template(template), persisted=False
        )

    @Slot(str)
    def setDraftName(self, value: str) -> None:
        if not self._draft or self.draftBuiltIn:
            return
        name = str(value or "").strip()[:80]
        if name and name != self._draft.get("name"):
            self._record_history()
            self._draft["name"] = name
            self._refresh_draft()

    @Slot(bool)
    def setPreviewUsesProjectData(self, enabled: bool) -> None:
        enabled = bool(enabled) and self.previewProjectDataAvailable
        if self._preview_uses_project_data == enabled:
            return
        self._preview_uses_project_data = enabled
        self._refresh_draft(normalize=False)

    @Slot()
    def undo(self) -> None:
        if not self.canUndo:
            return
        self._redo_stack.append((deepcopy(self._draft), self._selected_node_id))
        self._draft, self._selected_node_id = self._undo_stack.pop()
        self._refresh_draft(normalize=False)

    @Slot()
    def redo(self) -> None:
        if not self.canRedo:
            return
        self._undo_stack.append((deepcopy(self._draft), self._selected_node_id))
        self._draft, self._selected_node_id = self._redo_stack.pop()
        self._refresh_draft(normalize=False)

    @Slot()
    def revertDraft(self) -> None:
        if self._original:
            self._record_history()
            self._draft = deepcopy(self._original)
            self._selected_node_id = str(
                self._draft.get("root", {}).get("id") or ""
            )
            self._refresh_draft()

    @Slot(result=bool)
    def saveDraft(self) -> bool:
        if not self._draft or self.draftBuiltIn:
            self.errorRequested.emit(
                "Встроенный макет нельзя изменить. Сначала создайте его копию."
            )
            return False
        normalized = normalize_layout_template(
            self._draft, forced_kind=self._kind
        )
        library = self._settings.get_layout_templates()
        items = library[self._kind]
        for index, item in enumerate(items):
            if item["id"] == normalized["id"]:
                items[index] = normalized
                break
        else:
            items.append(normalized)
        previous = deepcopy(self._settings.settings)
        self._settings.set_layout_templates(library)
        if not self._settings.save_settings(self._settings.settings):
            self._settings.settings = previous
            self.errorRequested.emit("Не удалось сохранить макет")
            return False
        self._draft = deepcopy(normalized)
        self._original = deepcopy(normalized)
        self._draft_persisted = True
        self._refresh_library()
        self._refresh_draft()
        self.statusRequested.emit(f"Макет «{normalized['name']}» сохранён")
        return True

    @Slot(str, result=bool)
    def deleteTemplate(self, template_id: str) -> bool:
        template = self._find_template(template_id)
        if template is None or template.get("built_in"):
            return False
        library = self._settings.get_layout_templates()
        library[self._kind] = [
            item for item in library[self._kind]
            if item["id"] != template_id
        ]
        previous = deepcopy(self._settings.settings)
        self._settings.set_layout_templates(library)
        if self._settings.get_active_layout_template_id(self._kind) == template_id:
            fallback = builtin_layout_templates(self._kind)[0]["id"]
            self._settings.set_active_layout_template_id(self._kind, fallback)
        if not self._settings.save_settings(self._settings.settings):
            self._settings.settings = previous
            self.errorRequested.emit("Не удалось удалить макет")
            return False
        self.begin(self._kind)
        self._emit_target_changed()
        self.statusRequested.emit(f"Макет «{template['name']}» удалён")
        return True

    @Slot(str, result=bool)
    def activateTemplate(self, template_id: str) -> bool:
        template = (
            deepcopy(self._draft)
            if self._draft.get("id") == template_id
            else self._find_template(template_id)
        )
        if template is None:
            return False
        if not template.get("built_in") and self._draft.get("id") == template_id:
            if (self.draftDirty or self._find_template(template_id) is None) \
                    and not self.saveDraft():
                return False
            template = self._find_template(template_id)
            if template is None:
                return False
        previous = deepcopy(self._settings.settings)
        self._settings.set_active_layout_template_id(self._kind, template_id)
        self._sync_legacy_layout(template_id)
        if not self._settings.save_settings(self._settings.settings):
            self._settings.settings = previous
            self.errorRequested.emit("Не удалось выбрать макет")
            return False
        self._refresh_library()
        self._emit_target_changed()
        self.statusRequested.emit(f"Выбран макет «{template['name']}»")
        return True

    @Slot(str)
    def selectNode(self, node_id: str) -> None:
        root = self._draft.get("root")
        if isinstance(root, dict) and find_layout_node(root, node_id):
            self._selected_node_id = str(node_id)
            self.draftChanged.emit()

    @Slot(str, str)
    def addNode(self, node_type: str, field: str = "") -> None:
        if self.draftBuiltIn:
            self.errorRequested.emit(
                "Встроенный макет нельзя изменить. Сначала создайте его копию."
            )
            return
        parent = self._selected_container()
        if parent is None:
            return
        node_type = str(node_type)
        if node_type == "field":
            field = str(field)
            if field not in LAYOUT_FIELDS:
                return
            if any(row["field"] == field for row in flatten_layout_tree(self._draft["root"])):
                self.errorRequested.emit(f"Поле «{FIELD_LABELS[field]}» уже добавлено")
                return
            size = 30 if field == "replica" else 18
            if self._kind == "teleprompter":
                size = round(size * 1.35)
            child = {
                "type": "field",
                "field": field,
                "style": {
                    "font_size": size,
                    "bold": field == "character",
                    "italic": field == "actor",
                    "alignment": "left",
                },
            }
        elif node_type in {"row", "column"}:
            child = {"type": node_type, "children": [], "gap": 8}
        elif node_type in {"separator", "spacer"}:
            child = {"type": node_type}
        else:
            return
        self._record_history()
        normalized_child = normalize_layout_template({
            "kind": self._kind,
            "root": child,
        })["root"]
        parent.setdefault("children", []).append(normalized_child)
        self._selected_node_id = normalized_child["id"]
        self._refresh_draft(normalize=False)

    @Slot()
    def removeSelectedNode(self) -> None:
        self.removeNode(self._selected_node_id)

    @Slot(str)
    def removeNode(self, node_id: str) -> None:
        if self.draftBuiltIn:
            return
        root = self._draft.get("root")
        if not isinstance(root, dict) or str(node_id) == str(root.get("id")):
            return
        location = self._node_location(root, str(node_id))
        if location is None:
            return
        self._record_history()
        parent, index = location
        parent["children"].pop(index)
        self._selected_node_id = str(parent.get("id") or "")
        self._refresh_draft(normalize=False)

    @Slot(int)
    def moveSelectedNode(self, direction: int) -> None:
        self.moveNode(self._selected_node_id, direction)

    @Slot(str, int)
    def moveNode(self, node_id: str, direction: int) -> None:
        if self.draftBuiltIn or direction not in {-1, 1}:
            return
        root = self._draft.get("root")
        if not isinstance(root, dict):
            return
        location = self._node_location(root, str(node_id))
        if location is None:
            return
        parent, index = location
        target = index + direction
        if not 0 <= target < len(parent["children"]):
            return
        self._record_history()
        parent["children"][index], parent["children"][target] = (
            parent["children"][target], parent["children"][index]
        )
        self._selected_node_id = str(node_id)
        self._refresh_draft(normalize=False)

    @Slot(str, str)
    def moveNodeBefore(self, source_id: str, target_id: str) -> None:
        """Reorder siblings after a direct-manipulation drag in the tree."""
        if self.draftBuiltIn or source_id == target_id:
            return
        root = self._draft.get("root")
        if not isinstance(root, dict):
            return
        source = self._node_location(root, source_id)
        target = self._node_location(root, target_id)
        if source is None or target is None or source[0] is not target[0]:
            return
        self._record_history()
        parent = source[0]
        source_index = source[1]
        target_index = target[1]
        node = parent["children"].pop(source_index)
        if source_index < target_index:
            target_index -= 1
        parent["children"].insert(target_index, node)
        self._selected_node_id = str(source_id)
        self._refresh_draft(normalize=False)

    @Slot(str, "QVariant")
    def setSelectedNodeValue(self, key: str, value: Any) -> None:
        self.setNodeValue(self._selected_node_id, key, value)

    @Slot(str, str, "QVariant")
    def setNodeValue(self, node_id: str, key: str, value: Any) -> None:
        if self.draftBuiltIn:
            return
        root = self._draft.get("root")
        node = find_layout_node(root, str(node_id)) if isinstance(root, dict) else None
        if node is None:
            return
        draft_before = deepcopy(self._draft)
        previous = deepcopy(node)
        if key in {"weight", "gap", "size"}:
            try:
                node[key] = int(value)
            except (TypeError, ValueError):
                return
        elif key in {"font_size", "bold", "italic", "alignment"} and node.get("type") == "field":
            node.setdefault("style", {})[key] = value
        else:
            return
        if node == previous:
            return
        self._record_history(draft_before)
        selected_id = str(node_id)
        self._draft = normalize_layout_template(
            self._draft, forced_kind=self._kind
        )
        self._selected_node_id = selected_id
        self._refresh_draft(normalize=False)

    def _templates(self) -> List[Dict[str, Any]]:
        return (
            builtin_layout_templates(self._kind)
            + self._settings.get_layout_templates()[self._kind]
        )

    def _find_template(self, template_id: str) -> Optional[Dict[str, Any]]:
        return next(
            (deepcopy(item) for item in self._templates() if item["id"] == template_id),
            None,
        )

    def _load_draft(
        self, template: Dict[str, Any], *, persisted: bool = True
    ) -> None:
        self._draft = normalize_layout_template(
            template,
            forced_kind=self._kind,
            allow_built_in=True,
        )
        self._original = deepcopy(self._draft)
        self._draft_persisted = persisted
        self._selected_node_id = str(self._draft["root"]["id"])
        self._undo_stack = []
        self._redo_stack = []
        self._refresh_draft(normalize=False)

    def _refresh_library(self) -> None:
        active_id = self._settings.get_active_layout_template_id(self._kind)
        self._library_model.set_rows([
            {
                "templateId": item["id"],
                "name": item["name"],
                "builtIn": bool(item.get("built_in")),
                "active": item["id"] == active_id,
                "kind": self._kind,
            }
            for item in self._templates()
        ])
        self.changed.emit()

    def _refresh_draft(self, *, normalize: bool = True) -> None:
        if normalize:
            selected_id = self._selected_node_id
            self._draft = normalize_layout_template(
                self._draft,
                forced_kind=self._kind,
                allow_built_in=self.draftBuiltIn,
            )
            self._selected_node_id = selected_id
        root = self._draft.get("root", {})
        self._tree_model.set_rows(flatten_layout_tree(root))
        if find_layout_node(root, self._selected_node_id) is None:
            self._selected_node_id = str(root.get("id") or "")
        project_values = (
            self._project_sample_values()
            if self._preview_uses_project_data else None
        )
        if self._preview_uses_project_data and project_values is None:
            self._preview_uses_project_data = False
        self._preview_html = preview_html(
            self._draft,
            selected_node_id=self._selected_node_id,
            interactive=True,
            editable=not self.draftBuiltIn,
            sample_values=project_values,
        )
        self.draftChanged.emit()

    def _record_history(
        self, draft: Optional[Dict[str, Any]] = None
    ) -> None:
        if self.draftBuiltIn or not self._draft:
            return
        self._undo_stack.append((
            deepcopy(draft if draft is not None else self._draft),
            self._selected_node_id,
        ))
        if len(self._undo_stack) > 60:
            self._undo_stack.pop(0)
        self._redo_stack = []

    def _project_sample_values(self) -> Optional[Dict[str, str]]:
        if self._session is None or self._script_text_service is None:
            return None
        episode = str(getattr(self._session, "current_episode", "") or "")
        if not episode:
            return None
        data = getattr(self._session, "data", {})
        if not isinstance(data, dict):
            return None
        try:
            lines = self._script_text_service.load_episode_lines(data, episode)
        except (OSError, ValueError, TypeError):
            return None
        line = next((item for item in lines if item.get("text")), None)
        if not isinstance(line, dict):
            return None
        character = str(line.get("char") or "ПЕРСОНАЖ")
        actor_id = get_actor_for_character(data, character, episode)
        actor = data.get("actors", {}).get(actor_id, {}) if actor_id else {}
        actor_name = str(actor.get("name") or "Актёр не назначен")

        def timestamp(value: Any) -> str:
            try:
                seconds = max(0, int(float(value)))
            except (TypeError, ValueError):
                seconds = 0
            hours, remainder = divmod(seconds, 3600)
            minutes, secs = divmod(remainder, 60)
            return f"{hours:02d}:{minutes:02d}:{secs:02d}"

        return {
            "timecode": (
                f"{timestamp(line.get('s', 0))} — "
                f"{timestamp(line.get('e', 0))}"
            ),
            "character": character,
            "actor": actor_name,
            "replica": str(line.get("text") or ""),
        }

    def _selected_container(self) -> Optional[Dict[str, Any]]:
        root = self._draft.get("root")
        if not isinstance(root, dict):
            return None
        selected = find_layout_node(root, self._selected_node_id)
        if selected and selected.get("type") in {"row", "column"}:
            return selected
        location = self._node_location(root, self._selected_node_id)
        return location[0] if location else root

    def _node_location(
        self, root: Dict[str, Any], node_id: str
    ) -> Optional[Tuple[Dict[str, Any], int]]:
        for index, child in enumerate(root.get("children", [])):
            if str(child.get("id")) == str(node_id):
                return root, index
            if child.get("type") in {"row", "column"}:
                found = self._node_location(child, node_id)
                if found is not None:
                    return found
        return None

    def _selected_can_move(self, direction: int) -> bool:
        root = self._draft.get("root")
        if self.draftBuiltIn or not isinstance(root, dict):
            return False
        location = self._node_location(root, self._selected_node_id)
        if location is None:
            return False
        parent, index = location
        return 0 <= index + direction < len(parent.get("children", []))

    def _sync_legacy_layout(self, template_id: str) -> None:
        if not template_id.startswith("builtin."):
            return
        suffix = template_id.rsplit(".", 1)[-1]
        labels = {
            "table": "Таблица",
            "scenario1": "Сценарий 1",
            "scenario2": "Сценарий 2",
            "scenario3": "Сценарий 3",
        }
        layout_type = labels.get(suffix)
        if not layout_type:
            return
        if self._kind == "montage":
            config = self._settings.get_default_export_config()
            config["layout_type"] = layout_type
            self._settings.set_default_export_config(config)
        else:
            config = self._settings.get_default_prompter_config()
            config["layout_type"] = layout_type
            self._settings.set_default_prompter_config(config)

    def _emit_target_changed(self) -> None:
        if self._kind == "montage":
            self.montageTemplateChanged.emit()
        else:
            self.teleprompterTemplateChanged.emit()
