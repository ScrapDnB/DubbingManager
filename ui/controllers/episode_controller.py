"""Контроллер управления эпизодами"""

import os
import re
from PySide6.QtWidgets import (
    QFileDialog, QMessageBox, QInputDialog, QProgressDialog, QApplication
)
from PySide6.QtCore import Qt
from typing import Dict, List, Any, Optional, Tuple, Callable

import logging

from services import EpisodeService
from config.constants import DEFAULT_REPLICA_MERGE_CONFIG

logger = logging.getLogger(__name__)


class EpisodeController:
    """
    Контроллер для управления эпизодами.

    Отвечает за:
    - Загрузку и смену эпизодов
    - Импорт файлов (ASS, SRT, DOCX)
    - Сохранение эпизодов
    - Переименование и удаление эпизодов
    """

    def __init__(
        self,
        episode_service: EpisodeService,
        data_ref: Dict[str, Any],
        on_dirty_callback: Optional[callable] = None
    ):
        self.episode_service = episode_service
        self.data_ref = data_ref
        self.on_dirty_callback = on_dirty_callback

    def _mark_dirty(self) -> None:
        """Пометка проекта как изменённого"""
        if self.on_dirty_callback:
            self.on_dirty_callback()

    def change_episode(self, ep_num: str) -> List[Dict[str, Any]]:
        """
        Смена текущего эпизода

        Args:
            ep_num: номер эпизода

        Returns:
            Список реплик эпизода
        """
        episodes = self.data_ref.get("episodes", {})
        path = episodes.get(ep_num)

        if not path:
            return []

        # Проверяем существование файла
        if not os.path.exists(path):
            return []

        # Определяем тип файла и загружаем
        if path.lower().endswith('.srt'):
            lines = self.episode_service.load_srt_episode(ep_num, episodes)
        else:
            lines = self.episode_service.load_episode(ep_num, episodes)

        # Сохраняем в кэш проекта
        self.data_ref["loaded_episodes"][ep_num] = lines

        return lines

    def import_ass(
        self,
        paths: Optional[List[str]] = None,
        parent_widget=None
    ) -> Tuple[bool, str]:
        """
        Импорт ASS файлов

        Args:
            paths: пути к файлам (если None - показать диалог)
            parent_widget: родительский виджет для диалога

        Returns:
            Tuple[success, message]
        """
        if not paths:
            paths, _ = QFileDialog.getOpenFileNames(
                parent_widget,
                "Импорт ASS",
                "",
                "ASS Files (*.ass)"
            )

        if not paths:
            return False, "Файлы не выбраны"

        episodes = self.data_ref.get("episodes", {})
        imported_count = 0

        for path in paths:
            if not os.path.exists(path):
                continue

            # Извлекаем номер серии из имени файла
            ep_num = self._extract_episode_number(path)
            if not ep_num:
                continue

            episodes[ep_num] = path
            imported_count += 1

        self.data_ref["episodes"] = episodes
        self._mark_dirty()

        return True, f"Импортировано серий: {imported_count}"

    def import_srt(
        self,
        paths: Optional[List[str]] = None,
        parent_widget=None
    ) -> Tuple[bool, str]:
        """
        Импорт SRT файлов

        Args:
            paths: пути к файлам (если None - показать диалог)
            parent_widget: родительский виджет для диалога

        Returns:
            Tuple[success, message]
        """
        if not paths:
            paths, _ = QFileDialog.getOpenFileNames(
                parent_widget,
                "Импорт SRT",
                "",
                "SRT Files (*.srt)"
            )

        if not paths:
            return False, "Файлы не выбраны"

        episodes = self.data_ref.get("episodes", {})
        imported_count = 0

        for path in paths:
            if not os.path.exists(path):
                continue

            ep_num = self._extract_episode_number(path)
            if not ep_num:
                continue

            episodes[ep_num] = path
            imported_count += 1

        self.data_ref["episodes"] = episodes
        self._mark_dirty()

        return True, f"Импортировано серий: {imported_count}"

    def import_docx(
        self,
        paths: Optional[List[str]] = None,
        parent_widget=None
    ) -> Tuple[bool, str]:
        """
        Импорт DOCX файлов

        Args:
            paths: пути к файлам (если None - показать диалог)
            parent_widget: родительский виджет для диалога

        Returns:
            Tuple[success, message]
        """
        if not paths:
            paths, _ = QFileDialog.getOpenFileNames(
                parent_widget,
                "Импорт DOCX",
                "",
                "DOCX Files (*.docx)"
            )

        if not paths:
            return False, "Файлы не выбраны"

        # Импорт DOCX требует диалога настройки - возвращаем пути
        return True, paths[0] if len(paths) == 1 else str(paths)

    def save_episode(
        self,
        ep_num: str,
        target_path: Optional[str] = None
    ) -> Tuple[bool, str]:
        """
        Сохранение эпизода

        Args:
            ep_num: номер эпизода
            target_path: путь для сохранения (если None - в оригинал)

        Returns:
            Tuple[success, message]
        """
        episodes = self.data_ref.get("episodes", {})
        loaded_episodes = self.data_ref.get("loaded_episodes", {})

        if ep_num not in loaded_episodes:
            return False, "Эпизод не загружен"

        memory_lines = loaded_episodes[ep_num]

        # Определяем тип файла
        source_path = episodes.get(ep_num, "")
        if source_path.lower().endswith('.srt'):
            return self.episode_service.save_episode_to_srt(
                ep_num, episodes, memory_lines, target_path
            )
        else:
            return self.episode_service.save_episode_to_ass(
                ep_num, episodes, memory_lines, target_path
            )

    def rename_episode(
        self,
        old_name: str,
        new_name: str,
        parent_widget=None
    ) -> bool:
        """
        Переименование эпизода

        Args:
            old_name: старое имя
            new_name: новое имя
            parent_widget: родительский виджет

        Returns:
            True если успешно
        """
        if not new_name or new_name == old_name:
            return False

        episodes = self.data_ref.get("episodes", {})

        if old_name not in episodes:
            return False

        # Перемещаем данные
        path = episodes.pop(old_name)
        episodes[new_name] = path

        # Обновляем video_paths
        video_paths = self.data_ref.get("video_paths", {})
        if old_name in video_paths:
            video_paths[new_name] = video_paths.pop(old_name)

        # Обновляем loaded_episodes
        loaded_episodes = self.data_ref.get("loaded_episodes", {})
        if old_name in loaded_episodes:
            loaded_episodes[new_name] = loaded_episodes.pop(old_name)

        self._mark_dirty()
        return True

    def delete_episode(self, ep_num: str) -> bool:
        """
        Удаление эпизода

        Args:
            ep_num: номер эпизода

        Returns:
            True если успешно
        """
        episodes = self.data_ref.get("episodes", {})
        video_paths = self.data_ref.get("video_paths", {})
        loaded_episodes = self.data_ref.get("loaded_episodes", {})

        if ep_num not in episodes:
            return False

        episodes.pop(ep_num, None)
        video_paths.pop(ep_num, None)
        loaded_episodes.pop(ep_num, None)

        self._mark_dirty()
        return True

    def _extract_episode_number(self, path: str) -> str:
        """
        Извлечение номера эпизода из пути к файлу

        Args:
            path: путь к файлу

        Returns:
            Номер эпизода или пустая строка
        """
        import re
        filename = os.path.basename(path)

        # Пробуем найти номер в имени файла
        match = re.search(r'[Ss](\d+)[Ee](\d+)|(\d+)[xX](\d+)|[Ee]p\.?\s*(\d+)', filename)
        if match:
            groups = match.groups()
            if groups[0] and groups[1]:  # S01E01
                return f"{int(groups[1])}"
            elif groups[2] and groups[3]:  # 1x01
                return f"{int(groups[3])}"
            elif groups[4]:  # Ep. 1
                return f"{int(groups[4])}"

        # Если не нашли паттерн, используем первое число
        numbers = re.findall(r'\d+', filename)
        if numbers:
            return numbers[-1]  # Берём последнее число

        # Если нет чисел, используем имя файла без расширения
        name = os.path.splitext(filename)[0]
        return name if name else "1"

    def get_episode_list(self) -> List[str]:
        """Получение списка номеров эпизодов"""
        return sorted(
            self.data_ref.get("episodes", {}).keys(),
            key=lambda x: int(x) if x.isdigit() else 0
        )

    def get_current_episode_path(self, ep_num: str) -> Optional[str]:
        """Получение пути к текущему эпизоду"""
        return self.data_ref.get("episodes", {}).get(ep_num)

    def invalidate_episode_cache(self, ep_num: str) -> None:
        """Инвалидация кэша эпизода"""
        self.episode_service.invalidate_episode(ep_num)
        self.data_ref.get("loaded_episodes", {}).pop(ep_num, None)
