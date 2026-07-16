"""Feature-specific QML backend objects."""

from .actor_library_bridge import ActorLibraryBridge
from .audiobook_bridge import AudiobookBridge
from .casting_bridge import CastingBridge
from .converter_bridge import ConverterBridge
from .docx_import_bridge import DocxImportBridge
from .montage_bridge import MontageBridge
from .project_bridge import ProjectBridge
from .project_files_bridge import ProjectFilesBridge
from .reaper_bridge import ReaperBridge
from .reports_bridge import ReportsBridge
from .roles_bridge import RolesBridge
from .settings_bridge import SettingsBridge
from .subtitle_import_bridge import SubtitleImportBridge
from .teleprompter_bridge import TeleprompterBridge
from .ui_state_bridge import UiStateBridge
from .update_bridge import UpdateBridge
from .video_bridge import VideoBridge

__all__ = [
    "ActorLibraryBridge",
    "AudiobookBridge",
    "MontageBridge",
    "CastingBridge",
    "ConverterBridge",
    "DocxImportBridge",
    "ProjectBridge",
    "ProjectFilesBridge",
    "ReaperBridge",
    "ReportsBridge",
    "RolesBridge",
    "SettingsBridge",
    "SubtitleImportBridge",
    "TeleprompterBridge",
    "UiStateBridge",
    "UpdateBridge",
    "VideoBridge",
]
