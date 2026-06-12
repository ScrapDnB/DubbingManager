"""Quick subtitle-to-montage conversion helpers."""

import os
from copy import deepcopy
from typing import Any, Dict, List, Tuple

from config.constants import DEFAULT_EXPORT_CONFIG
from services.export_service import ExportService


class QuickSubtitleService:
    """Convert standalone ASS/SRT files to montage export formats."""

    SUPPORTED_EXTENSIONS = {".ass", ".srt"}

    def __init__(self, episode_service: Any, data_ref: Dict[str, Any]) -> None:
        self.episode_service = episode_service
        self.data_ref = data_ref

    @classmethod
    def is_supported_path(cls, path: str) -> bool:
        """Return True if path is a supported subtitle source."""
        return os.path.splitext(path)[1].lower() in cls.SUPPORTED_EXTENSIONS

    @classmethod
    def supported_files(cls, paths: List[str]) -> List[str]:
        """Return existing supported subtitle files."""
        return [
            path for path in paths
            if os.path.isfile(path) and cls.is_supported_path(path)
        ]

    def parse_file(
        self,
        path: str
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Parse a subtitle file for quick conversion."""
        extension = os.path.splitext(path)[1].lower()
        if extension == ".srt":
            return self.episode_service.parse_srt_file(path)
        if extension == ".ass":
            return self.episode_service.parse_ass_file(path)
        raise ValueError("поддерживаются только ASS и SRT")

    def preview_lines(self, path: str) -> List[Dict[str, Any]]:
        """Return normalized lines for quick preview."""
        _stats, lines = self.parse_file(path)
        if not lines:
            raise ValueError("в файле нет реплик")
        return self.normalize_lines(lines)

    def export_montage(
        self,
        path: str,
        export_html: bool,
        export_docx: bool
    ) -> List[str]:
        """Export one subtitle file to montage files next to it."""
        _stats, lines = self.parse_file(path)
        if not lines:
            raise ValueError("в файле нет реплик")
        lines = self.normalize_lines(lines)

        cfg = self.export_config()
        project_data = {
            "project_name": os.path.splitext(os.path.basename(path))[0],
            "actors": {},
            "global_map": {},
            "episode_actor_map": {},
            "export_config": cfg,
            "replica_merge_config": deepcopy(
                self.data_ref.get("replica_merge_config", {})
            ),
        }
        export_service = ExportService(project_data)
        processed = export_service.process_merge_logic(
            lines,
            project_data["replica_merge_config"]
        )
        exported: List[str] = []

        if export_html:
            html_path = self.output_path(path, ".html")
            html = export_service.generate_html(
                "1",
                processed,
                cfg,
                highlight_ids=[],
                layout_type=cfg.get("layout_type", "Таблица"),
                is_editable=False
            )
            with open(html_path, "w", encoding="utf-8") as file:
                file.write(html)
            exported.append(html_path)

        if export_docx:
            docx_path = self.output_path(path, ".docx")
            document = export_service.create_docx_document({"1": processed}, cfg)
            document.save(docx_path)
            exported.append(docx_path)

        return exported

    def normalize_lines(
        self,
        lines: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Ensure quick-converted subtitle lines have stable ids."""
        normalized = []
        for idx, line in enumerate(lines):
            line_data = line.copy()
            line_data.setdefault("id", idx)
            normalized.append(line_data)
        return normalized

    def export_config(self) -> Dict[str, Any]:
        """Return current export config without actor color highlighting."""
        cfg = deepcopy(DEFAULT_EXPORT_CONFIG)
        cfg.update(deepcopy(self.data_ref.get("export_config", {})))
        cfg["use_color"] = False
        cfg["highlight_ids_export"] = []
        cfg["highlight_negative_ids_export"] = []
        cfg["allow_edit"] = False
        return cfg

    def output_path(self, source_path: str, extension: str) -> str:
        """Return a unique montage path next to the source subtitle file."""
        folder = os.path.dirname(source_path)
        stem = os.path.splitext(os.path.basename(source_path))[0]
        base = os.path.join(folder, stem)
        candidate = f"{base}{extension}"
        counter = 2
        while os.path.exists(candidate):
            candidate = f"{base} ({counter}){extension}"
            counter += 1
        return candidate
