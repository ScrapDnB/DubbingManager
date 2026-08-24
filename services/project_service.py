"""Service for project file loading and saving."""

import json
import os
import shutil
import logging
import sys
import hashlib
import stat
import tempfile
from contextlib import contextmanager, nullcontext
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List

# Project files are locked on every supported desktop platform while replacing
# them. The lock lives beside the project and remains stable across os.replace.
try:
    import fcntl
    HAS_FCNTL = True
except ImportError:
    HAS_FCNTL = False

try:
    import msvcrt
    HAS_MSVCRT = True
except ImportError:
    HAS_MSVCRT = False

from config.constants import (
    APP_VERSION,
    DEFAULT_BACKUP_CONFIG,
    DEFAULT_EXPORT_CONFIG,
    DEFAULT_PROMPTER_CONFIG,
    PROJECT_VERSION,
    PROJECT_BACKUP_FILE_EXTENSION,
)
from services.project_compatibility import ensure_project_compatibility
from services.dynamic_script_storage import (
    is_dynamic_script_project,
    new_script_storage,
)
from services.project_fps_service import new_project_settings
from services.project_schema_service import ProjectSchemaError, ProjectSchemaService
from utils.i18n import translate_source

logger = logging.getLogger(__name__)

PROJECT_FORMAT_VERSION = PROJECT_VERSION

MAX_BACKUPS = int(DEFAULT_BACKUP_CONFIG["max_backups"])


class ProjectValidationError(Exception):
    """Project Validation Error class."""
    pass


class ProjectWriteConflictError(OSError):
    """Another DubbingManager process is currently saving this project."""


def _project_lock_path(path: Path) -> Path:
    return path.with_name(f".{path.name}.lock")


@contextmanager
def _exclusive_project_lock(path: Path):
    """Hold a non-blocking lock that survives atomic replacement of *path*."""
    lock_path = _project_lock_path(path)
    with open(lock_path, "a+b") as handle:
        try:
            if HAS_FCNTL:
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            elif HAS_MSVCRT:
                if handle.seek(0, os.SEEK_END) == 0:
                    handle.write(b"\0")
                    handle.flush()
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        except (IOError, OSError) as exc:
            raise ProjectWriteConflictError(
                f"Project is already being saved: {path}"
            ) from exc

        try:
            yield
        finally:
            try:
                if HAS_FCNTL:
                    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
                elif HAS_MSVCRT:
                    handle.seek(0)
                    msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            except (IOError, OSError):
                logger.warning("Could not release project lock %s", lock_path)


class ProjectService:
    """Project Service implementation."""

    def __init__(self, backup_config: Optional[Dict[str, Any]] = None):
        self.current_project_path: Optional[str] = None
        self.is_dirty: bool = False
        self._project_metadata: Dict[str, Any] = {}
        self._backup_config = self._normalize_backup_config(backup_config)
        self._schema = ProjectSchemaService()

    def set_backup_config(self, config: Optional[Dict[str, Any]]) -> None:
        """Apply global backup settings without touching project data."""
        self._backup_config = self._normalize_backup_config(config)

    def get_backup_config(self) -> Dict[str, Any]:
        return deepcopy(self._backup_config)

    def backups_enabled(self) -> bool:
        return bool(self._backup_config.get("enabled", True))

    def create_new_project(self, name: str) -> Dict[str, Any]:
        """Create new project."""
        now = datetime.now().isoformat()

        return {
            "metadata": {
                "format_version": PROJECT_FORMAT_VERSION,
                "app_version": APP_VERSION,
                "created_at": now,
                "modified_at": now,
                "created_by": "",
                "studio": ""
            },
            "project_name": name,
            "project_kind": "subtitle",
            "actors": {},
            "global_map": {},
            "episode_actor_map": {},
            "episodes": {},
            "video_paths": {},
            "episode_texts": {},
            "episode_working_texts": {},
            "script_storage": new_script_storage(),
            "project_settings": new_project_settings(),
            "audiobook_document": {},
            "audiobook_settings": {
                "font_family": "Georgia",
                "zoom_steps": 0,
                "slots": [],
            },
            "export_config": deepcopy(DEFAULT_EXPORT_CONFIG),
            "prompter_config": deepcopy(DEFAULT_PROMPTER_CONFIG),
            "project_folder": None,
        }

    def load_project(self, path: str) -> Optional[Dict[str, Any]]:
        """Load project."""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            self._validate_supported_schema(data)
            original_version = str(
                (data.get("metadata") or {}).get("format_version") or "0.9"
            )
            original_model = (
                "dynamic_source"
                if is_dynamic_script_project(data)
                else "legacy_merged"
            )
            preserved_legacy_fields = {
                key: deepcopy(data[key])
                for key in (
                    "replica_merge_config",
                    "ass_import_config",
                    "srt_import_config",
                    "docx_import_config",
                )
                if key in data
            }
            self._validate_project_structure(data)
            self._ensure_compatibility(data)
            self._validate_current_schema(data)
            data["_project_format"] = {
                "storage_model": original_model,
                "original_version": original_version,
                "preserved_fields": preserved_legacy_fields,
            }
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
        previous_path = self.current_project_path
        if not self._do_save(data, path):
            self.current_project_path = previous_path
            return False
        self.current_project_path = path
        return True

    def _do_save(self, data: Dict[str, Any], path: str) -> bool:
        """Do save."""
        try:
            legacy = self._uses_legacy_storage(data)
            self._validate_supported_schema(data)
            self._validate_project_structure(data)
            save_data = self._project_data_for_disk(data)
            if not legacy:
                self._ensure_compatibility(save_data)
            self._strip_global_ui_config(save_data)
            self._update_metadata_on_save(save_data)
            if legacy:
                save_data["metadata"]["format_version"] = (
                    self._legacy_format_version(data)
                )
            self._validate_supported_schema(save_data)
            if legacy:
                self._validate_project_structure(save_data)
            else:
                self._validate_current_schema(save_data)
        except ProjectValidationError as exc:
            logger.error(f"Save validation failed: {exc}")
            return False

        try:
            self._write_json_atomic(Path(path), save_data, lock=True)

            data["metadata"] = deepcopy(save_data["metadata"])
            self.is_dirty = False
            logger.info(f"Project saved to {path}")
            return True

        except ProjectWriteConflictError as exc:
            logger.warning("Save skipped to avoid a concurrent write: %s", exc)
            return False
        except Exception as e:
            logger.error(f"Save failed: {e}")
            return False

    def auto_save(self, data: Dict[str, Any]) -> bool:
        """Auto save."""
        if not self.is_dirty:
            return True
        return self.create_backup(data)

    def create_backup(
        self,
        data: Dict[str, Any],
        reason: str = "autosave",
    ) -> bool:
        """Write a complete project snapshot using the configured backup policy."""
        if not self.backups_enabled():
            return True
        try:
            legacy = self._uses_legacy_storage(data)
            self._validate_supported_schema(data)
            self._validate_project_structure(data)
            save_data = self._project_data_for_disk(data)
            if not legacy:
                self._ensure_compatibility(save_data)
            self._strip_global_ui_config(save_data)
            self._update_metadata_on_save(save_data)
            if legacy:
                save_data["metadata"]["format_version"] = (
                    self._legacy_format_version(data)
                )
            self._validate_supported_schema(save_data)
            if not legacy:
                self._validate_current_schema(save_data)
        except ProjectValidationError as exc:
            logger.error(f"Backup validation failed: {exc}")
            return False
        safe_reason = "".join(
            character if character.isalnum() or character in "-_" else "_"
            for character in str(reason or "backup")
        ).strip("_") or "backup"
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")

        if self.current_project_path:
            backup_dir = self._backup_directory_for(self.current_project_path)
            backup_dir.mkdir(parents=True, exist_ok=True)
            
            base_name = Path(self.current_project_path).stem
            backup_path = backup_dir / (
                f"{base_name}_{safe_reason}_{timestamp}"
                f"{PROJECT_BACKUP_FILE_EXTENSION}"
            )
            
            try:
                self._write_json_atomic(backup_path, save_data)
                
                logger.debug(f"Auto-saved to {backup_path}")
                
                self._rotate_backups(
                    backup_dir,
                    f"{base_name}_",
                    int(self._backup_config["max_backups"]),
                )
                
                return True
                
            except Exception as e:
                logger.error(f"Auto-save failed: {e}")
                return False
        else:
            backup_dir = self._unsaved_backup_directory()
            backup_dir.mkdir(parents=True, exist_ok=True)
            path = backup_dir / (
                f"unsaved_{safe_reason}_{timestamp}"
                f"{PROJECT_BACKUP_FILE_EXTENSION}"
            )
            try:
                self._write_json_atomic(path, save_data)
                self._rotate_backups(
                    backup_dir,
                    "unsaved_",
                    int(self._backup_config["max_backups"]),
                )
                logger.debug(f"Auto-saved to {path}")
                return True
            except Exception as e:
                logger.error(f"Auto-save failed: {e}")
                return False

    def _rotate_backups(
        self,
        backup_dir: Path,
        prefix: Optional[str] = None,
        limit: int = MAX_BACKUPS,
    ) -> None:
        """Rotate backups."""
        try:
            backups = sorted(
                (
                    path for path in backup_dir.glob(
                        f"*{PROJECT_BACKUP_FILE_EXTENSION}"
                    )
                    if prefix is None or path.name.startswith(prefix)
                ),
                key=lambda p: (p.stat().st_mtime_ns, p.name),
                reverse=True
            )
            
            for old_backup in backups[max(1, int(limit)):]:
                try:
                    old_backup.unlink()
                    logger.debug(f"Removed old backup: {old_backup}")
                except OSError as e:
                    logger.warning(f"Failed to remove backup {old_backup}: {e}")
                    
        except Exception as e:
            logger.error(f"Backup rotation failed: {e}")

    def _project_data_for_disk(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Return a save payload without runtime-only cache fields."""
        runtime = data.get("_project_format")
        save_data = deepcopy(data)
        save_data.pop("loaded_episodes", None)
        save_data.pop("_project_format", None)
        if (
            isinstance(runtime, dict)
            and runtime.get("storage_model") == "legacy_merged"
            and isinstance(runtime.get("preserved_fields"), dict)
        ):
            save_data.update(deepcopy(runtime["preserved_fields"]))
        if (
            is_dynamic_script_project(save_data)
            and save_data.get("project_kind") != "audiobook"
            and not save_data.get("episode_working_texts")
            and not save_data.get("episode_texts")
        ):
            save_data.pop("episode_texts", None)
            save_data.pop("episode_working_texts", None)
        return save_data

    @staticmethod
    def _uses_legacy_storage(data: Dict[str, Any]) -> bool:
        runtime = data.get("_project_format")
        if isinstance(runtime, dict):
            return runtime.get("storage_model") == "legacy_merged"
        return not is_dynamic_script_project(data)

    @staticmethod
    def _legacy_format_version(data: Dict[str, Any]) -> str:
        runtime = data.get("_project_format")
        if isinstance(runtime, dict) and runtime.get("original_version"):
            return str(runtime["original_version"])
        return str((data.get("metadata") or {}).get("format_version") or "0.9")

    @staticmethod
    def _strip_global_ui_config(data: Dict[str, Any]) -> None:
        """Keep global presentation settings out of project snapshots."""
        data.pop("export_config", None)
        data.pop("prompter_config", None)

    @staticmethod
    def _write_json_atomic(
        path: Path,
        data: Dict[str, Any],
        *,
        lock: bool = False,
    ) -> None:
        """Write a JSON snapshot without exposing a partially written file."""
        path = Path(path)
        temp_fd, temp_name = tempfile.mkstemp(
            prefix=f".{path.name}.",
            suffix=".tmp",
            dir=path.parent,
        )
        temp_path = Path(temp_name)
        lock_context = _exclusive_project_lock(path) if lock else nullcontext()
        try:
            with lock_context:
                with os.fdopen(temp_fd, "w", encoding="utf-8") as handle:
                    temp_fd = -1
                    json.dump(data, handle, ensure_ascii=False, indent=4)
                    handle.flush()
                    os.fsync(handle.fileno())
                if path.exists():
                    os.chmod(temp_path, stat.S_IMODE(path.stat().st_mode))
                os.replace(temp_path, path)
                ProjectService._sync_parent_directory(path.parent)
        finally:
            if temp_fd >= 0:
                os.close(temp_fd)
            if temp_path.exists():
                try:
                    temp_path.unlink()
                except OSError:
                    pass

    @staticmethod
    def _sync_parent_directory(directory: Path) -> None:
        """Best-effort durability for the rename itself on Unix filesystems."""
        if not hasattr(os, "O_DIRECTORY"):
            return
        directory_fd = None
        try:
            directory_fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY)
            os.fsync(directory_fd)
        except OSError:
            logger.debug("Could not fsync project directory %s", directory)
        finally:
            if directory_fd is not None:
                os.close(directory_fd)

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

        if (
            "episode_working_texts" in data and
            not isinstance(data["episode_working_texts"], dict)
        ):
            raise ProjectValidationError(
                "Field 'episode_working_texts' must be a dictionary"
            )

        if (
            "project_kind" in data and
            data["project_kind"] not in ("subtitle", "audiobook")
        ):
            raise ProjectValidationError(
                "Field 'project_kind' must be 'subtitle' or 'audiobook'"
            )

        if (
            "audiobook_document" in data and
            not isinstance(data["audiobook_document"], dict)
        ):
            raise ProjectValidationError(
                "Field 'audiobook_document' must be a dictionary"
            )

    def _ensure_compatibility(self, data: Dict[str, Any]) -> None:
        """Ensure compatibility."""
        ensure_project_compatibility(data)

    def _validate_supported_schema(self, data: Dict[str, Any]) -> None:
        """Reject unsupported or unpublished legacy project formats."""
        try:
            self._schema.validate_supported_version(data)
        except ProjectSchemaError as exc:
            raise ProjectValidationError(str(exc)) from exc

    def _validate_current_schema(self, data: Dict[str, Any]) -> None:
        """Validate the normalized current on-disk project structure."""
        try:
            self._schema.validate_current(data)
        except ProjectSchemaError as exc:
            raise ProjectValidationError(str(exc)) from exc

    def _update_metadata_on_save(self, data: Dict[str, Any]) -> None:
        """Update metadata on save."""
        if "metadata" not in data:
            data["metadata"] = {}

        now = datetime.now().isoformat()
        data["metadata"].setdefault("created_at", now)
        data["metadata"].setdefault("created_by", "")
        data["metadata"].setdefault("studio", "")
        data["metadata"]["modified_at"] = now
        data["metadata"]["format_version"] = PROJECT_FORMAT_VERSION
        data["metadata"]["app_version"] = APP_VERSION

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
            return self._backup_directory_for(self.current_project_path)
        return self._unsaved_backup_directory()

    def list_backups(self) -> List[Path]:
        """List backups."""
        backup_dir = self.get_backup_directory()
        if backup_dir and backup_dir.exists():
            project_stem = Path(self.current_project_path or "").stem
            prefix = f"{project_stem}_" if project_stem else "unsaved_"
            return sorted(
                (
                    path for path in backup_dir.glob(
                        f"*{PROJECT_BACKUP_FILE_EXTENSION}"
                    )
                    if path.name.startswith(prefix)
                ),
                key=lambda p: (p.stat().st_mtime_ns, p.name),
                reverse=True
            )
        return []

    def restore_from_backup(self, backup_path: str, target_path: str) -> bool:
        """Restore from backup."""
        try:
            with open(backup_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            self._validate_supported_schema(data)
            original_version = str(
                (data.get("metadata") or {}).get("format_version") or "0.9"
            )
            original_model = (
                "dynamic_source"
                if is_dynamic_script_project(data)
                else "legacy_merged"
            )
            preserved_legacy_fields = {
                key: deepcopy(data[key])
                for key in (
                    "replica_merge_config",
                    "ass_import_config",
                    "srt_import_config",
                    "docx_import_config",
                )
                if key in data
            }
            self._validate_project_structure(data)
            self._ensure_compatibility(data)
            self._validate_current_schema(data)
            data["_project_format"] = {
                "storage_model": original_model,
                "original_version": original_version,
                "preserved_fields": preserved_legacy_fields,
            }

            target = Path(target_path)
            if target.is_file():
                backup_dir = self._backup_directory_for(str(target))
                backup_dir.mkdir(parents=True, exist_ok=True)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
                safety_path = (
                    backup_dir
                    / (
                        f"{target.stem}_before_restore_{timestamp}"
                        f"{PROJECT_BACKUP_FILE_EXTENSION}"
                    )
                )
                shutil.copy2(target, safety_path)
                self._rotate_backups(
                    backup_dir,
                    f"{target.stem}_",
                    int(self._backup_config["max_backups"]),
                )

            return self._do_save(data, target_path)

        except Exception as e:
            logger.error(f"Restore from backup failed: {e}")
            return False

    def _backup_directory_for(self, project_path: str) -> Path:
        directory = Path(self._backup_config["directory"]).expanduser()
        if self._backup_config["path_mode"] == "absolute":
            resolved = str(Path(project_path).expanduser().resolve())
            digest = hashlib.sha1(
                resolved.encode("utf-8")
            ).hexdigest()[:8]
            stem = Path(project_path).stem or "project"
            return directory / f"{stem}-{digest}"
        return Path(project_path).expanduser().parent / directory

    def _unsaved_backup_directory(self) -> Path:
        if self._backup_config["path_mode"] == "absolute":
            return (
                Path(self._backup_config["directory"]).expanduser()
                / "unsaved"
            )
        if sys.platform == "win32":
            base = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA")
            root = Path(base) if base else Path.home() / "AppData" / "Local"
            return root / "DubbingManager" / "backups" / "unsaved"
        if sys.platform == "darwin":
            return (
                Path.home() / "Library" / "Application Support"
                / "DubbingManager" / "backups" / "unsaved"
            )
        data_home = os.environ.get("XDG_DATA_HOME")
        root = Path(data_home) if data_home else Path.home() / ".local" / "share"
        return root / "dubbing-manager" / "backups" / "unsaved"

    @staticmethod
    def _normalize_backup_config(
        value: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        config = deepcopy(DEFAULT_BACKUP_CONFIG)
        if isinstance(value, dict):
            config.update(value)
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
            ("max_backups", 1, 100, MAX_BACKUPS),
        ):
            try:
                config[key] = max(low, min(high, int(config.get(key, fallback))))
            except (TypeError, ValueError):
                config[key] = fallback
        return config
