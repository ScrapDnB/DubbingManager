"""Сервис для управления проектами"""

import json
import os
import logging
from typing import Dict, Any, Optional
from PySide6.QtWidgets import QMessageBox

from config.constants import DEFAULT_EXPORT_CONFIG, DEFAULT_PROMPTER_CONFIG

logger = logging.getLogger(__name__)


class ProjectService:
    """Сервис для работы с проектами: загрузка, сохранение, автосохранение"""

    def __init__(self):
        self.current_project_path: Optional[str] = None
        self.is_dirty: bool = False

    def create_new_project(self, name: str) -> Dict[str, Any]:
        """Создание нового проекта"""
        return {
            "project_name": name,
            "actors": {},
            "global_map": {},
            "episodes": {},
            "video_paths": {},
            "export_config": DEFAULT_EXPORT_CONFIG.copy(),
            "prompter_config": DEFAULT_PROMPTER_CONFIG.copy(),
        }

    def load_project(self, path: str) -> Optional[Dict[str, Any]]:
        """Загрузка проекта из файла"""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Обратная совместимость
            self._ensure_compatibility(data)

            self.current_project_path = path
            self.is_dirty = False

            logger.info(f"Project loaded from {path}")
            return data

        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON format: {e}")
            raise
        except Exception as e:
            logger.error(f"Load failed: {e}")
            raise

    def save_project(
        self,
        data: Dict[str, Any],
        path: Optional[str] = None
    ) -> bool:
        """Сохранение проекта"""
        save_path = path or self.current_project_path

        if not save_path:
            return False

        return self._do_save(data, save_path)

    def save_project_as(
        self,
        data: Dict[str, Any],
        path: str
    ) -> bool:
        """Сохранение проекта как..."""
        self.current_project_path = path
        return self._do_save(data, path)

    def _do_save(self, data: Dict[str, Any], path: str) -> bool:
        """Внутренний метод сохранения"""
        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)

            self.is_dirty = False
            logger.info(f"Project saved to {path}")
            return True

        except Exception as e:
            logger.error(f"Save failed: {e}")
            return False

    def auto_save(self, data: Dict[str, Any]) -> bool:
        """Автосохранение проекта"""
        if not self.is_dirty:
            return True

        if self.current_project_path:
            path = self.current_project_path + ".bak"
        else:
            path = "temp_autosave.json.bak"

        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
            logger.debug(f"Auto-saved to {path}")
            return True
        except Exception as e:
            logger.error(f"Auto-save failed: {e}")
            return False

    def set_dirty(self, dirty: bool = True) -> None:
        """Установка флага изменений"""
        self.is_dirty = dirty

    def get_project_name(self, data: Dict[str, Any]) -> str:
        """Получение имени проекта"""
        return data.get("project_name", "Новый проект")

    def set_project_name(
        self,
        data: Dict[str, Any],
        name: str
    ) -> None:
        """Установка имени проекта"""
        data["project_name"] = name
        self.set_dirty()

    def get_window_title(self, data: Dict[str, Any]) -> str:
        """Формирование заголовка окна"""
        title = "Dubbing Manager"

        if self.current_project_path:
            title += f" - {os.path.basename(self.current_project_path)}"
        else:
            title += " - [Новый]"

        if self.is_dirty:
            title += " *"

        return title

    def _ensure_compatibility(self, data: Dict[str, Any]) -> None:
        """Обеспечение обратной совместимости формата проекта"""
        if "video_paths" not in data:
            data["video_paths"] = {}
        if "export_config" not in data:
            data["export_config"] = DEFAULT_EXPORT_CONFIG.copy()
        if "prompter_config" not in data:
            data["prompter_config"] = DEFAULT_PROMPTER_CONFIG.copy()
        if "global_map" not in data:
            data["global_map"] = {}
        if "loaded_episodes" not in data:
            data["loaded_episodes"] = {}
