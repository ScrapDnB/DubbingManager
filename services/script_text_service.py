"""Service for episode working texts stored in project data."""

import json
import os
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from config.constants import (
    DEFAULT_GLOBAL_MERGE_CONFIG,
    DEFAULT_INLINE_TIMECODE_CONFIG,
    SCRIPT_TEXT_DIR_NAME,
)
from services.export_service import ExportService
from services.audiobook_document_service import AudiobookDocumentService
from services.dynamic_script_storage import (
    DynamicScriptStorage,
    is_dynamic_script_project,
)
from services.project_fps_service import effective_merge_config


SCRIPT_TEXT_FORMAT_VERSION = "1.1"


class ScriptTextService:
    """Script Text Service implementation."""

    def __init__(self) -> None:
        self._dynamic = DynamicScriptStorage()
        self._global_merge_config = dict(DEFAULT_GLOBAL_MERGE_CONFIG)

    def set_global_merge_config(self, config: Dict[str, Any]) -> None:
        """Set application-wide merge preferences for rendered text."""
        self._global_merge_config = self._normalize_global_merge_config(config)

    def global_merge_config(self) -> Dict[str, Any]:
        """Return application-wide merge preferences without project FPS."""
        return dict(self._global_merge_config)

    def set_inline_timecode_config(self, config: Dict[str, Any]) -> None:
        """Set global, non-project timing cues for rendered merged text."""
        merged = dict(self._global_merge_config)
        if isinstance(config, dict):
            for key in DEFAULT_INLINE_TIMECODE_CONFIG:
                if key in config:
                    merged[key] = config[key]
        self.set_global_merge_config(merged)

    def inline_timecode_config(self) -> Dict[str, Any]:
        """Return the active global timing-cue settings."""
        return {
            key: self._global_merge_config[key]
            for key in DEFAULT_INLINE_TIMECODE_CONFIG
        }

    @staticmethod
    def uses_dynamic_storage(project_data: Dict[str, Any]) -> bool:
        """Return whether a project uses source-based dynamic scripts."""
        if project_data.get("project_kind") == "audiobook":
            return False
        if not is_dynamic_script_project(project_data):
            return False
        dynamic_episodes = project_data.get("script_storage", {}).get(
            "episodes", {}
        )
        legacy_episodes = project_data.get("episode_working_texts", {})
        legacy_paths = project_data.get("episode_texts", {})
        # Transitional and test fixtures may attach a legacy payload to a new,
        # still-empty project. Treat that document as legacy instead of hiding
        # its only working text.
        return not ((legacy_episodes or legacy_paths) and not dynamic_episodes)

    def get_merge_config(self, project_data: Dict[str, Any]) -> Dict[str, Any]:
        """Return global merge rules combined with the project's FPS."""
        return effective_merge_config(project_data, self._global_merge_config)

    def set_merge_config(
        self,
        project_data: Dict[str, Any],
        config: Dict[str, Any],
    ) -> bool:
        """Compatibility alias: merge rules are global, never project data."""
        before = self.global_merge_config()
        self.set_global_merge_config(config)
        return before != self.global_merge_config()

    @staticmethod
    def _normalize_global_merge_config(config: Any) -> Dict[str, Any]:
        result = dict(DEFAULT_GLOBAL_MERGE_CONFIG)
        if not isinstance(config, dict):
            return result
        result["merge"] = bool(config.get("merge", result["merge"]))
        result["merge_parallel_replicas"] = bool(config.get(
            "merge_parallel_replicas",
            result["merge_parallel_replicas"],
        ))
        result["respect_existing_separators"] = bool(config.get(
            "respect_existing_separators",
            result["respect_existing_separators"],
        ))
        raw_gap = config.get("merge_gap_seconds")
        if raw_gap is None and "merge_gap" in config:
            try:
                raw_gap = float(config["merge_gap"]) / max(
                    0.001, float(config.get("fps", 25.0))
                )
            except (TypeError, ValueError):
                raw_gap = None
        for key, raw_value, low, high in (
            ("merge_gap_seconds", raw_gap, 0.0, 480.0),
            ("p_short", config.get("p_short"), 0.0, 5.0),
            ("p_long", config.get("p_long"), 0.0, 10.0),
            (
                "inline_timecode_min_duration",
                config.get("inline_timecode_min_duration"),
                0.0,
                86400.0,
            ),
        ):
            if raw_value is None:
                continue
            try:
                result[key] = max(low, min(high, float(raw_value)))
            except (TypeError, ValueError):
                pass
        result["inline_timecodes_enabled"] = bool(config.get(
            "inline_timecodes_enabled",
            result["inline_timecodes_enabled"],
        ))
        bracket_style = str(config.get(
            "inline_timecode_brackets",
            result["inline_timecode_brackets"],
        ))
        if bracket_style in {"square", "round", "curly"}:
            result["inline_timecode_brackets"] = bracket_style
        try:
            result["inline_timecode_every"] = max(1, min(
                1000,
                int(config.get(
                    "inline_timecode_every",
                    result["inline_timecode_every"],
                )),
            ))
        except (TypeError, ValueError):
            pass
        return result

    def get_texts_dir(
        self,
        project_data: Dict[str, Any],
        source_path: str,
        project_path: Optional[str] = None
    ) -> Path:
        """Return texts dir."""
        project_folder = project_data.get("project_folder")
        if project_folder:
            return Path(project_folder) / SCRIPT_TEXT_DIR_NAME

        if project_path:
            project_file = Path(project_path)
            return project_file.parent / f"{project_file.stem}_{SCRIPT_TEXT_DIR_NAME}"

        return Path(source_path).resolve().parent / SCRIPT_TEXT_DIR_NAME

    def create_episode_text(
        self,
        project_data: Dict[str, Any],
        ep_num: str,
        source_path: str,
        lines: List[Dict[str, Any]],
        merge_config: Dict[str, Any],
        project_path: Optional[str] = None,
        import_config: Optional[Dict[str, Any]] = None,
        line_mode: Optional[str] = None,
    ) -> str:
        """Create episode text in project data."""
        if self.uses_dynamic_storage(project_data):
            self._dynamic.create_episode(
                project_data,
                str(ep_num),
                source_path,
                lines,
                merge_config,
                import_config,
                line_mode,
            )
            project_data.setdefault("episode_texts", {}).pop(str(ep_num), None)
            project_data.setdefault("episode_working_texts", {}).pop(
                str(ep_num), None
            )
            return str(ep_num)

        normalized_lines = self._ensure_source_ids(lines)
        export_service = ExportService(project_data)
        merged_lines = export_service.process_merge_logic(
            normalized_lines,
            merge_config
        )

        text_data = self._build_episode_payload(
            ep_num,
            source_path,
            normalized_lines,
            merged_lines,
            merge_config
        )

        project_data.setdefault("episode_working_texts", {})[str(ep_num)] = text_data
        project_data.setdefault("episode_texts", {}).pop(str(ep_num), None)
        return str(ep_num)

    def load_episode_text(self, path: str) -> Dict[str, Any]:
        """Load episode text."""
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def load_episode_lines(
        self,
        project_data: Dict[str, Any],
        ep_num: str,
        display_config: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Load episode lines."""
        if self.uses_dynamic_storage(project_data):
            merge_config = self.get_merge_config(project_data)
            if isinstance(display_config, dict):
                merge_config.update(display_config)
            return self._dynamic.display_lines(
                project_data,
                str(ep_num),
                merge_config,
            )

        payload = self.get_episode_payload(project_data, ep_num)
        if not payload:
            text_path = project_data.get("episode_texts", {}).get(str(ep_num))
            if not text_path or not os.path.exists(text_path):
                return []
            payload = self.load_episode_text(text_path)

        result = []
        for idx, line in enumerate(payload.get("lines", [])):
            text = line.get("text", "")
            char = line.get("display_character") or line.get("character", "")
            result.append({
                "id": idx,
                "working_id": line.get("id"),
                "source_ids": line.get("source_ids", []),
                "source_texts": line.get("source_texts", []),
                "s": line.get("start", 0.0),
                "e": line.get("end", 0.0),
                "char": char,
                "source_char": line.get("character", char),
                "text": text,
                "s_raw": line.get("s_raw", ""),
                "parts": [{
                    "id": idx,
                    "text": text,
                    "sep": ""
                }],
                "_working_text": True
            })

        return result

    def load_atomic_episode_lines(
        self,
        project_data: Dict[str, Any],
        ep_num: str,
    ) -> List[Dict[str, Any]]:
        """Return editable, unmerged lines for calculations and editing."""
        if self.uses_dynamic_storage(project_data):
            return self._dynamic.atomic_lines(project_data, str(ep_num))
        return self.load_episode_lines(project_data, str(ep_num))

    def episode_line_count(
        self,
        project_data: Dict[str, Any],
        ep_num: str,
    ) -> int:
        """Return an episode line count without normalizing every line."""
        if self.uses_dynamic_storage(project_data):
            return len(self._dynamic.display_lines(
                project_data,
                str(ep_num),
                self.get_merge_config(project_data),
            ))
        payload = self.get_episode_payload(project_data, ep_num)
        if not payload:
            text_path = project_data.get("episode_texts", {}).get(str(ep_num))
            if not text_path or not os.path.exists(text_path):
                return 0
            payload = self.load_episode_text(text_path)
        lines = payload.get("lines", []) if isinstance(payload, dict) else []
        return len(lines) if isinstance(lines, list) else 0

    def get_source_lines(
        self,
        project_data: Dict[str, Any],
        ep_num: str
    ) -> List[Dict[str, Any]]:
        """Return original imported source lines in app line format."""
        if self.uses_dynamic_storage(project_data):
            return self._dynamic.source_lines(project_data, str(ep_num))
        payload = self.get_episode_payload(project_data, ep_num)
        if not payload:
            return []
        source_lines = payload.get("source_lines")
        if not isinstance(source_lines, list):
            source_lines = self._source_lines_from_payload_lines(payload)
        result = []
        for idx, line in enumerate(source_lines):
            char = line.get("char") or line.get("character", "")
            text = line.get("text", "")
            result.append({
                "id": line.get("id", idx),
                "s": line.get("s", line.get("start", 0.0)),
                "e": line.get("e", line.get("end", 0.0)),
                "char": char,
                "text": text,
                "s_raw": line.get("s_raw", ""),
                "parts": [{
                    "id": line.get("id", idx),
                    "text": text,
                    "sep": ""
                }],
                "_source_line": True,
            })
        return result

    def has_source_ass(
        self,
        project_data: Dict[str, Any],
        ep_num: str
    ) -> bool:
        """Return whether the episode stores an original ASS snapshot."""
        if self.uses_dynamic_storage(project_data):
            payload = self._dynamic.episode_payload(project_data, str(ep_num))
            source = payload.get("source") if payload else None
            return bool(
                isinstance(source, dict)
                and source.get("type") == "ass"
                and source.get("raw_content")
            )
        payload = self.get_episode_payload(project_data, ep_num)
        source_ass = payload.get("source_ass") if payload else None
        return bool(isinstance(source_ass, dict) and source_ass.get("raw_content"))

    def save_source_ass(
        self,
        project_data: Dict[str, Any],
        ep_num: str,
        save_path: str
    ) -> bool:
        """Save the original imported ASS snapshot for an episode."""
        if self.uses_dynamic_storage(project_data):
            payload = self._dynamic.episode_payload(project_data, str(ep_num))
            source = payload.get("source") if payload else None
            raw_content = source.get("raw_content") if isinstance(source, dict) else None
            if not raw_content or source.get("type") != "ass":
                return False
            with open(save_path, "w", encoding="utf-8") as f:
                f.write(raw_content)
            return True
        payload = self.get_episode_payload(project_data, ep_num)
        source_ass = payload.get("source_ass") if payload else None
        raw_content = (
            source_ass.get("raw_content")
            if isinstance(source_ass, dict)
            else None
        )
        if not raw_content:
            return False
        with open(save_path, "w", encoding="utf-8") as f:
            f.write(raw_content)
        return True

    def get_episode_payload(
        self,
        project_data: Dict[str, Any],
        ep_num: str
    ) -> Optional[Dict[str, Any]]:
        """Return embedded working-text payload for an episode."""
        if project_data.get("project_kind") == "audiobook":
            document = project_data.get("audiobook_document")
            if isinstance(document, dict):
                return AudiobookDocumentService().episode_payload(
                    document, str(ep_num)
                )
        if self.uses_dynamic_storage(project_data):
            return self._dynamic.episode_payload(project_data, str(ep_num))
        payload = project_data.get("episode_working_texts", {}).get(str(ep_num))
        return payload if isinstance(payload, dict) else None

    def set_episode_payload(
        self,
        project_data: Dict[str, Any],
        ep_num: str,
        payload: Dict[str, Any]
    ) -> None:
        """Store working-text payload in project data."""
        if self.uses_dynamic_storage(project_data):
            storage = self._dynamic.ensure_storage(project_data)
            storage.setdefault("episodes", {})[str(ep_num)] = payload
            return
        project_data.setdefault("episode_working_texts", {})[str(ep_num)] = payload
        project_data.setdefault("episode_texts", {}).pop(str(ep_num), None)

    def has_imported_source_lines(
        self,
        project_data: Dict[str, Any],
        ep_num: str,
    ) -> bool:
        """Return whether a working text has original, unmerged source lines."""
        if self.uses_dynamic_storage(project_data):
            payload = self._dynamic.episode_payload(project_data, str(ep_num))
            return bool(payload and payload.get("source_lines"))
        payload = self.get_episode_payload(project_data, ep_num)
        return bool(
            isinstance(payload, dict)
            and isinstance(payload.get("source_lines"), list)
            and payload.get("source_lines_origin") != "reconstructed"
        )

    def embed_source_lines_from_source(
        self,
        project_data: Dict[str, Any],
        ep_num: str,
        source_path: str,
        source_lines: List[Dict[str, Any]],
    ) -> bool:
        """Attach an original source-line snapshot to an existing working text."""
        payload = self.get_episode_payload(project_data, ep_num)
        if not isinstance(payload, dict) or not source_lines:
            return False

        normalized_lines = self._ensure_source_ids(source_lines)
        payload["format_version"] = SCRIPT_TEXT_FORMAT_VERSION
        payload["source_lines"] = self._build_source_line_payload(
            normalized_lines
        )
        payload["source_lines_origin"] = "imported"
        payload["source_ass"] = self._build_source_ass_snapshot(
            Path(source_path)
        )
        payload["modified_at"] = datetime.now().isoformat()
        return True

    def find_existing_episode_text(
        self,
        project_data: Dict[str, Any],
        ep_num: str,
        project_path: Optional[str] = None
    ) -> Optional[str]:
        """Find an existing generated working-text file for an episode."""
        ep_num = str(ep_num)
        current_path = project_data.get("episode_texts", {}).get(ep_num)
        for candidate in self._path_candidates(
            project_data, current_path, project_path
        ):
            if candidate.is_file():
                return str(candidate)

        candidates = self._candidate_episode_text_paths(
            project_data,
            ep_num,
            project_path
        )
        for candidate in candidates:
            if (
                candidate.exists() and
                candidate.is_file() and
                self._looks_like_episode_text(candidate, ep_num)
            ):
                return str(candidate)

        return None

    def find_existing_episode_texts(
        self,
        project_data: Dict[str, Any],
        project_path: Optional[str] = None
    ) -> Dict[str, str]:
        """Find existing generated working-text files for project episodes."""
        found = {}
        for ep_num in project_data.get("episodes", {}).keys():
            path = self.find_existing_episode_text(
                project_data,
                str(ep_num),
                project_path
            )
            if path:
                found[str(ep_num)] = path
        return found

    def episode_text_exists(
        self,
        project_data: Dict[str, Any],
        ep_num: str
    ) -> bool:
        """Return whether an episode has an existing working-text file."""
        if self.get_episode_payload(project_data, str(ep_num)) is not None:
            return True
        text_path = project_data.get("episode_texts", {}).get(str(ep_num))
        return bool(text_path and os.path.exists(text_path))

    def link_existing_working_texts(
        self,
        project_data: Dict[str, Any],
        project_path: Optional[str] = None
    ) -> int:
        """Import already generated working texts into project data."""
        if self.uses_dynamic_storage(project_data):
            return 0
        found = self.find_existing_episode_texts(project_data, project_path)
        imported_count = 0

        for ep_num, text_path in found.items():
            if self.get_episode_payload(project_data, str(ep_num)) is not None:
                continue
            try:
                payload = self.load_episode_text(text_path)
            except (OSError, json.JSONDecodeError):
                continue
            self.set_episode_payload(project_data, str(ep_num), payload)
            imported_count += 1

        return imported_count

    def episodes_needing_working_texts(
        self,
        project_data: Dict[str, Any],
        project_path: Optional[str] = None
    ) -> List[str]:
        """Return episodes that can generate but do not have working texts."""
        self.link_existing_working_texts(project_data, project_path)
        episodes = project_data.get("episodes", {})
        return [
            str(ep)
            for ep, path in episodes.items()
            if (
                not self.episode_text_exists(project_data, str(ep)) and
                self.is_text_source_path(path)
            )
        ]

    def is_subtitle_source_path(self, path: str) -> bool:
        """Return whether a path points to a subtitle source."""
        return os.path.splitext(path or "")[1].lower() in {'.ass', '.srt'}

    def is_text_source_path(self, path: str) -> bool:
        """Return whether a path can generate a working text."""
        return os.path.splitext(path or "")[1].lower() in {
            '.ass',
            '.srt',
            '.docx',
        }

    def _candidate_episode_text_paths(
        self,
        project_data: Dict[str, Any],
        ep_num: str,
        project_path: Optional[str] = None
    ) -> List[Path]:
        """Return standard working-text locations for an episode."""
        safe_ep = self._safe_episode_num(ep_num)
        filename = f"episode_{safe_ep}.json"
        candidates = []

        project_folder = project_data.get("project_folder")
        if project_folder:
            candidates.append(Path(project_folder) / SCRIPT_TEXT_DIR_NAME / filename)

        if project_path:
            project_file = Path(project_path)
            candidates.append(
                project_file.parent /
                f"{project_file.stem}_{SCRIPT_TEXT_DIR_NAME}" /
                filename
            )

        source_path = project_data.get("episodes", {}).get(ep_num)
        for resolved_source in self._path_candidates(
            project_data, source_path, project_path
        ):
            candidates.append(
                resolved_source.parent / SCRIPT_TEXT_DIR_NAME / filename
            )

        unique_candidates = []
        seen = set()
        for candidate in candidates:
            key = str(candidate)
            if key not in seen:
                seen.add(key)
                unique_candidates.append(candidate)
        return unique_candidates

    def _path_candidates(
        self,
        project_data: Dict[str, Any],
        raw_path: Optional[str],
        project_path: Optional[str] = None,
    ) -> List[Path]:
        """Return absolute and portable interpretations of a stored path."""
        if not raw_path:
            return []
        path = Path(str(raw_path)).expanduser()
        if path.is_absolute():
            return [path]
        bases = []
        project_folder = project_data.get("project_folder")
        if project_folder:
            bases.append(Path(str(project_folder)).expanduser())
        if project_path:
            bases.append(Path(project_path).expanduser().resolve().parent)
        candidates = [base / path for base in bases]
        candidates.append(path)
        return list(dict.fromkeys(candidate.resolve() for candidate in candidates))

    def _looks_like_episode_text(self, path: Path, ep_num: str) -> bool:
        """Check whether a JSON file is a generated episode working text."""
        try:
            payload = self.load_episode_text(str(path))
        except (OSError, json.JSONDecodeError):
            return False

        if not isinstance(payload, dict):
            return False
        if not isinstance(payload.get("lines"), list):
            return False

        payload_ep = payload.get("episode")
        return payload_ep in (None, ep_num, str(ep_num))

    def update_line_text(
        self,
        project_data: Dict[str, Any],
        ep_num: str,
        line_id: Any,
        new_text: str
    ) -> bool:
        """Update line text."""
        document = self._audiobook_document(project_data)
        if document is not None:
            return AudiobookDocumentService().update_line_text(
                document, str(ep_num), line_id, new_text
            )
        if self.uses_dynamic_storage(project_data):
            return self._dynamic.update_fragment_text(
                project_data, str(ep_num), line_id, new_text
            )
        payload = self.get_episode_payload(project_data, str(ep_num))
        if not payload:
            return False

        target = self._find_payload_line(payload.get("lines", []), line_id)
        if not target:
            return False

        if target.get("text", "") == new_text:
            return False

        target["text"] = new_text
        target["dirty"] = True
        payload["modified_at"] = datetime.now().isoformat()
        return True

    def update_line_character(
        self,
        project_data: Dict[str, Any],
        ep_num: str,
        line_id: Any,
        new_character: str
    ) -> bool:
        """Update one line display character."""
        document = self._audiobook_document(project_data)
        if document is not None:
            return AudiobookDocumentService().update_line_character(
                document, str(ep_num), line_id, new_character
            )
        if self.uses_dynamic_storage(project_data):
            return self._dynamic.update_fragment_character(
                project_data, str(ep_num), line_id, new_character
            )
        payload = self.get_episode_payload(project_data, str(ep_num))
        if not payload:
            return False

        target = self._find_payload_line(payload.get("lines", []), line_id)
        if not target:
            return False

        old_character = (
            target.get("display_character") or
            target.get("character", "")
        )
        if old_character == new_character:
            return False

        target["display_character"] = new_character
        target["dirty"] = True
        payload.setdefault("characters", {}).setdefault(
            new_character,
            {"display_name": new_character}
        )
        payload["modified_at"] = datetime.now().isoformat()
        return True

    def split_line_to_character(
        self,
        project_data: Dict[str, Any],
        ep_num: str,
        line_id: Any,
        remaining_text: str,
        split_text: str,
        split_character: str
    ) -> bool:
        """Split selected text into a new display-character line."""
        document = self._audiobook_document(project_data)
        if document is not None:
            return AudiobookDocumentService().split_line(
                document,
                str(ep_num),
                line_id,
                remaining_text,
                split_text,
                split_character,
            )
        if self.uses_dynamic_storage(project_data):
            return self._dynamic.split_fragment(
                project_data,
                str(ep_num),
                line_id,
                remaining_text,
                split_text,
                split_character,
            )
        payload = self.get_episode_payload(project_data, str(ep_num))
        if not payload:
            return False

        lines = payload.get("lines", [])
        target = self._find_payload_line(lines, line_id)
        if not target:
            return False

        split_text = split_text.strip()
        split_character = split_character.strip()
        if not split_text or not split_character:
            return False

        target_index = lines.index(target)
        target["text"] = remaining_text
        target["dirty"] = True

        new_line = target.copy()
        new_line["id"] = self._make_split_line_id(lines, target, target_index)
        new_line["character"] = split_character
        new_line["display_character"] = split_character
        new_line["text"] = split_text
        new_line["source_texts"] = [split_text]
        new_line["dirty"] = True

        lines.insert(target_index + 1, new_line)
        payload.setdefault("characters", {}).setdefault(
            split_character,
            {"display_name": split_character}
        )
        payload["modified_at"] = datetime.now().isoformat()
        return True

    def rename_character(
        self,
        project_data: Dict[str, Any],
        old_name: str,
        new_name: str,
        ep_num: Optional[str] = None
    ) -> int:
        """Rename character."""
        document = self._audiobook_document(project_data)
        if document is not None:
            return AudiobookDocumentService().rename_character(
                document, old_name, new_name, ep_num
            )
        if self.uses_dynamic_storage(project_data):
            return self._dynamic.rename_character(
                project_data, old_name, new_name, ep_num
            )
        episode_texts = project_data.get("episode_working_texts", {})
        if ep_num is not None:
            items = [(str(ep_num), episode_texts.get(str(ep_num)))]
        else:
            items = list(episode_texts.items())

        updated_files = 0
        for _, payload in items:
            if not isinstance(payload, dict):
                continue

            changed = False

            for char_key, char_data in payload.get("characters", {}).items():
                if (
                    char_key == old_name or
                    char_data.get("display_name", char_key) == old_name
                ):
                    char_data["display_name"] = new_name
                    changed = True

            for line in payload.get("lines", []):
                display_name = line.get("display_character") or line.get("character", "")
                if display_name == old_name:
                    line["display_character"] = new_name
                    changed = True

            if changed:
                payload["modified_at"] = datetime.now().isoformat()
                updated_files += 1

        return updated_files

    @staticmethod
    def _audiobook_document(
        project_data: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        if project_data.get("project_kind") != "audiobook":
            return None
        document = project_data.get("audiobook_document")
        return document if isinstance(document, dict) else None

    def backup_episode_text(
        self,
        text_path: Any,
        ep_num: Optional[Any] = None,
        reason: str = "backup"
    ) -> Optional[str]:
        """Create a timestamped backup for an existing working-text file."""
        source = Path(text_path)
        if not source.exists() or not source.is_file():
            return None

        backup_dir = source.parent / ".backups"
        backup_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        safe_ep = self._safe_episode_num(str(ep_num or source.stem))
        safe_reason = re.sub(r'[^A-Za-z0-9_-]+', '_', reason).strip('_') or "backup"
        target = backup_dir / f"{source.stem}_{safe_ep}_{safe_reason}_{timestamp}.json"
        shutil.copy2(source, target)
        return str(target)

    def _ensure_source_ids(
        self,
        lines: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Ensure source ids."""
        normalized = []
        for idx, line in enumerate(lines):
            item = line.copy()
            item.setdefault('id', idx)
            normalized.append(item)
        return normalized

    def _find_payload_line(
        self,
        lines: List[Dict[str, Any]],
        line_id: Any
    ) -> Optional[Dict[str, Any]]:
        """Find payload line."""
        line_id_str = str(line_id)
        for idx, line in enumerate(lines):
            if str(line.get("id")) == line_id_str:
                return line
            try:
                if int(line_id) == idx:
                    return line
            except (TypeError, ValueError):
                pass
        return None

    def _make_split_line_id(
        self,
        lines: List[Dict[str, Any]],
        target: Dict[str, Any],
        target_index: int
    ) -> str:
        """Return a unique id for a line split from another line."""
        base = str(target.get("id") or f"line_{target_index + 1}")
        existing = {str(line.get("id")) for line in lines}
        suffix = 1
        while True:
            candidate = f"{base}_split_{suffix}"
            if candidate not in existing:
                return candidate
            suffix += 1

    def _build_episode_payload(
        self,
        ep_num: str,
        source_path: str,
        source_lines: List[Dict[str, Any]],
        merged_lines: List[Dict[str, Any]],
        merge_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Build episode payload."""
        source = Path(source_path)
        characters = sorted({
            line.get('char', '')
            for line in merged_lines
            if line.get('char', '') != ''
        })

        payload_lines = []
        for idx, line in enumerate(merged_lines, 1):
            char = line.get('char', '')
            payload_lines.append({
                "id": f"{self._safe_episode_num(ep_num)}_{idx:04d}",
                "source_ids": line.get('source_ids', [line.get('id')]),
                "start": line.get('s', 0.0),
                "end": line.get('e', 0.0),
                "s_raw": line.get('s_raw', ''),
                "character": char,
                "display_character": char,
                "text": line.get('text', ''),
                "source_texts": line.get('source_texts', [line.get('text', '')]),
                "dirty": False
            })

        source_info = {
            "type": source.suffix.lower().lstrip('.'),
            "path": str(source),
            "imported_at": datetime.now().isoformat(),
            "mtime": source.stat().st_mtime if source.exists() else None
        }
        source_line_payload = self._build_source_line_payload(source_lines)
        source_ass = self._build_source_ass_snapshot(source)

        return {
            "format_version": SCRIPT_TEXT_FORMAT_VERSION,
            "episode": ep_num,
            "source": source_info,
            "source_ass": source_ass,
            "source_lines_origin": "imported",
            "source_lines": source_line_payload,
            "merge_config": merge_config.copy(),
            "characters": {
                char: {"display_name": char}
                for char in characters
            },
            "lines": payload_lines
        }

    def _build_source_line_payload(
        self,
        source_lines: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Build normalized original source line payload."""
        result = []
        for idx, line in enumerate(source_lines):
            source_id = line.get("id", idx)
            result.append({
                "id": source_id,
                "start": line.get("s", 0.0),
                "end": line.get("e", 0.0),
                "s_raw": line.get("s_raw", ""),
                "character": line.get("char", ""),
                "text": line.get("text", ""),
            })
        return result

    def _build_source_ass_snapshot(self, source: Path) -> Optional[Dict[str, Any]]:
        """Return original ASS file content for later source export."""
        if source.suffix.lower() != ".ass" or not source.exists():
            return None
        try:
            raw_content = source.read_text(encoding="utf-8")
        except OSError:
            return None
        return {
            "filename": source.name,
            "raw_content": raw_content,
            "imported_at": datetime.now().isoformat(),
        }

    def _source_lines_from_payload_lines(
        self,
        payload: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Reconstruct a legacy source-lines view from merged payload lines."""
        reconstructed = []
        for line in payload.get("lines", []):
            source_ids = line.get("source_ids") or [line.get("id")]
            source_texts = line.get("source_texts") or [line.get("text", "")]
            for idx, source_id in enumerate(source_ids):
                reconstructed.append({
                    "id": source_id,
                    "start": line.get("start", 0.0),
                    "end": line.get("end", 0.0),
                    "s_raw": line.get("s_raw", ""),
                    "character": line.get("character", ""),
                    "text": (
                        source_texts[idx]
                        if idx < len(source_texts)
                        else line.get("text", "")
                    ),
                })
        return reconstructed

    def _safe_episode_num(self, ep_num: str) -> str:
        """Safe episode num."""
        safe = ''.join(ch if ch.isalnum() else '_' for ch in ep_num.strip())
        return safe or "episode"
