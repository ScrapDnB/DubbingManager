"""Controller for subtitle and DOCX import mutations."""

import os
import re
from typing import Any, Dict, List, Optional, Tuple

from core.commands import AddEpisodeCommand
from services.project_metadata_service import maybe_set_project_name_from_first_import
from utils.helpers import set_project_kind


class ImportController:
    """Import source files into project data and working-text storage."""

    def __init__(
        self,
        data_ref: Dict[str, Any],
        episode_service: Any,
        script_text_service: Any,
        undo_stack: Any,
        get_current_project_path: Any,
    ) -> None:
        self.data_ref = data_ref
        self.episode_service = episode_service
        self.script_text_service = script_text_service
        self.undo_stack = undo_stack
        self.get_current_project_path = get_current_project_path

    def suggested_episode_name(self, path: str) -> str:
        """Return a numeric episode suggestion based on a file name."""
        numbers: List[str] = re.findall(r'\d+', os.path.basename(path))
        return " ".join(numbers) or "1"

    def add_subtitle_episode(
        self,
        name: str,
        path: str
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Add ASS/SRT episode, parse it, and create working text."""
        maybe_set_project_name_from_first_import(
            self.data_ref,
            path,
            {".ass"}
        )
        set_project_kind(self.data_ref, "subtitle")
        command = AddEpisodeCommand(
            self.data_ref["episodes"],
            name,
            path
        )
        self.undo_stack.push(command)

        stats, lines = self.parse_source_file(name, path)
        self.create_working_text_for_episode(name, path, lines)
        return stats, lines

    def add_docx_episode(
        self,
        name: str,
        docx_path: str,
        result: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Add a DOCX import result and create working text."""
        set_project_kind(self.data_ref, "subtitle")
        lines = result.get('lines', [])
        episode_lines = self.convert_imported_lines_for_cache(lines)

        command = AddEpisodeCommand(
            self.data_ref["episodes"],
            name,
            docx_path
        )
        self.undo_stack.push(command)

        self.data_ref.setdefault("loaded_episodes", {})[name] = episode_lines
        self.episode_service._loaded_episodes[name] = episode_lines

        self.create_working_text_for_episode(name, docx_path, episode_lines)
        working_lines = self.script_text_service.load_episode_lines(
            self.data_ref,
            name
        )
        if working_lines:
            self.data_ref["loaded_episodes"][name] = working_lines

        return episode_lines

    def parse_source_file(
        self,
        ep: str,
        path: str
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Parse an ASS or SRT source file."""
        extension = os.path.splitext(path)[1].lower()
        if extension == '.srt':
            return self.episode_service.parse_srt_file(path)
        return self.episode_service.parse_ass_file(path)

    def create_working_text_for_episode(
        self,
        ep: str,
        path: str,
        lines: List[Dict[str, Any]]
    ) -> None:
        """Create working text for an imported episode."""
        if not lines:
            return

        merge_config = self.data_ref.get("replica_merge_config", {})
        if os.path.splitext(path or "")[1].lower() == '.docx':
            merge_config = {**merge_config, "merge": False}

        self.script_text_service.create_episode_text(
            self.data_ref,
            ep,
            path,
            lines,
            merge_config,
            self.get_current_project_path()
        )

    def convert_imported_lines_for_cache(
        self,
        lines: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Convert imported DOCX lines into episode cache rows."""
        episode_lines = []
        for idx, line_data in enumerate(lines):
            episode_lines.append({
                'id': idx,
                's': line_data['s'],
                'e': line_data['e'],
                'char': line_data['char'],
                'text': line_data['text'],
                's_raw': line_data.get('s_raw', ''),
                'e_raw': line_data.get('e_raw', ''),
            })
        return episode_lines

    def relink_episode_file(self, ep: str, path: str) -> None:
        """Replace an episode source path."""
        self.data_ref["episodes"][ep] = path
