"""Composition root for the QML application backend."""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QObject, Property, Signal, Slot

from services import (
    EpisodeService,
    ProjectFolderService,
    ProjectHealthService,
    ScriptTextService,
)
from services.global_settings_service import GlobalSettingsService
from services.project_service import ProjectService
from ui.qml_backend.features import (
    ActorLibraryBridge,
    AudiobookBridge,
    CastingBridge,
    ConverterBridge,
    DocxImportBridge,
    MontageBridge,
    ProjectBridge,
    ProjectFilesBridge,
    ReaperBridge,
    ReportsBridge,
    RolesBridge,
    SettingsBridge,
    SubtitleImportBridge,
    TeleprompterBridge,
    UiStateBridge,
    UpdateBridge,
    VideoBridge,
)
from ui.qml_backend.project_session import ProjectSession
from utils.i18n import set_language


class AppBridge(QObject):
    """Assemble feature backends and route cross-feature application events."""

    statusTextChanged = Signal()
    errorOccurred = Signal(str)

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._global_settings_service = GlobalSettingsService()
        self._global_settings = self._global_settings_service.load_settings()
        # The QML beta is released with a Russian-only interface for now.
        set_language("ru")

        self._project_service = ProjectService(
            self._global_settings_service.get_backup_config()
        )
        self._episode_service = EpisodeService()
        self._script_text_service = ScriptTextService()
        self._project_folder_service = ProjectFolderService()
        self._project_health_service = ProjectHealthService()
        initial_project = self._project_service.create_new_project("Новый проект")
        initial_project.update({
            "export_config": (
                self._global_settings_service.get_default_export_config()
            ),
            "prompter_config": (
                self._global_settings_service.get_default_prompter_config()
            ),
            "replica_merge_config": (
                self._global_settings_service.get_replica_merge_config()
            ),
            "ass_import_config": (
                self._global_settings_service.get_ass_import_config()
            ),
            "srt_import_config": (
                self._global_settings_service.get_srt_import_config()
            ),
            "docx_import_config": (
                self._global_settings_service.get_docx_import_config()
            ),
        })
        self._session = ProjectSession(
            self._project_service,
            initial_project,
            parent=self,
        )
        self._status_text = "Интерфейс готов"

        self._ui_state = UiStateBridge(parent=self)
        self._updates = UpdateBridge(self)
        self._project = ProjectBridge(
            self._session,
            self._episode_service,
            self._script_text_service,
            self._project_folder_service,
            self._global_settings_service,
            self._global_settings,
            self,
        )
        self._project_files = ProjectFilesBridge(
            self._session,
            self._project_folder_service,
            self._project_health_service,
            self._episode_service,
            self._script_text_service,
            self,
        )
        self._casting = CastingBridge(
            self._session,
            self._episode_service,
            self._script_text_service,
            self,
        )
        self._actor_library = ActorLibraryBridge(
            self._session,
            self._global_settings_service,
            self._global_settings,
            self,
        )
        self._roles = RolesBridge(
            self._session,
            self._script_text_service,
            self,
        )
        self._settings = SettingsBridge(
            self._session,
            self._episode_service,
            self._global_settings_service,
            self._global_settings,
            self,
        )
        self._docx_import = DocxImportBridge(
            self._session,
            self._episode_service,
            self._script_text_service,
            self._global_settings_service,
            self,
        )
        self._audiobook = AudiobookBridge(
            self._session,
            self._script_text_service,
            self._global_settings_service,
            self,
        )
        self._subtitle_import = SubtitleImportBridge(
            self._session,
            self._episode_service,
            self._script_text_service,
            self,
        )
        self._converter = ConverterBridge(self._session, self)
        self._reports = ReportsBridge(
            self._session,
            self._script_text_service,
            self._global_settings_service,
            self,
        )
        self._teleprompter = TeleprompterBridge(
            self._session,
            self._episode_service,
            self._script_text_service,
            self._global_settings_service,
            self._project.episodesModel,
            self,
        )
        self._reaper = ReaperBridge(
            self._session,
            self._project_folder_service,
            self._script_text_service,
            self,
        )
        self._video = VideoBridge(
            self._session,
            self._project_folder_service,
            self._script_text_service,
            self,
        )
        self._montage = MontageBridge(
            self._session,
            self._episode_service,
            self._script_text_service,
            self._project.episodesModel,
            self,
        )

        self._connect_feature_events()
        self.refresh()

    def _connect_feature_events(self) -> None:
        features = (
            self._updates,
            self._project,
            self._project_files,
            self._casting,
            self._actor_library,
            self._roles,
            self._settings,
            self._docx_import,
            self._audiobook,
            self._subtitle_import,
            self._converter,
            self._reports,
            self._teleprompter,
            self._reaper,
            self._video,
            self._montage,
        )
        for feature in features:
            status_signal = getattr(feature, "statusRequested", None)
            if status_signal is not None:
                status_signal.connect(self._set_status)
            error_signal = getattr(feature, "errorRequested", None)
            if error_signal is not None:
                error_signal.connect(self._show_error)

        mutating_features = (
            self._project_files,
            self._casting,
            self._actor_library,
            self._roles,
            self._settings,
            self._docx_import,
            self._audiobook,
            self._subtitle_import,
            self._teleprompter,
            self._montage,
        )
        for feature in mutating_features:
            feature.projectDataChanged.connect(
                self._on_feature_project_data_changed
            )

        self._project.resetRequested.connect(self._on_project_reset_requested)
        self._project.refreshRequested.connect(
            self._on_project_refresh_requested
        )
        self._project_files.episodeDeletionRequested.connect(
            self._project.deleteEpisode
        )
        self._casting.actorCreated.connect(
            self._actor_library.rememberProjectActor
        )
        self._settings.backupConfigChanged.connect(
            self._project.setBackupConfig
        )
        self._settings.globalPrompterConfigChanged.connect(
            self._teleprompter.notify_global_config_changed
        )
        self._audiobook.projectNameChanged.connect(
            self._project.nameChanged
        )
        self._subtitle_import.projectNameChanged.connect(
            self._project.nameChanged
        )
        self._reports.navigationRequested.connect(self._open_search_result)
        self._montage.episodeSelectionRequested.connect(
            self._project.selectEpisode
        )

    @Property(str, notify=statusTextChanged)
    def statusText(self) -> str:
        return self._status_text

    @Property(QObject, constant=True)
    def project(self) -> QObject:
        return self._project

    @Property(QObject, constant=True)
    def uiState(self) -> QObject:
        return self._ui_state

    @Property(QObject, constant=True)
    def updates(self) -> QObject:
        return self._updates

    @Property(QObject, constant=True)
    def casting(self) -> QObject:
        return self._casting

    @Property(QObject, constant=True)
    def actorLibrary(self) -> QObject:
        return self._actor_library

    @Property(QObject, constant=True)
    def roles(self) -> QObject:
        return self._roles

    @Property(QObject, constant=True)
    def settings(self) -> QObject:
        return self._settings

    @Property(QObject, constant=True)
    def docxImport(self) -> QObject:
        return self._docx_import

    @Property(QObject, constant=True)
    def audiobook(self) -> QObject:
        return self._audiobook

    @Property(QObject, constant=True)
    def subtitleImport(self) -> QObject:
        return self._subtitle_import

    @Property(QObject, constant=True)
    def converter(self) -> QObject:
        return self._converter

    @Property(QObject, constant=True)
    def reports(self) -> QObject:
        return self._reports

    @Property(QObject, constant=True)
    def teleprompter(self) -> QObject:
        return self._teleprompter

    @Property(QObject, constant=True)
    def reaper(self) -> QObject:
        return self._reaper

    @Property(QObject, constant=True)
    def video(self) -> QObject:
        return self._video

    @Property(QObject, constant=True)
    def montage(self) -> QObject:
        return self._montage

    @Property(QObject, constant=True)
    def projectFiles(self) -> QObject:
        return self._project_files

    def refresh(self) -> None:
        self._project.refresh_models()
        self._casting.refresh()
        self._actor_library.refresh()
        self._roles.refresh()
        self._settings.refresh()
        self._docx_import.changed.emit()
        self._subtitle_import.changed.emit()
        self._montage.refresh()
        self._video.refresh_if_active()
        self._project_files.refresh()
        self._teleprompter.refresh_if_active()
        self._reports.refresh()

    def _clear_auxiliary_models(self) -> None:
        self._teleprompter.reset()
        self._docx_import.reset()
        self._subtitle_import.reset()
        self._reports.reset()
        self._montage.reset()
        self._video.reset()
        self._reaper.reset()

    @Slot(str, str)
    def _open_search_result(self, episode: str, character: str) -> None:
        self._casting.resetFilters()
        self._project.selectEpisode(episode)
        self._casting.selectCharacter(character)

    @Slot(str)
    def _on_feature_project_data_changed(self, domain: str) -> None:
        if domain not in {
            "working_text",
            "project_files",
            "actors",
            "assignments",
            "settings",
        }:
            return
        if domain == "settings":
            self._project.nameChanged.emit()
        self.refresh()
        if domain == "settings":
            self._teleprompter.notify_config_changed()
            self._montage.notify_project_changed()

    @Slot()
    def _on_project_reset_requested(self) -> None:
        self._actor_library.syncProjectActorsWithGlobalBase()
        self._casting.reset()
        self._clear_auxiliary_models()

    @Slot()
    def _on_project_refresh_requested(self) -> None:
        self.refresh()
        self._teleprompter.notify_config_changed()
        self._montage.notify_project_changed()

    @Slot(str)
    def _set_status(self, text: str) -> None:
        if text == self._status_text:
            return
        self._status_text = text
        self.statusTextChanged.emit()

    @Slot(str)
    def _show_error(self, text: str) -> None:
        self._set_status(text)
        self.errorOccurred.emit(text)
