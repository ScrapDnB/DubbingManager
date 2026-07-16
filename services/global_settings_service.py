"""Service for global application settings."""

import json
import os
import logging
import shutil
import sys
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

from config.constants import (
    DEFAULT_ASS_IMPORT_CONFIG,
    DEFAULT_AUDIOBOOK_CONFIG,
    DEFAULT_BACKUP_CONFIG,
    DEFAULT_GLOBAL_SETTINGS,
    DEFAULT_DOCX_IMPORT_CONFIG,
    DEFAULT_EXPORT_CONFIG,
    DEFAULT_PROMPTER_CONFIG,
    DEFAULT_REPLICA_MERGE_CONFIG,
    DEFAULT_SRT_IMPORT_CONFIG,
)
from utils.i18n import DEFAULT_LANGUAGE, SUPPORTED_LANGUAGES, translate_source

logger = logging.getLogger(__name__)


def _get_settings_file_path() -> Path:
    """Return settings file path."""
    if sys.platform == 'win32':
        # Windows: C:\Users\username\AppData\Roaming\dubbing_manager\global_settings.json
        appdata = os.environ.get('APPDATA')
        if appdata:
            return Path(appdata) / "dubbing_manager" / "global_settings.json"
        # Fall back to the home directory
        return Path.home() / ".dubbing_manager" / "global_settings.json"
    else:
        # macOS/Linux: ~/.dubbing_manager/global_settings.json
        return Path.home() / ".dubbing_manager" / "global_settings.json"


# Path to the global settings file
SETTINGS_FILE = _get_settings_file_path()
PROJECT_SUMMARY_EXPORT_METRICS = {"rings", "lines", "words"}
DEFAULT_PROJECT_SUMMARY_EXPORT_METRIC = "rings"


class GlobalSettingsService:
    """Global Settings Service implementation."""

    def __init__(self):
        self.settings: Dict[str, Any] = {}
        self._settings_file: Path = SETTINGS_FILE

    def load_settings(self) -> Dict[str, Any]:
        """Load global settings from disk."""
        if not self._settings_file.exists():
            logger.info("Global settings file not found, using defaults")
            return self._get_defaults()

        try:
            with open(self._settings_file, 'r', encoding='utf-8') as f:
                loaded = json.load(f)

            settings = self._get_defaults()

            if 'recent_projects' in loaded:
                settings['recent_projects'] = self._normalize_recent_projects(
                    loaded.get('recent_projects', [])
                )

            if 'global_actor_base' in loaded:
                settings['global_actor_base'] = self._normalize_actor_base(
                    loaded.get('global_actor_base', {})
                )

            if 'default_export_config' in loaded:
                settings['default_export_config'] = self._normalize_export_config(
                    loaded.get('default_export_config', {})
                )

            if 'default_prompter_config' in loaded:
                settings['default_prompter_config'] = (
                    self._normalize_prompter_config(
                        loaded.get('default_prompter_config', {})
                    )
                )

            if 'prompter_color_presets' in loaded:
                settings['prompter_color_presets'] = (
                    self._normalize_prompter_color_presets(
                        loaded.get('prompter_color_presets', [])
                    )
                )

            settings['audiobook_config'] = self._normalize_audiobook_config(
                loaded.get('audiobook_config', DEFAULT_AUDIOBOOK_CONFIG)
            )
            settings['backup_config'] = self._normalize_backup_config(
                loaded.get('backup_config', DEFAULT_BACKUP_CONFIG)
            )

            settings['docx_import_config'] = self._normalize_docx_import_config(
                loaded.get('docx_import_config', DEFAULT_DOCX_IMPORT_CONFIG)
            )
            settings['docx_import_presets'] = (
                self._normalize_docx_import_presets(
                    loaded.get('docx_import_presets', [])
                )
            )
            settings['ass_import_config'] = self._normalize_ass_import_config(
                loaded.get('ass_import_config', DEFAULT_ASS_IMPORT_CONFIG)
            )
            settings['srt_import_config'] = self._normalize_srt_import_config(
                loaded.get('srt_import_config', DEFAULT_SRT_IMPORT_CONFIG)
            )
            settings['default_replica_merge_config'] = (
                self._normalize_replica_merge_config(
                    loaded.get(
                        'default_replica_merge_config',
                        DEFAULT_REPLICA_MERGE_CONFIG,
                    )
                )
            )

            settings['project_summary_export_metric'] = (
                self._normalize_project_summary_export_metric(
                    loaded.get('project_summary_export_metric')
                )
            )

            settings['language'] = self._normalize_language(
                loaded.get('language', DEFAULT_LANGUAGE)
            )

            self.settings = settings
            logger.info(f"Global settings loaded from {self._settings_file}")
            return settings

        except Exception as e:
            logger.error(f"Failed to load global settings: {e}")
            return self._get_defaults()

    def save_settings(self, settings: Dict[str, Any]) -> bool:
        """Save global settings to disk."""
        try:
            # Create the directory if it does not exist
            self._settings_file.parent.mkdir(parents=True, exist_ok=True)
            self._backup_settings_file()

            data_to_save = {
                'recent_projects': self._normalize_recent_projects(
                    settings.get('recent_projects', [])
                ),
                'global_actor_base': self._normalize_actor_base(
                    settings.get('global_actor_base', {})
                ),
                'default_export_config': self._normalize_export_config(
                    settings.get('default_export_config', {})
                ),
                'default_prompter_config': self._normalize_prompter_config(
                    settings.get('default_prompter_config', {})
                ),
                'prompter_color_presets': (
                    self._normalize_prompter_color_presets(
                        settings.get('prompter_color_presets', [])
                    )
                ),
                'audiobook_config': self._normalize_audiobook_config(
                    settings.get('audiobook_config', DEFAULT_AUDIOBOOK_CONFIG)
                ),
                'backup_config': self._normalize_backup_config(
                    settings.get('backup_config', DEFAULT_BACKUP_CONFIG)
                ),
                'docx_import_config': self._normalize_docx_import_config(
                    settings.get('docx_import_config', DEFAULT_DOCX_IMPORT_CONFIG)
                ),
                'docx_import_presets': self._normalize_docx_import_presets(
                    settings.get('docx_import_presets', [])
                ),
                'ass_import_config': self._normalize_ass_import_config(
                    settings.get('ass_import_config', DEFAULT_ASS_IMPORT_CONFIG)
                ),
                'srt_import_config': self._normalize_srt_import_config(
                    settings.get('srt_import_config', DEFAULT_SRT_IMPORT_CONFIG)
                ),
                'default_replica_merge_config': (
                    self._normalize_replica_merge_config(
                        settings.get(
                            'default_replica_merge_config',
                            DEFAULT_REPLICA_MERGE_CONFIG,
                        )
                    )
                ),
                'project_summary_export_metric': (
                    self._normalize_project_summary_export_metric(
                        settings.get('project_summary_export_metric')
                    )
                ),
                'language': self._normalize_language(
                    settings.get('language', DEFAULT_LANGUAGE)
                ),
            }

            with open(self._settings_file, 'w', encoding='utf-8') as f:
                json.dump(data_to_save, f, ensure_ascii=False, indent=2)

            self.settings = data_to_save
            logger.info(f"Global settings saved to {self._settings_file}")
            return True

        except Exception as e:
            logger.error(f"Failed to save global settings: {e}")
            return False

    def _backup_settings_file(self) -> Optional[Path]:
        """Create a backup before overwriting global settings."""
        if not self._settings_file.exists() or not self._settings_file.is_file():
            return None

        backup_dir = self._settings_file.parent / ".backups"
        backup_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        backup_path = backup_dir / f"global_settings_{timestamp}.json"
        shutil.copy2(self._settings_file, backup_path)
        return backup_path

    def _get_defaults(self) -> Dict[str, Any]:
        """Return defaults."""
        return {
            'recent_projects': [],
            'global_actor_base': {},
            'default_export_config': deepcopy(DEFAULT_EXPORT_CONFIG),
            'default_prompter_config': deepcopy(DEFAULT_PROMPTER_CONFIG),
            'prompter_color_presets': [None, None, None, None],
            'audiobook_config': deepcopy(DEFAULT_AUDIOBOOK_CONFIG),
            'backup_config': deepcopy(DEFAULT_BACKUP_CONFIG),
            'docx_import_config': deepcopy(DEFAULT_DOCX_IMPORT_CONFIG),
            'docx_import_presets': [],
            'ass_import_config': deepcopy(DEFAULT_ASS_IMPORT_CONFIG),
            'srt_import_config': deepcopy(DEFAULT_SRT_IMPORT_CONFIG),
            'default_replica_merge_config': deepcopy(
                DEFAULT_REPLICA_MERGE_CONFIG
            ),
            'project_summary_export_metric': DEFAULT_PROJECT_SUMMARY_EXPORT_METRIC,
            'language': DEFAULT_GLOBAL_SETTINGS.get('language', DEFAULT_LANGUAGE),
        }

    def get_settings(self) -> Dict[str, Any]:
        """Return settings."""
        if not self.settings:
            return self._get_defaults()
        return self.settings

    def get_export_config(self) -> Dict[str, Any]:
        """Return export settings."""
        return self.get_default_export_config()

    def get_default_export_config(self) -> Dict[str, Any]:
        """Return default export settings for new projects."""
        return self._normalize_export_config(
            self.settings.get('default_export_config', {})
        )

    def set_default_export_config(self, config: Dict[str, Any]) -> None:
        """Set default export settings for new projects."""
        self.settings['default_export_config'] = self._normalize_export_config(
            config
        )

    def get_prompter_config(self) -> Dict[str, Any]:
        """Return teleprompter settings."""
        return self.get_default_prompter_config()

    def get_default_prompter_config(self) -> Dict[str, Any]:
        """Return default teleprompter settings for new projects."""
        return self._normalize_prompter_config(
            self.settings.get('default_prompter_config', {})
        )

    def set_default_prompter_config(self, config: Dict[str, Any]) -> None:
        """Set default teleprompter settings for new projects."""
        self.settings['default_prompter_config'] = (
            self._normalize_prompter_config(config)
        )

    def get_project_summary_export_metric(self) -> str:
        """Return the metric used by project summary spreadsheet export."""
        return self._normalize_project_summary_export_metric(
            self.settings.get('project_summary_export_metric')
        )

    def set_project_summary_export_metric(self, metric: str) -> None:
        """Set the metric used by project summary spreadsheet export."""
        self.settings['project_summary_export_metric'] = (
            self._normalize_project_summary_export_metric(metric)
        )

    def get_prompter_color_presets(self) -> List[Optional[Dict[str, str]]]:
        """Return global teleprompter color presets."""
        return self._normalize_prompter_color_presets(
            self.settings.get('prompter_color_presets', [])
        )

    def set_prompter_color_preset(
        self,
        index: int,
        colors: Optional[Dict[str, str]]
    ) -> None:
        """Set one global teleprompter color preset."""
        presets = self.get_prompter_color_presets()
        if 0 <= index < len(presets):
            presets[index] = self._normalize_prompter_colors(colors)
            self.settings['prompter_color_presets'] = presets

    def clear_prompter_color_preset(self, index: int) -> None:
        """Clear one global teleprompter color preset."""
        self.set_prompter_color_preset(index, None)

    def get_replica_merge_config(self) -> Dict[str, Any]:
        """Return replica merge settings."""
        return self._normalize_replica_merge_config(
            self.settings.get(
                'default_replica_merge_config',
                self.settings.get(
                    'replica_merge_config', DEFAULT_REPLICA_MERGE_CONFIG
                ),
            )
        )

    def get_ass_import_config(self) -> Dict[str, Any]:
        return self._normalize_ass_import_config(
            self.settings.get('ass_import_config', DEFAULT_ASS_IMPORT_CONFIG)
        )

    def get_srt_import_config(self) -> Dict[str, Any]:
        return self._normalize_srt_import_config(
            self.settings.get('srt_import_config', DEFAULT_SRT_IMPORT_CONFIG)
        )

    def get_docx_import_config(self) -> Dict[str, Any]:
        """Return DOCX import settings."""
        return self._normalize_docx_import_config(
            self.settings.get('docx_import_config', DEFAULT_DOCX_IMPORT_CONFIG)
        )

    def get_docx_import_presets(self) -> List[Dict[str, Any]]:
        """Return reusable named DOCX detection presets."""
        return self._normalize_docx_import_presets(
            self.settings.get('docx_import_presets', [])
        )

    def set_docx_import_presets(self, presets: Any) -> None:
        self.settings['docx_import_presets'] = (
            self._normalize_docx_import_presets(presets)
        )

    def get_audiobook_config(self) -> Dict[str, Any]:
        """Return global audiobook import settings."""
        return self._normalize_audiobook_config(
            self.get_settings().get(
                'audiobook_config',
                DEFAULT_AUDIOBOOK_CONFIG,
            )
        )

    def get_backup_config(self) -> Dict[str, Any]:
        """Return normalized project-backup settings."""
        return self._normalize_backup_config(
            self.get_settings().get('backup_config', DEFAULT_BACKUP_CONFIG)
        )

    @staticmethod
    def _normalize_backup_config(value: Any) -> Dict[str, Any]:
        config = deepcopy(DEFAULT_BACKUP_CONFIG)
        if isinstance(value, dict):
            config.update(value)
        config["enabled"] = bool(config.get("enabled", True))
        mode = str(config.get("path_mode", "relative") or "relative")
        config["path_mode"] = (
            mode if mode in {"relative", "absolute"} else "relative"
        )
        directory = str(config.get("directory", ".backups") or "").strip()
        config["directory"] = directory or ".backups"
        for key, low, high, fallback in (
            ("interval_minutes", 1, 1440, 5),
            ("max_backups", 1, 100, 10),
        ):
            try:
                config[key] = max(low, min(high, int(config.get(key, fallback))))
            except (TypeError, ValueError):
                config[key] = fallback
        return config

    def update_export_config(self, config: Dict[str, Any]) -> None:
        """Update export settings."""
        default_config = self.get_default_export_config()
        default_config.update(config)
        self.set_default_export_config(default_config)

    def update_prompter_config(self, config: Dict[str, Any]) -> None:
        """Update teleprompter settings."""
        default_config = self.get_default_prompter_config()
        default_config.update(config)
        self.set_default_prompter_config(default_config)

    def update_replica_merge_config(self, config: Dict[str, Any]) -> None:
        """Update replica merge settings."""
        current = self.get_replica_merge_config()
        current.update(config)
        self.settings['default_replica_merge_config'] = (
            self._normalize_replica_merge_config(current)
        )
        self.settings['replica_merge_config'] = deepcopy(
            self.settings['default_replica_merge_config']
        )

    def update_docx_import_config(self, config: Dict[str, Any]) -> None:
        """Update DOCX import settings."""
        current = self.get_docx_import_config()
        current.update(deepcopy(config))
        self.settings['docx_import_config'] = self._normalize_docx_import_config(
            current
        )

    def get_language(self) -> str:
        """Return the selected interface language."""
        return self._normalize_language(
            self.settings.get('language', DEFAULT_LANGUAGE)
        )

    def set_language(self, language: str) -> None:
        """Set the selected interface language."""
        self.settings['language'] = self._normalize_language(language)

    def get_recent_projects(self) -> List[str]:
        """Return recent project paths."""
        return self._normalize_recent_projects(
            self.settings.get('recent_projects', [])
        )

    def add_recent_project(self, path: str, limit: int = 10) -> None:
        """Add a project path to the recent-project list."""
        if not path:
            return

        normalized = str(Path(path).expanduser().resolve())
        current = [
            item for item in self.get_recent_projects()
            if item != normalized
        ]
        self.settings['recent_projects'] = [normalized, *current][:limit]

    def clear_recent_projects(self) -> None:
        """Clear the recent-project list."""
        self.settings['recent_projects'] = []

    def get_global_actor_base(self) -> Dict[str, Dict[str, str]]:
        """Return global actor base."""
        return self._normalize_actor_base(
            self.settings.get('global_actor_base', {})
        )

    def set_global_actor_base(self, actors: Dict[str, Any]) -> None:
        """Set global actor base."""
        self.settings['global_actor_base'] = self._normalize_actor_base(actors)

    def add_global_actor(
        self,
        name: str,
        color: str = "",
        actor_id: Optional[str] = None,
        gender: str = ""
    ) -> str:
        """Add an actor to the global actor base or update an existing name."""
        actor_base = self.get_global_actor_base()
        normalized_name = name.strip()
        if not normalized_name:
            raise ValueError("Actor name is required")

        existing_id = self.find_global_actor_by_name(normalized_name)
        if existing_id:
            return existing_id

        import time
        target_id = actor_id or f"global_{time.time()}"
        while target_id in actor_base:
            target_id = f"{target_id}_copy"

        actor_base[target_id] = {
            "name": normalized_name,
            "gender": self._normalize_actor_gender(gender),
        }
        self.settings['global_actor_base'] = actor_base
        return target_id

    def remove_global_actor(self, actor_id: str) -> bool:
        """Remove an actor from the global actor base."""
        actor_base = self.get_global_actor_base()
        if actor_id not in actor_base:
            return False
        del actor_base[actor_id]
        self.settings['global_actor_base'] = actor_base
        return True

    def add_project_actors_to_global(
        self,
        project_actors: Dict[str, Any],
        actor_ids: Optional[List[str]] = None
    ) -> Dict[str, int]:
        """Add selected project actors to the global actor base."""
        selected_ids = set(actor_ids) if actor_ids is not None else None
        actor_base = self.get_global_actor_base()
        added = 0
        skipped_existing = 0
        skipped_invalid = 0

        for actor_id, actor in project_actors.items():
            if selected_ids is not None and actor_id not in selected_ids:
                continue
            if not isinstance(actor, dict):
                skipped_invalid += 1
                continue

            name = str(actor.get("name", "")).strip()
            if not name:
                skipped_invalid += 1
                continue

            if self.find_global_actor_by_name(name):
                skipped_existing += 1
                continue

            target_id = str(actor_id)
            while target_id in actor_base:
                target_id = f"{target_id}_imported"
            actor_base[target_id] = {
                "name": name,
                "gender": self._normalize_actor_gender(
                    str(actor.get("gender", ""))
                ),
            }
            added += 1

        self.settings['global_actor_base'] = actor_base
        return {
            "added": added,
            "skipped_existing": skipped_existing,
            "skipped_invalid": skipped_invalid,
        }

    def find_global_actor_by_name(self, name: str) -> Optional[str]:
        """Find a global actor by name."""
        normalized_name = name.strip().casefold()
        for actor_id, actor in self.get_global_actor_base().items():
            if actor.get("name", "").strip().casefold() == normalized_name:
                return actor_id
        return None

    def export_global_actor_base(self, path: str) -> None:
        """Export global actor base to a JSON file."""
        payload = {
            "format": "dubbing-manager.global-actor-base",
            "version": "1.0",
            "actors": self.get_global_actor_base(),
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)

    def import_global_actor_base(self, path: str) -> Dict[str, int]:
        """Import global actor base from a JSON file."""
        with open(path, "r", encoding="utf-8") as f:
            payload = json.load(f)

        if (
            not isinstance(payload, dict) or
            payload.get("format") != "dubbing-manager.global-actor-base" or
            not isinstance(payload.get("actors"), dict)
        ):
            raise ValueError(
                translate_source("Это не файл глобальной базы актёров Dubbing Manager.")
            )

        current = self.get_global_actor_base()
        added = 0
        matched = 0

        for imported_id, actor in self._normalize_actor_base(
            payload.get("actors", {})
        ).items():
            existing_id = self.find_global_actor_by_name(actor["name"])
            if existing_id:
                matched += 1
                continue

            target_id = imported_id
            while target_id in current:
                target_id = f"{target_id}_imported"
            current[target_id] = actor
            added += 1

        self.settings['global_actor_base'] = current
        return {"added": added, "matched": matched}

    def _normalize_recent_projects(self, projects: Any) -> List[str]:
        """Return a deduplicated list of existing recent-project paths."""
        if not isinstance(projects, list):
            return []

        result: List[str] = []
        for item in projects:
            if not isinstance(item, str) or not item:
                continue
            path = str(Path(item).expanduser())
            if path not in result:
                result.append(path)
        return result[:10]

    def _normalize_actor_base(self, actors: Any) -> Dict[str, Dict[str, str]]:
        """Return sanitized global actor base data."""
        if not isinstance(actors, dict):
            return {}

        result: Dict[str, Dict[str, str]] = {}
        for actor_id, actor in actors.items():
            if not isinstance(actor, dict):
                continue
            name = str(actor.get("name", "")).strip()
            if not name:
                continue
            result[str(actor_id)] = {
                "name": name,
                "gender": self._normalize_actor_gender(
                    str(actor.get("gender", ""))
                ),
            }
        return result

    def _normalize_export_config(self, config: Any) -> Dict[str, Any]:
        """Return sanitized default export settings."""
        result = deepcopy(DEFAULT_EXPORT_CONFIG)
        if isinstance(config, dict):
            for key in DEFAULT_EXPORT_CONFIG:
                if key in config:
                    result[key] = deepcopy(config[key])
        return result

    def _normalize_prompter_config(self, config: Any) -> Dict[str, Any]:
        """Return sanitized default teleprompter settings."""
        result = deepcopy(DEFAULT_PROMPTER_CONFIG)
        if isinstance(config, dict):
            for key in DEFAULT_PROMPTER_CONFIG:
                if key == "colors":
                    continue
                if key in config:
                    result[key] = deepcopy(config[key])
            normalized_colors = self._normalize_prompter_colors(
                config.get("colors")
            )
            if normalized_colors is not None:
                result["colors"] = normalized_colors
        return result

    def _normalize_prompter_colors(
        self,
        colors: Any
    ) -> Optional[Dict[str, str]]:
        """Return sanitized teleprompter colors."""
        if not isinstance(colors, dict):
            return None

        result = deepcopy(DEFAULT_PROMPTER_CONFIG["colors"])
        for color_key in DEFAULT_PROMPTER_CONFIG["colors"]:
            if color_key in colors:
                result[color_key] = str(colors[color_key])
        return result

    def _normalize_prompter_color_presets(
        self,
        presets: Any
    ) -> List[Optional[Dict[str, str]]]:
        """Return four sanitized teleprompter color preset slots."""
        result: List[Optional[Dict[str, str]]] = [None, None, None, None]
        if not isinstance(presets, list):
            return result

        for index, colors in enumerate(presets[:4]):
            result[index] = self._normalize_prompter_colors(colors)
        return result

    def _normalize_audiobook_config(self, config: Any) -> Dict[str, Any]:
        """Return sanitized global audiobook import settings."""
        if not isinstance(config, dict) or "chapter_keywords" not in config:
            return deepcopy(DEFAULT_AUDIOBOOK_CONFIG)

        keywords = config.get("chapter_keywords")
        if not isinstance(keywords, list):
            return deepcopy(DEFAULT_AUDIOBOOK_CONFIG)

        normalized: List[str] = []
        seen = set()
        for keyword in keywords:
            value = " ".join(str(keyword).split())
            folded = value.casefold()
            if value and folded not in seen:
                seen.add(folded)
                normalized.append(value)
        return {"chapter_keywords": normalized}

    def _normalize_docx_import_config(self, config: Any) -> Dict[str, Any]:
        result = deepcopy(DEFAULT_DOCX_IMPORT_CONFIG)
        if not isinstance(config, dict):
            return result

        if config.get("header_mode") in {"auto", "first", "none"}:
            result["header_mode"] = config["header_mode"]
        for key, low, high in (
            ("header_search_rows", 1, 20),
            ("minimum_header_matches", 1, 5),
            ("rows_to_skip", 0, 100),
        ):
            try:
                result[key] = max(low, min(high, int(config.get(key, result[key]))))
            except (TypeError, ValueError):
                pass
        try:
            result["default_duration"] = max(
                0.01, min(60.0, float(config.get("default_duration", 1.0)))
            )
        except (TypeError, ValueError):
            pass

        separators = config.get("time_separators")
        if isinstance(separators, list):
            normalized = [str(item) for item in separators if str(item)]
            if normalized:
                result["time_separators"] = list(dict.fromkeys(normalized))

        valid_fields = set(DEFAULT_DOCX_IMPORT_CONFIG["field_priority"])
        priority = config.get("field_priority")
        if isinstance(priority, list):
            normalized = [str(item) for item in priority if str(item) in valid_fields]
            result["field_priority"] = list(dict.fromkeys(normalized))
            result["field_priority"].extend(
                field for field in DEFAULT_DOCX_IMPORT_CONFIG["field_priority"]
                if field not in result["field_priority"]
            )

        aliases = config.get("aliases")
        if isinstance(aliases, dict):
            for field in valid_fields:
                values = aliases.get(field)
                if isinstance(values, list):
                    cleaned = [" ".join(str(item).split()) for item in values]
                    result["aliases"][field] = [item for item in cleaned if item]

        for mapping_key in ("mapping", "fallback_mapping"):
            mapping = config.get(mapping_key)
            if isinstance(mapping, dict):
                for field in valid_fields:
                    value = mapping.get(field)
                    if value is None:
                        result[mapping_key][field] = None
                    else:
                        try:
                            result[mapping_key][field] = max(0, int(value))
                        except (TypeError, ValueError):
                            pass
        return result

    def _normalize_docx_import_presets(self, presets: Any) -> List[Dict[str, Any]]:
        if not isinstance(presets, list):
            return []
        result = []
        seen = set()
        for item in presets:
            if not isinstance(item, dict):
                continue
            name = " ".join(str(item.get('name') or '').split())
            folded = name.casefold()
            if not name or folded in seen:
                continue
            result.append({
                'name': name,
                'config': self._normalize_docx_import_config(
                    item.get('config', {})
                ),
            })
            seen.add(folded)
        return result

    @staticmethod
    def _normalize_ass_import_config(config: Any) -> Dict[str, Any]:
        result = deepcopy(DEFAULT_ASS_IMPORT_CONFIG)
        if not isinstance(config, dict):
            return result
        result['split_character_names'] = bool(
            config.get('split_character_names', result['split_character_names'])
        )
        result['strip_override_tags'] = bool(
            config.get('strip_override_tags', result['strip_override_tags'])
        )
        separator = str(config.get('character_separator', ';'))
        result['character_separator'] = separator or ';'
        return result

    @staticmethod
    def _normalize_srt_import_config(config: Any) -> Dict[str, Any]:
        result = deepcopy(DEFAULT_SRT_IMPORT_CONFIG)
        if not isinstance(config, dict):
            return result
        result['detect_character_prefix'] = bool(
            config.get('detect_character_prefix', True)
        )
        result['keep_multiline'] = bool(config.get('keep_multiline', True))
        separator = str(config.get('character_separator', ':'))
        result['character_separator'] = separator or ':'
        result['default_character'] = str(
            config.get('default_character', '')
        ).strip()
        return result

    @staticmethod
    def _normalize_replica_merge_config(config: Any) -> Dict[str, Any]:
        result = deepcopy(DEFAULT_REPLICA_MERGE_CONFIG)
        if not isinstance(config, dict):
            return result
        result['merge'] = bool(config.get('merge', result['merge']))
        for key, low, high in (
            ('fps', 1.0, 120.0),
            ('merge_gap', 0.0, 12000.0),
            ('p_short', 0.0, 5.0),
            ('p_long', 0.0, 10.0),
        ):
            try:
                result[key] = max(low, min(high, float(config.get(key, result[key]))))
            except (TypeError, ValueError):
                pass
        return result

    def _normalize_project_summary_export_metric(self, metric: Any) -> str:
        """Return a supported project summary spreadsheet metric."""
        value = str(metric or DEFAULT_PROJECT_SUMMARY_EXPORT_METRIC)
        if value in PROJECT_SUMMARY_EXPORT_METRICS:
            return value
        return DEFAULT_PROJECT_SUMMARY_EXPORT_METRIC

    def _normalize_actor_gender(self, gender: str) -> str:
        """Return a normalized actor gender marker."""
        value = str(gender or "").strip().upper()
        if value in {"M", "М"}:
            return "М"
        if value in {"F", "Ж"}:
            return "Ж"
        return ""

    def _normalize_language(self, language: Any) -> str:
        """Return a supported interface language code."""
        language_code = str(language or DEFAULT_LANGUAGE)
        if language_code in SUPPORTED_LANGUAGES:
            return language_code
        return DEFAULT_LANGUAGE
