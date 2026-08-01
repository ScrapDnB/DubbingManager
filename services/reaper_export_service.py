"""UI-independent orchestration for Reaper project and marker exports."""

from pathlib import Path
from typing import Any, Dict, List

from services.export_service import ExportService


class ReaperExportService:
    """Prepare and save Reaper exports for one project."""

    def __init__(
        self,
        data_ref: Dict[str, Any],
        project_folder_service: Any,
    ) -> None:
        self.data_ref = data_ref
        self.project_folder_service = project_folder_service

    def resolve_video_path(self, ep_num: str) -> str:
        return self.project_folder_service.resolve_project_path(
            self.data_ref,
            self.data_ref.get("video_paths", {}).get(ep_num),
        )

    def preview(
        self,
        ep_num: str,
        lines: List[Dict[str, Any]],
        video_path: str,
        use_video: bool,
        use_regions: bool,
        transliterate_actor_names: bool,
        marker_mode: str = "merged",
    ) -> Dict[str, Any]:
        return ExportService(self.data_ref).get_reaper_rpp_preview(
            ep_num,
            lines,
            merge_cfg=self.data_ref.get("replica_merge_config", {}),
            video_path=video_path,
            use_video=use_video,
            use_regions=use_regions,
            transliterate_actor_names=transliterate_actor_names,
            marker_mode=marker_mode,
        )

    def has_source_markers(self, ep_num: str) -> bool:
        return ExportService(self.data_ref).has_reaper_source_markers(ep_num)

    def default_filename(self, ep_num: str) -> str:
        return f"{self.data_ref.get('project_name', 'Project')} - Ep{ep_num}.rpp"

    def default_csv_filename(
        self,
        ep_num: str,
        filename_format: str = "source_ass",
    ) -> str:
        """Return the preferred CSV filename for an episode's markers.

        ASS imports retain the source filename in the working-text payload, so
        marker CSVs can use the familiar subtitle filename.  Other sources use
        a stable project-and-episode fallback.
        """
        if filename_format == "source_ass":
            source_filename = self._source_ass_filename(ep_num)
            if source_filename:
                return str(Path(source_filename).with_suffix(".csv"))
        return f"{self.data_ref.get('project_name', 'Project')} - {ep_num}.csv"

    def _source_ass_filename(self, ep_num: str) -> str:
        """Return an imported ASS basename, if this episode has one."""
        payload = self.data_ref.get("episode_working_texts", {}).get(
            str(ep_num), {}
        )
        if isinstance(payload, dict):
            source_ass = payload.get("source_ass")
            if isinstance(source_ass, dict):
                filename = str(source_ass.get("filename") or "")
                if Path(filename).suffix.lower() == ".ass":
                    return Path(filename).name

            source = payload.get("source")
            if isinstance(source, dict):
                source_type = str(source.get("type") or "").lower()
                if source_type and source_type != "ass":
                    return ""
                source_path = str(source.get("path") or "")
                if Path(source_path).suffix.lower() == ".ass":
                    return Path(source_path).name

        episode_path = str(self.data_ref.get("episodes", {}).get(ep_num) or "")
        if Path(episode_path).suffix.lower() == ".ass":
            return Path(episode_path).name
        return ""

    def save(
        self,
        ep_num: str,
        lines: List[Dict[str, Any]],
        save_path: str,
        video_path: str,
        use_video: bool,
        use_regions: bool,
        transliterate_actor_names: bool,
        marker_mode: str = "merged",
    ) -> None:
        export_service = ExportService(self.data_ref)
        content = export_service.generate_reaper_rpp(
            ep_num,
            lines,
            merge_cfg=self.data_ref.get("replica_merge_config", {}),
            video_path=video_path,
            use_video=use_video,
            use_regions=use_regions,
            transliterate_actor_names=transliterate_actor_names,
            marker_mode=marker_mode,
        )
        export_service.save_reaper_rpp(save_path, content)

    def save_marker_csv(
        self,
        ep_num: str,
        lines: List[Dict[str, Any]],
        save_path: str,
        marker_mode: str = "merged",
    ) -> None:
        export_service = ExportService(self.data_ref)
        marker_lines = export_service.get_reaper_marker_lines(
            ep_num,
            lines,
            merge_cfg=self.data_ref.get("replica_merge_config", {}),
            marker_mode=marker_mode,
        )
        export_service.save_reaper_marker_csv(save_path, ep_num, marker_lines)
