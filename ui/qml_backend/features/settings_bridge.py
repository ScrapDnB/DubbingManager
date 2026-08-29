"""QML backend for project and global settings."""

from copy import deepcopy
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QObject, Property, Signal, Slot, Qt

from config.constants import (
    DEFAULT_ASS_IMPORT_CONFIG,
    DEFAULT_BACKUP_CONFIG,
    DEFAULT_DOCX_IMPORT_CONFIG,
    DEFAULT_EXPORT_CONFIG,
    DEFAULT_GLOBAL_MERGE_CONFIG,
    DEFAULT_PROMPTER_CONFIG,
    DEFAULT_SRT_IMPORT_CONFIG,
    PROMPTER_FONT_KEYS,
    PROMPTER_LAYOUT_TYPES,
)
from core.export_config_profiles import (
    hydrate_layout_profile,
    sync_active_layout_profile,
)
from core.commands import UpdateProjectFileStateCommand
from services.project_fps_service import (
    fps_source_label,
    project_fps,
    set_project_fps,
)
from ui.qml_backend.models import DictListModel
from ui.qml_backend.project_session import ProjectSession
from utils.i18n import SUPPORTED_LANGUAGES


class SettingsBridge(QObject):
    """Expose staged settings workflows without coupling QML to storage."""

    changed = Signal()
    projectDataChanged = Signal(str)
    statusRequested = Signal(str)
    errorRequested = Signal(str)
    backupConfigChanged = Signal(dict)
    globalMontageConfigChanged = Signal()
    globalPrompterConfigChanged = Signal()

    def __init__(
        self,
        session: ProjectSession,
        episode_service,
        script_text_service,
        global_settings_service,
        global_settings: dict,
        parent: Optional[QObject] = None,
    ) -> None:
        super().__init__(parent)
        self._session = session
        self._episode_service = episode_service
        self._script_text_service = script_text_service
        self._global_settings_service = global_settings_service
        self._global_settings = global_settings
        self._languages_model = DictListModel({
            "id": Qt.UserRole + 1,
            "name": Qt.UserRole + 2,
        }, self)
        self._languages_model.set_rows([
            {"id": code, "name": name}
            for code, name in SUPPORTED_LANGUAGES.items()
        ])
        self._session.projectReplaced.connect(self.refresh)

    @Property(QObject, constant=True)
    def languagesModel(self) -> QObject:
        return self._languages_model

    @Property(str, notify=changed)
    def projectName(self) -> str:
        return str(self._session.data.get("project_name") or "Новый проект")

    @Property(str, notify=changed)
    def projectAuthor(self) -> str:
        return str(self._session.data.get("metadata", {}).get("created_by", ""))

    @Property(str, notify=changed)
    def projectStudio(self) -> str:
        return str(self._session.data.get("metadata", {}).get("studio", ""))

    @Property(str, notify=changed)
    def projectKindLabel(self) -> str:
        if self._session.data.get("project_kind") == "audiobook":
            return "Аудиокнига / аудиосериал"
        return "Субтитры / видео"

    @Property(str, notify=changed)
    def projectPath(self) -> str:
        return self._session.project_service.current_project_path or "Не сохранён"

    @Property(str, notify=changed)
    def projectFolder(self) -> str:
        return str(self._session.data.get("project_folder") or "Не задана")

    @Property(int, notify=changed)
    def episodeCount(self) -> int:
        return len(self._session.data.get("episodes", {}))

    @Property(bool, notify=changed)
    def dynamicTextStorage(self) -> bool:
        return self._script_text_service.uses_dynamic_storage(self._session.data)

    @Property(int, notify=changed)
    def workingTextCount(self) -> int:
        if self._session.data.get("project_kind") == "audiobook":
            return len(
                self._session.data.get("audiobook_document", {}).get(
                    "chapters", []
                )
            )
        if self._script_text_service.uses_dynamic_storage(self._session.data):
            return len(
                self._session.data.get("script_storage", {}).get("episodes", {})
            )
        return len(self._session.data.get("episode_working_texts", {}))

    @Property(bool, notify=changed)
    def mergeEnabled(self) -> bool:
        return bool(self._active_merge_config().get("merge", True))

    @Property(float, notify=changed)
    def mergeFps(self) -> float:
        return project_fps(self._session.data)

    @Property(float, notify=changed)
    def mergeGapSeconds(self) -> float:
        return float(
            self._active_merge_config().get("merge_gap_seconds", 4.8)
        )

    @Property(float, notify=changed)
    def projectFps(self) -> float:
        return project_fps(self._session.data)

    @Property(str, notify=changed)
    def projectFpsDisplay(self) -> str:
        return f"{project_fps(self._session.data):.3f}".rstrip("0").rstrip(".")

    @Property(str, notify=changed)
    def projectFpsSource(self) -> str:
        return fps_source_label(self._session.data)

    @Property(float, notify=changed)
    def shortPause(self) -> float:
        return float(self._active_merge_config().get("p_short", 0.5))

    @Property(float, notify=changed)
    def longPause(self) -> float:
        return float(self._active_merge_config().get("p_long", 2.0))

    @Property(str, notify=changed)
    def globalLanguage(self) -> str:
        return self._global_settings_service.get_language()

    @Property(str, notify=changed)
    def audiobookKeywords(self) -> str:
        config = self._global_settings_service.get_audiobook_config()
        return "\n".join(config.get("chapter_keywords", []))

    @Property("QVariantMap", notify=changed)
    def projectMontageConfig(self) -> dict:
        return self.globalMontageConfig

    @Property("QVariantMap", notify=changed)
    def globalMontageConfig(self) -> dict:
        return self._export_config(
            self._global_settings_service.get_default_export_config()
        )

    @Property("QVariantMap", notify=changed)
    def projectPrompterConfig(self) -> dict:
        return self.globalPrompterConfig

    @Property("QVariantMap", notify=changed)
    def globalPrompterConfig(self) -> dict:
        return self._prompter_config(
            self._global_settings_service.get_default_prompter_config()
        )

    @Property("QVariantMap", notify=changed)
    def globalMergeConfig(self) -> dict:
        return self._merge_config(
            self._global_settings_service.get_replica_merge_config()
        )

    @Property("QVariantMap", notify=changed)
    def activeMergeConfig(self) -> dict:
        return self._active_merge_config()

    @Property("QVariantMap", notify=changed)
    def globalAssImportConfig(self) -> dict:
        return self._ass_import_config(
            self._global_settings_service.get_ass_import_config()
        )

    @Property("QVariantMap", notify=changed)
    def globalSrtImportConfig(self) -> dict:
        return self._srt_import_config(
            self._global_settings_service.get_srt_import_config()
        )

    @Property("QVariantMap", notify=changed)
    def globalDocxImportConfig(self) -> dict:
        return self._docx_import_config(
            self._global_settings_service.get_docx_import_config()
        )

    @Property("QVariantList", notify=changed)
    def globalDocxImportPresets(self) -> list[dict]:
        return deepcopy(
            self._global_settings_service.get_docx_import_presets()
        )

    @Property("QVariantMap", notify=changed)
    def globalBackupConfig(self) -> dict:
        return self._backup_config(
            self._global_settings_service.get_backup_config()
        )

    @Slot(str, str, str, result=bool)
    def applyProjectSettingsFull(
        self,
        name: str,
        author: str,
        studio: str,
    ) -> bool:
        return self._apply_project_settings(name, author, studio, None)

    @Slot(str, str, str, float, result=bool)
    def applyProjectSettingsWithFps(
        self,
        name: str,
        author: str,
        studio: str,
        fps: float,
    ) -> bool:
        return self._apply_project_settings(name, author, studio, fps)

    def _apply_project_settings(
        self,
        name: str,
        author: str,
        studio: str,
        fps,
    ) -> bool:
        metadata = deepcopy(self._session.data.get("metadata", {}))
        metadata.update({
            "created_by": (author or "").strip(),
            "studio": (studio or "").strip(),
        })
        updates = {"project_name": (name or "").strip(), "metadata": metadata}
        if fps is not None:
            try:
                normalized_fps = float(fps)
            except (TypeError, ValueError):
                normalized_fps = 0.0
            if not 1.0 <= normalized_fps <= 120.0:
                self.errorRequested.emit("FPS должен быть в диапазоне от 1 до 120")
                return False
            if abs(normalized_fps - project_fps(self._session.data)) > 0.000001:
                candidate_settings = deepcopy(
                    self._session.data.get("project_settings", {})
                )
                temp_data = {"project_settings": candidate_settings}
                set_project_fps(temp_data, normalized_fps)
                updates["project_settings"] = temp_data["project_settings"]
        if not updates["project_name"]:
            self.errorRequested.emit("Введите название проекта")
            return False
        if all(self._session.data.get(key) == value for key, value in updates.items()):
            return True
        self._session.execute(UpdateProjectFileStateCommand(
            self._session.data, updates, "Изменены настройки проекта",
        ), "settings")
        self.changed.emit()
        self.projectDataChanged.emit(
            "working_text" if "project_settings" in updates else "settings"
        )
        return True

    @Slot(str, str, result=bool)
    def applyGlobalSettings(self, language: str, keywords_text: str) -> bool:
        return self._apply_global_bundle(
            language,
            keywords_text,
            self.globalMontageConfig,
            self.globalPrompterConfig,
        )

    @Slot(str, str, "QVariantMap", "QVariantMap", result=bool)
    def applyGlobalSettingsBundle(
        self,
        language: str,
        keywords_text: str,
        montage_config: dict,
        prompter_config: dict,
    ) -> bool:
        return self._apply_global_bundle(
            language, keywords_text, montage_config, prompter_config
        )

    @Slot(
        str, str, "QVariantMap", "QVariantMap", "QVariantMap",
        "QVariantMap", "QVariantMap", "QVariantMap", result=bool,
    )
    def applyGlobalSettingsFull(
        self,
        language: str,
        keywords_text: str,
        montage_config: dict,
        prompter_config: dict,
        merge_config: dict,
        ass_config: dict,
        srt_config: dict,
        docx_config: dict,
    ) -> bool:
        return self._apply_global_bundle(
            language,
            keywords_text,
            montage_config,
            prompter_config,
            merge_config,
            ass_config,
            srt_config,
            docx_config,
        )

    @Slot(
        str, str, "QVariantMap", "QVariantMap", "QVariantMap",
        "QVariantMap", "QVariantMap", "QVariantMap", "QVariantMap",
        result=bool,
    )
    def applyGlobalSettingsComplete(
        self,
        language: str,
        keywords_text: str,
        montage_config: dict,
        prompter_config: dict,
        merge_config: dict,
        ass_config: dict,
        srt_config: dict,
        docx_config: dict,
        backup_config: dict,
    ) -> bool:
        return self._apply_global_bundle(
            language,
            keywords_text,
            montage_config,
            prompter_config,
            merge_config,
            ass_config,
            srt_config,
            docx_config,
            backup_config,
        )

    def _apply_global_bundle(
        self,
        language: str,
        keywords_text: str,
        montage_config: dict,
        prompter_config: dict,
        merge_config=None,
        ass_config=None,
        srt_config=None,
        docx_config=None,
        backup_config=None,
    ) -> bool:
        # The beta intentionally exposes Russian only until the English copy has
        # received a full QML-specific editorial pass.
        language = "ru"
        keywords = self._parse_keywords(keywords_text)
        normalized_backup = self._backup_config(
            backup_config
            if backup_config is not None
            else self.globalBackupConfig
        )
        backup_directory = Path(normalized_backup["directory"]).expanduser()
        if (
            normalized_backup["enabled"]
            and
            normalized_backup["path_mode"] == "relative"
            and backup_directory.is_absolute()
        ):
            self.errorRequested.emit(
                "Для относительного режима укажите путь от папки проекта"
            )
            return False
        if (
            normalized_backup["enabled"]
            and
            normalized_backup["path_mode"] == "absolute"
            and not backup_directory.is_absolute()
        ):
            self.errorRequested.emit(
                "Для абсолютного режима выберите полную папку"
            )
            return False
        updated = deepcopy(self._global_settings)
        updated["language"] = language
        updated["audiobook_config"] = {"chapter_keywords": keywords}
        updated["default_export_config"] = self._export_config(montage_config)
        updated["default_prompter_config"] = (
            self._prompter_config_preserving_scroll_mode(prompter_config)
        )
        updated["default_replica_merge_config"] = self._merge_config(
            merge_config if merge_config is not None else self.globalMergeConfig
        )
        updated["ass_import_config"] = self._ass_import_config(
            ass_config if ass_config is not None else self.globalAssImportConfig
        )
        updated["srt_import_config"] = self._srt_import_config(
            srt_config if srt_config is not None else self.globalSrtImportConfig
        )
        updated["docx_import_config"] = self._docx_import_config(
            docx_config if docx_config is not None else self.globalDocxImportConfig
        )
        updated["backup_config"] = normalized_backup
        old_language = self.globalLanguage
        if not self._global_settings_service.save_settings(updated):
            self.errorRequested.emit("Не удалось сохранить глобальные настройки")
            return False

        self._global_settings.clear()
        self._global_settings.update(self._global_settings_service.get_settings())
        self.backupConfigChanged.emit(self.globalBackupConfig)
        self.globalMontageConfigChanged.emit()
        self._script_text_service.set_global_merge_config(
            self._global_settings_service.get_replica_merge_config()
        )
        self._episode_service.set_merge_gap_from_config(
            self._script_text_service.get_merge_config(self._session.data)
        )
        if self._script_text_service.uses_dynamic_storage(self._session.data):
            self.projectDataChanged.emit("working_text")
        self._episode_service.set_import_configs(
            self._global_settings_service.get_ass_import_config(),
            self._global_settings_service.get_srt_import_config(),
        )
        self.globalPrompterConfigChanged.emit()
        self.changed.emit()
        message = "Глобальные настройки сохранены"
        if language != old_language:
            message += ". Язык изменится после перезапуска"
        self.statusRequested.emit(message)
        return True

    @Slot(str, result=bool)
    def saveProjectConfigAsDefault(self, kind: str) -> bool:
        config = (
            self.projectMontageConfig
            if kind == "montage"
            else self.projectPrompterConfig
        )
        return self.saveConfigAsDefault(kind, config)

    @Slot(str, "QVariantMap", result=bool)
    def saveConfigAsDefault(self, kind: str, config: dict) -> bool:
        if kind == "montage":
            self._global_settings_service.set_default_export_config(
                self._export_config(config)
            )
        elif kind == "prompter":
            self._global_settings_service.set_default_prompter_config(
                self._prompter_config_preserving_scroll_mode(config)
            )
        else:
            return False
        if not self._save_global_service_state():
            return False
        if kind == "prompter":
            self.globalPrompterConfigChanged.emit()
        elif kind == "montage":
            self.globalMontageConfigChanged.emit()
        self.changed.emit()
        self.statusRequested.emit("Глобальные настройки сохранены")
        return True

    @Slot(
        "QVariantMap", "QVariantMap", "QVariantMap", "QVariantMap",
        result=bool,
    )
    def saveImportConfigAsDefault(
        self,
        merge_config: dict,
        ass_config: dict,
        srt_config: dict,
        docx_config: dict,
    ) -> bool:
        updated = deepcopy(self._global_settings)
        updated.update({
            "default_replica_merge_config": self._merge_config(merge_config),
            "ass_import_config": self._ass_import_config(ass_config),
            "srt_import_config": self._srt_import_config(srt_config),
            "docx_import_config": self._docx_import_config(docx_config),
        })
        if not self._global_settings_service.save_settings(updated):
            self.errorRequested.emit("Не удалось сохранить глобальные настройки")
            return False
        self._global_settings.clear()
        self._global_settings.update(self._global_settings_service.get_settings())
        self._script_text_service.set_global_merge_config(
            self._global_settings_service.get_replica_merge_config()
        )
        self._episode_service.set_merge_gap_from_config(
            self._script_text_service.get_merge_config(self._session.data)
        )
        self._episode_service.set_import_configs(
            self._global_settings_service.get_ass_import_config(),
            self._global_settings_service.get_srt_import_config(),
        )
        if self._script_text_service.uses_dynamic_storage(self._session.data):
            self.projectDataChanged.emit("working_text")
        self.changed.emit()
        self.statusRequested.emit(
            "Настройки объединения и разбора исходников сохранены по умолчанию"
        )
        return True

    @Slot(str, bool, result=bool)
    def setPrompterSyncEnabled(self, key: str, enabled: bool) -> bool:
        if key not in {"sync_in", "sync_out", "sync_play_only"}:
            return False
        return self._set_global_prompter_flag(
            key,
            enabled,
            "Настройки синхронизации REAPER сохранены",
        )

    @Slot(bool, result=bool)
    def setPrompterPageScrollMode(self, enabled: bool) -> bool:
        return self.setPrompterScrollMode(
            "page" if enabled else "normal"
        )

    @Slot(str, result=bool)
    def setPrompterScrollMode(self, mode: str) -> bool:
        """Persist one of the mutually exclusive teleprompter scroll modes."""
        mode = str(mode or "").strip().lower()
        if mode not in {"normal", "smooth", "page"}:
            return False
        config = self.globalPrompterConfig
        page_enabled = mode == "page"
        smooth_enabled = mode == "smooth"
        if (
            bool(config.get("page_scroll_mode")) == page_enabled
            and bool(config.get("smooth_scroll_mode")) == smooth_enabled
        ):
            return True
        config["page_scroll_mode"] = page_enabled
        config["smooth_scroll_mode"] = smooth_enabled
        updated = deepcopy(self._global_settings)
        updated["default_prompter_config"] = self._prompter_config(config)
        if not self._global_settings_service.save_settings(updated):
            self.errorRequested.emit(
                "Не удалось сохранить режим прокрутки телесуфлёра"
            )
            return False
        self._global_settings.clear()
        self._global_settings.update(
            self._global_settings_service.get_settings()
        )
        self.globalPrompterConfigChanged.emit()
        self.changed.emit()
        self.statusRequested.emit("Режим прокрутки телесуфлёра сохранён")
        return True

    def _set_global_prompter_flag(
        self,
        key: str,
        enabled: bool,
        status_message: str,
    ) -> bool:
        config = self.globalPrompterConfig
        enabled = bool(enabled)
        if config.get(key) == enabled:
            return True
        config[key] = enabled
        updated = deepcopy(self._global_settings)
        updated["default_prompter_config"] = self._prompter_config(config)
        if not self._global_settings_service.save_settings(updated):
            self.errorRequested.emit(
                "Не удалось сохранить настройки синхронизации REAPER"
            )
            return False
        self._global_settings.clear()
        self._global_settings.update(
            self._global_settings_service.get_settings()
        )
        self.globalPrompterConfigChanged.emit()
        self.changed.emit()
        self.statusRequested.emit(status_message)
        return True

    @Slot(str, "QVariantMap", result=bool)
    def saveDocxImportPreset(self, name: str, config: dict) -> bool:
        name = " ".join(str(name or "").split())
        if not name:
            self.errorRequested.emit("Введите название пресета DOCX")
            return False
        presets = self.globalDocxImportPresets
        replacement = {
            "name": name,
            "config": self._docx_import_config(config),
        }
        for index, preset in enumerate(presets):
            if str(preset.get("name", "")).casefold() == name.casefold():
                presets[index] = replacement
                break
        else:
            presets.append(replacement)
        return self._save_docx_import_presets(presets, f"Пресет «{name}» сохранён")

    @Slot(str, result=bool)
    def deleteDocxImportPreset(self, name: str) -> bool:
        folded = str(name or "").casefold()
        presets = [
            preset for preset in self.globalDocxImportPresets
            if str(preset.get("name", "")).casefold() != folded
        ]
        return self._save_docx_import_presets(
            presets, f"Пресет «{name}» удалён"
        )

    @Slot()
    def refresh(self) -> None:
        self.changed.emit()

    def _merge_config(self, value=None) -> dict:
        config = deepcopy(DEFAULT_GLOBAL_MERGE_CONFIG)
        stored = (self._global_settings_service.get_replica_merge_config()
                  if value is None else value)
        if isinstance(stored, dict):
            config.update(stored)
            if "merge_gap_seconds" not in stored and "merge_gap" in stored:
                try:
                    config["merge_gap_seconds"] = float(
                        stored["merge_gap"]
                    ) / max(0.001, float(stored.get("fps", 25.0)))
                except (TypeError, ValueError):
                    pass
        config.pop("fps", None)
        config.pop("merge_gap", None)
        config["merge"] = bool(config.get("merge", True))
        config["merge_parallel_replicas"] = bool(
            config.get("merge_parallel_replicas", False)
        )
        config["respect_existing_separators"] = bool(
            config.get("respect_existing_separators", False)
        )
        config["inline_timecodes_enabled"] = bool(
            config.get("inline_timecodes_enabled", False)
        )
        bracket_style = str(config.get(
            "inline_timecode_brackets", "square"
        ))
        config["inline_timecode_brackets"] = (
            bracket_style
            if bracket_style in {"square", "round", "curly"}
            else "square"
        )
        for key, low, high in (
            ("merge_gap_seconds", 0.0, 480.0),
            ("p_short", 0.0, 5.0),
            ("p_long", 0.0, 10.0),
            ("inline_timecode_min_duration", 0.0, 86400.0),
        ):
            try:
                config[key] = max(low, min(high, float(config[key])))
            except (KeyError, TypeError, ValueError):
                config[key] = float(DEFAULT_GLOBAL_MERGE_CONFIG[key])
        try:
            config["inline_timecode_every"] = max(1, min(
                1000,
                int(config.get("inline_timecode_every", 3)),
            ))
        except (TypeError, ValueError):
            config["inline_timecode_every"] = int(
                DEFAULT_GLOBAL_MERGE_CONFIG["inline_timecode_every"]
            )
        return config

    def _active_merge_config(self) -> dict:
        return self._merge_config()

    @staticmethod
    def _ass_import_config(value) -> dict:
        config = deepcopy(DEFAULT_ASS_IMPORT_CONFIG)
        if isinstance(value, dict):
            config.update(deepcopy(value))
        config["split_character_names"] = bool(config["split_character_names"])
        config["strip_override_tags"] = bool(config["strip_override_tags"])
        config["character_separator"] = str(config["character_separator"] or ";")
        return config

    @staticmethod
    def _srt_import_config(value) -> dict:
        config = deepcopy(DEFAULT_SRT_IMPORT_CONFIG)
        if isinstance(value, dict):
            config.update(deepcopy(value))
        config["detect_character_prefix"] = bool(config["detect_character_prefix"])
        config["keep_multiline"] = bool(config["keep_multiline"])
        config["character_separator"] = str(config["character_separator"] or ":")
        config["default_character"] = str(config["default_character"] or "").strip()
        return config

    @staticmethod
    def _docx_import_config(value) -> dict:
        config = deepcopy(DEFAULT_DOCX_IMPORT_CONFIG)
        if not isinstance(value, dict):
            return config
        for key, item in deepcopy(value).items():
            if key == "aliases" and isinstance(item, dict):
                config["aliases"].update(item)
            elif key in {"mapping", "fallback_mapping"} and isinstance(item, dict):
                config[key].update(item)
            else:
                config[key] = item
        return config

    @staticmethod
    def _backup_config(value) -> dict:
        config = deepcopy(DEFAULT_BACKUP_CONFIG)
        if isinstance(value, dict):
            config.update(deepcopy(value))
        config["enabled"] = bool(config.get("enabled", True))
        mode = str(config.get("path_mode", "relative") or "relative")
        config["path_mode"] = (
            mode if mode in {"relative", "absolute"} else "relative"
        )
        config["directory"] = str(
            config.get("directory", ".backups") or ".backups"
        ).strip()
        for key, low, high, fallback in (
            ("interval_minutes", 1, 1440, 5),
            ("max_backups", 1, 100, 10),
        ):
            try:
                config[key] = max(
                    low,
                    min(high, int(config.get(key, fallback))),
                )
            except (TypeError, ValueError):
                config[key] = fallback
        return config

    @staticmethod
    def _export_config(value) -> dict:
        config = deepcopy(DEFAULT_EXPORT_CONFIG)
        if isinstance(value, dict):
            config.update(deepcopy(value))
            if value and "layout_profiles" not in value:
                config["layout_profiles"] = {}
        if config.get("layout_type") == "Сценарий":
            config["layout_type"] = "Сценарий 1"
        return hydrate_layout_profile(sync_active_layout_profile(config))

    @staticmethod
    def _prompter_config(value, base=None) -> dict:
        config = deepcopy(base or DEFAULT_PROMPTER_CONFIG)
        source = value if isinstance(value, dict) else {}
        colors = deepcopy(config.get("colors", {}))
        config.update({
            key: deepcopy(item)
            for key, item in source.items()
            if key != "colors"
        })
        if isinstance(source.get("colors"), dict):
            colors.update(source["colors"])
        config["colors"] = colors
        layout_type = str(config.get("layout_type", "Сценарий 1"))
        if layout_type not in PROMPTER_LAYOUT_TYPES:
            layout_type = "Сценарий 1"
        profiles = deepcopy(config.get("layout_font_sizes", {}))
        profile = deepcopy(profiles.get(
            layout_type,
            DEFAULT_PROMPTER_CONFIG["layout_font_sizes"][layout_type],
        ))
        for key in PROMPTER_FONT_KEYS:
            if key in source:
                profile[key] = source[key]
        profiles[layout_type] = profile
        config["layout_type"] = layout_type
        config["layout_font_sizes"] = profiles
        return config

    def _prompter_config_preserving_scroll_mode(self, value) -> dict:
        """Keep the live teleprompter's mode out of staged settings drafts."""
        config = self._prompter_config(value)
        current = self._global_settings_service.get_default_prompter_config()
        config["page_scroll_mode"] = bool(
            current.get("page_scroll_mode", False)
        )
        config["smooth_scroll_mode"] = bool(
            current.get("smooth_scroll_mode", False)
        )
        return config

    def _save_global_service_state(self) -> bool:
        updated = deepcopy(self._global_settings)
        updated["default_export_config"] = (
            self._global_settings_service.get_default_export_config()
        )
        updated["default_prompter_config"] = (
            self._global_settings_service.get_default_prompter_config()
        )
        if not self._global_settings_service.save_settings(updated):
            self.errorRequested.emit("Не удалось сохранить глобальные настройки")
            return False
        self._global_settings.clear()
        self._global_settings.update(self._global_settings_service.get_settings())
        return True

    def _save_docx_import_presets(self, presets: list, message: str) -> bool:
        updated = deepcopy(self._global_settings)
        updated["docx_import_presets"] = presets
        if not self._global_settings_service.save_settings(updated):
            self.errorRequested.emit("Не удалось сохранить пресеты DOCX")
            return False
        self._global_settings.clear()
        self._global_settings.update(self._global_settings_service.get_settings())
        self.changed.emit()
        self.statusRequested.emit(message)
        return True

    @staticmethod
    def _parse_keywords(text: str) -> list[str]:
        result = []
        seen = set()
        for line in str(text or "").replace(",", "\n").splitlines():
            value = " ".join(line.split())
            folded = value.casefold()
            if value and folded not in seen:
                result.append(value)
                seen.add(folded)
        return result
