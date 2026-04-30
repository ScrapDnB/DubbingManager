"""Сервис для управления проектами"""

import json
import os
import shutil
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List

# fcntl доступен только на Unix-системах
# Используем try/except для надёжности при сборке PyInstaller
try:
    import fcntl
    HAS_FCNTL = True
except ImportError:
    HAS_FCNTL = False

from PySide6.QtWidgets import QMessageBox

from config.constants import (
    DEFAULT_EXPORT_CONFIG,
    DEFAULT_PROMPTER_CONFIG,
    DEFAULT_REPLICA_MERGE_CONFIG,
    PROJECT_VERSION,
)

logger = logging.getLogger(__name__)

# Версия формата проекта
PROJECT_FORMAT_VERSION = PROJECT_VERSION

# Максимальное количество бэкапов
MAX_BACKUPS = 10


class ProjectValidationError(Exception):
    """Исключение валидации проекта"""
    pass


class ProjectService:
    """
    Сервис для работы с проектами: загрузка, сохранение, автосохранение.
    
    Особенности:
    - Атомарное сохранение через временный файл
    - Валидация структуры данных при загрузке
    - Мета-информация (версии, даты)
    - Ротация бэкапов
    - Обратная совместимость форматов
    """

    def __init__(self):
        self.current_project_path: Optional[str] = None
        self.is_dirty: bool = False
        self._project_metadata: Dict[str, Any] = {}

    def create_new_project(self, name: str) -> Dict[str, Any]:
        """
        Создание нового проекта.
        
        Args:
            name: Название проекта
            
        Returns:
            Словарь с данными проекта
        """
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
            "export_config": DEFAULT_EXPORT_CONFIG.copy(),
            "prompter_config": DEFAULT_PROMPTER_CONFIG.copy(),
            "replica_merge_config": DEFAULT_REPLICA_MERGE_CONFIG.copy(),
            "project_folder": None,  # Путь к папке проекта
        }

    def load_project(self, path: str) -> Optional[Dict[str, Any]]:
        """
        Загрузка проекта из файла.
        
        Args:
            path: Путь к файлу проекта
            
        Returns:
            Данные проекта
            
        Raises:
            ProjectValidationError: Если данные не прошли валидацию
            json.JSONDecodeError: Если файл не является валидным JSON
        """
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Валидация структуры
            self._validate_project_structure(data)
            
            # Обратная совместимость
            self._ensure_compatibility(data)
            
            # Обновление metadata
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
        """
        Сохранение проекта.
        
        Args:
            data: Данные проекта
            path: Путь для сохранения (если None, используется текущий)
            
        Returns:
            True если сохранение успешно
        """
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
        """
        Сохранение проекта как...
        
        Args:
            data: Данные проекта
            path: Путь для сохранения
            
        Returns:
            True если сохранение успешно
        """
        self.current_project_path = path
        return self._do_save(data, path)

    def _do_save(self, data: Dict[str, Any], path: str) -> bool:
        """
        Внутренний метод сохранения с атомарностью и блокировкой файла.

        Использует временный файл, атомарную замену и файловую блокировку
        для предотвращения повреждения данных при одновременной записи.

        Args:
            data: Данные проекта
            path: Путь для сохранения

        Returns:
            True если сохранение успешно
        """
        # Обновление metadata перед сохранением
        self._update_metadata_on_save(data)

        # Временный файл для атомарного сохранения
        temp_path = path + ".tmp"

        try:
            # Запись во временный файл с эксклюзивной блокировкой
            with open(temp_path, 'w', encoding='utf-8') as f:
                # Устанавливаем эксклюзивную блокировку (неблокирующую)
                # fcntl доступен только на Unix-системах
                if HAS_FCNTL:
                    try:
                        fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                    except (IOError, OSError) as lock_err:
                        logger.warning(f"Could not acquire lock on {temp_path}: {lock_err}")
                        # Продолжаем без блокировки - лучше сохранить, чем потерять данные

                json.dump(data, f, ensure_ascii=False, indent=4)
                f.flush()
                os.fsync(f.fileno())  # Гарантируем запись на диск

                # Освобождаем блокировку
                if HAS_FCNTL:
                    try:
                        fcntl.flock(f.fileno(), fcntl.LOCK_UN)
                    except (IOError, OSError):
                        pass

            # Атомарная замена основного файла
            os.replace(temp_path, path)

            self.is_dirty = False
            logger.info(f"Project saved to {path}")
            return True

        except Exception as e:
            logger.error(f"Save failed: {e}")
            # Очистка временного файла при ошибке
            if os.path.exists(temp_path):
                try:
                    os.unlink(temp_path)
                except OSError:
                    pass
            return False
        finally:
            # Дополнительная очистка на случай если os.replace не сработал
            if os.path.exists(temp_path):
                try:
                    os.unlink(temp_path)
                except OSError:
                    pass

    def auto_save(self, data: Dict[str, Any]) -> bool:
        """
        Автосохранение проекта с ротацией бэкапов.
        
        Args:
            data: Данные проекта
            
        Returns:
            True если автосохранение успешно
        """
        if not self.is_dirty:
            return True

        if self.current_project_path:
            # Директория для бэкапов
            backup_dir = Path(self.current_project_path).parent / ".backups"
            backup_dir.mkdir(exist_ok=True)
            
            # Имя файла с timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            base_name = Path(self.current_project_path).stem
            backup_path = backup_dir / f"{base_name}_{timestamp}.json"
            
            try:
                # Сохранение бэкапа
                with open(backup_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=4)
                
                logger.debug(f"Auto-saved to {backup_path}")
                
                # Ротация старых бэкапов
                self._rotate_backups(backup_dir)
                
                return True
                
            except Exception as e:
                logger.error(f"Auto-save failed: {e}")
                return False
        else:
            # Если проект ещё не сохранён, используем временный файл
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
        """
        Ротация бэкапов - хранит только последние MAX_BACKUPS.
        
        Args:
            backup_dir: Директория с бэкапами
        """
        try:
            # Получаем список всех бэкапов, сортируем по времени
            backups = sorted(
                backup_dir.glob("*.json"),
                key=lambda p: p.stat().st_mtime,
                reverse=True
            )
            
            # Удаляем старые, если их больше MAX_BACKUPS
            for old_backup in backups[MAX_BACKUPS:]:
                try:
                    old_backup.unlink()
                    logger.debug(f"Removed old backup: {old_backup}")
                except OSError as e:
                    logger.warning(f"Failed to remove backup {old_backup}: {e}")
                    
        except Exception as e:
            logger.error(f"Backup rotation failed: {e}")

    def _validate_project_structure(self, data: Dict[str, Any]) -> None:
        """
        Валидация структуры данных проекта.
        
        Args:
            data: Данные проекта
            
        Raises:
            ProjectValidationError: Если структура невалидна
        """
        # Проверка обязательных полей
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
        
        # Проверка типов данных
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
        
        # Проверка global_map (если есть)
        if "global_map" in data and not isinstance(data["global_map"], dict):
            raise ProjectValidationError(
                "Field 'global_map' must be a dictionary"
            )

        # Проверка episode_actor_map (если есть)
        if (
            "episode_actor_map" in data and
            not isinstance(data["episode_actor_map"], dict)
        ):
            raise ProjectValidationError(
                "Field 'episode_actor_map' must be a dictionary"
            )
        
        # Проверка video_paths (если есть)
        if "video_paths" in data and not isinstance(data["video_paths"], dict):
            raise ProjectValidationError(
                "Field 'video_paths' must be a dictionary"
            )

        # Проверка episode_texts (если есть)
        if "episode_texts" in data and not isinstance(data["episode_texts"], dict):
            raise ProjectValidationError(
                "Field 'episode_texts' must be a dictionary"
            )

    def _ensure_compatibility(self, data: Dict[str, Any]) -> None:
        """
        Обеспечение обратной совместимости формата проекта.

        Добавляет缺失ствующие поля со значениями по умолчанию.

        Args:
            data: Данные проекта
        """
        if "video_paths" not in data:
            data["video_paths"] = {}
        if "episode_texts" not in data:
            data["episode_texts"] = {}
        if "export_config" not in data:
            data["export_config"] = DEFAULT_EXPORT_CONFIG.copy()
        if "prompter_config" not in data:
            data["prompter_config"] = DEFAULT_PROMPTER_CONFIG.copy()
        if "global_map" not in data:
            data["global_map"] = {}
        if "episode_actor_map" not in data:
            data["episode_actor_map"] = {}
        if "loaded_episodes" not in data:
            data["loaded_episodes"] = {}
        if "replica_merge_config" not in data:
            # Миграция: если настройки объединения в export_config, переносим их
            if "export_config" in data:
                export_cfg = data["export_config"]
                data["replica_merge_config"] = {
                    'merge': export_cfg.get('merge', True),
                    'merge_gap': export_cfg.get('merge_gap', 5),
                    'p_short': export_cfg.get('p_short', 0.5),
                    'p_long': export_cfg.get('p_long', 2.0),
                }
            else:
                data["replica_merge_config"] = DEFAULT_REPLICA_MERGE_CONFIG.copy()
        
        # Добавляем project_folder для старых проектов
        if "project_folder" not in data:
            data["project_folder"] = None

        # Проверка metadata для старых проектов
        if "metadata" not in data:
            now = datetime.now().isoformat()
            data["metadata"] = {
                "format_version": "0.9",  # Старый формат
                "app_version": "pre-1.0",
                "created_at": now,
                "modified_at": now,
            }

    def _update_metadata_on_save(self, data: Dict[str, Any]) -> None:
        """
        Обновление metadata при сохранении.
        
        Args:
            data: Данные проекта
        """
        if "metadata" not in data:
            data["metadata"] = {}
        
        # Обновление времени изменения
        data["metadata"]["modified_at"] = datetime.now().isoformat()
        data["metadata"]["format_version"] = PROJECT_FORMAT_VERSION
        data["metadata"]["app_version"] = "1.0+"

    def _update_metadata_on_load(self, data: Dict[str, Any], path: str) -> None:
        """
        Обновление metadata при загрузке.
        
        Args:
            data: Данные проекта
            path: Путь к файлу
        """
        if "metadata" in data:
            self._project_metadata = data["metadata"]
        else:
            self._project_metadata = {}

    def set_dirty(self, dirty: bool = True) -> None:
        """
        Установка флага изменений.
        
        Args:
            dirty: True если проект изменён
        """
        self.is_dirty = dirty

    def get_project_name(self, data: Dict[str, Any]) -> str:
        """
        Получение имени проекта.
        
        Args:
            data: Данные проекта
            
        Returns:
            Название проекта
        """
        return data.get("project_name", "Новый проект")

    def set_project_name(
        self,
        data: Dict[str, Any],
        name: str
    ) -> None:
        """
        Установка имени проекта.
        
        Args:
            data: Данные проекта
            name: Новое название
        """
        data["project_name"] = name
        self.set_dirty()

    def get_window_title(self, data: Dict[str, Any]) -> str:
        """
        Формирование заголовка окна.
        
        Args:
            data: Данные проекта
            
        Returns:
            Заголовок окна
        """
        title = "Dubbing Manager"

        if self.current_project_path:
            title += f" - {os.path.basename(self.current_project_path)}"
        else:
            title += " - [Новый]"

        if self.is_dirty:
            title += " *"

        return title

    def get_project_metadata(self) -> Dict[str, Any]:
        """
        Получение мета-информации проекта.
        
        Returns:
            Мета-информация
        """
        return self._project_metadata.copy()

    def get_backup_directory(self) -> Optional[Path]:
        """
        Получение директории бэкапов для текущего проекта.
        
        Returns:
            Путь к директории бэкапов или None
        """
        if self.current_project_path:
            return Path(self.current_project_path).parent / ".backups"
        return None

    def list_backups(self) -> List[Path]:
        """
        Получение списка бэкапов.
        
        Returns:
            Отсортированный список путей к бэкапам
        """
        backup_dir = self.get_backup_directory()
        if backup_dir and backup_dir.exists():
            return sorted(
                backup_dir.glob("*.json"),
                key=lambda p: p.stat().st_mtime,
                reverse=True
            )
        return []

    def restore_from_backup(self, backup_path: str, target_path: str) -> bool:
        """
        Восстановление из бэкапа.
        
        Args:
            backup_path: Путь к файлу бэкапа
            target_path: Путь для восстановления
            
        Returns:
            True если восстановление успешно
        """
        try:
            # Чтение бэкапа
            with open(backup_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Валидация
            self._validate_project_structure(data)
            
            # Сохранение в целевой файл
            return self._do_save(data, target_path)
            
        except Exception as e:
            logger.error(f"Restore from backup failed: {e}")
            return False
