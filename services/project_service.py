"""Service for project file loading and saving."""

import json
import os
import shutil
import logging
import sys
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List

# fcntl is only available on Unix-like systems; Windows saves without locking.
try:
    import fcntl
    HAS_FCNTL = True
except ImportError:
    HAS_FCNTL = False

from PySide6.QtWidgets import QMessageBox

from config.constants import (
    DEFAULT_DOCX_IMPORT_CONFIG,
    DEFAULT_EXPORT_CONFIG,
    DEFAULT_PROMPTER_CONFIG,
    DEFAULT_REPLICA_MERGE_CONFIG,
    PROJECT_VERSION,
)
from services.project_compatibility import ensure_project_compatibility
from utils.i18n import translate_source

logger = logging.getLogger(__name__)

PROJECT_FORMAT_VERSION = PROJECT_VERSION

MAX_BACKUPS = 10


class ProjectValidationError(Exception):
    """Project Validation Error class."""
    pass


class ProjectService:
    """Project Service implementation."""

    def __init__(self):
        self.current_project_path: Optional[str] = None
        self.is_dirty: bool = False
        self._project_metadata: Dict[str, Any] = {}

    def create_new_project(self, name: str) -> Dict[str, Any]:
        """Create new project."""
        now = datetime.now().isoformat()

        return {
            "metadata": {
                "format_version": PROJECT_FORMAT_VERSION,
                "app_version": "1.0+",
                "created_at": now,
                "modified_at": now,
                "created_by": "",
                "studio": ""
            },
            "project_name": name,
            "actors": {},
            "global_map": {},
            "episode_actor_map": {},
            "episodes": {},
            "video_paths": {},
            "episode_texts": {},
            "export_config": deepcopy(DEFAULT_EXPORT_CONFIG),
            "prompter_config": deepcopy(DEFAULT_PROMPTER_CONFIG),
            "replica_merge_config": deepcopy(DEFAULT_REPLICA_MERGE_CONFIG),
            "docx_import_config": deepcopy(DEFAULT_DOCX_IMPORT_CONFIG),
            "project_folder": None,
        }

    def load_project(self, path: str) -> Optional[Dict[str, Any]]:
        """Load project."""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            self._validate_project_structure(data)
            
            self._ensure_compatibility(data)
            
            self._update_metadata_on_load(data, path)

            self.current_project_path = path
            self.is_dirty = False

            logger.info(f"Project loaded from {path}")
            return data

        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON format: {e}")
            raise
        except ProjectValidationError as e:
            logger.error(f"Project validation failed: {e}")
            raise
        except Exception as e:
            logger.error(f"Load failed: {e}")
            raise

    def save_project(
        self,
        data: Dict[str, Any],
        path: Optional[str] = None
    ) -> bool:
        """Save project."""
        save_path = path or self.current_project_path

        if not save_path:
            logger.error("No path specified for save")
            return False

        return self._do_save(data, save_path)

    def save_project_as(
        self,
        data: Dict[str, Any],
        path: str
    ) -> bool:
        """Save project as."""
        self.current_project_path = path
        return self._do_save(data, path)

    def _do_save(self, data: Dict[str, Any], path: str) -> bool:
        """Do save."""
        self._update_metadata_on_save(data)
        save_data = self._project_data_for_disk(data)

        # Write to a temporary file first so a failed save does not corrupt the project.
        temp_path = path + ".tmp"

        try:
            with open(temp_path, 'w', encoding='utf-8') as f:
                if HAS_FCNTL:
                    try:
                        # Use a non-blocking exclusive lock when the platform supports it.
                        fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                    except (IOError, OSError) as lock_err:
                        logger.warning(f"Could not acquire lock on {temp_path}: {lock_err}")

                json.dump(save_data, f, ensure_ascii=False, indent=4)
                f.flush()
                # Force the JSON to disk before swapping it into place.
                os.fsync(f.fileno())

                if HAS_FCNTL:
                    try:
                        fcntl.flock(f.fileno(), fcntl.LOCK_UN)
                    except (IOError, OSError):
                        pass

            # os.replace is atomic on the same filesystem.
            os.replace(temp_path, path)

            self.is_dirty = False
            logger.info(f"Project saved to {path}")
            return True

        except Exception as e:
            logger.error(f"Save failed: {e}")
            if os.path.exists(temp_path):
                try:
                    os.unlink(temp_path)
                except OSError:
                    pass
            return False
        finally:
            # Clean up a leftover temp file if os.replace or any earlier step failed.
            if os.path.exists(temp_path):
                try:
                    os.unlink(temp_path)
                except OSError:
                    pass

    def auto_save(self, data: Dict[str, Any]) -> bool:
        """Auto save."""
        if not self.is_dirty:
            return True
        save_data = self._project_data_for_disk(data)

        if self.current_project_path:
            # Saved projects keep rotating backups next to the project file.
            backup_dir = Path(self.current_project_path).parent / ".backups"
            backup_dir.mkdir(exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            base_name = Path(self.current_project_path).stem
            backup_path = backup_dir / f"{base_name}_{timestamp}.json"
            
            try:
                with open(backup_path, 'w', encoding='utf-8') as f:
                    json.dump(save_data, f, ensure_ascii=False, indent=4)
                
                logger.debug(f"Auto-saved to {backup_path}")
                
                self._rotate_backups(backup_dir)
                
                return True
                
            except Exception as e:
                logger.error(f"Auto-save failed: {e}")
                return False
        else:
            # Unsaved projects still get a temporary backup in the current working directory.
            path = "temp_autosave.json.bak"
            try:
                with open(path, 'w', encoding='utf-8') as f:
                    json.dump(save_data, f, ensure_ascii=False, indent=4)
                logger.debug(f"Auto-saved to {path}")
                return True
            except Exception as e:
                logger.error(f"Auto-save failed: {e}")
                return False

    def _rotate_backups(self, backup_dir: Path) -> None:
        """Rotate backups."""
        try:
            backups = sorted(
                backup_dir.glob("*.json"),
                key=lambda p: p.stat().st_mtime,
                reverse=True
            )
            
            for old_backup in backups[MAX_BACKUPS:]:
                try:
                    old_backup.unlink()
                    logger.debug(f"Removed old backup: {old_backup}")
                except OSError as e:
                    logger.warning(f"Failed to remove backup {old_backup}: {e}")
                    
        except Exception as e:
            logger.error(f"Backup rotation failed: {e}")

    def _project_data_for_disk(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Return a save payload without runtime-only cache fields."""
        save_data = deepcopy(data)
        save_data.pop("loaded_episodes", None)
        return save_data

    def _validate_project_structure(self, data: Dict[str, Any]) -> None:
        """Validate project structure."""
        required_fields = [
            "project_name",
            "actors",
            "episodes",
        ]
        
        for field in required_fields:
            if field not in data:
                raise ProjectValidationError(
                    f"Missing required field: {field}"
                )
        
        if not isinstance(data["project_name"], str):
            raise ProjectValidationError(
                "Field 'project_name' must be a string"
            )
        
        if not isinstance(data["actors"], dict):
            raise ProjectValidationError(
                "Field 'actors' must be a dictionary"
            )
        
        if not isinstance(data["episodes"], dict):
            raise ProjectValidationError(
                "Field 'episodes' must be a dictionary"
            )
        
        if "global_map" in data and not isinstance(data["global_map"], dict):
            raise ProjectValidationError(
                "Field 'global_map' must be a dictionary"
            )

        if (
            "episode_actor_map" in data and
            not isinstance(data["episode_actor_map"], dict)
        ):
            raise ProjectValidationError(
                "Field 'episode_actor_map' must be a dictionary"
            )
        
        # Video handling
        if "video_paths" in data and not isinstance(data["video_paths"], dict):
            raise ProjectValidationError(
                "Field 'video_paths' must be a dictionary"
            )

        if "episode_texts" in data and not isinstance(data["episode_texts"], dict):
            raise ProjectValidationError(
                "Field 'episode_texts' must be a dictionary"
            )

    def _ensure_compatibility(self, data: Dict[str, Any]) -> None:
        """Ensure compatibility."""
        ensure_project_compatibility(data)

    def _update_metadata_on_save(self, data: Dict[str, Any]) -> None:
        """Update metadata on save."""
        if "metadata" not in data:
            data["metadata"] = {}
        
        data["metadata"]["modified_at"] = datetime.now().isoformat()
        data["metadata"]["format_version"] = PROJECT_FORMAT_VERSION
        data["metadata"]["app_version"] = "1.0+"

    def _update_metadata_on_load(self, data: Dict[str, Any], path: str) -> None:
        """Update metadata on load."""
        if "metadata" in data:
            self._project_metadata = data["metadata"]
        else:
            self._project_metadata = {}

    def set_dirty(self, dirty: bool = True) -> None:
        """Set dirty."""
        self.is_dirty = dirty

    def get_project_name(self, data: Dict[str, Any]) -> str:
        """Return project name."""
        return data.get("project_name", translate_source("Новый проект"))

    def set_project_name(
        self,
        data: Dict[str, Any],
        name: str
    ) -> None:
        """Set project name."""
        data["project_name"] = name
        self.set_dirty()

    def get_window_title(self, data: Dict[str, Any]) -> str:
        """Return window title."""
        title = "Dubbing Manager"
        project_name = str(
            data.get("project_name") or translate_source("Новый проект")
        ).strip()
        if project_name:
            title += f" - {project_name}"

        if self.current_project_path:
            title += f" - {os.path.basename(self.current_project_path)}"
        else:
            title += f" - [{translate_source('Новый')}]"

        if self.is_dirty:
            title += " *"

        return title

    def get_project_metadata(self) -> Dict[str, Any]:
        """Return project metadata."""
        return self._project_metadata.copy()

    def get_backup_directory(self) -> Optional[Path]:
        """Return backup directory."""
        if self.current_project_path:
            return Path(self.current_project_path).parent / ".backups"
        return None

    def list_backups(self) -> List[Path]:
        """List backups."""
        backup_dir = self.get_backup_directory()
        if backup_dir and backup_dir.exists():
            return sorted(
                backup_dir.glob("*.json"),
                key=lambda p: p.stat().st_mtime,
                reverse=True
            )
        return []

    def restore_from_backup(self, backup_path: str, target_path: str) -> bool:
        """Restore from backup."""
        try:
            with open(backup_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self._validate_project_structure(data)
            
            return self._do_save(data, target_path)
            
        except Exception as e:
            logger.error(f"Restore from backup failed: {e}")
            return False
