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

# Internal implementation detail
# Internal implementation detail
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

logger = logging.getLogger(__name__)

# Internal implementation detail
PROJECT_FORMAT_VERSION = PROJECT_VERSION

# Internal implementation detail
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
            "project_folder": None,  # Internal implementation detail
        }

    def load_project(self, path: str) -> Optional[Dict[str, Any]]:
        """Load project."""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Internal implementation detail
            self._validate_project_structure(data)
            
            # Internal implementation detail
            self._ensure_compatibility(data)
            
            # Internal implementation detail
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
        # Internal implementation detail
        self._update_metadata_on_save(data)

        # Internal implementation detail
        temp_path = path + ".tmp"

        try:
            # Internal implementation detail
            with open(temp_path, 'w', encoding='utf-8') as f:
                # Internal implementation detail
                # Internal implementation detail
                if HAS_FCNTL:
                    try:
                        fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                    except (IOError, OSError) as lock_err:
                        logger.warning(f"Could not acquire lock on {temp_path}: {lock_err}")
                        # Internal implementation detail

                json.dump(data, f, ensure_ascii=False, indent=4)
                f.flush()
                os.fsync(f.fileno())  # Internal implementation detail

                # Internal implementation detail
                if HAS_FCNTL:
                    try:
                        fcntl.flock(f.fileno(), fcntl.LOCK_UN)
                    except (IOError, OSError):
                        pass

            # Internal implementation detail
            os.replace(temp_path, path)

            self.is_dirty = False
            logger.info(f"Project saved to {path}")
            return True

        except Exception as e:
            logger.error(f"Save failed: {e}")
            # Internal implementation detail
            if os.path.exists(temp_path):
                try:
                    os.unlink(temp_path)
                except OSError:
                    pass
            return False
        finally:
            # Internal implementation detail
            if os.path.exists(temp_path):
                try:
                    os.unlink(temp_path)
                except OSError:
                    pass

    def auto_save(self, data: Dict[str, Any]) -> bool:
        """Auto save."""
        if not self.is_dirty:
            return True

        if self.current_project_path:
            # Internal implementation detail
            backup_dir = Path(self.current_project_path).parent / ".backups"
            backup_dir.mkdir(exist_ok=True)
            
            # Internal implementation detail
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            base_name = Path(self.current_project_path).stem
            backup_path = backup_dir / f"{base_name}_{timestamp}.json"
            
            try:
                # Internal implementation detail
                with open(backup_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=4)
                
                logger.debug(f"Auto-saved to {backup_path}")
                
                # Internal implementation detail
                self._rotate_backups(backup_dir)
                
                return True
                
            except Exception as e:
                logger.error(f"Auto-save failed: {e}")
                return False
        else:
            # Internal implementation detail
            path = "temp_autosave.json.bak"
            try:
                with open(path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=4)
                logger.debug(f"Auto-saved to {path}")
                return True
            except Exception as e:
                logger.error(f"Auto-save failed: {e}")
                return False

    def _rotate_backups(self, backup_dir: Path) -> None:
        """Rotate backups."""
        try:
            # Internal implementation detail
            backups = sorted(
                backup_dir.glob("*.json"),
                key=lambda p: p.stat().st_mtime,
                reverse=True
            )
            
            # Internal implementation detail
            for old_backup in backups[MAX_BACKUPS:]:
                try:
                    old_backup.unlink()
                    logger.debug(f"Removed old backup: {old_backup}")
                except OSError as e:
                    logger.warning(f"Failed to remove backup {old_backup}: {e}")
                    
        except Exception as e:
            logger.error(f"Backup rotation failed: {e}")

    def _validate_project_structure(self, data: Dict[str, Any]) -> None:
        """Validate project structure."""
        # Internal implementation detail
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
        
        # Internal implementation detail
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
        
        # Internal implementation detail
        if "global_map" in data and not isinstance(data["global_map"], dict):
            raise ProjectValidationError(
                "Field 'global_map' must be a dictionary"
            )

        # Internal implementation detail
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

        # Internal implementation detail
        if "episode_texts" in data and not isinstance(data["episode_texts"], dict):
            raise ProjectValidationError(
                "Field 'episode_texts' must be a dictionary"
            )

    def _ensure_compatibility(self, data: Dict[str, Any]) -> None:
        """Ensure compatibility."""
        if "video_paths" not in data:
            data["video_paths"] = {}
        if "episode_texts" not in data:
            data["episode_texts"] = {}
        if "export_config" not in data:
            data["export_config"] = deepcopy(DEFAULT_EXPORT_CONFIG)
        if "prompter_config" not in data:
            data["prompter_config"] = deepcopy(DEFAULT_PROMPTER_CONFIG)
        if "global_map" not in data:
            data["global_map"] = {}
        if "episode_actor_map" not in data:
            data["episode_actor_map"] = {}
        if "loaded_episodes" not in data:
            data["loaded_episodes"] = {}
        if "replica_merge_config" not in data:
            # Internal implementation detail
            if "export_config" in data:
                export_cfg = data["export_config"]
                data["replica_merge_config"] = {
                    'merge': export_cfg.get('merge', True),
                    'merge_gap': export_cfg.get('merge_gap', 5),
                    'p_short': export_cfg.get('p_short', 0.5),
                    'p_long': export_cfg.get('p_long', 2.0),
                }
            else:
                data["replica_merge_config"] = deepcopy(
                    DEFAULT_REPLICA_MERGE_CONFIG
                )
        if "docx_import_config" not in data:
            data["docx_import_config"] = deepcopy(DEFAULT_DOCX_IMPORT_CONFIG)
        
        # Internal implementation detail
        if "project_folder" not in data:
            data["project_folder"] = None

        # Internal implementation detail
        if "metadata" not in data:
            now = datetime.now().isoformat()
            data["metadata"] = {
                "format_version": "0.9",  # Internal implementation detail
                "app_version": "pre-1.0",
                "created_at": now,
                "modified_at": now,
            }

    def _update_metadata_on_save(self, data: Dict[str, Any]) -> None:
        """Update metadata on save."""
        if "metadata" not in data:
            data["metadata"] = {}
        
        # Internal implementation detail
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
        return data.get("project_name", "Новый проект")

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

        if self.current_project_path:
            title += f" - {os.path.basename(self.current_project_path)}"
        else:
            title += " - [Новый]"

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
            # Internal implementation detail
            with open(backup_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Internal implementation detail
            self._validate_project_structure(data)
            
            # Internal implementation detail
            return self._do_save(data, target_path)
            
        except Exception as e:
            logger.error(f"Restore from backup failed: {e}")
            return False
