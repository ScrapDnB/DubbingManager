"""Сервис для управления папкой проекта и поиска файлов"""

import os
import re
import logging
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Set
from collections import defaultdict

logger = logging.getLogger(__name__)


class ProjectFolderService:
    """
    Сервис для управления папкой проекта.
    
    Возможности:
    - Установка и сохранение папки проекта
    - Рекурсивный поиск ASS и видео файлов
    - Умное сопоставление файлов с эпизодами
    - Поиск файлов даже при изменении структуры подпапок
    """

    # Расширения файлов
    ASS_EXTENSIONS = {'.ass'}
    VIDEO_EXTENSIONS = {'.mp4', '.mkv', '.avi', '.mov', '.m4v', '.wmv'}

    def __init__(self):
        self._found_files_cache: Dict[str, Dict[str, str]] = {}

    def set_project_folder(
        self,
        data: Dict,
        folder_path: str
    ) -> bool:
        """
        Установка папки проекта.
        
        Args:
            data: Данные проекта
            folder_path: Путь к папке
            
        Returns:
            True если папка установлена успешно
        """
        if not os.path.isdir(folder_path):
            logger.error(f"Folder does not exist: {folder_path}")
            return False

        # Нормализуем путь
        folder_path = os.path.abspath(folder_path)
        
        # Сохраняем в данные проекта
        data["project_folder"] = folder_path
        
        logger.info(f"Project folder set: {folder_path}")
        return True

    def clear_project_folder(self, data: Dict) -> None:
        """Очистка папки проекта"""
        data.pop("project_folder", None)
        self._found_files_cache.clear()
        logger.info("Project folder cleared")

    def get_project_folder(self, data: Dict) -> Optional[str]:
        """Получение пути к папке проекта"""
        return data.get("project_folder")

    def find_all_media_files(
        self,
        folder_path: str
    ) -> Dict[str, Dict[str, str]]:
        """
        Рекурсивный поиск всех медиа файлов в папке.
        
        Args:
            folder_path: Путь к папке для поиска
            
        Returns:
            Словарь с найденными файлами:
            {
                "ass": {episode_num: path},
                "video": {episode_num: path}
            }
        """
        if not os.path.isdir(folder_path):
            return {"ass": {}, "video": {}}

        # Проверяем кэш
        cache_key = folder_path
        if cache_key in self._found_files_cache:
            return self._found_files_cache[cache_key]

        result = {"ass": {}, "video": {}}

        # Рекурсивный обход папки
        for root, dirs, files in os.walk(folder_path):
            # Пропускаем скрытые папки и кэш
            dirs[:] = [d for d in dirs if not d.startswith('.')]

            for file in files:
                if file.startswith('.'):
                    continue

                file_path = os.path.join(root, file)
                ext = os.path.splitext(file)[1].lower()

                # Извлекаем номер серии из имени файла
                episode_num = self._extract_episode_number(file)

                if episode_num:
                    if ext in self.ASS_EXTENSIONS:
                        result["ass"][episode_num] = file_path
                    elif ext in self.VIDEO_EXTENSIONS:
                        result["video"][episode_num] = file_path

        # Кэшируем результат
        self._found_files_cache[cache_key] = result

        logger.info(
            f"Found {len(result['ass'])} ASS files "
            f"and {len(result['video'])} video files"
        )

        return result

    def _extract_episode_number(self, filename: str) -> Optional[str]:
        """
        Извлечение номера серии из имени файла.
        
        Поддерживаемые форматы:
        - Series_01.ass, Series_01.mkv
        - EP01.ass, Ep01.mkv
        - Episode 01.ass
        - S01E01.ass
        - [Subs] Series - 01.ass
        - Просто цифры: 01.ass, 1.ass
        
        Args:
            filename: Имя файла
            
        Returns:
            Номер серии (строка) или None
        """
        # Убираем расширение
        name = os.path.splitext(filename)[0]

        # Паттерны для поиска номера серии
        patterns = [
            # S01E01, S1E1
            r'[Ss](\d+)[Ee](\d+)',
            # EP01, Ep01, ep01
            r'[Ee][Pp]?(\d+)',
            # Episode 01
            r'[Ee]pisode\s*(\d+)',
            # - 01 (после дефиса)
            r'-\s*(\d+)',
            # [01]
            r'\[(\d+)\]',
            # Просто цифры в конце или начале
            r'^(\d+)',
            r'(\d+)$',
        ]

        for pattern in patterns:
            match = re.search(pattern, name)
            if match:
                groups = match.groups()
                if len(groups) == 2:
                    # Для S01E01 комбинируем
                    return f"{int(groups[0])} {int(groups[1])}"
                else:
                    # Нормализуем номер (убираем ведущие нули)
                    num = str(int(groups[0]))
                    return num

        return None

    def scan_and_link_files(
        self,
        data: Dict,
        folder_path: Optional[str] = None
    ) -> Tuple[int, int]:
        """
        Сканирование папки и автоматическое связывание файлов с эпизодами.
        
        Args:
            data: Данные проекта
            folder_path: Путь к папке (если None, используется project_folder)
            
        Returns:
            Tuple(количество ASS файлов, количество видео файлов)
        """
        if not folder_path:
            folder_path = self.get_project_folder(data)

        if not folder_path:
            return 0, 0

        found = self.find_all_media_files(folder_path)
        
        ass_count = 0
        video_count = 0

        # Связываем ASS файлы
        for ep_num, path in found["ass"].items():
            if ep_num not in data.get("episodes", {}):
                data["episodes"][ep_num] = path
                ass_count += 1
            else:
                # Обновляем путь если файл перемещён
                old_path = data["episodes"][ep_num]
                if not os.path.exists(old_path):
                    data["episodes"][ep_num] = path
                    logger.info(f"Updated path for episode {ep_num}")

        # Связываем видео файлы
        if "video_paths" not in data:
            data["video_paths"] = {}

        for ep_num, path in found["video"].items():
            if ep_num not in data.get("video_paths", {}):
                data["video_paths"][ep_num] = path
                video_count += 1
            else:
                old_path = data["video_paths"][ep_num]
                if not os.path.exists(old_path):
                    data["video_paths"][ep_num] = path

        logger.info(
            f"Linked {ass_count} ASS files and {video_count} video files"
        )

        return ass_count, video_count

    def find_missing_files(
        self,
        data: Dict,
        folder_path: Optional[str] = None
    ) -> Dict[str, List[str]]:
        """
        Поиск отсутствующих файлов для эпизодов.
        
        Args:
            data: Данные проекта
            folder_path: Путь к папке
            
        Returns:
            Словарь с отсутствующими файлами:
            {
                "ass": [ep_num1, ep_num2, ...],
                "video": [ep_num1, ep_num2, ...]
            }
        """
        if not folder_path:
            folder_path = self.get_project_folder(data)

        result = {"ass": [], "video": []}

        if not folder_path:
            return result

        found = self.find_all_media_files(folder_path)

        # Проверяем ASS файлы
        for ep_num in data.get("episodes", {}).keys():
            if ep_num not in found["ass"]:
                result["ass"].append(ep_num)

        # Проверяем видео файлы
        for ep_num in data.get("video_paths", {}).keys():
            if ep_num not in found["video"]:
                result["video"].append(ep_num)

        return result

    def get_folder_stats(self, folder_path: str) -> Dict:
        """
        Получение статистики по папке.
        
        Args:
            folder_path: Путь к папке
            
        Returns:
            Словарь со статистикой
        """
        found = self.find_all_media_files(folder_path)

        return {
            "ass_count": len(found["ass"]),
            "video_count": len(found["video"]),
            "episodes": sorted(
                set(found["ass"].keys()) | set(found["video"].keys()),
                key=lambda x: int(x) if x.isdigit() else 0
            )
        }

    def invalidate_cache(self, folder_path: Optional[str] = None) -> None:
        """
        Инвалидация кэша файлов.
        
        Args:
            folder_path: Путь к папке (если None, очистка всего кэша)
        """
        if folder_path:
            self._found_files_cache.pop(folder_path, None)
        else:
            self._found_files_cache.clear()

    def suggest_video_for_episode(
        self,
        data: Dict,
        episode_num: str
    ) -> Optional[str]:
        """
        Поиск подходящего видео файла для серии.
        
        Args:
            data: Данные проекта
            episode_num: Номер серии
            
        Returns:
            Путь к видео файлу или None
        """
        folder_path = self.get_project_folder(data)
        if not folder_path:
            return None

        found = self.find_all_media_files(folder_path)
        return found["video"].get(episode_num)

    def batch_import_from_folder(
        self,
        data: Dict,
        folder_path: Optional[str] = None
    ) -> Tuple[int, int]:
        """
        Массовый импорт файлов из папки проекта.
        
        Args:
            data: Данные проекта
            folder_path: Путь к папке
            
        Returns:
            Tuple(добавлено ASS, добавлено видео)
        """
        if not folder_path:
            folder_path = self.get_project_folder(data)

        if not folder_path:
            return 0, 0

        found = self.find_all_media_files(folder_path)

        added_ass = 0
        added_video = 0

        # Добавляем ASS файлы
        for ep_num, path in found["ass"].items():
            if ep_num not in data.get("episodes", {}):
                data["episodes"][ep_num] = path
                added_ass += 1

        # Добавляем видео файлы
        if "video_paths" not in data:
            data["video_paths"] = {}

        for ep_num, path in found["video"].items():
            if ep_num not in data["video_paths"]:
                data["video_paths"][ep_num] = path
                added_video += 1

        logger.info(
            f"Batch imported: {added_ass} ASS, {added_video} video"
        )

        return added_ass, added_video
