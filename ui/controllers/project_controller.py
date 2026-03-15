"""Контроллер управления проектами"""

from PySide6.QtWidgets import QFileDialog, QMessageBox
from typing import Dict, Any, Optional, List

import os
import logging

from services import ProjectService
from core.commands import (
    UpdateProjectNameCommand,
    SetProjectFolderCommand,
)

logger = logging.getLogger(__name__)


class ProjectController:
    """
    Контроллер для управления проектами.

    Отвечает за:
    - Создание нового проекта
    - Сохранение и загрузку проектов
    - Переименование проекта
    - Установка папки проекта
    - Автосохранение
    """

    def __init__(
        self,
        project_service: ProjectService,
        data_ref: Dict[str, Any],
        undo_stack: Any,
        on_dirty_callback: Optional[callable] = None
    ):
        self.project_service = project_service
        self.data_ref = data_ref
        self.undo_stack = undo_stack
        self.on_dirty_callback = on_dirty_callback

    def _mark_dirty(self) -> None:
        """Пометка проекта как изменённого"""
        if self.on_dirty_callback:
            self.on_dirty_callback()

    def create_new_project(self, name: str) -> Dict[str, Any]:
        """
        Создание нового проекта

        Args:
            name: название проекта

        Returns:
            Данные нового проекта
        """
        self.data_ref = self.project_service.create_new_project(name)
        return self.data_ref

    def save_project(self, path: Optional[str] = None) -> bool:
        """
        Сохранение проекта

        Args:
            path: путь сохранения (если None - используется текущий)

        Returns:
            True если успешно
        """
        result = self.project_service.save_project(self.data_ref, path)
        if result:
            logger.info(f"Project saved: {path or self.project_service.current_project_path}")
        return result

    def save_project_as(self, path: str) -> bool:
        """
        Сохранение проекта как...

        Args:
            path: путь сохранения

        Returns:
            True если успешно
        """
        result = self.project_service.save_project_as(self.data_ref, path)
        if result:
            logger.info(f"Project saved as: {path}")
        return result

    def load_project(self, path: str) -> Optional[Dict[str, Any]]:
        """
        Загрузка проекта

        Args:
            path: путь к файлу проекта

        Returns:
            Данные проекта или None
        """
        try:
            data = self.project_service.load_project(path)
            self.data_ref.clear()
            self.data_ref.update(data)
            logger.info(f"Project loaded from: {path}")
            return data
        except Exception as e:
            logger.error(f"Failed to load project: {e}")
            return None

    def maybe_save(self, parent_widget=None) -> bool:
        """
        Проверка необходимости сохранения

        Args:
            parent_widget: родительский виджет для диалога

        Returns:
            True если можно продолжать
        """
        if not self.project_service.is_dirty:
            return True

        if parent_widget:
            reply = QMessageBox.question(
                parent_widget,
                "Сохранить?",
                "Сохранить изменения?",
                QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel
            )

            if reply == QMessageBox.Save:
                return self.save_project()
            return reply == QMessageBox.Discard

        return True

    def update_project_name(
        self,
        new_name: str,
        old_name: Optional[str] = None
    ) -> None:
        """
        Обновление названия проекта

        Args:
            new_name: новое название
            old_name: старое название (для отмены)
        """
        command = UpdateProjectNameCommand(self.data_ref, new_name)
        self.undo_stack.push(command)
        self._mark_dirty()

    def set_project_folder(
        self,
        folder_path: Optional[str]
    ) -> None:
        """
        Установка папки проекта

        Args:
            folder_path: путь к папке (None для очистки)
        """
        command = SetProjectFolderCommand(self.data_ref, folder_path)
        self.undo_stack.push(command)
        self._mark_dirty()

    def auto_save(self) -> bool:
        """
        Автосохранение проекта

        Returns:
            True если успешно
        """
        return self.project_service.auto_save(self.data_ref)

    def get_window_title(self) -> str:
        """
        Получение заголовка окна

        Returns:
            Заголовок окна
        """
        return self.project_service.get_window_title(self.data_ref)

    def get_project_name(self) -> str:
        """Получение названия проекта"""
        return self.project_service.get_project_name(self.data_ref)

    def is_dirty(self) -> bool:
        """Проверка флага изменений"""
        return self.project_service.is_dirty

    def set_dirty(self, dirty: bool = True) -> None:
        """Установка флага изменений"""
        self.project_service.set_dirty(dirty)

    def get_backup_directory(self) -> Optional[str]:
        """Получение директории бэкапов"""
        backup_dir = self.project_service.get_backup_directory()
        return str(backup_dir) if backup_dir else None

    def list_backups(self) -> List[str]:
        """Получение списка бэкапов"""
        backups = self.project_service.list_backups()
        return [str(p) for p in backups]

    def restore_from_backup(
        self,
        backup_path: str,
        target_path: str
    ) -> bool:
        """
        Восстановление из бэкапа

        Args:
            backup_path: путь к бэкапу
            target_path: путь для восстановления

        Returns:
            True если успешно
        """
        return self.project_service.restore_from_backup(backup_path, target_path)

    def get_current_project_path(self) -> Optional[str]:
        """Получение пути к текущему проекту"""
        return self.project_service.current_project_path

    def set_current_project_path(self, path: str) -> None:
        """Установка пути к текущему проекту"""
        self.project_service.current_project_path = path
