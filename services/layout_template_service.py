"""Validation and editing primitives for user-defined visual layouts."""

from __future__ import annotations

from copy import deepcopy
from html import escape
from typing import Any, Dict, Iterable, List, Optional
from uuid import uuid4


LAYOUT_KINDS = ("montage", "teleprompter")
LAYOUT_NODE_TYPES = ("row", "column", "field", "separator", "spacer")
LAYOUT_FIELDS = ("timecode", "character", "actor", "replica")
MAX_LAYOUT_DEPTH = 4
MAX_LAYOUT_CHILDREN = 12

FIELD_LABELS = {
    "timecode": "Таймкод",
    "character": "Персонаж",
    "actor": "Актёр",
    "replica": "Реплика",
}
NODE_LABELS = {
    "row": "Горизонтальная группа",
    "column": "Вертикальная группа",
    "separator": "Линия-разделитель",
    "spacer": "Отступ",
}


def _node_id(prefix: str = "node") -> str:
    return f"{prefix}-{uuid4().hex[:12]}"


def _field_node(field: str, *, size: int, bold: bool = False) -> Dict[str, Any]:
    return {
        "id": _node_id(field),
        "type": "field",
        "field": field,
        "weight": 1,
        "style": {
            "font_size": size,
            "bold": bold,
            "italic": field == "actor",
            "alignment": "left",
        },
    }


def _container(node_type: str, children: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    return {
        "id": _node_id(node_type),
        "type": node_type,
        "gap": 8,
        "weight": 1,
        "children": list(children),
    }


def default_layout_tree(kind: str) -> Dict[str, Any]:
    """Return a practical editable starting tree for one target."""
    normalized_kind = normalize_layout_kind(kind)
    multiplier = 1.35 if normalized_kind == "teleprompter" else 1.0

    def size(value: int) -> int:
        return round(value * multiplier)

    return _container("column", [
        _container("row", [
            _field_node("character", size=size(20), bold=True),
            _field_node("timecode", size=size(18)),
            _field_node("actor", size=size(15)),
        ]),
        _field_node("replica", size=size(30)),
    ])


def _builtin_template(
    kind: str,
    template_id: str,
    name: str,
    root: Dict[str, Any],
) -> Dict[str, Any]:
    return {
        "schema_version": 1,
        "id": template_id,
        "kind": kind,
        "name": name,
        "built_in": True,
        "root": root,
    }


def builtin_layout_templates(kind: str) -> List[Dict[str, Any]]:
    """Return immutable layouts mirroring the existing application presets."""
    normalized_kind = normalize_layout_kind(kind)
    large = normalized_kind == "teleprompter"
    scale = 1.35 if large else 1.0

    def field(name: str, value: int, bold: bool = False) -> Dict[str, Any]:
        return _field_node(name, size=round(value * scale), bold=bold)

    scenario1 = _container("column", [
        _container("row", [
            field("character", 20, True),
            field("timecode", 18),
            field("actor", 14),
        ]),
        field("replica", 30),
    ])
    scenario2 = _container("column", [
        _container("row", [
            field("timecode", 18, True),
            field("character", 20, True),
            field("actor", 14),
        ]),
        field("replica", 34),
    ])
    metadata = _container("column", [
        field("timecode", 18, True),
        field("character", 20, True),
        field("actor", 14),
    ])
    metadata["weight"] = 1
    replica = field("replica", 30)
    replica["weight"] = 3
    scenario3 = _container("row", [metadata, replica])

    prefix = f"builtin.{normalized_kind}"
    templates: List[Dict[str, Any]] = []
    if normalized_kind == "montage":
        table_fields = [
            field("timecode", 18, True),
            field("character", 15, True),
            field("actor", 14),
            field("replica", 20),
        ]
        for item, weight in zip(table_fields, (2, 3, 2, 6)):
            item["weight"] = weight
        table = _container("row", table_fields)
        templates.append(_builtin_template(
            normalized_kind, f"{prefix}.table", "Таблица", table
        ))
    templates.extend([
        _builtin_template(
            normalized_kind, f"{prefix}.scenario1", "Сценарий 1", scenario1
        ),
        _builtin_template(
            normalized_kind, f"{prefix}.scenario2", "Сценарий 2", scenario2
        ),
        _builtin_template(
            normalized_kind, f"{prefix}.scenario3", "Сценарий 3", scenario3
        ),
    ])
    return templates


def normalize_layout_kind(value: Any) -> str:
    value = str(value or "")
    return value if value in LAYOUT_KINDS else "montage"


def _integer(value: Any, low: int, high: int, fallback: int) -> int:
    try:
        return max(low, min(high, int(value)))
    except (TypeError, ValueError):
        return fallback


def normalize_layout_node(
    value: Any,
    *,
    depth: int = 0,
    seen_ids: Optional[set[str]] = None,
) -> Dict[str, Any]:
    """Return a bounded, renderer-safe layout node."""
    if seen_ids is None:
        seen_ids = set()
    source = value if isinstance(value, dict) else {}
    node_type = str(source.get("type") or "column")
    if node_type not in LAYOUT_NODE_TYPES:
        node_type = "column"
    if depth >= MAX_LAYOUT_DEPTH and node_type in {"row", "column"}:
        node_type = "field"
        source = {**source, "field": "replica"}

    raw_id = str(source.get("id") or "").strip()
    node_id = raw_id[:80] if raw_id and raw_id not in seen_ids else _node_id(node_type)
    seen_ids.add(node_id)
    result: Dict[str, Any] = {
        "id": node_id,
        "type": node_type,
        "weight": _integer(source.get("weight"), 1, 10, 1),
    }

    if node_type in {"row", "column"}:
        result["gap"] = _integer(source.get("gap"), 0, 48, 8)
        children = source.get("children")
        if not isinstance(children, list):
            children = []
        result["children"] = [
            normalize_layout_node(child, depth=depth + 1, seen_ids=seen_ids)
            for child in children[:MAX_LAYOUT_CHILDREN]
        ]
        return result

    if node_type == "field":
        field = str(source.get("field") or "replica")
        result["field"] = field if field in LAYOUT_FIELDS else "replica"
        style = source.get("style") if isinstance(source.get("style"), dict) else {}
        result["style"] = {
            "font_size": _integer(style.get("font_size"), 8, 300, 24),
            "bold": bool(style.get("bold", result["field"] == "character")),
            "italic": bool(style.get("italic", result["field"] == "actor")),
            "alignment": (
                str(style.get("alignment"))
                if str(style.get("alignment")) in {"left", "center", "right"}
                else "left"
            ),
        }
    elif node_type == "spacer":
        result["size"] = _integer(source.get("size"), 2, 100, 12)
    return result


def normalize_layout_template(
    value: Any,
    *,
    forced_kind: Optional[str] = None,
    allow_built_in: bool = False,
) -> Dict[str, Any]:
    """Normalize one persisted template and strip unsafe/unknown values."""
    source = value if isinstance(value, dict) else {}
    kind = normalize_layout_kind(forced_kind or source.get("kind"))
    name = str(source.get("name") or "Новый макет").strip()[:80]
    template_id = str(source.get("id") or "").strip()[:120]
    if not template_id or (template_id.startswith("builtin.") and not allow_built_in):
        template_id = f"custom.{kind}.{uuid4().hex}"
    return {
        "schema_version": 1,
        "id": template_id,
        "kind": kind,
        "name": name or "Новый макет",
        "built_in": bool(source.get("built_in")) if allow_built_in else False,
        "root": normalize_layout_node(
            source.get("root") or default_layout_tree(kind)
        ),
    }


def normalize_layout_library(value: Any) -> Dict[str, List[Dict[str, Any]]]:
    """Normalize the two separate custom-template collections."""
    source = value if isinstance(value, dict) else {}
    result: Dict[str, List[Dict[str, Any]]] = {}
    for kind in LAYOUT_KINDS:
        items = source.get(kind)
        if not isinstance(items, list):
            items = []
        normalized: List[Dict[str, Any]] = []
        ids: set[str] = set()
        for item in items[:100]:
            template = normalize_layout_template(item, forced_kind=kind)
            if template["id"] in ids:
                template["id"] = f"custom.{kind}.{uuid4().hex}"
            ids.add(template["id"])
            normalized.append(template)
        result[kind] = normalized
    return result


def new_layout_template(kind: str, name: str = "Новый макет") -> Dict[str, Any]:
    return normalize_layout_template({
        "kind": normalize_layout_kind(kind),
        "name": name,
        "root": default_layout_tree(kind),
    })


def duplicate_layout_template(template: Dict[str, Any]) -> Dict[str, Any]:
    copy = deepcopy(template)
    copy["id"] = ""
    copy["built_in"] = False
    copy["name"] = f"{str(copy.get('name') or 'Макет')} — копия"
    return normalize_layout_template(copy, forced_kind=copy.get("kind"))


def flatten_layout_tree(root: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Return display rows for a tree editor."""
    rows: List[Dict[str, Any]] = []

    def visit(node: Dict[str, Any], parent_id: str, depth: int) -> None:
        node_type = str(node.get("type"))
        field = str(node.get("field") or "")
        rows.append({
            "nodeId": str(node.get("id") or ""),
            "parentId": parent_id,
            "depth": depth,
            "nodeType": node_type,
            "field": field,
            "label": FIELD_LABELS.get(field, NODE_LABELS.get(node_type, node_type)),
            "container": node_type in {"row", "column"},
        })
        for child in node.get("children", []):
            if isinstance(child, dict):
                visit(child, str(node.get("id") or ""), depth + 1)

    visit(normalize_layout_node(root), "", 0)
    return rows


def find_layout_node(root: Dict[str, Any], node_id: str) -> Optional[Dict[str, Any]]:
    if str(root.get("id")) == str(node_id):
        return root
    for child in root.get("children", []):
        if isinstance(child, dict):
            found = find_layout_node(child, node_id)
            if found is not None:
                return found
    return None


def layout_template_rows(root: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Project a tree into rows/cells/stacks for the non-recursive QML renderer."""
    normalized = normalize_layout_node(root)

    def stacked_items(node: Dict[str, Any]) -> List[Dict[str, Any]]:
        node_type = node.get("type")
        if node_type in {"field", "separator", "spacer"}:
            return [deepcopy(node)]
        result: List[Dict[str, Any]] = []
        for child in node.get("children", []):
            if isinstance(child, dict):
                result.extend(stacked_items(child))
        return result

    def row_from(node: Dict[str, Any]) -> Dict[str, Any]:
        if node.get("type") == "row":
            children = [
                child for child in node.get("children", [])
                if isinstance(child, dict)
            ]
        else:
            children = [node]
        return {
            "gap": int(node.get("gap", 8)),
            "cells": [
                {
                    "weight": int(child.get("weight", 1)),
                    "gap": int(child.get("gap", 4)),
                    "items": stacked_items(child),
                }
                for child in children
            ],
        }

    if normalized.get("type") == "column":
        return [
            row_from(child)
            for child in normalized.get("children", [])
            if isinstance(child, dict)
        ]
    return [row_from(normalized)]


def preview_html(
    template: Dict[str, Any],
    *,
    selected_node_id: str = "",
    interactive: bool = False,
    editable: bool = False,
    sample_values: Optional[Dict[str, str]] = None,
) -> str:
    """Render a representative preview, optionally as an editing canvas."""
    normalized = normalize_layout_template(
        template,
        forced_kind=template.get("kind") if isinstance(template, dict) else None,
        allow_built_in=True,
    )
    dark = normalized["kind"] == "teleprompter"
    values: Dict[str, str] = {
        "timecode": "00:01:12 — 00:01:15",
        "character": "ГЕРОЙ",
        "actor": "Иван Иванов",
        "replica": "Я совершенно с этим не согласен. Давайте попробуем ещё раз.",
    }
    if isinstance(sample_values, dict):
        for field in LAYOUT_FIELDS:
            if sample_values.get(field):
                values[field] = str(sample_values[field])

    def render(
        node: Dict[str, Any], *, is_root: bool = False
    ) -> str:
        node_type = node["type"]
        weight = int(node.get("weight", 1))
        node_id = str(node.get("id") or "")
        selected = str(selected_node_id) == node_id
        node_classes = ["layout-node", node_type]
        if selected:
            node_classes.append("selected")
        attributes = (
            f"class='{' '.join(node_classes)}' "
            f"data-node-id='{escape(node_id, quote=True)}' "
            f"data-node-type='{escape(node_type, quote=True)}' "
            f"data-weight='{weight}' "
            f"draggable='{'true' if editable and not is_root else 'false'}'"
        )
        controls = ""
        if interactive and selected and editable and not is_root:
            controls = (
                "<div class='node-controls'>"
                "<button data-action='up' title='Переместить раньше'>↑</button>"
                "<button data-action='down' title='Переместить позже'>↓</button>"
                "<button data-action='remove' title='Удалить'>×</button>"
                "</div>"
            )
        if node_type in {"row", "column"}:
            direction = "row" if node_type == "row" else "column"
            rendered_children: List[str] = []
            children = node.get("children", [])
            for index, child in enumerate(children):
                rendered_children.append(render(child))
                if editable and node_type == "row" and index < len(children) - 1:
                    rendered_children.append(
                        "<div class='resize-handle' "
                        f"data-resize-id='{escape(str(child.get('id') or ''), quote=True)}' "
                        f"data-weight='{int(child.get('weight', 1))}' "
                        "title='Потяните, чтобы изменить ширину'></div>"
                    )
            return (
                f"<div {attributes} style='display:flex;"
                f"flex-direction:{direction};gap:{int(node.get('gap', 8))}px;"
                f"flex:{weight} 1 0'>{controls}{''.join(rendered_children)}</div>"
            )
        if node_type == "separator":
            return f"<div {attributes}>{controls}</div>"
        if node_type == "spacer":
            return (
                f"<div {attributes} style='min-height:"
                f"{int(node.get('size', 12))}px'>{controls}</div>"
            )
        field = node.get("field", "replica")
        style = node.get("style", {})
        color = (
            "#ffffff" if dark and field != "actor"
            else "#aaaaaa" if dark
            else "#111111"
        )
        return (
            f"<div {attributes} data-field='{escape(field, quote=True)}' "
            f"style='flex:{weight} 1 0;"
            f"font-size:{int(style.get('font_size', 24))}px;"
            f"font-weight:{'700' if style.get('bold') else '400'};"
            f"font-style:{'italic' if style.get('italic') else 'normal'};"
            f"text-align:{escape(str(style.get('alignment', 'left')))};"
            f"color:{color}'>{controls}{escape(values[field])}</div>"
        )

    background = "#050505" if dark else "#ffffff"
    border = "#454545" if dark else "#dadada"
    sample = render(normalized["root"], is_root=True)
    script = ""
    if interactive:
        script = """
<script>
(() => {
  const prefix = "__DM_LAYOUT__";
  const send = (action, payload = {}) => {
    console.log(prefix + JSON.stringify({action, ...payload}));
  };
  let draggedId = "";
  document.addEventListener("click", event => {
    const actionButton = event.target.closest("[data-action]");
    const node = event.target.closest("[data-node-id]");
    if (!node) return;
    event.stopPropagation();
    const nodeId = node.dataset.nodeId;
    if (actionButton) {
      const action = actionButton.dataset.action;
      if (action === "remove") send("remove", {nodeId});
      if (action === "up") send("move", {nodeId, direction: -1});
      if (action === "down") send("move", {nodeId, direction: 1});
      return;
    }
    send("select", {nodeId});
  });
  document.addEventListener("dragstart", event => {
    const node = event.target.closest("[data-node-id][draggable='true']");
    if (!node) return;
    draggedId = node.dataset.nodeId;
    event.dataTransfer.effectAllowed = "move";
    event.dataTransfer.setData("text/plain", draggedId);
    node.classList.add("dragging");
  });
  document.addEventListener("dragend", event => {
    const node = event.target.closest("[data-node-id]");
    if (node) node.classList.remove("dragging");
    draggedId = "";
  });
  document.addEventListener("dragover", event => {
    if (event.target.closest("[data-node-id]")) event.preventDefault();
  });
  document.addEventListener("drop", event => {
    const target = event.target.closest("[data-node-id]");
    if (!target) return;
    event.preventDefault();
    event.stopPropagation();
    const sourceId = draggedId || event.dataTransfer.getData("text/plain");
    if (sourceId && sourceId !== target.dataset.nodeId) {
      send("moveBefore", {sourceId, targetId: target.dataset.nodeId});
    }
  });
  document.querySelectorAll(".resize-handle").forEach(handle => {
    handle.addEventListener("pointerdown", event => {
      event.preventDefault();
      event.stopPropagation();
      const startX = event.clientX;
      const startWeight = Number(handle.dataset.weight || 1);
      const nodeId = handle.dataset.resizeId;
      handle.setPointerCapture(event.pointerId);
      const finish = finishEvent => {
        const delta = Math.round((finishEvent.clientX - startX) / 55);
        const weight = Math.max(1, Math.min(10, startWeight + delta));
        handle.releasePointerCapture(finishEvent.pointerId);
        handle.removeEventListener("pointerup", finish);
        handle.removeEventListener("pointercancel", finish);
        if (weight !== startWeight) send("setWeight", {nodeId, weight});
      };
      handle.addEventListener("pointerup", finish);
      handle.addEventListener("pointercancel", finish);
    });
  });
})();
</script>"""
    return f"""<!doctype html>
<html><head><meta charset='utf-8'><style>
html,body{{margin:0;min-height:100%;background:{background};font-family:'Segoe UI',sans-serif}}
body{{padding:28px;box-sizing:border-box}}
.sample{{border:1px solid {border};border-radius:8px;padding:18px;margin-bottom:14px}}
.layout-node{{min-width:0;position:relative;box-sizing:border-box;border-radius:4px}}
.layout-node.row{{align-items:flex-start}} .layout-node.column{{min-width:0}}
.layout-node.field{{white-space:pre-wrap;overflow-wrap:anywhere;cursor:pointer}}
.layout-node[draggable='true']{{cursor:grab}}
.layout-node[draggable='true']:active{{cursor:grabbing}}
.layout-node:hover{{outline:1px dashed #4b91e2;outline-offset:3px}}
.layout-node.selected{{outline:2px solid #1976d2;outline-offset:4px}}
.layout-node.dragging{{opacity:.45}}
.separator{{height:1px;background:{border};margin:6px 0}}
.inactive{{opacity:.32}}
.inactive .layout-node{{pointer-events:none}}
.inactive .layout-node.selected{{outline:none}}
.inactive .node-controls{{display:none}}
.node-controls{{position:absolute;right:-5px;top:-30px;z-index:20;display:flex;gap:3px;
background:#1976d2;border-radius:5px;padding:3px;box-shadow:0 2px 8px #0004}}
.node-controls button{{border:0;border-radius:3px;min-width:24px;height:22px;background:#fff;
color:#202020;font:600 13px sans-serif;cursor:pointer}}
.resize-handle{{align-self:stretch;flex:0 0 8px;margin:0 -4px;z-index:10;cursor:col-resize;
border-left:2px solid transparent}}
.resize-handle:hover{{border-left-color:#1976d2;background:#1976d218}}
</style></head><body>
<div class='sample'>{sample}</div>
<div class='sample inactive'>{sample}</div>
{script}</body></html>"""
