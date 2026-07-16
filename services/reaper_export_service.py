"""UI-independent orchestration for Reaper project and marker exports."""

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

    def default_csv_filename(self, ep_num: str) -> str:
        return (
            f"{self.data_ref.get('project_name', 'Project')} - "
            f"Ep{ep_num} markers.csv"
        )

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
