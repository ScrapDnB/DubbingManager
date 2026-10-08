"""Dynamic source-line storage for project format 2.0."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime
import hashlib
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional
from uuid import uuid4

from config.constants import (
    DEFAULT_REPLICA_MERGE_CONFIG,
)
from services.replica_merge_service import ReplicaMergeService


DYNAMIC_SCRIPT_MODEL = "dynamic_source"
DYNAMIC_SCRIPT_SCHEMA_REVISION = 1
SOURCE_LINE_MODE_ATOMIC = "atomic"
SOURCE_LINE_MODE_PREMERGED = "premerged"
SOURCE_LINE_MODES = {
    SOURCE_LINE_MODE_ATOMIC,
    SOURCE_LINE_MODE_PREMERGED,
}


def is_dynamic_script_project(project_data: Dict[str, Any]) -> bool:
    """Return whether *project_data* uses the dynamic source-line model."""
    storage = project_data.get("script_storage")
    return bool(
        isinstance(storage, dict)
        and storage.get("model") == DYNAMIC_SCRIPT_MODEL
    )


def new_script_storage(
    merge_config: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Return an empty dynamic script-storage container."""
    return {
        "model": DYNAMIC_SCRIPT_MODEL,
        "schema_revision": DYNAMIC_SCRIPT_SCHEMA_REVISION,
        "episodes": {},
    }


class DynamicScriptStorage:
    """Read and mutate source-based subtitle scripts."""

    def __init__(self) -> None:
        self._merger = ReplicaMergeService()

    def ensure_storage(
        self,
        project_data: Dict[str, Any],
        merge_config: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        storage = project_data.get("script_storage")
        if not isinstance(storage, dict):
            storage = new_script_storage(merge_config)
            project_data["script_storage"] = storage
        storage.setdefault("model", DYNAMIC_SCRIPT_MODEL)
        storage.setdefault("schema_revision", DYNAMIC_SCRIPT_SCHEMA_REVISION)
        storage.pop("merge_config", None)
        storage.setdefault("episodes", {})
        return storage

    def episode_payload(
        self,
        project_data: Dict[str, Any],
        episode: str,
    ) -> Optional[Dict[str, Any]]:
        storage = project_data.get("script_storage")
        if not isinstance(storage, dict):
            return None
        episodes = storage.get("episodes")
        if not isinstance(episodes, dict):
            return None
        payload = episodes.get(str(episode))
        return payload if isinstance(payload, dict) else None

    def create_episode(
        self,
        project_data: Dict[str, Any],
        episode: str,
        source_path: str,
        lines: List[Dict[str, Any]],
        merge_config: Optional[Dict[str, Any]] = None,
        import_config: Optional[Dict[str, Any]] = None,
        line_mode: Optional[str] = None,
    ) -> Dict[str, Any]:
        storage = self.ensure_storage(project_data, merge_config)

        source = Path(source_path)
        source_lines = []
        for order, line in enumerate(lines):
            source_id = self._new_id("src")
            source_lines.append({
                "id": source_id,
                "order": order,
                "start": float(line.get("s", line.get("start", 0.0)) or 0.0),
                "end": float(line.get("e", line.get("end", 0.0)) or 0.0),
                "s_raw": str(line.get("s_raw", "") or ""),
                "e_raw": str(line.get("e_raw", "") or ""),
                "character": str(
                    line.get("char", line.get("character", "")) or ""
                ),
                "text": str(line.get("text", "") or ""),
                "origin": {
                    "imported_id": line.get("id", order),
                    "event_index": line.get("event_index", order),
                },
            })

        payload = {
            "schema_revision": DYNAMIC_SCRIPT_SCHEMA_REVISION,
            "source": self._source_snapshot(
                source,
                import_config,
                self._normalized_line_mode(line_mode, source.suffix),
            ),
            "source_lines": source_lines,
            "edit_blocks": [],
            "character_aliases": {},
            "created_at": datetime.now().isoformat(),
            "modified_at": datetime.now().isoformat(),
        }
        storage["episodes"][str(episode)] = payload
        return payload

    def source_lines(
        self,
        project_data: Dict[str, Any],
        episode: str,
    ) -> List[Dict[str, Any]]:
        payload = self.episode_payload(project_data, episode)
        if not payload:
            return []
        result = []
        for line in payload.get("source_lines", []):
            if not isinstance(line, dict):
                continue
            item = deepcopy(line)
            item.update({
                "s": float(line.get("start", 0.0) or 0.0),
                "e": float(line.get("end", 0.0) or 0.0),
                "char": str(line.get("character", "") or ""),
                "_source_line": True,
            })
            result.append(item)
        return result

    def atomic_lines(
        self,
        project_data: Dict[str, Any],
        episode: str,
    ) -> List[Dict[str, Any]]:
        payload = self.episode_payload(project_data, episode)
        if not payload:
            return []

        source_lines = [
            line for line in payload.get("source_lines", [])
            if isinstance(line, dict) and line.get("id")
        ]
        aliases = payload.get("character_aliases", {})
        if not isinstance(aliases, dict):
            aliases = {}
        blocks = [
            block for block in payload.get("edit_blocks", [])
            if isinstance(block, dict)
        ]
        block_by_first: Dict[str, Dict[str, Any]] = {}
        covered: set[str] = set()
        for block in blocks:
            source_ids = [str(value) for value in block.get("source_ids", [])]
            if not source_ids or any(value in covered for value in source_ids):
                continue
            block_by_first[source_ids[0]] = block
            covered.update(source_ids)

        source_by_id = {str(line["id"]): line for line in source_lines}
        result: List[Dict[str, Any]] = []
        index = 0
        while index < len(source_lines):
            source_line = source_lines[index]
            source_id = str(source_line["id"])
            block = block_by_first.get(source_id)
            if block is not None:
                block_source_ids = [
                    str(value) for value in block.get("source_ids", [])
                    if str(value) in source_by_id
                ]
                block_sources = [source_by_id[value] for value in block_source_ids]
                if block_sources:
                    start = float(block_sources[0].get("start", 0.0) or 0.0)
                    end = float(block_sources[-1].get("end", start) or start)
                    s_raw = str(block_sources[0].get("s_raw", "") or "")
                    for fragment in block.get("fragments", []):
                        if not isinstance(fragment, dict):
                            continue
                        character = str(fragment.get("character", "") or "")
                        result.append({
                            "id": str(fragment.get("id") or self._new_id("frag")),
                            "s": start,
                            "e": end,
                            "s_raw": s_raw,
                            "char": aliases.get(character, character),
                            "source_char": character,
                            "text": str(fragment.get("text", "") or ""),
                            "source_line_ids": list(block_source_ids),
                            "edit_block_id": str(block.get("id") or ""),
                            "_dynamic_fragment": True,
                        })
                    index += max(1, len(block_source_ids))
                    continue

            character = str(source_line.get("character", "") or "")
            result.append({
                "id": source_id,
                "s": float(source_line.get("start", 0.0) or 0.0),
                "e": float(source_line.get("end", 0.0) or 0.0),
                "s_raw": str(source_line.get("s_raw", "") or ""),
                "char": aliases.get(character, character),
                "source_char": character,
                "text": str(source_line.get("text", "") or ""),
                "source_line_ids": [source_id],
                "_dynamic_fragment": True,
            })
            index += 1
        return result

    def display_lines(
        self,
        project_data: Dict[str, Any],
        episode: str,
        display_config: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        atomic = self.atomic_lines(project_data, episode)
        payload = self.episode_payload(project_data, episode)
        source = payload.get("source", {}) if payload else {}
        line_mode = self._normalized_line_mode(
            source.get("line_mode") if isinstance(source, dict) else None,
            source.get("type") if isinstance(source, dict) else None,
        )
        merge_config = deepcopy(DEFAULT_REPLICA_MERGE_CONFIG)
        if isinstance(display_config, dict):
            merge_config.update(display_config)
        merged = (
            self._preserve_lines(atomic)
            if line_mode == SOURCE_LINE_MODE_PREMERGED
            else self._merger.process(atomic, merge_config)
        )
        source_ids_by_fragment = {
            str(line.get("id")): list(line.get("source_line_ids", []))
            for line in atomic
        }
        result = []
        for index, line in enumerate(merged):
            item = deepcopy(line)
            edit_ids = [str(value) for value in line.get("source_ids", [])]
            source_line_ids = list(self._flatten_unique(
                source_ids_by_fragment.get(value, []) for value in edit_ids
            ))
            item.update({
                "id": index,
                "working_id": edit_ids[0] if len(edit_ids) == 1 else None,
                "edit_ids": edit_ids,
                "source_line_ids": source_line_ids,
                "source_ids": edit_ids,
                "_working_text": True,
                "_dynamic_text": True,
            })
            result.append(item)
        return result

    def update_fragment_text(
        self,
        project_data: Dict[str, Any],
        episode: str,
        fragment_id: Any,
        text: str,
    ) -> bool:
        target = self._ensure_editable_fragment(
            project_data, episode, str(fragment_id)
        )
        if target is None or str(target.get("text", "")) == text:
            return False
        target["text"] = text
        self._touch(project_data, episode)
        return True

    def update_fragment_character(
        self,
        project_data: Dict[str, Any],
        episode: str,
        fragment_id: Any,
        character: str,
    ) -> bool:
        target = self._ensure_editable_fragment(
            project_data, episode, str(fragment_id)
        )
        if target is None or str(target.get("character", "")) == character:
            return False
        target["character"] = character
        self._touch(project_data, episode)
        return True

    def split_fragment(
        self,
        project_data: Dict[str, Any],
        episode: str,
        fragment_id: Any,
        remaining_text: str,
        split_text: str,
        split_character: str,
    ) -> bool:
        payload = self.episode_payload(project_data, episode)
        if not payload:
            return False
        target = self._ensure_editable_fragment(
            project_data, episode, str(fragment_id)
        )
        if target is None or not split_text.strip() or not split_character.strip():
            return False
        for block in payload.get("edit_blocks", []):
            fragments = block.get("fragments", []) if isinstance(block, dict) else []
            if target not in fragments:
                continue
            position = fragments.index(target)
            target["text"] = remaining_text
            fragments.insert(position + 1, {
                "id": self._new_id("frag"),
                "text": split_text.strip(),
                "character": split_character.strip(),
            })
            self._touch(project_data, episode)
            return True
        return False

    def rename_episode(
        self,
        project_data: Dict[str, Any],
        old_name: str,
        new_name: str,
    ) -> None:
        storage = project_data.get("script_storage")
        episodes = storage.get("episodes") if isinstance(storage, dict) else None
        if isinstance(episodes, dict) and old_name in episodes:
            episodes[new_name] = episodes.pop(old_name)

    def delete_episode(self, project_data: Dict[str, Any], episode: str) -> None:
        storage = project_data.get("script_storage")
        episodes = storage.get("episodes") if isinstance(storage, dict) else None
        if isinstance(episodes, dict):
            episodes.pop(str(episode), None)

    def rename_character(
        self,
        project_data: Dict[str, Any],
        old_name: str,
        new_name: str,
        episode: Optional[str] = None,
    ) -> int:
        storage = project_data.get("script_storage")
        episodes = storage.get("episodes") if isinstance(storage, dict) else None
        if not isinstance(episodes, dict):
            return 0
        items = (
            [(str(episode), episodes.get(str(episode)))]
            if episode is not None
            else list(episodes.items())
        )
        changed_count = 0
        for episode_name, payload in items:
            if not isinstance(payload, dict):
                continue
            aliases = payload.setdefault("character_aliases", {})
            changed = False
            for source_character, displayed in list(aliases.items()):
                if str(displayed) != old_name:
                    continue
                if str(source_character) == new_name:
                    aliases.pop(source_character, None)
                else:
                    aliases[source_character] = new_name
                changed = True
            if any(
                str(line.get("character", "")) == old_name
                for line in payload.get("source_lines", [])
                if isinstance(line, dict)
            ) and aliases.get(old_name) != new_name:
                aliases[old_name] = new_name
                changed = True
            for block in payload.get("edit_blocks", []):
                if not isinstance(block, dict):
                    continue
                for fragment in block.get("fragments", []):
                    if (
                        isinstance(fragment, dict)
                        and str(fragment.get("character", "")) == old_name
                    ):
                        fragment["character"] = new_name
                        changed = True
            if changed:
                payload["modified_at"] = datetime.now().isoformat()
                changed_count += 1
        return changed_count

    def _ensure_editable_fragment(
        self,
        project_data: Dict[str, Any],
        episode: str,
        fragment_id: str,
    ) -> Optional[Dict[str, Any]]:
        payload = self.episode_payload(project_data, episode)
        if not payload:
            return None
        for block in payload.get("edit_blocks", []):
            if not isinstance(block, dict):
                continue
            for fragment in block.get("fragments", []):
                if isinstance(fragment, dict) and str(fragment.get("id")) == fragment_id:
                    return fragment

        source = next((
            line for line in payload.get("source_lines", [])
            if isinstance(line, dict) and str(line.get("id")) == fragment_id
        ), None)
        if source is None:
            return None
        fragment = {
            "id": fragment_id,
            "text": str(source.get("text", "") or ""),
            "character": str(source.get("character", "") or ""),
        }
        payload.setdefault("edit_blocks", []).append({
            "id": self._new_id("edit"),
            "source_ids": [fragment_id],
            "fragments": [fragment],
        })
        return fragment

    def _touch(self, project_data: Dict[str, Any], episode: str) -> None:
        payload = self.episode_payload(project_data, episode)
        if payload is not None:
            payload["modified_at"] = datetime.now().isoformat()

    @staticmethod
    def _new_id(prefix: str) -> str:
        return f"{prefix}_{uuid4().hex}"

    @staticmethod
    def _flatten_unique(groups: Iterable[Iterable[str]]) -> Iterable[str]:
        seen: set[str] = set()
        for group in groups:
            for value in group:
                value = str(value)
                if value not in seen:
                    seen.add(value)
                    yield value

    @staticmethod
    def _source_snapshot(
        source: Path,
        import_config: Optional[Dict[str, Any]],
        line_mode: str,
    ) -> Dict[str, Any]:
        raw_content = None
        digest = None
        if source.exists() and source.is_file():
            try:
                raw_bytes = source.read_bytes()
                digest = hashlib.sha256(raw_bytes).hexdigest()
                if source.suffix.lower() in {".ass", ".srt"}:
                    raw_content = raw_bytes.decode("utf-8")
            except (OSError, UnicodeDecodeError):
                pass
        return {
            "type": source.suffix.lower().lstrip("."),
            "line_mode": line_mode,
            "path": str(source),
            "filename": source.name,
            "sha256": digest,
            "imported_at": datetime.now().isoformat(),
            "mtime": source.stat().st_mtime if source.exists() else None,
            "import_config": deepcopy(import_config or {}),
            "raw_content": raw_content,
        }

    @staticmethod
    def _normalized_line_mode(value: Any, source_type: Any = None) -> str:
        """Return source line semantics, including old dynamic DOCX fallback."""
        normalized = str(value or "").strip().lower()
        if normalized in SOURCE_LINE_MODES:
            return normalized
        normalized_type = str(source_type or "").strip().lower().lstrip(".")
        if normalized_type == "docx":
            return SOURCE_LINE_MODE_PREMERGED
        return SOURCE_LINE_MODE_ATOMIC

    @staticmethod
    def _preserve_lines(lines: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Prepare display rows without combining or decomposing source rows."""
        result = []
        for line in lines:
            item = deepcopy(line)
            fragment_id = item.get("id")
            text = str(item.get("text", "") or "")
            item["parts"] = [{
                "id": fragment_id,
                "text": text,
                "sep": "",
            }]
            item["source_ids"] = [fragment_id]
            item["source_texts"] = [text]
            result.append(item)
        return result
