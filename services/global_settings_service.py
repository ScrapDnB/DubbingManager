"""Service for global application settings."""

import json
import os
import logging
import sys
from copy import deepcopy
from pathlib import Path
from typing import Dict, Any, Optional

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

            # Save only the required sections
            data_to_save = {
                'export_config': settings.get('export_config'),
                'prompter_config': settings.get('prompter_config'),
                'replica_merge_config': settings.get('replica_merge_config'),
                'docx_import_config': settings.get('docx_import_config'),
            }

            with open(self._settings_file, 'w', encoding='utf-8') as f:
                json.dump(data_to_save, f, ensure_ascii=False, indent=2)

            self.settings = settings
            logger.info(f"Global settings saved to {self._settings_file}")
            return True

        except Exception as e:
            logger.error(f"Failed to save global settings: {e}")
            return False

    def _get_defaults(self) -> Dict[str, Any]:
        """Return defaults."""
        return {
            'export_config': deepcopy(DEFAULT_EXPORT_CONFIG),
            'prompter_config': deepcopy(DEFAULT_PROMPTER_CONFIG),
            'replica_merge_config': deepcopy(DEFAULT_REPLICA_MERGE_CONFIG),
            'docx_import_config': deepcopy(DEFAULT_DOCX_IMPORT_CONFIG),
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
