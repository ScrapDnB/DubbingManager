"""Service for episode working-text files."""

import json
import os
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from config.constants import SCRIPT_TEXT_DIR_NAME
from services.export_service import ExportService


SCRIPT_TEXT_FORMAT_VERSION = "1.0"


class ScriptTextService:
    """Script Text Service implementation."""

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
        project_path: Optional[str] = None
    ) -> str:
        """Create episode text."""
        normalized_lines = self._ensure_source_ids(lines)
        export_service = ExportService(project_data)
        merged_lines = export_service.process_merge_logic(
            normalized_lines,
            merge_config
        )

        text_data = self._build_episode_payload(
            ep_num,
            source_path,
            merged_lines,
            merge_config
        )

        texts_dir = self.get_texts_dir(project_data, source_path, project_path)
        texts_dir.mkdir(parents=True, exist_ok=True)

        text_path = texts_dir / f"episode_{self._safe_episode_num(ep_num)}.json"
        self.backup_episode_text(text_path, ep_num, "recreate")
        with open(text_path, 'w', encoding='utf-8') as f:
            json.dump(text_data, f, ensure_ascii=False, indent=4)

        project_data.setdefault("episode_texts", {})[ep_num] = str(text_path)
        return str(text_path)

    def load_episode_text(self, path: str) -> Dict[str, Any]:
        """Load episode text."""
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def load_episode_lines(
        self,
        project_data: Dict[str, Any],
        ep_num: str
    ) -> List[Dict[str, Any]]:
        """Load episode lines."""
        text_path = project_data.get("episode_texts", {}).get(ep_num)
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

    def find_existing_episode_text(
        self,
        project_data: Dict[str, Any],
        ep_num: str,
        project_path: Optional[str] = None
    ) -> Optional[str]:
        """Find an existing generated working-text file for an episode."""
        ep_num = str(ep_num)
        current_path = project_data.get("episode_texts", {}).get(ep_num)
        if current_path and os.path.exists(current_path):
            return current_path

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
        if source_path:
            candidates.append(Path(source_path).resolve().parent / SCRIPT_TEXT_DIR_NAME / filename)

        unique_candidates = []
        seen = set()
        for candidate in candidates:
            key = str(candidate)
            if key not in seen:
                seen.add(key)
                unique_candidates.append(candidate)
        return unique_candidates

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
        text_path = project_data.get("episode_texts", {}).get(str(ep_num))
        if not text_path or not os.path.exists(text_path):
            return False

        payload = self.load_episode_text(text_path)
        target = self._find_payload_line(payload.get("lines", []), line_id)
        if not target:
            return False

        if target.get("text", "") == new_text:
            return False

        target["text"] = new_text
        target["dirty"] = True
        payload["modified_at"] = datetime.now().isoformat()

        self.backup_episode_text(text_path, ep_num, "edit")
        with open(text_path, 'w', encoding='utf-8') as f:
            json.dump(payload, f, ensure_ascii=False, indent=4)

        return True

    def rename_character(
        self,
        project_data: Dict[str, Any],
        old_name: str,
        new_name: str,
        ep_num: Optional[str] = None
    ) -> int:
        """Rename character."""
        episode_texts = project_data.get("episode_texts", {})
        if ep_num is not None:
            items = [(str(ep_num), episode_texts.get(str(ep_num)))]
        else:
            items = list(episode_texts.items())

        updated_files = 0
        for _, text_path in items:
            if not text_path or not os.path.exists(text_path):
                continue

            payload = self.load_episode_text(text_path)
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
                self.backup_episode_text(text_path, ep_num or payload.get("episode"), "rename")
                with open(text_path, 'w', encoding='utf-8') as f:
                    json.dump(payload, f, ensure_ascii=False, indent=4)
                updated_files += 1

        return updated_files

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

    def _build_episode_payload(
        self,
        ep_num: str,
        source_path: str,
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

        return {
            "format_version": SCRIPT_TEXT_FORMAT_VERSION,
            "episode": ep_num,
            "source": source_info,
            "merge_config": merge_config.copy(),
            "characters": {
                char: {"display_name": char}
                for char in characters
            },
            "lines": payload_lines
        }

    def _safe_episode_num(self, ep_num: str) -> str:
        """Safe episode num."""
        safe = ''.join(ch if ch.isalnum() else '_' for ch in ep_num.strip())
        return safe or "episode"
