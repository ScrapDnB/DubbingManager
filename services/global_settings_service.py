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
    DEFAULT_DOCX_IMPORT_CONFIG,
    DEFAULT_EXPORT_CONFIG,
    DEFAULT_PROMPTER_CONFIG,
    DEFAULT_REPLICA_MERGE_CONFIG,
)

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

            # Apply loaded settings over defaults
            settings = self._get_defaults()
            
            # Merge loaded settings with defaults
            if 'export_config' in loaded and loaded['export_config']:
                settings['export_config'].update(loaded['export_config'])
            
            if 'prompter_config' in loaded and loaded['prompter_config']:
                settings['prompter_config'].update(loaded['prompter_config'])
                # Special handling for nested colors
                if 'colors' in loaded['prompter_config']:
                    settings['prompter_config']['colors'].update(
                        loaded['prompter_config']['colors']
                    )
            
            if 'replica_merge_config' in loaded and loaded['replica_merge_config']:
                settings['replica_merge_config'].update(
                    loaded['replica_merge_config']
                )

            if 'docx_import_config' in loaded and loaded['docx_import_config']:
                settings['docx_import_config'].update(
                    loaded['docx_import_config']
                )

            if 'recent_projects' in loaded:
                settings['recent_projects'] = self._normalize_recent_projects(
                    loaded.get('recent_projects', [])
                )

            if 'global_actor_base' in loaded:
                settings['global_actor_base'] = self._normalize_actor_base(
                    loaded.get('global_actor_base', {})
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

            # Save only the required sections
            data_to_save = {
                'export_config': settings.get('export_config'),
                'prompter_config': settings.get('prompter_config'),
                'replica_merge_config': settings.get('replica_merge_config'),
                'docx_import_config': settings.get('docx_import_config'),
                'recent_projects': self._normalize_recent_projects(
                    settings.get('recent_projects', [])
                ),
                'global_actor_base': self._normalize_actor_base(
                    settings.get('global_actor_base', {})
                ),
            }

            with open(self._settings_file, 'w', encoding='utf-8') as f:
                json.dump(data_to_save, f, ensure_ascii=False, indent=2)

            self.settings = settings
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
            'export_config': deepcopy(DEFAULT_EXPORT_CONFIG),
            'prompter_config': deepcopy(DEFAULT_PROMPTER_CONFIG),
            'replica_merge_config': deepcopy(DEFAULT_REPLICA_MERGE_CONFIG),
            'docx_import_config': deepcopy(DEFAULT_DOCX_IMPORT_CONFIG),
            'recent_projects': [],
            'global_actor_base': {},
        }

    def get_settings(self) -> Dict[str, Any]:
        """Return settings."""
        if not self.settings:
            return self._get_defaults()
        return self.settings

    def get_export_config(self) -> Dict[str, Any]:
        """Return export settings."""
        return self.settings.get('export_config', deepcopy(DEFAULT_EXPORT_CONFIG))

    def get_prompter_config(self) -> Dict[str, Any]:
        """Return teleprompter settings."""
        return self.settings.get(
            'prompter_config',
            deepcopy(DEFAULT_PROMPTER_CONFIG)
        )

    def get_replica_merge_config(self) -> Dict[str, Any]:
        """Return replica merge settings."""
        return self.settings.get(
            'replica_merge_config',
            deepcopy(DEFAULT_REPLICA_MERGE_CONFIG)
        )

    def get_docx_import_config(self) -> Dict[str, Any]:
        """Return DOCX import settings."""
        return self.settings.get(
            'docx_import_config',
            deepcopy(DEFAULT_DOCX_IMPORT_CONFIG)
        )

    def update_export_config(self, config: Dict[str, Any]) -> None:
        """Update export settings."""
        if 'export_config' not in self.settings:
            self.settings['export_config'] = {}
        self.settings['export_config'].update(config)

    def update_prompter_config(self, config: Dict[str, Any]) -> None:
        """Update teleprompter settings."""
        if 'prompter_config' not in self.settings:
            self.settings['prompter_config'] = {}
        self.settings['prompter_config'].update(config)

    def update_replica_merge_config(self, config: Dict[str, Any]) -> None:
        """Update replica merge settings."""
        if 'replica_merge_config' not in self.settings:
            self.settings['replica_merge_config'] = {}
        self.settings['replica_merge_config'].update(config)

    def update_docx_import_config(self, config: Dict[str, Any]) -> None:
        """Update DOCX import settings."""
        if 'docx_import_config' not in self.settings:
            self.settings['docx_import_config'] = {}
        self.settings['docx_import_config'].update(config)

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
        color: str,
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
            "color": color or "#FFFFFF",
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
                "color": str(actor.get("color", "#FFFFFF") or "#FFFFFF"),
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
            raise ValueError("Это не файл глобальной базы актёров Dubbing Manager.")

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
                "color": str(actor.get("color", "#FFFFFF") or "#FFFFFF"),
                "gender": self._normalize_actor_gender(
                    str(actor.get("gender", ""))
                ),
            }
        return result

    def _normalize_actor_gender(self, gender: str) -> str:
        """Return a normalized actor gender marker."""
        value = str(gender or "").strip().upper()
        if value in {"M", "М"}:
            return "М"
        if value in {"F", "Ж"}:
            return "Ж"
        return ""
