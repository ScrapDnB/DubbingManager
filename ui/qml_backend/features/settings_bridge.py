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
    DEFAULT_PROMPTER_CONFIG,
    DEFAULT_REPLICA_MERGE_CONFIG,
    DEFAULT_SRT_IMPORT_CONFIG,
)
from core.commands import UpdateProjectFileStateCommand
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
    globalPrompterConfigChanged = Signal()

    def __init__(
        self,
        session: ProjectSession,
        episode_service,
        global_settings_service,
        global_settings: dict,
        parent: Optional[QObject] = None,
    ) -> None:
        super().__init__(parent)
        self._session = session
        self._episode_service = episode_service
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

    @Property(int, notify=changed)
    def workingTextCount(self) -> int:
        return len(self._session.data.get("episode_working_texts", {}))

    @Property(bool, notify=changed)
    def mergeEnabled(self) -> bool:
        return bool(self._merge_config().get("merge", True))

    @Property(float, notify=changed)
    def mergeFps(self) -> float:
        return float(self._merge_config().get("fps", 25.0) or 25.0)

    @Property(float, notify=changed)
    def mergeGapSeconds(self) -> float:
        config = self._merge_config()
        fps = float(config.get("fps", 25.0) or 25.0)
        return float(config.get("merge_gap", 120)) / fps

    @Property(float, notify=changed)
    def shortPause(self) -> float:
        return float(self._merge_config().get("p_short", 0.5))

    @Property(float, notify=changed)
    def longPause(self) -> float:
        return float(self._merge_config().get("p_long", 2.0))

    @Property(str, notify=changed)
    def globalLanguage(self) -> str:
        return self._global_settings_service.get_language()

    @Property(str, notify=changed)
    def audiobookKeywords(self) -> str:
        config = self._global_settings_service.get_audiobook_config()
        return "\n".join(config.get("chapter_keywords", []))

    @Property("QVariantMap", notify=changed)
    def projectMontageConfig(self) -> dict:
        return self._export_config(self._session.data.get("export_config"))

    @Property("QVariantMap", notify=changed)
    def globalMontageConfig(self) -> dict:
        return self._export_config(
            self._global_settings_service.get_default_export_config()
        )

    @Property("QVariantMap", notify=changed)
    def projectPrompterConfig(self) -> dict:
        config = self._prompter_config(
            self._global_settings_service.get_default_prompter_config()
        )
        return self._prompter_config(
            self._session.data.get("prompter_config"), config
        )

    @Property("QVariantMap", notify=changed)
    def globalPrompterConfig(self) -> dict:
        return self._prompter_config(
            self._global_settings_service.get_default_prompter_config()
        )

    @Property("QVariantMap", notify=changed)
    def projectMergeConfig(self) -> dict:
        return self._merge_config()

    @Property("QVariantMap", notify=changed)
    def projectAssImportConfig(self) -> dict:
        return self._ass_import_config(
            self._session.data.get("ass_import_config")
        )

    @Property("QVariantMap", notify=changed)
    def projectSrtImportConfig(self) -> dict:
        return self._srt_import_config(
            self._session.data.get("srt_import_config")
        )

    @Property("QVariantMap", notify=changed)
    def projectDocxImportConfig(self) -> dict:
        return self._docx_import_config(
            self._session.data.get("docx_import_config")
        )

    @Property("QVariantMap", notify=changed)
    def globalMergeConfig(self) -> dict:
        return self._merge_config(
            self._global_settings_service.get_replica_merge_config()
        )

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

    @Slot(str, str, str, bool, float, float, float, float, result=bool)
    def applyProjectSettings(
        self,
        name: str,
        author: str,
        studio: str,
        merge_enabled: bool,
        fps: float,
        gap_seconds: float,
        short_pause: float,
        long_pause: float,
    ) -> bool:
        return self._apply_project_bundle(
            name, author, studio, merge_enabled, fps, gap_seconds,
            short_pause, long_pause, self.projectMontageConfig,
            self.projectPrompterConfig,
        )

    @Slot(
        str, str, str, bool, float, float, float, float,
        "QVariantMap", "QVariantMap", result=bool,
    )
    def applyProjectSettingsBundle(
        self,
        name: str,
        author: str,
        studio: str,
        merge_enabled: bool,
        fps: float,
        gap_seconds: float,
        short_pause: float,
        long_pause: float,
        montage_config: dict,
        prompter_config: dict,
    ) -> bool:
        return self._apply_project_bundle(
            name, author, studio, merge_enabled, fps, gap_seconds,
            short_pause, long_pause, montage_config, prompter_config,
        )

    @Slot(
        str, str, str, "QVariantMap", "QVariantMap", "QVariantMap",
        "QVariantMap", "QVariantMap", "QVariantMap", result=bool,
    )
    def applyProjectSettingsFull(
        self,
        name: str,
        author: str,
        studio: str,
        montage_config: dict,
        prompter_config: dict,
        merge_config: dict,
        ass_config: dict,
        srt_config: dict,
        docx_config: dict,
    ) -> bool:
        normalized_merge = self._merge_config(merge_config)
        fps = float(normalized_merge["fps"])
        return self._apply_project_bundle(
            name,
            author,
            studio,
            bool(normalized_merge["merge"]),
            fps,
            float(normalized_merge["merge_gap"]) / fps,
            float(normalized_merge["p_short"]),
            float(normalized_merge["p_long"]),
            montage_config,
            prompter_config,
            ass_config,
            srt_config,
            docx_config,
        )

    def _apply_project_bundle(
        self,
        name: str,
        author: str,
        studio: str,
        merge_enabled: bool,
        fps: float,
        gap_seconds: float,
        short_pause: float,
        long_pause: float,
        montage_config: dict,
        prompter_config: dict,
        ass_config=None,
        srt_config=None,
        docx_config=None,
    ) -> bool:
        name = (name or "").strip()
        if not name:
            self.errorRequested.emit("Введите название проекта")
            return False
        if not 1.0 <= fps <= 120.0:
            self.errorRequested.emit("FPS должен быть от 1 до 120")
            return False
        if not 0.0 <= gap_seconds <= 10.0:
            self.errorRequested.emit("Порог слияния должен быть от 0 до 10 секунд")
            return False
        if not 0.0 <= short_pause <= 5.0 or not 0.0 <= long_pause <= 10.0:
            self.errorRequested.emit("Проверьте длительность короткой и длинной паузы")
            return False

        metadata = deepcopy(self._session.data.get("metadata", {}))
        metadata.update({
            "created_by": (author or "").strip(),
            "studio": (studio or "").strip(),
        })
        merge_config = self._merge_config()
        merge_config.update({
            "merge": bool(merge_enabled),
            "fps": float(fps),
            "merge_gap": int(round(float(gap_seconds) * float(fps))),
            "p_short": float(short_pause),
            "p_long": float(long_pause),
        })
        updates = {
            "project_name": name,
            "metadata": metadata,
            "replica_merge_config": merge_config,
            "export_config": self._export_config(montage_config),
            "prompter_config": self._prompter_config(prompter_config),
            "ass_import_config": self._ass_import_config(
                ass_config if ass_config is not None else self.projectAssImportConfig
            ),
            "srt_import_config": self._srt_import_config(
                srt_config if srt_config is not None else self.projectSrtImportConfig
            ),
            "docx_import_config": self._docx_import_config(
                docx_config if docx_config is not None else self.projectDocxImportConfig
            ),
        }
        current = {key: self._session.data.get(key) for key in updates}
        if current == updates:
            return True

        self._session.execute(UpdateProjectFileStateCommand(
            self._session.data,
            updates,
            "Изменены настройки проекта",
        ), "settings")
        self._episode_service.set_merge_gap_from_config(merge_config)
        for episode in self._session.data.get("episodes", {}):
            self._episode_service.invalidate_episode(str(episode))
        self.changed.emit()
        self.projectDataChanged.emit("settings")
        self.statusRequested.emit("Настройки проекта сохранены")
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
        updated["default_prompter_config"] = self._prompter_config(
            prompter_config
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
                self._prompter_config(config)
            )
        else:
            return False
        if not self._save_global_service_state():
            return False
        if kind == "prompter":
            self.globalPrompterConfigChanged.emit()
        self.changed.emit()
        self.statusRequested.emit("Настройки проекта сохранены по умолчанию")
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
        self.changed.emit()
        self.statusRequested.emit("Настройки импорта сохранены по умолчанию")
        return True

    @Slot(
        "QVariantMap", "QVariantMap", "QVariantMap", "QVariantMap",
        result=bool,
    )
    def applyImportConfigToProject(
        self,
        merge_config: dict,
        ass_config: dict,
        srt_config: dict,
        docx_config: dict,
    ) -> bool:
        updates = {
            "replica_merge_config": self._merge_config(merge_config),
            "ass_import_config": self._ass_import_config(ass_config),
            "srt_import_config": self._srt_import_config(srt_config),
            "docx_import_config": self._docx_import_config(docx_config),
        }
        current = {key: self._session.data.get(key) for key in updates}
        if current == updates:
            return True
        self._session.execute(UpdateProjectFileStateCommand(
            self._session.data,
            updates,
            "Применены глобальные настройки импорта",
        ), "settings")
        self._episode_service.set_merge_gap_from_config(
            updates["replica_merge_config"]
        )
        self.changed.emit()
        self.projectDataChanged.emit("settings")
        self.statusRequested.emit("Глобальные настройки импорта применены к проекту")
        return True

    @Slot(str, "QVariantMap", result=bool)
    def applyGlobalConfigToProject(self, kind: str, config: dict) -> bool:
        if kind == "montage":
            key, value = "export_config", self._export_config(config)
        elif kind == "prompter":
            key, value = "prompter_config", self._prompter_config(config)
        elif kind == "merge":
            key, value = "replica_merge_config", self._merge_config(config)
        elif kind == "ass":
            key, value = "ass_import_config", self._ass_import_config(config)
        elif kind == "srt":
            key, value = "srt_import_config", self._srt_import_config(config)
        elif kind == "docx":
            key, value = "docx_import_config", self._docx_import_config(config)
        else:
            return False
        if self._session.data.get(key) == value:
            return True
        self._session.execute(UpdateProjectFileStateCommand(
            self._session.data,
            {key: value},
            "Применены глобальные настройки к проекту",
        ), "settings")
        self.changed.emit()
        self.projectDataChanged.emit("settings")
        self.statusRequested.emit("Глобальные настройки применены к проекту")
        return True

    @Slot(str, bool, result=bool)
    def setPrompterSyncEnabled(self, key: str, enabled: bool) -> bool:
        if key not in {"sync_in", "sync_out"}:
            return False
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
        self.statusRequested.emit("Настройки синхронизации REAPER сохранены")
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
        config = deepcopy(DEFAULT_REPLICA_MERGE_CONFIG)
        stored = (
            self._session.data.get("replica_merge_config", {})
            if value is None else value
        )
        if isinstance(stored, dict):
            config.update(stored)
        config["merge"] = bool(config.get("merge", True))
        for key, low, high in (
            ("fps", 1.0, 120.0),
            ("merge_gap", 0.0, 12000.0),
            ("p_short", 0.0, 5.0),
            ("p_long", 0.0, 10.0),
        ):
            try:
                config[key] = max(low, min(high, float(config[key])))
            except (KeyError, TypeError, ValueError):
                config[key] = float(DEFAULT_REPLICA_MERGE_CONFIG[key])
        return config

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
        if config.get("layout_type") == "Сценарий":
            config["layout_type"] = "Сценарий 1"
        return config

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
